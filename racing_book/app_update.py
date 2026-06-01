"""Check for and apply GridNotes application updates."""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

from .app_version import __version__, is_newer_version

logger = logging.getLogger(__name__)

GITHUB_OWNER = "troyerl"
GITHUB_REPO = "race_book"
GITHUB_RELEASES_API = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
GITHUB_RELEASES_PAGE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
REQUEST_TIMEOUT_SEC = 15
_GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "GridNotes-Updater",
}


@dataclass(frozen=True)
class UpdateCheckResult:
    ok: bool
    message: str
    current_version: str
    latest_version: str | None = None
    download_url: str | None = None
    release_notes: str | None = None
    update_available: bool = False
    can_apply_in_place: bool = False
    source_update_commits: int = 0


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def is_frozen_build() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_git_source_tree(root: Path | None = None) -> bool:
    root = root or project_root()
    return (root / ".git").is_dir()


def _normalize_tag(tag: str) -> str:
    return re.sub(r"^v", "", (tag or "").strip(), flags=re.IGNORECASE)


def _git_default_branch(root: Path) -> str:
    try:
        branch = subprocess.check_output(
            ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            cwd=root,
            text=True,
            timeout=10,
        ).strip()
        if branch.startswith("origin/"):
            return branch.split("/", 1)[1]
    except (subprocess.SubprocessError, OSError, ValueError):
        pass
    for candidate in ("main", "master"):
        try:
            subprocess.check_output(
                ["git", "rev-parse", f"origin/{candidate}"],
                cwd=root,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            return candidate
        except (subprocess.SubprocessError, OSError):
            continue
    return "main"


def git_source_status(root: Path | None = None) -> tuple[bool, int, str]:
    """Return whether git pull is possible and how many commits origin is ahead."""
    root = root or project_root()
    if not is_git_source_tree(root):
        return False, 0, ""

    try:
        subprocess.run(
            ["git", "fetch", "--quiet", "origin"],
            cwd=root,
            timeout=REQUEST_TIMEOUT_SEC,
            check=True,
        )
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root,
            text=True,
            timeout=10,
        ).strip()
        upstream = f"origin/{branch}"
        try:
            subprocess.check_output(
                ["git", "rev-parse", upstream],
                cwd=root,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except (subprocess.SubprocessError, OSError):
            default_branch = _git_default_branch(root)
            upstream = f"origin/{default_branch}"
            branch = default_branch

        behind_text = subprocess.check_output(
            ["git", "rev-list", "--count", f"HEAD..{upstream}"],
            cwd=root,
            text=True,
            timeout=10,
        ).strip()
        behind = int(behind_text) if behind_text.isdigit() else 0
        return True, behind, branch
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        logger.warning("Could not determine git update status: %s", exc)
        return False, 0, ""


def check_github_release() -> tuple[bool, str, str | None, str | None, str | None]:
    """Return (ok, message, latest_version, download_url, release_notes)."""
    try:
        response = requests.get(
            GITHUB_RELEASES_API,
            headers=_GITHUB_HEADERS,
            timeout=REQUEST_TIMEOUT_SEC,
        )
    except requests.RequestException as exc:
        logger.warning("GitHub release check failed: %s", exc)
        return False, f"Could not reach GitHub ({exc}).", None, None, None

    if response.status_code == 404:
        return (
            True,
            "No published releases yet. Check the GitHub repository for updates.",
            None,
            GITHUB_RELEASES_PAGE,
            None,
        )
    if response.status_code != 200:
        return (
            False,
            f"GitHub returned status {response.status_code} while checking for updates.",
            None,
            None,
            None,
        )

    payload = response.json()
    latest_version = _normalize_tag(str(payload.get("tag_name", "")))
    release_notes = str(payload.get("body", "") or "").strip() or None
    download_url = str(payload.get("html_url", "") or "") or GITHUB_RELEASES_PAGE

    for asset in payload.get("assets") or []:
        name = str(asset.get("name", "")).lower()
        if name.endswith(".exe") or name.endswith(".zip"):
            download_url = str(asset.get("browser_download_url", "") or download_url)
            break

    if not latest_version:
        return False, "Release information from GitHub did not include a version.", None, None, None

    return True, "Release check completed.", latest_version, download_url, release_notes


def check_for_updates() -> UpdateCheckResult:
    """Check GitHub releases and, for source installs, whether git pull has updates."""
    current = __version__
    release_ok, release_message, latest, download_url, notes = check_github_release()

    can_apply = False
    source_behind = 0
    update_available = False
    messages: list[str] = []

    if release_ok and latest:
        if is_newer_version(latest, current):
            update_available = True
            messages.append(f"A newer release is available: v{latest} (you have v{current}).")
        else:
            messages.append(f"You have the latest published release (v{current}).")
    elif release_ok:
        messages.append(release_message)
    else:
        messages.append(release_message)

    if not is_frozen_build() and is_git_source_tree():
        git_ok, behind, branch = git_source_status()
        if git_ok and behind > 0:
            update_available = True
            can_apply = True
            source_behind = behind
            noun = "commit" if behind == 1 else "commits"
            messages.append(
                f"Source install: {behind} new {noun} on origin/{branch} can be pulled."
            )
        elif git_ok:
            messages.append("Source install: already up to date with origin.")
            can_apply = True
        else:
            messages.append("Source install: could not compare with origin.")

    if update_available and can_apply:
        action = "Click “Update now” to pull the latest code and restart."
    elif update_available and is_frozen_build():
        action = "Download the latest installer from GitHub to update."
    elif update_available:
        action = "See GitHub for download instructions."
    else:
        action = ""

    message = " ".join(part for part in [*messages, action] if part)
    return UpdateCheckResult(
        ok=release_ok or can_apply,
        message=message,
        current_version=current,
        latest_version=latest,
        download_url=download_url,
        release_notes=notes,
        update_available=update_available,
        can_apply_in_place=can_apply and source_behind > 0,
        source_update_commits=source_behind,
    )


def apply_source_update(root: Path | None = None) -> tuple[bool, str]:
    """Run git pull --ff-only for a source checkout."""
    root = root or project_root()
    if not is_git_source_tree(root):
        return False, "This install is not a git repository."

    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.exception("git pull failed")
        return False, str(exc)

    output = (result.stdout or result.stderr or "").strip()
    if result.returncode != 0:
        return False, output or "git pull failed."

    logger.info("git pull succeeded: %s", output or "(no output)")
    return True, output or "Updated successfully."


def restart_application() -> None:
    """Restart GridNotes so code and UI changes take effect."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        app.quit()

    if is_frozen_build():
        os_args = [sys.executable]
        executable = sys.executable
    else:
        main_py = project_root() / "main.py"
        executable = sys.executable
        os_args = [sys.executable, str(main_py)]

    logger.info("Restarting application: %s", " ".join(os_args))
    import os

    os.execv(executable, os_args)
