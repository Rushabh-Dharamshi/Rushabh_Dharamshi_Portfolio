# Local Validation Runbook

Use this runbook before creating the Oracle VM account or enabling deployment in CircleCI.

## Plain-English Summary

This document is your local testing checklist. It helps you prove the app works on your laptop before you spend time setting up the Oracle production VM and CircleCI deployment.

Use fake users and fake finance data while following this guide.

## Goal

Validate Monetra locally as a production-style system before production deployment.

## What You Need Before Starting

- Docker Desktop running
- Node.js installed
- Python installed
- Ollama installed and running if you want to test AI/RAG features
- The Ollama models pulled locally:

```powershell
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

## Phase 1: Code Quality Gates

Run backend tests with the 100% coverage gate:

```powershell
cd "Monetra (Budget Tracker)/backend"
.venv\Scripts\python.exe -m pytest
```

Run frontend unit/integration tests and TypeScript checks:

```powershell
cd "Monetra (Budget Tracker)/frontend"
npm.cmd test
npx.cmd tsc --noEmit
```

Or run both through the helper:

```powershell
cd "Monetra (Budget Tracker)"
powershell -ExecutionPolicy Bypass -File scripts\validate-local.ps1 -SkipDocker
```

## Phase 2: Local Docker Stack

Start the production-style local stack:

```powershell
cd "Monetra (Budget Tracker)"
docker compose up -d --build
```

Expected local URLs:

| Surface | URL |
| --- | --- |
| Frontend | `http://localhost:3000` |
| Backend health | `http://localhost:8000/api/health` |
| Chroma | `http://localhost:8001` |
| Email delivery | Uses `backend/.env` SMTP settings |

Local Docker email uses the SMTP settings in `backend/.env`. If `SMTP_HOST=smtp.gmail.com`, reset codes and report emails are sent to real inboxes, so use only email accounts you own. For dummy/load testing, switch to `EMAIL_DELIVERY_MODE=dry_run` or a safe local SMTP capture service first.

Run the helper including Docker health checks:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate-local.ps1
```

## Phase 3: Manual Product Smoke Test

Use a test account and verify:

1. Register a new user.
2. Log out and log back in.
3. Use forgot/reset password in local fallback mode or with SMTP configured.
4. Add income and expense transactions.
5. Filter/search transactions.
6. Review piggy bank carryover after income and expense changes.
7. Create recurring reminders.
8. Mark recurring occurrences paid/unpaid.
9. Update budget and monthly income.
10. Generate/export CSV.
11. Generate monthly PDF report.
12. Run prediction.
13. Reindex RAG.
14. Ask RAG a finance question.
15. Run an agent workflow.
16. Trigger month-end/upcoming-bills email and confirm the message arrives at the registered email account you own, or in your safe test SMTP capture service if one is configured.

## Phase 4: Dummy-User And Load Testing

Run the rigorous k6 dummy-user scenarios:

```powershell
cd "Monetra (Budget Tracker)"
docker compose --profile load run --rm load-test-runner
```

Or:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate-local.ps1 -SkipBackend -SkipFrontend -RunLoad
```

This covers:

- auth lifecycle
- full finance journeys
- user data isolation
- concurrent dashboard reads
- concurrent budget updates
- invalid inputs and security checks
- repeated report and AI/RAG requests
- captured email dispatch using fake `@monetra.test` dummy-user addresses
- latency thresholds

Read `docs/DUMMY_USER_LOAD_TESTING.md` for the full scenario list and pass/fail criteria.

## Phase 4b: Latency Baseline

Record a local latency baseline after the Docker stack is running:

```powershell
cd "Monetra (Budget Tracker)"
$env:MONETRA_LATENCY_USERNAME="your-test-username"
$env:MONETRA_LATENCY_PASSWORD="your-test-password"
powershell -ExecutionPolicy Bypass -File scripts\measure-latency.ps1 -Environment local -BaseUrl http://localhost:8000 -Iterations 20
```

The script saves raw request timings and summary percentiles under `latency-results/`.

Later, use the same script against production:

```powershell
$env:MONETRA_LATENCY_USERNAME="your-production-smoke-username"
$env:MONETRA_LATENCY_PASSWORD="your-production-smoke-password"
powershell -ExecutionPolicy Bypass -File scripts\measure-latency.ps1 -Environment production -BaseUrl https://your-production-api.example.com -Iterations 20
```

Credentials are optional, but protected endpoints such as `/api/dashboard` need them. Do not run heavy load tests against production by default. The latency script is a lightweight baseline check; k6 is the heavier concurrent-user test.

## Phase 5: Controlled Chaos Smoke

Run only the non-outage smoke drill locally:

```powershell
cd "Monetra (Budget Tracker)"
powershell -ExecutionPolicy Bypass -File chaos\run-controlled-chaos.ps1 -Drill ChaosSmoke
```

Run outage drills only in local or a planned non-production clone:

```powershell
powershell -ExecutionPolicy Bypass -File chaos\run-controlled-chaos.ps1 -Drill ChromaOutage
powershell -ExecutionPolicy Bypass -File chaos\run-controlled-chaos.ps1 -Drill PostgresOutage
```

## Phase 6: Oracle VM Readiness

Create the Oracle VM only after local validation passes.

You will need:

- one production VM
- Docker and Docker Compose on the VM
- Monetra repo cloned on the VM
- `.env.production` on production
- DNS or public IP URLs
- SSH keys for CircleCI
- CircleCI variables from `docs/ORACLE_VM_CICD.md`

## Phase 7: CircleCI Deployment

Normal CI runs without Oracle deployment.

When Oracle is ready, trigger CircleCI with:

```text
deploy-oracle=true
```

Deployment flow:

```text
tests/builds/E2E
-> dummy/load checks
-> controlled chaos smoke checks
-> manual approval
-> production deploy
-> production smoke checks
```
