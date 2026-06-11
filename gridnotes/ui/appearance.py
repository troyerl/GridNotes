"""Application appearance (theme) preference."""

from __future__ import annotations

from ..data.db import get_setting, set_setting

THEME_DARK_ID = "dark"
THEME_LIGHT_ID = "light"
THEME_SETTING_KEY = "app_theme"
DEFAULT_THEME_ID = THEME_DARK_ID

THEME_OPTIONS: tuple[tuple[str, str], ...] = (
    (THEME_DARK_ID, "Dark"),
    (THEME_LIGHT_ID, "Light"),
)


def normalize_theme_id(value: str | None) -> str:
    if (value or "").strip().lower() == THEME_LIGHT_ID:
        return THEME_LIGHT_ID
    return THEME_DARK_ID


_active_theme_id: str | None = None


def get_theme_id() -> str:
    return normalize_theme_id(get_setting(THEME_SETTING_KEY, DEFAULT_THEME_ID))


def active_theme_id() -> str:
    """Theme currently applied to the UI (may differ from saved setting while previewing)."""
    if _active_theme_id is not None:
        return _active_theme_id
    return get_theme_id()


def set_active_theme_id(theme_id: str | None = None) -> str:
    """Record the theme id used for stylesheets and theme-aware widgets."""
    global _active_theme_id
    resolved = get_theme_id() if theme_id is None else normalize_theme_id(theme_id)
    _active_theme_id = resolved
    return resolved


def set_theme_id(theme_id: str) -> None:
    normalized = normalize_theme_id(theme_id)
    set_setting(THEME_SETTING_KEY, normalized)
    set_active_theme_id(normalized)
