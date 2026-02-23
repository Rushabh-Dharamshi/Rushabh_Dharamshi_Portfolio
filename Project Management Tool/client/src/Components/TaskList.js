import React from 'react';
import { Badge, Button, Form } from 'react-bootstrap';

const statusLabels = {
  backlog: 'Backlog',
  in_progress: 'In Progress',
  blocked: 'Blocked',
  done: 'Done',
};

function TaskList({ tasks, onToggleComplete, onDelete, onEdit, onStatusChange }) {
  if (!tasks.length) {
    return <p className="empty-state">No work items in this view.</p>;
  }

  return (
    <section className="list-grid" aria-label="Work item list">
      {tasks.map((task) => {
        const dueDate = new Date(task.due_date);
        const overdue = !task.is_completed && dueDate < new Date();
        const canSetDone = Number(task.progress) === 100;

        return (
          <article key={task.id} className={`work-card ${task.priority}`}>
            <div className="work-card-header">
              <h4>{task.title}</h4>
              <Badge bg={task.priority === 'high' ? 'danger' : task.priority === 'medium' ? 'warning' : 'info'}>
                {task.priority}
              </Badge>
            </div>

            <p className="work-meta">#{task.id} • {task.project_name || 'Unassigned'} • {task.assignee || 'Unassigned'}</p>
            <p className="work-desc">{task.description}</p>

            <div className="status-row">
              <Form.Select
                size="sm"
                value={task.status || 'backlog'}
                onChange={(event) => onStatusChange(task.id, event.target.value)}
              >
                <option value="backlog">Backlog</option>
                <option value="in_progress">In Progress</option>
                <option value="blocked">Blocked</option>
                <option value="done" disabled={!canSetDone}>Done (100% only)</option>
              </Form.Select>
              <span className={`status-pill ${task.status || 'backlog'}`}>{statusLabels[task.status] || 'Backlog'}</span>
            </div>

            <div className="progress-track" aria-label={`Progress ${task.progress}%`}>
              <div className="progress-fill" style={{ width: `${task.progress}%` }} />
            </div>

            <p className={`work-due ${overdue ? 'overdue' : ''}`}>
              Due: {dueDate.toLocaleDateString()} {overdue ? '• Overdue' : ''}
            </p>

            <div className="card-actions">
              <Form.Check
                type="checkbox"
                label="Completed"
                checked={Boolean(task.is_completed)}
                disabled={!canSetDone}
                onChange={(event) => onToggleComplete(task.id, event.target.checked)}
              />
              <div>
                <Button size="sm" variant="outline-secondary" onClick={() => onEdit(task)}>
                  Edit
                </Button>{' '}
                <Button size="sm" variant="outline-danger" onClick={() => onDelete(task.id)}>
                  Delete
                </Button>
              </div>
            </div>
          </article>
        );
      })}
    </section>
  );
}

export default TaskList;

