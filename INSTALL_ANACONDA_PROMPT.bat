@echo off
REM ============================================================
REM  Use this file in Anaconda Prompt (NOT regular cmd)
REM ============================================================
echo ================================================================
echo  AutoTrade 32-bit Environment Setup
echo  (Run in Anaconda Prompt!)
echo ================================================================
echo.

REM Step 1: Initialize conda for this session
call conda --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Please run this in Anaconda Prompt!
    echo.
    echo How to open Anaconda Prompt:
    echo   1. Press Windows key
    echo   2. Type "Anaconda Prompt"
    echo   3. Click it
    echo   4. cd C:\Users\USER\Desktop\autotrade
    echo   5. Run this script again
    pause
    exit /b 1
)

echo OK: conda found
echo Version:
call conda --version
echo.

REM Step 2: Create 32-bit environment
echo [Step 1/4] Creating 32-bit Python environment...
echo Name: autotrade_32
echo Python: 3.10 (32-bit compatible)
echo.
set CONDA_FORCE_32BIT=1
call conda create -n autotrade_32 python=3.10 -y
if errorlevel 1 (
    echo ERROR: Failed to create environment
    pause
    exit /b 1
)
echo.

REM Step 3: Activate environment
echo [Step 2/4] Activating environment...
call conda activate autotrade_32
if errorlevel 1 (
    echo ERROR: Failed to activate
    pause
    exit /b 1
)
echo.

REM Step 4: Verify 32-bit
echo [Step 3/4] Verifying architecture...
python -c "import struct; bits=struct.calcsize('P')*8; print(f'Python: {bits}-bit'); exit(0 if bits==32 else 1)"
if errorlevel 1 (
    echo.
    echo WARNING: 64-bit environment was created!
    echo This happens if Anaconda is 64-bit only.
    echo.
    echo Solution: Install 32-bit Python directly
    echo   https://www.python.org/downloads/
    echo.
    pause
)
echo.

REM Step 5: Install packages
echo [Step 4/4] Installing packages...
echo This takes 5-10 minutes...
echo.

call pip install --upgrade pip
call pip install PyQt5 PyQt5-Qt5 PyQt5-sip
call pip install protobuf==3.20.3 grpcio==1.50.0
call pip install koapy pywin32
call pip install -r requirements.txt
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
echo To use:
echo   1. Open Anaconda Prompt
echo   2. conda activate autotrade_32
echo   3. cd C:\Users\USER\Desktop\autotrade
echo   4. python test_login.py
echo.
pause
