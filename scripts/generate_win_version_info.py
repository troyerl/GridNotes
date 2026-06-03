#!/usr/bin/env python3
"""Generate PyInstaller Windows version resource (CompanyName / ProductName)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_VERSION_PY = ROOT / "gridnotes" / "app" / "app_version.py"
OUT_PATH = ROOT / "scripts" / "win_version_info.txt"

PUBLISHER = "Logan Troyer"
PRODUCT = "GridNotes"


def read_app_version() -> str:
    text = APP_VERSION_PY.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    if not match:
        raise SystemExit(f"Could not read __version__ from {APP_VERSION_PY}")
    return match.group(1).strip()


def version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(p) for p in re.split(r"[.\-+]", version.strip()) if p.isdigit()]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def render(version: str) -> str:
    filevers = prodvers = version_tuple(version)
    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={filevers},
    prodvers={prodvers},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '{PUBLISHER}'),
          StringStruct('FileDescription', '{PRODUCT}'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', '{PRODUCT}'),
          StringStruct('LegalCopyright', 'Copyright (C) {PUBLISHER}'),
          StringStruct('OriginalFilename', '{PRODUCT}.exe'),
          StringStruct('ProductName', '{PRODUCT}'),
          StringStruct('ProductVersion', '{version}'),
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> int:
    version = read_app_version()
    OUT_PATH.write_text(render(version), encoding="utf-8")
    print(f"Wrote {OUT_PATH} for v{version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
