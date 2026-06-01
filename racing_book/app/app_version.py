"""Application version metadata."""

from __future__ import annotations

import re

__version__ = "1.2.21"


def parse_version(value: str) -> tuple[int, ...]:
    """Parse a semver-like string into a comparable integer tuple."""
    parts: list[int] = []
    for segment in re.split(r"[.\-+]", (value or "").strip()):
        if segment.isdigit():
            parts.append(int(segment))
        elif parts:
            break
    return tuple(parts) if parts else (0,)


def is_newer_version(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)
