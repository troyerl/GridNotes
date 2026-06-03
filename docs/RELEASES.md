# Releasing GridNotes (developers)

How to ship a **stable** release that prompts users to update, and how to publish **test builds** that do not.

## How in-app updates work

GridNotes calls GitHub’s **latest full release** API:

`GET /repos/troyerl/GridNotes/releases/latest`

That endpoint **ignores pre-releases and drafts**. Only a normal (non–pre-release) release can become “latest.”

So:

| You publish | Users on `1.0.34` see |
|-------------|------------------------|
| `v1.0.35` — **full** release | Update available → `1.0.35` |
| `v1.0.35-rc1` — **pre-release** | Still on `1.0.34` (no update prompt) |

Implementation: `gridnotes/services/app_update.py`.

---

## Stable release (production)

1. Merge changes to `main`.
2. Bump `gridnotes/app/app_version.py` (`__version__`).
3. Add a section to **`docs/RELEASE_NOTES.md`**:
   - Heading must match the tag, e.g. `## v1.0.35 — 2026-06-02`
4. Commit and push `main`.
5. Tag **without a hyphen** in the version part after `v`:
   ```bash
   git tag v1.0.35
   git push origin v1.0.35
   ```
6. GitHub Actions **Release** workflow builds and uploads:
   - `GridNotes-Setup.exe`
   - `GridNotes-Windows.zip`
7. The release is published as a **full** release (not pre-release). It becomes **latest** for update checks.

Installer build details: [BUILD_WINDOWS_INSTALLER.md](BUILD_WINDOWS_INSTALLER.md).

---

## Pre-release / test build (no update for users)

Use a tag that contains a **hyphen** after the `v` prefix. Examples:

- `v1.0.35-rc1`
- `v1.0.35-beta2`
- `v1.0.35-test1`

### Steps

1. Add a matching section in **`docs/RELEASE_NOTES.md`** (same as stable), e.g. `## v1.0.35-rc1 — 2026-06-02`.
2. You may bump `__version__` on a branch for local testing, or leave it until the stable tag.
3. Push the tag:
   ```bash
   git tag v1.0.35-rc1
   git push origin v1.0.35-rc1
   ```
4. The **Release** workflow (`.github/workflows/release.yml`) sets **`prerelease: true`** when the tag name contains `-`.
5. Download the installer from that release’s **Assets** on GitHub and install on your test machine.

Pre-releases still run the same Windows build; they are only excluded from “latest” for update checks.

### What not to do

- Do **not** push a **full** release with a higher version (e.g. `v1.0.35`) until you want everyone to be offered the update.
- Do **not** rely on a tag alone without a GitHub Release if you need the CI-built `GridNotes-Setup.exe` (the workflow creates the release).

---

## Tag naming rules (summary)

| Tag pattern | GitHub pre-release? | Becomes “latest” for updates? |
|-------------|---------------------|------------------------------|
| `v1.0.35` | No | Yes |
| `v1.0.35-rc1` | Yes (automatic) | No |
| `v1.0.35-beta1` | Yes (automatic) | No |

The workflow uses: `prerelease: ${{ contains(github.ref_name, '-') }}`.

Avoid hyphens in stable tags (e.g. do not use `v1.0.35` with extra segments unless you mean pre-release).

---

## Release workflow

File: `.github/workflows/release.yml`

- Triggers on push of any tag matching `v*`.
- Reads release notes via `scripts/extract_release_notes.py` from `docs/RELEASE_NOTES.md`.
- Builds on `windows-latest` with `scripts/build_installer.ps1`.
- Uploads assets with `softprops/action-gh-release@v2`.

---

## Local build (no tag)

To test without pushing a tag:

```bat
scripts\build_installer.bat
```

Output under `dist\`. This does not affect GitHub or other users’ update checks.

---

## Promoting a pre-release to stable

1. Finish testing from the pre-release Assets (or merge any last fixes on `main`).
2. Bump version and add **`## v1.0.35`** (no `-rc`) to `RELEASE_NOTES.md`.
3. Tag and push **`v1.0.35`** (no hyphen after the version digits in the tag name).
4. Leave the old `v1.0.35-rc1` pre-release as-is on GitHub (optional archive) or delete it from Releases if you prefer a clean list.

Users only move to the new version when they install the **full** `v1.0.35` release or use **Check for updates** after that release is latest.
