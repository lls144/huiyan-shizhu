@echo off
setlocal
cd /d "%~dp0.."
title Huiyan Shizhu - PLC 12-test auto acceptance

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. See 1-*.bat for the setup commands.
  pause
  exit /b 1
)

echo Runs 12 automatic acceptance tests against the real PLC.
echo The queue and the lamps will be driven - keep hands away from the buttons.
echo.
".venv\Scripts\python.exe" plc\tools\m8_real_plc_acceptance.py --all --db-number 3 --output output/m8-real
echo.
echo Evidence written under output\m8-real\
pause
