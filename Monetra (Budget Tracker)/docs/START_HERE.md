# Start Here

This guide explains Monetra in plain English and points you to the right document for each task.

(First deployed to a staging environment, then to production.)

## What Monetra Is

Monetra is a personal finance web app. You can use it to:

- register and log in as a user
- add income and expenses
- track spending by category
- manage recurring payments
- review piggy bank carryover
- generate monthly reports
- ask AI questions about your finances
- test the app with dummy users before deployment
- deploy to the Oracle production VM through CircleCI

## The Safest Order To Work

Follow this order:

1. Run Monetra locally.
2. Test the main features manually.
3. Run automated backend and frontend tests.
4. Run dummy-user/load tests.
5. Run controlled chaos checks locally or through CI.
6. Create an Oracle VM account.
7. Create the production VM with Terraform.
8. Configure production environment variables on the VM and in CircleCI.
9. Approve production deployment.
10. Run production smoke checks.

Staging was used to validate the first Oracle deployment. The current setup keeps one production Oracle VM and uses automated gates plus manual approval before deployment.

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
- review the piggy bank balance
- generate a PDF report
- reindex RAG
- ask the AI a finance question
- run dummy-user/load tests

## Important Safety Notes

- Keep real passwords and API keys in `backend/.env`; never commit them.
- Use fake users and fake finance data for testing.
- Run destructive chaos/failure drills only in local or planned non-production environments.
- Production deployment should happen only after tests, reliability checks, and manual approval pass.
