# Monetra Production Infrastructure

Use this folder to create the production Oracle VM and its network from Terraform.

(First deployed to a staging environment, then to production.)

Production creates its own VCN, subnet, security list, public IP, and VM state.

If your Oracle tenancy only allows one `2 OCPU / 12 GB` A1 VM, terminate staging and permanently delete its boot volume before applying this production stack.

## What This Creates

- Oracle A1 Flex production VM
- public VCN/subnet
- internet gateway and route table
- SSH access
- HTTP and HTTPS ingress
- no direct public access to ports `3000` or `8000` by default
- Docker and Docker Compose installed on first boot
- optional Ollama installation and model pulls

## First-Time Setup

```powershell
cd "C:\Users\rusha\RD Documents\Rushabh's career\GitHub Portfolio\Rushabh_Dharamshi_Portfolio\Monetra (Budget Tracker)\infra\oracle\environments\production"
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

Fill in:

- `tenancy_ocid`
- `user_ocid`
- `fingerprint`
- `private_key_path`
- `compartment_ocid`
- `ssh_public_key`

For production, replace `ssh_allowed_cidr = "0.0.0.0/0"` with your own public IP in `/32` format when possible.

## Create Production

```powershell
terraform init
terraform fmt -recursive
terraform validate
terraform plan
terraform apply
```

If Oracle reports `Out of host capacity`, try another availability domain or run the retry helper:

```powershell
powershell -ExecutionPolicy Bypass -File "..\..\..\scripts\oracle-production-terraform-retry.ps1" -IUnderstandFreeTierLimits
```

## After Terraform Succeeds

Terraform prints the public IP and SSH command. Then production deployment should be handled by CircleCI:

```text
tests -> build -> E2E -> reliability checks -> manual approval -> deploy production -> smoke test production
```

Terraform creates infrastructure. CircleCI deploys the Monetra app.
