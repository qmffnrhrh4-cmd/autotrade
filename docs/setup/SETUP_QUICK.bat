@echo off
echo ================================================================
echo  AutoTrade Quick Setup (32-bit Compatible)
echo ================================================================
echo.
echo This will:
echo   1. Check/activate autotrade_32 environment
echo   2. Install all packages with 32-bit compatible versions
echo   3. Verify installation
echo.
echo Press any key to start...
pause >nul
echo.

REM Find and initialize Anaconda
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
    echo ERROR: Anaconda not found!
    echo.
    echo Please install Anaconda3 first from:
    echo https://www.anaconda.com/download
    echo.
    pause
    exit /b 1
)

echo Found Anaconda at: %CONDA_PATH%
echo.

REM Activate environment
echo Activating autotrade_32 environment...
call "%CONDA_PATH%\Scripts\activate.bat" autotrade_32

if errorlevel 1 (
    echo.
    echo ERROR: autotrade_32 environment not found!
    echo.
    echo Please create it first:
    echo   1. Open Anaconda Prompt
    echo   2. Run: INSTALL_ANACONDA_PROMPT.bat
    echo.
    pause
    exit /b 1
)

echo Environment activated!
echo.

REM Check Python version and architecture
echo Checking Python environment...
python --version
python -c "import struct; print('Architecture:', struct.calcsize('P')*8, 'bit')"
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

echo ================================================================
echo  Installing packages with 32-bit compatible versions
echo ================================================================
echo.

REM Core packages (필수)
echo [1/12] pydantic...
pip install pydantic==2.5.3

echo [2/12] pandas (32-bit compatible)...
pip install pandas==2.0.3

echo [3/12] numpy (32-bit compatible)...
pip install numpy==1.24.3

echo [4/12] requests, urllib3...
pip install requests>=2.31.0 urllib3>=2.0.0

echo [5/12] python-dotenv, PyYAML...
pip install python-dotenv>=1.0.0 PyYAML>=6.0.0

echo [6/12] colorlog, loguru...
pip install colorlog>=6.8.0 loguru>=0.7.0

echo [7/12] Flask, flask-socketio...
pip install Flask>=3.0.0 flask-socketio>=5.3.0 websocket-client>=1.7.0 python-socketio>=5.10.0 python-engineio>=4.8.0

echo [8/12] flask-cors...
pip install flask-cors>=4.0.0

echo [9/12] PyQt5 (for koapy)...
pip install PyQt5>=5.15.0 PyQt5-Qt5>=5.15.0 PyQt5-sip>=12.0.0

echo [10/12] koapy dependencies...
pip install protobuf==3.20.3 grpcio==1.50.0

echo [11/12] koapy, pywin32...
pip install koapy>=0.5.0 pywin32>=305

echo [12/12] Additional utilities...
pip install pytz>=2023.3 python-dateutil>=2.8.0 SQLAlchemy>=2.0.0

echo.
echo ================================================================
echo  Verifying critical packages
echo ================================================================
echo.

python -c "from pydantic import BaseModel; print('[OK] pydantic')," || echo [FAIL] pydantic
python -c "import pandas; print('[OK] pandas', pandas.__version__)" || echo [FAIL] pandas
python -c "import numpy; print('[OK] numpy', numpy.__version__)" || echo [FAIL] numpy
python -c "from PyQt5.QtWidgets import QApplication; print('[OK] PyQt5')" || echo [FAIL] PyQt5
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[OK] koapy')" || echo [FAIL] koapy
python -c "import flask; print('[OK] Flask')" || echo [FAIL] Flask

echo.
echo ================================================================
echo  Setup Complete!
echo ================================================================
echo.
echo Next steps:
echo   1. To run AutoTrade from ANY CMD window:
echo      run.bat
echo.
echo   2. Or manually:
echo      python main.py
echo.
echo   3. Or from Anaconda Prompt:
echo      conda activate autotrade_32
echo      python main.py
echo.
echo Your AutoTrade will connect to:
echo   - REST API (for trading)
echo   - OpenAPI+ (for live data and orders)
echo.

pause
