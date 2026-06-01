@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

title GridNotes Install Helper

set "LOGFILE=%~dp0install-helper.log"
echo.>>"%LOGFILE%"
echo ============================================================>>"%LOGFILE%"
echo GridNotes install helper %date% %time%>>"%LOGFILE%"
echo Folder: %~dp0>>"%LOGFILE%"

:: /elevate = re-launch as administrator (only needed for C:\Program Files).
:: Double-click normally — no UAC prompt; default install uses your user folder.
if /I "%~1"=="/elevate" (
  net session >nul 2>&1
  if errorlevel 1 (
    echo.
    echo  Requesting administrator permission for Program Files install...
    echo  Click Yes on the Windows prompt. A new window will open.
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -ArgumentList '/elevate' -Verb RunAs -WorkingDirectory '%~dp0.'"
    echo  If you clicked No, close this window and run Install GridNotes.bat again
    echo  without choosing Program Files ^(default install needs no admin^).
    echo.
    pause
    exit /b 0
  )
)

call :find_python
if errorlevel 1 goto :failed

echo.
echo  ============================================================
echo   INSTALLER - this is NOT the GridNotes app itself
echo  ============================================================
echo.
echo  Default install needs no administrator permission.
echo  For C:\Program Files: right-click this file - Run as administrator,
echo  or run: Install GridNotes.bat /elevate
echo  For D: drive: use Choose folder in the wizard ^(creates D:\GridNotes^).
echo.
echo  Starting install wizard...
echo  ^(If nothing appears, read install-helper.log in this folder.^)
echo.

%PYEXE% %PYARGS% -u "%~dp0install_gui.py" 2>>"%LOGFILE%"
set "ERR=!ERRORLEVEL!"
echo Exit code: !ERR!>>"%LOGFILE%"

if !ERR! neq 0 goto :failed
goto :done

:find_python
set "PYEXE=python"
set "PYARGS="
where python >nul 2>&1
if not errorlevel 1 (
  python -c "import sys" >>"%LOGFILE%" 2>&1
  if not errorlevel 1 (
    echo Using python>>"%LOGFILE%"
    exit /b 0
  )
)
set "PYEXE=py"
set "PYARGS=-3"
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys" >>"%LOGFILE%" 2>&1
  if not errorlevel 1 (
    echo Using py -3>>"%LOGFILE%"
    exit /b 0
  )
)
set "PYEXE="
set "PYARGS="
echo.
echo  GridNotes could not run Python from this folder.
echo.
echo  Install Python from https://www.python.org/downloads/
echo  Turn ON "Add python.exe to PATH" on the first installer screen.
echo.
echo  Opening the download page...
start https://www.python.org/downloads/
pause
exit /b 1

:failed
echo.
echo  ============================================================
echo   Install helper did not finish successfully.
echo  ============================================================
echo.
echo  See: %LOGFILE%
echo  Help: INSTALL.md in this folder
echo.
if exist "%LOGFILE%" (
  echo --- Last lines from log ---
  powershell -NoProfile -Command "Get-Content -LiteralPath '%LOGFILE%' -Tail 25"
  echo ---------------------------
)
pause
exit /b 1

:done
endlocal
