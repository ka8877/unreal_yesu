#requires -Version 7.2
[CmdletBinding()]
param([string]$EngineRoot, [switch]$InspectOnly)
. "$PSScriptRoot/Common.ps1"
$report = [ordered]@{checkedUtc=[DateTime]::UtcNow.ToString('O'); os=[Runtime.InteropServices.RuntimeInformation]::OSDescription; windows=$IsWindows; root=$script:RepoRoot; unrealInstalled=$false; buildToolsPresent=$false; encoderValidated=$false; compatibility='Not compiled'; notes=@()}
if ($IsWindows) {
    $report.gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM)
    $report.memoryBytes = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    $report.disk = @(Get-PSDrive -PSProvider FileSystem | Select-Object Name,Free,Used)
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    $vs = if (Test-Path -LiteralPath $vswhere) { & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json | ConvertFrom-Json } else { @() }
    $report.visualStudio = @($vs | Select-Object installationPath,installationVersion)
    $sdkRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits/10/Include'
    $report.windowsSdks = @(if (Test-Path -LiteralPath $sdkRoot) { Get-ChildItem -LiteralPath $sdkRoot -Directory | Select-Object -ExpandProperty Name })
    $report.msvcVersions = @(foreach ($entry in $vs) { $directory = Join-Path $entry.installationPath 'VC/Tools/MSVC'; if (Test-Path -LiteralPath $directory) { Get-ChildItem -LiteralPath $directory -Directory | Select-Object -ExpandProperty Name } })
    $report.minimums = @{visualStudio='17.14 (VS2022) or 18.0 (VS2026)'; msvc='14.38'; windowsSdk='10.0.22621'}
    $report.minimumToolchainPresent = @($vs | Where-Object { [version]$_.installationVersion -ge [version]'17.14' }).Count -gt 0 -and @($report.msvcVersions | Where-Object { [version]$_ -ge [version]'14.38' }).Count -gt 0 -and @($report.windowsSdks | Where-Object { [version]$_ -ge [version]'10.0.22621' }).Count -gt 0
}
try {
    $resolved = Resolve-DawnEngine $EngineRoot
    $report.engineRoot = $resolved
    $report.engineVersion = Get-Content -Raw -LiteralPath (Join-Path $resolved 'Engine/Build/Build.version') | ConvertFrom-Json
    $report.unrealInstalled = $true
    $report.executables = [ordered]@{}
    foreach ($relative in @('Engine/Binaries/Win64/UnrealEditor.exe','Engine/Binaries/Win64/UnrealEditor-Cmd.exe','Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll','Engine/Build/BatchFiles/RunUAT.bat','Engine/Build/BatchFiles/Build.bat')) {
        $report.executables[$relative] = Test-Path -LiteralPath (Join-Path $resolved $relative)
    }
    $report.plugins = @(Get-ChildItem -LiteralPath (Join-Path $resolved 'Engine/Plugins') -Recurse -Filter '*.uplugin' | Where-Object {$_.BaseName -in @('PixelStreaming2','ModelContextProtocol','AllToolsets','PythonScriptPlugin','EnhancedInput')} | ForEach-Object { $p = Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json; @{id=$_.BaseName; file=$_.FullName; metadata=$p} })
    $report.buildToolsPresent = $IsWindows -and $report.minimumToolchainPresent -and ($report.executables.Values -notcontains $false)
    $report.notes += 'MSVC/SDK compatibility is established by successful UBT Editor build, not presence checks. No encoder success is inferred from GPU name.'
} catch { $report.notes += $_.Exception.Message }
foreach ($tool in @('node','npm','blender','python','git')) { $command = Get-Command $tool -ErrorAction SilentlyContinue; $report[$tool] = if ($command) { $command.Source } else { $null } }
$report.notes += 'MCP configuration is not changed; discovery is read-only. Do not expose Editor/MCP ports.'
Write-DawnJson (Join-Path $script:EvidenceRoot 'windows-environment.json') $report
$report | ConvertTo-Json -Depth 20
if (-not $InspectOnly -and -not $report.buildToolsPresent) { throw 'Build environment incomplete. See Evidence/windows-environment.json.' }
