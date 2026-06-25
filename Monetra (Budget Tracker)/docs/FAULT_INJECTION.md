# Fault-Injection Notes

Use these only in local or planned non-production environments.

## Plain-English Summary

Fault injection means creating a controlled failure on purpose so you can check that the app handles it properly.

Examples:

- temporarily stop Chroma to see if RAG fails cleanly
- temporarily stop PostgreSQL to see if errors are logged
- make SMTP invalid to test email failure handling

Do this only in local or planned non-production environments. Do not intentionally break production.

## Scenarios

| Failure | Expected Behavior |
| --- | --- |
| SMTP unavailable | email endpoint returns a controlled service-unavailable error |
| Ollama timeout | agent/RAG request returns a controlled AI service error |
| Chroma unavailable | RAG status/query fails gracefully |
| PostgreSQL unavailable | health checks and API calls fail with logged errors |
| Slow database | latency logging surfaces slow requests |
| Invalid transactions | validation returns 400 with clear message |

## Recommended Wording

Use:

> Implemented fault-injection tests in a controlled non-production environment to validate failure handling and recovery.

Avoid:

> I broke production.

## Manual Checks

1. Stop SMTP credentials or set an invalid SMTP host.
2. Trigger manual month-end email.
3. Stop Ollama.
4. Trigger AI briefing and RAG query.
5. Stop Chroma.
6. Trigger RAG status and query.
7. Review `backend/.run/monetra.log` for structured error entries.

## Automated Local Drills

Run these only against local or planned non-production stacks:

```powershell
cd "Monetra (Budget Tracker)"
powershell -ExecutionPolicy Bypass -File chaos\run-controlled-chaos.ps1 -Drill ChaosSmoke
powershell -ExecutionPolicy Bypass -File chaos\run-controlled-chaos.ps1 -Drill ChromaOutage
powershell -ExecutionPolicy Bypass -File chaos\run-controlled-chaos.ps1 -Drill PostgresOutage
```

The outage drills stop the target Docker Compose dependency, run smoke checks, and restart the dependency in a cleanup block.
