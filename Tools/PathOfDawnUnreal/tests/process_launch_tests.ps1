#requires -Version 7.2
# Real native argv roundtrip on every host, plus the real Run-Step/long-lived
# process handoff on Windows. No Unreal, GPU or media success is inferred.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../Common.ps1')
$common=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../Common.ps1'))
$start=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../StartHere.ps1'))
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('Dawn launch tests '+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temporary)
$shell=(Get-Process -Id $PID).Path
$wrapper=$null; $script:StreamRoot=$temporary
try {
    $python=(Get-Command $(if ($IsWindows) {'python.exe'} else {'python3'}) -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    $arguments=@('','two words','Korean_한국어','a"b','C:\folder with spaces\','backslash\"quote','literal $() & | ; % ! ` chars')
    $info=[Diagnostics.ProcessStartInfo]::new()
    $info.FileName=$python; $info.UseShellExecute=$false; $info.RedirectStandardOutput=$true; $info.RedirectStandardError=$true
    $info.Arguments=ConvertTo-DawnNativeArguments (@('-c','import json,sys; print(json.dumps(sys.argv[1:]))')+$arguments)
    $roundtrip=[Diagnostics.Process]::Start($info)
    $output=$roundtrip.StandardOutput.ReadToEnd(); $errorText=$roundtrip.StandardError.ReadToEnd(); $roundtrip.WaitForExit()
    if ($roundtrip.ExitCode -ne 0) { throw "Native argv fixture failed: $errorText" }
    $received=@($output | ConvertFrom-Json)
    if ($received.Count -ne $arguments.Count) { throw 'Native argument count changed.' }
    for ($index=0; $index -lt $arguments.Count; $index++) { if ($received[$index] -cne $arguments[$index]) { throw "Native argument $index changed." } }
    Write-Host 'PASS: native arguments retain empty values, spaces, Unicode, embedded quotes, trailing backslashes and shell punctuation.'
    if (-not $IsWindows) {
        Write-Host 'NOT RUN: Windows detached process/file-handle test requires Windows. It will run in TestDemo on the target host.'
        return
    }

    [IO.File]::WriteAllText((Join-Path $temporary 'worker.ps1'),@'
[Console]::WriteLine('worker early stdout')
[Console]::Error.WriteLine('worker early stderr')
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'worker.ready'),'ready')
for ($i=0; $i -lt 150; $i++) {
    if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'worker.release')) {
        [Console]::WriteLine('worker late stdout')
        [Console]::Error.WriteLine('worker late stderr')
        exit 0
    }
    Start-Sleep -Milliseconds 200
}
exit 41
'@)
    [IO.File]::WriteAllText((Join-Path $temporary 'launch.ps1'),@'
param($Common,$Shell)
$ErrorActionPreference='Stop'
. $Common
$script:StreamRoot=$PSScriptRoot
$child=Start-DawnProcess 'fixture' $Shell @('-NoLogo','-NoProfile','-File',(Join-Path $PSScriptRoot 'worker.ps1')) $PSScriptRoot
Write-Output "Worker started: $($child.Id)"
'@)
    $tokens=$null; $parseErrors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($start,[ref]$tokens,[ref]$parseErrors)
    if ($parseErrors.Count) { throw 'StartHere parse failed.' }
    $definition=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Run-Step'},$true)
    [IO.File]::WriteAllText((Join-Path $temporary 'run-step.ps1'),$definition.Extent.Text,[Text.UTF8Encoding]::new($true))
    [IO.File]::WriteAllText((Join-Path $temporary 'wrapper.ps1'),@'
param($Common,$Shell)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'run-step.ps1')
$script:pwsh=$Shell
$script:stamp='detach-test'
$script:diagnostic=Join-Path $PSScriptRoot 'diagnostic.json'
$script:report=@{steps=@()}
Run-Step 'launch' 'launch.ps1' @('-Common',$Common,'-Shell',$Shell)
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'browser-step.ready'),'next step reached')
'@)
    $info=[Diagnostics.ProcessStartInfo]::new()
    $info.FileName=$shell; $info.UseShellExecute=$false
    $info.RedirectStandardOutput=$true; $info.RedirectStandardError=$true
    foreach ($argument in @('-NoLogo','-NoProfile','-File',(Join-Path $temporary 'wrapper.ps1'),'-Common',$common,'-Shell',$shell)) { $info.ArgumentList.Add($argument) }
    $wrapper=[Diagnostics.Process]::Start($info)
    $stdoutTask=$wrapper.StandardOutput.ReadToEndAsync(); $stderrTask=$wrapper.StandardError.ReadToEndAsync()
    $deadline=[DateTime]::UtcNow.AddSeconds(12)
    while ([DateTime]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath (Join-Path $temporary 'browser-step.ready'))) {
        if ($wrapper.HasExited -and -not (Test-Path -LiteralPath (Join-Path $temporary 'browser-step.ready'))) { throw "Launcher exited before its next step: $($stdoutTask.Result) $($stderrTask.Result)" }
        Start-Sleep -Milliseconds 100
    }
    if (-not (Test-Path -LiteralPath (Join-Path $temporary 'browser-step.ready'))) { throw 'Persistent child retained the launcher output pipe; browser-open step could not be reached.' }
    if (-not (Test-DawnProcessRunning 'fixture')) { throw 'Detached child did not remain alive after the launch step returned.' }
    if (-not $wrapper.WaitForExit(3000) -or $wrapper.ExitCode -ne 0) { throw 'Launcher did not finish independently of its child.' }
    $record=Get-Content -LiteralPath (Join-Path $temporary 'runtime/fixture.process.json') -Raw | ConvertFrom-Json
    [IO.File]::WriteAllText((Join-Path $temporary 'worker.release'),'release')
    $deadline=[DateTime]::UtcNow.AddSeconds(5)
    while ((Test-DawnProcessRunning 'fixture') -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
    if (Test-DawnProcessRunning 'fixture') { throw 'Detached child did not finish.' }
    $stdout=Get-Content -LiteralPath $record.stdoutLog -Raw
    $stderr=Get-Content -LiteralPath $record.stderrLog -Raw
    if ($stdout -notmatch 'worker early stdout' -or $stdout -notmatch 'worker late stdout' -or $stderr -notmatch 'worker early stderr' -or $stderr -notmatch 'worker late stderr') { throw 'Detached stdout/stderr was lost after the launcher exited.' }
    Write-Host 'PASS: Windows Run-Step returned while its child remained alive; subsequent browser step reached; late stdout/stderr preserved in dedicated logs.'
} finally {
    if ($wrapper -and -not $wrapper.HasExited) { $wrapper.Kill($true); [void]$wrapper.WaitForExit(3000) }
    Stop-DawnProcess 'fixture'
    Remove-Item -LiteralPath $temporary -Recurse -Force
}
