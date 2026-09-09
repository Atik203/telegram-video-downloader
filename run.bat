@echo off
title Telegram Video Downloader Pro
cd /d "%~dp0"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ==========================================================
    echo [ERROR] Python is not installed or not in your PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    echo Be sure to check "Add Python to PATH" during setup.
    echo ==========================================================
    echo.
    pause
    exit /b 1
)

:: Launch Telegram Video Downloader GUI
python main.py %*

if %errorlevel% neq 0 (
    echo.
    echo [Notice] Program closed.
    pause
)

