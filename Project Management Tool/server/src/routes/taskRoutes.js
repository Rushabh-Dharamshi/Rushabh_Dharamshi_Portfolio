const express = require('express');
const taskRepository = require('../repositories/taskRepository');
const { normalizeTaskPayload, VALID_STATUSES } = require('../services/taskService');

const router = express.Router();

function isValidationError(error) {
  return [
    'Missing required fields',
    'must be one of',
    'Progress',
    'Status can be set to done',
    'marked completed only',
    'project_id',
    'estimated_hours',
  ].some((token) => error.message.includes(token));
}

router.get('/', async (req, res, next) => {
  try {
    const projectId = req.query.project_id ? Number(req.query.project_id) : undefined;
    const tasks = await taskRepository.listTasks({ projectId });
    res.json(tasks);
  } catch (error) {
    next(error);
  }
});

router.post('/', async (req, res, next) => {
  try {
    const payload = normalizeTaskPayload(req.body);
    const createdTask = await taskRepository.createTask(payload);
    res.status(201).json({ message: 'Task added', taskId: createdTask.id, task: createdTask });
  } catch (error) {
    if (isValidationError(error)) {
      return res.status(400).json({ error: error.message });
    }
    next(error);
  }
});

router.put('/:id', async (req, res, next) => {
  try {
    const payload = normalizeTaskPayload(req.body, { isUpdate: true });
    const task = await taskRepository.updateTask(Number(req.params.id), payload);
    res.json({ message: 'Task updated successfully', task });
  } catch (error) {
    if (isValidationError(error)) {
      return res.status(400).json({ error: error.message });
    }
    next(error);
  }
});

router.patch('/:id/completed', async (req, res, next) => {
  try {
    const taskId = Number(req.params.id);
    const { is_completed: isCompleted } = req.body;

    if (typeof isCompleted !== 'boolean') {
      return res.status(400).json({ error: 'is_completed must be a boolean' });
    }

    const task = await taskRepository.getTaskById(taskId);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }

    if (isCompleted && Number(task.progress) !== 100) {
      return res.status(400).json({ error: 'A task can be marked completed only when progress is 100' });
    }

    await taskRepository.updateTaskCompletion(taskId, isCompleted);
    res.json({ message: 'Task completion status updated' });
  } catch (error) {
    next(error);
  }
});

router.patch('/:id/status', async (req, res, next) => {
  try {
    const taskId = Number(req.params.id);
    const status = String(req.body.status || '').toLowerCase();

    if (!VALID_STATUSES.includes(status)) {
      return res.status(400).json({ error: `status must be one of: ${VALID_STATUSES.join(', ')}` });
    }

    const task = await taskRepository.getTaskById(taskId);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }

    if (status === 'done' && Number(task.progress) !== 100) {
      return res.status(400).json({ error: 'Status can be set to done only when progress is 100' });
    }

    await taskRepository.updateTaskStatus(taskId, status);
    res.json({ message: 'Task status updated' });
  } catch (error) {
    next(error);
  }
});

router.delete('/:id', async (req, res, next) => {
  try {
    await taskRepository.deleteTask(Number(req.params.id));
    res.json({ message: 'Task deleted' });
  } catch (error) {
    next(error);
  }
});

module.exports = router;


