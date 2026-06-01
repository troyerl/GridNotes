# GridNotes

**Version 1.1.0**

Desktop app for **iRacing driver scouting**: keep personal notes, review race history and stats, and optionally see who is in your current session while iRacing is running (Windows).

All data stays on your machine in a local SQLite database — no account or cloud sync.

**New users:** step-by-step install instructions are in **[INSTALL.md](INSTALL.md)**.

## Overview

GridNotes helps you remember who you raced against and whether you want to race with them again.

- **Driver list** — sortable table with race counts, average incidents/finish, position delta, DNF totals and breakdown, last iRating/SR, series, and a note indicator (`+`).
- **Scouting notes** — free-text notes per driver, saved locally.
- **Like / dislike** — mark drivers you enjoyed or did not; rows highlight green or red.
- **Search & filters** — filter by name, hide your own driver name, and (when connected) show only the **current iRacing session**.
- **JSON import** — load iRacing `event_result` exports or custom race JSON to build history.
- **Live SDK (Windows)** — while iRacing is running, registers drivers in the session and powers the “current session only” filter (does not import full race results; use JSON for that).

### Import deduplication

Each race result is stored with its **iRacing subsession ID** (`subsession_id`). Re-importing the same session JSON **does not duplicate** rows: one result per driver per subsession. Stats, notes, and preferences are left unchanged for rows that already exist.

Custom JSON should include `subsession_id` (or `session_id`) on each race object. Files without a subsession ID cannot be deduplicated and may still create duplicate rows if imported repeatedly.

### Supported JSON formats

1. iRacing **`event_result`** payload (`type: "event_result"`) — imports the **Race** session.
2. **`{"races": [{"subsession_id": …, "results": […]}]}`**
3. A top-level **array** of race objects with the same shape.

## Install from downloaded source (graphical wizard, v1.1.0+)

If you downloaded or cloned the project folder (not the Windows `.exe` installer), use the built-in setup wizard. Full details: **[INSTALL.md](INSTALL.md)**.

**Windows:** double-click `Install GridNotes.bat`  
**macOS:** double-click `Install GridNotes.command` (first time: right-click → Open if Gatekeeper blocks it)

Or from a terminal:

```bash
python install_gui.py
```

The wizard will:

1. Check that Python 3.10+ is installed  
2. Let you choose an **install location** (copies source there if you pick a new folder)  
3. Create a `.venv` and install dependencies (with a live progress log)  
4. Optionally **build a standalone app** to a **build output folder** you choose (Windows)  
5. Optionally add a **Desktop shortcut**  
6. Create `Run GridNotes.bat` or `Run GridNotes.command` in the install folder  

When finished, click **Launch GridNotes**, use the run script, or the Desktop shortcut. Your database stays in the install folder when running from source.

## Run from source (manual)

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
- On first launch after an update, existing duplicate rows for the same driver + subsession may be merged automatically when the database migrates

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
