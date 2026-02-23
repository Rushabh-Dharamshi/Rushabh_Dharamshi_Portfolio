'use strict';

const mysql = require('mysql2/promise');
const env = require('../config/env');

const db = env.db;

const config = {
  user: db.user,
  password: db.password,
  database: db.database,
  waitForConnections: true,
  connectionLimit: db.connectionLimit || 10,
  queueLimit: 0,
  multipleStatements: true,
};

// Cloud Run + Cloud SQL: connect via Unix socket
if (db.socketPath) {
  config.socketPath = db.socketPath;
} else {
  // Local/dev: connect via host
  config.host = db.host;
  config.port = db.port || 3306;
}

const pool = mysql.createPool(config);

module.exports = pool;