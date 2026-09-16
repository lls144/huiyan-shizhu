@echo off
setlocal
cd /d "%~dp0.."
title Huiyan Shizhu - Sorting Line (no PLC)

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. See 1-*.bat for the setup commands.
  pause
  exit /b 1
)

echo Sorting line without the PLC bridge (visualisation only). Camera ~13 s to start.
echo.
".venv\Scripts\python.exe" -m pc.sorting --source camera --reuse-calibration --no-plc
echo.
pause
