@echo off
setlocal
cd /d %~dp0
if not exist .venv\Scripts\python.exe exit /b 1
if not exist dist\PancakeDesktopToolkit_debug\PancakeDesktopToolkit_debug.exe (
  .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean PancakeDesktopToolkit_debug.spec
  if errorlevel 1 exit /b %errorlevel%
)
dist\PancakeDesktopToolkit_debug\PancakeDesktopToolkit_debug.exe
echo Exit code: %errorlevel%
echo Log: %LOCALAPPDATA%\PancakeDesktopToolkit\logs\startup.log
endlocal
