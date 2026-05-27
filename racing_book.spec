# PyInstaller spec for GridNotes (Windows primary; macOS bundle optional)

import os
import sys

block_cipher = None

_datas = [("icon.png", ".")]
if os.path.isfile("icon.ico"):
    _datas.append(("icon.ico", "."))

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
        "racing_book.db",
        "racing_book.iracing_worker",
        "irsdk",
        "racing_book.racebook_app",
        "racing_book.theme",
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
            "CFBundleVersion": "1.0.0",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
        },
    )
