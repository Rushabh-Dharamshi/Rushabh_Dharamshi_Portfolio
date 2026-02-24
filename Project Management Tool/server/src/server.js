const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { port, nodeEnv, cors: corsConfig, security } = require('./config/env');
const { initializeSchema } = require('./db/initialize');
const tasksRouter = require('./routes/taskRoutes');
const projectsRouter = require('./routes/projectRoutes');
const analyticsRouter = require('./routes/analyticsRoutes');
const aiRouter = require('./routes/aiRoutes');
const { closeRiskWorkerPool } = require('./services/riskScoringService');

function buildAllowedOrigins() {
  const configured = new Set(corsConfig.allowedOrigins || []);

  if (nodeEnv !== 'production') {
    [
      'http://localhost:3000',
      'http://127.0.0.1:3000',
      'http://localhost:5173',
      'http://127.0.0.1:5173',
    ].forEach((origin) => configured.add(origin));
  }

  return configured;
}

function createCorsOptions() {
  const allowedOrigins = buildAllowedOrigins();

  return {
    origin(origin, callback) {
      if (!origin) {
        return callback(null, true);
      }

      if (allowedOrigins.size === 0 && nodeEnv !== 'production') {
        return callback(null, true);
      }

      return callback(null, allowedOrigins.has(origin));
    },
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    credentials: true,
    maxAge: 86400,
  };
}

function createApp() {
  const app = express();

  app.disable('x-powered-by');
  app.set('trust proxy', 1);

  app.use(helmet({
    contentSecurityPolicy: false,
    crossOriginEmbedderPolicy: false,
  }));
  
  app.use(compression());
  app.use(cors(createCorsOptions()));
  app.use(express.json({ limit: '1mb' }));

  if (nodeEnv !== 'test') {
    const globalLimiter = rateLimit({
      windowMs: security.globalRateWindowMs,
      max: security.globalRateMax,
      standardHeaders: true,
      legacyHeaders: false,
    });

    const chatLimiter = rateLimit({
      windowMs: security.globalRateWindowMs,
      max: security.chatRateMax,
      standardHeaders: true,
      legacyHeaders: false,
      message: {
        error: 'Too many chat requests, slow down and try again.',
      },
    });

    app.use(globalLimiter);
    app.use('/api/chat', chatLimiter);
  }

  app.use((req, res, next) => {
    const requestStart = Date.now();
    res.on('finish', () => {
      const elapsed = Date.now() - requestStart;
      console.log(`[${new Date().toISOString()}] ${req.method} ${req.url} -> ${res.statusCode} (${elapsed}ms)`);
    });

    next();
  });

  app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString(), env: nodeEnv });
  });

  app.use('/tasks', tasksRouter);
  app.use('/projects', projectsRouter);
  app.use('/api/analytics', analyticsRouter);
  app.use('/api', analyticsRouter);
  app.use('/api', aiRouter);
  

  app.use((error, req, res, next) => {
    console.error('Unhandled server error:', error);
    res.status(500).json({ error: 'Internal server error', details: error.message });
  });

  return app;
}

async function start() {
  try {
    await initializeSchema();
    console.log('Database schema initialized.');

    const app = createApp();
    const server = app.listen(port, () => {
      console.log(`Server listening on http://localhost:${port}`);
    });

    const shutdown = async () => {
      console.log('Graceful shutdown started...');
      await closeRiskWorkerPool();
      server.close(() => {
        process.exit(0);
      });
    };

    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);
  } catch (error) {
    console.error('Failed to start server:', error.message);
    process.exit(1);
  }
}

module.exports = { start, createApp };
