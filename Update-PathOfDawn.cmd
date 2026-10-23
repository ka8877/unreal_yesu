@echo off
setlocal
title Path of Dawn - GitHub Update and Play
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Tools\PathOfDawnUnreal\Bootstrap.ps1" %*
set "DawnExit=%ERRORLEVEL%"
if not "%DawnExit%"=="0" pause
exit /b %DawnExit%
