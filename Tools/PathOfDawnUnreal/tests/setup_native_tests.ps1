#requires -Version 7.2
# Runs the actual setup command wrapper against Linux child processes; installs nothing.
$ErrorActionPreference='Stop'
if ($IsWindows) { throw 'This native-wrapper regression test uses /bin/sh and must run on Linux.' }
$t=$null;$e=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot '../InstallPrerequisites.ps1'),[ref]$t,[ref]$e)
$function=$ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Invoke-SetupCommand'},$true)
. ([ScriptBlock]::Create($function.Extent.Text))
$report=[ordered]@{steps=@()};$PlanOnly=$false;$resultCode=1
Invoke-SetupCommand 'stderr-success' '/bin/sh' @('-c','echo harmless-stderr >&2; exit 0')
if($report.steps[-1].status -ne 'completed' -or $ErrorActionPreference -ne 'Stop'){throw 'stderr/restoration assertion'}
$failed=$false
try {Invoke-SetupCommand 'exit-failure' '/bin/sh' @('-c','exit 37')} catch {$failed=$true}
if(-not $failed -or $resultCode -ne 37 -or $report.steps[-1].exitCode -ne 37){throw 'native exit assertion'}
$PlanOnly=$true
Invoke-SetupCommand 'plan-does-not-launch' '/tmp/intentionally-missing' @('--example','value with spaces')
if($report.steps[-1].status -ne 'planned'){throw 'plan assertion'}
'PASS: stderr success, preference restoration, nonzero native exit, plan does not launch'
