@echo off
setlocal
cd /d "%~dp0"

title GridNotes Install Helper

where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo  GridNotes needs Python installed once before it can run.
  echo.
  echo  1. We will open the Python download page in your browser.
  echo  2. Click Download Python and run the installer.
  echo  3. On the FIRST screen, check "Add python.exe to PATH"
  echo  4. Click Install Now and finish.
  echo  5. Double-click "Install GridNotes.bat" again.
  echo.
  pause
  start https://www.python.org/downloads/
  exit /b 1
)

echo.
echo  Starting GridNotes install helper...
echo  Follow the on-screen steps and click "Install GridNotes".
echo.
python install_gui.py
if errorlevel 1 (
  echo.
  echo  Something went wrong. Open INSTALL.md in this folder for help.
  echo.
  pause
  exit /b 1
)
endlocal
