const { parentPort } = require('worker_threads');

function computeRisk(task) {
  const now = new Date();
  const dueDate = task.due_date ? new Date(task.due_date) : null;
  const daysUntilDue = dueDate ? Math.floor((dueDate - now) / (1000 * 60 * 60 * 24)) : 30;

  const priorityWeight = { low: 0.08, medium: 0.16, high: 0.28 };
  const difficultyWeight = { easy: 0.06, medium: 0.12, hard: 0.22 };

  const urgencyWeight =
    daysUntilDue < 0 ? 0.35 :
    daysUntilDue <= 1 ? 0.28 :
    daysUntilDue <= 3 ? 0.2 :
    daysUntilDue <= 7 ? 0.12 :
    0.06;

  const progressPenalty = Math.max(0, (70 - Number(task.progress || 0)) / 100) * 0.25;
  const statusPenalty = task.status === 'blocked' ? 0.22 : task.status === 'backlog' && daysUntilDue < 4 ? 0.1 : 0;

  let score =
    (priorityWeight[task.priority] || 0.1) +
    (difficultyWeight[task.difficulty_level] || 0.1) +
    urgencyWeight +
    progressPenalty +
    statusPenalty;

  if (task.is_completed || Number(task.progress) >= 100) {
    score = 0.02;
  }

  const bounded = Math.min(0.99, Math.max(0.01, Number(score.toFixed(2))));
  const label = bounded >= 0.65 ? 'high' : bounded >= 0.4 ? 'medium' : 'low';
  const recommendation =
    label === 'high'
      ? 'Split this task and assign immediate owner follow-up.'
      : label === 'medium'
        ? 'Increase check-in frequency and monitor progress daily.'
        : 'Current execution pace looks healthy.';

  return {
    score: bounded,
    label,
    days_until_due: daysUntilDue,
    recommendation,
  };
}

parentPort.on('message', (task) => {
  try {
    const result = computeRisk(task);
    parentPort.postMessage({ ok: true, result });
  } catch (error) {
    parentPort.postMessage({ ok: false, error: error.message });
  }
});
