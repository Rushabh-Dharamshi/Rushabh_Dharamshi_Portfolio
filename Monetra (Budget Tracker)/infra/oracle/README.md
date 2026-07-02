# Oracle Terraform Infrastructure

This folder lets you create Monetra Oracle Cloud VMs without clicking through the OCI console.

(First deployed to a manually created Oracle staging VM, then to a Terraform-managed Oracle production VM.)

It creates:

- VCN
- public subnet
- internet gateway
- route table
- security list
- Oracle compute instance
- public IP
- first-boot Docker setup through cloud-init

This repo now keeps Terraform for production only:

- `environments/production`

Staging was created and validated manually through the Oracle console. After staging is terminated, Terraform is used to create the production VM reproducibly.

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

Production should be created only after staging or local validation has passed. If your tenancy only allows one `2 OCPU / 12 GB` A1 VM, terminate any old VM first and confirm its boot volume has been deleted.

## Retry Capacity Automatically

From the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File "Monetra (Budget Tracker)\scripts\oracle-production-terraform-retry.ps1" -IUnderstandFreeTierLimits
```

The script retries only when Terraform output contains Oracle host-capacity errors. It stops for configuration errors.

## After The VM Is Created

Terraform prints the public IP and SSH command. Then:

1. SSH into the VM.
2. Clone the Monetra repository into `/opt/monetra`.
3. Create the production environment file.
4. Run `docker compose up -d --build`.
5. Add the VM details to CircleCI deployment variables.

CircleCI then handles repeat deployments after the VM exists.
