@echo off
setlocal
cd /d "%~dp0.."
title Huiyan Shizhu - Vision Console (M5 GUI)

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. See 1-*.bat for the setup commands.
  pause
  exit /b 1
)

echo Vision console: live camera, detections, tracked objects, events.
echo Keys 1-5 save M3 evidence, Start/Stop control the session.
echo.
".venv\Scripts\python.exe" -m pc.gui --source camera --reuse-calibration --plc-config pc/config/plc.json
echo.
pause
