const express = require('express');
const taskRepository = require('../repositories/taskRepository');
const { scoreTasks } = require('../services/riskScoringService');
const { answerMessage } = require('../services/chatService');

const router = express.Router();

router.get('/ml/risk', async (req, res, next) => {
  try {
    const tasks = await taskRepository.listTasks();
    const scored = await scoreTasks(tasks);
    const ranked = scored.sort((a, b) => b.ml_risk.score - a.ml_risk.score);

    res.json({
      generated_at: new Date().toISOString(),
      tasks: ranked,
      top_risk: ranked.slice(0, 10),
    });
  } catch (error) {
    next(error);
  }
});

router.post('/chat', async (req, res, next) => {
  try {
    const message = String(req.body.message || '');
    const startedAt = Date.now();
    const result = await answerMessage(message, {
      conversationId: String(req.body.conversation_id || ''),
      context: req.body.context || {},
      recentMessages: Array.isArray(req.body.recent_messages) ? req.body.recent_messages : [],
    });
    const latencyMs = Date.now() - startedAt;

    res.json({
      ...result,
      latency_ms: latencyMs,
      mode: 'langchain-rag-ollama',
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;

