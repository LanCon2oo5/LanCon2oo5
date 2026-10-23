@echo off
setlocal
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo Khong tim thay .venv. Hay tao moi truoc khi build.
  exit /b 1
)
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean PancakeDesktopToolkit.spec
if errorlevel 1 exit /b %errorlevel%
echo Da tao dist\PancakeDesktopToolkit\PancakeDesktopToolkit.exe
endlocal
