# -*- mode: python ; coding: utf-8 -*-
a = Analysis(['app/main.py'], pathex=['.'], binaries=[], datas=[], hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=['runtime_hooks/qt_bundle_path.py'], excludes=[], noarchive=False, optimize=0)
a.binaries = [entry for entry in a.binaries if entry[0] not in {'ucrtbase.dll', 'VCRUNTIME140.dll', 'VCRUNTIME140_1.dll', 'MSVCP140.dll', 'MSVCP140_1.dll', 'MSVCP140_2.dll'}]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PancakeDesktopToolkit_debug', debug=True, bootloader_ignore_signals=False, strip=False, upx=False, console=True, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PancakeDesktopToolkit_debug')
