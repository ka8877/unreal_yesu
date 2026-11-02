#requires -Version 7.2
[CmdletBinding()]
param([string]$Compiler)
. (Join-Path $PSScriptRoot '../Common.ps1')
$python=(Get-Command $(if ($IsWindows) {'python.exe'} else {'python3'}) -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$evidence=Join-Path $script:EvidenceRoot 'Rebuild'
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
Invoke-DawnCommand $python @((Join-Path $PSScriptRoot 'fetch_environment.py'),'--verify-only') (Join-Path $evidence 'environment-validation.log')
Invoke-DawnCommand $python @((Join-Path $PSScriptRoot 'fetch_environment.py'),'--self-test') (Join-Path $evidence 'environment-mutation-tests.log')
Invoke-DawnCommand $python @((Join-Path $PSScriptRoot 'fetch_character_sources.py'),'--verify-only') (Join-Path $evidence 'character-source-validation.log')
Invoke-DawnCommand $python @((Join-Path $PSScriptRoot 'fetch_character_sources.py'),'--self-test') (Join-Path $evidence 'character-source-mutation-tests.log')
Invoke-DawnCommand $python @((Join-Path $PSScriptRoot 'validate_journey.py'),'--self-test','--report',(Join-Path $evidence 'narrative-validation.json')) (Join-Path $evidence 'narrative-validation.log')
Invoke-DawnCommand $python @('-m','unittest','discover','-s',(Join-Path $PSScriptRoot 'tests'),'-p','test_*.py','-v') (Join-Path $evidence 'policy-tests.log')
if (-not $Compiler) { $Compiler=(Get-Command $(if ($IsWindows) {'cl.exe'} else {'g++'}) -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source }
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('Journey core tests '+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary | Out-Null
try {
    $executable=Join-Path $temporary $(if ($IsWindows) {'journal.exe'} else {'journal'})
    $core=Join-Path $script:ProjectRoot 'Source/PathOfDawnUnreal/Core'
    $test=Join-Path $PSScriptRoot 'test_journey_journal.cpp'
    if ($IsWindows) {
        Push-Location $temporary
        try { Invoke-DawnCommand $Compiler @('/nologo','/std:c++17','/EHsc','/W4',"/I$core",$test,"/Fe:$executable") (Join-Path $evidence 'journal-compile.log') }
        finally { Pop-Location }
    } else { Invoke-DawnCommand $Compiler @('-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-I',$core,$test,'-o',$executable) (Join-Path $evidence 'journal-compile.log') }
    Invoke-DawnCommand $executable @() (Join-Path $evidence 'journal-core.log')
} finally { Remove-Item -LiteralPath $temporary -Recurse -Force }
Write-Host 'Source tests passed. Unreal compilation, scene quality, UMG, SaveGame disk integration, package and browser media remain unverified.'
