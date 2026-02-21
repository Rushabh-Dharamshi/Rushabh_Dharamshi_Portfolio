const pool = require('../db/pool');

async function listProjects() {
  const [rows] = await pool.query(
    `SELECT id, name, description, created_at
     FROM projects
     ORDER BY created_at ASC`
  );
  return rows;
}

async function createProject({ name, description }) {
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

module.exports = {
  listProjects,
  createProject,
};
