# PyInstaller spec for GridNotes (Windows primary; macOS bundle optional)

import os
import sys

block_cipher = None

_datas = [("icon.png", ".")]
if os.path.isfile("LICENSE"):
    _datas.append(("LICENSE", "."))
if os.path.isfile("icon.ico"):
    _datas.append(("icon.ico", "."))
if os.path.isfile("icon.icns"):
    _datas.append(("icon.icns", "."))
if os.path.isfile("scripts/windows_taskbar_identity.ps1"):
    _datas.append(("scripts/windows_taskbar_identity.ps1", "scripts"))

try:
    from PyInstaller.utils.hooks import collect_data_files

    _datas += collect_data_files("tzdata")
except Exception:
    pass

_win_icon = None
_win_version = None
if sys.platform == "win32":
    if os.path.isfile("icon.ico"):
        _win_icon = "icon.ico"
    elif os.path.isfile("icon.png"):
        _win_icon = "icon.png"
    if os.path.isfile("scripts/win_version_info.txt"):
        _win_version = "scripts/win_version_info.txt"

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        "gridnotes",
        "gridnotes.app",
        "gridnotes.app.app_icon",
        "gridnotes.app.app_version",
        "gridnotes.app.feature_flags",
        "gridnotes.app.gridnotes_app",
        "gridnotes.core",
        "gridnotes.core.timestamps",
        "gridnotes.core.utils",
        "gridnotes.data",
        "gridnotes.data.data_retention",
        "gridnotes.data.db",
        "gridnotes.data.driver_cleanup",
        "gridnotes.data.driver_models",
        "gridnotes.data.note_tags",
        "gridnotes.data.queries",
        "gridnotes.iracing",
        "gridnotes.iracing.import_worker",
        "gridnotes.iracing.iracing_api_fetch_worker",
        "gridnotes.iracing.iracing_data_api",
        "gridnotes.iracing.iracing_data_api_config",
        "gridnotes.iracing.iracing_import",
        "gridnotes.iracing.iracing_oauth_guide",
        "gridnotes.iracing.iracing_worker",
        "gridnotes.iracing.session_kind",
        "gridnotes.iracing.spotter_telemetry",
        "gridnotes.iracing.grid_walk",
        "gridnotes.ui.grid_walk_view",
        "gridnotes.services.audio_spotter",
        "gridnotes.ui.a11y",
        "pyttsx3",
        "pyttsx3.drivers",
        "pyttsx3.drivers.sapi5",
        "gridnotes.installer",
        "gridnotes.installer.logic",
        "gridnotes.installer.portable_update",
        "gridnotes.installer.frozen_update",
        "gridnotes.installer.installer_update",
        "gridnotes.installer.update_paths",
        "gridnotes.installer.post_update_cli",
        "gridnotes.installer.shortcuts",
        "gridnotes.installer.window",
        "gridnotes.installer.worker",
        "gridnotes.platform",
        "gridnotes.platform.windows.windows_apps",
        "gridnotes.platform.windows.windows_launcher",
        "gridnotes.platform.windows.windows_shell",
        "gridnotes.platform.windows.windows_shell_native",
        "gridnotes.safety",
        "gridnotes.safety.safety_index",
        "gridnotes.services",
        "gridnotes.services.app_update",
        "gridnotes.services.app_update_worker",
        "gridnotes.services.log_config",
        "gridnotes.services.user_feedback",
        "gridnotes.broadcast",
        "gridnotes.broadcast.client",
        "gridnotes.broadcast.controller",
        "gridnotes.broadcast.discovery",
        "gridnotes.broadcast.patches",
        "gridnotes.broadcast.protocol",
        "gridnotes.broadcast.server",
        "gridnotes.broadcast.session_feed",
        "gridnotes.broadcast.snapshot",
        "gridnotes.ui",
        "gridnotes.ui.appearance",
        "gridnotes.ui.broadcast_connect_dialog",
        "gridnotes.ui.broadcast_status_dialog",
        "gridnotes.ui.driver_table",
        "gridnotes.ui.live_session",
        "gridnotes.ui.safety_widgets",
        "gridnotes.ui.settings_tab",
        "gridnotes.ui.theme",
        "gridnotes.ui.theme_tokens",
        "gridnotes.ui.ui_widgets",
        "iracingdataapi",
        "iracingdataapi.client",
        "pydantic",
        "pydantic_core",
        "irsdk",
        "tzdata",
        "zoneinfo",
        "PyQt6.QtWebSockets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tests",
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "cv2",
        "pytest",
        "_pytest",
        "pluggy",
        "unittest",
        "pydoc",
        "doctest",
        "xml",
        "xmlrpc",
        "multiprocessing",
        "concurrent.futures",
        "lib2to3",
        "IPython",
        "notebook",
        "setuptools",
        "distutils",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GridNotes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_win_icon,
    version=_win_version,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GridNotes",
)

if sys.platform == "darwin":
    # macOS .app bundle needs .icns; icon.png is still bundled via datas for the window icon.
    _bundle_icon = "icon.icns" if os.path.isfile("icon.icns") else None
    app = BUNDLE(
        coll,
        name="GridNotes.app",
        icon=_bundle_icon,
        bundle_identifier="com.gridnotes.app",
        info_plist={
            "CFBundleName": "GridNotes",
            "CFBundleDisplayName": "GridNotes",
            "CFBundleVersion": "1.0.21",
            "CFBundleShortVersionString": "1.0.21",
            "NSHighResolutionCapable": True,
        },
    )
