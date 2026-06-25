param(
    [int]$MaxAttempts = 72,

    [int]$SleepSeconds = 600
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Environment = "production"
$TerraformDir = Join-Path $RepoRoot "infra\oracle\environments\production"

if (-not (Test-Path $TerraformDir)) {
    throw "Terraform environment folder not found: $TerraformDir"
}

Push-Location $TerraformDir
try {
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        Write-Host "Terraform apply attempt $attempt of $MaxAttempts for $Environment at $timestamp"

        $output = terraform apply -auto-approve 2>&1
        $exitCode = $LASTEXITCODE
        $text = $output | Out-String

        Write-Host $text

        if ($exitCode -eq 0) {
            Write-Host "SUCCESS: Terraform created or updated the production infrastructure."
            break
        }

        if ($text -match "Out of host capacity|Out of capacity|capacity") {
            Write-Host "Oracle capacity unavailable. Waiting $SleepSeconds seconds before retrying..."
            Start-Sleep -Seconds $SleepSeconds
            continue
        }

        Write-Host "Stopped because this does not look like a capacity error."
        exit $exitCode
    }
}
finally {
    Pop-Location
}
