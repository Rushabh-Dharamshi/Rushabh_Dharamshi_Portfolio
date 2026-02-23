'use strict';

const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const { execFile } = require('child_process');

const execFileAsync = promisify(execFile);
const isWindows = process.platform === 'win32';

function getArgValue(flagName) {
  const index = process.argv.indexOf(flagName);
  if (index === -1) {
    return undefined;
  }

  return process.argv[index + 1];
}

function hasFlag(flagName) {
  return process.argv.includes(flagName);
}

function normalizeGsUri(uri) {
  if (!uri || !uri.startsWith('gs://')) {
    throw new Error('RAG_GCS_URI_PREFIX (or --gcs-prefix) must start with gs://');
  }

  return uri.endsWith('/') ? uri.slice(0, -1) : uri;
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function runCommand(command, args, options = {}) {
  const cmd = isWindows ? 'cmd.exe' : command;
  const cmdArgs = isWindows ? ['/d', '/s', '/c', command, ...args] : args;

  const { stdout, stderr } = await execFileAsync(cmd, cmdArgs, {
    windowsHide: true,
    maxBuffer: 1024 * 1024 * 10,
    ...options,
  });

  return { stdout: String(stdout || ''), stderr: String(stderr || '') };
}

function assertPathExists(targetPath, label) {
  if (!fs.existsSync(targetPath)) {
    throw new Error(`${label} not found: ${targetPath}`);
  }
}

async function getAccessToken() {
  const { stdout } = await runCommand('gcloud', ['auth', 'print-access-token']);
  const token = stdout.trim();
  if (!token) {
    throw new Error('Could not obtain access token from gcloud. Run: gcloud auth login');
  }
  return token;
}

async function uploadToGcs(localExportDir, gcsPrefix) {
  console.log(`Syncing export artifacts to ${gcsPrefix} ...`);

  await runCommand('gcloud', [
    'storage',
    'rsync',
    '--recursive',
    '--delete-unmatched-destination-objects',
    localExportDir,
    gcsPrefix,
  ]);

  return {
    taskDocsUri: `${gcsPrefix}/task_docs/`,
    projectDocsUri: `${gcsPrefix}/project_docs/`,
    summaryDocsUri: `${gcsPrefix}/summary_docs/`,
  };
}
async function vertexApiRequest({ endpoint, token, method = 'GET', body }) {
  const response = await fetch(endpoint, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const responseText = await response.text();
  const payload = responseText ? JSON.parse(responseText) : {};

  if (!response.ok) {
    throw new Error(`Vertex API ${response.status}: ${JSON.stringify(payload)}`);
  }

  return payload;
}

async function listRagFiles({ projectId, region, ragCorpusId, token }) {
  let pageToken = '';
  const ragFiles = [];

  do {
    const pageTokenQuery = pageToken ? `&pageToken=${encodeURIComponent(pageToken)}` : '';
    const endpoint = `https://${region}-aiplatform.googleapis.com/v1beta1/projects/${projectId}/locations/${region}/ragCorpora/${ragCorpusId}/ragFiles?pageSize=100${pageTokenQuery}`;
    const payload = await vertexApiRequest({ endpoint, token });

    if (Array.isArray(payload.ragFiles)) {
      ragFiles.push(...payload.ragFiles);
    }

    pageToken = payload.nextPageToken || '';
  } while (pageToken);

  return ragFiles;
}

async function clearCorpusRagFiles({ projectId, region, ragCorpusId, token }) {
  const existing = await listRagFiles({ projectId, region, ragCorpusId, token });

  if (!existing.length) {
    console.log('No existing RAG files to clear.');
    return;
  }

  console.log(`Clearing ${existing.length} existing RAG files from corpus before import...`);

  for (const ragFile of existing) {
    if (!ragFile.name) {
      continue;
    }

    const endpoint = `https://${region}-aiplatform.googleapis.com/v1beta1/${ragFile.name}`;
    const response = await vertexApiRequest({ endpoint, token, method: 'DELETE' });

    if (response.name) {
      await waitForOperation({
        projectId,
        region,
        operationName: response.name,
        token,
      });
    }
  }

  console.log('Existing corpus documents cleared.');
}

async function startImport({ projectId, region, ragCorpusId, uris, chunkSize, chunkOverlap, token }) {
  const endpoint = `https://${region}-aiplatform.googleapis.com/v1beta1/projects/${projectId}/locations/${region}/ragCorpora/${ragCorpusId}/ragFiles:import`;

  const payload = {
    import_rag_files_config: {
      gcs_source: {
        uris,
      },
      rag_file_chunking_config: {
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      },
    },
  };

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(`Vertex import request failed (${response.status}): ${JSON.stringify(body)}`);
  }

  if (!body.name) {
    throw new Error(`Vertex import response missing operation name: ${JSON.stringify(body)}`);
  }

  return body.name;
}

async function waitForOperation({ projectId, region, operationName, token, timeoutMs = 15 * 60 * 1000 }) {
  const start = Date.now();
  const operationPath = operationName.startsWith('projects/')
    ? operationName
    : `projects/${projectId}/locations/${region}/operations/${operationName}`;

  const endpoint = `https://${region}-aiplatform.googleapis.com/v1beta1/${operationPath}`;

  for (;;) {
    const response = await fetch(endpoint, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const body = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(`Failed to poll operation (${response.status}): ${JSON.stringify(body)}`);
    }

    if (body.done === true) {
      if (body.error) {
        throw new Error(`Vertex import operation failed: ${JSON.stringify(body.error)}`);
      }

      return body;
    }

    if (Date.now() - start > timeoutMs) {
      throw new Error(`Timed out waiting for operation: ${operationName}`);
    }

    await sleep(5000);
  }
}

function printUsage() {
  console.log('Usage: node scripts/uploadAndImportVertexRag.js [options]');
  console.log('Options:');
  console.log('  --project-id <id>          GCP project id (default: GCP_PROJECT_ID)');
  console.log('  --region <region>          Vertex region (default: GCP_REGION or us-central1)');
  console.log('  --corpus-id <id>           Vertex RagCorpus id (default: VERTEX_RAG_CORPUS_ID)');
  console.log('  --gcs-prefix <gs://...>    GCS prefix for uploads (default: RAG_GCS_URI_PREFIX)');
  console.log('  --out-dir <path>           Local export dir (default: server/rag_exports)');
  console.log('  --chunk-size <n>           Chunk size tokens (default: 512)');
  console.log('  --chunk-overlap <n>        Chunk overlap tokens (default: 100)');
  console.log('  --skip-clear-corpus        Keep existing corpus files and append import');
  console.log('  --wait                     Wait for import operation completion');
  console.log('  --dry-run                  Print actions without calling gcloud/Vertex APIs');
}
async function main() {
  if (hasFlag('--help')) {
    printUsage();
    return;
  }

  const projectId = getArgValue('--project-id') || process.env.GCP_PROJECT_ID;
  const region = getArgValue('--region') || process.env.GCP_REGION || 'us-central1';
  const ragCorpusId = getArgValue('--corpus-id') || process.env.VERTEX_RAG_CORPUS_ID;
  const gcsPrefixInput = getArgValue('--gcs-prefix') || process.env.RAG_GCS_URI_PREFIX;
  const localExportDir = getArgValue('--out-dir')
    ? path.resolve(getArgValue('--out-dir'))
    : path.resolve(__dirname, '..', 'rag_exports');
  const chunkSize = Number(getArgValue('--chunk-size') || process.env.RAG_CHUNK_SIZE || 512);
  const chunkOverlap = Number(getArgValue('--chunk-overlap') || process.env.RAG_CHUNK_OVERLAP || 100);
  const replaceCorpus = !hasFlag('--skip-clear-corpus');

  if (!projectId) {
    throw new Error('Missing project id. Set GCP_PROJECT_ID or pass --project-id');
  }

  if (!ragCorpusId) {
    throw new Error('Missing RAG corpus id. Set VERTEX_RAG_CORPUS_ID or pass --corpus-id');
  }

  const gcsPrefix = normalizeGsUri(gcsPrefixInput);

  const taskDocsPath = path.join(localExportDir, 'task_docs');
  const projectDocsPath = path.join(localExportDir, 'project_docs');
  const summaryDocsPath = path.join(localExportDir, 'summary_docs');

  assertPathExists(localExportDir, 'Local export directory');
  assertPathExists(taskDocsPath, 'Task docs directory');
  assertPathExists(projectDocsPath, 'Project docs directory');
  assertPathExists(summaryDocsPath, 'Summary docs directory');

  const taskDocCount = fs.readdirSync(taskDocsPath).filter((name) => name.endsWith('.txt')).length;
  const projectDocCount = fs.readdirSync(projectDocsPath).filter((name) => name.endsWith('.txt')).length;
  const summaryDocCount = fs.readdirSync(summaryDocsPath).filter((name) => name.endsWith('.txt')).length;

  console.log('Preparing Vertex RAG import from SQL-derived documents...');
  console.log(`Project: ${projectId}`);
  console.log(`Region: ${region}`);
  console.log(`RagCorpus: ${ragCorpusId}`);
  console.log(`Local exports: ${localExportDir}`);
  console.log(`GCS prefix: ${gcsPrefix}`);
  console.log(`Task docs: ${taskDocCount}`);
  console.log(`Project docs: ${projectDocCount}`);
  console.log(`Summary docs: ${summaryDocCount}`);
  console.log(`Clear existing corpus docs: ${replaceCorpus ? 'yes' : 'no'}`);

  if (hasFlag('--dry-run')) {
    console.log('Dry run enabled; no upload/import executed.');
    return;
  }

  const { taskDocsUri, projectDocsUri, summaryDocsUri } = await uploadToGcs(localExportDir, gcsPrefix);
  console.log('Upload sync complete.');

  const token = await getAccessToken();

  if (replaceCorpus) {
    await clearCorpusRagFiles({ projectId, region, ragCorpusId, token });
  }

  const operationName = await startImport({
    projectId,
    region,
    ragCorpusId,
    uris: [taskDocsUri, projectDocsUri, summaryDocsUri],
    chunkSize,
    chunkOverlap,
    token,
  });

  console.log(`Vertex import started. Operation: ${operationName}`);

  if (hasFlag('--wait')) {
    console.log('Waiting for operation completion...');
    const result = await waitForOperation({ projectId, region, operationName, token });
    console.log(`Import completed: ${JSON.stringify(result.response || result, null, 2)}`);
  } else {
    console.log('Run again with --wait to block until completion.');
  }
}

main().catch((error) => {
  console.error(`RAG upload/import failed: ${error.message}`);
  process.exitCode = 1;
});


