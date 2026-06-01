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


def get_theme_id() -> str:
    return normalize_theme_id(get_setting(THEME_SETTING_KEY, DEFAULT_THEME_ID))


def set_theme_id(theme_id: str) -> None:
    set_setting(THEME_SETTING_KEY, normalize_theme_id(theme_id))
