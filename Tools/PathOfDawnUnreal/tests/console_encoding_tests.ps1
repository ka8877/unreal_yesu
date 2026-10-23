#requires -Version 7.2
# Exercise the actual updater native-command boundary with real UTF-8 bytes.
# This runs on pwsh; Windows PowerShell 5.1 and a physical Windows terminal still
# require host observation. No Unreal process is started here.
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot '../SyncAndPlay.ps1'
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$definition=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Invoke-SyncChild'},$true)
if (-not $definition) { throw 'Updater child wrapper was not found.' }
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('dawn-utf8-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temporary)
$priorInput=[Console]::InputEncoding
$priorOutput=[Console]::OutputEncoding
$priorPipe=$OutputEncoding
$priorPythonEncoding=$env:PYTHONIOENCODING
try {
    $functionFile=Join-Path $temporary 'actual-function.ps1'
    [IO.File]::WriteAllText($functionFile,$definition.Extent.Text)
    . $functionFile
    $expected='새벽의 길: 환경 검사를 시작합니다. 갈릴리의 첫 아침'
    $payload=Join-Path $temporary 'utf8.txt'
    [IO.File]::WriteAllText($payload,$expected+"`n",(New-Object Text.UTF8Encoding($false)))
    $child=Join-Path $temporary 'emit-utf8.ps1'
    [IO.File]::WriteAllText($child,@'
param([string]$Payload,[int]$ExitCode=0)
$bytes=[IO.File]::ReadAllBytes($Payload)
$stdout=[Console]::OpenStandardOutput()
$stdout.Write($bytes,0,$bytes.Length)
$stdout.Flush()
exit $ExitCode
'@)
    $shell=(Get-Process -Id $PID).Path

    # A negative control proves this host can reproduce a wrong native decoder.
    [Console]::OutputEncoding=[Text.Encoding]::GetEncoding(949)
    $broken=@(& $shell -NoLogo -NoProfile -File $child -Payload $payload)
    if (($broken -join '') -eq $expected) { throw 'Negative control did not reproduce CP949 decoding; cannot claim this regression was exercised.' }

    $script:captured=New-Object 'Collections.Generic.List[string]'
    function Out-Host {
        [CmdletBinding()]
        param([Parameter(ValueFromPipeline=$true)]$InputObject)
        process { $script:captured.Add([string]$InputObject) }
    }
    # Set all parent encodings incorrectly, then run the production function.
    [Console]::InputEncoding=[Text.Encoding]::GetEncoding(949)
    [Console]::OutputEncoding=[Text.Encoding]::GetEncoding(949)
    $OutputEncoding=[Text.Encoding]::ASCII
    Invoke-SyncChild $shell $child @('-Payload',$payload)
    if (($script:captured -join '') -ne $expected) { throw 'The updater corrupted Korean native stdout.' }
    if ([Console]::InputEncoding.CodePage -ne 65001 -or [Console]::OutputEncoding.CodePage -ne 65001) { throw 'The native boundary did not align console encoding.' }
    $script:captured.Clear()
    [Console]::OutputEncoding=[Text.Encoding]::GetEncoding(949)
    $caught=$null
    try { Invoke-SyncChild $shell $child @('-Payload',$payload,'-ExitCode','37') } catch { $caught=$_.Exception.Message }
    if (-not $caught -or $caught -notmatch '37') { throw 'Native failure status was lost.' }
    if (($script:captured -join '') -ne $expected) { throw 'Korean failure output was corrupted.' }

    # Exercise StartHere's real initialization before Python emits locale-sensitive
    # redirected text. Running only its prefix does not run Windows setup/builds.
    $startFile=Join-Path $PSScriptRoot '../StartHere.ps1'
    $startAst=[Management.Automation.Language.Parser]::ParseFile($startFile,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw ($errors | Out-String) }
    $prefix=@()
    foreach ($statement in $startAst.EndBlock.Statements) {
        if ($statement -is [Management.Automation.Language.AssignmentStatementAst] -and $statement.Left -is [Management.Automation.Language.VariableExpressionAst] -and $statement.Left.VariablePath.UserPath -eq 'repo') { break }
        $prefix+=$statement.Extent.Text
    }
    $python=Get-Command $(if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {'python.exe'} else {'python3'}) -CommandType Application -ErrorAction Stop | Select-Object -First 1
    $env:PYTHONIOENCODING='cp949'
    [Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
    $pythonBroken=@(& $python.Source -c 'import sys; print(sys.argv[1])' $expected)
    if (($pythonBroken -join '') -eq $expected) { throw 'Python negative control did not reproduce locale-mismatched output.' }
    & ([ScriptBlock]::Create(($prefix -join "`n")))
    $pythonFixed=@(& $python.Source -c 'import sys; print(sys.argv[1])' $expected)
    if (($pythonFixed -join '') -ne $expected) { throw 'StartHere did not align Python redirected output with the PowerShell decoder.' }
    'PASS: CP949 native/Python decode failures reproduced; real UTF-8 child stdout preserved; console input/output aligned; exit 37 and Korean failure output retained; StartHere Python output corrected.'
} finally {
    [Console]::InputEncoding=$priorInput
    [Console]::OutputEncoding=$priorOutput
    $OutputEncoding=$priorPipe
    $env:PYTHONIOENCODING=$priorPythonEncoding
    Remove-Item -LiteralPath $temporary -Recurse -Force
}
