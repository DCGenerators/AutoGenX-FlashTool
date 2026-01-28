@echo off
setlocal
cd /d "%~dp0"

echo ==============================
echo  AutoGen X USB Flash Tool
echo ==============================
echo.

py -3 autogen_flash.py
if errorlevel 1 (
  echo.
  echo ❌ Flash failed. Copy/paste this window to Nick.
  pause
  exit /b 1
)

echo.
echo ✅ Flash complete.
pause
