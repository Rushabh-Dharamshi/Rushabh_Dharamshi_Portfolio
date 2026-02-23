const express = require('express');
const projectRepository = require('../repositories/projectRepository');

const router = express.Router();

router.get('/', async (req, res, next) => {
  try {
    const projects = await projectRepository.listProjects();
    res.json(projects);
  } catch (error) {
    next(error);
  }
});

router.post('/', async (req, res, next) => {
  try {
    const name = String(req.body.name || '').trim();
    const description = String(req.body.description || '').trim();

    if (!name) {
      return res.status(400).json({ error: 'Project name is required' });
    }

    const project = await projectRepository.createProject({ name, description });
    res.status(201).json(project);
  } catch (error) {
    if (error.code === 'ER_DUP_ENTRY' || error.code === 'PROJECT_DUPLICATE') {
      return res.status(409).json({ error: 'Project with that name already exists' });
    }
    next(error);
  }
});

router.delete('/:id', async (req, res, next) => {
  try {
    const projectId = Number(req.params.id);
    if (!Number.isFinite(projectId) || projectId <= 0) {
      return res.status(400).json({ error: 'Invalid project id' });
    }

    const deleted = await projectRepository.deleteProject(projectId);
    res.json({ message: 'Project deleted', project: deleted });
  } catch (error) {
    if (error.code === 'PROJECT_NOT_FOUND') {
      return res.status(404).json({ error: 'Project not found' });
    }

    if (error.code === 'PROJECT_HAS_TASKS' || error.code === 'PROJECT_PROTECTED') {
      return res.status(409).json({ error: error.message });
    }

    next(error);
  }
});

module.exports = router;
