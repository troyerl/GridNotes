"""Command-line uninstaller (Windows Settings → Apps, or Uninstall GridNotes.bat)."""

from __future__ import annotations

import sys


def _argv_flags() -> tuple[bool, bool]:
    lowered = {arg.lower() for arg in sys.argv[1:]}
    quiet = bool(lowered & {"/s", "/silent", "/quiet", "--quiet"})
    purge = bool(lowered & {"--purge-data", "/purge-data"})
    return quiet, purge


def _ask_purge_user_data() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        result = ctypes.windll.user32.MessageBoxW(
            0,
            "Also delete your GridNotes notes, database, and settings?\n\n"
            "Choose No to keep your data.",
            "Uninstall GridNotes",
            0x04 | 0x20,  # Yes/No + question
        )
        return result == 6  # IDYES
    except OSError:
        return False


def main() -> int:
    from .uninstall import perform_uninstall, resolve_install_root

    install_root = resolve_install_root()
    quiet, purge_flag = _argv_flags()
    remove_user_data = purge_flag
    if not quiet and not purge_flag:
        remove_user_data = _ask_purge_user_data()

    result = perform_uninstall(
        install_root=install_root,
        remove_user_data=remove_user_data,
    )

    if not quiet:
        if sys.platform == "win32":
            try:
                import ctypes

                icon = 0x40 if result.ok else 0x10
                ctypes.windll.user32.MessageBoxW(
                    0,
                    result.summary(),
                    "Uninstall GridNotes",
                    icon,
                )
            except OSError:
                print(result.summary())
        else:
            print(result.summary())

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
