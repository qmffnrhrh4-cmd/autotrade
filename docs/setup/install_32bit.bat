@echo off
echo ================================================================
echo  Install Packages for 32-bit OpenAPI Server Environment
echo ================================================================
echo.
echo This installs packages needed for openapi_server.py
echo in the autotrade_32 (32-bit) environment.
echo.

REM Find Anaconda
set CONDA_FOUND=0
set CONDA_PATH=

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
    echo Please install Anaconda3 and run INSTALL_ANACONDA_PROMPT.bat
    pause
    exit /b 1
)

echo [OK] Anaconda found: %CONDA_PATH%
echo.

REM Activate environment
echo Activating autotrade_32 environment...
call "%CONDA_PATH%\Scripts\activate.bat" autotrade_32

if errorlevel 1 (
    echo.
    echo ERROR: autotrade_32 environment not found!
    echo.
    echo Please create it first:
    echo   INSTALL_ANACONDA_PROMPT.bat
    echo.
    pause
    exit /b 1
)

echo [OK] Environment activated
echo.

REM Check Python
echo Current Python:
python --version
python -c "import struct; print('Architecture:', struct.calcsize('P')*8, 'bit')"
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

echo ================================================================
echo  Installing packages from requirements_32bit.txt...
echo ================================================================
echo.

pip install -r requirements_32bit.txt

echo.
echo ================================================================
echo  Verifying installation...
echo ================================================================
echo.

python -c "import flask; print('[OK] Flask')" 2>nul || echo [FAIL] Flask
python -c "from flask_cors import CORS; print('[OK] flask-cors')" 2>nul || echo [FAIL] flask-cors
python -c "from PyQt5.QtWidgets import QApplication; print('[OK] PyQt5')" 2>nul || echo [FAIL] PyQt5
python -c "import protobuf; print('[OK] protobuf')" 2>nul || echo [FAIL] protobuf
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[OK] koapy')" 2>nul || echo [FAIL] koapy
python -c "import requests; print('[OK] requests')" 2>nul || echo [FAIL] requests

echo.
echo ================================================================
echo  Installation Complete!
echo ================================================================
echo.
echo You can now run:
echo   python main.py
echo.
echo The OpenAPI server will start automatically in the background.
echo.

pause
