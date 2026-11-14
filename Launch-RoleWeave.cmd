@echo off
setlocal
cd /d "%~dp0"
if exist ".build-venv\Scripts\python.exe" (
  ".build-venv\Scripts\python.exe" launch_roleweave.py
  if errorlevel 1 pause
  exit /b
)
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" launch_roleweave.py
  if errorlevel 1 pause
  exit /b
)
python launch_roleweave.py
if errorlevel 1 pause
