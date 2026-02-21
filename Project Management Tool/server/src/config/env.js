const os = require('os');
require('dotenv').config({ override: true });

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

const dbHost = pickEnv('MYSQL_HOST', 'DB_HOST');
const dbUser = pickEnv('MYSQL_USER', 'DB_USER');
const dbName = pickEnv('MYSQL_DATABASE', 'DB_NAME');
const dbPass = pickEnv('MYSQL_PASSWORD', 'DB_PASS', 'MYSQL_PASS');
const dbPoolSize = pickEnv('MYSQL_POOL_SIZE', 'DB_POOL_SIZE');

const missing = [];
if (!dbHost) missing.push('MYSQL_HOST (or DB_HOST)');
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
    user: dbUser,
    password: dbPass || '',
    database: dbName,
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
  ollama: {
    baseUrl: process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434',
    chatModel: process.env.OLLAMA_CHAT_MODEL || 'mistral:latest',
    embedModel: process.env.OLLAMA_EMBED_MODEL || 'nomic-embed-text:latest',
  },
};
