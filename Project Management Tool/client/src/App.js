import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Col, Container, Form, Row, Spinner } from 'react-bootstrap';
import TaskForm from './Components/TaskForm';
import TaskList from './Components/TaskList';
import TaskStats from './Components/TaskStats';
import KanbanBoard from './Components/KanbanBoard';
import MlInsights from './Components/MlInsights';
import RagAssistant from './Components/RagAssistant';
import './App.css';
import { apiUrl } from './config/api';

const defaultTask = () => ({
  title: '',
  description: '',
  due_date: new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10),
  priority: 'medium',
  difficulty_level: 'medium',
  progress: 0,
  category: '',
  project_id: null,
  status: 'backlog',
  assignee: '',
  estimated_hours: '',
  is_completed: false,
});

function normalizeTaskForForm(task) {
  return {
    ...defaultTask(),
    ...task,
    due_date: task?.due_date ? new Date(task.due_date).toISOString().slice(0, 10) : '',
    estimated_hours: task?.estimated_hours ?? '',
    project_id: task?.project_id ?? null,
    status: task?.status || (task?.is_completed ? 'done' : 'backlog'),
  };
}

function App() {
  const [tasks, setTasks] = useState([]);
  const [projects, setProjects] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [riskData, setRiskData] = useState(null);

  const [taskDraft, setTaskDraft] = useState(defaultTask());
  const [editingTaskId, setEditingTaskId] = useState(null);

  const [viewMode, setViewMode] = useState('list');
  const [sortBy, setSortBy] = useState('due_date');
  const [search, setSearch] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [newProjectName, setNewProjectName] = useState('');

  const [loading, setLoading] = useState(true);
  const [riskLoading, setRiskLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const fetchTasks = useCallback(async (projectId = '') => {
    const query = projectId ? `?project_id=${projectId}` : '';
    const response = await fetch(apiUrl(`/tasks${query}`));
    if (!response.ok) {
      throw new Error('Failed to fetch tasks');
    }
    return response.json();
  }, []);

  const fetchProjects = useCallback(async () => {
    const response = await fetch(apiUrl('/projects'));
    if (!response.ok) {
      throw new Error('Failed to fetch projects');
    }
    return response.json();
  }, []);

  const fetchAnalytics = useCallback(async (projectId = '') => {
    const query = projectId ? `?project_id=${projectId}` : '';
    const response = await fetch(apiUrl(`/api/analytics/overview${query}`));
    if (!response.ok) {
      throw new Error('Failed to fetch analytics');
    }
    return response.json();
  }, []);

  const refreshRisk = useCallback(async () => {
    setRiskLoading(true);
    try {
      const response = await fetch(apiUrl('/api/ml/risk'));
      if (!response.ok) {
        throw new Error('Failed to fetch risk insights');
      }
      const data = await response.json();
      setRiskData(data);
    } catch (riskError) {
      setError(riskError.message);
    } finally {
      setRiskLoading(false);
    }
  }, []);

  const loadWorkspace = useCallback(async (projectId = '') => {
    setLoading(true);
    setError('');

    try {
      const [taskRows, projectRows, analyticsData] = await Promise.all([
        fetchTasks(projectId),
        fetchProjects(),
        fetchAnalytics(projectId),
      ]);

      setTasks(taskRows);
      setProjects(projectRows);
      setAnalytics(analyticsData);
    } catch (workspaceError) {
      setError(workspaceError.message);
    } finally {
      setLoading(false);
    }
  }, [fetchAnalytics, fetchProjects, fetchTasks]);

  useEffect(() => {
    loadWorkspace();
    refreshRisk();
  }, [loadWorkspace, refreshRisk]);

  const clearForm = () => {
    setEditingTaskId(null);
    setTaskDraft(defaultTask());
  };

  const runPostMutationRefresh = async () => {
    await Promise.all([loadWorkspace(selectedProjectId), refreshRisk()]);
  };

  const handleSubmitTask = async (event) => {
    event.preventDefault();
    setError('');

    if (taskDraft.status === 'done' && Number(taskDraft.progress) !== 100) {
      setError('Status can be set to done only when progress is 100.');
      return;
    }

    const endpoint = editingTaskId ? `/tasks/${editingTaskId}` : '/tasks';
    const method = editingTaskId ? 'PUT' : 'POST';

    try {
      const response = await fetch(apiUrl(endpoint), {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskDraft),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Request failed');
      }

      setMessage(editingTaskId ? 'Work item updated.' : 'Work item created.');
      clearForm();
      await runPostMutationRefresh();
      setTimeout(() => setMessage(''), 2500);
    } catch (submitError) {
      setError(submitError.message);
    }
  };

  const handleDeleteTask = async (id) => {
    try {
      const response = await fetch(apiUrl(`/tasks/${id}`), { method: 'DELETE' });
      if (!response.ok) {
        throw new Error('Delete failed');
      }
      await runPostMutationRefresh();
    } catch (deleteError) {
      setError(deleteError.message);
    }
  };

  const handleToggleComplete = async (id, isCompleted) => {
    const targetTask = tasks.find((task) => task.id === id);
    if (isCompleted && targetTask && Number(targetTask.progress) !== 100) {
      setError('A task can be marked completed only when progress is 100.');
      return;
    }

    try {
      const response = await fetch(apiUrl(`/tasks/${id}/completed`), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_completed: isCompleted }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to update completion state');
      }

      await runPostMutationRefresh();
    } catch (toggleError) {
      setError(toggleError.message);
    }
  };

  const handleStatusChange = async (id, status) => {
    const targetTask = tasks.find((task) => task.id === id);
    if (!targetTask) {
      return;
    }

    if (status === 'done' && Number(targetTask.progress) !== 100) {
      setError('Status can be set to done only when progress is 100.');
      return;
    }

    setTasks((prev) => prev.map((task) => (task.id === id ? { ...task, status } : task)));

    try {
      const response = await fetch(apiUrl(`/tasks/${id}/status`), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to update status');
      }

      await Promise.all([fetchAnalytics(selectedProjectId).then(setAnalytics), refreshRisk()]);
    } catch (statusError) {
      setError(statusError.message);
      await loadWorkspace(selectedProjectId);
    }
  };
  const handleCreateProject = async () => {
    if (!newProjectName.trim()) {
      return;
    }

    try {
      const response = await fetch(apiUrl('/projects'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newProjectName.trim() }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to create project');
      }

      setNewProjectName('');
      setProjects((prev) => [...prev, data]);
      setMessage('Project created.');
      setTimeout(() => setMessage(''), 2500);
    } catch (projectError) {
      setError(projectError.message);
    }
  };

  const handleDeleteProject = async () => {
    const projectId = Number(selectedProjectId);
    if (!Number.isFinite(projectId) || projectId <= 0) {
      setError('Select a project to delete.');
      return;
    }

    const project = projects.find((item) => Number(item.id) === projectId);
    const projectName = project?.name || `#${projectId}`;

    if (!window.confirm(`Delete project "${projectName}"? This only works when the project has no tasks.`)) {
      return;
    }

    try {
      const response = await fetch(apiUrl(`/projects/${projectId}`), {
        method: 'DELETE',
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to delete project');
      }

      setSelectedProjectId('');
      setMessage(`Project "${projectName}" deleted.`);
      setTimeout(() => setMessage(''), 2500);
      await Promise.all([loadWorkspace(''), refreshRisk()]);
    } catch (projectError) {
      setError(projectError.message);
    }
  };

  const overdueCount = useMemo(() => {
    const now = new Date();
    return tasks.filter((task) => !task.is_completed && new Date(task.due_date) < now).length;
  }, [tasks]);


  const filteredAndSorted = useMemo(() => {
    const needle = search.toLowerCase().trim();

    const filtered = tasks.filter((task) => {
      if (!needle) {
        return true;
      }

      return (
        String(task.id).includes(needle) ||
        task.title.toLowerCase().includes(needle) ||
        (task.description || '').toLowerCase().includes(needle) ||
        (task.assignee || '').toLowerCase().includes(needle)
      );
    });

    const priorityRank = { high: 0, medium: 1, low: 2 };

    return filtered.sort((left, right) => {
      if (sortBy === 'priority') {
        return (priorityRank[left.priority] ?? 99) - (priorityRank[right.priority] ?? 99);
      }
      if (sortBy === 'progress') {
        return Number(right.progress) - Number(left.progress);
      }
      if (sortBy === 'status') {
        return String(left.status).localeCompare(String(right.status));
      }
      return new Date(left.due_date) - new Date(right.due_date);
    });
  }, [tasks, search, sortBy]);
  const selectedProject = useMemo(
    () => projects.find((project) => Number(project.id) === Number(selectedProjectId)) || null,
    [projects, selectedProjectId]
  );

  const analyticsScopeLabel = selectedProject
    ? `Specific Project: ${selectedProject.name}`
    : 'All Projects';
  const assistantContext = useMemo(() => ({
    selected_project_id: selectedProjectId ? Number(selectedProjectId) : null,
    active_view: viewMode,
    visible_task_count: filteredAndSorted.length,
    overdue_count: overdueCount,
  }), [selectedProjectId, viewMode, filteredAndSorted.length, overdueCount]);
  const startEdit = (task) => {
    setEditingTaskId(task.id);
    setTaskDraft(normalizeTaskForForm(task));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const onProjectFilterChange = async (nextProjectId) => {
    setSelectedProjectId(nextProjectId);
    await loadWorkspace(nextProjectId);
  };

  return (
    <div className="app-shell">
      <Container fluid="xl" className="py-4">
        <header className="top-banner">
          <div>
            <h1>Project Management Tool</h1>
            <p>Portfolio-grade project management with analytics, ML risk intelligence, and a Vertex AI RAG assistant.</p>
          </div>
          <div className="banner-badges">
            <Badge bg="dark">{tasks.length} items</Badge>
            <Badge bg={overdueCount ? 'danger' : 'success'}>{overdueCount} overdue</Badge>
          </div>
        </header>

        {message && <Alert variant="success">{message}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}

        {loading ? (
          <div className="loading-wrap">
            <Spinner animation="border" />
          </div>
        ) : (
          <>
            <TaskStats analytics={analytics} scopeLabel={analyticsScopeLabel} />

            <section className="panel-card controls-row">
              <Row className="g-3 align-items-end">
                <Col md={3}>
                  <Form.Label>Project Filter</Form.Label>
                  <Form.Select
                    className="field-input"
                    value={selectedProjectId}
                    onChange={(event) => onProjectFilterChange(event.target.value)}
                  >
                    <option value="">All Projects</option>
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>{project.name}</option>
                    ))}
                  </Form.Select>
                  <div className="mt-2">
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={handleDeleteProject}
                      disabled={!selectedProjectId}
                    >
                      Delete Selected Project
                    </Button>
                  </div>
                </Col>
                <Col md={3}>
                  <Form.Label>Search</Form.Label>
                  <Form.Control
                    className="field-input"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="ID, title, description, assignee"
                  />
                </Col>
                <Col md={2}>
                  <Form.Label>Sort By</Form.Label>
                  <Form.Select className="field-input" value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                    <option value="due_date">Due Date</option>
                    <option value="priority">Priority</option>
                    <option value="progress">Progress</option>
                    <option value="status">Status</option>
                  </Form.Select>
                </Col>
                <Col md={2}>
                  <Form.Label>View</Form.Label>
                  <div className="view-toggle">
                    <Button
                      variant={viewMode === 'list' ? 'dark' : 'outline-dark'}
                      onClick={() => setViewMode('list')}
                    >
                      List
                    </Button>
                    <Button
                      variant={viewMode === 'kanban' ? 'dark' : 'outline-dark'}
                      onClick={() => setViewMode('kanban')}
                    >
                      Kanban
                    </Button>
                  </div>
                </Col>
                <Col md={2}>
                  <Form.Label>New Project</Form.Label>
                  <div className="project-create">
                    <Form.Control
                      className="field-input"
                      value={newProjectName}
                      onChange={(event) => setNewProjectName(event.target.value)}
                      placeholder="Project name"
                    />
                    <Button className="primary-btn" onClick={handleCreateProject}>Add</Button>
                  </div>
                </Col>
              </Row>
            </section>

            <Row className="g-4 mt-1">
              <Col lg={8}>
                <TaskForm
                  task={taskDraft}
                  setTask={setTaskDraft}
                  projects={projects}
                  onSubmit={handleSubmitTask}
                  isEditing={Boolean(editingTaskId)}
                />
                {editingTaskId && (
                  <div className="mt-2">
                    <Button variant="outline-secondary" onClick={clearForm}>Cancel Editing</Button>
                  </div>
                )}

                {viewMode === 'list' ? (
                  <TaskList
                    tasks={filteredAndSorted}
                    onToggleComplete={handleToggleComplete}
                    onDelete={handleDeleteTask}
                    onEdit={startEdit}
                    onStatusChange={handleStatusChange}
                  />
                ) : (
                  <KanbanBoard tasks={filteredAndSorted} onStatusChange={handleStatusChange} onEdit={startEdit} />
                )}
              </Col>

              <Col lg={4}>
                <MlInsights riskData={riskData} onRefresh={refreshRisk} loading={riskLoading} />
                <RagAssistant assistantContext={assistantContext} />
              </Col>
            </Row>
          </>
        )}
      </Container>
    </div>
  );
}

export default App;








