# Installing GridNotes

**Current version: 1.1.0**

GridNotes is a desktop app for iRacing driver scouting. All data stays on your computer.

This guide is for **new users**. Pick the section that matches what you downloaded.

---

## Which install method do I have?

| You have… | Follow |
|-----------|--------|
| `GridNotes-Setup.exe` | [Path A — Windows installer](#path-a--windows-installer-easiest) |
| `GridNotes.exe` inside a zip folder | [Path A — Windows installer](#path-a--windows-installer-easiest) (unzip first) |
| A folder with `Install GridNotes.bat` or `Install GridNotes.command` | [Path B — Graphical install wizard](#path-b--graphical-install-wizard) |

---

## Path A — Windows installer (easiest)

**No Python required.** Best for users who receive a pre-built app.

1. **Get the app**
   - Download `GridNotes-Setup.exe` from a [GitHub release](https://github.com/troyerl/race_book/releases), or
   - Download and unzip `GridNotes-Windows.zip`.

2. **Install or run**
   - **Setup.exe:** Double-click `GridNotes-Setup.exe` → follow the wizard → Finish.
   - **Zip:** Unzip the folder → open it → double-click `GridNotes.exe`.

3. **Open GridNotes**
   - Use the Start menu or desktop shortcut (if you created one during setup).

4. **First steps**
   - **Controls → Import race JSON** to load iRacing race results.
   - Click a driver in the table to add notes or like/dislike.

**Where your data is stored**

```
%APPDATA%\GridNotes\driver_history.db
```

Installing a newer `.exe` over an older one does **not** delete your database.

---

## Path B — Graphical install wizard

Use this when you downloaded the **source code** (GitHub ZIP or git clone). You do **not** need to use `pip` or the terminal yourself—the wizard does it for you.

### Before you start

1. Install **Python 3.10 or newer**
   - [python.org/downloads](https://www.python.org/downloads/)
   - **Windows:** on the first installer screen, check **“Add python.exe to PATH”**.

2. Unzip or clone the project so you have a folder containing:
   - `Install GridNotes.bat` (Windows) or `Install GridNotes.command` (macOS)
   - `install_gui.py`, `main.py`, `requirements.txt`

### Start the wizard

| Platform | Action |
|----------|--------|
| **Windows** | Double-click **`Install GridNotes.bat`** |
| **macOS** | Double-click **`Install GridNotes.command`** (if blocked: right-click → **Open** → **Open**) |
| **Any** | In that folder: `python install_gui.py` (or `python3` on Mac) |

### Wizard options (version 1.1.0+)

| Option | What it does |
|--------|----------------|
| **Install location** | Where GridNotes is copied and where `.venv` and your database live. See [default folders](#default-install-folders) below. |
| **Browse…** | Pick any folder you prefer. |
| **Program Files** (Windows only) | Sets install path to `C:\Program Files\GridNotes`. You may need to run **`Install GridNotes.bat` as administrator**. |
| **Create a shortcut on the Desktop** | Adds a Desktop shortcut (`.lnk` on Windows, launcher on Mac). On by default. |
| **Build a standalone Windows app** | Runs PyInstaller; optional, takes several minutes. |
| **Build output folder** | Where `GridNotes.exe` is written (default: `{install folder}\dist`). Only when the build option is checked. |
| **Install** | Copies files (if needed), creates `.venv`, installs packages, creates `Run GridNotes.bat` / `.command`. |

When installation finishes, click **Launch GridNotes**, use the **Desktop** shortcut, or run the launcher script in your **install folder** (not necessarily the original download folder).

### Default install folders

These are filled in automatically; you can change them with **Browse…**.

| Platform | Default path | Notes |
|----------|--------------|--------|
| **Windows** | `%LOCALAPPDATA%\Programs\GridNotes` | Per-user “Programs” folder; **no admin password** |
| **Windows** (optional) | `C:\Program Files\GridNotes` | All users; use **Program Files** button + run installer **as administrator** |
| **macOS** | `~/Applications/GridNotes` | Your user Applications folder; no admin password |
| **Linux** | `~/.local/share/GridNotes` | Standard user app data location |

**Important:** If you accept the default, your data file is:

```
{install location}\driver_history.db
```

For example on Windows:

```
C:\Users\YourName\AppData\Local\Programs\GridNotes\driver_history.db
```

The original **download/ZIP folder is not modified** unless you leave the install location pointing there.

### Windows quick steps

1. Install Python 3.10+ with **Add to PATH**.
2. Double-click **`Install GridNotes.bat`**.
3. Confirm **Install location** (default is fine for most people).
4. Leave **Desktop shortcut** checked if you want one.
5. Click **Install** → wait for the log to finish → **Launch GridNotes**.

### macOS quick steps

1. Install Python 3.10+.
2. Double-click **`Install GridNotes.command`**.
3. Confirm **Install location** (`~/Applications/GridNotes` by default).
4. Click **Install** → **Launch GridNotes**.

Live iRacing session scouting requires **Windows** with iRacing running. On Mac you can still import JSON and use notes/stats.

---

## After installation (all users)

1. **Import race history** — **Controls → Import race JSON**  
   See [README.md](README.md) for supported JSON formats.

2. **Scout drivers** — Select a row for notes, like/dislike, and safety stats.

3. **Settings** — **Settings** tab: appearance (light/dark), data retention, etc. Click **Save settings** after changes.

4. **Live session (Windows only)** — With iRacing running: **Live Mode** and **Current session only**.

5. **Updates (source installs)** — **Settings → Maintenance → Check for updates** → **Update now** to pull latest code and restart, or open the download page for a packaged build.

---

## Where is my data?

| How you installed | Database | Log file |
|-------------------|----------|----------|
| `GridNotes-Setup.exe` / portable `.exe` | `%APPDATA%\GridNotes\driver_history.db` | `%APPDATA%\GridNotes\gridnotes.log` |
| Install wizard (default location) | `{install location}\driver_history.db` | `{install location}\gridnotes.log` |
| `python main.py` in download folder without wizard | `driver_history.db` next to `main.py` | `gridnotes.log` in same folder |

---

## Troubleshooting

### “Python was not found” (Path B, Windows)

- Reinstall Python with **“Add python.exe to PATH”**.
- Close the folder, reopen it, run **`Install GridNotes.bat`** again.

### Install wizard won’t start

From the project folder:

```bash
python install_gui.py
```

On Mac use `python3` if `python` is missing.

### “Access denied” or install fails (Program Files)

- Use the default **`%LOCALAPPDATA%\Programs\GridNotes`** (no admin), or  
- Right-click **`Install GridNotes.bat`** → **Run as administrator** when using `C:\Program Files\GridNotes`.

### Desktop shortcut missing

- Run the wizard again with **Create a shortcut on the Desktop** checked, or  
- Use **`Run GridNotes.bat`** / **`Run GridNotes.command`** in your install folder.

### Standalone build failed

- Open the install log in the wizard for PyInstaller errors.
- You can still run GridNotes from source via **`Run GridNotes.bat`** without building `.exe`.

### App won’t connect to iRacing

- Live SDK needs **Windows**, **iRacing running**, and you in a session.
- Race history import uses **Import race JSON** only—no SDK required.

### Something else

Check the log (see [Where is my data?](#where-is-my-data)). The log is cleared each time the app starts.

---

## Building a Windows installer (developers)

To produce `GridNotes-Setup.exe` for others, on a Windows PC with Python 3.10+:

```bat
scripts\build_installer.bat
```

See [README.md — Build a Windows installer](README.md#build-a-windows-installer). Bump `racing_book/app_version.py` and `scripts/racing_book.iss` when releasing a new version.

---

## More help

- Features and JSON formats: [README.md](README.md)
- Manual install (no wizard): [README.md — Run from source](README.md#run-from-source-manual)
