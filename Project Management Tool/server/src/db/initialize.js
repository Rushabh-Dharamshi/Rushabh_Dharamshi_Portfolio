const fs = require('fs');
const path = require('path');
const pool = require('./pool');

async function initializeSchema() {
  const schemaPath = path.join(__dirname, '..', '..', '..', 'database', 'schema.sql');
  const schemaSQL = fs.readFileSync(schemaPath, 'utf8');
  await pool.query(schemaSQL);
}

module.exports = { initializeSchema };
