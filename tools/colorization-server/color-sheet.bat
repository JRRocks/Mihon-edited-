@echo off
rem Builds the color sheet of a series, e.g. color-sheet.bat "One Piece" (see start-color-sheet.ps1).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-color-sheet.ps1" %*
pause
