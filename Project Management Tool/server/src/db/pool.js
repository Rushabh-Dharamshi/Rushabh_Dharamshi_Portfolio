const mysql = require('mysql2/promise');
const { db } = require('../config/env');

const pool = mysql.createPool({
  host: db.host,
  user: db.user,
  password: db.password,
  database: db.database,
  waitForConnections: true,
  connectionLimit: db.connectionLimit,
  queueLimit: 0,
  multipleStatements: true,
});

module.exports = pool;
