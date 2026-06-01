# How to install GridNotes

**Version 1.2.0**

GridNotes helps you remember iRacing drivers you raced with and keep private notes.  
You do **not** need to know how to code. Follow the steps below in order.

---

## Start here

Answer one question: **What file did you download?**

### A) I have `GridNotes-Setup.exe` (or a zip with `GridNotes.exe` inside)

This is the **easy install**. You do **not** need Python.

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

#### Step 2 — Open your GridNotes folder

1. Open your **Downloads** folder (or wherever you saved the project).
2. If it is a **.zip** file, **right-click** it → **Extract All** → **Extract**.
3. Open the extracted folder. You should see **`Install GridNotes.bat`** (Windows).

#### Step 3 — Run the install helper

1. **Double-click** `Install GridNotes.bat`.
2. A window titled **Install GridNotes** opens.
3. Leave the **install folder** as shown (recommended).
4. Leave **“Put a GridNotes icon on my Desktop”** turned on if you want a desktop icon.
5. Click **Install GridNotes** and wait. A bar will move across the screen; this can take several minutes.
6. When it says finished, click **Launch GridNotes**.

#### Step 4 — Open GridNotes later

Use any of these (same app):

- The **GridNotes** icon on your Desktop, or  
- **`Run GridNotes.bat`** in your install folder (see below for where that is).

**Where did it install?**  
Usually here on Windows:

`C:\Users\YourName\AppData\Local\Programs\GridNotes`

Your notes and race data are saved in that folder as `driver_history.db`.

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

1. Do **not** change the install folder — use the default.  
2. Run **`Install GridNotes.bat`** again.  
3. If it still fails, right-click **`Install GridNotes.bat`** → **Run as administrator**.

### I closed the app — how do I open it again?

- Double-click the **Desktop** icon **GridNotes**, or  
- Go to your install folder and double-click **`Run GridNotes.bat`**.

### GridNotes does not see iRacing

- Live session tools only work on **Windows** with **iRacing already running**.  
- To add old races, use **Import race JSON** — that does not need iRacing open.

### Still stuck?

Ask whoever shared GridNotes with you to send **`GridNotes-Setup.exe`** instead of the code folder — that is the simplest install.

If you are comfortable sending a log file, look for `gridnotes.log` in:

- **Setup.exe install:** `%APPDATA%\GridNotes\`  
- **Install helper install:** your install folder (see Step 4 above)

---

## For people who package GridNotes (technical)

Developers building `GridNotes-Setup.exe` or releasing on GitHub: see [README.md — Build a Windows installer](README.md#build-a-windows-installer).  
Advanced wizard options (custom folders, standalone `.exe` build) are under **Show advanced options** in the install helper.
