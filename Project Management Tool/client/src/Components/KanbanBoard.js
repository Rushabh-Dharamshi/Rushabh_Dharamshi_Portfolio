import React from 'react';

const columns = [
  { key: 'backlog', label: 'Backlog' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'blocked', label: 'Blocked' },
  { key: 'done', label: 'Done' },
];

function KanbanBoard({ tasks, onStatusChange, onEdit }) {
  return (
    <section className="kanban-board" aria-label="Kanban board">
      {columns.map((column) => {
        const columnTasks = tasks.filter((task) => (task.status || 'backlog') === column.key);

        return (
          <div key={column.key} className="kanban-column">
            <h4>{column.label} <span>{columnTasks.length}</span></h4>
            <div className="kanban-items">
              {columnTasks.map((task) => {
                const canSetDone = Number(task.progress) === 100;

                return (
                  <button key={task.id} className="kanban-item" onClick={() => onEdit(task)}>
                    <strong>{task.title}</strong>
                    <small>{task.project_name || 'General'} • {task.priority}</small>
                    <small>{new Date(task.due_date).toLocaleDateString()}</small>
                    <select
                      value={task.status || 'backlog'}
                      onChange={(event) => {
                        event.stopPropagation();
                        onStatusChange(task.id, event.target.value);
                      }}
                      onClick={(event) => event.stopPropagation()}
                    >
                      <option value="backlog">Backlog</option>
                      <option value="in_progress">In Progress</option>
                      <option value="blocked">Blocked</option>
                      <option value="done" disabled={!canSetDone}>Done (100% only)</option>
                    </select>
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </section>
  );
}

export default KanbanBoard;
