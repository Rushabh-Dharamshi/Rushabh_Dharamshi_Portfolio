const pool = require('../db/pool');

async function listProjects() {
  const [rows] = await pool.query(
    `SELECT id, name, description, created_at
     FROM projects
     WHERE LOWER(name) <> 'general'
     ORDER BY created_at ASC`
  );
  return rows;
}

async function createProject({ name, description }) {
  const [existing] = await pool.query(
    `SELECT id FROM projects WHERE LOWER(name) = LOWER(?) LIMIT 1`,
    [name]
  );

  if (existing.length > 0) {
    const duplicateError = new Error('Project with that name already exists');
    duplicateError.code = 'PROJECT_DUPLICATE';
    throw duplicateError;
  }

  const [result] = await pool.query(
    `INSERT INTO projects (name, description) VALUES (?, ?)`,
    [name, description || null]
  );

  const [rows] = await pool.query(
    `SELECT id, name, description, created_at FROM projects WHERE id = ?`,
    [result.insertId]
  );

  return rows[0];
}

async function deleteProject(projectId) {
  const [projectRows] = await pool.query(
    `SELECT id, name FROM projects WHERE id = ? LIMIT 1`,
    [projectId]
  );

  if (!projectRows.length) {
    const notFoundError = new Error('Project not found');
    notFoundError.code = 'PROJECT_NOT_FOUND';
    throw notFoundError;
  }

  const project = projectRows[0];
  if (String(project.name || '').toLowerCase() === 'general') {
    const protectedError = new Error('Default General project cannot be deleted');
    protectedError.code = 'PROJECT_PROTECTED';
    throw protectedError;
  }

  const [taskRows] = await pool.query(
    `SELECT COUNT(*) AS count FROM tasks WHERE project_id = ?`,
    [projectId]
  );

  const taskCount = Number(taskRows[0]?.count || 0);
  if (taskCount > 0) {
    const hasTasksError = new Error('Cannot delete project with existing tasks. Move or delete tasks first.');
    hasTasksError.code = 'PROJECT_HAS_TASKS';
    hasTasksError.taskCount = taskCount;
    throw hasTasksError;
  }

  await pool.query(`DELETE FROM projects WHERE id = ?`, [projectId]);

  return {
    id: project.id,
    name: project.name,
  };
}

module.exports = {
  listProjects,
  createProject,
  deleteProject,
};
