# Monetra Production-Readiness Checklist

Target signal: AI-enabled personal finance platform with backend systems, RAG/tool-calling, production-style deployment, CI/CD, testing, dummy-user simulation, and fault-injection readiness.

## Plain-English Summary

This checklist maps the project goal to real evidence in the codebase.

Use it to answer:

- what features Monetra already has
- where the evidence is in the repo
- what remains before longer-term production hardening

This file is useful for portfolio review, interview preparation, and planning the next production-readiness work.

## Core Product

| Status | Feature | Evidence |
| --- | --- | --- |
| Done | Expense tracking | `POST/GET/PUT/DELETE /api/expenses` |
| Done | Income tracking | income transaction support and monthly income settings |
| Done | Budget management | `/api/settings/budget` |
| Done | Category-based spending | category analytics and dashboard cards |
| Done | Recurring payments | `/api/recurring-items` |
| Done | Payment reminders | recurring calendar, paid/unpaid occurrence verification |
| Done | Piggy bank carryover | dashboard piggy bank panel and cumulative cash-flow calculation |
| Done | Transaction search/filtering | ID search plus category/text/date filters |
| Done | Monthly financial summary | `/api/dashboard`, `/api/reports/monthly` |
| Done | Input validation and error handling | service-layer validation and API error handlers |

## Backend

| Status | Task | Evidence |
| --- | --- | --- |
| Done | Flask backend APIs | `backend/budget_tracker_api/blueprints` |
| Done | RESTful endpoint structure | `docs/API.md` |
| Done | PostgreSQL schema | `backend/budget_tracker_api/db.py` |
| Done | SQLAlchemy models/tables | SQLAlchemy Core table definitions |
| Done | Database migrations | schema migration guards in `init_db`; legacy SQLite migration script |
| Done | Authentication | register, login, forgot/reset password |
| Done | Validation layer | service modules |
| Done | Error-handling middleware | `errors.py` and app error handlers |
| Done | Logging | structured request and service logs |
| Done | Health-check endpoint | `/api/health` |
| Done | API documentation | `docs/API.md` |

## Frontend

| Status | Task | Evidence |
| --- | --- | --- |
| Done | Next.js frontend | `frontend/app` |
| Done | TypeScript setup | `tsconfig.json` |
| Done | Dashboard page | composed dashboard shell |
| Done | Transactions page/surface | expense form/table panel |
| Done | Budgets page/surface | operations panel |
| Done | Reports page/surface | PDF/report controls |
| Done | AI assistant page/surface | AI agent and RAG panels |
| Done | Form validation | API validation plus required form controls |
| Done | Loading/error states | hook status and error messages |
| Done | Clean UI layout | panel-based dashboard |
| Done | Responsive design | responsive CSS rules |

## Analytics, AI, Testing, and Operations

| Status | Area | Evidence |
| --- | --- | --- |
| Done | Analytics/reporting | dashboard, category insights, financial pulse, PDF, CSV, email |
| Done | Agentic AI/RAG | Ollama, LangGraph, FastMCP, Chroma RAG |
| Done | Testing | pytest, Jest, RTL, Playwright, Cucumber, tsc |
| Done | Dummy/load testing | `load-tests/k6/monetra-load.js` |
| Done | CI/CD gates | CircleCI backend/frontend/build/E2E/load/chaos/deploy jobs |
| Done | Docker setup | `docker-compose.yml` on Oracle production VM |
| Done | Infrastructure as Code | production Oracle VM, VCN, subnet, route table, security list, and public IP via Terraform |
| Done | Observability | logs, health endpoint, latency logs, fault notes |
| Done | Documentation | `docs/` |

## Production Caveat

Monetra has been deployed through a staging-to-production path (first deployed to a staging environment, then to production). Remaining hardening work includes a custom domain, TLS termination, managed backups, stricter SSH CIDR rules, rollback automation, and longer-running production monitoring.
