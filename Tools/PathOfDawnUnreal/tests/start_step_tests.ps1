#requires -Version 7.2
# Exercise the actual Run-Step function with child pwsh processes; no Unreal is run.
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$true
$tokens=$null; $errors=$null
$source=Join-Path $PSScriptRoot '../StartHere.ps1'
$ast=[System.Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$function=$ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Run-Step'},$true)
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('Dawn 시작 검사 '+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary | Out-Null
try {
    # A real definition file preserves PSScriptRoot for the relative child scripts.
    $definition=Join-Path $temporary 'definition.ps1'
    [IO.File]::WriteAllText($definition,$function.Extent.Text)
    . $definition
    $script:pwsh=(Get-Process -Id $PID).Path
    $script:stamp='regression'
    $script:diagnostic=Join-Path $temporary 'diagnostic.json'
    $script:report=[ordered]@{steps=@()}
    [IO.File]::WriteAllText((Join-Path $temporary 'success.ps1'),@'
param([string]$Value)
[Console]::Error.WriteLine('harmless native stderr')
Write-Output $Value
exit 0
'@)
    Run-Step 'success' 'success.ps1' @('-Value','한국어 path with spaces')
    $contents=Get-Content -Raw -LiteralPath $report.steps[-1].log
    if ($report.steps[-1].exitCode -ne 0 -or $contents -notmatch 'harmless native stderr' -or $contents -notmatch '한국어 path with spaces') { throw 'Success output/arguments were lost.' }
    if ($ErrorActionPreference -ne 'Stop' -or -not $PSNativeCommandUseErrorActionPreference) { throw 'Caller preferences changed.' }
    [IO.File]::WriteAllText((Join-Path $temporary 'failure.ps1'),@'
Write-Output 'fixture build error: shared build settings differ'
[Console]::Error.WriteLine('fixture wrapper exception')
exit 37
'@)
    $caught=$null
    try { Run-Step 'failure' 'failure.ps1' } catch { $caught=$_.Exception.Message }
    if (-not $caught -or $caught -notmatch '37' -or $report.steps[-1].exitCode -ne 37) { throw 'Native failure code was lost.' }
    $contents=Get-Content -Raw -LiteralPath $report.steps[-1].log
    if ($contents -notmatch 'shared build settings differ' -or $contents -notmatch 'fixture wrapper exception') { throw 'Failure log was truncated.' }
    [IO.File]::WriteAllText((Join-Path $temporary 'compiler.ps1'),@'
Write-Output 'DawnPlayerController.cpp(227,31): error C4458: Player hides a class member'
Write-Output 'PlayerController.h(272,22): note: see declaration of Player'
1..40 | ForEach-Object { Write-Output 'wrapper tail: no compiler diagnostic here' }
exit 6
'@)
    $caught=$null
    try { Run-Step 'compiler' 'compiler.ps1' } catch { $caught=$_.Exception.Message }
    if (-not $caught -or $report.steps[-1].exitCode -ne 6) { throw 'Compiler exit code was lost.' }
    $summary=$report.steps[-1].errorSummary -join "`n"
    if ($summary -notmatch 'error C4458' -or $summary -notmatch 'note: see declaration of Player') { throw 'Early compiler error/context was lost.' }
    $json=$report | ConvertTo-Json -Depth 8
    if ($json -notmatch 'error C4458') { throw 'JSON did not retain compiler errors.' }
    $before=$report.steps.Count
    $caught=$null
    try { Run-Step 'missing' 'missing.ps1' } catch { $caught=$_.Exception.Message }
    if (-not $caught -or $report.steps.Count -ne $before) { throw 'Missing child incorrectly succeeded.' }
    if ($ErrorActionPreference -ne 'Stop' -or -not $PSNativeCommandUseErrorActionPreference) { throw 'Failure changed caller preferences.' }
    'PASS: native stderr success; Unicode/space arguments; preferences preserved; exit 37 recorded; complete failure log; missing script rejected; compiler exit 6; early compiler error/context; JSON error summary.'
} finally { Remove-Item -LiteralPath $temporary -Recurse -Force }
