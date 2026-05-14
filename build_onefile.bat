@echo off
REM ============================================
REM  asynk - Build Single-File EXE
REM  Produces one asynk.exe (slower startup,
REM  but easier to share as a single file)
REM ============================================

echo.
echo  =====================================
echo   asynk - Build Single-File EXE
echo  =====================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ and add to PATH.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
) else (
    echo [1/4] Virtual environment exists...
)

call .venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

echo [3/4] Building single-file executable... (this takes 3-8 minutes)
pyinstaller ^
    --onefile ^
    --windowed ^
    --name asynk ^
    --hidden-import scipy.signal ^
    --hidden-import scipy.fft ^
    --hidden-import scipy.fft._pocketfft ^
    --hidden-import numpy ^
    --hidden-import soundfile ^
    --hidden-import lxml ^
    --hidden-import lxml.etree ^
    --hidden-import PySide6.QtWidgets ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --exclude-module matplotlib ^
    --exclude-module tkinter ^
    --exclude-module PIL ^
    --noconfirm ^
    --clean ^
    main.py

if exist "dist\asynk.exe" (
    echo.
    echo [4/4] Build successful!
    echo.
    echo  Output: dist\asynk.exe
    echo.
    echo  This is a single portable file.
    echo  FFmpeg must still be installed on the target machine.
    echo  First launch may take a few seconds to unpack.
    echo.
) else (
    echo.
    echo [ERROR] Build failed. Check output above.
    echo.
)

pause
