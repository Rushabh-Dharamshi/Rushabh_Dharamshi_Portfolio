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
    if (error.code === 'ER_DUP_ENTRY') {
      return res.status(409).json({ error: 'Project with that name already exists' });
    }
    next(error);
  }
});

module.exports = router;
