# Dummy-User And Load Testing

This document explains the rigorous dummy-user test suite in plain English.

## What This Test Does

The k6 script at `load-tests/k6/monetra-load.js` simulates fake users using Monetra at the same time.

It is designed to answer:

- can new users register and log in?
- does each user only see their own finance data?
- can users create income and expenses?
- can users update budgets and monthly income?
- do savings goals work under repeated use?
- do recurring payments work under repeated use?
- do dashboards stay responsive under concurrent reads?
- do invalid inputs get rejected correctly?
- do reports, RAG, and agent endpoints fail cleanly if AI services are unavailable?
- do manual report/reminder email endpoints route messages to the dummy user's registered email?
- does the app stay within reasonable API latency limits?

## Scenarios Covered

| Scenario | What It Checks |
| --- | --- |
| `auth_lifecycle` | register, session check, logout, login, forgot-password response |
| `end_to_end_finance_journeys` | income, expenses, budget, income settings, savings goals, recurring payments, dashboard, analytics, CSV export |
| `user_isolation_probes` | one user cannot list or fetch another user's transaction |
| `concurrent_dashboard_reads` | many users repeatedly reading dashboard and analytics endpoints |
| `concurrent_budget_updates` | repeated budget writes under concurrent pressure |
| `invalid_and_security_inputs` | invalid transactions, invalid savings goals, invalid recurring items, wrong password, unauthenticated access |
| `reports_rag_and_agent_resilience` | monthly report, RAG reindex/query, AI finance briefing behavior, and manual email dispatch |

## Email Safety Model

Use three email modes:

| Test type | Sender | Recipient | Email mode |
| --- | --- | --- | --- |
| Mixed local testing | `rushabh.dharamshi@gmail.com` for allowlisted recipients, `demo@monetra.test` for simulated recipients | Your four Gmail accounts and `@monetra.test` demo users | `EMAIL_MODE=hybrid` |
| Real email delivery | `rushabh.dharamshi@gmail.com` | Your four Gmail accounts | `EMAIL_MODE=real` |
| Load testing | none required | `@monetra.test` dummy users | `EMAIL_MODE=mock` |
| PDF report logic | none required | `@monetra.test` dummy users | `EMAIL_MODE=mock` |
| AI workflow tests | none required | `@monetra.test` dummy users | `EMAIL_MODE=mock` |
| Production smoke test | `rushabh.dharamshi@gmail.com` | your main Gmail | `EMAIL_MODE=real` |
| Fault testing | mock or intentionally broken service | `@monetra.test` dummy users | `EMAIL_MODE=mock` |

For mixed local testing, configure only accounts you own and mock domains for fake users:

```env
EMAIL_MODE=hybrid
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=rushabh.dharamshi@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_USE_TLS=true
SMTP_REQUIRE_AUTH=true
EMAIL_FROM=rushabh.dharamshi@gmail.com
ALLOWED_TEST_EMAILS=rushabh.dharamshi@gmail.com,testpurposes683@gmail.com,rushlovesgames28@gmail.com,rushabh.is.cool28@gmail.com
EMAIL_MOCK_DOMAINS=monetra.test,example.test
MOCK_EMAIL_FROM=demo@monetra.test
```

In hybrid mode, allowlisted Gmail recipients receive real email, `@monetra.test` and `@example.test` recipients are simulated, and unknown real recipients are blocked.

For portfolio screenshots, demo users can open **Forgot password -> Demo email inbox** and enter an address such as `user001@monetra.test`. Monetra shows simulated reset-code/report emails there without sending anything to a real inbox or Mailpit.

For dummy users and load tests, use mock mode:

```env
EMAIL_MODE=mock
```

The load test should use fake addresses such as `user001@monetra.test`, `user002@monetra.test`, and `user100@monetra.test`.

In mock mode, Monetra records the simulated email recipient, subject, sender, attachment status, and `status=simulated`. No SMTP connection is opened and no real email is sent.

In real mode, Monetra blocks every recipient that is not in the allowlist. If the allowlist is missing, real SMTP delivery is blocked.

## Quality Gates

The script has strict thresholds:

| Gate | Meaning |
| --- | --- |
| `checks >= 97%` | Almost every business check must pass. |
| `monetra_business_failure_rate < 1%` | Important workflow failures must be very rare. |
| `monetra_isolation_failure_rate == 0` | Data isolation must never fail. |
| `monetra_unexpected_status_count == 0` | Unexpected HTTP statuses are not allowed. |
| `p95 < 2500ms` | 95% of API requests should finish within 2.5 seconds. |
| `p99 < 5000ms` | 99% of API requests should finish within 5 seconds. |
| dashboard read `p95 < 1500ms` | Dashboard reads should stay fast under load. |

## Run Locally

Start the app first:

```powershell
cd "Monetra (Budget Tracker)"
docker compose up -d --build
```

Run the rigorous dummy-user suite:

```powershell
docker compose --profile load run --rm load-test-runner
```

Or through the validation helper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate-local.ps1 -SkipBackend -SkipFrontend -RunLoad
```

## Strict AI Mode

By default, RAG and agent endpoints are allowed to return controlled service-unavailable responses because Ollama may not be running in every environment.

If Ollama is running and you want AI/RAG to be mandatory, run with:

```powershell
docker compose --profile load run --rm -e MONETRA_STRICT_AI=true load-test-runner
```

In strict AI mode:

- RAG reindex must succeed
- RAG query must succeed
- agent start must succeed

## Custom Target

To test staging later:

```powershell
docker compose --profile load run --rm -e MONETRA_BASE_URL=https://staging.example.com load-test-runner
```

## How To Interpret Results

Good result:

- checks pass
- thresholds pass
- no data isolation failures
- no unexpected statuses
- p95 and p99 latency stay under the thresholds
- dummy-user email dispatch succeeds or fails only through expected controlled paths

Bad result:

- failed checks mean a user workflow broke
- isolation failures mean a serious multi-user security issue
- latency failures mean APIs are too slow under dummy-user pressure
- unexpected statuses mean the backend returned something the test did not expect

## Important Notes

- Use fake users and fake finance data.
- Use fake email addresses such as `user001@monetra.test`.
- Run this locally or against staging.
- Do not run heavy load tests against production unless you intentionally planned a controlled production load test.
