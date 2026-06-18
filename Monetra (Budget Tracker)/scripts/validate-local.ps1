param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$SkipDocker,
    [switch]$RunLoad,
    [switch]$RunChaosSmoke
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendRoot = Join-Path $ProjectRoot "backend"
$FrontendRoot = Join-Path $ProjectRoot "frontend"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

Push-Location $ProjectRoot
try {
    if (-not $SkipBackend) {
        Write-Step "Running backend pytest coverage gate"
        Push-Location $BackendRoot
        try {
            if (Test-Path ".venv\Scripts\python.exe") {
                & ".venv\Scripts\python.exe" -m pytest
            } else {
                python -m pytest
            }
        } finally {
            Pop-Location
        }
    }

    if (-not $SkipFrontend) {
        Write-Step "Running frontend Jest tests"
        Push-Location $FrontendRoot
        try {
            npm.cmd test
            Write-Step "Running TypeScript check"
            npx.cmd tsc --noEmit
        } finally {
            Pop-Location
        }
    }

    if (-not $SkipDocker) {
        Write-Step "Building and starting local Docker stack"
        docker compose up -d --build

        Write-Step "Checking backend health"
        Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 20 | ConvertTo-Json -Depth 5

        Write-Step "Checking frontend"
        Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 20 | Out-Null
        Write-Host "Frontend responded on http://localhost:3000"

        $EnvFile = Join-Path $BackendRoot ".env"
        $SmtpHost = ""
        if (Test-Path $EnvFile) {
            $SmtpHostLine = Select-String -Path $EnvFile -Pattern "^SMTP_HOST=" | Select-Object -First 1
            if ($SmtpHostLine) {
                $SmtpHost = $SmtpHostLine.Line.Split("=", 2)[1].Trim()
            }
        }

        if ($SmtpHost -eq "mailpit") {
            Write-Step "Checking Mailpit captured email inbox"
            Invoke-WebRequest -Uri "http://localhost:8025" -UseBasicParsing -TimeoutSec 20 | Out-Null
            Write-Host "Mailpit responded on http://localhost:8025"
        } else {
            Write-Step "Checking email mode"
            Write-Host "Mailpit is not enabled. Current SMTP_HOST=$SmtpHost, so emails use the configured real SMTP provider."
        }
    }

    if ($RunLoad) {
        Write-Step "Running dummy-user/load test"
        docker compose --profile load run --rm load-test-runner
    }

    if ($RunChaosSmoke) {
        Write-Step "Running controlled chaos smoke drill"
        powershell -ExecutionPolicy Bypass -File "chaos\run-controlled-chaos.ps1" -Drill ChaosSmoke
    }

    Write-Step "Local validation completed"
} finally {
    Pop-Location
}
