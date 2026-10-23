# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PancakeDesktopToolkit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX-compressing Qt6/PySide6 binaries can produce loader errors such as
    # "specified procedure could not be found" on Windows. Keep Qt binaries
    # uncompressed and let the official PyInstaller hooks collect them.
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PancakeDesktopToolkit',
)
