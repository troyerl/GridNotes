# Installing GridNotes

GridNotes is a desktop app for iRacing driver scouting. All data stays on your computer.

This guide is for **new users**. Pick the section that matches what you downloaded.

---

## Which install method do I have?

| You have… | Follow |
|-----------|--------|
| `GridNotes-Setup.exe` | [Path A — Windows installer](#path-a--windows-installer-easiest) |
| `GridNotes.exe` inside a zip folder | [Path A — Windows installer](#path-a--windows-installer-easiest) (unzip first) |
| A project folder with `Install GridNotes.bat` | [Path B — Install from source](#path-b--install-from-source-code) |

---

## Path A — Windows installer (easiest)

**No Python required.**

1. **Get the app**
   - Download `GridNotes-Setup.exe` from a release, or
   - Download and unzip `GridNotes-Windows.zip`.

2. **Install or run**
   - **Setup.exe:** Double-click `GridNotes-Setup.exe` → follow the wizard → Finish.
   - **Zip:** Unzip the folder → open it → double-click `GridNotes.exe`.

3. **Open GridNotes**
   - Use the Start menu or desktop shortcut (if you created one during setup).

4. **First steps in the app**
   - Use **Controls → Import race JSON** to load iRacing race results.
   - Click a driver in the table to add notes or like/dislike.

**Where your data is stored**

```
%APPDATA%\GridNotes\
```

Your database file is `driver_history.db` in that folder. Updates to the app do not delete it.

---

## Path B — Install from source code

Use this if you downloaded the GitHub project (ZIP) or cloned the repository. You will use the graphical install wizard in the project folder.

### Windows

1. **Install Python 3.10 or newer**
   - Download from [python.org/downloads](https://www.python.org/downloads/).
   - On the installer’s first screen, enable **“Add python.exe to PATH”**.
   - Complete the installation.

2. **Get the GridNotes folder**
   - Download the repository ZIP from GitHub and unzip it, or clone with Git.
   - You should see files such as `main.py`, `Install GridNotes.bat`, and `requirements.txt`.

3. **Run the install wizard**
   - Open the GridNotes folder.
   - Double-click **`Install GridNotes.bat`**.
   - Click **Install** and wait for the progress bar to finish (internet required).

4. **Start the app**
   - Click **Launch GridNotes** in the wizard, or
   - Double-click **`Run GridNotes.bat`** anytime later.

**Optional:** Check **“Also build a standalone Windows app”** in the wizard to create `dist\GridNotes\GridNotes.exe`. This takes several minutes and is not required to run the app.

### macOS

Live iRacing session features require Windows. On Mac you can still import JSON, view stats, and keep notes.

1. **Install Python 3.10+** from [python.org](https://www.python.org/downloads/) or Homebrew.

2. **Get and open the GridNotes folder** (same as Windows step 2).

3. **Run the install wizard**
   - Double-click **`Install GridNotes.command`**.
   - If macOS says the file can’t be opened: right-click → **Open** → **Open** again.

4. **Install and launch**
   - Click **Install**, then **Launch GridNotes**, or use **`Run GridNotes.command`** later.

**Where your data is stored (source install)**

`driver_history.db` in the GridNotes project folder (same folder as `main.py`).

---

## After installation (all users)

1. **Import race history** — **Controls → Import race JSON**  
   Supports iRacing `event_result` exports and the JSON formats described in [README.md](README.md).

2. **Scout drivers** — Select a row to open notes, like/dislike, and safety stats.

3. **Settings** — Open the **Settings** tab for appearance, data retention, and more. Click **Save settings** after changes.

4. **Live session (Windows only)** — With iRacing running, use **Live Mode** and **Current session only** to focus on drivers in your lobby. Full race history still comes from JSON import.

5. **Check for updates (source installs)** — **Settings → Maintenance → Check for updates**. If updates are available, use **Update now** to pull the latest code and restart (or open the download page for a packaged build).

---

## Troubleshooting

### “Python was not found” (Path B on Windows)

- Reinstall Python from [python.org](https://www.python.org/downloads/).
- Enable **“Add python.exe to PATH”**.
- Close and reopen the GridNotes folder, then run `Install GridNotes.bat` again.

### Install wizard won’t start

From a terminal in the project folder:

```bash
python install_gui.py
```

On Mac, use `python3` instead of `python` if needed.

### App won’t connect to iRacing

- Live SDK features work on **Windows** with **iRacing running** and you in a session.
- Importing race results does **not** require the SDK — use **Import race JSON**.

### Something else went wrong

Check the log file:

| How you run GridNotes | Log file |
|-----------------------|----------|
| Installed `.exe` / Setup | `%APPDATA%\GridNotes\gridnotes.log` |
| From source (`Run GridNotes.bat`) | `gridnotes.log` in the project folder |

The log is cleared each time the app starts.

---

## Building an installer (advanced, for developers)

If you are packaging GridNotes for others on Windows, see [README.md — Build a Windows installer](README.md#build-a-windows-installer).

---

## More help

- Feature overview and JSON formats: [README.md](README.md)
- Run from source without the wizard: [README.md — Run from source](README.md#run-from-source-manual)
