const os = require('os');
require('dotenv').config();

function pickEnv(...keys) {
  for (const key of keys) {
    const value = process.env[key];
    if (value !== undefined && String(value).trim() !== '') {
      return value;
    }
  }
  return undefined;
}

function parseCsv(value) {
  if (!value) {
    return [];
  }

  return String(value)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

const cloudSqlConnectionName = pickEnv('CLOUD_SQL_CONNECTION_NAME');
const cloudSqlSocketPath = cloudSqlConnectionName ? `/cloudsql/${cloudSqlConnectionName}` : undefined;

const dbHost = pickEnv('MYSQL_HOST', 'DB_HOST');
const dbUser = pickEnv('MYSQL_USER', 'DB_USER');
const dbName = pickEnv('MYSQL_DATABASE', 'DB_NAME');
const dbPass = pickEnv('MYSQL_PASSWORD', 'DB_PASS', 'MYSQL_PASS');
const dbPoolSize = pickEnv('MYSQL_POOL_SIZE', 'DB_POOL_SIZE');
const dbPort = pickEnv('MYSQL_PORT', 'DB_PORT');

const missing = [];

if (!cloudSqlSocketPath && !dbHost) missing.push('MYSQL_HOST (or DB_HOST)');
if (!dbUser) missing.push('MYSQL_USER (or DB_USER)');
if (!dbName) missing.push('MYSQL_DATABASE (or DB_NAME)');

if (missing.length > 0) {
  throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
}

module.exports = {
  nodeEnv: process.env.NODE_ENV || 'development',
  port: Number(process.env.PORT || 5000),

  db: {
    host: dbHost,
    socketPath: cloudSqlSocketPath,
    user: dbUser,
    password: dbPass || '',
    database: dbName,
    port: Number(dbPort || 3306),
    connectionLimit: Number(dbPoolSize || 10),
  },

  workers: {
    size: Number(process.env.WORKER_POOL_SIZE || Math.max(2, Math.min(6, os.cpus().length - 1))),
  },

  cors: {
    allowedOrigins: parseCsv(process.env.CORS_ALLOWED_ORIGINS),
  },

  security: {
    globalRateWindowMs: Number(process.env.RATE_LIMIT_WINDOW_MS || 60_000),
    globalRateMax: Number(process.env.RATE_LIMIT_MAX || 240),
    chatRateMax: Number(process.env.CHAT_RATE_LIMIT_MAX || 40),
  },

  ai: {
    provider: process.env.AI_PROVIDER || 'vertex-rag',
    gcpProjectId: pickEnv('GCP_PROJECT_ID', 'GOOGLE_CLOUD_PROJECT', 'GCLOUD_PROJECT'),
    gcpRegion: process.env.GCP_REGION || 'europe-west2',
    ragCorpusId: process.env.VERTEX_RAG_CORPUS_ID || '',
    geminiModel: process.env.GEMINI_MODEL || 'gemini-3.1-pro-preview',
    geminiRegion: process.env.GEMINI_REGION || 'global',
    ragTopK: Number(process.env.RAG_TOP_K || 4),
    temperature: Number(process.env.GEMINI_TEMPERATURE || 0.15),
    maxOutputTokens: Number(process.env.GEMINI_MAX_OUTPUT_TOKENS || 512),
  },
};


