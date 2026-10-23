#requires -Version 7.2
# Real child pwsh fixtures exercise report/exit handling, not Unreal execution.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
. (Join-Path $PSScriptRoot '../Common.ps1')
. (Join-Path $PSScriptRoot '../AssetDiagnostics.ps1')
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('Dawn 에셋 diagnostics '+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary | Out-Null
$nativeInvoker=${function:Invoke-DawnCommand}
$childPwsh=(Get-Process -Id $PID).Path
$fixture=Join-Path $temporary 'editor fixture.ps1'
$report=Join-Path $temporary 'Saved report.json'
$evidence=Join-Path $temporary 'Evidence'
$checks=0
function Require([bool]$Condition,[string]$Message) { if (-not $Condition) { throw $Message }; $script:checks++ }
function Invoke-DawnCommand([string]$File,[string[]]$Arguments,[string]$Log) {
    $script:receivedArguments=$Arguments
    & $script:nativeInvoker $script:childPwsh @('-NoLogo','-NoProfile','-File',$script:fixture,'-Report',$script:report,'-Scenario',$script:scenario,'-Mode',$script:mode) $Log
}
function Run-Case([string]$Scenario,[string]$Mode='generation') {
    $script:scenario=$Scenario; $script:mode=$Mode
    $script:lastFailure=$null
    $script:lastConsole=Join-Path $temporary ($Scenario+'-'+$Mode+'-captured.log')
    try {
        Invoke-DawnAssetEditorPass -Editor 'fixture-editor' -ProjectFile 'C:\game folder\한국어\Demo.uproject' -Generator 'C:\game folder\generate.py' -ReportPath $report -EvidenceDirectory $evidence -Mode $Mode *> $script:lastConsole
    } catch { $script:lastFailure=$_.Exception.Message }
}
try {
    [IO.File]::WriteAllText($fixture,@'
param([string]$Report,[string]$Scenario,[string]$Mode)
$data=@{mode=$Mode;status='passed'}
switch ($Scenario) {
    'missing' { Write-Output 'Fixture native process produced no report'; exit 0 }
    'corrupt' { [IO.File]::WriteAllText($Report,'{broken report'); exit 0 }
    'schema' { $data=@{mode=$Mode} }
    'wrong-mode' { $data.mode='unexpected-mode' }
    'running' { $data.status='running' }
    'failed' { $data.status='failed' }
    'native-failed' { $data.status='failed' }
}
if ($data.status -eq 'failed') {
    $data.error='TypeError: DawnDialogueNode Illustration SoftObjectProperty cannot nativize SoftObjectPath as Object (allowed Texture2D)'
    $data.traceback="Traceback (most recent call last):`n  File generate_demo_assets.py, line 147`nTypeError: use Texture2D object"
}
[IO.File]::WriteAllText($Report,($data|ConvertTo-Json))
Write-Output 'Fixture report written'
if ($Scenario -in @('native-failed','native-passed')) { exit 37 }
exit 0
'@)
    Run-Case 'passed'
    Require (-not $lastFailure) 'Passed generation was rejected'
    Require ($receivedArguments -contains 'C:\game folder\한국어\Demo.uproject') 'Project argument split or changed'
    Require ($receivedArguments -contains '-ExecutePythonScript=C:\game folder\generate.py') 'Python script argument split or changed'
    Require ($receivedArguments -contains '-stdout' -and $receivedArguments -contains '-UTF8Output') 'Editor log output flags missing'
    $firstLog=@($receivedArguments | Where-Object {$_ -like '-ABSLOG=*'})[0]
    Require ([IO.Path]::IsPathRooted($firstLog.Substring(8))) 'Editor log path is not absolute'
    Run-Case 'passed' 'reload-verification'
    Require (-not $lastFailure -and $receivedArguments -contains '-PODVerifyAssets') 'Reload pass or mode flag failed'
    Require (@($receivedArguments | Where-Object {$_ -like '-ABSLOG=*'})[0] -ne $firstLog) 'Editor log reused between invocations'
    Run-Case 'failed'
    Require ($lastFailure -match 'TypeError: DawnDialogueNode') 'Failed report was hidden or accepted with native exit 0'
    $output=Get-Content -Raw -LiteralPath $lastConsole
    Require ($output -match 'Python traceback:' -and $output -match 'use Texture2D object') 'Python traceback did not reach console'
    $failedCopy=Get-Content -Raw -LiteralPath (Join-Path $evidence 'asset-generation-report.json') | ConvertFrom-Json
    Require ($failedCopy.status -eq 'failed' -and $failedCopy.error -match 'SoftObjectProperty') 'Failure report was not preserved in Evidence'
    Run-Case 'failed' 'reload-verification'
    Require ($lastFailure -match 'TypeError: DawnDialogueNode' -and (Test-Path -LiteralPath (Join-Path $evidence 'asset-verification-report.json'))) 'Reload failure report not preserved/rejected'
    Run-Case 'native-failed'
    Require ($lastFailure -match '37' -and $lastFailure -match 'SoftObjectProperty') 'Native failure prevented report capture'
    Run-Case 'native-passed'
    Require ($lastFailure -match '37') 'Passed report overrode nonzero native exit'
    Run-Case 'missing'
    Require ($lastFailure -match 'not produced') 'Previous passed report was reused after missing current report'
    Require (@(Get-ChildItem -LiteralPath $evidence -Filter '*-previous-*.json').Count -gt 0) 'Previous diagnostic report was discarded'
    Run-Case 'corrupt'
    Require ($lastFailure -match 'invalid JSON') 'Corrupt report not distinguished'
    Require ((Get-Content -Raw -LiteralPath (Join-Path $evidence 'asset-generation-report.json')) -eq '{broken report') 'Corrupt report bytes not preserved'
    Run-Case 'schema'
    Require ($lastFailure -match 'no status') 'Missing status not rejected explicitly'
    Run-Case 'wrong-mode'
    Require ($lastFailure -match 'mode mismatch') 'Passed report from another mode accepted'
    Run-Case 'running'
    Require ($lastFailure -match 'status=running') 'Incomplete report accepted'
    "PASS $checks asset diagnostics assertions: real child process fixtures; report and native-exit gates; failed/corrupt/previous reports preserved; Python traceback visible; generation/reload modes; unique logs and space/Unicode paths. No Unreal execution."
} finally {
    ${function:Invoke-DawnCommand}=$nativeInvoker
    Remove-Item -LiteralPath $temporary -Recurse -Force
}
