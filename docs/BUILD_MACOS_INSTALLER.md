# Building `GridNotes-macOS-AppleSilicon.zip`

macOS release builds are produced on **Apple Silicon (arm64)** only. Intel Macs are not supported in CI.

## Automatic builds on GitHub

When you push a version tag (for example `v1.0.53`), the **Release** workflow:

1. Runs tests on Linux
2. Builds Windows assets on `windows-latest`
3. Builds `GridNotes.app` on `macos-14` (arm64)
4. Uploads **`GridNotes-macOS-AppleSilicon.zip`** to the GitHub Release alongside the Windows installer

## Build locally on a Mac (Apple Silicon)

1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/) or Homebrew.
2. Clone or unzip the project.
3. Run:

```bash
bash scripts/build_macos.sh
```

4. Output:
   - App bundle: `dist/GridNotes.app`
   - Zip: `dist/GridNotes-macOS-AppleSilicon.zip`

## First open on another Mac

The build is **not notarized**. macOS may show “GridNotes cannot be opened”. Tell users to **right-click** `GridNotes.app` → **Open** → **Open** once.

## Platform notes

- **Live iRacing session** features (Live Mode, Grid Walk, audio spotter) require **Windows** with iRacing running.
- On macOS, users can import race JSON, manage notes, use leagues, broadcast/receiver, and other non-SDK features.
- In-app auto-update applies the Windows installer only. macOS users download a new zip from [Releases](https://github.com/troyerl/GridNotes/releases).

Windows build details: [BUILD_WINDOWS_INSTALLER.md](BUILD_WINDOWS_INSTALLER.md).
