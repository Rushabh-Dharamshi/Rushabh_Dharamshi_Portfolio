# Testing Strategy

Monetra targets meaningful coverage across critical user and system workflows, not superficial coverage.

## Plain-English Summary

Testing is how you prove the app still works after changes.

Monetra uses several test types because one kind of test cannot catch every issue:

- backend tests check server logic
- frontend tests check screens and user interactions
- E2E tests check browser workflows
- load tests simulate many users
- fault tests check how the app behaves when something fails

The goal is not just a high coverage number. The goal is confidence that important finance workflows keep working.

## Backend

- Unit tests: service, repository, validation, AI helpers.
- Integration tests: Flask API, auth/session behavior, production guards.
- Fault paths: email unavailable, Ollama timeout, RAG service errors, scheduler failures.

Commands:

```powershell
cd "Monetra (Budget Tracker)/backend"
.venv\Scripts\python.exe -m pytest
```

## Frontend

- Unit tests: components, hooks, API client.
- Integration tests: dashboard shell and error/loading states.
- E2E tests: Playwright browser workflows.
- BDD tests: Cucumber features.
- Static check: `tsc --noEmit`.

Commands:

```powershell
cd "Monetra (Budget Tracker)/frontend"
npm.cmd test
npx.cmd tsc --noEmit
npm.cmd run test:e2e
npm.cmd run test:bdd
```

## Load and Dummy-User Testing

Use `load-tests/k6/monetra-load.js` against a local API or a planned non-production clone. The scenarios are intentionally rigorous and cover:

- auth lifecycle: register, session check, logout, login, forgot password response
- full finance journey: income, expenses, budget, monthly income, piggy bank carryover, recurring payments, dashboard, analytics, CSV export
- user isolation: one user cannot list or fetch another user's transaction
- read concurrency: many dashboard and analytics requests at once
- write concurrency: repeated budget updates
- negative paths: invalid transactions, invalid recurring items, unauthenticated access, wrong password
- AI/reporting resilience: PDF report, RAG reindex/query, and agent briefing behavior

The k6 suite enforces thresholds for check pass rate, business failures, data isolation failures, unexpected statuses, and API latency.

Detailed guide: `docs/DUMMY_USER_LOAD_TESTING.md`.

## Latency Baselines

Use `scripts/measure-latency.ps1` to record lightweight request latency for local and production environments.

Local:

```powershell
cd "Monetra (Budget Tracker)"
$env:MONETRA_LATENCY_USERNAME="your-test-username"
$env:MONETRA_LATENCY_PASSWORD="your-test-password"
powershell -ExecutionPolicy Bypass -File scripts\measure-latency.ps1 -Environment local -BaseUrl http://localhost:8000 -Iterations 20
```

Production:

```powershell
$env:MONETRA_LATENCY_USERNAME="your-production-smoke-username"
$env:MONETRA_LATENCY_PASSWORD="your-production-smoke-password"
powershell -ExecutionPolicy Bypass -File scripts\measure-latency.ps1 -Environment production -BaseUrl https://your-production-api.example.com -Iterations 20
```

The script writes raw CSV, summary CSV, summary JSON, Markdown, and HTML monitoring reports under `latency-results/`. Compare p50, p95, p99, failures, and max latency between environments. Each measured user gets a `report_id`; each API call gets a `request_id` with timestamp, endpoint, status code, and duration. Credentials are optional, but protected endpoints will return `401` without them.

For multiple users, pass a CSV:

```csv
label,username,password
primary,Rushabh,password-for-that-account
test-683,testpurposes683@gmail.com,password-for-that-account
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\measure-latency.ps1 -Environment local -BaseUrl http://localhost:8000 -Iterations 20 -UserCredentialCsv .\latency-users.local.csv
```

## CI/CD

CircleCI runs:

- backend pytest suite
- frontend Jest/integration suite
- TypeScript checks
- backend Docker build
- frontend Docker build
- Playwright E2E
- dummy/load checks
- controlled chaos smoke checks
- production deployment after manual approval

Production deployment is defined in `.circleci/continue-config.yml` and deploys over SSH to the Oracle VM.
