@echo off
setlocal
cd /d "%~dp0.."
title Huiyan Shizhu - M2 single-object evidence

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. See 1-*.bat for the setup commands.
  pause
  exit /b 1
)

echo M2 live preview. Press S to save evidence, R to recalibrate, Q to quit.
echo Hold the A3 sheet so it fills the ROI box, then S for background / triangle / rectangle / circle.
echo.
".venv\Scripts\python.exe" -m pc.vision live --camera-config pc/config/camera.json --reuse-calibration --calibration-file output/m2/runtime-calibration.json --evidence-dir output/m2/live-evidence-builtin
echo.
pause
