@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ====================================
REM  AutoTrade - All-in-One Setup
REM ====================================

:MAIN_MENU
cls
echo.
echo ================================================================
echo.
echo              AutoTrade Setup and Management Tool
echo.
echo          Kiwoom OpenAPI 32-bit Environment Setup
echo.
echo ================================================================
echo.

REM Check environment
call :CHECK_ENVIRONMENT

echo.
echo ================================================================
echo  Menu
echo ================================================================
echo.
echo   [1] Full Install (Create 32-bit env + Install packages)
echo   [2] Install Packages Only (If env already exists)
echo   [3] Run Login Test
echo   [4] Run Main Program
echo   [5] Show Environment Info
echo   [6] Remove Environment and Reinstall
echo   [0] Exit
echo.
echo ================================================================
echo.

set /p CHOICE="Select option (0-6): "

if "%CHOICE%"=="1" goto FULL_INSTALL
if "%CHOICE%"=="2" goto INSTALL_PACKAGES
if "%CHOICE%"=="3" goto TEST_LOGIN
if "%CHOICE%"=="4" goto RUN_MAIN
if "%CHOICE%"=="5" goto SHOW_INFO
if "%CHOICE%"=="6" goto REMOVE_ENV
if "%CHOICE%"=="0" goto EXIT
goto MAIN_MENU

REM ====================================
REM Check Environment
REM ====================================
:CHECK_ENVIRONMENT
where conda >nul 2>&1
if %errorLevel% neq 0 (
    set CONDA_INSTALLED=[X]
) else (
    set CONDA_INSTALLED=[OK]
)

conda env list 2>nul | find "autotrade_32" >nul 2>&1
if %errorLevel% neq 0 (
    set ENV_EXISTS=[X]
) else (
    set ENV_EXISTS=[OK]
)

echo Current Status:
echo    Anaconda: %CONDA_INSTALLED%
echo    autotrade_32 environment: %ENV_EXISTS%

if "%ENV_EXISTS%"=="[OK]" (
    call conda activate autotrade_32 2>nul
    python -c "import struct; bits = struct.calcsize('P') * 8; print('   Python bits:', bits, 'bit')" 2>nul
)

goto :EOF

REM ====================================
REM 1. Full Install
REM ====================================
:FULL_INSTALL
cls
echo.
echo ================================================================
echo  Full Installation Starting
echo ================================================================
echo.

REM Check Conda
where conda >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Anaconda is not installed!
    echo.
    echo Please install Anaconda first:
    echo    https://www.anaconda.com/download
    echo.
    pause
    goto MAIN_MENU
)

echo [OK] Anaconda found
echo.

REM Check existing environment
conda env list | find "autotrade_32" >nul 2>&1
if %errorLevel% equ 0 (
    echo [WARNING] autotrade_32 environment already exists.
    echo.
    set /p REMOVE="Remove and reinstall? (y/n): "
    if /i "!REMOVE!"=="y" (
        call :REMOVE_ENVIRONMENT
    ) else (
        echo.
        echo Keeping existing environment. Moving to package installation.
        timeout /t 2 >nul
        goto INSTALL_PACKAGES
    )
)

echo.
echo ================================================================
echo  Step 1/5: Creating 32-bit Python Environment
echo ================================================================
echo.

set CONDA_FORCE_32BIT=1
echo Creating 32-bit Python 3.11 environment...
echo (This may take a while)
echo.

conda create -n autotrade_32 python=3.11 -y

if %errorLevel% neq 0 (
    echo.
    echo [ERROR] Environment creation failed!
    pause
    goto MAIN_MENU
)

echo.
echo [OK] Environment created
timeout /t 2 >nul

goto INSTALL_PACKAGES

REM ====================================
REM 2. Install Packages
REM ====================================
:INSTALL_PACKAGES
cls
echo.
echo ================================================================
echo  Package Installation
echo ================================================================
echo.

REM Activate environment
call conda activate autotrade_32

if %errorLevel% neq 0 (
    echo [ERROR] Cannot find autotrade_32 environment!
    echo.
    echo Please run "Full Install" first.
    pause
    goto MAIN_MENU
)

echo [OK] autotrade_32 environment activated
echo.

REM Check Python bits
echo ================================================================
echo  Step 2/5: Checking Python Architecture
echo ================================================================
echo.

python -c "import struct; bits = struct.calcsize('P') * 8; print(f'Python: {bits}-bit'); exit(0 if bits == 32 else 1)"

if %errorLevel% neq 0 (
    echo.
    echo [ERROR] This is not a 32-bit environment!
    echo.
    echo Solution:
    echo    1. Remove environment and reinstall (Menu [6])
    echo    2. Or install 32-bit Python directly
    echo       https://www.python.org/downloads/
    pause
    goto MAIN_MENU
)

echo.

REM Upgrade pip
echo ================================================================
echo  Step 3/5: Upgrading pip
echo ================================================================
echo.

python -m pip install --upgrade pip --quiet

echo [OK] pip upgraded
echo.

REM Install core packages
echo ================================================================
echo  Step 4/5: Installing Core Packages
echo ================================================================
echo.

echo [1/4] Installing PyQt5...
pip install PyQt5 PyQt5-Qt5 PyQt5-sip --quiet --no-warn-script-location

if %errorLevel% neq 0 (
    echo [ERROR] PyQt5 installation failed
    pause
    goto MAIN_MENU
)
echo [OK] PyQt5 installed

echo.
echo [2/4] Installing koapy dependencies...
pip install protobuf==3.20.3 grpcio==1.50.0 --quiet --no-warn-script-location
echo [OK] protobuf, grpcio installed

echo.
echo [3/4] Installing koapy...
pip install koapy --quiet --no-warn-script-location
echo [OK] koapy installed

echo.
echo [4/4] Installing pywin32...
pip install pywin32 --quiet --no-warn-script-location
echo [OK] pywin32 installed

echo.

REM Install all packages
echo ================================================================
echo  Step 5/5: Installing Remaining Packages
echo ================================================================
echo.

echo Installing all requirements.txt packages...
echo (This may take a while)
echo.

pip install -r requirements.txt --quiet --no-warn-script-location

if %errorLevel% neq 0 (
    echo.
    echo [WARNING] Some packages failed to install.
    echo           Core packages are installed, continuing...
)

echo.
echo [OK] Package installation complete
echo.

REM Verify installation
call :VERIFY_INSTALLATION

echo.
echo ================================================================
echo  Installation Complete!
echo ================================================================
echo.
echo Run login test now?
echo.
set /p RUN_TEST="Run login test? (y/n): "

if /i "%RUN_TEST%"=="y" (
    goto TEST_LOGIN
)

pause
goto MAIN_MENU

REM ====================================
REM 3. Login Test
REM ====================================
:TEST_LOGIN
cls
echo.
echo ================================================================
echo  Login Test
echo ================================================================
echo.

REM Activate environment
call conda activate autotrade_32 2>nul

if %errorLevel% neq 0 (
    echo [ERROR] Cannot find autotrade_32 environment!
    echo.
    echo Please run installation first (Menu [1])
    pause
    goto MAIN_MENU
)

REM Check test file
if not exist "test_login.py" (
    echo [ERROR] test_login.py not found!
    echo.
    echo Current directory: %CD%
    pause
    goto MAIN_MENU
)

echo Starting login test...
echo.
echo ================================================================
echo.

python test_login.py

echo.
echo ================================================================
echo  Test Complete
echo ================================================================
echo.

pause
goto MAIN_MENU

REM ====================================
REM 4. Run Main Program
REM ====================================
:RUN_MAIN
cls
echo.
echo ================================================================
echo  Running Main Program
echo ================================================================
echo.

REM Activate environment
call conda activate autotrade_32 2>nul

if %errorLevel% neq 0 (
    echo [ERROR] Cannot find autotrade_32 environment!
    echo.
    echo Please run installation first (Menu [1])
    pause
    goto MAIN_MENU
)

REM Check main file
if not exist "main.py" (
    echo [ERROR] main.py not found!
    echo.
    echo Current directory: %CD%
    pause
    goto MAIN_MENU
)

echo Starting AutoTrade...
echo.
echo ================================================================
echo.

python main.py

echo.
echo ================================================================
echo  Program Terminated
echo ================================================================
echo.

pause
goto MAIN_MENU

REM ====================================
REM 5. Show Environment Info
REM ====================================
:SHOW_INFO
cls
echo.
echo ================================================================
echo  Environment Information
echo ================================================================
echo.

REM Check Anaconda
echo ================================================================
echo  Anaconda Info
echo ================================================================
echo.

where conda >nul 2>&1
if %errorLevel% neq 0 (
    echo [X] Anaconda not installed
) else (
    echo [OK] Anaconda installed
    conda --version 2>nul
)

echo.

REM Environment list
echo ================================================================
echo  Conda Environments
echo ================================================================
echo.

conda env list 2>nul

echo.

REM autotrade_32 details
echo ================================================================
echo  autotrade_32 Environment Details
echo ================================================================
echo.

conda env list | find "autotrade_32" >nul 2>&1
if %errorLevel% neq 0 (
    echo [X] autotrade_32 environment does not exist
) else (
    echo [OK] autotrade_32 environment exists
    echo.

    call conda activate autotrade_32 2>nul

    echo Python version:
    python --version 2>nul

    echo.
    echo Python architecture:
    python -c "import struct; print(f'{struct.calcsize(\"P\")*8}-bit')" 2>nul

    echo.
    echo Installed core packages:
    call :VERIFY_INSTALLATION
)

echo.
pause
goto MAIN_MENU

REM ====================================
REM 6. Remove Environment
REM ====================================
:REMOVE_ENV
cls
echo.
echo ================================================================
echo  Remove Environment
echo ================================================================
echo.

echo [WARNING] This will completely remove autotrade_32 environment!
echo.
set /p CONFIRM="Are you sure? (y/n): "

if /i not "%CONFIRM%"=="y" (
    echo.
    echo Cancelled.
    timeout /t 2 >nul
    goto MAIN_MENU
)

call :REMOVE_ENVIRONMENT

set /p REINSTALL="Install again now? (y/n): "

if /i "%REINSTALL%"=="y" (
    goto FULL_INSTALL
)

pause
goto MAIN_MENU

REM ====================================
REM Remove Environment Function
REM ====================================
:REMOVE_ENVIRONMENT
echo.
echo Removing autotrade_32 environment...

call conda deactivate 2>nul
conda env remove -n autotrade_32 -y

if %errorLevel% equ 0 (
    echo [OK] Environment removed
) else (
    echo [ERROR] Failed to remove environment
)

echo.
timeout /t 2 >nul
goto :EOF

REM ====================================
REM Verify Installation Function
REM ====================================
:VERIFY_INSTALLATION
echo ================================================================
echo  Verifying Installation
echo ================================================================
echo.

python -c "from PyQt5.QtWidgets import QApplication; print('[OK] PyQt5')" 2>nul
if %errorLevel% neq 0 echo [X] PyQt5

python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[OK] koapy')" 2>nul
if %errorLevel% neq 0 echo [X] koapy

python -c "from pydantic import BaseModel; print('[OK] pydantic')" 2>nul
if %errorLevel% neq 0 echo [X] pydantic

python -c "import pandas; print('[OK] pandas')" 2>nul
if %errorLevel% neq 0 echo [X] pandas

python -c "import numpy; print('[OK] numpy')" 2>nul
if %errorLevel% neq 0 echo [X] numpy

python -c "import pywin32_system32; print('[OK] pywin32')" 2>nul
if %errorLevel% neq 0 echo [X] pywin32

goto :EOF

REM ====================================
REM Exit
REM ====================================
:EXIT
cls
echo.
echo ================================================================
echo.
echo            Thank you for using AutoTrade!
echo.
echo                   Happy Trading!
echo.
echo ================================================================
echo.
timeout /t 2 >nul
exit /b 0
