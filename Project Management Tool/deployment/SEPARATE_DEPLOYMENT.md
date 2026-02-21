# Separate Deployment Guide (Frontend + Backend)

This project supports separate deployment with a dedicated frontend domain and backend API domain.

## Reality Check on "100% Free"

You can deploy for zero cost for demo/portfolio use, but always-on production-grade hosting with local Ollama inference is usually not free.

- Frontend static hosting can be free.
- Backend API can be free-tier for low traffic.
- Managed MySQL can be free-tier.
- Running Ollama models in cloud continuously is typically the expensive part.

## Recommended Architectures

## Option A: No-Cost Portfolio Demo (Most Practical)

- Frontend: Cloudflare Pages (free)
- Backend API: Render free web service (or similar free-tier)
- Database: Aiven for MySQL free-tier (or any free MySQL-compatible tier)
- LLM/RAG: Ollama on your own machine or a home server, exposed to backend via secure tunnel

Pros:
- No recurring payment
- Keeps LangChain RAG + your database

Cons:
- Not enterprise-grade uptime
- Ollama availability depends on your machine uptime

## Option B: Fully Cloud, Production Uptime

- Frontend: Cloudflare Pages / Netlify / Vercel
- Backend: Render/Koyeb/Fly/Railway paid plan
- DB: Managed MySQL paid plan
- LLM: Hosted model endpoint paid plan

Pros:
- Reliable uptime and scaling

Cons:
- Not fully free

## Frontend Deployment Steps

1. Build settings:
- Build command: `npm run build`
- Output directory: `build`
- Root directory: `client`

2. Set frontend environment variable:
- `REACT_APP_API_BASE_URL=https://your-backend-domain.example.com`

3. Redeploy frontend.

## Backend Deployment Steps

1. Deploy `server` as Node service.
2. Set environment variables from `server/.env.production.example`.
3. Set strict CORS:
- `CORS_ALLOWED_ORIGINS=https://your-frontend-domain.example.com`
4. Health check path:
- `/health`

## Database Setup

1. Provision MySQL.
2. Use these values in backend env:
- `MYSQL_HOST`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

Schema is applied automatically at backend startup.

## LangChain + Ollama in Separate Deployment

Your backend currently uses:
- Chat model: `OLLAMA_CHAT_MODEL`
- Embedding model: `OLLAMA_EMBED_MODEL`
- Ollama URL: `OLLAMA_BASE_URL`

If Ollama is not colocated with backend, backend must still be able to reach `OLLAMA_BASE_URL` privately.

## Security Checklist

- Set `NODE_ENV=production`
- Configure `CORS_ALLOWED_ORIGINS`
- Keep `MYSQL_PASSWORD` secret
- Keep `OLLAMA_BASE_URL` private when possible
- Use HTTPS for both frontend and backend domains

## Quick Test After Deploy

1. `GET https://your-backend-domain/health`
2. Open frontend and create/read tasks.
3. Ask assistant: `what task has been done`

## Notes

- Free tiers and limits change often by provider.
- If you need consistent low-latency AI at scale, you will likely need paid compute.
