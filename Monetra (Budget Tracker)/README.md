# ?? Monetra (Budget Tracker)

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-Backend-000000?logo=flask&logoColor=white">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql&logoColor=white">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-Frontend-000000?logo=nextdotjs&logoColor=white">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-Typed_UI-3178C6?logo=typescript&logoColor=white">
</p>

<p align="center">
  <img alt="Ollama" src="https://img.shields.io/badge/Ollama-Local_AI-111111">
  <img alt="LangGraph" src="https://img.shields.io/badge/LangGraph-Agent_Flows-1C3C3C">
  <img alt="scikit-learn" src="https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikitlearn&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white">
  <img alt="AWS Ready" src="https://img.shields.io/badge/AWS-Deployment_Ready-FF9900?logo=amazonaws&logoColor=white">
</p>

Monetra is a full-stack personal finance platform for recording expenses, monitoring budget performance, generating reports, surfacing predictive insights, and orchestrating local agentic-AI workflows. The system combines a Flask backend for business logic and APIs, PostgreSQL for persistence, and a Next.js frontend for a dashboard-driven user experience.

## ? App Overview

The application helps a user track day-to-day spending, understand where money is going, and act on trends before a monthly budget is exceeded. It combines operational features such as expense management and CSV import and export with analytical features such as category trends, prediction, KPI dashboards, visual reporting, and financial health indicators.

## ?? Features

- ?? Expense create, read, update, and delete flows with server-side validation
- ?? Search by transaction ID for direct record lookup
- ?? CSV import with row cleaning, whitespace normalization, and automatic skipping of rows with missing values
- ?? CSV export for offline analysis and backups
- ?? Monthly dashboard with budget progress, total spend, and weekly totals
- ?? KPI visualizations including category mix, monthly trend, and weekly cadence charts
- ?? Category analytics showing strongest and weakest spend areas
- ?? Word-cloud data for the most prominent expense descriptions
- ?? Financial pulse analytics with health score, spend velocity, runway, and recent activity
- ?? Next-month spend prediction using machine learning
- ?? Detailed multi-section PDF financial reports with charts, category variance analysis, transaction highlights, insights, and recommendations
- ?? Responsive user interface with a dashboard-oriented layout and action-focused workflows
- ?? Optional demo-access protection and read-only deployment mode for private live showcases

## ?? Tech Stack

### ?? Backend

- ?? Python 3
- ??? Flask
- ?? Flask-Cors
- ?? PostgreSQL
- ?? SQLAlchemy
- ? psycopg
- ?? NumPy
- ?? scikit-learn
- ?? matplotlib
- ?? ReportLab
- ?? pytest

### ?? Frontend

- ? Next.js
- ?? React
- ?? TypeScript
- ?? CSS
- ?? Jest
- ?? Playwright
- ?? Cucumber

## ?? Libraries Used

- ?? `Flask` provides the HTTP API and application bootstrap
- ?? `Flask-Cors` enables browser access from the frontend
- ?? `SQLAlchemy` provides database connectivity and schema management
- ?? `psycopg` connects the backend to PostgreSQL
- ?? `numpy` supports numerical calculations
- ?? `scikit-learn` powers the spend prediction workflow
- ?? `matplotlib` generates chart output for reporting
- ?? `reportlab` builds PDF reports
- ?? `Next.js` handles the frontend application shell and routing
- ?? `React` renders the UI and manages interactive views
- ?? `TypeScript` adds type safety to frontend logic
- ?? `Jest` runs frontend unit and integration tests
- ?? `Playwright` runs browser end-to-end tests
- ?? `Cucumber` supports behavior-driven testing scenarios
- ?? `pytest` runs backend unit and integration tests

## ??? System Design And Architecture

The application uses a three-part architecture:

- ??? Presentation layer: a Next.js frontend responsible for the visual interface, user interactions, state orchestration, and API consumption
- ?? Application layer: a Flask backend responsible for request handling, validation, business workflows, analytics, prediction, reporting, and orchestration
- ??? Data layer: PostgreSQL, accessed only through repository classes

### ?? Architecture Classification

The system is a small distributed three-tier application. It is not a microservice architecture because there is only one backend service owning all business capabilities. It is also not a traditional single-process monolith because the frontend and backend run as separate deployable applications. The best description is:

- ?? Separate frontend and backend services
- ?? One backend API service
- ??? One shared relational database
- ?? Modular backend design inside a single service boundary

In practice, that makes the backend a modular monolith exposed through a clean API layer, with the overall system following a three-tier architecture.

### ?? Data Isolation Note

The current application is intentionally designed as a single-user personal finance system. It does not yet implement:

- ?? user accounts
- ?? per-user row ownership
- ?? tenant isolation
- ?? user-scoped report access

That means a public deployment should be treated as a private or demo deployment unless a full authentication and per-user authorization model is added.

### ?? Architectural Patterns

- ?? Application factory pattern in Flask for clean startup configuration and environment-specific setup
- ?? Blueprint pattern for grouping API routes by capability
- ?? Service layer pattern for business logic and orchestration
- ??? Repository pattern for isolating data access from the rest of the codebase
- ?? Client adapter pattern in the frontend for centralized API communication
- ?? Hook-based state orchestration in the frontend to separate data workflows from presentational components
- ?? Component-based UI composition so each dashboard section remains focused and reusable

### ??? Design Patterns In Use

The codebase uses a focused subset of common design patterns and design principles:

- ?? Factory / Application Factory: the Flask app is created and wired in `create_app`
- ??? Repository Pattern: data access is isolated in the repository layer
- ?? Service Layer Pattern: business logic lives in service classes rather than routes
- ?? Adapter / Facade Pattern: the frontend API client presents one clean interface over HTTP calls
- ?? Dependency Injection: repositories and configuration are passed into services instead of being created internally
- ? Lazy Initialization: the database engine is created only when first needed
- ?? Composition Over Inheritance: behavior is assembled from focused classes and modules rather than deep inheritance trees
- ?? MVC-inspired separation: routes/controllers, service logic, persistence, and presentation are kept separate

### ?? Patterns Intentionally Not Used

Some common patterns are not implemented because they would add complexity without adding value to the current scope:

- ?? Microservices
- ?? CQRS
- ?? Event sourcing
- ?? Event-driven architecture
- ?? Singleton
- ?? Abstract Factory
- ?? Prototype
- ?? Object Pool
- ?? Formal Command objects
- ?? Formal Strategy objects
- ?? Chain of Responsibility
- ?? Mediator
- ?? Visitor

That is a deliberate `YAGNI` decision: the current application is clearer and easier to maintain without those abstractions.

### ?? Backend Design

The Flask backend is organized into clear layers:

- ?? Blueprints expose HTTP endpoints and keep controller logic thin
- ?? Services implement application rules such as expense validation, CSV cleaning, analytics, prediction, and reporting
- ??? Repositories execute database reads and writes against PostgreSQL through SQLAlchemy connections
- ?? Configuration centralizes database URL, CORS origins, report output directory, and budget settings
- ?? Migration tooling supports one-time import from the legacy SQLite database into PostgreSQL

This structure keeps HTTP concerns, business logic, and persistence concerns separate. It also makes unit and integration testing more direct because each layer has a narrow responsibility.

### ?? Frontend Design

The Next.js frontend is organized around a small set of focused responsibilities:

- ?? `app/` contains the application entry points and global layout
- ?? `components/` contains reusable UI sections such as dashboard panels, forms, tables, KPI charts, and analytics cards
- ?? `hooks/` contains the main orchestration hook for loading data and handling mutations
- ?? `lib/` contains the API client and request utilities

The frontend uses a dashboard-oriented design so the most important information is visible immediately: budget usage, current totals, KPI charts, trends, and recent activity. Actions such as adding expenses, searching, importing, exporting, and report generation are placed close to the data they affect.

## ?? High-Level Flow

1. The user interacts with the Next.js interface.
2. The frontend calls the Flask API through centralized client helpers.
3. Flask routes delegate work to service classes.
4. Services use repository classes to access PostgreSQL.
5. Responses return structured data to the frontend for rendering.
6. Analytical services also generate derived insights such as category trends, prediction, financial pulse metrics, KPI data, and PDF reports.

## ?? Project Structure

```text
backend/
  budget_tracker_api/
    blueprints/
    repositories/
    services/
    config.py
  scripts/
  tests/
  run.py
  wsgi.py

frontend/
  app/
  components/
  hooks/
  lib/
  tests/
  package.json

docker-compose.yml
README.md
```

## ?? Running The System Locally

### ?? Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
set DATABASE_URL=postgresql+psycopg://budget_user:budget_password@localhost:5432/budget_tracker
python run.py
```

The backend runs on `http://127.0.0.1:5000`.

### ?? Frontend

```bash
cd frontend
copy .env.example .env.local
npm.cmd install
npm.cmd run dev
```

The frontend runs on `http://127.0.0.1:3000`.

### Docker Compose

```bash
docker compose up --build
```

This starts PostgreSQL, the Flask backend, and the Next.js frontend together.

## ?? Safe Demo Production Deployment

If you want to deploy this live for learning or portfolio review without exposing personal finance data, use it as a private demo deployment rather than a public multi-user app.

Recommended production shape:

- ?? public `Next.js` frontend URL
- ?? same-origin `/api/*` proxy from Next.js to Flask using `API_PROXY_TARGET`
- ?? private Flask API behind the frontend
- ?? PostgreSQL for persistence
- ?? optional `Ollama` host for local-model workflows

Recommended production environment variables:

Backend:

```env
DEMO_ACCESS_ENABLED=true
DEMO_ACCESS_USERNAME=your_demo_username
DEMO_ACCESS_PASSWORD=your_strong_demo_password
READ_ONLY_MODE=true
PUBLIC_HEALTHCHECK_ENABLED=true
EXPOSE_ERROR_DETAILS=false
REPORT_EMAIL_TO=your_email@example.com
```

Frontend:

```env
API_PROXY_TARGET=https://your-backend.internal
DEMO_ACCESS_ENABLED=true
DEMO_ACCESS_USERNAME=your_demo_username
DEMO_ACCESS_PASSWORD=your_strong_demo_password
NEXT_PUBLIC_API_BASE_URL=
```

What this does:

- ?? protects both the web UI and API with a shared Basic Auth gate
- ?? keeps the app reachable at one public URL while proxying `/api` through Next.js
- ??? prevents dashboard viewers from mutating your personal data when `READ_ONLY_MODE=true`
- ?? avoids leaking internal exception details in production

For a portfolio deployment with your own finance data, this is the safest current mode. For a real multi-user product, the next step would be proper user authentication plus per-user data ownership in every table.

## ?? Migration From The Legacy SQLite Database

To move historical data from the previous SQLite database into PostgreSQL:

```bash
cd backend
.venv\Scripts\activate
python scripts/migrate_sqlite_to_postgres.py --database-url postgresql+psycopg://budget_user:budget_password@localhost:5432/budget_tracker --truncate
```

## ??? API Capabilities

- ?? `GET /api/health`
- ?? `GET /api/expenses`
- ?? `GET /api/expenses/<id>`
- ?? `POST /api/expenses`
- ?? `PUT /api/expenses/<id>`
- ?? `DELETE /api/expenses/<id>`
- ?? `POST /api/expenses/import`
- ?? `GET /api/expenses/export`
- ?? `GET /api/dashboard`
- ?? `GET /api/analytics/categories`
- ?? `GET /api/analytics/wordcloud`
- ?? `GET /api/analytics/financial-pulse`
- ?? `GET /api/predictions/next-month`
- ?? `GET /api/reports/monthly`

## ?? Testing

The repository includes four testing styles:

- ?? Unit tests for isolated logic
- ?? Integration tests for API and persistence behavior
- ?? End-to-end tests for browser workflows
- ?? Cucumber BDD scenarios for user-facing behavior definitions

## ?? Deployment

For production, deploy the Flask backend as a persistent service with PostgreSQL as the database, deploy the Next.js frontend as the web application, and place both behind one domain or reverse proxy so the frontend can use same-origin `/api` requests. Docker support is included through the backend and frontend Dockerfiles plus `docker-compose.yml`.

## ?? Notes

- ?? Generated reports are written to `backend/generated_reports/`.
- ?? The monthly budget value remains configurable through backend settings.
- ? The backend test suite passes locally with `40` passing backend tests and `100%` coverage.
- ? The frontend unit and integration suites pass locally with `16` passing tests.
