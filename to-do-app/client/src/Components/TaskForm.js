import React from 'react';
import { Form, Button } from 'react-bootstrap';
import '../App.css'; 


function TaskForm({ newTask, setNewTask, onAdd }) {
  const handleSubmit = (e) => {
    e.preventDefault();
    onAdd(); 
  };

  return (
    <Form onSubmit={handleSubmit} className="mb-4" aria-label="Add New Task Form">

      {/* Title */}
      <Form.Group controlId="title" className="mb-3">
        <Form.Label>Title</Form.Label>
        <Form.Control
          className="styled-input"
          type="text"
          placeholder="Enter title"
          value={newTask.title}
          onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
          required
          aria-required="true"
          maxLength={255}
          autoComplete="off"
        />  
      </Form.Group>

      {/* Priority */}
      <Form.Group controlId="priority" className="mb-3">
        <Form.Label>Priority</Form.Label>
        <Form.Select
          className="styled-input"
          value={newTask.priority}
          onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
          required
          aria-required="true"
        >
          <option value="" disabled>
            Select priority
          </option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </Form.Select>
      </Form.Group>

      {/* Difficulty Level */}
      <Form.Group controlId="difficulty_level" className="mb-3">
        <Form.Label>Difficulty Level</Form.Label>
        <Form.Select
          className="styled-input"
          value={newTask.difficulty_level || ''}
          onChange={(e) => setNewTask({ ...newTask, difficulty_level: e.target.value })}
        >
          <option value="" disabled>
            Select difficulty
          </option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </Form.Select>
      </Form.Group>

      {/* Progress */}
      <Form.Group controlId="progress" className="mb-3">
        <Form.Label>Progress (%)</Form.Label>
        <Form.Control
          className="styled-input"
          type="number"
          min={0}
          max={100}
          value={newTask.progress ?? 0}
          onChange={(e) =>
            setNewTask({
              ...newTask,
              progress: Math.min(100, Math.max(0, Number(e.target.value))),
            })
          }
          placeholder="0"
        />
      </Form.Group>

      {/* Category */}
      <Form.Group controlId="category" className="mb-3">
        <Form.Label>Category</Form.Label>
        <Form.Control
          className="styled-input"
          type="text"
          placeholder="Enter category"
          value={newTask.category || ''}
          onChange={(e) => setNewTask({ ...newTask, category: e.target.value })}
          maxLength={100}
          autoComplete="off"
        />
      </Form.Group>

      {/* Description */}
      <Form.Group controlId="description" className="mb-3">
        <Form.Label>Description</Form.Label>
        <Form.Control
          className="styled-input"
          as="textarea"
          rows={1}
          placeholder="Enter description"
          value={newTask.description}
          onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
          required
          aria-required="true"
          maxLength={1000}
        />
      </Form.Group>

      {/* Due Date */}
      <Form.Group controlId="due_date" className="mb-3">
        <Form.Label>Due Date</Form.Label>
        <Form.Control
          className="styled-input"
          type="date"
          value={newTask.due_date}
          onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
          required
          aria-required="true"
          min={new Date().toISOString().split('T')[0]}
        />
      </Form.Group>

      <Button
        variant="primary"
        type="submit"
        disabled={
          !newTask.title || !newTask.priority || !newTask.description || !newTask.due_date
        }
      >
        Add Task
      </Button>
    </Form>
  );
}

export default TaskForm;
