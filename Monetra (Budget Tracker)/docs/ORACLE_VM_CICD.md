# Oracle VM CI/CD

Monetra deploys to one Oracle production VM through CircleCI.

(First deployed to a manually created Oracle staging VM, then to a Terraform-managed Oracle production VM.)

The current workflow is production-only:

```text
push to main
-> backend tests
-> frontend tests and TypeScript
-> Docker build
-> Playwright E2E
-> dummy/load checks
-> controlled chaos smoke checks
-> manual approval
-> production deploy over SSH
-> production smoke check inside the VM
```

Staging was created and validated manually through the Oracle console before production. Terraform is now kept for production infrastructure only.

## Required VM Setup

The production VM should have:

- Oracle Linux 9 on an Ampere A1 shape
- Docker Engine and Docker Compose plugin
- Ollama installed and reachable from Docker via `http://host.docker.internal:11434`
- `qwen2.5:7b` and `nomic-embed-text` pulled in Ollama
- the Monetra repo cloned at `/opt/monetra`
- `/opt/monetra/.env.production`
- `/opt/monetra/Monetra (Budget Tracker)/backend/.env`

Terraform creates the VCN, subnet, route table, security list, public IP, VM, and first-boot bootstrap. See `infra/oracle/README.md`.

## CircleCI Environment Variables

Store these in CircleCI project environment variables:

```text
PROD_ORACLE_VM_HOST=<production_public_ip>
PROD_ORACLE_VM_USER=opc
PROD_ORACLE_VM_SSH_KEY_B64=<base64 private SSH key>
PROD_MONETRA_APP_DIR=/opt/monetra
PROD_MONETRA_BASE_URL=http://<production_public_ip>:8000
PROD_MONETRA_FRONTEND_URL=http://<production_public_ip>:3000
```

Generate the SSH key value locally:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("$env:USERPROFILE\.ssh\monetra_oracle_vm.key")) | Set-Clipboard
```

Paste the clipboard value into `PROD_ORACLE_VM_SSH_KEY_B64`.

## Remote Deploy Command

CircleCI streams `deploy/remote-compose-deploy.sh` to the VM. It effectively runs:

```bash
APP_DIR="/opt/monetra" \
GIT_BRANCH="main" \
COMPOSE_FILE="Monetra (Budget Tracker)/docker-compose.yml" \
ENV_FILE=".env.production" \
bash -s
```

The script pulls the latest `main` branch and runs:

```bash
docker compose --env-file .env.production -f "Monetra (Budget Tracker)/docker-compose.yml" up -d --build --remove-orphans
```

## Production Smoke Checks

After deployment, verify:

```powershell
curl http://<production_public_ip>:3000/api/health
curl http://<production_public_ip>:8000/api/health
```

Then open:

```text
http://<production_public_ip>:3000
```

Minimum product smoke checks:

- register or login
- add an expense
- set monthly budget and income
- reindex RAG
- ask a deterministic RAG question
- run one Automation Center workflow
- generate a PDF report
- check the latency monitor
- test demo email with an `@monetra.test` account
- test one real Gmail email only if the allowlist and app password are correct

## Production Rule

Production deploys only after all automated gates pass and the manual CircleCI approval is clicked. Do not bypass the approval gate for normal application changes.
