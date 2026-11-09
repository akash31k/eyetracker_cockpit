@echo off
title Tobii Eye Tracker - ADP Recording & Evaluation GUI
color 0A
echo ===================================================
echo   TOBII EYE TRACKER - RECORDING & EVALUATION GUI
echo ===================================================
echo.

:: Activate your Conda tobii-env environment
echo Activating Tobii Python 3.10 environment...
call "C:\Users\akash\miniconda3\Scripts\activate.bat" tobii-env

:: Run the ADP Recording GUI
echo.
echo Launching Eye Tracker GUI...
cd /d "D:\MASTERS AE\ADP- Eye Tracking\eye-tracker-adp-main (1)\eye-tracker-adp-main"
python eye_tracker_GUI.py

pause
