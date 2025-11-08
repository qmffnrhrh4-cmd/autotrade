@echo off
echo ================================================================
echo  Install Packages for 64-bit Python Environment
echo ================================================================
echo.
echo This installs packages needed to run main.py in 64-bit Python.
echo.
echo Current Python:
python --version
python -c "import struct; print('Architecture:', struct.calcsize('P')*8, 'bit')"
echo.

set /p CONTINUE="Continue installation? (y/n): "
if /i not "%CONTINUE%"=="y" exit /b 0

echo.
echo ================================================================
echo  Installing packages...
echo ================================================================
echo.

REM Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing packages from requirements_64bit.txt...
pip install -r requirements_64bit.txt

echo.
echo ================================================================
echo  Verifying installation...
echo ================================================================
echo.

python -c "from pydantic import BaseModel; print('[OK] pydantic')" 2>nul || echo [FAIL] pydantic
python -c "import pandas; print('[OK] pandas', pandas.__version__)" 2>nul || echo [FAIL] pandas
python -c "import numpy; print('[OK] numpy', numpy.__version__)" 2>nul || echo [FAIL] numpy
python -c "import flask; print('[OK] Flask')" 2>nul || echo [FAIL] Flask
python -c "from flask_socketio import SocketIO; print('[OK] flask-socketio')" 2>nul || echo [FAIL] flask-socketio
python -c "import requests; print('[OK] requests')" 2>nul || echo [FAIL] requests

echo.
echo ================================================================
echo  Installation Complete!
echo ================================================================
echo.
echo You can now run:
echo   python main.py
echo.

pause
