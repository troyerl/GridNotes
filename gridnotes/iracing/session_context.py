"""Live session context from iRacing SDK (track, laps, category) for scouting UI."""

from __future__ import annotations

from .session_kind import session_kind_label


def _format_category(raw) -> str:
    if raw is None:
        return ""
    text = str(raw).strip().replace("_", " ")
    if not text:
        return ""
    mapping = {
        "oval": "Oval",
        "road": "Road",
        "dirt road": "Dirt road",
        "dirtroad": "Dirt road",
        "dirt oval": "Dirt oval",
        "dirtoval": "Dirt oval",
    }
    key = text.lower()
    return mapping.get(key, text.title())


def parse_session_context(ir) -> dict[str, str]:
    """Best-effort track/laps/category from WeekendInfo and SessionInfo."""
    out: dict[str, str] = {}
    session_num = 0
    try:
        session_num = int(ir["SessionNum"] or 0)
    except Exception:
        session_num = 0

    try:
        weekend = ir["WeekendInfo"]
        if isinstance(weekend, dict):
            track = weekend.get("TrackDisplayName") or weekend.get("TrackDisplayShortName")
            if track:
                out["track"] = str(track).strip()
            for key in ("Category", "TrackCategory", "TrackType"):
                cat = _format_category(weekend.get(key))
                if cat:
                    out["category"] = cat
                    break
    except Exception:
        pass

    try:
        info = ir["SessionInfo"]
        if isinstance(info, dict):
            sessions = info.get("Sessions") or []
            if isinstance(sessions, list) and 0 <= session_num < len(sessions):
                entry = sessions[session_num]
                if isinstance(entry, dict):
                    laps = entry.get("SessionLaps")
                    if laps is not None:
                        try:
                            laps_i = int(laps)
                            if laps_i > 0:
                                out["laps"] = str(laps_i)
                        except (TypeError, ValueError):
                            pass
                    if "laps" not in out:
                        time_raw = entry.get("SessionTime")
                        if time_raw is not None:
                            try:
                                minutes = int(float(time_raw))
                                if minutes > 0:
                                    out["timed_minutes"] = str(minutes)
                            except (TypeError, ValueError):
                                pass
    except Exception:
        pass

    return out


def format_session_context_banner(
    session_kind: str | None,
    context: dict[str, str] | None,
) -> str:
    """Single context line, e.g. ``Race · 25 laps · Daytona · Oval``."""
    parts: list[str] = [session_kind_label(session_kind)]
    ctx = context or {}

    laps = ctx.get("laps")
    if laps:
        parts.append(f"{laps} laps")
    elif ctx.get("timed_minutes"):
        parts.append(f"{ctx['timed_minutes']} min")

    track = ctx.get("track")
    if track:
        parts.append(track)

    category = ctx.get("category")
    if category:
        parts.append(category)

    return " · ".join(parts)
