const path = require('path');
const express = require('express');
const request = require('supertest');
const { loadFeature, defineFeature } = require('jest-cucumber');

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
  refreshTaskRisk: jest.fn().mockResolvedValue(null),
}));

const taskRepository = require('../../src/repositories/taskRepository');
const taskRoutes = require('../../src/routes/taskRoutes');

const feature = loadFeature(path.join(__dirname, 'task-status.feature'));

function createTestApp() {
  const app = express();
  app.use(express.json());
  app.use('/tasks', taskRoutes);
  app.use((error, req, res, next) => {
    res.status(500).json({ error: error.message });
  });
  return app;
}

defineFeature(feature, (test) => {
  let app;
  let response;
  let taskId;

  beforeEach(() => {
    jest.clearAllMocks();
    app = createTestApp();
    response = undefined;
    taskId = undefined;
    taskRepository.updateTaskStatus.mockResolvedValue();
  });

  test('Reject done status when progress is below 100', ({ given, when, then, and }) => {
    given(/^a task with id (\d+) and progress (\d+)$/, async (id, progress) => {
      taskId = Number(id);
      taskRepository.getTaskById.mockResolvedValue({
        id: taskId,
        progress: Number(progress),
        status: 'in_progress',
      });
    });

    when(/^I set the task status to "(.*)"$/, async (status) => {
      response = await request(app).patch(`/tasks/${taskId}/status`).send({ status });
    });

    then(/^the API responds with status code (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and(/^the response contains "(.*)"$/, (expectedMessage) => {
      expect(response.body.error).toContain(expectedMessage);
      expect(taskRepository.updateTaskStatus).not.toHaveBeenCalled();
    });
  });

  test('Accept done status when progress is 100', ({ given, when, then, and }) => {
    given(/^a task with id (\d+) and progress (\d+)$/, async (id, progress) => {
      taskId = Number(id);
      taskRepository.getTaskById.mockResolvedValue({
        id: taskId,
        progress: Number(progress),
        status: 'in_progress',
      });
    });

    when(/^I set the task status to "(.*)"$/, async (status) => {
      response = await request(app).patch(`/tasks/${taskId}/status`).send({ status });
    });

    then(/^the API responds with status code (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and('the task status update is persisted', () => {
      expect(taskRepository.updateTaskStatus).toHaveBeenCalledWith(taskId, 'done');
      expect(response.body.message).toBe('Task status updated');
    });
  });
});