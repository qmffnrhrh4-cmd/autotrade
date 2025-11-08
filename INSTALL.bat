@echo off
echo ================================================================
echo  AutoTrade 32-bit Environment Setup
echo ================================================================
echo.

REM Initialize Conda (try common paths)
set "CONDA_EXE="
if exist "%USERPROFILE%\Anaconda3\Scripts\conda.exe" set "CONDA_EXE=%USERPROFILE%\Anaconda3\Scripts\conda.exe"
if exist "%USERPROFILE%\anaconda3\Scripts\conda.exe" set "CONDA_EXE=%USERPROFILE%\anaconda3\Scripts\conda.exe"
if exist "C:\ProgramData\Anaconda3\Scripts\conda.exe" set "CONDA_EXE=C:\ProgramData\Anaconda3\Scripts\conda.exe"
if exist "%LOCALAPPDATA%\Continuum\anaconda3\Scripts\conda.exe" set "CONDA_EXE=%LOCALAPPDATA%\Continuum\anaconda3\Scripts\conda.exe"

REM Step 1: Check Conda
echo [Step 1/5] Checking Anaconda...
if "%CONDA_EXE%"=="" (
    where conda >nul 2>&1
    if errorlevel 1 (
        echo.
        echo ERROR: Anaconda not found in common locations!
        echo.
        echo Please use Anaconda Prompt instead:
        echo   1. Press Windows key
        echo   2. Type "Anaconda Prompt"
        echo   3. Click it
        echo   4. Run: cd C:\Users\USER\Desktop\autotrade
        echo   5. Run: INSTALL_ANACONDA_PROMPT.bat
        echo.
        echo Or install Anaconda from:
        echo   https://www.anaconda.com/download
        pause
        exit /b 1
    )
    echo OK: conda found in PATH
) else (
    echo OK: conda found at: %CONDA_EXE%
    REM Initialize conda for this session
    call "%CONDA_EXE%" init cmd.exe >nul 2>&1
)
echo.

REM Step 2: Create 32-bit environment
echo [Step 2/5] Creating 32-bit Python environment...
echo This will create: autotrade_32
echo.
set CONDA_FORCE_32BIT=1
conda create -n autotrade_32 python=3.11 -y
echo.

REM Step 3: Activate environment
echo [Step 3/5] Activating environment...
call conda activate autotrade_32
if errorlevel 1 (
    echo ERROR: Failed to activate environment
    pause
    exit /b 1
)
echo.

REM Step 4: Verify 32-bit
echo [Step 4/5] Verifying 32-bit Python...
python -c "import struct; print('Python:', struct.calcsize('P')*8, 'bit')"
echo.

REM Step 5: Install packages
echo [Step 5/5] Installing packages...
echo This may take 5-10 minutes...
echo.
pip install --upgrade pip
pip install PyQt5 PyQt5-Qt5 PyQt5-sip
pip install protobuf==3.20.3 grpcio==1.50.0
pip install koapy
pip install pywin32
pip install -r requirements.txt
echo.

REM Verify
echo ================================================================
echo  Verifying Installation
echo ================================================================
python -c "from PyQt5.QtWidgets import QApplication; print('OK: PyQt5')" 2>nul || echo FAIL: PyQt5
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('OK: koapy')" 2>nul || echo FAIL: koapy
python -c "from pydantic import BaseModel; print('OK: pydantic')" 2>nul || echo FAIL: pydantic
echo.

echo ================================================================
echo  Installation Complete!
echo ================================================================
echo.
echo Next: Run login test
echo   python test_login.py
echo.
pause
