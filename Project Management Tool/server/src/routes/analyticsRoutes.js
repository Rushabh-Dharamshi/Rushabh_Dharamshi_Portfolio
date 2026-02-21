const express = require('express');
const taskRepository = require('../repositories/taskRepository');

const router = express.Router();

function mapRows(rows) {
  return rows.map((row) => ({ label: row.key_name, value: row.value_count }));
}

router.get('/overview', async (req, res, next) => {
  try {
    const overview = await taskRepository.getAnalyticsOverview();
    res.json({
      ...overview,
      category: mapRows(overview.category),
      priority: mapRows(overview.priority),
      difficulty: mapRows(overview.difficulty),
      status: mapRows(overview.status),
    });
  } catch (error) {
    next(error);
  }
});

router.get('/tasks/completed-by-category', async (req, res, next) => {
  try {
    const overview = await taskRepository.getAnalyticsOverview();
    res.json(mapRows(overview.category).map((item) => ({ category: item.label, completed_count: item.value })));
  } catch (error) {
    next(error);
  }
});

router.get('/tasks/completed-by-difficulty', async (req, res, next) => {
  try {
    const overview = await taskRepository.getAnalyticsOverview();
    res.json(mapRows(overview.difficulty).map((item) => ({ difficulty_level: item.label, completed_count: item.value })));
  } catch (error) {
    next(error);
  }
});

router.get('/tasks/completed-by-deadline', async (req, res, next) => {
  try {
    const tasks = await taskRepository.listTasks();
    const now = new Date();
    const buckets = {
      'Past Due': 0,
      Today: 0,
      'This Week': 0,
      Later: 0,
    };

    tasks.filter((task) => task.is_completed).forEach((task) => {
      const dueDate = new Date(task.due_date);
      const diffDays = Math.floor((dueDate - now) / (1000 * 60 * 60 * 24));

      if (diffDays < 0) {
        buckets['Past Due'] += 1;
      } else if (diffDays === 0) {
        buckets.Today += 1;
      } else if (diffDays <= 7) {
        buckets['This Week'] += 1;
      } else {
        buckets.Later += 1;
      }
    });

    res.json(Object.entries(buckets).map(([due_range, completed_count]) => ({ due_range, completed_count })));
  } catch (error) {
    next(error);
  }
});

module.exports = router;
