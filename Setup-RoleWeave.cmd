@echo off
setlocal
cd /d "%~dp0"
python -c "import sys, tkinter; assert sys.version_info >= (3,11), 'Python 3.11 or newer is required'"
if errorlevel 1 goto failed
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Open Launch-RoleWeave.cmd to start.
pause
exit /b 0
:failed
echo Setup failed. Install Python 3.11 or newer with Tcl/Tk, then retry.
pause
exit /b 1
