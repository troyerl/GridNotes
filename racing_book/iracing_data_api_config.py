"""Settings keys and helpers for iRacing Data API auto-import."""

from __future__ import annotations

from .db import get_setting, set_setting
from .feature_flags import iracing_data_api_auto_import_enabled

SETTING_ENABLED = "iracing_api_auto_fetch"
SETTING_ACCESS_TOKEN = "iracing_api_access_token"

# Removed with legacy login — cleared on save so old DB rows are not reused
_LEGACY_SETTING_KEYS = (
    "iracing_api_auth_mode",
    "iracing_api_username",
    "iracing_api_password",
)


def is_auto_fetch_enabled() -> bool:
    if not iracing_data_api_auto_import_enabled():
        return False
    return get_setting(SETTING_ENABLED, "0") == "1"


def get_access_token() -> str:
    return (get_setting(SETTING_ACCESS_TOKEN, "") or "").strip()


def clear_legacy_api_settings() -> None:
    """Remove retired username/password settings from the local database."""
    for key in _LEGACY_SETTING_KEYS:
        set_setting(key, None)


def save_api_settings(*, enabled: bool, access_token: str) -> None:
    set_setting(SETTING_ENABLED, "1" if enabled else "0")
    set_setting(SETTING_ACCESS_TOKEN, access_token.strip() or None)
    clear_legacy_api_settings()
