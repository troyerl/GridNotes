# How to install GridNotes

**Version 1.2.2**

GridNotes helps you remember iRacing drivers you raced with and keep private notes.  
You do **not** need to know how to code. Follow the steps below in order.

---

## Start here

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

1. Open this page in your browser: **https://www.python.org/downloads/**
2. Click the big yellow **Download Python** button.
3. Run the downloaded installer.
4. On the **first screen**, turn **ON** the box that says **“Add python.exe to PATH”** (important).
5. Click **Install Now** and finish.

#### Step 2 — Extract the download anywhere

1. Open your **Downloads** folder, **Desktop**, or anywhere you saved the project.
2. If it is a **.zip** file, **right-click** it → **Extract All** → **Extract**.
3. Open the extracted folder. You should see **`Install GridNotes.bat`** (Windows).  
   You can move or delete this folder **after** install — GridNotes runs from the install location, not from here.

#### Step 3 — Run the install helper

1. **Double-click** `Install GridNotes.bat`.  
   If Windows asks for permission, click **Yes** (GridNotes installs to **Program Files** like other apps).
2. A window titled **Install GridNotes** opens.
3. Leave the **install folder** as shown (default: **Program Files**). Use **Choose folder…** to pick another drive or folder — GridNotes is installed in a **GridNotes** folder there (for example choose `D:\` → installs to `D:\GridNotes`, or `D:\Program Files` → `D:\Program Files\GridNotes`).
4. Leave **“Put a GridNotes icon on my Desktop”** turned on if you want a desktop icon.
5. Click **Install GridNotes** and wait. A bar will move across the screen; this can take several minutes.
6. When it says finished, click **Launch GridNotes**.

#### Step 4 — Open GridNotes later

Use the **GridNotes** icon on your **Desktop** (recommended). It opens the copy installed on your PC, not the download folder.

You can also run **`Run GridNotes.bat`** in the install folder (see below).

**Where did it install?**  
Usually here on Windows:

`C:\Program Files\GridNotes`

(Or another drive if you chose one, for example `D:\Program Files\GridNotes`.)

Your notes and race data are saved in that install folder as `driver_history.db`.

To install without administrator permission: open **Show advanced options** → **Install for only me (no admin)**, then close the installer and run **`Install GridNotes.bat /noelevate`** from your download folder.

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

## Something went wrong?

### “Python was not found” (Windows)

You skipped Step 1 or did not check **Add python.exe to PATH**.

1. Install Python again from https://www.python.org/downloads/  
2. Check **Add python.exe to PATH** on the first screen.  
3. Close all folders, open the GridNotes download folder again, double-click **`Install GridNotes.bat`**.

### The install window never opens

1. Make sure Python is installed (see above).  
2. In the GridNotes folder, double-click **`Install GridNotes.bat`** again.  
3. If Windows SmartScreen warns you, click **More info** → **Run anyway** (you downloaded this yourself).

### “Access denied” during install

1. Use the default install folder (**Program Files**).  
2. Double-click **`Install GridNotes.bat`** again and click **Yes** when Windows asks for permission.  
3. If it still fails, right-click **`Install GridNotes.bat`** → **Run as administrator**, or use **Show advanced options** → **Install for only me (no admin)**.

### I closed the app — how do I open it again?

- Double-click the **Desktop** icon **GridNotes**, or  
- Go to your install folder and double-click **`Run GridNotes.bat`**.

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
