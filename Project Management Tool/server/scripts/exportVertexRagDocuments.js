'use strict';

const fs = require('fs/promises');
const path = require('path');
const pool = require('../src/db/pool');

function getArgValue(flagName) {
  const index = process.argv.indexOf(flagName);
  if (index === -1) {
    return undefined;
  }

  return process.argv[index + 1];
}

function toIso(value) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date.toISOString();
}

function sanitizeFileName(value) {
  return String(value)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'untitled';
}

function buildTaskDocument(task) {
  const lines = [
    `Task #${task.id}`,
    `Project: ${task.project_name || 'Unassigned'} (project_id=${task.project_id || 'none'})`,
    `Title: ${task.title}`,
    `Description: ${task.description}`,
    `Status: ${task.status}`,
    `Progress: ${task.progress}%`,
    `Priority: ${task.priority}`,
    `Difficulty: ${task.difficulty_level}`,
    `Assignee: ${task.assignee || 'Unassigned'}`,
    `Category: ${task.category || 'Unspecified'}`,
    `Estimated Hours: ${task.estimated_hours ?? 'n/a'}`,
    `Due Date: ${task.due_date}`,
    `Completed: ${task.is_completed ? 'yes' : 'no'}`,
    `Created At: ${toIso(task.created_at) || task.created_at}`,
    `Updated At: ${toIso(task.updated_at) || task.updated_at}`,
  ];

  return {
    id: `task-${task.id}`,
    type: 'task',
    content: lines.join('\n'),
    metadata: {
      table: 'tasks',
      task_id: task.id,
      project_id: task.project_id,
      project_name: task.project_name || 'Unassigned',
      status: task.status,
      priority: task.priority,
      assignee: task.assignee || 'Unassigned',
      updated_at: toIso(task.updated_at),
    },
  };
}

function buildProjectDocument(project) {
  const lines = [
    `Project #${project.id}`,
    `Name: ${project.name}`,
    `Description: ${project.description || 'n/a'}`,
    `Total Tasks: ${project.total_tasks}`,
    `Backlog: ${project.backlog_tasks}`,
    `In Progress: ${project.in_progress_tasks}`,
    `Blocked: ${project.blocked_tasks}`,
    `Done: ${project.done_tasks}`,
    `Average Progress: ${project.avg_progress ?? 0}%`,
    `Created At: ${toIso(project.created_at) || project.created_at}`,
  ];

  return {
    id: `project-${project.id}`,
    type: 'project',
    content: lines.join('\n'),
    metadata: {
      table: 'projects',
      project_id: project.id,
      project_name: project.name,
      total_tasks: Number(project.total_tasks || 0),
      done_tasks: Number(project.done_tasks || 0),
      updated_at: toIso(project.latest_task_update || project.created_at),
    },
  };
}

function buildPortfolioSummary(tasks) {
  const total = tasks.length;
  const done = tasks.filter((task) => task.status === 'done').length;
  const blocked = tasks.filter((task) => task.status === 'blocked').length;
  const overdue = tasks.filter((task) => {
    if (!task.due_date || task.status === 'done') {
      return false;
    }

    const dueDate = new Date(task.due_date);
    const today = new Date();
    dueDate.setHours(0, 0, 0, 0);
    today.setHours(0, 0, 0, 0);
    return dueDate < today;
  }).length;

  const content = [
    'Portfolio Summary',
    `Total tasks: ${total}`,
    `Done tasks: ${done}`,
    `Blocked tasks: ${blocked}`,
    `Overdue tasks: ${overdue}`,
  ].join('\n');

  return {
    id: 'portfolio-summary',
    type: 'summary',
    content,
    metadata: {
      table: 'derived',
      total_tasks: total,
      done_tasks: done,
      blocked_tasks: blocked,
      overdue_tasks: overdue,
      generated_at: new Date().toISOString(),
    },
  };
}

async function fetchTasks(updatedSince) {
  const values = [];
  let whereClause = '';

  if (updatedSince) {
    whereClause = 'WHERE t.updated_at >= ?';
    values.push(updatedSince);
  }

  const [rows] = await pool.query(
    `SELECT
      t.id,
      t.title,
      t.description,
      t.due_date,
      t.priority,
      t.difficulty_level,
      t.progress,
      t.category,
      t.is_completed,
      t.project_id,
      t.status,
      t.assignee,
      t.estimated_hours,
      t.created_at,
      t.updated_at,
      p.name AS project_name
     FROM tasks t
     LEFT JOIN projects p ON p.id = t.project_id
     ${whereClause}
     ORDER BY t.updated_at DESC`,
    values
  );

  return rows;
}

async function fetchProjectSnapshots(updatedSince) {
  const values = [];
  let whereClause = '';

  if (updatedSince) {
    whereClause = 'WHERE p.created_at >= ? OR t.updated_at >= ?';
    values.push(updatedSince, updatedSince);
  }

  const [rows] = await pool.query(
    `SELECT
      p.id,
      p.name,
      p.description,
      p.created_at,
      MAX(t.updated_at) AS latest_task_update,
      COUNT(t.id) AS total_tasks,
      SUM(CASE WHEN t.status = 'backlog' THEN 1 ELSE 0 END) AS backlog_tasks,
      SUM(CASE WHEN t.status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress_tasks,
      SUM(CASE WHEN t.status = 'blocked' THEN 1 ELSE 0 END) AS blocked_tasks,
      SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) AS done_tasks,
      ROUND(AVG(CASE WHEN t.progress IS NULL THEN 0 ELSE t.progress END), 2) AS avg_progress
     FROM projects p
     LEFT JOIN tasks t ON t.project_id = p.id
     ${whereClause}
     GROUP BY p.id, p.name, p.description, p.created_at
     ORDER BY p.id ASC`,
    values
  );

  return rows;
}

async function ensureOutputDirs(rootDir) {
  await fs.mkdir(rootDir, { recursive: true });
  await fs.rm(path.join(rootDir, 'task_docs'), { recursive: true, force: true });
  await fs.rm(path.join(rootDir, 'project_docs'), { recursive: true, force: true });
  await fs.rm(path.join(rootDir, 'summary_docs'), { recursive: true, force: true });
  await fs.mkdir(path.join(rootDir, 'task_docs'), { recursive: true });
  await fs.mkdir(path.join(rootDir, 'project_docs'), { recursive: true });
  await fs.mkdir(path.join(rootDir, 'summary_docs'), { recursive: true });
}

async function writeDocuments(rootDir, docs) {
  const jsonlPath = path.join(rootDir, 'vertex_rag_documents.jsonl');
  const manifestPath = path.join(rootDir, 'vertex_rag_manifest.json');

  const jsonlLines = [];

  for (const doc of docs) {
    const categoryDir = doc.type === 'project'
      ? 'project_docs'
      : doc.type === 'task'
        ? 'task_docs'
        : doc.type === 'summary'
          ? 'summary_docs'
          : null;
    let sourceFile = null;

    if (categoryDir) {
      const fileName = `${sanitizeFileName(doc.id)}.txt`;
      sourceFile = path.join(rootDir, categoryDir, fileName);
      await fs.writeFile(sourceFile, doc.content, 'utf8');
    }

    jsonlLines.push(JSON.stringify({
      id: doc.id,
      content: doc.content,
      metadata: doc.metadata,
      source_file: sourceFile ? path.relative(rootDir, sourceFile).replace(/\\/g, '/') : null,
    }));
  }

  await fs.writeFile(jsonlPath, `${jsonlLines.join('\n')}\n`, 'utf8');

  const manifest = {
    generated_at: new Date().toISOString(),
    document_count: docs.length,
    files: {
      jsonl: path.basename(jsonlPath),
      task_docs_dir: 'task_docs/',
      project_docs_dir: 'project_docs/',
      summary_docs_dir: 'summary_docs/',
    },
    vertex_ingestion_hint: {
      recommended_source: 'Upload JSONL and/or text files to GCS, then import into Vertex AI RAG corpus.',
      example_gcs_path: 'gs://YOUR_BUCKET/rag_exports/',
    },
  };

  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

  return { jsonlPath, manifestPath };
}

async function run() {
  const outputArg = getArgValue('--out-dir');
  const updatedSinceArg = getArgValue('--updated-since');

  const outputDir = outputArg
    ? path.resolve(outputArg)
    : path.resolve(__dirname, '..', 'rag_exports');

  let updatedSince;
  if (updatedSinceArg) {
    const parsed = new Date(updatedSinceArg);
    if (Number.isNaN(parsed.getTime())) {
      throw new Error('Invalid --updated-since value. Use ISO timestamp, e.g. 2026-02-22T00:00:00Z');
    }
    updatedSince = parsed.toISOString();
  }

  console.log('Exporting SQL data as Vertex RAG documents...');
  if (updatedSince) {
    console.log(`Incremental mode from: ${updatedSince}`);
  }

  await ensureOutputDirs(outputDir);

  const [tasks, projects] = await Promise.all([
    fetchTasks(updatedSince),
    fetchProjectSnapshots(updatedSince),
  ]);

  const docs = [
    ...tasks.map(buildTaskDocument),
    ...projects.map(buildProjectDocument),
    buildPortfolioSummary(tasks),
  ];

  const { jsonlPath, manifestPath } = await writeDocuments(outputDir, docs);

  console.log(`Task documents: ${tasks.length}`);
  console.log(`Project documents: ${projects.length}`);
  console.log(`Total exported documents: ${docs.length}`);
  console.log(`JSONL output: ${jsonlPath}`);
  console.log(`Manifest output: ${manifestPath}`);
}

run()
  .catch((error) => {
    console.error('RAG export failed:', error.message);
    process.exitCode = 1;
  })
  .finally(async () => {
    try {
      await pool.end();
    } catch (error) {
      // ignore pool close errors on shutdown
    }
  });