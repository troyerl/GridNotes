# Building `GridNotes-Setup.exe` (Windows)

`GridNotes-Setup.exe` is **not stored in git**. It is produced on a Windows PC and uploaded to GitHub Releases for end users.

## Build steps

1. On **Windows**, install **Python 3.10+** ([python.org](https://www.python.org/downloads/)) with **Add to PATH**.
2. Clone or unzip the project.
3. Open **Command Prompt** or **PowerShell** in the project folder.
4. Run:

```bat
scripts\build_installer.bat
```

5. Wait until it finishes (several minutes).

## Output location

| File | Path |
|------|------|
| Portable app | `dist\GridNotes\GridNotes.exe` |
| Installer (if Inno Setup installed) | `dist\GridNotes-Setup.exe` |
| Fallback zip (no Inno Setup) | `dist\GridNotes-Windows.zip` |

## If you only get a ZIP, not `GridNotes-Setup.exe`

Install **[Inno Setup 6](https://jrsoftware.org/isinfo.php)** (free), then run `scripts\build_installer.bat` again.

## Attach to GitHub Release

1. Open https://github.com/troyerl/GridNotes/releases  
2. Edit release **v1.0.0** (or create one with tag **`v1.0.0`** — must start with `v`).  
3. Under **Assets**, upload **`dist\GridNotes-Setup.exe`**.  
4. Save the release.

End users can then download `GridNotes-Setup.exe` from **Assets** — not from “Source code (zip)”.
