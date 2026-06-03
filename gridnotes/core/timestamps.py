"""Parse and format race timestamps for display."""

from __future__ import annotations

from datetime import datetime, timezone

from .timezone_settings import display_zone_info, display_timezone_abbrev

_UTC = timezone.utc


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


def format_last_seen(value) -> str:
    """Format timestamp as MM/DD/YYYY h:mm AM/PM in the user's display timezone."""
    dt = parse_race_timestamp(value)
    if dt is None:
        return "N/A"

    try:
        local = dt.astimezone(display_zone_info())
    except Exception:
        return "N/A"

    hour = local.hour % 12 or 12
    am_pm = "AM" if local.hour < 12 else "PM"
    return f"{local.month:02d}/{local.day:02d}/{local.year} {hour}:{local.minute:02d} {am_pm}"


def format_last_seen_et(value) -> str:
    """Backward-compatible alias for :func:`format_last_seen`."""
    return format_last_seen(value)


__all__ = [
    "display_timezone_abbrev",
    "format_last_seen",
    "format_last_seen_et",
    "parse_race_timestamp",
]
