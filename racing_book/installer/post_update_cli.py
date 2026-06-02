"""Entry point for apply-update.bat after robocopy (reliable vs python -c)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GridNotes post-update refresh")
    parser.add_argument("version", help="Release version (e.g. 1.0.14)")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Install folder (default: current working directory)",
    )
    args = parser.parse_args(argv)
    install_root = (args.root or Path.cwd()).resolve()
    version = args.version.strip().lstrip("vV")
    if not version:
        print("post_update_cli: missing version", file=sys.stderr)
        return 1
    if not (install_root / "main.py").is_file():
        print(f"post_update_cli: not an install root: {install_root}", file=sys.stderr)
        return 1

    from ..app.app_version import write_installed_version
    from .logic import purge_install_bytecode, refresh_installed_artifacts

    write_installed_version(install_root, version)
    purge_install_bytecode(install_root)
    refresh_installed_artifacts(
        install_root,
        version=version,
        upgrade_dependencies=True,
    )
    print(f"post_update_cli: refreshed {install_root} at v{version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
