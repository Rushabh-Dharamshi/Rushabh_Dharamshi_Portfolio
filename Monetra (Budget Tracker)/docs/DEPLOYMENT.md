# Deployment Guide

## Plain-English Summary

Deployment means running Monetra somewhere other than your development laptop.

(First deployed to a staging environment, then to production.)

The safe path is:

1. Run locally.
2. Test locally.
3. Run CI quality gates.
4. Build and validate the production VM with Terraform.
5. Manually approve production in CircleCI.
6. Deploy to production.

Staging was used to validate the first Oracle deployment. The current repository is configured for one production Oracle VM.

## Local Production-Style Stack

```powershell
cd "Monetra (Budget Tracker)"
docker compose up -d --build
```

Services:

| Service | Port |
| --- | --- |
| Frontend | 3000 |
| Backend API | 8000 in Docker, 5000 for local Flask dev |
| PostgreSQL | 5432 |
| Chroma RAG store | 8001 |

The backend expects Ollama to be reachable through `OLLAMA_BASE_URL`. In Docker, this is configured as `http://host.docker.internal:11434`.

Email delivery has three safe modes:

| Mode | Purpose | Delivery behavior |
| --- | --- | --- |
| `EMAIL_MODE=hybrid` | Local or production smoke testing with owned Gmail accounts plus fake demo users | Sends allowlisted recipients through SMTP, simulates configured fake domains, blocks everything else |
| `EMAIL_MODE=real` | Gmail smoke tests and production SMTP | Sends only to allowlisted recipients |
| `EMAIL_MODE=mock` | Dummy users, load tests, CI, fault testing | Records simulated sends and opens no SMTP connection |

For Gmail delivery, use `rushabh.dharamshi@gmail.com` as the sender and only allowlist Gmail accounts you own.

## Required Secrets

- `SECRET_KEY`
- `DATABASE_URL`
- `AUTH_PASSWORD_HASH` for the seeded owner account
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME` or `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_REQUIRE_AUTH`
- `EMAIL_MODE` or `EMAIL_DELIVERY_MODE`
- `EMAIL_FROM`
- `EMAIL_ALLOWED_RECIPIENTS` or `ALLOWED_TEST_EMAILS`
- `EMAIL_MOCK_DOMAINS` when `EMAIL_MODE=hybrid`
- `MOCK_EMAIL_FROM` when `EMAIL_MODE=hybrid`
- `REPORT_EMAIL_TO`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`

Email environment guidance:

| Environment | Recommended email mode |
| --- | --- |
| Developer Gmail and fake-user screenshots | `EMAIL_MODE=hybrid` with Gmail SMTP, your four-account allowlist, and `EMAIL_MOCK_DOMAINS=monetra.test,example.test` |
| Developer Gmail smoke tests only | `EMAIL_MODE=real` with Gmail SMTP and your four-account allowlist |
| CI | `EMAIL_MODE=mock` |
| Dummy/load tests | `EMAIL_MODE=mock` with `@monetra.test` users |
| Production smoke test | `EMAIL_MODE=hybrid` with your Gmail allowlist and fake demo domains |
| Production | `EMAIL_MODE=hybrid` or `EMAIL_MODE=real` with real SMTP credentials and a deliberate recipient allowlist |

## Migration Strategy

The app creates required tables at startup and applies guarded schema migrations in `budget_tracker_api/db.py`. For existing legacy SQLite data, use:

```powershell
cd "Monetra (Budget Tracker)/backend"
python scripts/migrate_sqlite_to_postgres.py
```

## Post-Deployment Smoke Checks

1. `GET /api/health`
2. Register or login.
3. Create a test expense.
4. Load dashboard.
5. Generate monthly report.
6. Run RAG status check.
7. Trigger a manual month-end email only to an allowlisted address or a demo mock inbox.

Automated CI/CD smoke checks are defined in `deploy/smoke-test.sh`.

## Production Deployment

The current CircleCI workflow runs tests, Docker builds, E2E checks, dummy/load checks, and controlled chaos smoke checks. Production deployment then waits for the manual `hold-production-deploy` approval.

See `docs/ORACLE_VM_CICD.md` for the required Oracle VM and CircleCI environment variables.

Before creating or changing the Oracle VM, complete `docs/LOCAL_VALIDATION_RUNBOOK.md`.

Production infrastructure is created from `infra/oracle/environments/production`. The production VM needs `/opt/monetra/.env.production` and `Monetra (Budget Tracker)/backend/.env` before CircleCI deployment.

## Rollback Notes

- Keep database backups before schema changes.
- Deploy immutable Docker images tagged by commit SHA.
- Roll back the frontend and backend images together when API contracts change.
- Preserve `generated_reports` and `.run` volumes unless intentionally resetting local artifacts.
