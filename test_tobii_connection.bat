@echo off
title Tobii Connection Test
color 0B
echo.
echo Running Tobii device connection test...
echo.
cd /d "%~dp0"

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

python test_tobii_connection.py
pause
