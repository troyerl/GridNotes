@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/
  echo During setup, enable "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)

echo Starting GridNotes installer...
python install_gui.py
if errorlevel 1 (
  echo.
  echo The installer exited with an error.
  pause
  exit /b 1
)
endlocal
