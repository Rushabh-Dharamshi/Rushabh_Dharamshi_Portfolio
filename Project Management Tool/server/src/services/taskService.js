const VALID_PRIORITIES = ['low', 'medium', 'high'];
const VALID_DIFFICULTIES = ['easy', 'medium', 'hard'];
const VALID_STATUSES = ['backlog', 'in_progress', 'blocked', 'done'];

function normalizeString(value) {
  if (typeof value !== 'string') {
    return '';
  }

  return value.trim();
}

function normalizeTaskPayload(payload, { isUpdate = false } = {}) {
  const title = normalizeString(payload.title);
  const description = normalizeString(payload.description);
  const dueDate = normalizeString(payload.due_date);
  const priority = normalizeString(payload.priority).toLowerCase();
  const difficulty = normalizeString(payload.difficulty_level).toLowerCase();
  const progress = Number(payload.progress);
  const statusInput = normalizeString(payload.status).toLowerCase();
  const status = VALID_STATUSES.includes(statusInput)
    ? statusInput
    : progress === 100 || payload.is_completed
      ? 'done'
      : 'backlog';

  if (!title || !description || !dueDate || !priority || !difficulty || Number.isNaN(progress)) {
    const mode = isUpdate ? 'update' : 'create';
    throw new Error(`Missing required fields for ${mode}: title, description, due_date, priority, difficulty_level, progress`);
  }

  if (!VALID_PRIORITIES.includes(priority)) {
    throw new Error(`Priority must be one of: ${VALID_PRIORITIES.join(', ')}`);
  }

  if (!VALID_DIFFICULTIES.includes(difficulty)) {
    throw new Error(`Difficulty level must be one of: ${VALID_DIFFICULTIES.join(', ')}`);
  }

  if (!VALID_STATUSES.includes(status)) {
    throw new Error(`Status must be one of: ${VALID_STATUSES.join(', ')}`);
  }

  if (progress < 0 || progress > 100) {
    throw new Error('Progress must be a number between 0 and 100');
  }

  if (status === 'done' && progress !== 100) {
    throw new Error('Status can be set to done only when progress is 100');
  }

  if (payload.is_completed === true && progress !== 100) {
    throw new Error('A task can be marked completed only when progress is 100');
  }

  const projectId = payload.project_id ? Number(payload.project_id) : null;

  return {
    title,
    description,
    due_date: dueDate,
    priority,
    difficulty_level: difficulty,
    progress,
    category: normalizeString(payload.category) || null,
    is_completed: Boolean(payload.is_completed) || status === 'done' || progress === 100,
    project_id: Number.isFinite(projectId) ? projectId : null,
    status,
    assignee: normalizeString(payload.assignee) || null,
    estimated_hours:
      payload.estimated_hours === null || payload.estimated_hours === undefined || payload.estimated_hours === ''
        ? null
        : Number(payload.estimated_hours),
  };
}

module.exports = {
  VALID_STATUSES,
  normalizeTaskPayload,
};

