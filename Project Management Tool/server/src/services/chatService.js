const { ChatOllama, OllamaEmbeddings } = require('@langchain/ollama');
const { ChatPromptTemplate } = require('@langchain/core/prompts');
const { RunnableSequence } = require('@langchain/core/runnables');
const { StringOutputParser } = require('@langchain/core/output_parsers');
const taskRepository = require('../repositories/taskRepository');
const projectRepository = require('../repositories/projectRepository');

const INDEX_TTL_MS = 45 * 1000;
const CONVERSATION_TTL_MS = 45 * 60 * 1000;
const MAX_CONVERSATIONS = 300;
const TOP_K = 4;

const vectorIndexCache = {
  key: null,
  vectors: [],
  docs: [],
  updatedAt: 0,
};

const conversations = new Map();

let chatModel;
let embeddingModel;

function getChatModel() {
  if (!chatModel) {
    chatModel = new ChatOllama({
      baseUrl: process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434',
      model: process.env.OLLAMA_CHAT_MODEL || 'mistral:latest',
      temperature: Number(process.env.OLLAMA_TEMPERATURE || 0.15),
      numCtx: Number(process.env.OLLAMA_NUM_CTX || 2048),
      numPredict: Number(process.env.OLLAMA_NUM_PREDICT || 110),
      keepAlive: process.env.OLLAMA_KEEP_ALIVE || '10m',
    });
  }

  return chatModel;
}

function getEmbeddingModel() {
  if (!embeddingModel) {
    embeddingModel = new OllamaEmbeddings({
      baseUrl: process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434',
      model: process.env.OLLAMA_EMBED_MODEL || 'nomic-embed-text:latest',
    });
  }

  return embeddingModel;
}

function safeToLower(value) {
  return String(value || '').toLowerCase();
}

function tokenizeForLexical(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((token) => token.length >= 3);
}

function lexicalOverlapScore(question, content) {
  const questionTokens = tokenizeForLexical(question);
  if (!questionTokens.length) {
    return 0;
  }

  const contentTokenSet = new Set(tokenizeForLexical(content));
  if (!contentTokenSet.size) {
    return 0;
  }

  let overlap = 0;
  questionTokens.forEach((token) => {
    if (contentTokenSet.has(token)) {
      overlap += 1;
    }
  });

  return overlap / questionTokens.length;
}

function cosineSimilarity(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length || a.length === 0) {
    return 0;
  }

  let dot = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < a.length; i += 1) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }

  if (normA === 0 || normB === 0) {
    return 0;
  }

  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
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

function buildDocuments({ tasks, projects, overview, scopedProjectId }) {
  const scopedTasks = scopedProjectId
    ? tasks.filter((task) => Number(task.project_id) === Number(scopedProjectId))
    : tasks;

  const scopedProject = scopedProjectId
    ? projects.find((project) => Number(project.id) === Number(scopedProjectId))
    : null;

  const docs = [];

  scopedTasks.forEach((task) => {
    docs.push({
      id: `task:${task.id}`,
      text: [
        `Task #${task.id}`,
        `title: ${task.title}`,
        `description: ${task.description}`,
        `project: ${task.project_name || 'General'}`,
        `status: ${task.status}`,
        `is_completed: ${task.is_completed ? 'yes' : 'no'}`,
        `progress: ${task.progress}`,
        `priority: ${task.priority}`,
        `difficulty: ${task.difficulty_level}`,
        `assignee: ${task.assignee || 'unassigned'}`,
        `due_date: ${task.due_date}`,
        `updated_at: ${task.updated_at || ''}`,
      ].join(' | '),
      freshness: task.updated_at || task.due_date || '',
    });
  });

  const projectDocs = scopedProject ? [scopedProject] : projects;
  projectDocs.forEach((project) => {
    docs.push({
      id: `project:${project.id}`,
      text: [
        `Project #${project.id}`,
        `name: ${project.name}`,
        `description: ${project.description || 'n/a'}`,
        `created_at: ${project.created_at || ''}`,
      ].join(' | '),
      freshness: project.created_at || '',
    });
  });

  docs.push({
    id: 'analytics:overview',
    text: [
      `status_distribution: ${overview.status.map((row) => `${row.key_name}:${row.value_count}`).join(', ') || 'n/a'}`,
      `workload: ${overview.workload.map((row) => `${row.assignee}:${row.open_tasks}`).join(', ') || 'n/a'}`,
      `project_velocity: ${overview.projectVelocity.map((row) => `${row.project_name}:${row.completed}/${row.total}`).join(', ') || 'n/a'}`,
    ].join(' | '),
    freshness: new Date().toISOString(),
  });

  return { docs, scopedTasks, scopedProject };
}

function buildIndexKey(docs) {
  return docs
    .map((doc) => `${doc.id}:${doc.freshness}:${doc.text.length}`)
    .join('||');
}

async function ensureVectorIndex(docs) {
  const indexKey = buildIndexKey(docs);
  const isFresh = Date.now() - vectorIndexCache.updatedAt <= INDEX_TTL_MS;

  if (vectorIndexCache.key === indexKey && isFresh) {
    return {
      docs: vectorIndexCache.docs,
      vectors: vectorIndexCache.vectors,
      cached: true,
    };
  }

  const embeddings = getEmbeddingModel();
  const vectors = await embeddings.embedDocuments(docs.map((doc) => doc.text));

  vectorIndexCache.key = indexKey;
  vectorIndexCache.docs = docs;
  vectorIndexCache.vectors = vectors;
  vectorIndexCache.updatedAt = Date.now();

  return {
    docs,
    vectors,
    cached: false,
  };
}

async function retrieveRelevantDocs(question, indexedDocs) {
  const embeddings = getEmbeddingModel();
  const queryVector = await embeddings.embedQuery(question);

  const ranked = indexedDocs.docs
    .map((doc, index) => {
      const vectorScore = cosineSimilarity(queryVector, indexedDocs.vectors[index]);
      const lexicalScore = lexicalOverlapScore(question, doc.text);
      const score = vectorScore * 0.75 + lexicalScore * 0.25;

      return {
        ...doc,
        score,
        vectorScore,
        lexicalScore,
      };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, TOP_K)
    .filter((doc) => doc.score > 0.04 || doc.lexicalScore > 0);

  return ranked;
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

async function generateAnswer({ question, retrievedDocs, conversationContext, uiContext }) {
  const prompt = ChatPromptTemplate.fromMessages([
    [
      'system',
      [
        'You are the Project Management Tool assistant.',
        'Answer strictly using the retrieved database context.',
        'If the answer is not present in context, say that clearly and suggest a follow-up query.',
        'Be concise and practical. Prefer bullet-like short sentences.',
        'When tasks are mentioned, include task ids where possible.',
      ].join(' '),
    ],
    [
      'human',
      [
        'User question:',
        '{question}',
        '',
        'UI context:',
        '{uiContext}',
        '',
        'Conversation context:',
        '{conversationContext}',
        '',
        'Retrieved database context:',
        '{retrievedContext}',
      ].join('\n'),
    ],
  ]);

  const chain = RunnableSequence.from([
    prompt,
    getChatModel(),
    new StringOutputParser(),
  ]);

  const retrievedContext = retrievedDocs
    .map((doc, index) => `[${index + 1}] ${doc.id} :: ${doc.text}`)
    .join('\n');

  const response = await chain.invoke({
    question,
    uiContext,
    conversationContext: conversationContext || 'none',
    retrievedContext: retrievedContext || 'No context retrieved.',
  });

  return String(response || '').trim();
}

function mapError(error) {
  const message = String(error?.message || error || 'Unknown error');

  if (message.includes('ECONNREFUSED') || message.includes('fetch failed')) {
    return new Error('LangChain RAG requires Ollama running locally at http://127.0.0.1:11434. Start Ollama and retry.');
  }

  if (message.includes('model') && message.includes('not found')) {
    return new Error('Required Ollama model not found. Run: ollama pull mistral:latest and ollama pull nomic-embed-text:latest');
  }

  return error;
}

async function answerMessage(message, options = {}) {
  const question = String(message || '').trim();
  if (!question) {
    return {
      answer: 'Ask about project status, overdue work, completed tasks, blockers, or workload by assignee.',
      sources: [],
      cached: false,
    };
  }

  const conversationId = String(options.conversationId || '').trim();
  const context = options.context || {};
  const recentMessages = Array.isArray(options.recentMessages) ? options.recentMessages : [];

  const conversation = getConversation(conversationId);

  try {
    const [tasks, projects, overview] = await Promise.all([
      taskRepository.listTasks(),
      projectRepository.listProjects(),
      taskRepository.getAnalyticsOverview(),
    ]);

    const scopedProjectId = deriveScopeProjectId({
      message: question,
      context,
      projects,
      conversation,
    });

    if (conversation && scopedProjectId) {
      conversation.preferredProjectId = scopedProjectId;
    }

    const { docs, scopedTasks, scopedProject } = buildDocuments({
      tasks,
      projects,
      overview,
      scopedProjectId,
    });

    const index = await ensureVectorIndex(docs);
    const retrievedDocs = await retrieveRelevantDocs(question, index);

    const conversationContext = formatConversationContext(conversation, recentMessages);
    const uiContext = formatUiContext(context, scopedProject);

    const answer = await generateAnswer({
      question,
      retrievedDocs,
      conversationContext,
      uiContext,
    });

    appendConversation(conversation, question, answer, recentMessages);

    const sources = retrievedDocs.map((doc) => doc.id);

    if (!answer) {
      return {
        answer: `I could not derive a confident answer from current database context (${scopedTasks.length} tasks in scope). Try narrowing your question.`,
        sources,
        cached: index.cached,
      };
    }

    return {
      answer,
      sources,
      cached: index.cached,
    };
  } catch (error) {
    throw mapError(error);
  }
}

module.exports = {
  answerMessage,
};


