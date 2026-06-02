# Apply AppUserModelID + relaunch metadata to a .lnk or main window (GridNotes taskbar name/icon).
# Called from GridNotes via environment variables (avoids broken -Argument quoting).
param(
    [ValidateSet("Window", "Shortcut")]
    [string]$Mode = "Window"
)

$ErrorActionPreference = "Stop"

$AppId = if ($env:GN_APP_ID) { $env:GN_APP_ID } else { "GridNotes.GridNotes.1" }
$DisplayName = if ($env:GN_DISPLAY_NAME) { $env:GN_DISPLAY_NAME } else { "GridNotes" }
$RelaunchCommand = $env:GN_RELAUNCH_CMD
$IconPath = $env:GN_ICON_PATH
$ShortcutPath = $env:GN_SHORTCUT_PATH
$Hwnd = [long]($env:GN_HWND)

if (-not $RelaunchCommand) {
    Write-Error "GN_RELAUNCH_CMD is required"
    exit 2
}

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

if ($Mode -eq "Shortcut") {
    if (-not $ShortcutPath) { Write-Error "GN_SHORTCUT_PATH required"; exit 3 }
    [GridNotesShellProps]::ApplyShortcut(
        $ShortcutPath, $AppId, $iconResource, $RelaunchCommand, $DisplayName
    )
} else {
    if ($Hwnd -le 0) { Write-Error "GN_HWND required"; exit 4 }
    [GridNotesShellProps]::ApplyWindow(
        $Hwnd, $AppId, $iconResource, $RelaunchCommand, $DisplayName
    )
}

exit 0
