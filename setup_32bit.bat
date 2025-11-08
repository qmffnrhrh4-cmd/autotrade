@echo off
chcp 65001 >nul 2>&1
REM ====================================
REM  AutoTrade - 32-bit Auto Setup
REM ====================================
echo.
echo ================================================================
echo.
echo       AutoTrade 32-bit Python Environment Setup
echo.
echo ================================================================
echo.

REM Check admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Please run as Administrator!
    echo.
    pause
    exit /b 1
)

REM Check Conda installation
where conda >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Anaconda not installed!
    echo.
    echo Please install Anaconda from:
    echo https://www.anaconda.com/download
    echo.
    pause
    exit /b 1
)

echo [OK] Anaconda found
echo.

REM Remove existing environment (optional)
conda env list | find "autotrade_32" >nul 2>&1
if %errorLevel% equ 0 (
    echo.
    echo [WARNING] autotrade_32 environment already exists.
    set /p REMOVE="Remove and reinstall? (y/n): "
    if /i "%REMOVE%"=="y" (
        echo.
        echo Removing existing environment...
        call conda deactivate 2>nul
        conda env remove -n autotrade_32 -y
        echo [OK] Environment removed
        echo.
    )
)

REM Create 32-bit environment
echo ================================================================
echo  Step 1: Creating 32-bit Python Environment
echo ================================================================
echo.

set CONDA_FORCE_32BIT=1
echo Creating 32-bit Python 3.11 environment...
conda create -n autotrade_32 python=3.11 -y

if %errorLevel% neq 0 (
    echo [ERROR] Environment creation failed!
    pause
    exit /b 1
)

echo.
echo [OK] Environment created
echo.

REM Activate environment
echo ================================================================
echo  Step 2: Activating Environment
echo ================================================================
echo.

call conda activate autotrade_32

if %errorLevel% neq 0 (
    echo [ERROR] Environment activation failed!
    pause
    exit /b 1
)

echo [OK] Environment activated
echo.

REM Verify 32-bit
echo Verifying Python architecture...
python -c "import struct; bits = struct.calcsize('P') * 8; print(f'Python: {bits}-bit'); exit(0 if bits == 32 else 1)"

if %errorLevel% neq 0 (
    echo.
    echo [ERROR] 32-bit environment creation failed!
    echo         64-bit environment was created instead.
    echo.
    echo Solution:
    echo    1. Reinstall Anaconda (32-bit version)
    echo    2. Or install 32-bit Python directly
    echo       https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo.

REM Upgrade pip
echo ================================================================
echo  Step 3: Upgrading pip
echo ================================================================
echo.

python -m pip install --upgrade pip

echo [OK] pip upgraded
echo.

REM Install dependencies
echo ================================================================
echo  Step 4: Installing Dependencies
echo ================================================================
echo.

echo Installing packages (this may take a while)...
echo.

echo [1/3] Core packages (PyQt5, koapy)...
pip install PyQt5 PyQt5-Qt5 PyQt5-sip --no-warn-script-location

if %errorLevel% neq 0 (
    echo [ERROR] PyQt5 installation failed!
    echo.
    echo Solution:
    echo    Manual install: pip install PyQt5
    pause
    exit /b 1
)

pip install protobuf==3.20.3 grpcio==1.50.0 koapy --no-warn-script-location

if %errorLevel% neq 0 (
    echo [ERROR] koapy installation failed!
    pause
    exit /b 1
)

echo.
echo [2/3] pywin32...
pip install pywin32 --no-warn-script-location

echo.
echo [3/3] All remaining packages...
pip install -r requirements.txt --no-warn-script-location

if %errorLevel% neq 0 (
    echo.
    echo [WARNING] Some packages failed to install.
    echo           Core packages are installed, continuing...
    echo.
)

echo [OK] Dependencies installed
echo.

REM Verify installation
echo ================================================================
echo  Step 5: Verifying Installation
echo ================================================================
echo.

echo Checking installed packages...
echo.

python -c "from PyQt5.QtWidgets import QApplication; print('[OK] PyQt5')" 2>nul
if %errorLevel% neq 0 echo [X] PyQt5 installation failed

python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[OK] koapy')" 2>nul
if %errorLevel% neq 0 echo [X] koapy installation failed

python -c "from pydantic import BaseModel; print('[OK] pydantic')" 2>nul
if %errorLevel% neq 0 echo [X] pydantic installation failed

python -c "import pandas; print('[OK] pandas')" 2>nul
if %errorLevel% neq 0 echo [X] pandas installation failed

python -c "import pywin32_system32; print('[OK] pywin32')" 2>nul
if %errorLevel% neq 0 echo [X] pywin32 installation failed

echo.

REM Complete
echo ================================================================
echo  Installation Complete!
echo ================================================================
echo.
echo Next steps:
echo.
echo   1. Open new terminal:
echo      conda activate autotrade_32
echo.
echo   2. Run login test:
echo      python test_login.py
echo.
echo   3. Run main program:
echo      python main.py
echo.
echo Tips:
echo   - Always activate autotrade_32 environment
echo   - Select autotrade_32 as Python interpreter in VSCode
echo   - Use activate_32.bat for quick activation
echo.
echo Documentation:
echo   docs\SETUP_32BIT_ENVIRONMENT.md
echo.

pause
