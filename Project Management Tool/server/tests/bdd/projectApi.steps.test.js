const path = require('path');
const express = require('express');
const request = require('supertest');
const { loadFeature, defineFeature } = require('jest-cucumber');

jest.mock('../../src/repositories/projectRepository', () => ({
  listProjects: jest.fn(),
  createProject: jest.fn(),
  deleteProject: jest.fn(),
}));

const projectRepository = require('../../src/repositories/projectRepository');
const projectRoutes = require('../../src/routes/projectRoutes');

const feature = loadFeature(path.join(__dirname, 'project-api.feature'));

function createTestApp() {
  const app = express();
  app.use(express.json());
  app.use('/projects', projectRoutes);
  app.use((error, req, res, next) => {
    res.status(500).json({ error: error.message });
  });
  return app;
}

defineFeature(feature, (test) => {
  let app;
  let response;
  let createdName;
  let createdDescription;

  beforeEach(() => {
    jest.clearAllMocks();
    app = createTestApp();
    response = undefined;
    createdName = undefined;
    createdDescription = undefined;
  });

  test('Reject empty project name', ({ when, then, and }) => {
    when(/^I create a project with name "(.*)" and description "(.*)"$/, async (name, description) => {
      createdName = name;
      createdDescription = description;
      response = await request(app).post('/projects').send({ name, description });
    });

    then(/^the project API response status should be (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and(/^the project API error should contain "(.*)"$/, (message) => {
      expect(response.body.error).toContain(message);
      expect(projectRepository.createProject).not.toHaveBeenCalled();
    });
  });

  test('Create project successfully', ({ when, then, and }) => {
    when(/^I create a project with name "(.*)" and description "(.*)"$/, async (name, description) => {
      createdName = name;
      createdDescription = description;
      projectRepository.createProject.mockResolvedValue({ id: 77, name, description });
      response = await request(app).post('/projects').send({ name, description });
    });

    then(/^the project API response status should be (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and(/^the project payload should include name "(.*)"$/, (expectedName) => {
      expect(response.body.name).toBe(expectedName);
      expect(projectRepository.createProject).toHaveBeenCalledWith({ name: createdName, description: createdDescription });
    });
  });

  test('Reject duplicate project name', ({ given, when, then, and }) => {
    given(/^a project already exists with name "(.*)"$/, (name) => {
      const duplicateError = new Error('Duplicate');
      duplicateError.code = 'ER_DUP_ENTRY';
      projectRepository.createProject.mockRejectedValue(duplicateError);
      createdName = name;
    });

    when(/^I create a project with name "(.*)" and description "(.*)"$/, async (name, description) => {
      response = await request(app).post('/projects').send({ name, description });
    });

    then(/^the project API response status should be (\d+)$/, (statusCode) => {
      expect(response.status).toBe(Number(statusCode));
    });

    and(/^the project API error should contain "(.*)"$/, (message) => {
      expect(response.body.error).toContain(message);
    });
  });
});