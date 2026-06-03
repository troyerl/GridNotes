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

## Publisher name on install / uninstall

The installer metadata uses **Logan Troyer** as publisher (`AppPublisher` in `scripts\gridnotes.iss`). Builds also embed **CompanyName** in `GridNotes.exe` and the setup executable version resource.

**Settings → Apps** should show **Publisher: Logan Troyer** after install. If you installed with `GridNotes-Setup.exe`, launch GridNotes once so it refreshes the Apps list entry.

**SmartScreen / UAC “Unknown publisher”** on the yellow/blue prompt is normal for apps that are **not code-signed**. Windows only shows a verified publisher name when the `.exe` is signed with an Authenticode certificate. Removing that warning requires purchasing a code-signing cert and configuring `SignTool` in the Inno Setup script (not included in public builds).

## Automatic builds on GitHub

When you push a version tag (for example `v1.0.21`), the **Release** workflow on GitHub Actions:

1. Copies the matching section from **`docs/RELEASE_NOTES.md`** (heading `## v1.0.21 — …`) into the GitHub Release description.
2. Runs `scripts/build_installer.ps1` on Windows.
3. Uploads `GridNotes-Setup.exe` and `GridNotes-Windows.zip` to that release when the build succeeds.

Add or edit the section in `docs/RELEASE_NOTES.md` **before** pushing the tag.

You can still build locally with `scripts\build_installer.bat` before tagging.

## Attach to GitHub Release (manual)

1. Open https://github.com/troyerl/GridNotes/releases  
2. Edit release **v1.0.0** (or create one with tag **`v1.0.0`** — must start with `v`).  
3. Under **Assets**, upload **`dist\GridNotes-Setup.exe`**.  
4. Save the release.

End users can then download `GridNotes-Setup.exe` from **Assets** — not from “Source code (zip)”.
