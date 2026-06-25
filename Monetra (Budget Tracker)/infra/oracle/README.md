# Oracle Terraform Infrastructure

This folder lets you create Monetra Oracle Cloud VMs without clicking through the OCI console.

It creates:

- VCN
- public subnet
- internet gateway
- route table
- security list
- Oracle compute instance
- public IP
- first-boot Docker setup through cloud-init

Staging and production can use separate Terraform states:

- `environments/staging`
- `environments/production`

If your Oracle tenancy only allows one `2 OCPU / 12 GB` A1 VM, use the production environment after staging has been validated, then terminate staging and delete its boot volume. In that setup, CircleCI should deploy only to production after the manual approval gate.

## Prerequisites

Install locally:

- Terraform
- OCI CLI configured with a working API key

On Windows, Terraform can be installed with:

```powershell
winget install HashiCorp.Terraform
```

The OCI CLI should already pass:

```powershell
oci iam region list
```

## Create Staging

```powershell
cd "Monetra (Budget Tracker)\infra\oracle\environments\staging"
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
terraform init
terraform fmt -recursive
terraform validate
terraform plan
terraform apply
```

If Oracle returns `Out of host capacity`, change `availability_domain_index` or retry later.

## Create Production

```powershell
cd "Monetra (Budget Tracker)\infra\oracle\environments\production"
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
terraform init
terraform fmt -recursive
terraform validate
terraform plan
terraform apply
```

Production should be created only after staging is working. If you cannot run staging and production together, terminate staging first and confirm its boot volume has been deleted.

## Retry Capacity Automatically

From the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File "Monetra (Budget Tracker)\scripts\oracle-terraform-retry.ps1" -Environment staging
```

The script retries only when Terraform output contains Oracle host-capacity errors. It stops for configuration errors.

For production, use the explicit production wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File "Monetra (Budget Tracker)\scripts\oracle-production-terraform-retry.ps1" -IUnderstandFreeTierLimits
```

Free Tier safety rule: do not run a 12 GB staging VM and a 12 GB production VM at the same time unless your Oracle account limits clearly allow it. Terminate staging and delete its boot volume before creating production if you are trying to stay within the free allowance.

## After The VM Is Created

Terraform prints the public IP and SSH command. Then:

1. SSH into the VM.
2. Clone the Monetra repository into `/opt/monetra`.
3. Copy staging or production env templates.
4. Run `docker compose up -d --build`.
5. Add the VM details to CircleCI deployment variables.

CircleCI then handles repeat deployments after the VM exists.
