"""Force PySide6 to resolve its Qt DLLs from the bundled directory first."""
import os
import sys
import ctypes

if getattr(sys, "frozen", False):
    bundled_root = sys._MEIPASS
    bundled_pyside = os.path.join(sys._MEIPASS, "PySide6")
    if os.path.isdir(bundled_pyside):
        os.add_dll_directory(bundled_root)
        os.add_dll_directory(bundled_pyside)
        for name in ("icudt78.dll", "icuuc.dll"):
            path = os.path.join(bundled_root, name)
            if os.path.exists(path): ctypes.WinDLL(path)
        ctypes.windll.kernel32.SetDllDirectoryW(bundled_pyside)
        os.environ["PATH"] = bundled_pyside + os.pathsep + os.environ.get("PATH", "")
        # Load the exact Qt/MSVC chain by absolute path before importing the
        # extension module. This avoids Windows resolving a same-named DLL
        # from the PyInstaller root or another process-global DLL directory.
        for name in ("VCRUNTIME140.dll", "VCRUNTIME140_1.dll", "MSVCP140.dll", "MSVCP140_2.dll", "Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll"):
            path = os.path.join(bundled_pyside, name)
            if os.path.exists(path): ctypes.WinDLL(path)
