@echo off
setlocal EnableExtensions
title Open GridNotes

:: Opens the installed copy (not the installer). Run Install GridNotes.bat first.

set "POINTER=%LOCALAPPDATA%\GridNotes\install-path.txt"
if exist "%POINTER%" (
  set "INSTALL_DIR="
  for /f "usebackq delims=" %%I in ("%POINTER%") do set "INSTALL_DIR=%%I"
  if defined INSTALL_DIR if exist "%INSTALL_DIR%\Run GridNotes.bat" (
    call "%INSTALL_DIR%\Run GridNotes.bat"
    exit /b %ERRORLEVEL%
  )
)

for %%D in (
  "%ProgramFiles%\GridNotes"
  "%LOCALAPPDATA%\Programs\GridNotes"
  "D:\GridNotes"
  "D:\Program Files\GridNotes"
) do (
  if exist "%%~D\Run GridNotes.bat" (
    call "%%~D\Run GridNotes.bat"
    exit /b %ERRORLEVEL%
  )
)

echo.
echo  GridNotes could not be found.
echo.
echo  1. Run "Install GridNotes.bat" from your download folder first.
echo  2. After install, use the Desktop icon "GridNotes"
echo     or open your install folder (e.g. D:\GridNotes) and run "Run GridNotes.bat"
echo.
pause
exit /b 1
