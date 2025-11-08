@echo off
echo ================================================================
echo  AutoTrade Setup Verification
echo ================================================================
echo.

REM Find Anaconda
set CONDA_FOUND=0

if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
    set CONDA_PATH=%USERPROFILE%\anaconda3
    set CONDA_FOUND=1
) else if exist "%USERPROFILE%\Anaconda3\Scripts\activate.bat" (
    set CONDA_PATH=%USERPROFILE%\Anaconda3
    set CONDA_FOUND=1
) else if exist "C:\ProgramData\Anaconda3\Scripts\activate.bat" (
    set CONDA_PATH=C:\ProgramData\Anaconda3
    set CONDA_FOUND=1
) else if exist "C:\ProgramData\anaconda3\Scripts\activate.bat" (
    set CONDA_PATH=C:\ProgramData\anaconda3
    set CONDA_FOUND=1
)

if %CONDA_FOUND%==0 (
    echo [FAIL] Anaconda not found
    echo.
    echo Please install Anaconda3 and run INSTALL_ANACONDA_PROMPT.bat
    pause
    exit /b 1
) else (
    echo [OK] Anaconda found at: %CONDA_PATH%
)

echo.
echo Activating autotrade_32 environment...
call "%CONDA_PATH%\Scripts\activate.bat" autotrade_32

if errorlevel 1 (
    echo [FAIL] autotrade_32 environment not found
    echo.
    echo Please run: INSTALL_ANACONDA_PROMPT.bat
    pause
    exit /b 1
) else (
    echo [OK] autotrade_32 environment activated
)

echo.
echo ================================================================
echo  Python Environment
echo ================================================================
python --version
python -c "import struct; print('Architecture:', struct.calcsize('P')*8, 'bit')"
echo.

echo ================================================================
echo  Package Verification
echo ================================================================
echo.

set FAIL_COUNT=0

python -c "from pydantic import BaseModel; print('[OK] pydantic')," 2>nul || (echo [FAIL] pydantic & set /a FAIL_COUNT+=1)
python -c "import pandas; print('[OK] pandas', pandas.__version__)" 2>nul || (echo [FAIL] pandas & set /a FAIL_COUNT+=1)
python -c "import numpy; print('[OK] numpy', numpy.__version__)" 2>nul || (echo [FAIL] numpy & set /a FAIL_COUNT+=1)
python -c "import requests; print('[OK] requests')" 2>nul || (echo [FAIL] requests & set /a FAIL_COUNT+=1)
python -c "import flask; print('[OK] flask')" 2>nul || (echo [FAIL] flask & set /a FAIL_COUNT+=1)
python -c "from flask_socketio import SocketIO; print('[OK] flask_socketio')" 2>nul || (echo [FAIL] flask_socketio & set /a FAIL_COUNT+=1)
python -c "from PyQt5.QtWidgets import QApplication; print('[OK] PyQt5')" 2>nul || (echo [FAIL] PyQt5 & set /a FAIL_COUNT+=1)
python -c "import protobuf; print('[OK] protobuf', protobuf.__version__)" 2>nul || (echo [FAIL] protobuf & set /a FAIL_COUNT+=1)
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[OK] koapy')" 2>nul || (echo [FAIL] koapy & set /a FAIL_COUNT+=1)
python -c "import pywin32; print('[OK] pywin32')" 2>nul || (echo [FAIL] pywin32 & set /a FAIL_COUNT+=1)

echo.

if %FAIL_COUNT%==0 (
    echo ================================================================
    echo  All packages verified! Ready to run!
    echo ================================================================
    echo.
    echo To start AutoTrade:
    echo   1. From any CMD: run.bat
    echo   2. Or: python main.py
    echo.
) else (
    echo ================================================================
    echo  %FAIL_COUNT% package(s) missing!
    echo ================================================================
    echo.
    echo Please run: SETUP_QUICK.bat
    echo.
)

pause
