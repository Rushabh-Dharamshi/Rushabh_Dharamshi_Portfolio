# Start Here

This guide explains Monetra in plain English and points you to the right document for each task.

## What Monetra Is

Monetra is a personal finance web app. You can use it to:

- register and log in as a user
- add income and expenses
- track spending by category
- manage recurring payments
- create savings goals
- generate monthly reports
- ask AI questions about your finances
- test the app with dummy users before deployment
- deploy later to staging and production

## The Safest Order To Work

Follow this order:

1. Run Monetra locally.
2. Test the main features manually.
3. Run automated backend and frontend tests.
4. Run dummy-user/load tests.
5. Run controlled chaos checks locally or in staging.
6. Create an Oracle VM account.
7. Deploy to staging first.
8. Run staging smoke checks.
9. Approve production deployment.
10. Deploy to production.

Do not skip staging. Staging is where you practice fixing deployment, data, latency, logging, and reliability issues before production.

## Which Document Should I Read?

| If you want to... | Read this |
| --- | --- |
| Understand the app quickly | `README.md` |
| Run and test everything locally | `docs/LOCAL_VALIDATION_RUNBOOK.md` |
| See all API routes | `docs/API.md` |
| Understand production readiness | `docs/MONETRA_CHECKLIST.md` |
| Understand testing strategy | `docs/TESTING_STRATEGY.md` |
| Understand dummy-user/load testing | `docs/DUMMY_USER_LOAD_TESTING.md` |
| Understand deployment steps | `docs/DEPLOYMENT.md` |
| Deploy with CircleCI and Oracle VM | `docs/ORACLE_VM_CICD.md` |
| Practice controlled failures | `docs/FAULT_INJECTION.md` and `chaos/README.md` |
| Understand common technical words | `docs/GLOSSARY.md` |

## Quick Local Run

From the repository root:

```powershell
cd "Monetra (Budget Tracker)"
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
docker compose up -d --build
```

Open:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/api/health`

If the health check works, the backend is running.

## What Success Looks Like Locally

You should be able to:

- open the app in the browser
- register a test user
- log in and log out
- add an income transaction
- add an expense transaction
- create a budget
- create a recurring payment
- create a savings goal
- generate a PDF report
- reindex RAG
- ask the AI a finance question
- run dummy-user/load tests

## Important Safety Notes

- Keep real passwords and API keys in `backend/.env`; never commit them.
- Use fake users and fake finance data for testing.
- Run chaos/failure drills in local or staging only.
- Production deployment should happen only after tests and staging checks pass.
