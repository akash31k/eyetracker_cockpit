@echo off
title Tobii Eye Spark Pro - Cockpit Control
color 0B
echo ===================================================
echo   TOBII EYE SPARK PRO - COCKPIT GAZE & DOUBLE-BLINK
echo ===================================================
echo.

:: Change to script's directory
cd /d "%~dp0"

:: 1. Activate Python environment (check conda locations or local venv)
echo Activating Tobii Python environment...

if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\miniconda3\Scripts\activate.bat" tobii-env
) else if exist "C:\Users\akash\miniconda3\Scripts\activate.bat" (
    call "C:\Users\akash\miniconda3\Scripts\activate.bat" tobii-env
) else if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\anaconda3\Scripts\activate.bat" tobii-env
) else if exist "%~dp0tobii_env\Scripts\activate.bat" (
    call "%~dp0tobii_env\Scripts\activate.bat"
) else (
    call conda activate tobii-env 2>nul
)

:: 2. Launch the Cockpit HUD in default web browser
echo Opening Cockpit HUD in browser...
start "" "%~dp0cockpit.html"

:: 3. Run the Python bridge
echo.
echo Starting Tobii Eye Tracker Controller...
echo (Keep this window open while using the cockpit)
echo.
python tobii_cockpit_controller.py

pause
