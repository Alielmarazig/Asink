@echo off
REM ============================================
REM  asynk Windows Build Script
REM  Run this from the asynk project folder
REM ============================================

echo.
echo  =============================
echo   asynk - Build Windows EXE
echo  =============================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ and add to PATH.
    pause
    exit /b 1
)

REM Create venv if it doesn't exist
if not exist ".venv" (
    echo [1/5] Creating virtual environment...
    python -m venv .venv
) else (
    echo [1/5] Virtual environment exists, skipping...
)

REM Activate venv
echo [2/5] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo [3/5] Installing dependencies...
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

REM Build
echo [4/5] Building executable... (this takes 2-5 minutes)
pyinstaller asynk.spec --noconfirm --clean

REM Check result
if exist "dist\asynk\asynk.exe" (
    echo.
    echo [5/5] Build successful!
    echo.
    echo  Output: dist\asynk\asynk.exe
    echo  Folder: dist\asynk\
    echo.
    echo  To distribute: zip the entire dist\asynk\ folder.
    echo  FFmpeg must be installed on the target machine.
    echo.
) else (
    echo.
    echo [ERROR] Build failed. Check the output above for errors.
    echo.
)

pause
