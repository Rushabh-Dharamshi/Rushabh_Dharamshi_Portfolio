const express = require('express');
const request = require('supertest');

jest.mock('../../src/repositories/taskRepository', () => ({
  listTasks: jest.fn(),
  createTask: jest.fn(),
  updateTask: jest.fn(),
  getTaskById: jest.fn(),
  updateTaskCompletion: jest.fn(),
  updateTaskStatus: jest.fn(),
  deleteTask: jest.fn(),
}));

jest.mock('../../src/services/riskScoringService', () => ({
  refreshTaskRisk: jest.fn(),
}));

const taskRepository = require('../../src/repositories/taskRepository');
const { refreshTaskRisk } = require('../../src/services/riskScoringService');
const taskRoutes = require('../../src/routes/taskRoutes');

function createTestApp() {
  const app = express();
  app.use(express.json());
  app.use('/tasks', taskRoutes);
  app.use((error, req, res, next) => {
    res.status(500).json({ error: error.message });
  });
  return app;
}

describe('taskRoutes', () => {
  let app;

  beforeEach(() => {
    jest.clearAllMocks();
    refreshTaskRisk.mockResolvedValue(null);
    app = createTestApp();
  });

  test('POST /tasks returns 400 for invalid payload', async () => {
    const response = await request(app).post('/tasks').send({
      title: 'Only title',
    });

    expect(response.status).toBe(400);
    expect(response.body.error).toContain('Missing required fields');
    expect(taskRepository.createTask).not.toHaveBeenCalled();
    expect(refreshTaskRisk).not.toHaveBeenCalled();
  });

  test('POST /tasks refreshes risk for created task', async () => {
    taskRepository.createTask.mockResolvedValue({ id: 3, title: 'New Task' });
    refreshTaskRisk.mockResolvedValue({ id: 3, title: 'New Task', risk_level: 'medium', risk_score: 0.52 });

    const response = await request(app).post('/tasks').send({
      title: 'New Task',
      description: 'Task description',
      due_date: '2026-12-15',
      priority: 'medium',
      difficulty_level: 'easy',
      progress: 10,
      project_id: 1,
    });

    expect(response.status).toBe(201);
    expect(refreshTaskRisk).toHaveBeenCalledWith(3);
    expect(response.body.task.risk_level).toBe('medium');
  });

  test('PUT /tasks/:id refreshes risk after update', async () => {
    taskRepository.updateTask.mockResolvedValue({ id: 5, title: 'Updated Task' });
    refreshTaskRisk.mockResolvedValue({ id: 5, title: 'Updated Task', risk_level: 'low', risk_score: 0.31 });

    const response = await request(app).put('/tasks/5').send({
      title: 'Updated Task',
      description: 'Task description',
      due_date: '2026-12-15',
      priority: 'low',
      difficulty_level: 'easy',
      progress: 80,
      project_id: 1,
      status: 'in_progress',
      is_completed: false,
    });

    expect(response.status).toBe(200);
    expect(refreshTaskRisk).toHaveBeenCalledWith(5);
    expect(response.body.task.risk_level).toBe('low');
  });

  test('PATCH /tasks/:id/completed returns 400 when progress is below 100', async () => {
    taskRepository.getTaskById.mockResolvedValue({
      id: 7,
      progress: 80,
      is_completed: 0,
    });

    const response = await request(app).patch('/tasks/7/completed').send({
      is_completed: true,
    });

    expect(response.status).toBe(400);
    expect(response.body.error).toBe('A task can be marked completed only when progress is 100');
    expect(taskRepository.updateTaskCompletion).not.toHaveBeenCalled();
    expect(refreshTaskRisk).not.toHaveBeenCalled();
  });

  test('PATCH /tasks/:id/completed refreshes risk when update succeeds', async () => {
    taskRepository.getTaskById.mockResolvedValue({ id: 7, progress: 100, is_completed: 0 });
    taskRepository.updateTaskCompletion.mockResolvedValue();

    const response = await request(app).patch('/tasks/7/completed').send({ is_completed: true });

    expect(response.status).toBe(200);
    expect(taskRepository.updateTaskCompletion).toHaveBeenCalledWith(7, true);
    expect(refreshTaskRisk).toHaveBeenCalledWith(7);
  });

  test('PATCH /tasks/:id/status returns 400 when done is requested below 100', async () => {
    taskRepository.getTaskById.mockResolvedValue({
      id: 9,
      progress: 60,
      status: 'in_progress',
    });

    const response = await request(app).patch('/tasks/9/status').send({
      status: 'done',
    });

    expect(response.status).toBe(400);
    expect(response.body.error).toBe('Status can be set to done only when progress is 100');
    expect(taskRepository.updateTaskStatus).not.toHaveBeenCalled();
    expect(refreshTaskRisk).not.toHaveBeenCalled();
  });

  test('PATCH /tasks/:id/status updates status and refreshes risk when progress is 100', async () => {
    taskRepository.getTaskById.mockResolvedValue({
      id: 12,
      progress: 100,
      status: 'in_progress',
    });
    taskRepository.updateTaskStatus.mockResolvedValue();

    const response = await request(app).patch('/tasks/12/status').send({
      status: 'done',
    });

    expect(response.status).toBe(200);
    expect(response.body.message).toBe('Task status updated');
    expect(taskRepository.updateTaskStatus).toHaveBeenCalledWith(12, 'done');
    expect(refreshTaskRisk).toHaveBeenCalledWith(12);
  });
});