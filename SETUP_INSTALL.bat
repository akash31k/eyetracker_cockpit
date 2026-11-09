@echo off
setlocal EnableDelayedExpansion
title Tobii Eye Spark Pro - SETUP INSTALLER
color 0B

echo.
echo  ████████╗ ██████╗ ██████╗ ██╗██╗    ███████╗██╗   ██╗███████╗
echo  ╚══██╔══╝██╔═══██╗██╔══██╗██║██║    ██╔════╝╚██╗ ██╔╝██╔════╝
echo     ██║   ██║   ██║██████╔╝██║██║    █████╗   ╚████╔╝ █████╗
echo     ██║   ██║   ██║██╔══██╗██║██║    ██╔══╝    ╚██╔╝  ██╔══╝
echo     ██║   ╚██████╔╝██████╔╝██║██║    ███████╗   ██║   ███████╗
echo     ╚═╝    ╚═════╝ ╚═════╝ ╚═╝╚═╝    ╚══════╝   ╚═╝   ╚══════╝
echo.
echo  COCKPIT EYE GAZE CONTROL — SETUP SCRIPT
echo  ════════════════════════════════════════
echo.
echo  This script will:
echo    1. Check if Python 3.10 is installed
echo    2. Install all required packages
echo    3. Verify Tobii SDK works
echo    4. Create a virtual environment for your project
echo.
pause

:: ─────────────────────────────────────────────────────────────
:: STEP 1: Check for Python 3.10
:: ─────────────────────────────────────────────────────────────
echo.
echo [STEP 1] Checking for Python 3.10...
echo.

:: Try to find python3.10 specifically
python3.10 --version >nul 2>&1
if %errorlevel% == 0 (
    echo   [OK] Python 3.10 found!
    set PYTHON_CMD=python3.10
    goto :PYTHON_OK
)

:: Try py launcher for 3.10
py -3.10 --version >nul 2>&1
if %errorlevel% == 0 (
    echo   [OK] Python 3.10 found via py launcher!
    set PYTHON_CMD=py -3.10
    goto :PYTHON_OK
)

:: Check the default python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo   Current Python version: %PYVER%

if "%PYVER:~0,4%"=="3.10" (
    echo   [OK] Python 3.10 is the default Python!
    set PYTHON_CMD=python
    goto :PYTHON_OK
)

:: Python 3.10 not found
echo.
echo   [ERROR] Python 3.10 is NOT installed!
echo.
echo   The Tobii Research SDK REQUIRES Python 3.10 exactly.
echo   (It will NOT work with Python 3.9, 3.11, 3.12 etc.)
echo.
echo   Please:
echo     1. Go to: https://www.python.org/downloads/release/python-31011/
echo     2. Download "Windows installer (64-bit)"
echo     3. Run the installer
echo     4. CHECK the box "Add Python 3.10 to PATH"
echo     5. Re-run this setup script
echo.
echo   Opening download page in browser...
start https://www.python.org/downloads/release/python-31011/
echo.
pause
exit /b 1

:PYTHON_OK

:: ─────────────────────────────────────────────────────────────
:: STEP 2: Create virtual environment
:: ─────────────────────────────────────────────────────────────
echo.
echo [STEP 2] Creating Python virtual environment...
echo   (This keeps project packages separate from your system)
echo.

if exist "tobii_env" (
    echo   [INFO] Virtual environment already exists, skipping creation.
) else (
    %PYTHON_CMD% -m venv tobii_env
    if %errorlevel% neq 0 (
        echo   [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo   [OK] Virtual environment created: tobii_env\
)

:: ─────────────────────────────────────────────────────────────
:: STEP 3: Install packages
:: ─────────────────────────────────────────────────────────────
echo.
echo [STEP 3] Installing required packages...
echo   (This may take 1-3 minutes, please wait)
echo.

call tobii_env\Scripts\activate.bat

pip install --upgrade pip --quiet
echo   Installing tobii_research (Tobii Pro SDK)...
pip install tobii_research --quiet
if %errorlevel% neq 0 (
    echo   [ERROR] Failed to install tobii_research!
    echo   Make sure you have internet connection.
    pause
    exit /b 1
)
echo   [OK] tobii_research installed

echo   Installing websockets...
pip install websockets --quiet
echo   [OK] websockets installed

echo   Installing numpy...
pip install numpy --quiet
echo   [OK] numpy installed

:: ─────────────────────────────────────────────────────────────
:: STEP 4: Update run script to use virtual environment
:: ─────────────────────────────────────────────────────────────
echo.
echo [STEP 4] Updating launcher to use virtual environment...

(
echo @echo off
echo title Tobii Eye Spark Pro - Cockpit Controller
echo color 0B
echo.
echo echo Starting Tobii Cockpit Eye Control System...
echo echo.
echo.
echo :: Activate the Python virtual environment
echo call "%~dp0tobii_env\Scripts\activate.bat"
echo.
echo :: Open the cockpit HUD in default browser
echo echo Opening Cockpit HUD in browser...
echo start "" "%~dp0cockpit.html"
echo.
echo :: Start the Python eye tracker bridge
echo echo Starting Eye Tracker Bridge ^(keep this window open^)...
echo echo.
echo python "%~dp0tobii_cockpit_controller.py"
echo.
echo pause
) > run_cockpit_control.bat

echo   [OK] Launcher updated

:: ─────────────────────────────────────────────────────────────
:: DONE
:: ─────────────────────────────────────────────────────────────
echo.
echo ════════════════════════════════════════════════════════════
echo   SETUP COMPLETE!
echo.
echo   NEXT STEPS:
echo.
echo   1. Plug in your Tobii Pro Spark via USB
echo   2. Open "Tobii Pro Eye Tracker Manager" and calibrate
echo   3. Double-click "test_tobii_connection.bat" to verify
echo   4. Double-click "run_cockpit_control.bat" to start flying!
echo ════════════════════════════════════════════════════════════
echo.
pause
