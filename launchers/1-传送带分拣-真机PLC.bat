@echo off
setlocal
cd /d "%~dp0.."
title Huiyan Shizhu - Sorting Line (real PLC)

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found.
  echo   python -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)

echo ============================================================
echo  Sorting line: camera + conveyor + real PLC bridge
echo  Camera needs ~13 s to show the first frame. Please wait.
echo  Put the A3 sheet so it fills the blue ROI box.
echo ============================================================
echo.

".venv\Scripts\python.exe" -m pc.sorting --source camera --reuse-calibration --plc-config pc/config/plc.json

echo.
if errorlevel 1 echo [WARN] the program exited with a non-zero code. Read the messages above.
echo Session JSON is written under output\sorting\sessions\
pause
