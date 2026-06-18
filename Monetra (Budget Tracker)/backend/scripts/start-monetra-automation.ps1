$ErrorActionPreference = "Stop"

$BackendRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$RunDir = Join-Path $BackendRoot ".run"
$PythonExe = Join-Path $BackendRoot ".venv\Scripts\python.exe"
$RunPy = Join-Path $BackendRoot "run.py"
$LogFile = Join-Path $RunDir "scheduled-automation.log"
$BackendOut = Join-Path $RunDir "scheduled-backend.out.log"
$BackendErr = Join-Path $RunDir "scheduled-backend.err.log"
$OllamaOut = Join-Path $RunDir "scheduled-ollama.out.log"
$OllamaErr = Join-Path $RunDir "scheduled-ollama.err.log"

New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Write-SchedulerLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "$timestamp | $Message"
}

function Test-PortListening {
    param([int]$Port)
    try {
        return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    } catch {
        return $false
    }
}

Write-SchedulerLog "Monetra automation launcher started."

if (-not (Test-PortListening -Port 5432)) {
    Write-SchedulerLog "PostgreSQL does not appear to be listening on port 5432. Attempting to start a local PostgreSQL service if one exists."
    $postgresServices = Get-Service -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -like "postgresql*" -or $_.DisplayName -like "postgresql*"
    }
    foreach ($service in $postgresServices) {
        if ($service.Status -ne "Running") {
            try {
                Start-Service -Name $service.Name
                Write-SchedulerLog "Requested start for PostgreSQL service '$($service.Name)'."
            } catch {
                Write-SchedulerLog "Could not start PostgreSQL service '$($service.Name)': $($_.Exception.Message)"
            }
        }
    }
}

if (-not (Test-PortListening -Port 11434)) {
    $ollamaCommand = Get-Command ollama.exe -ErrorAction SilentlyContinue
    if ($ollamaCommand) {
        Write-SchedulerLog "Ollama is not listening on port 11434. Starting 'ollama serve' hidden."
        Start-Process `
            -FilePath $ollamaCommand.Source `
            -ArgumentList "serve" `
            -WindowStyle Hidden `
            -RedirectStandardOutput $OllamaOut `
            -RedirectStandardError $OllamaErr
        Start-Sleep -Seconds 5
    } else {
        Write-SchedulerLog "ollama.exe was not found on PATH."
    }
}

if (-not (Test-Path $PythonExe)) {
    Write-SchedulerLog "Python virtual environment was not found at '$PythonExe'."
    exit 1
}

if (Test-PortListening -Port 5000) {
    Write-SchedulerLog "Backend already appears to be listening on port 5000. No new backend process started."
    exit 0
}

Write-SchedulerLog "Starting Monetra backend hidden from '$BackendRoot'."
Start-Process `
    -FilePath $PythonExe `
    -ArgumentList "`"$RunPy`"" `
    -WorkingDirectory $BackendRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $BackendOut `
    -RedirectStandardError $BackendErr

Start-Sleep -Seconds 8
if (Test-PortListening -Port 5000) {
    Write-SchedulerLog "Monetra backend is now listening on port 5000."
} else {
    Write-SchedulerLog "Monetra backend did not start listening on port 5000. Check scheduled-backend.err.log and monetra.log."
}
