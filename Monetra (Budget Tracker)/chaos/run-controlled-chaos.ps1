param(
    [ValidateSet("ChaosSmoke", "ChromaOutage", "PostgresOutage")]
    [string]$Drill = "ChaosSmoke"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot ".run"
$LogFile = Join-Path $LogDir "chaos-drills.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-ChaosLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "$timestamp | $Message"
    Write-Host "$timestamp | $Message"
}

function Invoke-K6 {
    param([string]$ScriptPath)
    docker compose run --rm `
        -e MONETRA_BASE_URL=http://backend:8000 `
        load-test-runner run $ScriptPath
}

Push-Location $ProjectRoot
try {
    Write-ChaosLog "Starting controlled chaos drill: $Drill"

    if ($Drill -eq "ChaosSmoke") {
        Invoke-K6 "/scripts/k6/monetra-chaos-smoke.js"
        Write-ChaosLog "ChaosSmoke completed."
        exit 0
    }

    if ($Drill -eq "ChromaOutage") {
        Write-ChaosLog "Stopping Chroma to simulate RAG vector-store outage."
        docker compose stop chroma
        Invoke-K6 "/scripts/k6/monetra-chaos-smoke.js"
        Write-ChaosLog "Chroma outage drill completed."
        exit 0
    }

    if ($Drill -eq "PostgresOutage") {
        Write-ChaosLog "Stopping PostgreSQL to simulate database outage."
        docker compose stop postgres
        Invoke-K6 "/scripts/k6/monetra-chaos-smoke.js"
        Write-ChaosLog "PostgreSQL outage drill completed."
        exit 0
    }
} finally {
    if ($Drill -eq "ChromaOutage") {
        Write-ChaosLog "Restarting Chroma."
        docker compose up -d chroma
    }
    if ($Drill -eq "PostgresOutage") {
        Write-ChaosLog "Restarting PostgreSQL."
        docker compose up -d postgres
    }
    Pop-Location
}
