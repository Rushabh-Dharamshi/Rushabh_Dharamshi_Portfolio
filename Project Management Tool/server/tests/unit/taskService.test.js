const { normalizeTaskPayload } = require('../../src/services/taskService');

describe('normalizeTaskPayload', () => {
  const basePayload = {
    title: 'Ship release',
    description: 'Prepare and deploy release build',
    due_date: '2026-03-01',
    priority: 'high',
    difficulty_level: 'hard',
    progress: 70,
    status: 'in_progress',
    is_completed: false,
    project_id: 3,
    assignee: 'Alex',
    estimated_hours: 8,
  };

  test('normalizes payload and auto-completes when progress is 100', () => {
    const payload = normalizeTaskPayload({
      ...basePayload,
      progress: 100,
      status: '',
      title: '  Ship release  ',
      description: '  Prepare and deploy release build  ',
    });

    expect(payload.title).toBe('Ship release');
    expect(payload.description).toBe('Prepare and deploy release build');
    expect(payload.status).toBe('done');
    expect(payload.is_completed).toBe(true);
    expect(payload.project_id).toBe(3);
  });

  test('persists optional user-entered fields', () => {
    const payload = normalizeTaskPayload({
      ...basePayload,
      category: '  Operations  ',
      assignee: '  Priya  ',
      estimated_hours: '12.5',
    });

    expect(payload.category).toBe('Operations');
    expect(payload.assignee).toBe('Priya');
    expect(payload.estimated_hours).toBe(12.5);
  });

  test('rejects status done when progress is below 100', () => {
    expect(() =>
      normalizeTaskPayload({
        ...basePayload,
        status: 'done',
        progress: 99,
      })
    ).toThrow('Status can be set to done only when progress is 100');
  });

  test('rejects is_completed=true when progress is below 100', () => {
    expect(() =>
      normalizeTaskPayload({
        ...basePayload,
        is_completed: true,
        progress: 40,
      })
    ).toThrow('A task can be marked completed only when progress is 100');
  });

  test('rejects invalid priority', () => {
    expect(() =>
      normalizeTaskPayload({
        ...basePayload,
        priority: 'urgent',
      })
    ).toThrow('Priority must be one of: low, medium, high');
  });

  test('rejects invalid estimated_hours', () => {
    expect(() =>
      normalizeTaskPayload({
        ...basePayload,
        estimated_hours: 'abc',
      })
    ).toThrow('estimated_hours must be a non-negative number');
  });
});
