import React, { useEffect, useState } from 'react';
import TaskForm from './Components/TaskForm';
import TaskList from './Components/TaskList';
import TaskStats from './Components/TaskStats';
import { Container, Form, Button } from 'react-bootstrap';

function App() {
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    due_date: '',
    priority: '',
    difficulty_level: '',
    progress: 0,
    category: '',
  });

  const [searchId, setSearchId] = useState('');
  const [sortOption, setSortOption] = useState('date');
  const [successMessage, setSuccessMessage] = useState('');
  const [editTask, setEditTask] = useState(null);

  const [showTodayOnly, setShowTodayOnly] = useState(false);

  const styles = {
    fieldRow: {
      display: 'flex',
      alignItems: 'center',
      marginBottom: '1rem',
    },
    label: {
      width: '120px',
      fontWeight: '600',
      fontSize: '1rem',
      color: '#333',
    },
    input: {
      flex: 1,
      padding: '0.4rem 0.6rem',
      fontSize: '1rem',
      borderRadius: '4px',
      border: '1px solid #ccc',
      boxSizing: 'border-box',
    },
  };

  useEffect(() => {
    fetch('/tasks')
      .then((res) => res.json())
      .then((data) => setTasks(data));
  }, []);

  const handleAddTask = () => {
    const {
      title,
      description,
      due_date,
      priority,
      difficulty_level,
      progress,
    } = newTask;

    if (!title || !description || !due_date || !priority || !difficulty_level || progress === '') {
      alert('Please fill in all required fields');
      return;
    }

    fetch('/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newTask),
    })
      .then((res) => res.json())
      .then((data) => {
        setTasks([...tasks, { ...newTask, id: data.taskId, is_completed: false }]);
        setNewTask({
          title: '',
          description: '',
          due_date: '',
          priority: '',
          difficulty_level: '',
          progress: 0,
          category: '',
        });
        setSuccessMessage('Task added successfully!');
        setTimeout(() => setSuccessMessage(''), 3000);
      })
      .catch((error) => {
        console.error('Error adding task:', error);
        alert('Failed to add task');
      });
  };

  const handleToggleComplete = (id, is_completed) => {
    fetch(`/tasks/${id}/completed`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_completed }),
    }).then(() => {
      setTasks(tasks.map((task) => (task.id === id ? { ...task, is_completed } : task)));
    });
  };

  const handleDelete = (id) => {
    fetch(`/tasks/${id}`, { method: 'DELETE' }).then(() => {
      setTasks(tasks.filter((task) => task.id !== id));
    });
  };

  const handleEdit = (updatedTask) => {
    setNewTask(updatedTask);
    setTasks(tasks.filter((task) => task.id !== updatedTask.id));
  };

  const handleUpdateTask = (e) => {
    e.preventDefault();
    const {
      title,
      description,
      due_date,
      priority,
      difficulty_level,
      progress,
    } = editTask;

    if (!title || !description || !due_date || !priority || !difficulty_level || progress === '') {
      alert('Please fill in all required fields');
      return;
    }

    fetch(`/tasks/${editTask.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editTask),
    })
      .then((res) => res.json())
      .then(() => {
        setTasks(tasks.map((task) => (task.id === editTask.id ? editTask : task)));
        setEditTask(null);
        setSuccessMessage('Task updated successfully!');
        setTimeout(() => setSuccessMessage(''), 3000);
      })
      .catch((error) => {
        console.error('Error updating task:', error);
        alert('Failed to update task');
      });
  };

  const filteredTasks = searchId
    ? tasks.filter((task) => task.id.toString() === searchId.toString())
    : tasks;

  const today = new Date();
  const tasksDueToday = tasks.filter((task) => {
    if (task.is_completed) return false;
    const dueDate = new Date(task.due_date);
    const diffDays = Math.floor((dueDate - today) / (1000 * 60 * 60 * 24));
    return diffDays < 0; 
  });

  const displayedTasks = showTodayOnly ? tasksDueToday : filteredTasks;

  const sortedTasks = [...displayedTasks].sort((a, b) => {
    if (sortOption === 'date') {
      return new Date(a.due_date) - new Date(b.due_date);
    } else if (sortOption === 'priority') {
      const priorityOrder = { high: 1, medium: 2, low: 3 };
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    } else if (sortOption === 'difficulty') {
      const difficultyOrder = { hard: 1, medium: 2, easy: 3 };
      return difficultyOrder[a.difficulty_level] - difficultyOrder[b.difficulty_level];
    } else if (sortOption === 'category') {
      return (a.category || '').localeCompare(b.category || '');
    } else if (sortOption === 'completed') {
      return b.is_completed - a.is_completed;
    } else if (sortOption === 'incomplete') {
      return a.is_completed - b.is_completed;
    } else if (sortOption === 'progress-asc') {
      return a.progress - b.progress;
    } else if (sortOption === 'progress-desc') {
      return b.progress - a.progress;
    } else if (sortOption === 'id') {
      return a.id - b.id;
    }
    return 0;
  });

  return (
    <div style={{ padding: '2rem', position: 'relative' }}>
      {/* Notification Button */}
      <div style={{ position: 'fixed', top: 20, right: 20, zIndex: 1000 }}>
        <button
          onClick={() => setShowTodayOnly(!showTodayOnly)}
          style={{
            position: 'relative',
            fontSize: '1.5rem',
            fontWeight: 'bold',
            borderRadius: '50%',
            width: '40px',
            height: '40px',
            border: 'none',
            backgroundColor: showTodayOnly ? '#dc3545' : '#ffc107',
            color: '#fff',
            cursor: 'pointer',
          }}
          aria-label="Tasks due today"
          title="Tasks due today"
        >
          !
          {tasksDueToday.length > 0 && (
            <span
              style={{
                position: 'absolute',
                top: '-8px',
                right: '-8px',
                background: 'red',
                color: 'white',
                borderRadius: '50%',
                padding: '2px 6px',
                fontSize: '0.8rem',
                fontWeight: 'bold',
                lineHeight: 1,
              }}
            >
              {tasksDueToday.length}
            </span>
          )}
        </button>
      </div>

      <h1><b><center><u>To-Do List</u></center></b></h1>

      {successMessage && <div className="alert alert-success">{successMessage}</div>}

      <TaskStats tasks={tasks} />

      {/* Add New Task Form */}
      <TaskForm newTask={newTask} setNewTask={setNewTask} onAdd={handleAddTask} />

      {/* Sort Options */}
      <div className="mb-3">
        <label htmlFor="sort" className="form-label"><strong>Sort by:</strong></label>
        <select
          id="sort"
          className="form-select"
          value={sortOption}
          onChange={(e) => setSortOption(e.target.value)}
        >
          <option value="date">Due Date</option>
          <option value="priority">Priority</option>
          <option value="difficulty">Difficulty</option>
          <option value="category">Category</option>
          <option value="completed">Completed First</option>
          <option value="incomplete">Incomplete First</option>
          <option value="progress-asc">Progress (Ascending)</option>
          <option value="progress-desc">Progress (Descending)</option>
          <option value="id">Task ID</option>
        </select>
      </div>

      {/* Search by ID */}
      <Form className="mb-3" aria-label="Search by Task ID">
        <Form.Control
          type="number"
          placeholder="Search by Task ID"
          value={searchId}
          onChange={(e) => setSearchId(e.target.value)}
          min={1}
        />
        <Button
          variant="secondary"
          onClick={() => setSearchId('')}
          className="mt-2"
          disabled={!searchId}
        >
          Clear Search
        </Button>
      </Form>

      {/* Task List */}
      <TaskList
        tasks={sortedTasks}
        onToggleComplete={handleToggleComplete}
        onDelete={handleDelete}
        onEdit={(task) => setEditTask(task)}
        styles={styles}
      />

      {/* Edit Task Form */}
      {editTask && (
        <form onSubmit={handleUpdateTask} style={{ marginTop: '2rem', maxWidth: '500px' }}>
          <h3>Edit Task</h3>

          {/* Title */}
          <div style={styles.fieldRow}>
            <label style={styles.label}>Title:</label>
            <input
              type="text"
              value={editTask.title}
              onChange={(e) => setEditTask({ ...editTask, title: e.target.value })}
              required
              maxLength={255}
              placeholder="Title"
              style={styles.input}
            />
          </div>

          {/* Priority */}
          <div style={styles.fieldRow}>
            <label style={styles.label}>Priority:</label>
            <select
              value={editTask.priority}
              onChange={(e) => setEditTask({ ...editTask, priority: e.target.value })}
              required
              style={styles.input}
            >
              <option value="">Select priority</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          {/* Difficulty */}
          <div style={styles.fieldRow}>
            <label style={styles.label}>Difficulty:</label>
            <select
              value={editTask.difficulty_level}
              onChange={(e) => setEditTask({ ...editTask, difficulty_level: e.target.value })}
              required
              style={styles.input}
            >
              <option value="">Select difficulty</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>

          {/* Progress */}
          <div style={styles.fieldRow}>
            <label style={styles.label}>Progress (%):</label>
            <input
              type="number"
              min="0"
              max="100"
              value={editTask.progress}
              onChange={(e) => setEditTask({ ...editTask, progress: Number(e.target.value) })}
              required
              style={styles.input}
            />
          </div>

          {/* Description */}
          <div style={styles.fieldRow}>
            <label style={styles.label}>Description:</label>
            <textarea
              value={editTask.description}
              onChange={(e) => setEditTask({ ...editTask, description: e.target.value })}
              required
              maxLength={1000}
              placeholder="Description"
              style={{ ...styles.input, height: '80px', resize: 'vertical' }}
            />
          </div>

          {/* Due Date */}
          <div style={styles.fieldRow}>
            <label style={styles.label}>Due Date:</label>
            <input
              type="date"
              value={editTask.due_date}
              onChange={(e) => setEditTask({ ...editTask, due_date: e.target.value })}
              required
              min={new Date().toISOString().split('T')[0]}
              style={styles.input}
            />
          </div>

          {/* Category */}
          <div style={styles.fieldRow}>
            <label style={styles.label}>Category:</label>
            <input
              type="text"
              value={editTask.category}
              onChange={(e) => setEditTask({ ...editTask, category: e.target.value })}
              placeholder="Category"
              style={styles.input}
            />
          </div>

          <div style={{ marginTop: '1rem', textAlign: 'right' }}>
            <button type="submit" className="btn btn-primary" style={{ marginRight: '0.5rem' }}>
              Save
            </button>
            <button type="button" onClick={() => setEditTask(null)} className="btn btn-secondary">
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default App;
