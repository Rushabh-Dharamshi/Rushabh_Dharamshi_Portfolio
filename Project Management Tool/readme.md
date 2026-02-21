# Project Management Tool

A full-stack project management platform built with React, Node.js, Express, and MySQL. The app keeps task CRUD functionality while extending into portfolio-grade capabilities: analytics dashboards, kanban execution flow, local ML risk scoring, and a free local RAG-style assistant.

## Overview

Project Management Tool is designed as a production-style upgrade from a task tracker into a modern project operations workspace. It combines execution, visibility, and decision support in one interface while keeping costs at zero for AI/ML features.

## Core Features

### Project and Work Management
- Create, update, complete, and delete work items
- Project-aware planning with a `projects` workspace model
- Kanban statuses: `backlog`, `in_progress`, `blocked`, `done`
- Priority, difficulty, progress, due date, assignee, and estimated hours
- Filter by project, search across work items, and sort by key dimensions

### Analytics and Visualization
- Category mix dashboard
- Status distribution chart
- Completion velocity trend
- Workload by assignee
- Low-latency analytics endpoint aggregation

### Free AI and ML
- Local ML risk scoring engine (no paid API)
- Worker-thread pool for concurrent risk computation
- Local retrieval-augmented assistant over your own data
- Operational assistant actions (create task / mark complete) via chat commands

### Performance and Reliability
- Modular backend architecture with clear separation of concerns
- MySQL connection pooling for concurrent request handling
- `Promise.all` query concurrency in analytics/services
- In-memory response caching for repeated assistant prompts
- Graceful server shutdown handling

## Architecture

### Frontend (React)
- Dashboard-first information layout
- List and Kanban execution modes
- Dedicated ML insights panel
- Dedicated RAG assistant panel
- Responsive UI for desktop and mobile

### Backend (Node.js + Express)
- `config`: environment and runtime settings
- `db`: pool and schema initialization
- `repositories`: data access abstraction
- `services`: business logic, ML, assistant behavior
- `routes`: API contracts
- `workers`: CPU-bound ML scoring in worker threads
- `utils`: reusable infrastructure helpers (worker pool)

### Data Layer (MySQL)
- `projects` table for workspace organization
- `tasks` table extended with PM-specific fields
- Schema migration-safe setup on startup

## Technology Stack
- Frontend: React, React Bootstrap, Chart.js
- Backend: Node.js, Express
- Database: MySQL (`mysql2` pool)
- AI/ML: local heuristic model + local retrieval logic
- Runtime model cost: free by default

## API Summary

### Work Items
- `GET /tasks`
- `POST /tasks`
- `PUT /tasks/:id`
- `PATCH /tasks/:id/completed`
- `PATCH /tasks/:id/status`
- `DELETE /tasks/:id`

### Projects
- `GET /projects`
- `POST /projects`

### Analytics
- `GET /api/analytics/overview`
- Backward-compatible analytics routes under `/api/tasks/...`

### AI/ML
- `GET /api/ml/risk`
- `POST /api/chat`

## Repository Structure

```text
client/
server/
  src/
    config/
    db/
    repositories/
    routes/
    services/
    utils/
    workers/
database/
```

## Getting Started

## Prerequisites
- Node.js 18+
- npm 9+
- MySQL 8+

## Environment Variables (server)

Create `server/.env`:

```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=project_management
PORT=5000
MYSQL_POOL_SIZE=10
WORKER_POOL_SIZE=4
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=mistral:latest
OLLAMA_EMBED_MODEL=nomic-embed-text:latest
```

Notes:
- `MYSQL_*` is now the preferred naming.
- `DB_*` is still supported for backward compatibility.

## Install Dependencies

```bash
cd server && npm install
cd ../client && npm install
```

## Run the App

Use two terminals.

Terminal 1:

```bash
cd server
npm start
```

Terminal 2:

```bash
cd client
npm start
```

Frontend: `http://localhost:3000`  
Backend: `http://localhost:5000`

## Testing

Backend tests are in 'server/tests' and include unit/API tests plus Cucumber-style BDD scenarios.

Run from 'server':

```bash
npm run test:unit
npm run test:bdd
npm test
```

## Example Assistant Commands
- `show overdue`
- `show risk`
- `create task: title=Write API docs; description=Publish v1 docs; due=2026-03-01; priority=medium`
- `mark task 12 complete`

## Portfolio Highlights
- End-to-end architecture refactor from monolithic file to layered modules
- Practical concurrency: pooled DB + worker-thread compute offloading
- Data-driven UI with multiple charting views
- Zero-cost AI/ML baseline with extensible interfaces
- Strong foundation for adding auth, real-time updates, and CI/CD


## Local LLM (LangChain RAG)
- Chat uses LangChain + Ollama with retrieval over your MySQL data.
- Ensure Ollama is running before starting the server.
- Required models:
```bash
ollama pull mistral:latest
ollama pull nomic-embed-text:latest
```

