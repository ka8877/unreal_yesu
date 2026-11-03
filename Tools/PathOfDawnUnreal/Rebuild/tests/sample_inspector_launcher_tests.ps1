#requires -Version 7.2
# Windows launcher contract fixtures only. The executable below is NOT Unreal.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (-not $IsWindows) { throw 'Run these launcher fixtures on Windows.' }
$PSNativeCommandUseErrorActionPreference=$false
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('WJ sample inspector '+[guid]::NewGuid().ToString('N'))
$tools=Split-Path -Parent $PSScriptRoot
$launcher=Join-Path $tools 'InspectSample.ps1'
$windowsPowerShell=(Get-Command powershell.exe -CommandType Application).Source
$revision='1111111111111111111111111111111111111111'
$previousMode=$env:WJ_SAMPLE_FIXTURE_MODE
$previousCapture=$env:WJ_SAMPLE_FIXTURE_CAPTURE
$previousReport=$env:WORD_JOURNEY_SAMPLE_REPORT
$checks=0
function Assert([bool]$Condition,[string]$Message) {
    if (-not $Condition) { throw $Message }
    $script:checks++
}
function Invoke-Inspector([string]$Tool=$launcher,[int]$Timeout=30) {
    $script:lastOutput=@(& $windowsPowerShell -NoLogo -NoProfile -ExecutionPolicy Bypass -File $Tool -Revision $revision -SampleRoot $sample -EngineRoot $engine -OutputRoot $output -TimeoutSeconds $Timeout 2>&1)
    $script:code=$LASTEXITCODE
    $script:lastOutput | ForEach-Object { Write-Host $_ }
}
try {
    # Construct Unicode without depending on the test runner's script encoding.
    $sample=Join-Path $temporary ('Sample '+[char]0xAC08+[char]0xB9B4+[char]0xB9AC)
    $engine=Join-Path $temporary 'Fixture Engine'
    $output=Join-Path $temporary 'Private Reports'
    [void][IO.Directory]::CreateDirectory($sample)
    [void][IO.Directory]::CreateDirectory((Join-Path $engine 'Engine/Build'))
    [void][IO.Directory]::CreateDirectory((Join-Path $engine 'Engine/Binaries/Win64'))
    $project=Join-Path $sample 'FixtureSample.uproject'
    $original='{"FileVersion":3,"EngineAssociation":"5.8","Plugins":[{"Name":"PythonScriptPlugin","Enabled":false}]}'
    [IO.File]::WriteAllText($project,$original)
    [IO.File]::WriteAllText((Join-Path $engine 'Engine/Build/Build.version'),'{"MajorVersion":5,"MinorVersion":8,"PatchVersion":0,"BranchName":"fixture"}')
    $compiler=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    if (-not (Test-Path -LiteralPath $compiler)) { throw 'Windows .NET Framework fixture compiler not found.' }
    $fixtureCode=@'
using System;
using System.IO;
using System.Threading;
public class FixtureEditor {
    public static int Main(string[] args) {
        // This is a launcher fixture, never a real Editor or asset report.
        var capture=Environment.GetEnvironmentVariable("WJ_SAMPLE_FIXTURE_CAPTURE");
        File.WriteAllLines(capture,args);
        if(args.Length!=10 || !File.Exists(args[0]) || !Path.GetFileName(args[0]).StartsWith("WJInspect_")) return 31;
        var descriptor=File.ReadAllText(args[0]);
        if(!descriptor.Contains("EditorScriptingUtilities") || !descriptor.Contains("PythonScriptPlugin")) return 32;
        if(args[1]!="-run=pythonscript" || args[2].IndexOf("inspect_sample.py")<0 || args[5]!="-NullRHI") return 33;
        var mode=Environment.GetEnvironmentVariable("WJ_SAMPLE_FIXTURE_MODE");
        if(mode=="timeout") { Thread.Sleep(20000); return 34; }
        if(mode=="native-error") return 35;
        var report=Environment.GetEnvironmentVariable("WORD_JOURNEY_SAMPLE_REPORT");
        if(String.IsNullOrEmpty(report)) return 36;
        var status=mode=="partial" ? "PARTIAL_INVENTORY" : "SAMPLE_ASSETS_INSPECTED";
        File.WriteAllText(report,"{\"fixtureOnly\":true,\"schemaVersion\":1,\"status\":\""+status+"\",\"graphicsVerified\":false,\"retargetVerified\":false,\"sourceAssetsSaved\":false,\"licensedSourceFilesExported\":false,\"loadedMeshes\":[],\"loadedAnimations\":[]}");
        Console.WriteLine("Launcher fixture completed; no Unreal/GPU test.");
        return 0;
    }
}
'@
    $source=Join-Path $temporary 'FixtureEditor.cs'
    [IO.File]::WriteAllText($source,$fixtureCode)
    & $compiler /nologo /target:exe ('/out:'+(Join-Path $engine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe')) $source
    if ($LASTEXITCODE -ne 0) { throw 'Fixture executable compilation failed.' }
    $env:WJ_SAMPLE_FIXTURE_CAPTURE=Join-Path $temporary 'captured-args.txt'
    $env:WORD_JOURNEY_SAMPLE_REPORT='outer-process-sentinel'
    $env:WJ_SAMPLE_FIXTURE_MODE='success'
    Invoke-Inspector
    Assert ($code -eq 0) 'Windows PowerShell 5.1 success path failed.'
    Assert ((Get-Content -LiteralPath $project -Raw) -ceq $original) 'Original descriptor was modified.'
    Assert (@(Get-ChildItem -LiteralPath $sample -Filter 'WJInspect_*.uproject').Count -eq 0) 'Own temporary descriptor was not cleaned.'
    Assert ($env:WORD_JOURNEY_SAMPLE_REPORT -eq 'outer-process-sentinel') 'Parent environment was modified.'
    $arguments=Get-Content -LiteralPath $env:WJ_SAMPLE_FIXTURE_CAPTURE
    Assert ($arguments[0].StartsWith($sample)) 'Unicode/spaced sample path was not preserved.'
    Assert ($arguments[9].StartsWith('-UserDir='+$output)) 'Private UserDir argument was not preserved.'
    $reports=@(Get-ChildItem -LiteralPath $output -Recurse -Filter 'sample-inventory.json')
    Assert ($reports.Count -eq 1) 'One private fixture report expected.'
    $env:WJ_SAMPLE_FIXTURE_MODE='partial'
    Invoke-Inspector
    Assert ($code -eq 2) 'Partial inventory must not report complete success.'
    $env:WJ_SAMPLE_FIXTURE_MODE='native-error'
    Invoke-Inspector
    Assert ($code -eq 1) 'Native failure must propagate as failure.'
    Assert (@(Get-ChildItem -LiteralPath $sample -Filter 'WJInspect_*.uproject').Count -eq 0) 'Failure left its temporary descriptor.'
    $env:WJ_SAMPLE_FIXTURE_MODE='timeout'
    Invoke-Inspector -Timeout 10
    Assert ($code -eq 1) 'Timed-out inspection must fail.'
    Assert (($lastOutput -join '\n') -match 'timed out') 'Timeout reason was not shown.'
    Assert (@(Get-ChildItem -LiteralPath $sample -Filter 'WJInspect_*.uproject').Count -eq 0) 'Timeout left its temporary descriptor.'
    [IO.File]::WriteAllText($project,$original.Replace('5.8','5.7'))
    Invoke-Inspector
    Assert ($code -eq 1) 'Mismatched engine association must be rejected.'
    Assert ((Get-Content -LiteralPath $project -Raw).Contains('5.7')) 'Mismatched sample was upgraded.'
    [IO.File]::WriteAllText($project,$original)
    $edited=Join-Path $temporary 'Edited inspector'
    [void][IO.Directory]::CreateDirectory($edited)
    Copy-Item -LiteralPath $launcher -Destination $edited
    [IO.File]::WriteAllText((Join-Path $edited 'inspect_sample.py'),'# locally edited fixture')
    Invoke-Inspector -Tool (Join-Path $edited 'InspectSample.ps1')
    Assert ($code -eq 1) 'Changed companion source must be rejected.'
    Assert ((Get-Content -LiteralPath (Join-Path $edited 'inspect_sample.py') -Raw) -eq '# locally edited fixture') 'Edited helper was overwritten.'
    Write-Host "Sample inspector Windows PowerShell 5.1 launcher: $checks checks passed (fixtures only, no Unreal/GPU)."
} finally {
    $env:WJ_SAMPLE_FIXTURE_MODE=$previousMode
    $env:WJ_SAMPLE_FIXTURE_CAPTURE=$previousCapture
    $env:WORD_JOURNEY_SAMPLE_REPORT=$previousReport
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
}
# Expected failing children must not become the Actions shell's exit status.
exit 0
