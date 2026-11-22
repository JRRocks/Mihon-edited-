@echo off
rem Double-click to start the colorization server for Mihon (edited).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-server.ps1" %*
pause
