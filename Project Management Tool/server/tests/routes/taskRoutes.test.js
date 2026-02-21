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

const taskRepository = require('../../src/repositories/taskRepository');
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
    app = createTestApp();
  });

  test('POST /tasks returns 400 for invalid payload', async () => {
    const response = await request(app).post('/tasks').send({
      title: 'Only title',
    });

    expect(response.status).toBe(400);
    expect(response.body.error).toContain('Missing required fields');
    expect(taskRepository.createTask).not.toHaveBeenCalled();
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
  });

  test('PATCH /tasks/:id/status updates status when progress is 100', async () => {
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
  });
});