"""Compile-time feature flags — change here to enable in-development features."""

from __future__ import annotations

# iRacing Data API auto-import (OAuth token + post-race fetch). Off while iRacing has
# paused new OAuth client registrations.
ENABLE_IRACING_DATA_API_AUTO_IMPORT = False


def iracing_data_api_auto_import_enabled() -> bool:
    return ENABLE_IRACING_DATA_API_AUTO_IMPORT
