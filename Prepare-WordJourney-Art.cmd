@echo off
setlocal
where pwsh.exe >nul 2>&1
if errorlevel 1 (
  echo PowerShell 7.2 or newer is required. Install it, then run this file again.
  exit /b 1
)
pwsh.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Tools\PathOfDawnUnreal\Rebuild\PrepareArtOnPC.ps1" -OpenOfficialPages %*
exit /b %errorlevel%
