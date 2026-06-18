# Controlled Chaos Engineering

These drills are for local or staging environments only.

## Plain-English Summary

Chaos engineering sounds dramatic, but here it means controlled failure practice.

The goal is to learn how Monetra behaves when a dependency is unavailable, then confirm the app logs the problem and recovers after the dependency comes back.

Run these against local or staging only. Do not run outage drills against real production.

## Goals

- Verify Monetra fails closed when dependencies are unavailable.
- Confirm API errors are controlled and logged.
- Confirm recovery after a dependency is restored.
- Generate evidence for portfolio language such as:

> Implemented fault-injection tests in a controlled staging environment to validate failure handling and recovery.

## Supported Drills

| Drill | What It Does |
| --- | --- |
| `ChromaOutage` | Stops the Chroma container and runs RAG smoke checks |
| `PostgresOutage` | Stops PostgreSQL and validates controlled API failure behavior |
| `ChaosSmoke` | Runs a k6 smoke script against health/auth/protected endpoints |

## Run

```powershell
cd "Monetra (Budget Tracker)"
powershell -ExecutionPolicy Bypass -File chaos\run-controlled-chaos.ps1 -Drill ChaosSmoke
```

For dependency outage drills:

```powershell
powershell -ExecutionPolicy Bypass -File chaos\run-controlled-chaos.ps1 -Drill ChromaOutage
powershell -ExecutionPolicy Bypass -File chaos\run-controlled-chaos.ps1 -Drill PostgresOutage
```

The script restarts the stopped service in a `finally` block.
