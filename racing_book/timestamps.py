"""Parse and format race timestamps for display."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache

_UTC = timezone.utc


@lru_cache(maxsize=1)
def _eastern_tz():
    """US Eastern timezone; works in dev and PyInstaller builds with bundled tzdata."""
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("America/New_York")
    except Exception:
        pass

    # PyInstaller: zoneinfo may need explicit TZPATH to bundled tzdata files.
    try:
        import os
        import sys
        from zoneinfo import ZoneInfo

        if getattr(sys, "frozen", False):
            base = getattr(sys, "_MEIPASS", "")
            for subpath in ("tzdata/zoneinfo", "zoneinfo"):
                tz_root = os.path.join(base, subpath)
                if os.path.isdir(tz_root):
                    existing = os.environ.get("TZPATH", "")
                    paths = [p for p in (existing, tz_root) if p]
                    os.environ["TZPATH"] = os.pathsep.join(paths)
                    return ZoneInfo("America/New_York")
    except Exception:
        pass

    # Last resort: fixed EST (no DST). Better than crashing the app.
    return timezone(timedelta(hours=-5))


def parse_race_timestamp(value) -> datetime | None:
    """Parse stored race / last-seen timestamps into UTC-aware datetime."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=_UTC)
        except (OSError, OverflowError, ValueError):
            return None
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    candidates = [text]
    if text.endswith("Z"):
        candidates.append(text[:-1] + "+00:00")
    if " " in text and "T" not in text:
        candidates.append(text.replace(" ", "T", 1))
    if "T" in text and "+" not in text[10:] and not text.endswith("Z"):
        candidates.append(text + "+00:00")

    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_UTC)
            return dt.astimezone(_UTC)
        except ValueError:
            continue
    return None


def format_last_seen_et(value) -> str:
    """Format timestamp as MM/DD/YYYY h:mm AM/PM in US Eastern Time."""
    dt = parse_race_timestamp(value)
    if dt is None:
        return "N/A"

    try:
        et = dt.astimezone(_eastern_tz())
    except Exception:
        return "N/A"

    hour = et.hour % 12 or 12
    am_pm = "AM" if et.hour < 12 else "PM"
    return f"{et.month:02d}/{et.day:02d}/{et.year} {hour}:{et.minute:02d} {am_pm}"
