#!/usr/bin/env python3
"""Print gridnotes.app.app_version.__version__ for build scripts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_VERSION_PY = ROOT / "gridnotes" / "app" / "app_version.py"


def read_app_version() -> str:
    text = APP_VERSION_PY.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    if not match:
        raise SystemExit(f"Could not read __version__ from {APP_VERSION_PY}")
    return match.group(1).strip()


if __name__ == "__main__":
    print(read_app_version())
    raise SystemExit(0)
