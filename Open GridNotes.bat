@echo off
setlocal EnableExtensions

:: Opens an installed copy silently (no console). Run Install GridNotes.bat first.

set "POINTER=%LOCALAPPDATA%\GridNotes\install-path.txt"
if exist "%POINTER%" (
  set "INSTALL_DIR="
  for /f "usebackq delims=" %%I in ("%POINTER%") do set "INSTALL_DIR=%%I"
  if defined INSTALL_DIR call :launch "%%INSTALL_DIR%%"
)

for %%D in (
  "%ProgramFiles%\GridNotes"
  "%LOCALAPPDATA%\Programs\GridNotes"
  "D:\GridNotes"
  "D:\Program Files\GridNotes"
) do (
  if exist "%%~D\main.py" call :launch "%%~D"
)

echo.
echo  GridNotes could not be found.
echo.
echo  1. Run "Install GridNotes.bat" from your download folder first.
echo  2. After install, use the Desktop icon "GridNotes"
echo     or "Launch GridNotes.vbs" in your install folder (e.g. D:\GridNotes)
echo.
echo  For troubleshooting with a console, use "Run GridNotes.bat" in the install folder.
echo.
pause
exit /b 1

:launch
set "ROOT=%~1"
set "LAUNCHER=%ROOT%\.venv\Scripts\GridNotes.exe"
set "STARTER=%ROOT%\gridnotes_start.py"
if exist "%LAUNCHER%" if exist "%STARTER%" (
  start "" "%LAUNCHER%" "%STARTER%"
  exit /b 0
)
if exist "%ROOT%\Launch GridNotes.vbs" (
  start "" wscript.exe "%ROOT%\Launch GridNotes.vbs"
  exit /b 0
)
exit /b 1
