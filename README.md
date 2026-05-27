# Racing Book

iRacing driver history and race logger — track notes, stats, and race results offline or with the live iRacing SDK.

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

Optional live SDK support:

```bash
pip install iracingdata
```

## Build a Windows installer

Run this on a Windows machine (Python 3.10+ required):

```bat
scripts\build_installer.bat
```

Or in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
```

The script will:

1. Create a temporary `.build-venv`
2. Install PyInstaller and dependencies
3. Build `dist\Racing Book\Racing Book.exe`
4. Create an installer if [Inno Setup 6](https://jrsoftware.org/isinfo.php) is installed, otherwise a zip

Outputs:

- `dist\Racing Book\` — portable app folder
- `dist\RacingBook-Setup.exe` — setup wizard (when Inno Setup is installed)
- `dist\RacingBook-Windows.zip` — fallback if Inno Setup is not installed

## End-user install (Windows)

**With installer:** run `RacingBook-Setup.exe` and follow the wizard.

**With zip:** unzip and run `Racing Book.exe`.

Driver history and settings are stored in:

`%APPDATA%\RacingBook\driver_history.db`

## Development notes

- When running from source, the database stays in the project folder as `driver_history.db`
- When running the bundled app, data lives in `%APPDATA%\RacingBook\` so updates do not wipe history
