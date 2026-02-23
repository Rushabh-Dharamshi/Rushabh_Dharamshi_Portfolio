process.env.NODE_ENV = process.env.NODE_ENV || 'test';
process.env.MYSQL_HOST = process.env.MYSQL_HOST || '127.0.0.1';
process.env.MYSQL_USER = process.env.MYSQL_USER || 'root';
process.env.MYSQL_PASSWORD = process.env.MYSQL_PASSWORD || 'rootpass';
process.env.MYSQL_DATABASE = process.env.MYSQL_DATABASE || 'project_management_test';
process.env.MYSQL_PORT = process.env.MYSQL_PORT || '3306';
process.env.MYSQL_POOL_SIZE = process.env.MYSQL_POOL_SIZE || '6';

const request = require('supertest');
const { createApp } = require('../../src/server');
const { initializeSchema } = require('../../src/db/initialize');
const pool = require('../../src/db/pool');

describe('API Integration', () => {
  let app;

  async function resetDatabase() {
    await pool.query('DELETE FROM tasks');
    await pool.query('DELETE FROM projects');
  }

  beforeAll(async () => {
    await initializeSchema();
    app = createApp();
  });

  beforeEach(async () => {
    await resetDatabase();
  });

  afterAll(async () => {
    await resetDatabase();
    await pool.end();
  });

  test('GET /health returns service status', async () => {
    const response = await request(app).get('/health');

    expect(response.status).toBe(200);
    expect(response.body.status).toBe('ok');
    expect(response.body.env).toBe('test');
  });

  test('POST /projects creates a project and GET /projects returns it', async () => {
    const createResponse = await request(app)
      .post('/projects')
      .send({ name: 'Integration Project', description: 'Created from integration test' });

    expect(createResponse.status).toBe(201);
    expect(createResponse.body.name).toBe('Integration Project');

    const listResponse = await request(app).get('/projects');
    expect(listResponse.status).toBe(200);
    expect(listResponse.body.some((project) => project.name === 'Integration Project')).toBe(true);
  });

  test('POST /projects rejects duplicate project names', async () => {
    await request(app).post('/projects').send({ name: 'Duplicate Name', description: '' });

    const duplicateResponse = await request(app)
      .post('/projects')
      .send({ name: 'Duplicate Name', description: 'Another description' });

    expect(duplicateResponse.status).toBe(409);
    expect(duplicateResponse.body.error).toContain('already exists');
  });

  test('POST /tasks creates task linked to project and filter by project_id returns it', async () => {
    const projectResponse = await request(app)
      .post('/projects')
      .send({ name: 'Task Scope Project', description: 'Scope test project' });

    const projectId = projectResponse.body.id;

    const createTaskResponse = await request(app)
      .post('/tasks')
      .send({
        title: 'Integration task',
        description: 'Verify task create endpoint',
        due_date: '2026-12-15',
        priority: 'medium',
        difficulty_level: 'easy',
        progress: 25,
        status: 'in_progress',
        is_completed: false,
        project_id: projectId,
      });

    expect(createTaskResponse.status).toBe(201);
    expect(createTaskResponse.body.task.project_id).toBe(projectId);

    const filteredList = await request(app).get(`/tasks?project_id=${projectId}`);

    expect(filteredList.status).toBe(200);
    expect(filteredList.body.length).toBe(1);
    expect(filteredList.body[0].title).toBe('Integration task');
  });

  test('PATCH /tasks/:id/status enforces done only at 100 progress', async () => {
    const projectResponse = await request(app)
      .post('/projects')
      .send({ name: 'Status Guardrail Project', description: 'for status check' });

    const createTaskResponse = await request(app)
      .post('/tasks')
      .send({
        title: 'Not done yet',
        description: 'Status guardrail check',
        due_date: '2026-11-02',
        priority: 'high',
        difficulty_level: 'hard',
        progress: 90,
        status: 'in_progress',
        is_completed: false,
        project_id: projectResponse.body.id,
      });

    const taskId = createTaskResponse.body.taskId;

    const response = await request(app).patch(`/tasks/${taskId}/status`).send({ status: 'done' });

    expect(response.status).toBe(400);
    expect(response.body.error).toContain('Status can be set to done only when progress is 100');
  });
});
