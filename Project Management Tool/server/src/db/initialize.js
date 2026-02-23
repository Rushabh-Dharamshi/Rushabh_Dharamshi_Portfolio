const fs = require('fs');
const path = require('path');
const pool = require('./pool');

async function initializeSchema() {
  // Keep schema colocated with backend source so it exists inside the server container image.
  const schemaPath = path.join(__dirname, 'schema.sql');
  const schemaSQL = fs.readFileSync(schemaPath, 'utf8');
  await pool.query(schemaSQL);
}

module.exports = { initializeSchema };
