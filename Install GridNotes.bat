@echo off
setlocal
cd /d "%~dp0"

title GridNotes Install Helper

:: Do not auto-elevate. If you install to C:\Program Files and get "access denied",
:: right-click this file and choose "Run as administrator".
:: Installing to D:\GridNotes (or another drive) does not require admin.

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
echo  ============================================================
echo   INSTALLER - this is NOT the GridNotes app itself
echo  ============================================================
echo.
echo  This wizard installs GridNotes (default: C:\Program Files\GridNotes).
echo  To use your D: drive, click Choose folder and pick D:\  (creates D:\GridNotes).
echo.
echo  After install, open GridNotes from the DESKTOP icon "GridNotes"
echo  or double-click "Open GridNotes.bat" in this download folder.
echo.
echo  Starting install wizard...
echo.
python install_gui.py
if errorlevel 1 (
  echo.
  echo  Something went wrong. Open INSTALL.md in this folder for help.
  echo  If installing to Program Files failed, right-click this file and
  echo  Run as administrator, or choose a folder on D: in the wizard.
  echo.
  pause
  exit /b 1
)
endlocal
