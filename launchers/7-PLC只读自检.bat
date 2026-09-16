@echo off
setlocal
cd /d "%~dp0.."
title Huiyan Shizhu - PLC read-only check

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. See 1-*.bat for the setup commands.
  pause
  exit /b 1
)

echo Read-only check of DB_M8_Acceptance on 192.0.2.1.
echo Expect: "pass": true, magic 0x4D38, CycleCounter increasing.
echo.
".venv\Scripts\python.exe" plc\tools\m8_real_plc_acceptance.py --check-access --db-number 3
echo.
pause
