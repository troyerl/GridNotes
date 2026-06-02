"""Register GridNotes AppUserModelID so the taskbar shows the correct name."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def register_app_user_model_id(
    app_id: str,
    display_name: str,
    *,
    icon_path: Path | None = None,
) -> bool:
    """
    Write HKCU\\Software\\Classes\\AppUserModelId\\{app_id} so Windows can show
  GridNotes instead of Python in the taskbar jump list / pin UI.
    """
    if sys.platform != "win32":
        return False
    try:
        import winreg
    except ImportError:
        return False

    key_path = rf"Software\Classes\AppUserModelId\{app_id}"
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, display_name)
            if icon_path is not None and icon_path.is_file():
                winreg.SetValueEx(
                    key,
                    "IconUri",
                    0,
                    winreg.REG_SZ,
                    str(icon_path.resolve()),
                )
        logger.info("Registered AppUserModelID %s as %s", app_id, display_name)
        return True
    except OSError as exc:
        logger.warning("Could not register AppUserModelID in registry: %s", exc)
        return False
