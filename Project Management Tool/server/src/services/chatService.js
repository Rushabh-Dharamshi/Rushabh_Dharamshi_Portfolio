const { GoogleAuth } = require('google-auth-library');
const projectRepository = require('../repositories/projectRepository');
const taskRepository = require('../repositories/taskRepository');
const { scoreTasks } = require('./riskScoringService');

const CONVERSATION_TTL_MS = 45 * 60 * 1000;
const MAX_CONVERSATIONS = 300;

const conversations = new Map();
const auth = new GoogleAuth({
  scopes: ['https://www.googleapis.com/auth/cloud-platform'],
});

let authClientPromise;
let ragRefreshQueue = Promise.resolve();

function getVertexConfig() {
  const ragRegion = process.env.GCP_REGION || 'europe-west2';
  const geminiModel = process.env.GEMINI_MODEL || 'gemini-3.1-pro-preview';

  return {
    projectId: process.env.GCP_PROJECT_ID || process.env.GOOGLE_CLOUD_PROJECT || process.env.GCLOUD_PROJECT,
    ragRegion,
    geminiRegion: process.env.GEMINI_REGION || (geminiModel.indexOf('gemini-3') === 0 ? 'global' : ragRegion),
    ragCorpusId: process.env.VERTEX_RAG_CORPUS_ID,
    ragGcsPrefix: process.env.RAG_GCS_URI_PREFIX,
    geminiModel,
    ragTopK: Number(process.env.RAG_TOP_K || 4),
    ragChunkSize: Number(process.env.RAG_CHUNK_SIZE || 512),
    ragChunkOverlap: Number(process.env.RAG_CHUNK_OVERLAP || 100),
    ragRefreshTimeoutMs: Number(process.env.RAG_REFRESH_TIMEOUT_MS || 180000),
    temperature: Number(process.env.GEMINI_TEMPERATURE || 0.15),
    maxOutputTokens: Number(process.env.GEMINI_MAX_OUTPUT_TOKENS || 2048),
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

  if (!config.ragGcsPrefix) {
    missing.push('RAG_GCS_URI_PREFIX');
  }

  if (missing.length > 0) {
    throw new Error('Missing required Vertex settings: ' + missing.join(', '));
  }
}

async function getAuthClient() {
  if (!authClientPromise) {
    authClientPromise = auth.getClient();
  }

  return authClientPromise;
}

async function authenticatedJsonRequest(options) {
  const client = await getAuthClient();
  const headers = await client.getRequestHeaders(options.url);
  headers['Content-Type'] = 'application/json';

  const response = await fetch(options.url, {
    method: options.method || 'POST',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
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
    throw new Error('API ' + response.status + ': ' + (responseText || response.statusText));
  }

  return payload;
}

async function authenticatedTextUpload(url, textBody) {
  const client = await getAuthClient();
  const headers = await client.getRequestHeaders(url);
  headers['Content-Type'] = 'text/plain; charset=utf-8';

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: textBody,
  });

  const responseText = await response.text();
  if (!response.ok) {
    throw new Error('API ' + response.status + ': ' + (responseText || response.statusText));
  }
}

async function vertexRequest(args) {
  return authenticatedJsonRequest({
    url: args.url,
    method: 'POST',
    body: args.body,
  });
}

function cleanupConversations() {
  const now = Date.now();

  for (const entry of conversations.entries()) {
    const id = entry[0];
    const state = entry[1];
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

function appendConversation(conversation, question, answer, recentMessages) {
  if (!conversation) {
    return;
  }

  const compactRecent = (recentMessages || [])
    .slice(-6)
    .map(function mapRecent(item) {
      return {
        role: item.role === 'assistant' ? 'assistant' : 'user',
        text: String(item.text || '').slice(0, 240),
      };
    })
    .filter(function onlyText(item) {
      return item.text;
    });

  conversation.history = conversation.history
    .concat(compactRecent)
    .concat([
      { role: 'user', text: String(question || '').slice(0, 240) },
      { role: 'assistant', text: String(answer || '').slice(0, 300) },
    ])
    .slice(-14);

  conversation.updatedAt = Date.now();
}

function safeToLower(value) {
  return String(value || '').toLowerCase();
}

function detectStatusIntent(question) {
  const text = safeToLower(question);
  const mapping = [
    { aliases: ['in progress', 'in_progress', 'in-progress', 'ongoing'], status: 'in_progress', label: 'in progress' },
    { aliases: ['blocked', 'stuck'], status: 'blocked', label: 'blocked' },
    { aliases: ['done', 'completed', 'complete', 'finished'], status: 'done', label: 'done' },
    { aliases: ['backlog', 'todo', 'to do'], status: 'backlog', label: 'in backlog' },
  ];

  return mapping.find(function findIntent(item) {
    return item.aliases.some(function hasAlias(alias) {
      return text.indexOf(alias) >= 0;
    });
  }) || null;
}

function shouldEnumerateTasks(question) {
  const text = safeToLower(question);
  const intentHints = ['what', 'which', 'list', 'show', 'name', 'names'];
  const taskHints = ['task', 'tasks', 'work item', 'work items'];

  return intentHints.some(function hasIntent(hint) {
    return text.indexOf(hint) >= 0;
  }) && taskHints.some(function hasTaskHint(hint) {
    return text.indexOf(hint) >= 0;
  });
}

async function buildExactStatusAnswer(question, scopedProjectId) {
  const statusIntent = detectStatusIntent(question);
  if (!statusIntent || !shouldEnumerateTasks(question)) {
    return null;
  }

  const tasks = await taskRepository.listTasks({ projectId: scopedProjectId || undefined });
  const matching = tasks.filter(function sameStatus(task) {
    return String(task.status) === statusIntent.status;
  });

  const scopeLabel = scopedProjectId ? 'for the selected project' : 'across all projects';

  if (!matching.length) {
    return 'There are no tasks currently ' + statusIntent.label + ' ' + scopeLabel + '.';
  }

  const header = 'There ' + (matching.length === 1 ? 'is' : 'are') + ' ' + matching.length + ' task' + (matching.length === 1 ? '' : 's') + ' currently ' + statusIntent.label + ' ' + scopeLabel + '. Their names are:';
  const lines = matching.map(function formatTask(task, index) {
    return String(index + 1) + '. ' + task.title;
  });

  return [header].concat(lines).join('\n');
}

function deriveScopeProjectId(args) {
  const fromContext = Number(args.context && args.context.selected_project_id);
  if (Number.isFinite(fromContext) && fromContext > 0) {
    return fromContext;
  }

  const projectIdMatch = String(args.message || '').match(/project\s*#?(\d+)/i);
  if (projectIdMatch) {
    return Number(projectIdMatch[1]);
  }

  const loweredMessage = safeToLower(args.message);
  const matchedProject = (args.projects || []).find(function matchProject(project) {
    return loweredMessage.indexOf(safeToLower(project.name)) >= 0;
  });

  if (matchedProject) {
    return Number(matchedProject.id);
  }

  if (args.conversation && Number.isFinite(Number(args.conversation.preferredProjectId))) {
    return Number(args.conversation.preferredProjectId);
  }

  return null;
}

function formatConversationContext(conversation, recentMessages) {
  const conversationHistory = (conversation && conversation.history) || [];
  const recent = Array.isArray(recentMessages) ? recentMessages : [];

  return conversationHistory
    .concat(recent)
    .slice(-10)
    .map(function render(item) {
      return (item.role === 'assistant' ? 'assistant' : 'user') + ': ' + String(item.text || '').slice(0, 220);
    })
    .join('\n');
}

function formatUiContext(context, scopedProject) {
  return [
    'selected_project_id: ' + ((context && context.selected_project_id) || 'none'),
    'selected_project_name: ' + ((scopedProject && scopedProject.name) || 'all-projects'),
    'active_view: ' + ((context && context.active_view) || 'n/a'),
    'visible_task_count: ' + ((context && context.visible_task_count) ?? 'n/a'),
    'overdue_count: ' + ((context && context.overdue_count) ?? 'n/a'),
  ].join('\n');
}

function buildVertexApiBase(region) {
  if (region === 'global') {
    return 'https://aiplatform.googleapis.com';
  }

  return 'https://' + region + '-aiplatform.googleapis.com';
}

function buildRagCorpusResourceName(config) {
  if (String(config.ragCorpusId).indexOf('projects/') === 0) {
    return config.ragCorpusId;
  }

  return 'projects/' + config.projectId + '/locations/' + config.ragRegion + '/ragCorpora/' + config.ragCorpusId;
}

function buildRetrievalPrompt(question, scopedProjectId, context, conversationContext) {
  const lines = ['User question: ' + question];

  if (Number.isFinite(Number(scopedProjectId)) && Number(scopedProjectId) > 0) {
    lines.push('Focus project_id: ' + Number(scopedProjectId));
  }

  if (context && context.active_view) {
    lines.push('Active view: ' + context.active_view);
  }

  return lines.join('\n');
}

function parseGcsPrefix(gcsPrefix) {
  const trimmed = String(gcsPrefix || '').trim();
  if (trimmed.indexOf('gs://') !== 0) {
    throw new Error('RAG_GCS_URI_PREFIX must start with gs://');
  }

  const noScheme = trimmed.slice(5).replace(/\/$/, '');
  const firstSlash = noScheme.indexOf('/');

  if (firstSlash === -1) {
    return { bucket: noScheme, prefix: '' };
  }

  return {
    bucket: noScheme.slice(0, firstSlash),
    prefix: noScheme.slice(firstSlash + 1),
  };
}

function toIsoSafe(value) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function resolveRiskScore(task) {
  const direct = Number(task && task.risk_score);
  if (Number.isFinite(direct)) {
    return direct.toFixed(2);
  }

  const fromMl = Number(task && task.ml_risk && task.ml_risk.score);
  if (Number.isFinite(fromMl)) {
    return fromMl.toFixed(2);
  }

  return 'n/a';
}

function resolveRiskLevel(task) {
  const direct = String((task && task.risk_level) || '').toLowerCase();
  if (direct) {
    return direct;
  }

  const fromMl = String((task && task.ml_risk && task.ml_risk.label) || '').toLowerCase();
  if (fromMl) {
    return fromMl;
  }

  return 'n/a';
}

function buildTaskRagDocs(tasks) {
  return tasks.map(function mapTask(task) {
    return {
      objectPath: 'task_docs/task-' + task.id + '.txt',
      content: [
        'Task #' + task.id,
        'Project: ' + (task.project_name || 'Unassigned') + ' (project_id=' + (task.project_id || 'none') + ')',
        'Title: ' + task.title,
        'Description: ' + task.description,
        'Status: ' + task.status,
        'Progress: ' + task.progress + '%',
        'Priority: ' + task.priority,
        'Difficulty: ' + task.difficulty_level,
        'Assignee: ' + (task.assignee || 'Unassigned'),
        'Category: ' + (task.category || 'Unspecified'),
        'Estimated Hours: ' + (task.estimated_hours ?? 'n/a'),
        'Risk Score: ' + resolveRiskScore(task),
        'Risk Level: ' + resolveRiskLevel(task),
        'Due Date: ' + task.due_date,
        'Completed: ' + (task.is_completed ? 'yes' : 'no'),
        'Created At: ' + (toIsoSafe(task.created_at) || task.created_at),
        'Updated At: ' + (toIsoSafe(task.updated_at) || task.updated_at),
      ].join('\n'),
    };
  });
}

function buildProjectRagDocs(projects, tasks) {
  const statsByProject = new Map();

  tasks.forEach(function eachTask(task) {
    const projectId = Number(task.project_id);
    if (!Number.isFinite(projectId) || projectId <= 0) {
      return;
    }

    if (!statsByProject.has(projectId)) {
      statsByProject.set(projectId, {
        total: 0,
        backlog: 0,
        in_progress: 0,
        blocked: 0,
        done: 0,
        progressSum: 0,
      });
    }

    const stats = statsByProject.get(projectId);
    stats.total += 1;
    stats.progressSum += Number(task.progress || 0);
    const statusKey = String(task.status || 'backlog');
    if (Object.prototype.hasOwnProperty.call(stats, statusKey)) {
      stats[statusKey] += 1;
    }
  });

  return projects.map(function mapProject(project) {
    const stats = statsByProject.get(Number(project.id)) || {
      total: 0,
      backlog: 0,
      in_progress: 0,
      blocked: 0,
      done: 0,
      progressSum: 0,
    };

    const avgProgress = stats.total ? (stats.progressSum / stats.total).toFixed(2) : '0.00';

    return {
      objectPath: 'project_docs/project-' + project.id + '.txt',
      content: [
        'Project #' + project.id,
        'Name: ' + project.name,
        'Description: ' + (project.description || 'n/a'),
        'Total Tasks: ' + stats.total,
        'Backlog: ' + stats.backlog,
        'In Progress: ' + stats.in_progress,
        'Blocked: ' + stats.blocked,
        'Done: ' + stats.done,
        'Average Progress: ' + avgProgress + '%',
        'Created At: ' + (toIsoSafe(project.created_at) || project.created_at),
      ].join('\n'),
    };
  });
}

function buildSummaryRagDoc(tasks) {
  const done = tasks.filter(function isDone(task) { return task.status === 'done'; }).length;
  const blocked = tasks.filter(function isBlocked(task) { return task.status === 'blocked'; }).length;
  const overdue = tasks.filter(function isOverdue(task) {
    if (!task.due_date || task.status === 'done') {
      return false;
    }

    const dueDate = new Date(task.due_date);
    const today = new Date();
    dueDate.setHours(0, 0, 0, 0);
    today.setHours(0, 0, 0, 0);
    return dueDate < today;
  }).length;

  return {
    objectPath: 'summary_docs/portfolio-summary.txt',
    content: [
      'Portfolio Summary',
      'Total tasks: ' + tasks.length,
      'Done tasks: ' + done,
      'Blocked tasks: ' + blocked,
      'Overdue tasks: ' + overdue,
      'Generated at: ' + new Date().toISOString(),
    ].join('\n'),
  };
}

async function buildRagDocsFromSql() {
  const rows = await Promise.all([
    taskRepository.listTasks(),
    projectRepository.listProjects(),
  ]);

  const tasks = rows[0];
  const projects = rows[1];
  const scoredTasks = tasks.length ? await scoreTasks(tasks, { persist: true }) : tasks;

  return buildTaskRagDocs(scoredTasks)
    .concat(buildProjectRagDocs(projects, scoredTasks))
    .concat([buildSummaryRagDoc(scoredTasks)]);
}

async function listGcsObjects(bucket, prefix) {
  const items = [];
  let pageToken = '';

  do {
    const params = new URLSearchParams();
    params.set('prefix', prefix ? prefix + '/' : '');
    params.set('maxResults', '1000');
    if (pageToken) {
      params.set('pageToken', pageToken);
    }

    const url = 'https://storage.googleapis.com/storage/v1/b/' + encodeURIComponent(bucket) + '/o?' + params.toString();
    const payload = await authenticatedJsonRequest({ url: url, method: 'GET' });

    (payload.items || []).forEach(function eachItem(item) {
      if (item && item.name) {
        items.push(item.name);
      }
    });

    pageToken = payload.nextPageToken || '';
  } while (pageToken);

  return items;
}

async function clearGcsPrefix(bucket, prefix) {
  const objectNames = await listGcsObjects(bucket, prefix);

  for (const objectName of objectNames) {
    const deleteUrl = 'https://storage.googleapis.com/storage/v1/b/' + encodeURIComponent(bucket) + '/o/' + encodeURIComponent(objectName);
    await authenticatedJsonRequest({ url: deleteUrl, method: 'DELETE' });
  }
}

async function uploadDocToGcs(bucket, prefix, doc) {
  const objectName = prefix ? prefix + '/' + doc.objectPath : doc.objectPath;
  const uploadUrl = 'https://storage.googleapis.com/upload/storage/v1/b/' + encodeURIComponent(bucket) + '/o?uploadType=media&name=' + encodeURIComponent(objectName);
  await authenticatedTextUpload(uploadUrl, doc.content);
}

async function waitForVertexOperation(config, operationName) {
  const operationPath = operationName.indexOf('projects/') === 0
    ? operationName
    : ('projects/' + config.projectId + '/locations/' + config.ragRegion + '/operations/' + operationName);

  const deadline = Date.now() + Math.max(config.ragRefreshTimeoutMs, 15000);

  while (Date.now() < deadline) {
    const opUrl = buildVertexApiBase(config.ragRegion) + '/v1beta1/' + operationPath;
    const payload = await authenticatedJsonRequest({ url: opUrl, method: 'GET' });

    if (payload.done === true) {
      if (payload.error) {
        throw new Error('Vertex operation failed: ' + JSON.stringify(payload.error));
      }

      return;
    }

    await new Promise(function pause(resolve) { setTimeout(resolve, 2000); });
  }

  throw new Error('Timed out waiting for Vertex RAG refresh operation to complete');
}

async function listVertexRagFiles(config) {
  const files = [];
  let pageToken = '';

  do {
    const tokenPart = pageToken ? ('&pageToken=' + encodeURIComponent(pageToken)) : '';
    const url = buildVertexApiBase(config.ragRegion) + '/v1beta1/projects/' + config.projectId + '/locations/' + config.ragRegion + '/ragCorpora/' + config.ragCorpusId + '/ragFiles?pageSize=100' + tokenPart;
    const payload = await authenticatedJsonRequest({ url: url, method: 'GET' });

    (payload.ragFiles || []).forEach(function eachFile(item) {
      if (item && item.name) {
        files.push(item.name);
      }
    });

    pageToken = payload.nextPageToken || '';
  } while (pageToken);

  return files;
}

async function clearVertexRagFiles(config) {
  const files = await listVertexRagFiles(config);

  for (const fileName of files) {
    const url = buildVertexApiBase(config.ragRegion) + '/v1beta1/' + fileName;
    const payload = await authenticatedJsonRequest({ url: url, method: 'DELETE' });
    if (payload && payload.name) {
      await waitForVertexOperation(config, payload.name);
    }
  }
}

async function importVertexRagFiles(config, uris) {
  const url = buildVertexApiBase(config.ragRegion) + '/v1beta1/projects/' + config.projectId + '/locations/' + config.ragRegion + '/ragCorpora/' + config.ragCorpusId + '/ragFiles:import';
  const payload = await authenticatedJsonRequest({
    url: url,
    method: 'POST',
    body: {
      import_rag_files_config: {
        gcs_source: { uris: uris },
        rag_file_chunking_config: {
          chunk_size: config.ragChunkSize,
          chunk_overlap: config.ragChunkOverlap,
        },
      },
    },
  });

  if (!payload || !payload.name) {
    throw new Error('Vertex import did not return an operation name');
  }

  await waitForVertexOperation(config, payload.name);
}

async function runRagRefreshWorkflow(config) {
  const docs = await buildRagDocsFromSql();
  const gcs = parseGcsPrefix(config.ragGcsPrefix);

  await clearGcsPrefix(gcs.bucket, gcs.prefix);

  for (const doc of docs) {
    await uploadDocToGcs(gcs.bucket, gcs.prefix, doc);
  }

  await clearVertexRagFiles(config);

  const prefixPart = gcs.prefix ? gcs.prefix + '/' : '';
  const taskUri = 'gs://' + gcs.bucket + '/' + prefixPart + 'task_docs/';
  const projectUri = 'gs://' + gcs.bucket + '/' + prefixPart + 'project_docs/';
  const summaryUri = 'gs://' + gcs.bucket + '/' + prefixPart + 'summary_docs/';

  await importVertexRagFiles(config, [taskUri, projectUri, summaryUri]);
}

async function refreshRagCorpusFromSql(config) {
  const queued = ragRefreshQueue
    .catch(function ignore() { return undefined; })
    .then(function run() { return runRagRefreshWorkflow(config); });

  ragRefreshQueue = queued;
  return queued;
}

async function retrieveContexts(args) {
  const ragCorpusResource = buildRagCorpusResourceName(args.vertexConfig);
  const endpoint = buildVertexApiBase(args.vertexConfig.ragRegion) + '/v1beta1/projects/' + args.vertexConfig.projectId + '/locations/' + args.vertexConfig.ragRegion + ':retrieveContexts';

  const payload = {
    vertex_rag_store: {
      rag_resources: [{ rag_corpus: ragCorpusResource }],
    },
    query: {
      text: buildRetrievalPrompt(args.question, args.scopedProjectId, args.context, args.conversationContext),
      rag_retrieval_config: {
        top_k: args.vertexConfig.ragTopK,
      },
    },
  };

  const response = await vertexRequest({
    url: endpoint,
    body: payload,
  });

  return (response && response.contexts && response.contexts.contexts ? response.contexts.contexts : [])
    .map(function mapItem(item, index) {
      const content = String(item.text || (item.chunk && item.chunk.text) || '').trim();
      return {
        id: 'context:' + String(index + 1),
        content: content,
      };
    })
    .filter(function hasContent(item) {
      return item.content;
    });
}

async function buildLiveSqlContext(scopedProjectId) {
  const rows = await Promise.all([
    taskRepository.listTasks({ projectId: scopedProjectId || undefined }),
    taskRepository.getAnalyticsOverview({ projectId: scopedProjectId || undefined }),
  ]);

  const tasks = rows[0];
  const analytics = rows[1];

  const sampleTasks = tasks.slice(0, 12).map(function mapTask(task) {
    return '#' + task.id + ' ' + task.title + ' (status=' + task.status + ', progress=' + task.progress + '%, project=' + (task.project_name || 'Unassigned') + ')';
  });

  return [
    'Live SQL snapshot at ' + new Date().toISOString(),
    'Tasks in scope: ' + tasks.length,
    'Done: ' + (analytics && analytics.totals ? analytics.totals.done : 0),
    'Blocked: ' + (analytics && analytics.totals ? analytics.totals.blocked : 0),
    'Overdue: ' + (analytics && analytics.totals ? analytics.totals.overdue : 0),
    sampleTasks.length ? ('Sample tasks: ' + sampleTasks.join(' | ')) : 'Sample tasks: none',
  ].join('\n');
}

function buildGenerationPrompt(args) {
  const retrievedContext = args.retrievedDocs
    .map(function mapDoc(doc, index) {
      const header = '[Context ' + String(index + 1) + ']';
      return header + '\n' + doc.content;
    })
    .join('\n\n');

  return [
    'You are the Project Management Tool assistant.',
    'Answer using only the live SQL context and retrieved RAG context below.',
    'If information is missing, say so clearly and suggest what to ask next.',
    'Keep responses concise and actionable.',
    'Do not end mid-sentence. Ensure your final sentence is complete.',
    'Do not include source URIs, latency, mode labels, or internal metadata unless explicitly asked.',
    '',
    'User question:',
    args.question,
    '',
    'UI context:',
    args.uiContext || 'none',
    '',
    'Conversation context:',
    args.conversationContext || 'none',
    '',
    'Live SQL context:',
    args.liveSqlContext || 'none',
    '',
    'Retrieved context:',
    retrievedContext || 'No retrieved context.',
  ].join('\n');
}

function extractGeneratedText(payload) {
  const candidates = Array.isArray(payload && payload.candidates) ? payload.candidates : [];
  if (!candidates.length) {
    return '';
  }

  const parts = Array.isArray(candidates[0] && candidates[0].content && candidates[0].content.parts) ? candidates[0].content.parts : [];
  return parts
    .map(function mapPart(part) { return String((part && part.text) || '').trim(); })
    .filter(Boolean)
    .join('\n')
    .trim();
}

function extractFinishReason(payload) {
  const candidates = Array.isArray(payload && payload.candidates) ? payload.candidates : [];
  if (!candidates.length) {
    return '';
  }

  return String(candidates[0].finishReason || '').toUpperCase();
}

function hasCompleteSentenceEnding(text) {
  return /[.!?]["')\]]?\s*$/.test(String(text || '').trim());
}

function buildContinuationPrompt(question, partialAnswer) {
  return [
    'Continue the assistant response below.',
    'Finish the current sentence and end with a complete sentence.',
    'Do not repeat earlier text.',
    '',
    'Original question:',
    question,
    '',
    'Current partial response:',
    partialAnswer,
  ].join('\n');
}

async function generateModelResponse(endpoint, promptText, vertexConfig, maxOutputTokensOverride) {
  const payload = {
    contents: [
      {
        role: 'user',
        parts: [
          {
            text: promptText,
          },
        ],
      },
    ],
    generationConfig: {
      temperature: vertexConfig.temperature,
      maxOutputTokens: maxOutputTokensOverride || vertexConfig.maxOutputTokens,
    },
  };

  const response = await vertexRequest({
    url: endpoint,
    body: payload,
  });

  return {
    text: extractGeneratedText(response),
    finishReason: extractFinishReason(response),
  };
}

async function generateAnswer(args) {
  const endpoint = buildVertexApiBase(args.vertexConfig.geminiRegion)
    + '/v1/projects/' + args.vertexConfig.projectId
    + '/locations/' + args.vertexConfig.geminiRegion
    + '/publishers/google/models/' + encodeURIComponent(args.vertexConfig.geminiModel)
    + ':generateContent';

  const primary = await generateModelResponse(
    endpoint,
    buildGenerationPrompt({
      question: args.question,
      retrievedDocs: args.retrievedDocs,
      conversationContext: args.conversationContext,
      uiContext: args.uiContext,
      liveSqlContext: args.liveSqlContext,
    }),
    args.vertexConfig
  );

  let answer = String(primary.text || '').trim();
  const endedByTokenLimit = primary.finishReason.indexOf('MAX') >= 0;

  if (answer && (endedByTokenLimit || !hasCompleteSentenceEnding(answer))) {
    const continuation = await generateModelResponse(
      endpoint,
      buildContinuationPrompt(args.question, answer),
      args.vertexConfig,
      256
    );

    const continuationText = String(continuation.text || '').trim();
    if (continuationText) {
      answer = (answer + ' ' + continuationText).trim();
    }
  }

  return answer;
}

function mapError(error) {
  const message = String((error && error.message) || error || 'Unknown error');

  if (message.indexOf('Missing required Vertex settings') >= 0) {
    return new Error(message + '. Configure Cloud Run env vars before calling /api/chat.');
  }

  if (message.indexOf('RAG_GCS_URI_PREFIX') >= 0) {
    return new Error('RAG_GCS_URI_PREFIX is missing or invalid. Set it to your RAG bucket prefix.');
  }

  if (message.indexOf('ragCorpora') >= 0 && message.indexOf('not found') >= 0) {
    return new Error('Vertex RAG corpus not found. Check VERTEX_RAG_CORPUS_ID and region.');
  }

  if (message.indexOf('publishers/google/models') >= 0 && message.indexOf('not found') >= 0) {
    return new Error('Gemini model not found for this location. Set GEMINI_MODEL and GEMINI_REGION to a supported combination.');
  }

  if (message.indexOf('PERMISSION_DENIED') >= 0 || message.indexOf('403') >= 0) {
    return new Error('Vertex or GCS access denied. Check Cloud Run service account IAM permissions.');
  }

  return error;
}

async function answerMessage(message, options) {
  const question = String(message || '').trim();
  if (!question) {
    return {
      answer: 'Ask about project status, overdue tasks, blockers, completed work, or workload by assignee.',
      sources: [],
      cached: false,
    };
  }

  const safeOptions = options || {};
  const conversationId = String(safeOptions.conversationId || '').trim();
  const context = safeOptions.context || {};
  const recentMessages = Array.isArray(safeOptions.recentMessages) ? safeOptions.recentMessages : [];

  const conversation = getConversation(conversationId);
  const vertexConfig = getVertexConfig();

  try {
    validateVertexConfig(vertexConfig);

    const projects = await projectRepository.listProjects();

    const scopedProjectId = deriveScopeProjectId({
      message: question,
      context: context,
      projects: projects,
      conversation: conversation,
    });

    if (conversation && scopedProjectId) {
      conversation.preferredProjectId = scopedProjectId;
    }

    const scopedProject = Number.isFinite(Number(scopedProjectId))
      ? projects.find(function findProject(project) { return Number(project.id) === Number(scopedProjectId); })
      : null;

    await refreshRagCorpusFromSql(vertexConfig);


    const conversationContext = formatConversationContext(conversation, recentMessages);

    const retrievedDocs = await retrieveContexts({
      question: question,
      context: context,
      scopedProjectId: scopedProjectId,
      conversationContext: conversationContext,
      vertexConfig: vertexConfig,
    });

    const uiContext = formatUiContext(context, scopedProject);
    const liveSqlContext = await buildLiveSqlContext(scopedProjectId);

    const answer = await generateAnswer({
      question: question,
      retrievedDocs: retrievedDocs,
      conversationContext: conversationContext,
      uiContext: uiContext,
      liveSqlContext: liveSqlContext,
      vertexConfig: vertexConfig,
    });

    const finalAnswer = answer || 'I found related context but could not generate a confident answer. Please try a narrower question.';
    appendConversation(conversation, question, finalAnswer, recentMessages);

    return {
      answer: finalAnswer,
      sources: [],
      cached: false,
    };
  } catch (error) {
    throw mapError(error);
  }
}

module.exports = {
  answerMessage,
};

