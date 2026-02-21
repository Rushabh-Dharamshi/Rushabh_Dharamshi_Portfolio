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
  p.name AS project_name
`;

async function listTasks({ projectId } = {}) {
  const where = [];
  const values = [];

  if (projectId) {
    where.push('t.project_id = ?');
    values.push(projectId);
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

async function getAnalyticsOverview() {
  const queries = [
    pool.query(
      `SELECT COALESCE(category, 'Unspecified') AS key_name, COUNT(*) AS value_count
       FROM tasks
       GROUP BY COALESCE(category, 'Unspecified')
       ORDER BY value_count DESC`
    ),
    pool.query(
      `SELECT priority AS key_name, COUNT(*) AS value_count
       FROM tasks
       GROUP BY priority
       ORDER BY value_count DESC`
    ),
    pool.query(
      `SELECT difficulty_level AS key_name, COUNT(*) AS value_count
       FROM tasks
       GROUP BY difficulty_level
       ORDER BY value_count DESC`
    ),
    pool.query(
      `SELECT status AS key_name, COUNT(*) AS value_count
       FROM tasks
       GROUP BY status
       ORDER BY value_count DESC`
    ),
    pool.query(
      `SELECT DATE_FORMAT(updated_at, '%Y-%m-%d') AS day, COUNT(*) AS completed_count
       FROM tasks
       WHERE is_completed = 1
       GROUP BY DATE_FORMAT(updated_at, '%Y-%m-%d')
       ORDER BY day DESC
       LIMIT 14`
    ),
    pool.query(
      `SELECT COALESCE(assignee, 'Unassigned') AS assignee, COUNT(*) AS open_tasks, ROUND(AVG(progress), 2) AS avg_progress
       FROM tasks
       WHERE is_completed = 0
       GROUP BY COALESCE(assignee, 'Unassigned')
       ORDER BY open_tasks DESC
       LIMIT 10`
    ),
    pool.query(
      `SELECT COALESCE(p.name, 'General') AS project_name,
              SUM(CASE WHEN t.is_completed = 1 THEN 1 ELSE 0 END) AS completed,
              COUNT(*) AS total
       FROM tasks t
       LEFT JOIN projects p ON p.id = t.project_id
       GROUP BY COALESCE(p.name, 'General')
       ORDER BY total DESC`
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


