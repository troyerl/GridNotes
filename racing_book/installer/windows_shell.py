"""Windows shell properties for taskbar icons and pinning."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _subprocess_hide_window_kwargs() -> dict:
    """Avoid flashing console windows when spawning PowerShell on Windows."""
    if sys.platform != "win32":
        return {}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return {"creationflags": flags} if flags else {}


_PS_APPLY = r"""
param(
  [string]$ShortcutPath,
  [long]$Hwnd,
  [string]$AppId = "GridNotes.GridNotes.1",
  [string]$IconPath,
  [string]$RelaunchCommand,
  [string]$DisplayName = "GridNotes"
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
    static readonly PROPERTYKEY PKEY_AppUserModel_RelaunchCommand = new PROPERTYKEY {
        fmtid = new Guid("9F4C2855-9F79-4F39-A8D0-E1D42DE1D5F3"), pid = 2
    };
    static readonly PROPERTYKEY PKEY_AppUserModel_RelaunchDisplayNameResource = new PROPERTYKEY {
        fmtid = new Guid("9F4C2855-9F79-4F39-A8D0-E1D42DE1D5F3"), pid = 4
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

  public static void Apply(
        IPropertyStore store,
        string appId,
        string iconResource,
        string relaunchCommand,
        string displayName
    ) {
        // Relaunch metadata must be set before AppUserModelID (taskbar reads ID last).
        if (!string.IsNullOrWhiteSpace(iconResource)) {
            SetString(store, PKEY_AppUserModel_RelaunchIconResource, iconResource);
        }
        if (!string.IsNullOrWhiteSpace(relaunchCommand)) {
            SetString(store, PKEY_AppUserModel_RelaunchCommand, relaunchCommand);
            SetString(
                store,
                PKEY_AppUserModel_RelaunchDisplayNameResource,
                string.IsNullOrWhiteSpace(displayName) ? "GridNotes" : displayName
            );
        }
        SetString(store, PKEY_AppUserModel_ID, appId);
        store.Commit();
    }

    public static void ApplyShortcut(
        string shortcutPath,
        string appId,
        string iconResource,
        string relaunchCommand,
        string displayName
    ) {
        IPropertyStore store;
        Guid iid = IID_PropertyStore;
        int hr = SHGetPropertyStoreFromParsingName(shortcutPath, IntPtr.Zero, 2, ref iid, out store);
        if (hr != 0) throw new System.ComponentModel.Win32Exception(hr);
        try { Apply(store, appId, iconResource, relaunchCommand, displayName); }
        finally { Marshal.ReleaseComObject(store); }
    }

    public static void ApplyWindow(
        long hwnd,
        string appId,
        string iconResource,
        string relaunchCommand,
        string displayName
    ) {
        IPropertyStore store;
        Guid iid = IID_PropertyStore;
        int hr = SHGetPropertyStoreForWindow(new IntPtr(hwnd), ref iid, out store);
        if (hr != 0) throw new System.ComponentModel.Win32Exception(hr);
        try { Apply(store, appId, iconResource, relaunchCommand, displayName); }
        finally { Marshal.ReleaseComObject(store); }
    }
}
"@

$iconResource = ""
if ($IconPath -and (Test-Path -LiteralPath $IconPath)) {
  $iconResource = "$IconPath,0"
}

if ($ShortcutPath) {
  [GridNotesShellProps]::ApplyShortcut(
    $ShortcutPath, $AppId, $iconResource, $RelaunchCommand, $DisplayName
  )
} elseif ($Hwnd -gt 0) {
  [GridNotesShellProps]::ApplyWindow(
    $Hwnd, $AppId, $iconResource, $RelaunchCommand, $DisplayName
  )
}
"""


def build_relaunch_command(install_root: Path) -> str | None:
    """Command line Windows uses when pinning the running app to the taskbar."""
    from .logic import (
        VENV_DIR_NAME,
        gridnotes_start_script_path,
        venv_pythonw,
        windows_launcher_arguments,
        windows_launcher_exe_path,
    )

    install_root = install_root.resolve()
    launcher = windows_launcher_exe_path(install_root)
    args = windows_launcher_arguments(install_root)
    if launcher.is_file() and args:
        return f'"{launcher.resolve()}" {args}'

    venv_dir = install_root / VENV_DIR_NAME
    pyw = venv_pythonw(venv_dir)
    starter = gridnotes_start_script_path(install_root)
    if not pyw.is_file() or not starter.is_file():
        return None
    return f'"{pyw.resolve()}" "{starter.resolve()}"'


def _run_shell_property_script(
    *,
    app_id: str,
    icon: Path | None,
    shortcut_path: Path | None = None,
    hwnd: int | None = None,
    relaunch_command: str | None = None,
    display_name: str = "GridNotes",
) -> bool:
    if sys.platform != "win32":
        return False

    import tempfile

    # -File passes -AppId / -ShortcutPath to the script. Using -Command with a
    # multi-line script leaves those flags on powershell.exe itself, which triggers
    # an interactive prompt for the mandatory $AppId parameter during install.
    script_file: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".ps1",
            delete=False,
            encoding="utf-8",
        ) as handle:
            handle.write(_PS_APPLY)
            script_file = Path(handle.name)

        args = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_file),
            "-AppId",
            app_id,
        ]
        if shortcut_path is not None:
            args.extend(["-ShortcutPath", str(shortcut_path.resolve())])
        if hwnd is not None and hwnd > 0:
            args.extend(["-Hwnd", str(hwnd)])
        icon_file = str(icon.resolve()) if icon is not None and icon.is_file() else ""
        if icon_file:
            args.extend(["-IconPath", icon_file])
        if relaunch_command:
            args.extend(["-RelaunchCommand", relaunch_command])
        args.extend(["-DisplayName", display_name])

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30,
            **_subprocess_hide_window_kwargs(),
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("Could not apply Windows shell properties: %s", exc)
        return False
    finally:
        if script_file is not None:
            try:
                script_file.unlink(missing_ok=True)
            except OSError:
                pass

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        logger.warning(
            "Windows shell property script failed (%s): %s",
            result.returncode,
            detail,
        )
        return False
    return True


def apply_shortcut_taskbar_identity(
    shortcut_path: Path,
    icon: Path | None,
    *,
    relaunch_command: str | None = None,
) -> bool:
    """Set AppUserModelID (and icon) on a .lnk so taskbar pins keep the GridNotes icon."""
    from ..app.app_icon import APP_USER_MODEL_ID

    return _run_shell_property_script(
        app_id=APP_USER_MODEL_ID,
        icon=icon,
        shortcut_path=shortcut_path,
        relaunch_command=relaunch_command,
    )


def apply_window_taskbar_identity(
    widget,
    icon: Path | None,
    *,
    relaunch_command: str | None = None,
) -> bool:
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
        relaunch_command=relaunch_command,
    )
