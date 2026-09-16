@echo off
setlocal
cd /d "%~dp0.."
title Huiyan Shizhu - M3 multi-object evidence

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. See 1-*.bat for the setup commands.
  pause
  exit /b 1
)

echo M3 multi-object preview with M4 event tracking.
echo Keys: 1 normal light, 2 bright/side, 3 dark, 4 occlusion, 5 touching. Q to quit.
echo.
".venv\Scripts\python.exe" -m pc.vision multi-live --camera-config pc/config/camera.json --reuse-calibration --calibration-file output/m2/runtime-calibration.json --evidence-dir output/m3/live-evidence-builtin-v4 --expected-labels triangle rectangle circle --events
echo.
pause
