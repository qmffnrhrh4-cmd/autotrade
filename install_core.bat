@echo off
echo ================================================================
echo  Installing Core Packages Only (32-bit compatible)
echo ================================================================
echo.

call conda activate autotrade_32
if errorlevel 1 (
    echo ERROR: autotrade_32 environment not found!
    echo Please run INSTALL_ANACONDA_PROMPT.bat first
    pause
    exit /b 1
)

echo Installing core packages with compatible versions...
echo.

REM Core packages (必수)
echo [1/10] pydantic...
pip install pydantic

echo [2/10] pandas (compatible version)...
pip install pandas==2.0.3

echo [3/10] numpy (compatible version)...
pip install numpy==1.24.3

echo [4/10] requests, urllib3...
pip install requests urllib3

echo [5/10] python-dotenv, PyYAML...
pip install python-dotenv PyYAML

echo [6/10] colorlog, loguru...
pip install colorlog loguru

echo [7/10] Flask, flask-socketio...
pip install Flask flask-socketio websocket-client python-socketio python-engineio

echo [8/10] PyQt5 (for koapy)...
pip install PyQt5 PyQt5-Qt5 PyQt5-sip

echo [9/10] koapy dependencies...
pip install protobuf==3.20.3 grpcio==1.50.0

echo [10/10] koapy, pywin32...
pip install koapy pywin32

echo.
echo ================================================================
echo  Core packages installed!
echo ================================================================
echo.

REM Verify
python -c "from pydantic import BaseModel; print('[OK] pydantic')" 2>nul || echo [FAIL] pydantic
python -c "import pandas; print('[OK] pandas', pandas.__version__)" 2>nul || echo [FAIL] pandas
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[OK] koapy')" 2>nul || echo [FAIL] koapy

echo.
echo Now you can run: python main.py
echo.

pause
