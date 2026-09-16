@echo off
setlocal
cd /d "%~dp0.."
title Huiyan Shizhu - full test suite

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. See 1-*.bat for the setup commands.
  pause
  exit /b 1
)

echo Running the full automated regression (no hardware needed).
echo.
".venv\Scripts\python.exe" -m pytest -q
echo.
pause
