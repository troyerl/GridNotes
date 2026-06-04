# GridNotes release notes

GridNotes is a desktop app for **iRacing driver scouting**. It keeps your notes, race history, and preferences on your PC in a local database — no cloud account required.

New versions are listed below with the newest first.

When you push a tag (for example `v1.0.24`), the GitHub **Release** workflow uses the matching `## v…` section from this file as the release description on GitHub.

**Developers:** stable vs pre-release tags and update behavior are documented in **[RELEASES.md](RELEASES.md)**.

---

## v1.0.44 — 2026-06-02

### New

- **Free for personal use license** — A `LICENSE` file defines personal, non-commercial use and allows sharing official release builds with the license included.
- **Settings → Legal** — License summary, how to use GridNotes, iRacing affiliation notice, data and privacy notes, and a general disclaimer (informational, not legal advice).

### Improved

- **Windows installer** — Setup shows the license agreement before install. The license file is bundled with packaged builds.

---

## v1.0.43 — 2026-06-02

### Improved

- **Resizable driver table columns** — Drag column header edges to set widths; your layout is saved across restarts. Pagination no longer forces narrow auto-sized columns.
- **Receiver connection feedback** — Connecting and connected states show a colored banner, status bar text, and **Disconnect** while a session is active. A 20-second timeout reports failure if the broadcaster cannot be reached.
- **Broadcaster receiver list** — The broadcast status window lists connected receiver device names (from a hello handshake) instead of only a count.
- **Streamer mode** — Toggling streamer mode shows a spinner instead of a progress bar while the table refreshes.
- **Import while receiving** — **Import race JSON…** is disabled for the whole receiver session (including while connecting), not only after data loads.

### Fixed

- **Receiver on macOS** — WebSocket connect uses a compatible protocol version when older PyQt6 builds lack `VersionLatest`.
- **Receiver connect** — Connecting as a receiver again starts the client and loads scouting data after the WebSocket opens.

---

## v1.0.42 — 2026-06-03

### New

- **LAN broadcast** — Share your scouting book and live iRacing session with another device on the same network. Use **Broadcast** in the header to send; use **Receiver** on a second PC or tablet to view the broadcaster’s data. Notes and likes on a receiver sync back to the broadcaster (not saved locally on the receiver).
- **Driver table pagination** — The driver list shows **50 rows per page** by default (choose 25, 50, 100, or 200). Previous/Next controls and a summary line appear below the table. Search, filters, and column sorting apply to the full list.

### Improved

- **Broadcast controls in header** — **Broadcast**, **Receiver**, and **Disconnect** live next to **Live Mode** for quick access. Settings → Live Mode explains the feature and shows receiver status.
- **Header tooltips** — Hover hints on broadcast, receiver, streamer, and live mode buttons explain what each control does.
- **Stopping broadcast** — A spinner and status message appear while the broadcaster shuts down so you know GridNotes is working.
- **Broadcaster audio spotter** — Optional co-driver warnings in the broadcast status window (off by default; does not change your saved app setting).

### Fixed

- **Quit while broadcasting** — Closing GridNotes no longer hangs; shutdown skips restarting the SDK worker or rebuilding the full driver table.
- **After broadcast** — Returning from broadcaster mode reliably restores the driver table and layout.

---

## v1.0.41 — 2026-06-02

### Improved

- **In-app update on Windows** — When an update needs administrator permission (typical Program Files installs), GridNotes now explains that Windows may ask you to click **Yes**. The update progress dialog stays on screen with a waiting state before the app closes so you know what to expect.

---

## v1.0.40 — 2026-06-02

### Improved

- **Quick note tags** — Tag inputs in **Settings → Data** now render correctly on macOS: transparent fill (no row strip behind the fields), visible rounded borders, and styles that stay in sync when you change theme.

---

## v1.0.39 — 2026-06-02

### Improved

- **Quick note tags** — Chip label and note inputs in **Settings → Quick note tags** use a transparent background so they blend with the panel instead of a filled box.

### Fixed

- **In-app update on Windows** — **Update now** again closes GridNotes briefly, applies the update in the background, and reopens automatically (same flow as before). Program Files installs request elevation when needed so files can be replaced; the app relaunches when finished and syncs the install pointer and version marker.
- **Installer fallback** — When only **GridNotes-Setup.exe** is available, the silent installer targets your existing install folder and relaunches GridNotes afterward.
- **Update diagnostics** — Failed updates point you to `%APPDATA%\\GridNotes\\gridnotes-update.log` for details.

---

## v1.0.38 — 2026-06-02

### Improved

- **System timezone detection** — **System default** now reads your PC’s zone via the OS (PyQt / Windows registry / localtime) instead of falling back to UTC. US users see the correct region and abbreviation (EST, CDT, CST, PST, etc.) in Settings and on **Last raced** labels.
- **Saved timezone** — Choosing a zone and clicking **Save settings** keeps that preference across restarts; **System default** clears the saved choice and follows the PC again.

---

## v1.0.37 — 2026-06-02

### Improved

- **Display timezone** — **Settings → Appearance** lets you choose a timezone or use **System default** (your PC’s zone). Last-raced times and labels use that zone instead of a fixed US Eastern time.
- **JSON import progress** — Importing race JSON shows a modal progress dialog with per-file status while data is loaded.

### Fixed

- **JSON import freeze** — The progress dialog stays open until the driver table finishes updating. Large imports update only changed rows instead of rebuilding the entire table, so the app stays responsive and new data appears when import completes.

---

## v1.0.36 — 2026-06-02

### Fixed

- **Installed version after Setup.exe** — Settings no longer shows an old version (for example 1.0.33) after installing a newer release. The app now prefers the running `GridNotes.exe` folder over a stale `install-path.txt` from an earlier source install, and always reconciles against the built-in app version.
- **Windows installer version** — `GridNotes-Setup.exe` and **Settings → Apps** version metadata are taken from `app_version.py` at build time (no hardcoded Inno version). Setup writes `.gridnotes-version` in the install folder on first install.

---

## v1.0.35 — 2026-06-02

### Improved

- **Pre-release builds** — Pushing a tag with a hyphen (for example `v1.0.35-rc1`) publishes a GitHub **pre-release** so installed apps are not offered that build as an update. Stable tags (for example `v1.0.35`) remain the latest for **Check for updates**.
- **Release documentation** — Maintainer guide at `docs/RELEASES.md` (stable vs test tags, CI behavior, and promoting a build to production).

---

## v1.0.34 — 2026-06-02

### Improved

- **Live Mode context** — Session banner shows race type, lap count (or timed length), track name, and category (road/oval) from the iRacing SDK when available.
- **Session at a glance** — Live Mode and Grid Walk show a one-line summary (driver count, flagged, liked/disliked, new to your book).
- **Grid Walk scouting** — Each grid row shows compact Safety Index score with form arrow; hover tooltips match the driver table; drivers with no history show a **New** badge.
- **New drivers** — Live driver cards badge drivers not yet in your book.
- **Audio spotter** — Clarified as optional and off by default in Live Mode.

---

## v1.0.33 — 2026-06-02

### Improved

- **Windows publisher metadata** — Installer and `GridNotes.exe` embed **Logan Troyer** as company/publisher. Setup.exe installs register correctly in **Settings → Apps** (including Inno `unins000.exe` uninstall path).

### Fixed

- **Settings → Apps publisher** — GridNotes now registers the uninstall entry after Setup installs, so Publisher is not blank/unknown when the app runs once.

---

## v1.0.32 — 2026-06-02

### Fixed

- **Startup crash on Windows builds** — Fixed a missing import that caused `name 'field' is not defined` when launching the packaged app (v1.0.31).

---

## v1.0.31 — 2026-06-02

### Fixed

- **Race JSON import freeze** — Importing a single race (or a few) no longer rebuilds the entire driver table on the UI thread. Only drivers from that session are updated, so the window stays responsive.
- **Database locking** — SQLite connections use a busy timeout so imports are less likely to hang when Live Mode is active.

---

## v1.0.30 — 2026-06-02

### Improved

- **Grid Walk layout** — Starting grid is shown in two columns like the real grid: odd positions on the left, even on the right (staggered half a row back).
- **Grid Walk highlights** — Highlights the car ahead in your column and beside you on the grid (e.g. at P5, P3 and P6). Flagged-driver warnings use the same neighbors.

---

## v1.0.29 — 2026-06-02

### Improved

- **Unknown Safety Index** — When a driver has no scoreable history, risk UI stays blank: no tier suffix in streamer mode, empty Safety Index cells, and no placeholder text in Live Mode cards or the detail panel.
- **Streamer mode labels** — Risk tier is appended only when a score exists (e.g. `Driver #42 (Moderate risk)` vs `Driver #42` alone).

---

## v1.0.28 — 2026-06-02

### Improved

- **Streamer mode in Live Mode** — Drivers in the current iRacing session show their **session car number** (e.g. `Driver #42 (Moderate risk)`) instead of a stable cust-ID alias. Grid Walk, live cards, and the audio spotter use the same label.
- **Streamer mode elsewhere** — The driver table and detail panel use the session car number when that driver is in the active session; otherwise the stable alias (e.g. `Driver #14`) is unchanged.

---

## v1.0.27 — 2026-06-02

### Added

- **Custom quick note tags** — Settings → Data lets you add, edit, and remove scouting note chips. Each tag has a short **chip label** (up to 20 characters) and an optional longer **note to append** when clicked; leave the note blank to append the chip label itself.
- **Default tags on first install** — New installs start with five built-in tags (Clean, Divebombs, Blocks, Restarts, Unpredictable). Change them anytime or use **Reset to defaults**.

### Improved

- **Scouting notes** — Quick note template buttons reflect your saved tags and update when you save Settings.

---

## v1.0.26 — 2026-06-02

### Improved

- **Automatic Windows updates** — **Update now** installs in the background without saving files to Downloads. If the release includes `GridNotes-Windows.zip`, GridNotes updates in place and reopens; otherwise it downloads `GridNotes-Setup.exe` to a private folder under your GridNotes data directory and runs a silent install, then reopens.
- **Release builds** — Windows CI now publishes both `GridNotes-Setup.exe` and `GridNotes-Windows.zip` so in-place ZIP updates are available when possible.

### Fixed

- **Get latest version** — Opens the GitHub releases page instead of triggering a browser download of the installer `.exe`.
- **Install detection** — Finds the install folder from the running app or Windows **Settings → Apps** when applying updates.

---

## v1.0.25 — 2026-06-02

### Improved

- **Database performance** — Faster driver table and Live Mode stats: Live session queries aggregate only drivers in the session instead of the full race history table; form-guide (recent races) queries use better indexes and batch large driver lists safely.
- **SQLite tuning** — WAL journal mode, larger page cache, and new indexes on `(cust_id, race_at)` and driver name for sorting.
- **Table refresh** — Adding a few drivers after import no longer re-queries the entire library just to update the UI cache.

### Fixed

- **Windows installer metadata** — Publisher shows **Logan Troyer** in Settings → Apps and in the installer (was **GridNotes**).

---

## v1.0.24 — 2026-06-02

### Added

- **In-place updates for installed app** — If you installed with **GridNotes-Setup.exe**, **Update now** downloads the release ZIP privately, replaces the app folder, and reopens (no browser download to your Downloads folder when the release includes `GridNotes-Windows.zip`).

### Improved

- **Update experience** — Progress text says **Updating…** instead of **Downloading…**; staging files live under your GridNotes data folder (`updates` subfolder), not Downloads; old staging folders are cleaned up automatically.
- **Update confirm** — Dialog clarifies that in-place updates do not save files to Downloads.

### Fixed

- **GitHub Release notes on Windows** — Release workflow extracts release notes with Unicode characters (for example form-guide arrows) without failing on Windows.

---

## v1.0.23 — 2026-06-02

### Added

- **Form guide** — Safety Index column and detail panel show a recent-form arrow (↗ ↘ →) comparing lifetime risk to the last five races; tooltips explain lifetime vs recent scores.
- **Grid Walk** — Live Mode starting-grid view between qualifying and the race, with position order and Liked / Disliked / Risk marks; toggle in the Live Mode header.
- **Audio spotter** — Optional Windows text-to-speech warnings when a disliked or high-risk driver is about 1.5 seconds behind you on a green-flag run (Settings → Live Mode and Live header toggle).
- **Streamer mode** — Title-bar toggle replaces driver names on screen with stable aliases (e.g. `Driver #14 (Moderate risk)`) for streaming and screenshots; database and notes are unchanged. Modal progress while names are hidden or restored.
- **Scouting guide** — Scrollable reference dialog for Safety Index tiers, form arrows, marks, and risk factors; open from **Scouting guide…** on the Drivers tab, **Guide** in the detail panel and Live Mode, or Settings → Maintenance.

### Improved

- **Settings** — Sidebar sections reorganized: **Appearance**, **Data** (retention, backup & restore, driver cleanup), **Live Mode** (audio spotter), and **Maintenance** (updates, help, uninstall).
- **Driver table** — Search still matches real names while streamer mode is on (aliases shown in the grid); customer ID column hidden during streamer mode.

---

## v1.0.22 — 2026-06-02

### Improved

- **Accessibility** — Keyboard focus rings on buttons, fields, tabs, and the driver table; visible labels for search and “hide your name”; screen-reader names on main controls and Settings actions; **Mark** column for Liked / Disliked / Risk (not color alone); note column shows **Notes** when a driver has scouting notes.
- **Keyboard** — **Ctrl+F** focus search, **Ctrl+L** toggle Live Mode, **Ctrl+S** / **Cmd+S** save notes; **Enter** on a selected row focuses scouting notes; Live Mode driver cards activate with **Enter** or **Space**.
- **Driver table** — Hover and selection feedback on liked, disliked, and risky rows (clearer interactive state on colored rows).
- **Contrast** — Muted and disabled text and safety-tier colors tuned for light and dark themes.

---

## v1.0.21 — 2026-06-02

### Improved

- **GitHub Releases** — Pushing a version tag now uses the matching section from this file (`docs/RELEASE_NOTES.md`) as the release description on GitHub, instead of auto-generated commit lists.

---

## v1.0.20 — 2026-06-02

### Added

- **Help & support (Settings)** — **Save support file** builds a zip with logs and version info for troubleshooting; **Open logs folder** opens your GridNotes data folder.
- **Backup & restore (Settings)** — Export or restore your `driver_history.db`; a safety copy is kept before restore.
- **Update notes** — When an update is available, you see what’s new before choosing **Update now**.
- **Auto-open after install** — Installer can open GridNotes when installation finishes (on by default).
- **GitHub Actions** — Pushing a `v*` tag builds `GridNotes-Setup.exe` and attaches it to the GitHub Release when Inno Setup is available.

### Improved

- **Taskbar name** — Windows registry registration for the GridNotes App User Model ID (with existing shortcut refresh) so the taskbar is more likely to show **GridNotes** instead of Python.

---

## v1.0.19 — 2026-06-02

### Improved

- **Cleaner codebase** — Python package renamed to `gridnotes` (was `racing_book`). Windows shell/launcher code lives under `gridnotes/platform/windows/`; in-app updates live under `gridnotes/installer/`. Main window module is `gridnotes_app.py` (`GridNotesApp`). In-app updates remove the old `racing_book` folder automatically.
- **Easier install and update** — Install wizard and **Update now** use plain-language progress and messages. Technical details are unchanged in `gridnotes.log`, `install-helper.log`, `launch-error.log`, and `gridnotes-update.log` (optional “Show details” in the installer).
- **Open GridNotes.bat** — Tries the branded `GridNotes.exe` launcher first, then falls back to the VBS launcher.

### Fixed

- **Update transition** — Post-update refresh can fall back to the legacy module name once if needed; version detection reads either package folder during migration.

---

## v1.0.18 — 2026-06-02

### Fixed

- **Taskbar right-click still said “Python”** — taskbar branding now runs from a shipped PowerShell script with environment variables (fixes broken relaunch-command quoting) and sets **GridNotes** on the launcher EXE metadata as a fallback.

---

## v1.0.17 — 2026-06-02

### Fixed

- **Shortcut / pin icon blank** — shortcuts now use **`icon.ico`** for the tile (not `GridNotes.exe`, which often still looks like Python). One-time shortcut rebuild on next launch.
- **Taskbar menu said “Python”** — running window now registers **GridNotes** as the display name with relaunch metadata (required for correct pin label). Prefer **pin from the Desktop shortcut**, not “Pin to taskbar” on the running button.

---

## v1.0.16 — 2026-06-02

### Fixed

- **Taskbar pin / shortcut target** — Desktop and Start Menu shortcuts that still pointed at `gridnotes_start.py` (or had no icon) are rebuilt to launch **`.venv\Scripts\GridNotes.exe`** with the GridNotes icon. The launcher is built automatically when missing.

---

## v1.0.15 — 2026-06-02

### Fixed

- **Version stuck at 1.0.12 after Update now** — the update batch now writes `.gridnotes-version` immediately after copying files, clears stale `__pycache__`, and runs a dedicated post-update module. Settings reconciles the displayed version with `app_version.py` on startup.

---

## v1.0.14 — 2026-06-02

### Fixed

- **Taskbar pin icon** — shortcuts now always get the correct `AppUserModelID` and pin icon (branded `GridNotes.exe`, not a stale pythonw reference). Shell properties are applied in the order Windows expects. **Unpin** any old taskbar icon, update, then pin from the **Desktop shortcut** again.

---

## v1.0.13 — 2026-06-02

### Fixed

- **Missing window and taskbar icons** — the UI and Windows shell now use `icon.ico` again instead of the branded `GridNotes.exe` stub (PyQt cannot load icons from the pythonw copy reliably). Shortcuts and taskbar pins use `icon.ico` when present.

---

## v1.0.12 — 2026-06-02

### Improved

- **In-app update refreshes everything** — **Update now** reapplies the same post-install steps as the installer: dependencies, `icon.ico`, branded `GridNotes.exe`, launch/uninstall scripts, Desktop and Start Menu shortcuts, and Windows Settings → Apps registration. No uninstall or re-run of **Install GridNotes.bat** needed for normal releases.

---

## v1.0.11 — 2026-05-29

### Fixed

- **Taskbar pin still showed Python** — shortcuts now use **`.venv\Scripts\GridNotes.exe`** as both the launch target and the shortcut icon (not `icon.ico` alone). GridNotes refreshes shortcuts on first launch after an update.

### Improved

- Window and taskbar branding use the branded launcher EXE for icon resources when available.

---

## v1.0.10 — 2026-05-29

### Fixed

- **`failed to locate pyvenv.cfg` when running `D:\GridNotes\GridNotes.exe`** — the branded launcher now lives in **`.venv\Scripts\GridNotes.exe`** (next to `pythonw`), where the virtual environment expects it. Install removes the broken copy from the install root.
- Shortcuts and **Launch GridNotes.vbs** point at the Scripts launcher automatically.

---

## v1.0.9 — 2026-05-29

### Fixed

- **Version in Settings and Windows Apps stayed on 1.0.2 (or another old release)** — in-app updates now write `.gridnotes-version` in your install folder and register **DisplayVersion** for the version you actually installed. GridNotes also refreshes the Windows Apps entry on each launch (HKCU and HKLM when allowed).

### Improved

- Settings shows **Installed version** from the install folder, not only the bundled `app_version.py` in memory.

---

## v1.0.8 — 2026-05-29

### Fixed

- **App would not start after v1.0.7** — a typo in the in-app update script (`portable_update.py`) caused a `SyntaxError` on launch. GridNotes starts normally again.

---

## v1.0.7 — 2026-05-29

### Fixed

- **In-app update now rebuilds `GridNotes.exe`** — after **Check for updates → Update now**, the branded launcher (pythonw copy + embedded icon) is recreated automatically. You no longer need a separate **Install GridNotes.bat** run for the taskbar pin fix after updating from v1.0.6.

### Improved

- Update log records launcher rebuild alongside refreshed VBS/start scripts.

---

## v1.0.6 — 2026-05-29

### Fixed

- **Taskbar pin actually shows the GridNotes icon** — v1.0.5’s launcher started `pythonw` in a second process, so Windows kept the Python logo. **`GridNotes.exe`** is now a copy of `pythonw` with **`icon.ico` embedded**; shortcuts run `GridNotes.exe gridnotes_start.py` in **one** process, so the taskbar uses the branded EXE.

### Improved

- Installer downloads **rcedit** (once) to embed the icon; shortcuts are upgraded if they pointed at the old stub launcher without arguments.

---

## v1.0.5 — 2026-05-29

### Fixed

- **Taskbar pin shows the GridNotes icon (not Python)** — install now builds **`GridNotes.exe`** in your install folder (small launcher with the embedded icon). Shortcuts and **`Launch GridNotes.vbs`** use it instead of `pythonw` / wscript.
- **Windows app identity is set before Qt loads** — fixes taskbar grouping when the real UI runs under `pythonw`.

### Improved

- First launch after update upgrades shortcuts that still point at `pythonw` to **`GridNotes.exe`** when available.
- Re-run **`Install GridNotes.bat`** once if **`GridNotes.exe`** is missing in your install folder.

---

## v1.0.4 — 2026-05-29

### Fixed

- **Correct icon when pinning to the taskbar** — Desktop and Start Menu shortcuts now launch via `pythonw` + `gridnotes_start.py` (with `icon.ico`) instead of `Launch GridNotes.vbs` / wscript, so Windows no longer groups GridNotes under the generic Python icon.
- **Automatic shortcut upgrade** — on first launch after updating, old shortcuts that still pointed at wscript/`.vbs` are rebuilt silently (no visible terminal windows).

### Improved

- App identity (`AppUserModelID`) is set earlier at startup; the running window gets proper relaunch metadata for taskbar pinning.
- Docs clarify pinning the **GridNotes** shortcut (not the Python taskbar button).

---

## v1.0.3 — 2026-05-29

### Fixed

- **No more flashing terminal windows on startup** — taskbar icon setup no longer spawns visible PowerShell consoles when GridNotes opens. Background scripts run hidden, and shortcut branding is not re-applied on every launch (only at install).

### Improved

- Install-time shortcut creation also runs PowerShell non-interactively and without a visible console.

---

## v1.0.2 — 2026-05-29

### Fixed

- **Install no longer asks for an App ID** — the Windows taskbar identity (`AppUserModelID`) is applied automatically when shortcuts are created. A PowerShell invocation bug had caused an interactive prompt during `Install GridNotes.bat`.

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
