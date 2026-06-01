@echo off
setlocal
cd /d "%~dp0"

title GridNotes Install Helper

:: /noelevate = stay as normal user (recommended for D:\GridNotes).
:: Without /noelevate, we offer admin elevation for C:\Program Files installs.
if /I not "%~1"=="/noelevate" (
  net session >nul 2>&1
  if errorlevel 1 (
    echo.
    echo  To install under C:\Program Files, Windows needs administrator permission.
    echo  Click Yes on the next prompt, OR close this and run:
    echo    Install GridNotes.bat /noelevate
    echo  for D:\ or the default folder (no admin).
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
  )
)

where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo  GridNotes needs Python on PATH once to run this installer.
  echo  Any version is OK for this step ^(even 3.14^) — the script can then
  echo  download Python 3.13 for GridNotes automatically.
  echo.
  echo  Opening the Python download page…
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
echo  Default install needs no administrator permission.
echo  For C:\Program Files, run this file as administrator ^(right-click^).
echo  For D: drive, use Choose folder in the wizard ^(creates D:\GridNotes^).
echo.
echo  Starting install wizard...
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
