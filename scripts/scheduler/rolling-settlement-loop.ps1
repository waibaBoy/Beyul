# Rolling market creation + settlement automation scheduler.
# Runs every $IntervalSeconds, calling:
#   POST /api/v1/admin/rolling/up-down/run
#   POST /api/v1/admin/settlement/run
#
# Usage:
#   .\scripts\scheduler\rolling-settlement-loop.ps1
#   .\scripts\scheduler\rolling-settlement-loop.ps1 -ApiBaseUrl "http://localhost:8000" -IntervalSeconds 60
#
# Set SATTA_ADMIN_TOKEN or pass -AdminToken for auth.

param(
    [string]$ApiBaseUrl = "http://localhost:8000",
    [string]$AdminToken = $env:SATTA_ADMIN_TOKEN,
    [int]$IntervalSeconds = 60,
    [string]$Symbol = "BTCUSDT",
    [int]$IntervalMinutes = 5,
    [int]$LookaheadWindows = 3,
    [switch]$FinalizeDueMarkets,
    [switch]$DryRun
)

if (-not $AdminToken) {
    Write-Host "[scheduler] ERROR: No admin token. Set SATTA_ADMIN_TOKEN or pass -AdminToken." -ForegroundColor Red
    exit 1
}

$headers = @{
    "Content-Type"  = "application/json"
    "Authorization" = "Bearer $AdminToken"
}

function Invoke-SafePost {
    param([string]$Url, [hashtable]$Body)
    $json = $Body | ConvertTo-Json -Depth 4
    try {
        $response = Invoke-RestMethod -Uri $Url -Method Post -Headers $headers -Body $json -ErrorAction Stop
        return $response
    } catch {
        $status = $_.Exception.Response.StatusCode.value__
        $detail = $_.ErrorDetails.Message
        Write-Host "[scheduler] WARN: $Url returned $status — $detail" -ForegroundColor Yellow
        return $null
    }
}

Write-Host "[scheduler] Starting rolling + settlement loop"
Write-Host "[scheduler] API: $ApiBaseUrl | Symbol: $Symbol | Interval: ${IntervalMinutes}m | Every: ${IntervalSeconds}s"
Write-Host "[scheduler] DryRun: $DryRun | FinalizeDue: $FinalizeDueMarkets"
Write-Host ""

while ($true) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    # Step 1: rolling market creation
    $rollingBody = @{
        symbol                    = $Symbol
        interval_minutes          = $IntervalMinutes
        lookahead_windows         = $LookaheadWindows
        auto_open_markets         = $true
        request_settlement_for_due = $true
        finalize_due_markets      = [bool]$FinalizeDueMarkets
    }
    Write-Host "[$ts] Running rolling up-down cycle..." -ForegroundColor Cyan
    $rollingResult = Invoke-SafePost -Url "$ApiBaseUrl/api/v1/admin/rolling/up-down/run" -Body $rollingBody
    if ($rollingResult) {
        $created = ($rollingResult.created_markets -join ", ") 
        $opened  = ($rollingResult.opened_markets -join ", ")
        $settled = ($rollingResult.settlement_requested -join ", ")
        $warns   = ($rollingResult.warnings -join "; ")
        if ($created) { Write-Host "  Created: $created" -ForegroundColor Green }
        if ($opened)  { Write-Host "  Opened:  $opened" -ForegroundColor Green }
        if ($settled) { Write-Host "  Settlement requested: $settled" -ForegroundColor Yellow }
        if ($warns)   { Write-Host "  Warnings: $warns" -ForegroundColor Red }
        if (-not $created -and -not $opened -and -not $settled) {
            Write-Host "  No changes (windows already exist)." -ForegroundColor DarkGray
        }
    }

    # Step 2: settlement automation
    $settlementBody = @{
        reconcile_due_markets    = $true
        finalize_settled_markets = $true
        include_disputed         = $false
        dry_run                  = [bool]$DryRun
    }
    Write-Host "[$ts] Running settlement automation..." -ForegroundColor Cyan
    $settlementResult = Invoke-SafePost -Url "$ApiBaseUrl/api/v1/admin/settlement/run" -Body $settlementBody
    if ($settlementResult) {
        $reconciled = ($settlementResult.reconciled_markets -join ", ")
        $finalized  = ($settlementResult.finalized_markets -join ", ")
        $skipped    = ($settlementResult.skipped_markets -join ", ")
        $warns2     = ($settlementResult.warnings -join "; ")
        if ($reconciled) { Write-Host "  Reconciled: $reconciled" -ForegroundColor Green }
        if ($finalized)  { Write-Host "  Finalized:  $finalized" -ForegroundColor Green }
        if ($skipped)    { Write-Host "  Skipped:    $skipped" -ForegroundColor DarkGray }
        if ($warns2)     { Write-Host "  Warnings:   $warns2" -ForegroundColor Red }
        if (-not $reconciled -and -not $finalized -and -not $skipped) {
            Write-Host "  No markets pending settlement." -ForegroundColor DarkGray
        }
    }

    Write-Host "[$ts] Sleeping ${IntervalSeconds}s..." -ForegroundColor DarkGray
    Start-Sleep -Seconds $IntervalSeconds
}
