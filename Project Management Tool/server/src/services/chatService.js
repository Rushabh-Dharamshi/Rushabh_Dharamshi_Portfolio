const { GoogleAuth } = require('google-auth-library');
const projectRepository = require('../repositories/projectRepository');
const taskRepository = require('../repositories/taskRepository');

const CONVERSATION_TTL_MS = 45 * 60 * 1000;
const MAX_CONVERSATIONS = 300;

const conversations = new Map();
const auth = new GoogleAuth({
  scopes: ['https://www.googleapis.com/auth/cloud-platform'],
});

let authClientPromise;

function getVertexConfig() {
  const ragRegion = process.env.GCP_REGION || 'europe-west2';
  const geminiModel = process.env.GEMINI_MODEL || 'gemini-3.1-pro-preview';

  return {
    projectId: process.env.GCP_PROJECT_ID || process.env.GOOGLE_CLOUD_PROJECT || process.env.GCLOUD_PROJECT,
    ragRegion,
    geminiRegion: process.env.GEMINI_REGION || (geminiModel.startsWith('gemini-3') ? 'global' : ragRegion),
    ragCorpusId: process.env.VERTEX_RAG_CORPUS_ID,
    geminiModel,
    ragTopK: Number(process.env.RAG_TOP_K || 4),
    temperature: Number(process.env.GEMINI_TEMPERATURE || 0.15),
    maxOutputTokens: Number(process.env.GEMINI_MAX_OUTPUT_TOKENS || 512),
  };
}

function validateVertexConfig(config) {
  const missing = [];

  if (!config.projectId) {
    missing.push('GCP_PROJECT_ID (or GOOGLE_CLOUD_PROJECT)');
  }

  if (!config.ragCorpusId) {
    missing.push('VERTEX_RAG_CORPUS_ID');
  }

  if (missing.length > 0) {
    throw new Error(`Missing required Vertex settings: ${missing.join(', ')}`);
  }
}

async function getAuthClient() {
  if (!authClientPromise) {
    authClientPromise = auth.getClient();
  }

  return authClientPromise;
}

async function vertexRequest({ url, body }) {
  const client = await getAuthClient();
  const headers = await client.getRequestHeaders(url);
  headers['Content-Type'] = 'application/json';

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  const responseText = await response.text();
  let payload = {};

  if (responseText) {
    try {
      payload = JSON.parse(responseText);
    } catch (error) {
      payload = { raw: responseText };
    }
  }

  if (!response.ok) {
    throw new Error(`Vertex API ${response.status}: ${responseText || response.statusText}`);
  }

  return payload;
}

function cleanupConversations() {
  const now = Date.now();

  for (const [id, state] of conversations.entries()) {
    if (now - state.updatedAt > CONVERSATION_TTL_MS) {
      conversations.delete(id);
    }
  }

  while (conversations.size > MAX_CONVERSATIONS) {
    const first = conversations.keys().next().value;
    conversations.delete(first);
  }
}

function getConversation(conversationId) {
  if (!conversationId) {
    return null;
  }

  cleanupConversations();

  if (!conversations.has(conversationId)) {
    conversations.set(conversationId, {
      preferredProjectId: null,
      history: [],
      updatedAt: Date.now(),
    });
  }

  const state = conversations.get(conversationId);
  state.updatedAt = Date.now();
  return state;
}

function appendConversation(conversation, question, answer, recentMessages = []) {
  if (!conversation) {
    return;
  }

  const compactRecent = recentMessages
    .slice(-6)
    .map((item) => ({
      role: item.role === 'assistant' ? 'assistant' : 'user',
      text: String(item.text || '').slice(0, 240),
    }))
    .filter((item) => item.text);

  conversation.history = [
    ...conversation.history,
    ...compactRecent,
    { role: 'user', text: String(question || '').slice(0, 240) },
    { role: 'assistant', text: String(answer || '').slice(0, 300) },
  ].slice(-14);

  conversation.updatedAt = Date.now();
}

function safeToLower(value) {
  return String(value || '').toLowerCase();
}

function deriveScopeProjectId({ message, context, projects, conversation }) {
  const fromContext = Number(context?.selected_project_id);
  if (Number.isFinite(fromContext) && fromContext > 0) {
    return fromContext;
  }

  const projectIdMatch = String(message || '').match(/project\s*#?(\d+)/i);
  if (projectIdMatch) {
    return Number(projectIdMatch[1]);
  }

  const loweredMessage = safeToLower(message);
  const matchedProject = projects.find((project) => loweredMessage.includes(safeToLower(project.name)));
  if (matchedProject) {
    return Number(matchedProject.id);
  }

  if (conversation && Number.isFinite(Number(conversation.preferredProjectId))) {
    return Number(conversation.preferredProjectId);
  }

  return null;
}

function formatConversationContext(conversation, recentMessages) {
  const conversationHistory = conversation?.history || [];
  const recent = Array.isArray(recentMessages) ? recentMessages : [];

  return [...conversationHistory, ...recent]
    .slice(-10)
    .map((item) => `${item.role === 'assistant' ? 'assistant' : 'user'}: ${String(item.text || '').slice(0, 220)}`)
    .join('\n');
}

function formatUiContext(context, scopedProject) {
  return [
    `selected_project_id: ${context?.selected_project_id || 'none'}`,
    `selected_project_name: ${scopedProject?.name || 'all-projects'}`,
    `active_view: ${context?.active_view || 'n/a'}`,
    `visible_task_count: ${context?.visible_task_count ?? 'n/a'}`,
    `overdue_count: ${context?.overdue_count ?? 'n/a'}`,
  ].join('\n');
}

function buildVertexApiBase(region) {
  if (region === 'global') {
    return 'https://aiplatform.googleapis.com';
  }

  return `https://${region}-aiplatform.googleapis.com`;
}

function buildRagCorpusResourceName({ projectId, ragRegion, ragCorpusId }) {
  if (String(ragCorpusId).startsWith('projects/')) {
    return ragCorpusId;
  }

  return `projects/${projectId}/locations/${ragRegion}/ragCorpora/${ragCorpusId}`;
}

function buildRetrievalPrompt(question, scopedProjectId, context) {
  const lines = [`User question: ${question}`];

  if (Number.isFinite(Number(scopedProjectId)) && Number(scopedProjectId) > 0) {
    lines.push(`Focus project_id: ${Number(scopedProjectId)}`);
  }

  if (context?.active_view) {
    lines.push(`Active view: ${context.active_view}`);
  }

  return lines.join('\n');
}

async function retrieveContexts({ question, context, scopedProjectId, vertexConfig }) {
  const ragCorpusResource = buildRagCorpusResourceName(vertexConfig);
  const endpoint = `${buildVertexApiBase(vertexConfig.ragRegion)}/v1beta1/projects/${vertexConfig.projectId}/locations/${vertexConfig.ragRegion}:retrieveContexts`;

  const payload = {
    vertex_rag_store: {
      rag_resources: [{ rag_corpus: ragCorpusResource }],
    },
    query: {
      text: buildRetrievalPrompt(question, scopedProjectId, context),
      rag_retrieval_config: {
        top_k: vertexConfig.ragTopK,
      },
    },
  };

  const response = await vertexRequest({
    url: endpoint,
    body: payload,
  });

  const rawContexts = response?.contexts?.contexts || [];

  return rawContexts
    .map((item, index) => {
      const content = String(item.text || item.chunk?.text || '').trim();
      const source = item.source_uri || item.sourceUri || item.rag_file_uri || item.ragFileUri || null;
      const distance = item.distance ?? item.score ?? null;

      return {
        id: source || `context:${index + 1}`,
        content,
        source,
        distance,
      };
    })
    .filter((item) => item.content);
}

async function buildLiveSqlContext(scopedProjectId) {
  const [tasks, analytics] = await Promise.all([
    taskRepository.listTasks({ projectId: scopedProjectId || undefined }),
    taskRepository.getAnalyticsOverview({ projectId: scopedProjectId || undefined }),
  ]);

  const sampleTasks = tasks.slice(0, 12).map((task) => {
    return [
      `#${task.id}`,
      `${task.title}`,
      `(status=${task.status}, progress=${task.progress}%, project=${task.project_name || 'Unassigned'})`,
    ].join(' ');
  });

  return [
    `Live SQL snapshot at ${new Date().toISOString()}`,
    `Tasks in scope: ${tasks.length}`,
    `Done: ${analytics?.totals?.done ?? 0}`,
    `Blocked: ${analytics?.totals?.blocked ?? 0}`,
    `Overdue: ${analytics?.totals?.overdue ?? 0}`,
    sampleTasks.length ? `Sample tasks: ${sampleTasks.join(' | ')}` : 'Sample tasks: none',
  ].join('\n');
}
function buildGenerationPrompt({ question, retrievedDocs, conversationContext, uiContext, liveSqlContext }) {
  const retrievedContext = retrievedDocs
    .map((doc, index) => {
      const header = `[${index + 1}] ${doc.source || doc.id}`;
      return `${header}\n${doc.content}`;
    })
    .join('\n\n');

  return [
    'You are the Project Management Tool assistant.',
    'Answer using the live SQL context and retrieved RAG context below.',
    'If information is missing, say so clearly and suggest what to ask next.',
    'Keep responses concise and actionable.',
    '',
    'User question:',
    question,
    '',
    'UI context:',
    uiContext || 'none',
    '',
    'Conversation context:',
    conversationContext || 'none',
    '',
    'Live SQL context:',
    liveSqlContext || 'none',
    '',
    'Retrieved context:',
    retrievedContext || 'No retrieved context.',
  ].join('\n');
}

function extractGeneratedText(payload) {
  const candidates = Array.isArray(payload?.candidates) ? payload.candidates : [];
  if (!candidates.length) {
    return '';
  }

  const parts = Array.isArray(candidates[0]?.content?.parts) ? candidates[0].content.parts : [];
  return parts
    .map((part) => String(part?.text || '').trim())
    .filter(Boolean)
    .join('\n')
    .trim();
}

async function generateAnswer({ question, retrievedDocs, conversationContext, uiContext, liveSqlContext, vertexConfig }) {
  const endpoint = `${buildVertexApiBase(vertexConfig.geminiRegion)}/v1/projects/${vertexConfig.projectId}/locations/${vertexConfig.geminiRegion}/publishers/google/models/${encodeURIComponent(vertexConfig.geminiModel)}:generateContent`;

  const payload = {
    contents: [
      {
        role: 'user',
        parts: [
          {
            text: buildGenerationPrompt({
              question,
              retrievedDocs,
              conversationContext,
              uiContext,
              liveSqlContext,
            }),
          },
        ],
      },
    ],
    generationConfig: {
      temperature: vertexConfig.temperature,
      maxOutputTokens: vertexConfig.maxOutputTokens,
    },
  };

  const response = await vertexRequest({
    url: endpoint,
    body: payload,
  });

  return extractGeneratedText(response);
}

function mapError(error) {
  const message = String(error?.message || error || 'Unknown error');

  if (message.includes('aiplatform.ragCorpora.create') || message.includes('aiplatform.ragCorpora.get')) {
    return new Error('Vertex RAG permission missing. Grant roles/aiplatform.user to the runtime identity.');
  }

  if (message.includes('Missing required Vertex settings')) {
    return new Error(`${message}. Configure Cloud Run env vars before calling /api/chat.`);
  }

  if (message.includes('ragCorpora') && message.includes('not found')) {
    return new Error('Vertex RAG corpus not found. Check VERTEX_RAG_CORPUS_ID and region.');
  }

  if (message.includes('publishers/google/models') && message.includes('not found')) {
    return new Error('Gemini model not found for this location. Set GEMINI_MODEL and GEMINI_REGION to a supported combination.');
  }

  if (message.includes('PERMISSION_DENIED') || message.includes('403')) {
    return new Error('Vertex access denied. Check Cloud Run service account IAM and project/region settings.');
  }

  return error;
}

async function answerMessage(message, options = {}) {
  const question = String(message || '').trim();
  if (!question) {
    return {
      answer: 'Ask about project status, overdue tasks, blockers, completed work, or workload by assignee.',
      sources: [],
      cached: false,
    };
  }

  const conversationId = String(options.conversationId || '').trim();
  const context = options.context || {};
  const recentMessages = Array.isArray(options.recentMessages) ? options.recentMessages : [];

  const conversation = getConversation(conversationId);
  const vertexConfig = getVertexConfig();

  try {
    validateVertexConfig(vertexConfig);

    const projects = await projectRepository.listProjects();

    const scopedProjectId = deriveScopeProjectId({
      message: question,
      context,
      projects,
      conversation,
    });

    if (conversation && scopedProjectId) {
      conversation.preferredProjectId = scopedProjectId;
    }

    const scopedProject = Number.isFinite(Number(scopedProjectId))
      ? projects.find((project) => Number(project.id) === Number(scopedProjectId))
      : null;

    const retrievedDocs = await retrieveContexts({
      question,
      context,
      scopedProjectId,
      vertexConfig,
    });

    const conversationContext = formatConversationContext(conversation, recentMessages);
    const uiContext = formatUiContext(context, scopedProject);

    const liveSqlContext = await buildLiveSqlContext(scopedProjectId);

    const answer = await generateAnswer({
      question,
      retrievedDocs,
      conversationContext,
      uiContext,
      liveSqlContext,
      vertexConfig,
    });

    const finalAnswer = answer || 'I found related context but could not generate a confident answer. Please try a narrower question.';
    appendConversation(conversation, question, finalAnswer, recentMessages);

    const sources = [...new Set(retrievedDocs.map((doc) => doc.source || doc.id))];
    if (!sources.length) {
      sources.push('live-sql-context');
    }

    return {
      answer: finalAnswer,
      sources,
      cached: false,
    };
  } catch (error) {
    throw mapError(error);
  }
}

module.exports = {
  answerMessage,
};



