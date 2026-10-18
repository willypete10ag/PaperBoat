@echo off
rem Keep the window open so extraction/setup failures remain readable.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Play-TTYD64.ps1" %*
pause
