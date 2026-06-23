param(
    [int]$MaxAttempts = 72,
    [int]$SleepSeconds = 600,
    [switch]$IUnderstandFreeTierLimits
)

$ErrorActionPreference = "Stop"

if (-not $IUnderstandFreeTierLimits) {
    Write-Host "Production VM retry is blocked by default."
    Write-Host "If you are staying on Oracle Free Tier, do not run a 12 GB staging VM and a 12 GB production VM at the same time."
    Write-Host "Terminate staging and delete its boot volume before creating production, unless your account limits clearly allow both."
    Write-Host ""
    Write-Host "To continue, rerun with:"
    Write-Host '  -IUnderstandFreeTierLimits'
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RetryScript = Join-Path $ScriptDir "oracle-terraform-retry.ps1"

& $RetryScript -Environment production -MaxAttempts $MaxAttempts -SleepSeconds $SleepSeconds
