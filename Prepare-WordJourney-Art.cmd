@echo off
setlocal
set "DAWN_PWSH=pwsh.exe"
where pwsh.exe >nul 2>&1
if errorlevel 1 (
  if not exist "%ProgramFiles%\PowerShell\7\pwsh.exe" (
    echo PowerShell 7.2 or newer is required. Install it, then run this file again.
    exit /b 1
  )
  set "DAWN_PWSH=%ProgramFiles%\PowerShell\7\pwsh.exe"
)
"%DAWN_PWSH%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Tools\PathOfDawnUnreal\Rebuild\PrepareArtOnPC.ps1" -OpenOfficialPages %*
exit /b %errorlevel%
