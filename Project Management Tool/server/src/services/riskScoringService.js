const path = require('path');
const { workers } = require('../config/env');
const WorkerPool = require('../utils/workerPool');

const workerPath = path.join(__dirname, '..', 'workers', 'riskWorker.js');
const workerPool = new WorkerPool(workerPath, workers.size);

async function scoreTasks(tasks) {
  const riskResults = await Promise.all(
    tasks.map((task) => workerPool.run(task))
  );

  return tasks.map((task, index) => ({
    ...task,
    ml_risk: riskResults[index],
  }));
}

function closeRiskWorkerPool() {
  return workerPool.close();
}

module.exports = {
  scoreTasks,
  closeRiskWorkerPool,
};
