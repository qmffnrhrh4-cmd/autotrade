@echo off
echo ================================================================
echo  AutoTrade 32-bit Environment Setup
echo ================================================================
echo.

REM Step 1: Check Conda
echo [Step 1/5] Checking Anaconda...
where conda >nul 2>&1
if errorlevel 1 (
    echo ERROR: Anaconda not found!
    echo Please install from: https://www.anaconda.com/download
    pause
    exit /b 1
)
echo OK: Anaconda found
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
