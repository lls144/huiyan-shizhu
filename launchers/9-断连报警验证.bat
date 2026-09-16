@echo off
setlocal
cd /d "%~dp0.."
title Huiyan Shizhu - COMM-002 heartbeat / alarm check

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. See 1-*.bat for the setup commands.
  pause
  exit /b 1
)

echo COMM-002 check: heartbeats, then 2 s silence - watch the box.
echo The three lamps should blink together for a couple of seconds.
echo.
".venv\Scripts\python.exe" plc\tools\m8_comm002_real_check.py --output-dir output/m8-comm002
echo.
pause
