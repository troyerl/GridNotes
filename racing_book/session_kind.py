"""iRacing session type helpers shared by SDK worker and UI."""

from __future__ import annotations

SESSION_KIND_RACE = "race"
SESSION_KIND_QUALIFY = "qualify"
SESSION_KIND_PRACTICE = "practice"
SESSION_KIND_OTHER = "other"

SESSION_KIND_LABELS = {
    SESSION_KIND_RACE: "Race",
    SESSION_KIND_QUALIFY: "Qualifying",
    SESSION_KIND_PRACTICE: "Practice",
    SESSION_KIND_OTHER: "Session",
}


def normalize_session_kind(raw) -> str | None:
    if isinstance(raw, str):
        text = raw.strip().lower()
        if not text:
            return None
        if "race" in text:
            return SESSION_KIND_RACE
        if "qual" in text:
            return SESSION_KIND_QUALIFY
        if any(token in text for token in ("pract", "test", "warm", "garage")):
            return SESSION_KIND_PRACTICE
        return SESSION_KIND_OTHER

    if isinstance(raw, int):
        if raw in (5, 6):
            return SESSION_KIND_RACE
        if raw in (2, 4):
            return SESSION_KIND_QUALIFY
        if raw in (0, 1, 3):
            return SESSION_KIND_PRACTICE
        return SESSION_KIND_OTHER

    return None


def session_kind_label(kind: str | None) -> str:
    if not kind:
        return "Session"
    return SESSION_KIND_LABELS.get(kind, kind.title())


def is_race_session(kind: str | None) -> bool:
    return kind == SESSION_KIND_RACE


def current_session_kind(ir) -> str:
    """Best-effort session kind from live SDK data."""
    session_num = 0
    try:
        session_num = int(ir["SessionNum"] or 0)
    except Exception:
        session_num = 0

    try:
        info = ir["SessionInfo"]
        if isinstance(info, dict):
            sessions = info.get("Sessions") or []
            if isinstance(sessions, list) and 0 <= session_num < len(sessions):
                entry = sessions[session_num]
                if isinstance(entry, dict):
                    for key in ("SessionType", "SessionTypeName", "SessionName"):
                        kind = normalize_session_kind(entry.get(key))
                        if kind:
                            return kind
    except Exception:
        pass

    try:
        weekend = ir["WeekendInfo"]
        if isinstance(weekend, dict):
            for key in ("SessionTypeName", "SessionType", "SessionName"):
                kind = normalize_session_kind(weekend.get(key))
                if kind:
                    return kind
    except Exception:
        pass

    return SESSION_KIND_OTHER
