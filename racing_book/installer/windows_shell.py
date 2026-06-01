"""Windows shell properties for taskbar icons and pinning."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_PS_APPLY = r"""
param(
  [string]$ShortcutPath,
  [long]$Hwnd,
  [Parameter(Mandatory=$true)][string]$AppId,
  [string]$IconPath
)

$ErrorActionPreference = "Stop"

Add-Type -Language CSharp -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential, Pack=4)]
public struct PROPERTYKEY {
    public Guid fmtid;
    public uint pid;
}

[StructLayout(LayoutKind.Explicit, Pack=8, Size=16)]
public struct PROPVARIANT {
    [FieldOffset(0)] public ushort vt;
    [FieldOffset(8)] public IntPtr ptr;
}

[ComImport, Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPropertyStore {
    void GetCount(out uint cProps);
    void GetAt(uint iProp, out PROPERTYKEY pkey);
    void GetValue(ref PROPERTYKEY key, out PROPVARIANT pv);
    void SetValue(ref PROPERTYKEY key, ref PROPVARIANT pv);
    void Commit();
}

public static class GridNotesShellProps {
    static readonly Guid IID_PropertyStore = new Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99");
    static readonly PROPERTYKEY PKEY_AppUserModel_RelaunchIconResource = new PROPERTYKEY {
        fmtid = new Guid("9F4C2855-9F79-4F39-A8D0-E1D42DE1D5F3"), pid = 3
    };
    static readonly PROPERTYKEY PKEY_AppUserModel_ID = new PROPERTYKEY {
        fmtid = new Guid("9F4C2855-9F79-4F39-A8D0-E1D42DE1D5F3"), pid = 5
    };

    [DllImport("propsys.dll", CharSet = CharSet.Unicode)]
    static extern int SHGetPropertyStoreFromParsingName(
        string pszPath, IntPtr pbc, int flags, ref Guid riid, out IPropertyStore store);

    [DllImport("shell32.dll")]
    static extern int SHGetPropertyStoreForWindow(
        IntPtr hwnd, ref Guid riid, out IPropertyStore store);

    [DllImport("ole32.dll")]
    static extern int PropVariantClear(ref PROPVARIANT pv);

    static PROPVARIANT StringProp(string value) {
        var pv = new PROPVARIANT();
        pv.vt = 31;
        pv.ptr = Marshal.StringToCoTaskMemUni(value);
        return pv;
    }

    static void SetString(IPropertyStore store, PROPERTYKEY key, string value) {
        var pv = StringProp(value);
        store.SetValue(ref key, ref pv);
        PropVariantClear(ref pv);
    }

  public static void Apply(IPropertyStore store, string appId, string iconResource) {
        if (!string.IsNullOrWhiteSpace(iconResource)) {
            SetString(store, PKEY_AppUserModel_RelaunchIconResource, iconResource);
        }
        SetString(store, PKEY_AppUserModel_ID, appId);
        store.Commit();
    }

    public static void ApplyShortcut(string shortcutPath, string appId, string iconResource) {
        IPropertyStore store;
        Guid iid = IID_PropertyStore;
        int hr = SHGetPropertyStoreFromParsingName(shortcutPath, IntPtr.Zero, 2, ref iid, out store);
        if (hr != 0) throw new System.ComponentModel.Win32Exception(hr);
        try { Apply(store, appId, iconResource); }
        finally { Marshal.ReleaseComObject(store); }
    }

    public static void ApplyWindow(long hwnd, string appId, string iconResource) {
        IPropertyStore store;
        Guid iid = IID_PropertyStore;
        int hr = SHGetPropertyStoreForWindow(new IntPtr(hwnd), ref iid, out store);
        if (hr != 0) throw new System.ComponentModel.Win32Exception(hr);
        try { Apply(store, appId, iconResource); }
        finally { Marshal.ReleaseComObject(store); }
    }
}
"@

$iconResource = ""
if ($IconPath -and (Test-Path -LiteralPath $IconPath)) {
  $iconResource = "$IconPath,0"
}

if ($ShortcutPath) {
  [GridNotesShellProps]::ApplyShortcut($ShortcutPath, $AppId, $iconResource)
} elseif ($Hwnd -gt 0) {
  [GridNotesShellProps]::ApplyWindow($Hwnd, $AppId, $iconResource)
}
"""


def _icon_resource(icon: Path | None) -> str:
    if icon is None or not icon.is_file():
        return ""
    return f"{icon.resolve()},0"


def _run_shell_property_script(
    *,
    app_id: str,
    icon: Path | None,
    shortcut_path: Path | None = None,
    hwnd: int | None = None,
) -> bool:
    if sys.platform != "win32":
        return False

    args = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        _PS_APPLY,
        "-AppId",
        app_id,
    ]
    if shortcut_path is not None:
        args.extend(["-ShortcutPath", str(shortcut_path.resolve())])
    if hwnd is not None and hwnd > 0:
        args.extend(["-Hwnd", str(hwnd)])
    icon_res = _icon_resource(icon)
    if icon_res:
        icon_file = str(icon.resolve()) if icon is not None else ""
        if icon_file:
            args.extend(["-IconPath", icon_file])

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("Could not apply Windows shell properties: %s", exc)
        return False

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        logger.warning(
            "Windows shell property script failed (%s): %s",
            result.returncode,
            detail,
        )
        return False
    return True


def apply_shortcut_taskbar_identity(shortcut_path: Path, icon: Path | None) -> bool:
    """Set AppUserModelID (and icon) on a .lnk so taskbar pins keep the GridNotes icon."""
    from ..app.app_icon import APP_USER_MODEL_ID

    return _run_shell_property_script(
        app_id=APP_USER_MODEL_ID,
        icon=icon,
        shortcut_path=shortcut_path,
    )


def apply_window_taskbar_identity(widget, icon: Path | None) -> bool:
    """Associate the main window with the same AppUserModelID as our shortcuts."""
    from ..app.app_icon import APP_USER_MODEL_ID, set_windows_app_user_model_id

    set_windows_app_user_model_id()
    if sys.platform != "win32":
        return False
    try:
        hwnd = int(widget.winId())
    except (AttributeError, TypeError, ValueError):
        return False
    if hwnd <= 0:
        return False
    return _run_shell_property_script(
        app_id=APP_USER_MODEL_ID,
        icon=icon,
        hwnd=hwnd,
    )
