# GridNotes release notes

GridNotes is a desktop app for **iRacing driver scouting**. It keeps your notes, race history, and preferences on your PC in a local database — no cloud account required.

New versions are listed below with the newest first. When publishing on GitHub, copy the section for the tag you are releasing into the release description.

---

## v1.0.1 — 2026-05-29

### Fixed

- **Uninstall with “delete my data”** no longer fails because `driver_history.db` is in use. GridNotes now stops background workers, closes the database cleanly, and removes your data folder after the app exits (same reliable pattern used for the install folder).
- **Log file lock on uninstall** — logging is shut down before user data is removed so `gridnotes.log` is not left locked.

### Improved

- Normal app shutdown also stops workers and closes the database connection in a consistent order.

---

## v1.0.0 — 2026-05-29

First public release of GridNotes.

### Highlights

- **Driver scouting** — searchable list of everyone you have raced with, with sortable stats and quick visual cues for drivers you like or dislike.
- **Private notes** — per-driver scouting notes stored locally on your computer.
- **Race history import** — load iRacing `event_result` JSON (and compatible custom formats); duplicate sessions are not imported twice.
- **Live session (Windows)** — while iRacing is running, see who is in your current session and filter the driver list to that lobby.
- **Safety insights** — safety index and breakdown to help judge incident risk at a glance.
- **Light and dark themes** — switch appearance in Settings.

### Driver list and details

- Sortable columns: races, incidents, finish, position delta, DNF counts, last iRating/SR, series, note indicator.
- Like / dislike markers with green and red row highlighting.
- Search by name and option to hide your own driver name.
- **Live Mode** to focus on the current iRacing session when the SDK is connected.
- Driver detail panel with history, notes, and safety breakdown.

### Import and data

- Supports iRacing **`event_result`** JSON (Race session), bundled `races` arrays, and top-level race arrays.
- Deduplication by **subsession ID** so re-importing the same race does not create duplicate rows.
- Optional **iRacing Data API** auto-fetch after races (Windows, OAuth token required when registration is available).
- Configurable **race history retention** (automatic cleanup of old imported results; notes and preferences are kept).

### Settings and maintenance

- **Save settings** only enables when you have unsaved changes.
- Remove drivers with zero races.
- Storage location and database size shown in Settings.
- **Uninstall** from Settings (with optional removal of notes, database, and settings).

### Updates and installation (Windows)

- **Check for updates** and **Update now** for standard installs (for example `D:\GridNotes` or `%LOCALAPPDATA%\Programs\GridNotes`):
  - Download progress UI with step-by-step status.
  - App closes before files are replaced, then reopens automatically.
- **Install GridNotes.bat** graphical installer for the GitHub source ZIP (creates Desktop and Start Menu shortcuts).
- Registers in **Windows Settings → Apps** for uninstall.
- Taskbar and window icons use the GridNotes branding; pin **`GridNotes.lnk`** in your install folder or the Desktop shortcut for best results.

### System requirements

- **Windows 10 or 11** (primary platform; Live SDK and silent launch require Windows).
- **Python 3.10–3.13** only if you install from the source ZIP via `Install GridNotes.bat` (the installer sets up a private `.venv` for you).
- **iRacing** optional but required for live session features and SDK integration.
- Internet optional (needed for update checks and optional API auto-fetch).

### Known limitations

- In-app updates compare version numbers only; install from a newer GitHub tag if you previously used a higher pre-1.0 test version.
- Live SDK does not import full race results — use JSON import for history.
- Standalone `.exe` installs open the download page for updates rather than one-click ZIP updates.

### Data location

Your database, settings, and log file live under:

`%LOCALAPPDATA%\GridNotes\`

(Older installs may migrate automatically from `%APPDATA%\RacingBook\`.)

---

## Template for future releases

```markdown
## vX.Y.Z — YYYY-MM-DD

### New
- …

### Improved
- …

### Fixed
- …
```
