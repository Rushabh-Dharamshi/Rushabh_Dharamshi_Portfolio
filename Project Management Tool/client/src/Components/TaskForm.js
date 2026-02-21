import React from 'react';
import { Button, Col, Form, Row } from 'react-bootstrap';

function TaskForm({ task, setTask, projects, onSubmit, isEditing }) {
  const today = new Date().toISOString().slice(0, 10);
  const progressValue = Number(task.progress || 0);
  const isDoneAllowed = progressValue === 100;

  const handleChange = (key, value) => {
    setTask((prev) => {
      const next = { ...prev, [key]: value };
      if (key === 'progress' && Number(value) < 100 && prev.status === 'done') {
        next.status = 'in_progress';
      }
      return next;
    });
  };

  const canSubmit =
    task.title &&
    task.description &&
    task.due_date &&
    task.priority &&
    task.difficulty_level &&
    task.status;

  return (
    <Form onSubmit={onSubmit} className="panel-card">
      <div className="panel-header">
        <h3>{isEditing ? 'Update Work Item' : 'Create Work Item'}</h3>
        <p>Backlog-ready form with project, estimate, owner, and execution metadata.</p>
      </div>

      <Row className="g-3">
        <Col md={6}>
          <Form.Label>Title</Form.Label>
          <Form.Control
            className="field-input"
            value={task.title}
            onChange={(event) => handleChange('title', event.target.value)}
            maxLength={255}
            placeholder="Example: Launch onboarding revamp"
            required
          />
        </Col>
        <Col md={3}>
          <Form.Label>Priority</Form.Label>
          <Form.Select
            className="field-input"
            value={task.priority}
            onChange={(event) => handleChange('priority', event.target.value)}
            required
          >
            <option value="">Choose</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </Form.Select>
        </Col>
        <Col md={3}>
          <Form.Label>Difficulty</Form.Label>
          <Form.Select
            className="field-input"
            value={task.difficulty_level}
            onChange={(event) => handleChange('difficulty_level', event.target.value)}
            required
          >
            <option value="">Choose</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </Form.Select>
        </Col>

        <Col md={8}>
          <Form.Label>Description</Form.Label>
          <Form.Control
            className="field-input"
            as="textarea"
            rows={2}
            value={task.description}
            onChange={(event) => handleChange('description', event.target.value)}
            maxLength={1000}
            placeholder="Describe scope, outcome, and constraints"
            required
          />
        </Col>
        <Col md={4}>
          <Form.Label>Category</Form.Label>
          <Form.Control
            className="field-input"
            value={task.category}
            onChange={(event) => handleChange('category', event.target.value)}
            placeholder="Engineering / Design / Ops"
          />
        </Col>

        <Col md={3}>
          <Form.Label>Due Date</Form.Label>
          <Form.Control
            className="field-input"
            type="date"
            value={task.due_date}
            min={today}
            onChange={(event) => handleChange('due_date', event.target.value)}
            required
          />
        </Col>
        <Col md={3}>
          <Form.Label>Status</Form.Label>
          <Form.Select
            className="field-input"
            value={task.status}
            onChange={(event) => handleChange('status', event.target.value)}
            required
          >
            <option value="backlog">Backlog</option>
            <option value="in_progress">In Progress</option>
            <option value="blocked">Blocked</option>
            <option value="done" disabled={!isDoneAllowed}>Done (100% only)</option>
          </Form.Select>
        </Col>
        <Col md={3}>
          <Form.Label>Assignee</Form.Label>
          <Form.Control
            className="field-input"
            value={task.assignee}
            onChange={(event) => handleChange('assignee', event.target.value)}
            placeholder="Owner"
          />
        </Col>
        <Col md={3}>
          <Form.Label>Project</Form.Label>
          <Form.Select
            className="field-input"
            value={task.project_id || ''}
            onChange={(event) => handleChange('project_id', event.target.value ? Number(event.target.value) : null)}
          >
            <option value="">General</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </Form.Select>
        </Col>

        <Col md={3}>
          <Form.Label>Progress (%)</Form.Label>
          <Form.Control
            className="field-input"
            type="number"
            min={0}
            max={100}
            value={task.progress}
            onChange={(event) => handleChange('progress', Math.max(0, Math.min(100, Number(event.target.value))))}
          />
          {!isDoneAllowed && <small className="text-muted">Set progress to 100 to enable Done.</small>}
        </Col>
        <Col md={3}>
          <Form.Label>Estimated Hours</Form.Label>
          <Form.Control
            className="field-input"
            type="number"
            min={0}
            step="0.5"
            value={task.estimated_hours ?? ''}
            onChange={(event) => handleChange('estimated_hours', event.target.value)}
            placeholder="8"
          />
        </Col>
      </Row>

      <div className="form-actions">
        <Button type="submit" disabled={!canSubmit} className="primary-btn">
          {isEditing ? 'Save Changes' : 'Add Work Item'}
        </Button>
      </div>
    </Form>
  );
}

export default TaskForm;
