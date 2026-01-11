@echo off
title Cigarette Counter - Smoke Free Tracker

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ first
    pause
    exit /b 1
)

REM Run the counter
echo Starting Cigarette Counter...
echo.
pythonw cigarette_counter.py

REM Note: Using pythonw to hide console window
REM If you want to see console output for debugging, change to: python cigarette_counter.py
