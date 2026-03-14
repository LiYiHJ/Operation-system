param(
    [string]$ApiBase = "http://127.0.0.1:5000/api",
    [int]$ShopId = 1,

    [string]$DbName = "ecom_v51_prod",
    [string]$DbUser = "ecom_user",
    [string]$DbPassword = "strong_password",
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 5432,
    [string]$PsqlPath = "psql",

    [string]$ImportFilePath = "",

    [string]$Provider = "ozon",
    [string]$ClientId = "",
    [string]$SellerId = "",
    [string]$ReadToken = "",
    [string]$ActionToken = "",
    [string[]]$Scopes = @("product_catalog", "promotion_pricing"),

    [string]$SalesBackendUrl = "",
    [switch]$UseMockSalesBackend,

    [string]$BearerToken = "",
    [string]$OutputJsonPath = ".\uat_result.json"
)

$ErrorActionPreference = "Stop"

function Write-Section($title) {
    Write-Host "`n==================== $title ====================" -ForegroundColor Cyan
}

function New-Result($name) {
    return [ordered]@{
        name = $name
        pass = $false
        details = @{}
        error = $null
    }
}

function Get-Headers {
    $headers = @{}
    if ($BearerToken -and $BearerToken.Trim()) {
        $headers["Authorization"] = "Bearer $BearerToken"
    }
    return $headers
}

function Invoke-Api {
    param(
        [Parameter(Mandatory=$true)][string]$Method,
        [Parameter(Mandatory=$true)][string]$Url,
        $Body = $null,
        [switch]$Raw
    )
    $headers = Get-Headers
    if ($Body -ne $null) {
        if ($Raw) {
            return Invoke-WebRequest -Method $Method -Uri $Url -Headers $headers -Body $Body -UseBasicParsing
        }
        return Invoke-RestMethod -Method $Method -Uri $Url -Headers $headers -Body ($Body | ConvertTo-Json -Depth 20) -ContentType "application/json"
    }
    return Invoke-RestMethod -Method $Method -Uri $Url -Headers $headers
}

function Invoke-UploadFile {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(Mandatory=$true)][string]$Url
    )
    if (!(Test-Path $FilePath)) {
        throw "Import file not found: $FilePath"
    }
    $curl = (Get-Command curl.exe -ErrorAction SilentlyContinue)
    if (-not $curl) {
        throw "curl.exe not found. Install curl or adjust this script."
    }

    $args = @("-sS", "-X", "POST")
    $headers = Get-Headers
    foreach ($k in $headers.Keys) {
        $args += @("-H", "$k: $($headers[$k])")
    }
    $args += @("-F", "file=@$FilePath", $Url)
    $output = & curl.exe @args
    if ($LASTEXITCODE -ne 0) {
        throw "curl upload failed with exit code $LASTEXITCODE"
    }
    try {
        return $output | ConvertFrom-Json -Depth 20
    } catch {
        return [ordered]@{ raw = $output }
    }
}

function Invoke-PsqlScalar {
    param([string]$Sql)
    $env:PGPASSWORD = $DbPassword
    $cmd = @(
        "-h", $DbHost,
        "-p", "$DbPort",
        "-U", $DbUser,
        "-d", $DbName,
        "-t", "-A",
        "-c", $Sql
    )
    $output = & $PsqlPath @cmd 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "psql failed: $output"
    }
    return ($output -join "`n").Trim()
}

function Try-GetSessionId($obj) {
    if ($null -eq $obj) { return $null }
    $candidates = @(
        $obj.sessionId,
        $obj.importSessionId,
        $obj.session_id,
        $obj.data.sessionId,
        $obj.data.importSessionId,
        $obj.result.sessionId,
        $obj.result.importSessionId
    )
    foreach ($c in $candidates) {
        if ($c) { return "$c" }
    }
    return $null
}

function Try-ConfirmImport {
    param([string]$SessionId)
    $payloads = @(
        @{ sessionId = $SessionId },
        @{ importSessionId = $SessionId },
        @{ sessionId = $SessionId; shopId = $ShopId },
        @{ importSessionId = $SessionId; shopId = $ShopId }
    )
    foreach ($p in $payloads) {
        try {
            $resp = Invoke-Api -Method POST -Url "$ApiBase/import/confirm" -Body $p
            return [ordered]@{ success = $true; payload = $p; response = $resp }
        } catch {
            continue
        }
    }
    return [ordered]@{ success = $false }
}

$summary = [ordered]@{
    generatedAt = (Get-Date).ToString("s")
    apiBase = $ApiBase
    db = [ordered]@{ host = $DbHost; port = $DbPort; name = $DbName; user = $DbUser }
    results = @()
}

# A. Real DB / core endpoints
$a = New-Result "A_real_db"
Write-Section "A. Real DB / Core Endpoint Checks"
try {
    $health = Invoke-Api -Method GET -Url "$ApiBase/health"
    $dashboard = Invoke-Api -Method GET -Url "$ApiBase/dashboard/overview"
    $reminders = Invoke-Api -Method GET -Url "$ApiBase/reminders/list?shopId=$ShopId"

    $currentDb = Invoke-PsqlScalar "SELECT current_database();"
    $tableReg = Invoke-PsqlScalar "SELECT CONCAT_WS(',', to_regclass('public.sync_run_log'), to_regclass('public.push_delivery_log'), to_regclass('public.import_batch'));"

    $a.pass = $true
    $a.details = [ordered]@{
        health = $health
        dashboard = $dashboard
        reminders = $reminders
        current_database = $currentDb
        key_tables = $tableReg
    }
    Write-Host "PASS: core endpoints reachable and DB query succeeded" -ForegroundColor Green
} catch {
    $a.error = $_.Exception.Message
    Write-Host "FAIL: $($a.error)" -ForegroundColor Red
}
$summary.results += $a

# B. File import
$b = New-Result "B_file_import"
Write-Section "B. File Import Closure"
if ($ImportFilePath -and (Test-Path $ImportFilePath)) {
    try {
        $beforeBatch = Invoke-PsqlScalar "SELECT COUNT(*) FROM import_batch;"
        $beforeSkuDaily = $null
        try { $beforeSkuDaily = Invoke-PsqlScalar "SELECT COUNT(*) FROM fact_sku_daily;" } catch {}

        $uploadResp = Invoke-UploadFile -FilePath $ImportFilePath -Url "$ApiBase/import/upload"
        $sessionId = Try-GetSessionId $uploadResp
        $confirm = $null
        if ($sessionId) {
            $confirm = Try-ConfirmImport -SessionId $sessionId
        }

        $afterBatch = Invoke-PsqlScalar "SELECT COUNT(*) FROM import_batch;"
        $afterSkuDaily = $null
        try { $afterSkuDaily = Invoke-PsqlScalar "SELECT COUNT(*) FROM fact_sku_daily;" } catch {}

        $latestBatch = $null
        try {
            $latestBatch = Invoke-PsqlScalar "SELECT CONCAT_WS('|', id, source_type, platform_code, status, success_count, error_count) FROM import_batch ORDER BY id DESC LIMIT 1;"
        } catch {}

        $dashboardPostImport = $null
        try { $dashboardPostImport = Invoke-Api -Method GET -Url "$ApiBase/dashboard/overview" } catch {}

        $b.pass = (($confirm -and $confirm.success) -or [int]$afterBatch -gt [int]$beforeBatch)
        $b.details = [ordered]@{
            file = $ImportFilePath
            upload_response = $uploadResp
            session_id = $sessionId
            confirm = $confirm
            import_batch_before = $beforeBatch
            import_batch_after = $afterBatch
            fact_sku_daily_before = $beforeSkuDaily
            fact_sku_daily_after = $afterSkuDaily
            latest_batch = $latestBatch
            dashboard_after_import = $dashboardPostImport
        }
        if ($b.pass) {
            Write-Host "PASS: import appears to have completed" -ForegroundColor Green
        } else {
            Write-Host "FAIL: upload/confirm did not produce a clear import closure" -ForegroundColor Red
        }
    } catch {
        $b.error = $_.Exception.Message
        Write-Host "FAIL: $($b.error)" -ForegroundColor Red
    }
} else {
    $b.error = "Skipped: provide -ImportFilePath to run real file import validation."
    Write-Host $b.error -ForegroundColor Yellow
}
$summary.results += $b

# C. Ozon real sync
$c = New-Result "C_ozon_sync"
Write-Section "C. Ozon Sync Closure"
try {
    $domains = Invoke-Api -Method GET -Url "$ApiBase/integration/domains?shopId=$ShopId"

    $saveConfigPayload = [ordered]@{
        provider = $Provider
        shopId = $ShopId
        enabled = $true
        autoSyncEnabled = $false
        syncFrequency = "manual"
        credentials = [ordered]@{
            clientId = $ClientId
            sellerId = $SellerId
            readToken = $ReadToken
            actionToken = $ActionToken
        }
        settings = [ordered]@{}
    }

    $saved = $null
    if ($ClientId -or $ReadToken -or $ActionToken -or $SellerId) {
        $saved = Invoke-Api -Method POST -Url "$ApiBase/integration/data-source" -Body $saveConfigPayload
    }

    $permissionCheck = $null
    $syncOnce = $null
    $syncLogs = $null
    $pricingAutofill = $null
    if ($ClientId -or $ReadToken -or $ActionToken -or $SellerId) {
        $permissionCheck = Invoke-Api -Method POST -Url "$ApiBase/integration/permission-check" -Body @{ shopId = $ShopId; provider = $Provider }
        $syncOnce = Invoke-Api -Method POST -Url "$ApiBase/integration/sync-once" -Body @{ shopId = $ShopId; provider = $Provider; scopes = $Scopes }
        $syncLogs = Invoke-Api -Method GET -Url "$ApiBase/integration/sync-logs?shopId=$ShopId&limit=10"
        try { $pricingAutofill = Invoke-Api -Method GET -Url "$ApiBase/integration/pricing-autofill?shopId=$ShopId&provider=$Provider" } catch {}
    }

    $syncCount = $null
    try { $syncCount = Invoke-PsqlScalar "SELECT COUNT(*) FROM sync_run_log;" } catch {}

    $c.pass = [bool]($syncOnce)
    $c.details = [ordered]@{
        domains = $domains
        config_saved = $saved
        permission_check = $permissionCheck
        sync_once = $syncOnce
        sync_logs = $syncLogs
        pricing_autofill = $pricingAutofill
        sync_run_log_count = $syncCount
        used_real_credentials = [bool]($ClientId -or $ReadToken -or $ActionToken -or $SellerId)
    }
    if ($c.pass) {
        Write-Host "PASS: sync endpoint completed" -ForegroundColor Green
    } else {
        Write-Host "WARN: real credentials not provided or sync not executed" -ForegroundColor Yellow
    }
} catch {
    $c.error = $_.Exception.Message
    Write-Host "FAIL: $($c.error)" -ForegroundColor Red
}
$summary.results += $c

# D. Sales push
$d = New-Result "D_sales_push"
Write-Section "D. Sales Push Closure"
try {
    $target = $SalesBackendUrl
    if (-not $target -and $UseMockSalesBackend) {
        $target = "$ApiBase/integration/mock/sales-backend"
    }

    if ($target) {
        $payload = [ordered]@{
            shopId = $ShopId
            targetUrl = $target
            payload = [ordered]@{
                sku = "SKU-UAT-001"
                actionType = "pricing"
                actionBefore = "price=99"
                actionAfter = "price=109"
                sourcePage = "decision"
                sourceReason = "uat_push"
                operator = "operator"
                confirmedAt = (Get-Date).ToString("o")
            }
        }
        $pushResp = Invoke-Api -Method POST -Url "$ApiBase/integration/push-sales" -Body $payload
        $pushLogs = Invoke-Api -Method GET -Url "$ApiBase/integration/push-logs?shopId=$ShopId&limit=10"
        $pushCount = $null
        try { $pushCount = Invoke-PsqlScalar "SELECT COUNT(*) FROM push_delivery_log;" } catch {}

        $d.pass = $true
        $d.details = [ordered]@{
            target_url = $target
            used_mock = [bool]$UseMockSalesBackend -and (-not $SalesBackendUrl)
            push_response = $pushResp
            push_logs = $pushLogs
            push_delivery_log_count = $pushCount
        }
        Write-Host "PASS: push request executed" -ForegroundColor Green
    } else {
        $d.error = "Skipped: provide -SalesBackendUrl or use -UseMockSalesBackend."
        Write-Host $d.error -ForegroundColor Yellow
    }
} catch {
    $d.error = $_.Exception.Message
    Write-Host "FAIL: $($d.error)" -ForegroundColor Red
}
$summary.results += $d

# Final output
Write-Section "Summary"
$summary | ConvertTo-Json -Depth 30 | Set-Content -Path $OutputJsonPath -Encoding UTF8

foreach ($r in $summary.results) {
    $status = if ($r.pass) { "PASS" } elseif ($r.error) { "FAIL/SKIP" } else { "FAIL" }
    Write-Host ("{0,-18} {1}" -f $r.name, $status)
}

Write-Host "`nDetailed JSON written to: $OutputJsonPath" -ForegroundColor Cyan
Write-Host "Note: real Ozon sync and real sales push only count as real-pass when you provide real credentials/real target URL." -ForegroundColor Yellow
