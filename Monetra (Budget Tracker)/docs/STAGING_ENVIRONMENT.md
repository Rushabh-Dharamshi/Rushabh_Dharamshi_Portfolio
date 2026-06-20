# Staging Environment Values

Staging should behave like production but use controlled data, controlled email recipients, and a separate database.

## Files To Prepare On The Oracle VM

Use these templates:

- `.env.staging.example` -> copy to `.env`
- `backend/.env.staging.example` -> copy to `backend/.env`
- `frontend/.env.staging.example` -> copy to `frontend/.env` only if running the frontend outside Docker

Do not commit the copied files. They contain staging secrets after you fill them in.

## Required Changes Before Running Staging

Replace these placeholder values:

- `CHANGE_ME_STAGING_DB_PASSWORD`
- `CHANGE_ME_GENERATE_A_LONG_RANDOM_SECRET`
- `CHANGE_ME_GMAIL_APP_PASSWORD`

The database password must match in both `.env` and `backend/.env`.

## Recommended Staging Defaults

```env
APP_ENV=staging
EMAIL_MODE=hybrid
EMAIL_ALLOWED_RECIPIENTS=Rushabh.Dharamshi@gmail.com,testpurposes683@gmail.com,rushlovesgames28@gmail.com,rushabh.is.cool28@gmail.com
EMAIL_MOCK_DOMAINS=monetra.test,example.test
OLLAMA_MODEL=qwen2.5:7b
RAG_EMBEDDING_MODEL=nomic-embed-text
```

Hybrid email mode means:

- allowlisted Gmail recipients receive real emails through Gmail SMTP
- `@monetra.test` and `@example.test` recipients use the mock inbox
- every other recipient is blocked

## Generate A Staging Secret Key

From PowerShell:

```powershell
[Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
```

Use the generated value as `SECRET_KEY`.

## Start Staging With Docker

```bash
cp .env.staging.example .env
cp backend/.env.staging.example backend/.env
docker compose up -d --build
docker compose ps
curl http://localhost:8000/api/health
```

If the app runs on an Oracle VM, replace `localhost` with the VM public IP when checking from your laptop.

## Notes

Keep local, staging, and production databases separate. Staging latency, test users, reports, RAG indexes, and automation history should not share production storage.
