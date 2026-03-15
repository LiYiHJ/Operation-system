$ErrorActionPreference = 'Stop'

$RepoRoot = 'C:\Operation-system\System'
$BaseUrl = 'http://127.0.0.1:5000'
$Operator = 'import_gate_regression'
$ShopId = 1
$OutDir = Join-Path $RepoRoot 'docs'
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$OutFile = Join-Path $OutDir ("p0_import_gate_regression_{0}.json" -f $Timestamp)

$samples = @(
    @{ name = 'ru_real_xlsx'; path = 'C:\Operation-system\System\data\analytics_report_2026-03-12_23_49.xlsx' },
    @{ name = 'cn_real_xlsx'; path = 'C:\Operation-system\System\data\销售数据分析.xlsx' },
    @{ name = 'ru_bad_header_xlsx'; path = 'C:\Operation-system\System\sample_data\ozon_bad_header_or_missing_sku.xlsx' }
)

$result = @()

foreach ($sample in $samples) {
    if (-not (Test-Path $sample.path)) {
        $result += [ordered]@{
            sample = $sample.name
            path = $sample.path
            upload = @{ status = 'missing_file' }
            confirm = $null
        }
        continue
    }

    $resolved = (Resolve-Path $sample.path).Path
    Write-Host "Uploading $($sample.name) -> $resolved"

    $uploadJson = curl.exe -sS -X POST `
      -F "file=@$resolved" `
      -F "shop_id=$ShopId" `
      -F "operator=$Operator" `
      "$BaseUrl/api/import/upload"

    $upload = $uploadJson | ConvertFrom-Json
    $confirm = $null

    if ($upload.sessionId) {
        $body = @{ sessionId = [int]$upload.sessionId; shopId = $ShopId; manualOverrides = @() } | ConvertTo-Json -Depth 8
        $confirmJson = curl.exe -sS -X POST `
          -H "Content-Type: application/json" `
          -d $body `
          "$BaseUrl/api/import/confirm"
        $confirm = $confirmJson | ConvertFrom-Json
    }

    $result += [ordered]@{
        sample = $sample.name
        path = $resolved
        upload = [ordered]@{
            sessionId = $upload.sessionId
            transportStatus = $upload.transportStatus
            semanticStatus = $upload.semanticStatus
            finalStatus = $upload.finalStatus
            semanticGateReasons = $upload.semanticGateReasons
            riskOverrideReasons = $upload.riskOverrideReasons
            semanticAcceptanceReason = $upload.semanticAcceptanceReason
            mappedCount = $upload.mappedCount
            unmappedCount = $upload.unmappedCount
            mappingCoverage = $upload.semanticMetrics.mappingCoverage
            headerStructureScore = $upload.headerStructureScore
            headerStructureRiskSignals = $upload.headerStructureRiskSignals
            preRecoveryStatus = $upload.preRecoveryStatus
            postRecoveryStatus = $upload.postRecoveryStatus
            recoveryAttempted = $upload.recoveryAttempted
            headerRecoveryApplied = $upload.headerRecoveryApplied
            recoveryImproved = $upload.recoveryImproved
            recoveryDiff = $upload.recoveryDiff
            mappedCanonicalFields = $upload.mappedCanonicalFields
            topUnmappedHeaders = $upload.topUnmappedHeaders
        }
        confirm = if ($confirm) {
            [ordered]@{
                importedRows = $confirm.importedRows
                errorRows = $confirm.errorRows
                quarantineCount = $confirm.quarantineCount
                factLoadErrors = $confirm.factLoadErrors
                transportStatus = $confirm.transportStatus
                semanticStatus = $confirm.semanticStatus
                finalStatus = $confirm.finalStatus
                semanticGateReasons = $confirm.semanticGateReasons
                riskOverrideReasons = $confirm.riskOverrideReasons
                recoverySummary = $confirm.recoverySummary
            }
        } else {
            $null
        }
    }
}

$result | ConvertTo-Json -Depth 10 | Set-Content -Path $OutFile -Encoding UTF8
Write-Host "Saved regression report: $OutFile"
