# PyInstaller spec for Racing Book (Windows primary; macOS bundle optional)

import os
import sys

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("icon.png", ".")],
    hiddenimports=[
        "racing_book",
        "racing_book.db",
        "racing_book.iracing_worker",
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
    name="Racing Book",
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
    icon="icon.png" if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Racing Book",
)

if sys.platform == "darwin":
    # macOS .app bundle needs .icns; icon.png is still bundled via datas for the window icon.
    _bundle_icon = "icon.icns" if os.path.isfile("icon.icns") else None
    app = BUNDLE(
        coll,
        name="Racing Book.app",
        icon=_bundle_icon,
        bundle_identifier="com.racingbook.app",
        info_plist={
            "CFBundleName": "Racing Book",
            "CFBundleDisplayName": "Racing Book",
            "CFBundleVersion": "1.0.0",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
        },
    )
