#requires -Version 7.2
# Dot-source after Common.ps1. Python exceptions may leave the full Editor's
# process exit code at zero, so both the report and the native result are gates.
function Get-DawnAssetReportText($Report,[string]$Name) {
    if ($null -eq $Report) { return '' }
    $property=$Report.PSObject.Properties[$Name]
    if ($null -eq $property -or $null -eq $property.Value) { return '' }
    return [string]$property.Value
}

function Invoke-DawnAssetEditorPass {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Editor,
        [Parameter(Mandatory)][string]$ProjectFile,
        [Parameter(Mandatory)][string]$Generator,
        [Parameter(Mandatory)][string]$ReportPath,
        [Parameter(Mandatory)][string]$EvidenceDirectory,
        [Parameter(Mandatory)][ValidateSet('generation','reload-verification')][string]$Mode
    )
    $attempt=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
    $label=if ($Mode -eq 'generation') { 'GenerateDemoAssets' } else { 'VerifyDemoAssets' }
    $reportName=if ($Mode -eq 'generation') { 'asset-generation-report' } else { 'asset-verification-report' }
    $EvidenceDirectory=[IO.Path]::GetFullPath($EvidenceDirectory)
    New-Item -ItemType Directory -Path $EvidenceDirectory -Force | Out-Null
    $engineLog=Join-Path $EvidenceDirectory "$label-$attempt-editor.log"
    $consoleLog=Join-Path $EvidenceDirectory "$label-$attempt-console.log"
    $savedReport=Join-Path $EvidenceDirectory "$reportName-$attempt.json"
    if (Test-Path -LiteralPath $ReportPath -PathType Leaf) {
        # Retain the last failure before deleting the old success/failure gate.
        Copy-Item -LiteralPath $ReportPath -Destination (Join-Path $EvidenceDirectory "$reportName-previous-$attempt.json")
        Remove-Item -LiteralPath $ReportPath
    }
    $arguments=@($ProjectFile,"-ExecutePythonScript=$Generator",'-unattended','-nosplash','-UTF8Output','-stdout',"-ABSLOG=$engineLog")
    if ($Mode -eq 'reload-verification') { $arguments+='-PODVerifyAssets' }
    Write-Host "Full Unreal Editor log: $engineLog"
    $nativeFailure=$null
    try { Invoke-DawnCommand $Editor $arguments $consoleLog }
    catch { $nativeFailure=$_.Exception.Message }

    # Collect the JSON even when the Editor process failed. Copy before checking
    # status so the original Python error survives the wrapper exception.
    $reportFailure=$null
    if (-not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) {
        $reportFailure="Asset report was not produced: $ReportPath. Inspect the full Unreal Editor log."
    } else {
        try {
            Copy-Item -LiteralPath $ReportPath -Destination $savedReport
            Copy-Item -LiteralPath $ReportPath -Destination (Join-Path $EvidenceDirectory "$reportName.json") -Force
        } catch {
            $reportFailure="Cannot preserve asset report $ReportPath`: $($_.Exception.Message)"
        }
        if (-not $reportFailure) {
            $data=$null
            try { $data=Get-Content -Raw -LiteralPath $savedReport -Encoding utf8 | ConvertFrom-Json }
            catch { $reportFailure="Asset report is invalid JSON: $savedReport. $($_.Exception.Message)" }
            if (-not $reportFailure) {
                $status=Get-DawnAssetReportText $data 'status'
                $reportedMode=Get-DawnAssetReportText $data 'mode'
                $errorText=Get-DawnAssetReportText $data 'error'
                $trace=Get-DawnAssetReportText $data 'traceback'
                if ($errorText) { Write-Host "Asset error: $errorText" }
                if ($trace) { Write-Host 'Python traceback:'; Write-Host $trace }
                if (-not $status) { $reportFailure="Asset report has no status: $savedReport" }
                elseif ($status -ne 'passed') {
                    $detail=if ($errorText) { $errorText } else { "status=$status" }
                    $reportFailure="Asset $Mode failed: $detail. Report: $savedReport"
                } elseif ($reportedMode -ne $Mode) {
                    $reportFailure="Asset report mode mismatch: expected $Mode, received '$reportedMode'. Report: $savedReport"
                }
            }
        }
        Write-Host "Asset report source: $ReportPath"
        if (Test-Path -LiteralPath $savedReport -PathType Leaf) { Write-Host "Preserved asset report: $savedReport" }
    }
    if ($nativeFailure -or $reportFailure) {
        Write-Host "Full Unreal Editor log: $engineLog"
        Write-Host "Captured process output: $consoleLog"
        $details=@()
        if ($nativeFailure) { $details+="Editor process failed: $nativeFailure" }
        if ($reportFailure) { $details+=$reportFailure }
        throw ($details -join "`n")
    }
    return [pscustomobject]@{ mode=$Mode; report=$savedReport; editorLog=$engineLog; consoleLog=$consoleLog }
}
