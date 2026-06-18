# Oracle VM CI/CD

Monetra can deploy through CircleCI to two Oracle VM environments:

- staging
- production

The production deployment is gated behind a manual CircleCI approval step after staging deployment and smoke checks pass.

## Plain-English Summary

This file explains the future deployment setup.

You do not need this until you have:

- an Oracle Cloud account
- at least one Oracle VM
- SSH access to the VM
- Docker installed on the VM
- CircleCI connected to the GitHub repo

Until then, keep deployment disabled and use local validation.

## Required VM Setup

Each VM should have:

- Ubuntu or another Docker-supported Linux distribution.
- Docker Engine and Docker Compose plugin.
- The Monetra repository cloned, for example at `/opt/monetra`.
- A server-side environment file, for example `.env.staging` or `.env.production`.
- Firewall rules allowing only required public ports, normally `80` and `443`.
- Ollama/model runtime reachable from the backend through `OLLAMA_BASE_URL`.

## CircleCI Environment Variables

Create separate CircleCI contexts for staging and production, or store these as project environment variables.

CircleCI deploy parameter:

- `deploy-oracle=true`

Leave this unset or set to `false` until the Oracle account, VMs, DNS, SSH keys, and environment files are ready. Tests and Docker builds can still run without deploying. When you are ready, trigger the CircleCI pipeline with `deploy-oracle=true`.

Staging:

- `STAGING_ORACLE_VM_HOST`
- `STAGING_ORACLE_VM_USER`
- `STAGING_ORACLE_VM_SSH_KEY_B64`
- `STAGING_MONETRA_APP_DIR`
- `STAGING_MONETRA_BASE_URL`
- `STAGING_MONETRA_FRONTEND_URL`

Production:

- `PROD_ORACLE_VM_HOST`
- `PROD_ORACLE_VM_USER`
- `PROD_ORACLE_VM_SSH_KEY_B64`
- `PROD_MONETRA_APP_DIR`
- `PROD_MONETRA_BASE_URL`
- `PROD_MONETRA_FRONTEND_URL`

`*_ORACLE_VM_SSH_KEY_B64` should be the base64-encoded private SSH key for that VM.

## Deployment Flow

1. Push to `main`.
2. CircleCI runs backend tests.
3. CircleCI runs frontend tests and TypeScript checks.
4. CircleCI builds Docker images.
5. CircleCI runs Playwright E2E.
6. CircleCI deploys to staging over SSH.
7. CircleCI runs staging smoke checks.
8. CircleCI waits for manual approval.
9. CircleCI deploys to production over SSH.
10. CircleCI runs production smoke checks.

## Remote Deploy Command

The CircleCI deployment job streams `deploy/remote-compose-deploy.sh` over SSH. On the VM, that script runs the equivalent of:

```bash
APP_DIR=/opt/monetra \
GIT_BRANCH=main \
COMPOSE_FILE="Monetra (Budget Tracker)/docker-compose.yml" \
ENV_FILE=".env.production" \
bash -s
```

For staging, use a staging env file such as `.env.staging`.

## Smoke Checks

Smoke checks call:

- `GET /api/health`
- optional frontend homepage check when `MONETRA_FRONTEND_URL` is set

Run locally:

```bash
MONETRA_BASE_URL=https://staging.example.com \
MONETRA_FRONTEND_URL=https://staging.example.com \
bash "Monetra (Budget Tracker)/deploy/smoke-test.sh"
```

## Production Rule

Do not deploy directly to production. Production should only run after:

- all tests pass
- Docker builds pass
- staging deploy passes
- staging smoke checks pass
- manual approval is given in CircleCI
