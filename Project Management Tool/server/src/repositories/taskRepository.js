const pool = require('../db/pool');

const baseTaskFields = `
  t.id,
  t.title,
  t.description,
  t.due_date,
  t.priority,
  t.difficulty_level,
  t.progress,
  t.category,
  t.is_completed,
  t.project_id,
  t.status,
  t.assignee,
  t.estimated_hours,
  t.created_at,
  t.updated_at,
  CASE
    WHEN p.name IS NULL OR LOWER(p.name) = 'general' THEN 'Unassigned'
    ELSE p.name
  END AS project_name
`;

function normalizeProjectId(projectId) {
  if (projectId === undefined || projectId === null || projectId === '') {
    return undefined;
  }

  const numeric = Number(projectId);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return undefined;
  }

  return numeric;
}

async function listTasks({ projectId } = {}) {
  const where = [];
  const values = [];
  const scopedProjectId = normalizeProjectId(projectId);

  if (scopedProjectId) {
    where.push('t.project_id = ?');
    values.push(scopedProjectId);
  }

  const whereClause = where.length ? `WHERE ${where.join(' AND ')}` : '';

  const [rows] = await pool.query(
    `SELECT ${baseTaskFields}
     FROM tasks t
     LEFT JOIN projects p ON p.id = t.project_id
     ${whereClause}
     ORDER BY t.due_date ASC,
      CASE t.priority
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
        ELSE 4
      END ASC,
      t.id DESC`,
    values
  );

  return rows;
}

async function createTask(task) {
  const [result] = await pool.query(
    `INSERT INTO tasks
      (title, description, due_date, priority, difficulty_level, progress, category, is_completed, project_id, status, assignee, estimated_hours)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      task.title,
      task.description,
      task.due_date,
      task.priority,
      task.difficulty_level,
      task.progress,
      task.category,
      task.is_completed,
      task.project_id,
      task.status,
      task.assignee,
      task.estimated_hours,
    ]
  );

  const [rows] = await pool.query(
    `SELECT ${baseTaskFields}
     FROM tasks t
     LEFT JOIN projects p ON p.id = t.project_id
     WHERE t.id = ?`,
    [result.insertId]
  );

  return rows[0];
}

async function getTaskById(id) {
  const [rows] = await pool.query(
    `SELECT ${baseTaskFields}
     FROM tasks t
     LEFT JOIN projects p ON p.id = t.project_id
     WHERE t.id = ?`,
    [id]
  );

  return rows[0] || null;
}

async function updateTask(id, task) {
  await pool.query(
    `UPDATE tasks
     SET
      title = ?,
      description = ?,
      due_date = ?,
      priority = ?,
      difficulty_level = ?,
      progress = ?,
      category = ?,
      is_completed = ?,
      project_id = ?,
      status = ?,
      assignee = ?,
      estimated_hours = ?
     WHERE id = ?`,
    [
      task.title,
      task.description,
      task.due_date,
      task.priority,
      task.difficulty_level,
      task.progress,
      task.category,
      task.is_completed,
      task.project_id,
      task.status,
      task.assignee,
      task.estimated_hours,
      id,
    ]
  );

  const [rows] = await pool.query(
    `SELECT ${baseTaskFields}
     FROM tasks t
     LEFT JOIN projects p ON p.id = t.project_id
     WHERE t.id = ?`,
    [id]
  );

  return rows[0];
}

async function updateTaskCompletion(id, isCompleted) {
  const normalizedStatus = isCompleted ? 'done' : 'in_progress';
  await pool.query(
    `UPDATE tasks SET is_completed = ?, status = ? WHERE id = ?`,
    [isCompleted, normalizedStatus, id]
  );
}

async function updateTaskStatus(id, status) {
  await pool.query(`UPDATE tasks SET status = ? WHERE id = ?`, [status, id]);
}

async function deleteTask(id) {
  await pool.query(`DELETE FROM tasks WHERE id = ?`, [id]);
}

async function getAnalyticsOverview({ projectId } = {}) {
  const scopedProjectId = normalizeProjectId(projectId);
  const filter = scopedProjectId ? 'WHERE project_id = ?' : '';
  const joinedFilter = scopedProjectId ? 'WHERE t.project_id = ?' : '';
  const values = scopedProjectId ? [scopedProjectId] : [];

  const queries = [
    pool.query(
      `SELECT COALESCE(category, 'Unspecified') AS key_name, COUNT(*) AS value_count
       FROM tasks
       ${filter}
       GROUP BY COALESCE(category, 'Unspecified')
       ORDER BY value_count DESC`,
      values
    ),
    pool.query(
      `SELECT priority AS key_name, COUNT(*) AS value_count
       FROM tasks
       ${filter}
       GROUP BY priority
       ORDER BY value_count DESC`,
      values
    ),
    pool.query(
      `SELECT difficulty_level AS key_name, COUNT(*) AS value_count
       FROM tasks
       ${filter}
       GROUP BY difficulty_level
       ORDER BY value_count DESC`,
      values
    ),
    pool.query(
      `SELECT status AS key_name, COUNT(*) AS value_count
       FROM tasks
       ${filter}
       GROUP BY status
       ORDER BY value_count DESC`,
      values
    ),
    pool.query(
      `SELECT DATE_FORMAT(updated_at, '%Y-%m-%d') AS day, COUNT(*) AS completed_count
       FROM tasks
       ${filter} ${filter ? 'AND' : 'WHERE'} is_completed = 1
       GROUP BY DATE_FORMAT(updated_at, '%Y-%m-%d')
       ORDER BY day DESC
       LIMIT 14`,
      values
    ),
    pool.query(
      `SELECT COALESCE(assignee, 'Unassigned') AS assignee, COUNT(*) AS open_tasks, ROUND(AVG(progress), 2) AS avg_progress
       FROM tasks
       ${filter} ${filter ? 'AND' : 'WHERE'} is_completed = 0
       GROUP BY COALESCE(assignee, 'Unassigned')
       ORDER BY open_tasks DESC
       LIMIT 10`,
      values
    ),
    pool.query(
      `SELECT CASE
                WHEN p.name IS NULL OR LOWER(p.name) = 'general' THEN 'Unassigned'
                ELSE p.name
              END AS project_name,
              SUM(CASE WHEN t.is_completed = 1 THEN 1 ELSE 0 END) AS completed,
              COUNT(*) AS total
       FROM tasks t
       LEFT JOIN projects p ON p.id = t.project_id
       ${joinedFilter}
       GROUP BY CASE
                  WHEN p.name IS NULL OR LOWER(p.name) = 'general' THEN 'Unassigned'
                  ELSE p.name
                END
       ORDER BY total DESC`,
      values
    ),
  ];

  const [category, priority, difficulty, status, completedTrend, workload, projectVelocity] =
    await Promise.all(queries);

  return {
    category: category[0],
    priority: priority[0],
    difficulty: difficulty[0],
    status: status[0],
    completedTrend: completedTrend[0].reverse(),
    workload: workload[0],
    projectVelocity: projectVelocity[0],
  };
}

module.exports = {
  listTasks,
  getTaskById,
  createTask,
  updateTask,
  updateTaskCompletion,
  updateTaskStatus,
  deleteTask,
  getAnalyticsOverview,
};
