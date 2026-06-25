param(
    [int]$MaxAttempts = 72,
    [int]$SleepSeconds = 600,
    [switch]$IUnderstandFreeTierLimits
)

$ErrorActionPreference = "Stop"

if (-not $IUnderstandFreeTierLimits) {
    Write-Host "Production VM retry is blocked by default."
    Write-Host "If your Oracle tenancy only allows one 2 OCPU / 12 GB A1 VM, terminate any old VM and delete its boot volume before creating production."
    Write-Host ""
    Write-Host "To continue, rerun with:"
    Write-Host '  -IUnderstandFreeTierLimits'
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RetryScript = Join-Path $ScriptDir "oracle-terraform-retry.ps1"

& $RetryScript -MaxAttempts $MaxAttempts -SleepSeconds $SleepSeconds
