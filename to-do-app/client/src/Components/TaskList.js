import React from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';

const TaskList = ({ tasks, onToggleComplete, onDelete, onEdit }) => {
  const highPriorityStyle = {
    backgroundColor: '#d37d7dff',
    color: '#fff',
  };

  const mediumPriorityStyle = {
    backgroundColor: '#ffc107',
    color: '#212529',
  };

  const lowPriorityStyle = {
    backgroundColor: '#08bbe8ff',
    color: '#151112ff',
  };

  const getDueDateColor = (dueDateStr) => {
    if (!dueDateStr) return '';
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dueDate = new Date(dueDateStr);
    dueDate.setHours(0, 0, 0, 0);

    const diffTime = dueDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return '#dc3545';       
    if (diffDays === 1) return '#d8b0ff';       
    if (diffDays > 1 && diffDays <= 7) return '#ffc107';  
    if (diffDays > 7 && diffDays <= 30) return '#0d6efd'; 

    return ''; 
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'No due date';
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    const date = new Date(dateStr);
    return isNaN(date) ? dateStr : date.toLocaleDateString(undefined, options);
  };

  const progressBarContainer = {
    width: '100%',
    backgroundColor: '#e9ecef',
    borderRadius: '0.25rem',
    overflow: 'hidden',
    height: '1rem',
    marginBottom: '0.5rem',
  };

  const progressBarStyle = (progress) => ({
    width: `${progress}%`,
    height: '100%',
    backgroundColor:
      progress < 40 ? '#e90920ff' : progress < 70 ? '#e1b01fff' : '#0bec83ff',
    transition: 'width 0.5s ease-in-out',
  });

  return (
    <section className="mt-4" aria-label="Task List">
      {tasks.length === 0 ? (
        <p className="text-muted">No tasks available</p>
      ) : (
        tasks.map(
          ({
            id,
            title,
            description,
            due_date,
            priority,
            is_completed,
            difficulty_level,
            progress = 0,
            category,
          }) => {
            const normalizedPriority = (priority || '').toLowerCase();

            let priorityStyle;
            if (normalizedPriority === 'high') {
              priorityStyle = highPriorityStyle;
            } else if (normalizedPriority === 'medium') {
              priorityStyle = mediumPriorityStyle;
            } else {
              priorityStyle = lowPriorityStyle;
            }

            const dueDateColor = getDueDateColor(due_date);

            const cardStyle = {
              ...priorityStyle,
              borderLeft: dueDateColor ? `6px solid ${dueDateColor}` : 'none',
            };

            return (
              <article key={id} className="card mb-3 shadow-sm" style={cardStyle}>
                <div className="card-body">
                  <h5 className="card-title">
                    {title}{' '}
                    <small className="text-muted" style={{cardStyle}}>
                      (ID: {id})
                    </small>
                  </h5>

                  <h6 className="card-subtitle mb-2">
                    Due: {formatDate(due_date)}
                  </h6>
                  <p className="card-text">{description}</p>

                  {difficulty_level && (
                    <p className="mb-1">
                      <strong>Difficulty:</strong> {difficulty_level}
                    </p>
                  )}

                  {category && (
                    <p className="mb-1">
                      <strong>Category:</strong> {category}
                    </p>
                  )}

                  <div
                    style={progressBarContainer}
                    aria-label={`Progress: ${progress}%`}
                  >
                    <div style={progressBarStyle(progress)}></div>
                  </div>
                  <small>Progress: {progress}%</small>

                  <div className="form-check mt-3">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      checked={is_completed}
                      onChange={(e) => onToggleComplete(id, e.target.checked)}
                      id={`task-${id}`}
                      aria-label={`Mark task "${title}" as completed`}
                      disabled={progress !== 100} 
                    />
                    <label className="form-check-label" htmlFor={`task-${id}`}>
                      Completed
                    </label>
                  </div>

                  <button
                    type="button"
                    onClick={() => onDelete(id)}
                    className={`btn btn-sm mt-3 ${
                      normalizedPriority === 'high' ? 'btn-light' : 'btn-dark'
                    }`}
                    aria-label={`Delete task: ${title}`}
                  >
                    Delete
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      onEdit({
                        id,
                        title,
                        description,
                        due_date,
                        priority,
                        is_completed,
                        difficulty_level,
                        progress,
                        category,
                      })
                    }
                    className="btn btn-sm btn-warning mt-3 ms-2"
                    aria-label={`Edit task: ${title}`}
                  >
                    Update
                  </button>
                </div>
              </article>
            );
          }
        )
      )}
    </section>
  );
};

export default TaskList;
