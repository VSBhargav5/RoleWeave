@echo off
setlocal
cd /d "%~dp0"
if exist "out\portable\RoleWeave\RoleWeave.exe" (
  start "" "%~dp0out\portable\RoleWeave\RoleWeave.exe" --db "%~dp0private\jobs.db"
  exit /b 0
)
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" desktop.py
  if errorlevel 1 pause
  exit /b
)
python desktop.py
if errorlevel 1 pause
