@echo off
setlocal
cd /d "%~dp0.."
title Huiyan Shizhu - Sorting Line (auto dequeue, self test)

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. See 1-*.bat for the setup commands.
  pause
  exit /b 1
)

echo SELF TEST ONLY: the lamp lights without pressing the dequeue button.
echo Do NOT use this mode as the final demonstration (the task needs the button).
echo.
".venv\Scripts\python.exe" -m pc.sorting --source camera --reuse-calibration --plc-config pc/config/plc.json --auto-dequeue
echo.
pause
