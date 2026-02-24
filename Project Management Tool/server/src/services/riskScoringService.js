const path = require('path');
const { workers } = require('../config/env');
const WorkerPool = require('../utils/workerPool');
const taskRepository = require('../repositories/taskRepository');

const workerPath = path.join(__dirname, '..', 'workers', 'riskWorker.js');
const workerPool = new WorkerPool(workerPath, workers.size);

async function scoreTasks(tasks, { persist = true } = {}) {
  const riskResults = await Promise.all(
    tasks.map((task) => workerPool.run(task))
  );

  const scoredTasks = tasks.map((task, index) => ({
    ...task,
    ml_risk: riskResults[index],
  }));

  if (persist) {
    const updates = scoredTasks
      .filter((task) => Number.isFinite(Number(task.id)) && task.ml_risk)
      .map((task) => ({
        id: Number(task.id),
        score: Number(task.ml_risk.score),
        label: String(task.ml_risk.label || '').toLowerCase(),
      }));

    await taskRepository.updateTaskRisks(updates);
  }

  return scoredTasks;
}

async function refreshTaskRisk(taskId) {
  const normalizedTaskId = Number(taskId);
  if (!Number.isFinite(normalizedTaskId) || normalizedTaskId <= 0) {
    return null;
  }

  const task = await taskRepository.getTaskById(normalizedTaskId);
  if (!task) {
    return null;
  }

  const [scoredTask] = await scoreTasks([task], { persist: true });
  return scoredTask || null;
}

function closeRiskWorkerPool() {
  return workerPool.close();
}

module.exports = {
  scoreTasks,
  refreshTaskRisk,
  closeRiskWorkerPool,
};