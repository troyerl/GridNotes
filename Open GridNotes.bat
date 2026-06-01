@echo off
setlocal EnableExtensions

:: Opens the installed copy silently (no console). Run Install GridNotes.bat first.

set "POINTER=%LOCALAPPDATA%\GridNotes\install-path.txt"
if exist "%POINTER%" (
  set "INSTALL_DIR="
  for /f "usebackq delims=" %%I in ("%POINTER%") do set "INSTALL_DIR=%%I"
  if defined INSTALL_DIR if exist "%INSTALL_DIR%\Launch GridNotes.vbs" (
    start "" wscript.exe "%INSTALL_DIR%\Launch GridNotes.vbs"
    exit /b 0
  )
)

for %%D in (
  "%ProgramFiles%\GridNotes"
  "%LOCALAPPDATA%\Programs\GridNotes"
  "D:\GridNotes"
  "D:\Program Files\GridNotes"
) do (
  if exist "%%~D\Launch GridNotes.vbs" (
    start "" wscript.exe "%%~D\Launch GridNotes.vbs"
    exit /b 0
  )
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
