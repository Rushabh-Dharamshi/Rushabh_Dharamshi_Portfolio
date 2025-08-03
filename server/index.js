require('dotenv').config({ override: true });
const fs = require('fs');
const path = require('path');
const express = require('express');
const mysql = require('mysql2');
const cors = require('cors');

console.log("Starting server...");

const app = express();
const port = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  next();
});

const requiredEnv = ['DB_HOST', 'DB_USER', 'DB_NAME'];
const missingEnv = requiredEnv.filter(envVar => !process.env[envVar]);
if (missingEnv.length > 0) {
  console.error(`Missing required environment variables: ${missingEnv.join(', ')}`);
  process.exit(1);
}

const db = mysql.createConnection({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASS || '',
  database: process.env.DB_NAME,
});

db.connect(async (err) => {
  if (err) {
    console.error('Error connecting to the database:', err.message);
    process.exit(1);
  }
  console.log('Connected to the MySQL database.');

  try {
    const schemaPath = path.join(__dirname, '..', 'database', 'schema.sql');
    const schemaSQL = fs.readFileSync(schemaPath, 'utf8');
    await new Promise((resolve, reject) => {
      db.query(schemaSQL, (err) => {
        if (err) {
          return reject(err);
        }
        console.log('Database schema setup completed.');
        resolve();
      });
    });
  } catch (error) {
    console.error('Error executing schema.sql:', error.message);
    process.exit(1);
  }
});

app.get('/tasks', (req, res) => {
  const query = `
    SELECT * FROM tasks 
    ORDER BY due_date ASC, 
    CASE priority 
      WHEN 'high' THEN 1 
      WHEN 'medium' THEN 2
      WHEN 'low' THEN 3 
      ELSE 4
    END ASC
  `;
  db.query(query, (err, results) => {
    if (err) {
      console.error('Failed to fetch tasks:', err);
      return res.status(500).json({ error: 'Failed to fetch tasks' });
    }
    res.json(results);
  });
});


app.get('/api/tasks/completed-by-category', (req, res) => {
  const query = `
    SELECT 
      COALESCE(category, 'Uncategorized') AS category,
      COUNT(*) AS completed_count
    FROM tasks
    WHERE is_completed = 1
    GROUP BY category
  `;
  db.query(query, (err, results) => {
    if (err) {
      console.error('Error fetching completed tasks by category:', err);
      return res.status(500).json({ error: 'Database error' });
    }
    res.json(results);
  });
});

app.get('/api/tasks/completed-by-difficulty', (req, res) => {
  const query = `
    SELECT 
      difficulty_level,
      COUNT(*) AS completed_count
    FROM tasks
    WHERE is_completed = 1
    GROUP BY difficulty_level
  `;
  db.query(query, (err, results) => {
    if (err) {
      console.error('Error fetching completed tasks by difficulty:', err);
      return res.status(500).json({ error: 'Database error' });
    }
    res.json(results);
  });
});

app.get('/api/tasks/completed-by-deadline', (req, res) => {
  const query = `
    SELECT
      CASE
        WHEN DATE(due_date) = CURDATE() THEN 'Today'
        WHEN DATE(due_date) > CURDATE() AND DATE(due_date) <= DATE_ADD(CURDATE(), INTERVAL 7 DAY) THEN 'Next Week'
        WHEN DATE(due_date) > DATE_ADD(CURDATE(), INTERVAL 7 DAY) AND DATE(due_date) <= DATE_ADD(CURDATE(), INTERVAL 30 DAY) THEN 'Next Month'
        ELSE 'Later'
      END AS due_range,
      COUNT(*) AS completed_count
    FROM tasks
    WHERE is_completed = 1
    GROUP BY due_range
  `;
  db.query(query, (err, results) => {
    if (err) {
      console.error('Error fetching completed tasks by deadline:', err);
      return res.status(500).json({ error: 'Database error' });
    }
    res.json(results);
  });
});


app.post('/tasks', (req, res) => {
  const { title, description, due_date, priority, difficulty_level, progress, category } = req.body;

  if (!title || !description || !due_date || !priority || !difficulty_level || progress === undefined) {
    return res.status(400).json({ error: 'All fields except category are required: title, description, due_date, priority, difficulty_level, progress' });
  }

  const validPriorities = ['low', 'medium', 'high'];
  const validDifficulties = ['easy', 'medium', 'hard'];
  const normalizedPriority = priority.toLowerCase();
  const normalizedDifficulty = difficulty_level.toLowerCase();

  if (!validPriorities.includes(normalizedPriority)) {
    return res.status(400).json({ error: `Priority must be one of: ${validPriorities.join(', ')}` });
  }
  if (!validDifficulties.includes(normalizedDifficulty)) {
    return res.status(400).json({ error: `Difficulty level must be one of: ${validDifficulties.join(', ')}` });
  }
  if (typeof progress !== 'number' || progress < 0 || progress > 100) {
    return res.status(400).json({ error: 'Progress must be a number between 0 and 100' });
  }

  const query = `
    INSERT INTO tasks (title, description, due_date, priority, difficulty_level, progress, category)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `;
  db.query(query, [title, description, due_date, normalizedPriority, normalizedDifficulty, progress, category || null], (err, results) => {
    if (err) {
      console.error('Failed to add task:', err);
      return res.status(500).json({ error: 'Failed to add task' });
    }
    res.status(201).json({ message: 'Task added', taskId: results.insertId });
  });
});

app.put('/tasks/:id', (req, res) => {
  const taskId = req.params.id;
  const { title, description, due_date, priority, difficulty_level, progress, category, is_completed } = req.body;

  if (!title || !description || !due_date || !priority || !difficulty_level || progress === undefined) {
    return res.status(400).json({ error: 'All fields except category are required: title, description, due_date, priority, difficulty_level, progress' });
  }

  const validPriorities = ['low', 'medium', 'high'];
  const validDifficulties = ['easy', 'medium', 'hard'];
  const normalizedPriority = priority.toLowerCase();
  const normalizedDifficulty = difficulty_level.toLowerCase();

  if (!validPriorities.includes(normalizedPriority)) {
    return res.status(400).json({ error: `Priority must be one of: ${validPriorities.join(', ')}` });
  }
  if (!validDifficulties.includes(normalizedDifficulty)) {
    return res.status(400).json({ error: `Difficulty level must be one of: ${validDifficulties.join(', ')}` });
  }
  if (typeof progress !== 'number' || progress < 0 || progress > 100) {
    return res.status(400).json({ error: 'Progress must be a number between 0 and 100' });
  }

  const completed = typeof is_completed === 'boolean' ? is_completed : false;

  const query = `
    UPDATE tasks
    SET title = ?, description = ?, due_date = ?, priority = ?, difficulty_level = ?, progress = ?, category = ?, is_completed = ?
    WHERE id = ?
  `;

  db.query(query, [title, description, due_date, normalizedPriority, normalizedDifficulty, progress, category || null, completed, taskId], (err) => {
    if (err) {
      console.error('Failed to update task:', err);
      return res.status(500).json({ error: 'Failed to update task' });
    }
    res.json({ message: 'Task updated successfully' });
  });
});


app.patch('/tasks/:id/completed', (req, res) => {
  const taskId = req.params.id;
  const { is_completed } = req.body;

  if (typeof is_completed !== 'boolean') {
    return res.status(400).json({ error: 'is_completed must be a boolean' });
  }

  const query = 'UPDATE tasks SET is_completed = ? WHERE id = ?';
  db.query(query, [is_completed, taskId], (err) => {
    if (err) {
      console.error('Failed to update task completion:', err);
      return res.status(500).json({ error: 'Failed to update task completion status' });
    }
    res.json({ message: 'Task completion status updated' });
  });
});

app.delete('/tasks/:id', (req, res) => {
  const taskId = req.params.id;

  const query = 'DELETE FROM tasks WHERE id = ?';
  db.query(query, [taskId], (err) => {
    if (err) {
      console.error('Failed to delete task:', err);
      return res.status(500).json({ error: 'Failed to delete task' });
    }
    res.json({ message: 'Task deleted' });
  });
});

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
