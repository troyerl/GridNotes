# GridNotes

**Version 1.2.19**

Desktop app for **iRacing driver scouting**: keep personal notes, review race history and stats, and optionally see who is in your current session while iRacing is running (Windows).

All data stays on your machine in a local SQLite database — no account or cloud sync.

### New here? No technical experience needed

1. Open **`START_HERE.txt`** in this folder (short checklist), or  
2. Read **[INSTALL.md](INSTALL.md)** — plain-language steps with pictures of what to click.

**Downloaded source from GitHub?** You will **not** see `GridNotes-Setup.exe` in the ZIP — use **`Install GridNotes.bat`** ([INSTALL.md](INSTALL.md)).  

**Easiest for Windows:** download **`GridNotes-Setup.exe`** from [Releases → Assets](https://github.com/troyerl/race_book/releases) (you must build and upload it first; see [docs/BUILD_WINDOWS_INSTALLER.md](docs/BUILD_WINDOWS_INSTALLER.md)).

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

## Install (non-technical users)

See **[INSTALL.md](INSTALL.md)**. Summary:

| What you have | What to do |
|---------------|------------|
| `GridNotes-Setup.exe` | Double-click it → Install → open from Start menu |
| Download folder with `Install GridNotes.bat` | Install Python once (link in INSTALL.md) → double-click the `.bat` → **Install GridNotes** |

## Install helper (developers / manual)

The graphical wizard is for the source folder: `Install GridNotes.bat` / `install_gui.py`. Advanced options are hidden unless you check **Show advanced options**.

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

## Code layout

Source is organized by area under `racing_book/` (`app`, `ui`, `data`, `iracing`, `safety`, `services`, `core`, `installer`). See **[docs/CODE_STRUCTURE.md](docs/CODE_STRUCTURE.md)**.

## Development notes

- When running from the install helper, the database and `gridnotes.log` are in `%APPDATA%\GridNotes\` (same as the Setup installer)
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
