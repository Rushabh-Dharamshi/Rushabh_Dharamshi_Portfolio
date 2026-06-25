# Monetra API Reference

## Plain-English Summary

An API is a set of backend URLs that the frontend calls when a user clicks buttons or submits forms.

For example:

- when a user logs in, the frontend calls an auth API
- when a user adds an expense, the frontend calls an expense API
- when a user asks an AI finance question, the frontend calls a RAG API

Most users do not need to call these URLs manually. This file is mainly for developers, testers, and deployment/debugging work.

Base URL: `/api`

All protected endpoints require a valid Monetra session cookie unless `LOGIN_REQUIRED=false` is set for local test runs.

## How To Read This File

- `GET` usually means read data.
- `POST` usually means create something or trigger an action.
- `PUT` usually means update something.
- `DELETE` removes something.
- `{id}` means a real numeric ID, such as `/expenses/12`.

## Auth

- `GET /auth/session` returns the current session.
- `POST /auth/register` creates a user and signs them in.
- `POST /auth/login` signs in by username or email.
- `POST /auth/logout` clears the session.
- `POST /auth/forgot-password` sends a reset code to the registered email address for the submitted username/email when SMTP is configured.
- `POST /auth/reset-password` applies a reset code and new password.

## Expenses

- `GET /expenses`
  - Query params: `sort`, `category`, `q`, `start_date`, `end_date`.
- `GET /expenses/{id}`
- `POST /expenses`
- `PUT /expenses/{id}`
- `DELETE /expenses/{id}`
- `POST /expenses/import`
- `GET /expenses/export`

Expense payload:

```json
{
  "date": "2026-05-18",
  "category": "Travel",
  "description": "Tube fare",
  "amount": "6.40"
}
```

## Piggy Bank

Piggy bank values are included in:

- `GET /dashboard`

The piggy bank is calculated from cumulative monthly cash flow:

```text
monthly income - monthly expenses
```

Positive months increase the cumulative piggy bank balance. Negative months reduce it.

## Legacy Savings Goal Routes

These backend routes are retained for compatibility, but the current user-facing product uses the piggy bank feature instead of the old savings-goal panel.

- `GET /savings-goals`
- `POST /savings-goals`
- `PUT /savings-goals/{id}`
- `DELETE /savings-goals/{id}`

Legacy savings goal payload:

```json
{
  "name": "Emergency fund",
  "target_amount": 3000,
  "current_amount": 750,
  "target_date": "2026-12-31"
}
```

## Analytics and Reports

- `GET /dashboard`
- `GET /analytics/categories`
- `GET /analytics/wordcloud`
- `GET /analytics/financial-pulse`
- `GET /predictions/next-month`
- `GET /reports/monthly`

## Recurring Payments

- `GET /recurring-items`
- `POST /recurring-items`
- `PUT /recurring-items/{id}`
- `DELETE /recurring-items/{id}`
- `GET /recurring-items/calendar?days=35`
- `POST /recurring-items/{id}/occurrences/pay`
- `POST /recurring-items/{id}/occurrences/unpay`

## AI and Automation

- `POST /rag/reindex`
- `GET /rag/status`
- `POST /rag/query`
- `POST /agents/finance-briefing`
- `GET /agents/finance-briefing/{job_id}`
- `GET /agents/workflows`
- `POST /agents/workflows/{workflow_name}/run`
- `GET /agents/workflow-jobs/{job_id}`
- `GET /agents/runs`
- `POST /agents/automation/month-end-email`
- `POST /agents/automation/upcoming-bills-email`

Manual email dispatch recipient behavior:

- If the request is made by a logged-in user, Monetra sends the email to that user's registered email address.
- If there is no logged-in user, Monetra falls back to the configured `REPORT_EMAIL_TO` address.
- Scheduled background automation loops through registered users with email addresses. For each user, Monetra temporarily sets that user's backend data context, runs the scheduled check against only that user's finance data, and passes that user's registered email as the recipient.

## Settings

- `GET /settings?month=YYYY-MM`
- `PUT /settings/budget`
- `PUT /settings/income`

## Health

- `GET /health`
