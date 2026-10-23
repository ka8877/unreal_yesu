@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0Tools\PathOfDawnUnreal\InstallPrerequisites.ps1" (
  echo Setup files are missing. Extract the whole setup ZIP before running this file.
  pause
  exit /b 1
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Tools\PathOfDawnUnreal\InstallPrerequisites.ps1" %*
set "POD_SETUP_EXIT=%ERRORLEVEL%"
echo.
echo Setup finished with exit code %POD_SETUP_EXIT%. Read the instructions above.
pause
exit /b %POD_SETUP_EXIT%
