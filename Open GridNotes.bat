@echo off
setlocal EnableExtensions
title Open GridNotes

:: Opens the installed copy (not the installer). Run Install GridNotes.bat first if you have not installed yet.

set "POINTER=%LOCALAPPDATA%\GridNotes\install-path.txt"
if exist "%POINTER%" (
  set "INSTALL_DIR="
  for /f "usebackq delims=" %%I in ("%POINTER%") do set "INSTALL_DIR=%%I"
  if defined INSTALL_DIR if exist "%INSTALL_DIR%\Launch GridNotes.vbs" (
    wscript.exe //B "%INSTALL_DIR%\Launch GridNotes.vbs"
    exit /b 0
  )
  if defined INSTALL_DIR if exist "%INSTALL_DIR%\Run GridNotes.bat" (
    call "%INSTALL_DIR%\Run GridNotes.bat"
    exit /b 0
  )
  if defined INSTALL_DIR if exist "%INSTALL_DIR%\dist\GridNotes\GridNotes.exe" (
    start "" "%INSTALL_DIR%\dist\GridNotes\GridNotes.exe"
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
    wscript.exe //B "%%~D\Launch GridNotes.vbs"
    exit /b 0
  )
  if exist "%%~D\Run GridNotes.bat" (
    call "%%~D\Run GridNotes.bat"
    exit /b 0
  )
)

echo.
echo  GridNotes is not installed yet, or the install folder could not be found.
echo.
echo  THIS file is NOT the installer. To install GridNotes:
echo    1. Double-click "Install GridNotes.bat" in your download folder
echo    2. Click the "Install GridNotes" button in the window and wait
echo    3. Then use the "GridNotes" icon on your Desktop
echo.
echo  If you already installed, open your install folder and double-click
echo  "Launch GridNotes.vbs" (often C:\Program Files\GridNotes or D:\GridNotes).
echo.
pause
exit /b 1
