@echo off
setlocal
chcp 65001 >nul
title Path of Dawn - Local Windows Setup
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Tools\PathOfDawnUnreal\StartHere.ps1" %*
set "DawnExit=%ERRORLEVEL%"
if not "%DawnExit%"=="0" (
  echo.
  echo Setup stopped. Read the instructions above; nothing was installed automatically.
  pause
)
exit /b %DawnExit%
