param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$Environment = "local",
    [int]$Iterations = 20,
    [int]$TimeoutSeconds = 30,
    [string]$OutputDir = "latency-results",
    [string]$Username = $env:MONETRA_LATENCY_USERNAME,
    [string]$Password = $env:MONETRA_LATENCY_PASSWORD,
    [string]$UserCredentialCsv = "",
    [switch]$IncludeUnauthenticated,
    [string[]]$Paths = @(
        "/api/health",
        "/api/dashboard",
        "/api/analytics/categories",
        "/api/analytics/financial-pulse",
        "/api/recurring-items/calendar?days=35"
    )
)

$ErrorActionPreference = "Stop"

function Normalize-BaseUrl {
    param([string]$Value)
    return $Value.Trim().TrimEnd("/")
}

function Get-Percentile {
    param(
        [double[]]$Values,
        [double]$Percentile
    )
    if ($Values.Count -eq 0) {
        return $null
    }

    $sorted = @($Values | Sort-Object)
    if ($sorted.Count -eq 1) {
        return [math]::Round($sorted[0], 2)
    }

    $rank = ($Percentile / 100) * ($sorted.Count - 1)
    $lower = [math]::Floor($rank)
    $upper = [math]::Ceiling($rank)
    if ($lower -eq $upper) {
        return [math]::Round($sorted[$lower], 2)
    }

    $weight = $rank - $lower
    $value = ($sorted[$lower] * (1 - $weight)) + ($sorted[$upper] * $weight)
    return [math]::Round($value, 2)
}

function ConvertTo-SafeName {
    param([string]$Value)
    $safe = $Value -replace "https?://", ""
    $safe = $safe -replace "[^A-Za-z0-9_.-]+", "-"
    return $safe.Trim("-")
}

function ConvertTo-MarkdownTable {
    param(
        [object[]]$Rows,
        [string[]]$Columns
    )
    if ($Rows.Count -eq 0) {
        return "_No rows._"
    }

    $header = "| " + ($Columns -join " | ") + " |"
    $separator = "| " + (($Columns | ForEach-Object { "---" }) -join " | ") + " |"
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add($header)
    $lines.Add($separator)
    foreach ($row in $Rows) {
        $values = foreach ($column in $Columns) {
            $value = $row.$column
            if ($null -eq $value) {
                ""
            } else {
                ([string]$value).Replace("|", "\|").Replace("`r", " ").Replace("`n", " ")
            }
        }
        $lines.Add("| " + ($values -join " | ") + " |")
    }
    return ($lines -join [Environment]::NewLine)
}

function Get-LatencyUsers {
    param(
        [string]$CsvPath,
        [string]$SingleUsername,
        [string]$SinglePassword,
        [switch]$AddUnauthenticated
    )

    $users = New-Object System.Collections.Generic.List[object]
    if ($CsvPath) {
        $rows = Import-Csv -Path $CsvPath
        foreach ($row in $rows) {
            $rowUsername = [string]$row.username
            if (-not $rowUsername) {
                $rowUsername = [string]$row.Username
            }
            $rowPassword = [string]$row.password
            if (-not $rowPassword) {
                $rowPassword = [string]$row.Password
            }
            $rowLabel = [string]$row.label
            if (-not $rowLabel) {
                $rowLabel = [string]$row.Label
            }
            if (-not $rowLabel) {
                $rowLabel = $rowUsername
            }
            if ($rowUsername -and $rowPassword) {
                $users.Add([pscustomobject]@{
                    label = $rowLabel
                    username = $rowUsername
                    password = $rowPassword
                    authenticated = $true
                })
            }
        }
    } elseif ($SingleUsername -and $SinglePassword) {
        $users.Add([pscustomobject]@{
            label = $SingleUsername
            username = $SingleUsername
            password = $SinglePassword
            authenticated = $true
        })
    }

    if ($AddUnauthenticated -or $users.Count -eq 0) {
        $users.Add([pscustomobject]@{
            label = "anonymous"
            username = ""
            password = ""
            authenticated = $false
        })
    }

    return $users.ToArray()
}

$base = Normalize-BaseUrl $BaseUrl
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runStartedLocal = Get-Date
$safeEnvironment = ConvertTo-SafeName $Environment
$safeBase = ConvertTo-SafeName $base
$resultRoot = Join-Path $OutputDir "$timestamp-$safeEnvironment-$safeBase"
New-Item -ItemType Directory -Path $resultRoot -Force | Out-Null

$rawResults = New-Object System.Collections.Generic.List[object]
$latencyUsers = @(Get-LatencyUsers -CsvPath $UserCredentialCsv -SingleUsername $Username -SinglePassword $Password -AddUnauthenticated:$IncludeUnauthenticated)

Write-Host "Measuring Monetra latency"
Write-Host "Environment: $Environment"
Write-Host "Base URL: $base"
Write-Host "Iterations per endpoint: $Iterations"
Write-Host "Users measured: $($latencyUsers.Count)"
Write-Host "Output: $resultRoot"

foreach ($latencyUser in $latencyUsers) {
    $safeUser = ConvertTo-SafeName $latencyUser.label
    if (-not $safeUser) {
        $safeUser = "anonymous"
    }
    $reportId = "$timestamp-$safeEnvironment-$safeBase-$safeUser"
    $webSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession

    Write-Host ""
    Write-Host "User: $($latencyUser.label)"
    Write-Host "Report ID: $reportId"

    if ($latencyUser.authenticated) {
        Write-Host "Authenticating as $($latencyUser.username) for protected endpoint measurements"
        $loginBody = @{ username = $latencyUser.username; password = $latencyUser.password } | ConvertTo-Json
        try {
            Invoke-WebRequest `
                -Uri "$base/api/auth/login" `
                -Method POST `
                -Body $loginBody `
                -ContentType "application/json" `
                -WebSession $webSession `
                -UseBasicParsing `
                -TimeoutSec $TimeoutSeconds | Out-Null
            Write-Host "Authentication succeeded"
        } catch {
            Write-Warning "Authentication failed. Protected endpoints may return 401. $($_.Exception.Message)"
        }
    } else {
        Write-Host "Unauthenticated measurement. Protected endpoints may return 401."
    }

    foreach ($path in $Paths) {
        $url = "$base$path"
        Write-Host ""
        Write-Host "Endpoint: $path"

        for ($i = 1; $i -le $Iterations; $i++) {
            $statusCode = $null
            $errorMessage = ""
            $durationMs = $null
            $requestStartedLocal = Get-Date
            $startedAtLocal = $requestStartedLocal.ToString("yyyy-MM-dd HH:mm:ss")
            $startedAtUtc = $requestStartedLocal.ToUniversalTime().ToString("o")
            $safePath = ConvertTo-SafeName $path
            $requestId = "$reportId-$safePath-$i"
            $timer = [System.Diagnostics.Stopwatch]::StartNew()

            try {
                $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $TimeoutSeconds -WebSession $webSession
                $timer.Stop()
                $statusCode = [int]$response.StatusCode
                $durationMs = [math]::Round($timer.Elapsed.TotalMilliseconds, 2)
            } catch {
                $timer.Stop()
                $durationMs = [math]::Round($timer.Elapsed.TotalMilliseconds, 2)
                $errorMessage = $_.Exception.Message
                if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
                    $statusCode = [int]$_.Exception.Response.StatusCode
                }
            }

            $ok = $statusCode -ge 200 -and $statusCode -lt 400
            $rawResults.Add([pscustomobject]@{
                report_id = $reportId
                request_id = $requestId
                user_label = $latencyUser.label
                username = $latencyUser.username
                authenticated = $latencyUser.authenticated
                timestamp_local = $startedAtLocal
                timestamp_utc = $startedAtUtc
                environment = $Environment
                base_url = $base
                method = "GET"
                path = $path
                iteration = $i
                status_code = $statusCode
                ok = $ok
                duration_ms = $durationMs
                error = $errorMessage
            })

            $statusLabel = "ERR"
            if ($null -ne $statusCode) {
                $statusLabel = $statusCode
            }
            Write-Host ("  {0}/{1}: {2} ms status={3}" -f $i, $Iterations, $durationMs, $statusLabel)
        }
    }
}

$summary = foreach ($group in ($rawResults | Group-Object report_id, user_label, username, authenticated, path)) {
    $items = @($group.Group)
    $successful = @($items | Where-Object { $_.ok -eq $true })
    $durations = @($successful | ForEach-Object { [double]$_.duration_ms })
    $failureCount = @($items | Where-Object { $_.ok -ne $true }).Count

    if ($durations.Count -gt 0) {
        $average = [math]::Round(($durations | Measure-Object -Average).Average, 2)
        $minimum = [math]::Round(($durations | Measure-Object -Minimum).Minimum, 2)
        $maximum = [math]::Round(($durations | Measure-Object -Maximum).Maximum, 2)
    } else {
        $average = $null
        $minimum = $null
        $maximum = $null
    }

    $first = $items[0]
    [pscustomobject]@{
        report_id = $first.report_id
        user_label = $first.user_label
        username = $first.username
        authenticated = $first.authenticated
        measured_at_local = $first.timestamp_local
        environment = $Environment
        base_url = $base
        method = "GET"
        path = $first.path
        requests = $items.Count
        successful_requests = $successful.Count
        failed_requests = $failureCount
        avg_ms = $average
        min_ms = $minimum
        max_ms = $maximum
        p50_ms = Get-Percentile $durations 50
        p95_ms = Get-Percentile $durations 95
        p99_ms = Get-Percentile $durations 99
    }
}

$rawCsv = Join-Path $resultRoot "raw-latency.csv"
$summaryCsv = Join-Path $resultRoot "summary-latency.csv"
$summaryJson = Join-Path $resultRoot "summary-latency.json"
$markdownReport = Join-Path $resultRoot "latency-report.md"
$htmlReport = Join-Path $resultRoot "latency-report.html"

$rawResults | Export-Csv -NoTypeInformation -Path $rawCsv
$summary | Export-Csv -NoTypeInformation -Path $summaryCsv
$summary | ConvertTo-Json -Depth 5 | Set-Content -Path $summaryJson -Encoding UTF8

$reportLines = New-Object System.Collections.Generic.List[string]
$reportLines.Add("# Monetra Latency Monitoring Report")
$reportLines.Add("")
$reportLines.Add("| Field | Value |")
$reportLines.Add("| --- | --- |")
$reportLines.Add("| Environment | $Environment |")
$reportLines.Add("| Base URL | $base |")
$reportLines.Add("| Generated local time | $($runStartedLocal.ToString("yyyy-MM-dd HH:mm:ss")) |")
$reportLines.Add("| Generated UTC time | $($runStartedLocal.ToUniversalTime().ToString("o")) |")
$reportLines.Add("| Users measured | $($latencyUsers.Count) |")
$reportLines.Add("| Iterations per endpoint | $Iterations |")
$reportLines.Add("")
$reportLines.Add("## Endpoint Summary")
$reportLines.Add("")
$summaryRows = @($summary | Select-Object report_id,user_label,method,path,requests,successful_requests,failed_requests,avg_ms,min_ms,max_ms,p50_ms,p95_ms,p99_ms)
$reportLines.Add((ConvertTo-MarkdownTable -Rows $summaryRows -Columns @("report_id","user_label","method","path","requests","successful_requests","failed_requests","avg_ms","min_ms","max_ms","p50_ms","p95_ms","p99_ms")))
$reportLines.Add("")
$reportLines.Add("## Per-User API Calls")
foreach ($userGroup in ($rawResults | Group-Object report_id, user_label)) {
    $first = $userGroup.Group[0]
    $reportLines.Add("")
    $reportLines.Add("### $($first.user_label)")
    $reportLines.Add("")
    $reportLines.Add("| Field | Value |")
    $reportLines.Add("| --- | --- |")
    $reportLines.Add("| Report ID | $($first.report_id) |")
    $reportLines.Add("| Username | $($first.username) |")
    $reportLines.Add("| Authenticated | $($first.authenticated) |")
    $reportLines.Add("| First request local time | $($first.timestamp_local) |")
    $reportLines.Add("")
    $callRows = @(
        $userGroup.Group |
            Sort-Object timestamp_utc, path, iteration |
            Select-Object request_id,timestamp_local,method,path,iteration,status_code,ok,duration_ms,error
    )
    $reportLines.Add((ConvertTo-MarkdownTable -Rows $callRows -Columns @("request_id","timestamp_local","method","path","iteration","status_code","ok","duration_ms","error")))
}
$reportMarkdown = $reportLines -join [Environment]::NewLine
$reportMarkdown | Set-Content -Path $markdownReport -Encoding UTF8
$htmlBody = [System.Net.WebUtility]::HtmlEncode($reportMarkdown) -replace "`r?`n", "<br />"
$html = @"
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Monetra Latency Monitoring Report</title>
  <style>
    body { font-family: Consolas, 'Segoe UI', sans-serif; margin: 32px; color: #172033; background: #f7f9fc; }
    main { background: #fff; border: 1px solid #d9e2f1; padding: 24px; border-radius: 8px; }
    code, pre { white-space: pre-wrap; }
  </style>
</head>
<body><main><pre>$htmlBody</pre></main></body>
</html>
"@
$html | Set-Content -Path $htmlReport -Encoding UTF8

Write-Host ""
Write-Host "Latency summary:"
$summary | Format-Table -AutoSize
Write-Host ""
Write-Host "Saved raw results: $rawCsv"
Write-Host "Saved summary CSV: $summaryCsv"
Write-Host "Saved summary JSON: $summaryJson"
Write-Host "Saved markdown report: $markdownReport"
Write-Host "Saved HTML report: $htmlReport"
