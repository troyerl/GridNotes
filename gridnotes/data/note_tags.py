"""User-defined quick note tags (appended from Scouting notes chips)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .db import DB_NAME, get_setting, set_setting

SETTING_KEY = "quick_note_tags"

MAX_CHIP_LABEL_LENGTH = 20
MAX_DESCRIPTION_LENGTH = 120
_MAX_TAGS = 24


@dataclass(frozen=True)
class NoteTag:
    """Short chip label plus optional longer note text appended on click."""

    label: str
    description: str = ""

    def append_text(self) -> str:
        """Text added to scouting notes when the chip is clicked."""
        desc = _normalize(self.description)
        label = _normalize(self.label)
        return desc or label


DEFAULT_NOTE_TAGS: tuple[NoteTag, ...] = (
    NoteTag("Clean", "Clean racer"),
    NoteTag("Divebombs", "Divebombs / late sends"),
    NoteTag("Blocks", "Blocks aggressively"),
    NoteTag("Restarts", "Good on restarts"),
    NoteTag("Unpredictable", "Unpredictable lines / braking"),
)


def _normalize(text: str) -> str:
    return " ".join((text or "").split())


def _clip(text: str, limit: int) -> str:
    return _normalize(text)[:limit]


def _tag_from_dict(item: dict) -> NoteTag | None:
    label = _clip(str(item.get("label", "")), MAX_CHIP_LABEL_LENGTH)
    if not label:
        return None
    description = _clip(str(item.get("description", "")), MAX_DESCRIPTION_LENGTH)
    return NoteTag(label=label, description=description)


def _tag_from_legacy_string(text: str) -> NoteTag | None:
    normalized = _clip(text, MAX_DESCRIPTION_LENGTH)
    if not normalized:
        return None
    if len(normalized) <= MAX_CHIP_LABEL_LENGTH:
        return NoteTag(label=normalized, description="")
    words = normalized.split()
    label = _clip(words[0], MAX_CHIP_LABEL_LENGTH)
    return NoteTag(label=label, description=normalized)


def _default_tags() -> list[NoteTag]:
    return list(DEFAULT_NOTE_TAGS)


def _parse_setting(raw: str | None) -> list[NoteTag]:
    if raw is None:
        return _default_tags()

    if not raw.strip():
        return _default_tags()

    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return _default_tags()

    if not isinstance(payload, list):
        return _default_tags()

    if not payload:
        return []

    tags: list[NoteTag] = []
    seen: set[str] = set()
    for item in payload:
        tag: NoteTag | None
        if isinstance(item, str):
            tag = _tag_from_legacy_string(item)
        elif isinstance(item, dict):
            tag = _tag_from_dict(item)
        else:
            continue
        if tag is None or tag.label in seen:
            continue
        seen.add(tag.label)
        tags.append(tag)
        if len(tags) >= _MAX_TAGS:
            break
    return tags


def note_tags_setting_exists(db_name: str | None = None) -> bool:
    name = db_name if db_name is not None else DB_NAME
    return get_setting(SETTING_KEY, db_name=name) is not None


def ensure_default_note_tags(db_name: str | None = None) -> None:
    """Seed default quick note tags on first install (does not overwrite user edits)."""
    name = db_name if db_name is not None else DB_NAME
    if note_tags_setting_exists(name):
        return
    save_note_tags(_default_tags(), db_name=name)


def load_note_tags(db_name: str | None = None) -> list[NoteTag]:
    name = db_name if db_name is not None else DB_NAME
    ensure_default_note_tags(name)
    return _parse_setting(get_setting(SETTING_KEY, db_name=name))


def save_note_tags(tags: list[NoteTag], db_name: str | None = None) -> None:
    payload: list[dict[str, str]] = []
    seen: set[str] = set()
    for tag in tags:
        label = _clip(tag.label, MAX_CHIP_LABEL_LENGTH)
        if not label or label in seen:
            continue
        seen.add(label)
        description = _clip(tag.description, MAX_DESCRIPTION_LENGTH)
        entry: dict[str, str] = {"label": label}
        if description:
            entry["description"] = description
        payload.append(entry)
        if len(payload) >= _MAX_TAGS:
            break
    set_setting(
        SETTING_KEY,
        json.dumps(payload, ensure_ascii=False),
        db_name=db_name if db_name is not None else DB_NAME,
    )


def chip_label(label: str) -> str:
    """Button label for a quick note tag chip."""
    text = _clip(label, MAX_CHIP_LABEL_LENGTH)
    if not text:
        return "+"
    return text if text.startswith("+") else f"+ {text}"
