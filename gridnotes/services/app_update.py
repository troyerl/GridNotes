"""Check for and apply GridNotes application updates."""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ProgressCallback = Callable[[str, int], None]

import requests

from ..app.app_version import installed_version, is_newer_version

logger = logging.getLogger(__name__)

GITHUB_OWNER = "troyerl"
GITHUB_REPO = "GridNotes"
GITHUB_RELEASES_API = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
GITHUB_RELEASES_PAGE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
AUTO_CHECK_UPDATES_KEY = "auto_check_updates_on_startup"
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
    release_zip_url: str | None = None
    release_setup_url: str | None = None
    apply_method: str | None = None  # "git", "portable", "frozen", or "installer"
    requires_windows_permission: bool = False


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


def _release_asset_urls(payload: dict) -> tuple[str | None, str | None]:
    """Prefer GridNotes-Windows.zip, then any release .zip; return (zip_url, setup_exe_url)."""
    zip_url: str | None = None
    setup_exe: str | None = None
    for asset in payload.get("assets") or []:
        name = str(asset.get("name", "")).lower()
        url = str(asset.get("browser_download_url", "") or "").strip()
        if not url:
            continue
        if name.endswith(".zip"):
            if "gridnotes-windows" in name or zip_url is None:
                zip_url = url
        elif name.endswith(".exe") and ("setup" in name or "gridnotes" in name):
            setup_exe = url
    return zip_url, setup_exe


def check_github_release() -> tuple[
    bool, str, str | None, str | None, str | None, str | None, str | None
]:
    """Return (ok, message, latest_version, download_url, release_notes, zip_url, setup_url)."""
    try:
        response = requests.get(
            GITHUB_RELEASES_API,
            headers=_GITHUB_HEADERS,
            timeout=REQUEST_TIMEOUT_SEC,
        )
    except requests.RequestException as exc:
        logger.warning("GitHub release check failed: %s", exc)
        return False, f"Could not reach GitHub ({exc}).", None, None, None, None, None

    if response.status_code == 404:
        return (
            True,
            "No published releases yet. Check the GitHub repository for updates.",
            None,
            GITHUB_RELEASES_PAGE,
            None,
            None,
            None,
        )
    if response.status_code != 200:
        return (
            False,
            f"GitHub returned status {response.status_code} while checking for updates.",
            None,
            None,
            None,
            None,
            None,
        )

    payload = response.json()
    latest_version = _normalize_tag(str(payload.get("tag_name", "")))
    release_notes = str(payload.get("body", "") or "").strip() or None
    download_url = str(payload.get("html_url", "") or "") or GITHUB_RELEASES_PAGE
    zip_url, setup_exe = _release_asset_urls(payload)

    if not latest_version:
        return (
            False,
            "Release information from GitHub did not include a version.",
            None,
            None,
            None,
            None,
            None,
        )

    return (
        True,
        "Release check completed.",
        latest_version,
        download_url,
        release_notes,
        zip_url,
        setup_exe,
    )


def check_for_updates() -> UpdateCheckResult:
    """Check GitHub releases and, for source installs, whether git pull has updates."""
    current = installed_version()
    release_ok, release_message, latest, download_url, notes, zip_url, setup_url = (
        check_github_release()
    )

    can_apply = False
    source_behind = 0
    update_available = False

    if release_ok and latest and is_newer_version(latest, current):
        update_available = True

    apply_method: str | None = None

    if not is_frozen_build() and is_git_source_tree():
        git_ok, behind, branch = git_source_status()
        if git_ok and behind > 0:
            update_available = True
            can_apply = True
            apply_method = "git"
            source_behind = behind
        elif git_ok and behind == 0 and not update_available:
            pass

    if apply_method is None and not is_frozen_build():
        from ..installer.portable_update import portable_install_root

        portable_root = portable_install_root()
        if (
            portable_root is not None
            and release_ok
            and latest
            and is_newer_version(latest, current)
        ):
            update_available = True
            can_apply = True
            apply_method = "portable"

    if (
        apply_method is None
        and is_frozen_build()
        and release_ok
        and latest
        and is_newer_version(latest, current)
    ):
        from ..installer.frozen_update import frozen_install_root

        install_root = frozen_install_root()
        if install_root is not None:
            update_available = True
            can_apply = True
            if zip_url:
                apply_method = "frozen"
            elif setup_url:
                apply_method = "installer"

    from ..installer.logic import update_requires_windows_permission
    from ..installer.user_messages import update_check_user_message

    requires_windows_permission = update_requires_windows_permission(apply_method)

    message = update_check_user_message(
        update_available=update_available,
        current=current,
        latest=latest,
        release_ok=release_ok,
        release_message=release_message,
        can_apply=can_apply and apply_method is not None,
        apply_method=apply_method,
        is_frozen=is_frozen_build(),
        requires_windows_permission=requires_windows_permission,
    )
    return UpdateCheckResult(
        ok=release_ok or can_apply,
        message=message,
        current_version=current,
        latest_version=latest,
        download_url=download_url,
        release_notes=notes,
        release_zip_url=zip_url,
        release_setup_url=setup_url,
        update_available=update_available,
        can_apply_in_place=can_apply and apply_method is not None,
        source_update_commits=source_behind,
        apply_method=apply_method,
        requires_windows_permission=requires_windows_permission,
    )


def apply_source_update(
    root: Path | None = None,
    on_progress: ProgressCallback | None = None,
) -> tuple[bool, str]:
    """Run git pull --ff-only for a source checkout."""
    root = root or project_root()
    if not is_git_source_tree(root):
        return False, "This install is not a git repository."

    if on_progress is not None:
        on_progress("Pulling latest code from GitHub…", 25)

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
        from ..installer.user_messages import source_update_failed_message

        return False, source_update_failed_message(output or "git pull failed.")

    logger.info("git pull succeeded: %s", output or "(no output)")
    if sys.platform == "win32":
        try:
            from ..installer.logic import refresh_installed_artifacts
            from ..installer.uninstall import resolve_install_root

            install_root = resolve_install_root()
            if install_root is not None and (install_root / "main.py").is_file():
                if on_progress is not None:
                    on_progress("Refreshing Windows launchers and shortcuts…", 85)
                refresh_installed_artifacts(install_root, upgrade_dependencies=True)
        except Exception:
            logger.exception("Post-pull Windows refresh failed")
    if on_progress is not None:
        on_progress("Restarting GridNotes…", 100)
    from ..installer.user_messages import source_update_success_message

    return True, source_update_success_message()


def restart_application() -> None:
    """Restart GridNotes so code and UI changes take effect."""
    import os

    from PyQt6.QtWidgets import QApplication

    from ..installer.logic import find_project_root, relaunch_gridnotes
    from ..installer.uninstall import resolve_install_root

    app = QApplication.instance()
    if app is not None:
        app.quit()

    install_root = resolve_install_root()
    if install_root is None and is_frozen_build():
        install_root = Path(sys.executable).resolve().parent
    if install_root is None:
        try:
            candidate = find_project_root()
            if (candidate / "main.py").is_file():
                install_root = candidate
        except Exception:
            pass

    if install_root is not None and relaunch_gridnotes(install_root):
        logger.info("Restarting GridNotes via new process at %s", install_root)
        os._exit(0)

    if is_frozen_build():
        executable = sys.executable
        os_args = [sys.executable]
    else:
        main_py = (install_root or find_project_root()) / "main.py"
        executable = sys.executable
        os_args = [sys.executable, str(main_py)]

    logger.info("Restarting application (execv): %s", " ".join(os_args))
    os.execv(executable, os_args)
