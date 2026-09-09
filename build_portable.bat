@echo off
title Build Telegram Video Downloader Portable
cd /d "%~dp0"

echo ==========================================================
echo    Building Standalone Portable Windows Application
echo ==========================================================
echo.

python build_portable.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build encountered an error.
    pause
    exit /b %errorlevel%
)

echo.
echo Build complete! Check the dist\ folder.
pause
