# GridNotes

iRacing driver scouting notes and race history — track notes, stats, and race results offline or with the live iRacing SDK.

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

Optional live SDK support (Windows only, while iRacing is running):

```bash
pip install pyirsdk
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
3. Build `dist\GridNotes\GridNotes.exe`
4. Create an installer if [Inno Setup 6](https://jrsoftware.org/isinfo.php) is installed, otherwise a zip

Outputs:

- `dist\GridNotes\` — portable app folder
- `dist\GridNotes-Setup.exe` — setup wizard (when Inno Setup is installed)
- `dist\GridNotes-Windows.zip` — fallback if Inno Setup is not installed

## End-user install (Windows)

**With installer:** run `GridNotes-Setup.exe` and follow the wizard.

**With zip:** unzip and run `GridNotes.exe`.

Driver history and settings are stored in:

`%APPDATA%\GridNotes\driver_history.db`

(If you used the app before it was renamed, data is copied automatically from `%APPDATA%\RacingBook\`.)

## Development notes

- When running from source, the database stays in the project folder as `driver_history.db`
- When running the bundled app, data lives in `%APPDATA%\GridNotes\` so updates do not wipe history

## Windows taskbar icon

The Windows build generates `icon.ico` from `icon.png` automatically during `scripts\build_installer.bat`.
If you run from source on Windows and the taskbar icon is missing:

```bash
pip install Pillow
python scripts/generate_icon.py
python main.py
```

## Troubleshooting log (for support)

If something goes wrong, check the log file (errors, SDK connection, imports):

- **Installed app:** `%APPDATA%\GridNotes\gridnotes.log`
- **Run from source:** `gridnotes.log` in the project folder

The log file is cleared each time the app starts.
