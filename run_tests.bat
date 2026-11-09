@echo off
chcp 65001 >nul
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

python test_filter_targets.py
pause
