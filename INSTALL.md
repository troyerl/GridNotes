# How to install GridNotes

**Version 1.0.17**

GridNotes helps you remember iRacing drivers you raced with and keep private notes.  
You do **not** need to know how to code. Follow the steps below in order.

---

## Start here

**In your download folder you should see two `.bat` files:**

| File | What it does |
|------|----------------|
| **`Install GridNotes.bat`** | **Installer** — run **once** to set up GridNotes (not the app itself). |
| **`Open GridNotes.bat`** | **Opens GridNotes** after you have installed (or finds your install folder). |

After install, use the **GridNotes** icon on your **Desktop**. The app does **not** run from the ZIP/download folder.

Answer one question: **What did you download?**

> **Downloaded the GitHub code (ZIP or “Source code”)?**  
> You will **not** see `GridNotes-Setup.exe` in that folder. That is normal.  
> Use **[section B](#b-i-have-a-folder-from-github-many-files-including-install-gridnotesbat)** below (`Install GridNotes.bat`).

> **`GridNotes-Setup.exe` only comes from:**  
> - A [GitHub Release](https://github.com/troyerl/race_book/releases) **asset** (if the author attached it), or  
> - Building it yourself on Windows (see [For people who package GridNotes](#for-people-who-package-gridnotes-technical)).

### A) I have `GridNotes-Setup.exe` (or a release zip with `GridNotes.exe` inside)

This is the **easy install**. You do **not** need Python.  
(This file is **not** included in the source-code download from GitHub.)

1. **Double-click** `GridNotes-Setup.exe`.
2. Click **Next**, then **Install**, then **Finish**.
3. Open **GridNotes** from the Windows Start menu (search “GridNotes”).
4. In the app, click **Controls** → **Import race JSON** to load your race files.

**Done.** Skip the rest of this page unless something went wrong.

---

### B) I have a **folder** from GitHub (many files, including `Install GridNotes.bat`)

This folder is the “download version.” You need to run the **install helper** once.

#### Step 1 — Install Python (one time only, Windows)

Python is free software GridNotes needs. You are not writing code.

**GridNotes needs Python 3.10–3.13** for the install helper (not 3.14 alone).

- If you only have **Python 3.14**, the install script can try to **download and install Python 3.13 for you** (via `winget` or the official python.org installer). You still need **some** Python on PATH to run `Install GridNotes.bat` (3.14 is fine for that one step).
- If automatic install fails, install **Python 3.13** (or 3.12) yourself:

1. Open **https://www.python.org/downloads/**
2. Download **Python 3.13** (or 3.12) and run the installer.
3. On the **first screen**, turn **ON** **“Add python.exe to PATH”**.
4. Click **Install Now** and finish.

#### Step 2 — Extract the download anywhere

1. Open your **Downloads** folder, **Desktop**, or anywhere you saved the project.
2. If it is a **.zip** file, **right-click** it → **Extract All** → **Extract**.
3. Open the extracted folder. You should see **`Install GridNotes.bat`** and **`Open GridNotes.bat`** (Windows).  
   **`Install GridNotes.bat` is only the installer**, not the app. You can move or delete this folder **after** install — GridNotes runs from the install location, not from here.

#### Step 3 — Run the install helper

1. **Double-click** `Install GridNotes.bat`.  
   **Default install** and **D:\** need **no** administrator.  
   **`C:\Program Files`** only: **right-click** → **Run as administrator**, or run `Install GridNotes.bat /elevate`.  
   If the black window closes instantly, open **`install-helper.log`** in the same folder.
2. A window titled **Install GridNotes** opens.
3. Leave the **install folder** as shown (default: your user folder, **no admin**), or use **Choose folder…** for **D:\** (→ `D:\GridNotes`).  
   For **`C:\Program Files`**, use advanced → **Use Program Files** and **right-click** `Install GridNotes.bat` → **Run as administrator**.
4. Leave **“Create an icon on my Desktop”** turned on if you want a desktop icon.
5. Click **Install GridNotes** and wait. A bar will move across the screen; this can take several minutes.
6. When it says finished, click **Launch GridNotes** (or use the Desktop icon afterward).

#### Step 4 — Open GridNotes later

Use any of these (they all start the **installed** app, not the installer):

- The **GridNotes** icon on your **Desktop** (recommended), or  
- **`Open GridNotes.bat`** in your download folder, or  
- **`Run GridNotes.bat`** in your install folder (see below).

**Where did it install?**  
Default (no administrator):

`C:\Users\YourName\AppData\Local\Programs\GridNotes`

Or **`D:\GridNotes`** if you chose the D: drive.  
**`C:\Program Files\GridNotes`** only if you installed as administrator.

Your notes, settings, and **`gridnotes.log`** are saved in your Windows user data folder:

`%APPDATA%\GridNotes\`

(Files: `driver_history.db`, `gridnotes.log` — not in the install folder on `D:\`.)

The default install path needs **no** administrator permission. Use **Show advanced options** only if you want **Program Files** (requires **Run as administrator**).

---

### C) I’m on a Mac

1. Install Python from **https://www.python.org/downloads/** (download and run the installer).
2. Unzip the GridNotes folder if needed.
3. **Double-click** `Install GridNotes.command`.  
   If Mac says it cannot open the file: **right-click** the file → **Open** → **Open**.
4. Click **Install GridNotes**, then **Launch GridNotes**.

**Note:** Live iRacing session features need **Windows**. On Mac you can still import races and keep notes.

---

## First time using the app

1. Open GridNotes.
2. Click **Controls** → **Import race JSON** and choose your iRacing race export file.
3. Click a driver’s name to add notes or mark like/dislike.
4. Optional: **Settings** tab → pick light/dark theme → **Save settings**.

---

## Updating GridNotes (no reinstall)

If you installed with **`Install GridNotes.bat`** (for example `D:\GridNotes`):

1. Open GridNotes → **Settings** → **Check for updates** (or turn on automatic check on startup).
2. When a newer version is available, click **Update now**.
3. GridNotes closes briefly, then reopens. The update refreshes **application files**, **icons**, **launch scripts**, **Desktop/Start shortcuts**, and the version shown in **Windows Settings → Apps**.

You do **not** need to uninstall or run the installer again for normal updates.

**Taskbar icon after an update:** If you pinned GridNotes before, **unpin** the old icon once, then **right-click the Desktop shortcut** → **Pin to taskbar**.

If you installed with **`GridNotes-Setup.exe`** (standalone `.exe` build), use a new setup installer from [Releases](https://github.com/troyerl/race_book/releases) to update.

---

## Something went wrong?

### I have Python 3.14 and GridNotes will not start

GridNotes **does not use Python 3.14** for the app in `D:\GridNotes\.venv`.

1. Run **`Install GridNotes.bat`** again — it may **install Python 3.13 automatically** (watch the console).  
2. If that fails, install **Python 3.13** yourself from https://www.python.org/downloads/ (keep 3.14 if you want).  
3. Delete **`D:\GridNotes\.venv`**.  
4. Run **`Install GridNotes.bat`** again, then **`Run GridNotes.bat`**.

The built **`GridNotes.exe`** in `dist\` uses its own Python and is not affected.

### “Python was not found” (Windows)

You skipped Step 1 or did not check **Add python.exe to PATH**.

1. Install Python again from https://www.python.org/downloads/  
2. Check **Add python.exe to PATH** on the first screen.  
3. Close all folders, open the GridNotes download folder again, double-click **`Install GridNotes.bat`**.

### The install window never opens (black window flashes and closes)

1. Open **`install-helper.log`** in your download folder (same folder as `Install GridNotes.bat`) and read the last lines.  
2. Make sure Python is installed with **Add python.exe to PATH** (see above).  
3. Double-click **`Install GridNotes.bat`** again — do **not** click No on a UAC prompt unless you chose Program Files.  
4. If Windows SmartScreen warns you, click **More info** → **Run anyway**.

### “Permission denied” writing to AppData or `launch-error.log`

This usually means **`%APPDATA%\GridNotes`** was created by an **administrator** install and your normal user cannot write there.

**Fix (pick one):**

1. **Delete the locked folder** (if you have no important data there):  
   Remove **`C:\Users\<you>\AppData\Roaming\GridNotes`** (and retry). GridNotes will recreate it under **`%LOCALAPPDATA%\GridNotes`** or **`%TEMP%\GridNotes`**.
2. **Fix permissions:** Right-click **`AppData\Roaming\GridNotes`** → **Properties** → **Security** → give your user **Full control**.
3. **Re-install without admin:** Run **`Install GridNotes.bat`** as a normal user (not “Run as administrator”) to **`D:\GridNotes`** or the default user folder.

After updating to the **latest release**, copy fresh **`gridnotes_start.py`** and **`Run GridNotes.bat`** into your install folder, or run the installer again.

### “Access denied” or `[WinError 5]` during install

Windows blocked writing to **Program Files** without administrator permission.

**Easiest fix:** Use the default install path (no admin), or choose **D:\** in the wizard → `D:\GridNotes`.

**For Program Files:**

1. Close the installer.  
2. Right-click **`Install GridNotes.bat`** → **Run as administrator**.  
3. Advanced options → **Use Program Files (admin)** → install again.

**For D: drive:** use **Choose folder…** in the wizard — no admin needed.

### How do I uninstall GridNotes?

**Option A — Windows Settings (recommended)**

1. Open **Settings** → **Apps** → **Installed apps** (or **Apps & features**).
2. Find **GridNotes** → **Uninstall**.
3. Answer whether to delete your notes and database.

**Option B — Inside GridNotes**

1. Open GridNotes → **Settings** → **Maintenance** → **Uninstall**.
2. Optionally check **Also delete my notes, database, and settings**.
3. Click **Uninstall GridNotes…** and confirm.

Both options remove the Desktop shortcut(s) and install folder (for example `D:\GridNotes`).  
The whole install folder (for example `D:\GridNotes`) is deleted after you click **OK**  
on the final message — GridNotes must fully close first (a background script then  
removes the folder). Wait about 30 seconds. If `D:\GridNotes` remains, delete it in  
File Explorer or open `%TEMP%\gridnotes-uninstall.log` for details.  
Your data stays unless you choose to delete it.

**Note:** GridNotes appears in the Apps list after you install with **`Install GridNotes.bat`**.  
The **`GridNotes-Setup.exe`** installer registers automatically as well.

### I closed the app — how do I open it again?

- Double-click the **Desktop** icon **GridNotes**, or  
- Use the **Desktop** icon **GridNotes** (no console window), or double-click **`Launch GridNotes.vbs`** in your install folder.  
  Use **`Run GridNotes.bat`** only when troubleshooting (shows a console).

**Taskbar pin:** Right‑click your **Desktop “GridNotes”** shortcut → **Properties**. **Target** should be **`D:\GridNotes\.venv\Scripts\GridNotes.exe`** with **Arguments** `D:\GridNotes\gridnotes_start.py` — not `gridnotes_start.py` alone. If it is wrong, update GridNotes and open the app once (shortcuts rebuild automatically). **Unpin** any old taskbar icon, then **Pin to taskbar** from that Desktop shortcut.

### Desktop icon or “Launch GridNotes” does nothing

This often happens if the installer ran **as administrator** but GridNotes needs to run as **you** (common when installing to **D:\GridNotes**).

1. Open your **install folder** (for example `D:\GridNotes`).  
2. Double-click the **Desktop** icon **GridNotes**, or **`Launch GridNotes.vbs`** in your install folder.  
   Use **`Run GridNotes.bat`** only if you need a console for errors.  
   If the window flashes and closes, it will **pause** and show the log path on screen.  
   Or run **`Diagnose GridNotes.bat`** in your install folder to test Python/PyQt6 imports.  
   On Windows, logs are usually in **`%LOCALAPPDATA%\GridNotes\`** (or **`%APPDATA%\GridNotes\`**):  
   **`gridnotes.log`** (app) and **`launch-error.log`** (startup).  
   If AppData is locked (admin install), GridNotes uses **`%TEMP%\GridNotes\`** instead.  
   **`Run GridNotes.bat`** also writes **`%TEMP%\GridNotes-launch.log`**.  
   If that file stops after `Install folder: D:\GridNotes`, re-run **`Install GridNotes.bat`** from the latest ZIP (fixes a Windows batch bug that hid the real error).  
3. Run **`Install GridNotes.bat`** again from your download ZIP folder — choose **D:\** again, finish install, use the new Desktop icon. **Do not** use “Run as administrator” unless you install to C:\Program Files.  
4. Or double-click **`Open GridNotes.bat`** in your download folder after install.

### GridNotes does not see iRacing

- Live session tools only work on **Windows** with **iRacing already running**.  
- To add old races, use **Import race JSON** — that does not need iRacing open.

### “Could not find requirements.txt”

The installer copies **from your download folder** into **Program Files** (or the folder you chose). Run **`Install GridNotes.bat` from the extracted download** (the folder that contains `main.py` and `requirements.txt`), not from `C:\Program Files\GridNotes` before install finishes.

1. Open the folder where you **extracted the ZIP** (e.g. `race_book-main` or `racing_book`).  
2. Confirm you see **`requirements.txt`** and **`Install GridNotes.bat`** in that same folder.  
3. Double-click **`Install GridNotes.bat`** there again.  
4. Leave the default install location as-is and click **Install GridNotes**.

### I don’t see `GridNotes-Setup.exe` anywhere

You probably downloaded the **project source** (green **Code → Download ZIP**). That folder has `Install GridNotes.bat`, not the Setup installer.

**Do this instead:**

1. Open the folder you unzipped.  
2. Follow **[section B](#b-i-have-a-folder-from-github-many-files-including-install-gridnotesbat)** (Python once, then `Install GridNotes.bat`).

**Or** open [Releases](https://github.com/troyerl/race_book/releases) and download **`GridNotes-Setup.exe`** under **Assets** — only if it was uploaded for that release.

### Still stuck?

Ask whoever shared GridNotes for either **`GridNotes-Setup.exe`** (from a release) or help running **`Install GridNotes.bat`**.

If you are comfortable sending a log file, look for `gridnotes.log` in:

- **Setup.exe install:** `%APPDATA%\GridNotes\`  
- **Install helper install:** your install folder (see Step 4 above)

---

## For people who package GridNotes (technical)

Developers building `GridNotes-Setup.exe` or releasing on GitHub: see [README.md — Build a Windows installer](README.md#build-a-windows-installer).  
Advanced wizard options (custom folders, standalone `.exe` build) are under **Show advanced options** in the install helper.
