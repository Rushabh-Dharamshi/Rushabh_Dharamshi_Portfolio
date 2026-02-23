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

const taskRepository = require('../../src/repositories/taskRepository');
const taskRoutes = require('../../src/routes/taskRoutes');

const feature = loadFeature(path.join(__dirname, 'task-route-guardrails.feature'));

function createTestApp() {
  const app = express();
  app.use(express.json());
  app.use('/tasks', taskRoutes);
  app.use((error, req, res, next) => {
    res.status(500).json({ error: error.message });
  });
  return app;
}

function parseBooleanInput(input) {
  if (input === 'true') return true;
  if (input === 'false') return false;
  return 'invalid';
}

defineFeature(feature, (test) => {
  let app;
  let response;
  let currentTaskId;

  beforeEach(() => {
    jest.clearAllMocks();
    app = createTestApp();
    response = undefined;
    currentTaskId = undefined;
    taskRepository.updateTaskStatus.mockResolvedValue();
    taskRepository.updateTaskCompletion.mockResolvedValue();
  });

  test('Reject invalid status value', ({ given, when, then, and }) => {
    given(/^a task exists with id (\d+) and progress (\d+)$/, (id, progress) => {
      currentTaskId = Number(id);
      taskRepository.getTaskById.mockResolvedValue({ id: currentTaskId, progress: Number(progress) });
    });

    when(/^I change task status for id (\d+) to "(.*)"$/, async (id, status) => {
      response = await request(app).patch(`/tasks/${id}/status`).send({ status });
    });

    then(/^the API response status should be (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and(/^the API error message should contain "(.*)"$/, (message) => {
      expect(response.body.error).toContain(message);
    });

    and('no task status update should be saved', () => {
      expect(taskRepository.updateTaskStatus).not.toHaveBeenCalled();
    });
  });

  test('Return not found when changing status for missing task', ({ given, when, then, and }) => {
    given(/^task id (\d+) does not exist$/, (id) => {
      currentTaskId = Number(id);
      taskRepository.getTaskById.mockResolvedValue(null);
    });

    when(/^I change task status for id (\d+) to "(.*)"$/, async (id, status) => {
      response = await request(app).patch(`/tasks/${id}/status`).send({ status });
    });

    then(/^the API response status should be (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and(/^the API error message should contain "(.*)"$/, (message) => {
      expect(response.body.error).toContain(message);
    });
  });

  test('Reject completion payload when boolean value is invalid', ({ given, when, then, and }) => {
    given(/^a task exists with id (\d+) and progress (\d+)$/, (id, progress) => {
      currentTaskId = Number(id);
      taskRepository.getTaskById.mockResolvedValue({ id: currentTaskId, progress: Number(progress) });
    });

    when(/^I change task completion for id (\d+) to "(.*)"$/, async (id, completion) => {
      const parsed = parseBooleanInput(completion);
      response = await request(app).patch(`/tasks/${id}/completed`).send({ is_completed: parsed });
    });

    then(/^the API response status should be (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and(/^the API error message should contain "(.*)"$/, (message) => {
      expect(response.body.error).toContain(message);
    });
  });

  test('Return not found when changing completion for missing task', ({ given, when, then, and }) => {
    given(/^task id (\d+) does not exist$/, (id) => {
      currentTaskId = Number(id);
      taskRepository.getTaskById.mockResolvedValue(null);
    });

    when(/^I change task completion for id (\d+) to "(.*)"$/, async (id, completion) => {
      const parsed = parseBooleanInput(completion);
      response = await request(app).patch(`/tasks/${id}/completed`).send({ is_completed: parsed });
    });

    then(/^the API response status should be (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and(/^the API error message should contain "(.*)"$/, (message) => {
      expect(response.body.error).toContain(message);
    });
  });

  test('Reject completion true below 100 progress', ({ given, when, then, and }) => {
    given(/^a task exists with id (\d+) and progress (\d+)$/, (id, progress) => {
      currentTaskId = Number(id);
      taskRepository.getTaskById.mockResolvedValue({ id: currentTaskId, progress: Number(progress) });
    });

    when(/^I change task completion for id (\d+) to "(.*)"$/, async (id, completion) => {
      const parsed = parseBooleanInput(completion);
      response = await request(app).patch(`/tasks/${id}/completed`).send({ is_completed: parsed });
    });

    then(/^the API response status should be (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and(/^the API error message should contain "(.*)"$/, (message) => {
      expect(response.body.error).toContain(message);
    });

    and('no task completion update should be saved', () => {
      expect(taskRepository.updateTaskCompletion).not.toHaveBeenCalled();
    });
  });

  test('Accept completion true at 100 progress', ({ given, when, then, and }) => {
    given(/^a task exists with id (\d+) and progress (\d+)$/, (id, progress) => {
      currentTaskId = Number(id);
      taskRepository.getTaskById.mockResolvedValue({ id: currentTaskId, progress: Number(progress) });
    });

    when(/^I change task completion for id (\d+) to "(.*)"$/, async (id, completion) => {
      const parsed = parseBooleanInput(completion);
      response = await request(app).patch(`/tasks/${id}/completed`).send({ is_completed: parsed });
    });

    then(/^the API response status should be (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and(/^task completion update should be saved as "(.*)"$/, (value) => {
      expect(taskRepository.updateTaskCompletion).toHaveBeenCalledWith(currentTaskId, value === 'true');
    });
  });

  test('Accept completion false at any progress', ({ given, when, then, and }) => {
    given(/^a task exists with id (\d+) and progress (\d+)$/, (id, progress) => {
      currentTaskId = Number(id);
      taskRepository.getTaskById.mockResolvedValue({ id: currentTaskId, progress: Number(progress) });
    });

    when(/^I change task completion for id (\d+) to "(.*)"$/, async (id, completion) => {
      const parsed = parseBooleanInput(completion);
      response = await request(app).patch(`/tasks/${id}/completed`).send({ is_completed: parsed });
    });

    then(/^the API response status should be (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and(/^task completion update should be saved as "(.*)"$/, (value) => {
      expect(taskRepository.updateTaskCompletion).toHaveBeenCalledWith(currentTaskId, value === 'true');
    });
  });
});