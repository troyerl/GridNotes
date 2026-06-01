# PyInstaller spec for GridNotes (Windows primary; macOS bundle optional)

import os
import sys

block_cipher = None

_datas = [("icon.png", ".")]
if os.path.isfile("icon.ico"):
    _datas.append(("icon.ico", "."))

try:
    from PyInstaller.utils.hooks import collect_data_files

    _datas += collect_data_files("tzdata")
except Exception:
    pass

_win_icon = None
if sys.platform == "win32":
    if os.path.isfile("icon.ico"):
        _win_icon = "icon.ico"
    elif os.path.isfile("icon.png"):
        _win_icon = "icon.png"

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        "racing_book",
        "racing_book.app",
        "racing_book.app.app_icon",
        "racing_book.app.app_version",
        "racing_book.app.feature_flags",
        "racing_book.app.racebook_app",
        "racing_book.core",
        "racing_book.core.timestamps",
        "racing_book.core.utils",
        "racing_book.data",
        "racing_book.data.data_retention",
        "racing_book.data.db",
        "racing_book.data.driver_cleanup",
        "racing_book.data.driver_models",
        "racing_book.data.queries",
        "racing_book.iracing",
        "racing_book.iracing.import_worker",
        "racing_book.iracing.iracing_api_fetch_worker",
        "racing_book.iracing.iracing_data_api",
        "racing_book.iracing.iracing_data_api_config",
        "racing_book.iracing.iracing_import",
        "racing_book.iracing.iracing_oauth_guide",
        "racing_book.iracing.iracing_worker",
        "racing_book.iracing.session_kind",
        "racing_book.installer",
        "racing_book.installer.logic",
        "racing_book.installer.shortcuts",
        "racing_book.installer.window",
        "racing_book.installer.worker",
        "racing_book.safety",
        "racing_book.safety.safety_index",
        "racing_book.services",
        "racing_book.services.app_update",
        "racing_book.services.app_update_worker",
        "racing_book.services.log_config",
        "racing_book.services.user_feedback",
        "racing_book.ui",
        "racing_book.ui.appearance",
        "racing_book.ui.driver_table",
        "racing_book.ui.live_session",
        "racing_book.ui.safety_widgets",
        "racing_book.ui.settings_tab",
        "racing_book.ui.theme",
        "racing_book.ui.theme_tokens",
        "racing_book.ui.ui_widgets",
        "iracingdataapi",
        "iracingdataapi.client",
        "pydantic",
        "pydantic_core",
        "irsdk",
        "tzdata",
        "zoneinfo",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "cv2",
        "pytest",
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
            "CFBundleVersion": "1.2.3",
            "CFBundleShortVersionString": "1.2.3",
            "NSHighResolutionCapable": True,
        },
    )
