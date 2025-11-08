@echo off
echo ================================================================
echo  AutoTrade Package Reinstall
echo ================================================================
echo.
echo This will reinstall all packages in autotrade_32 environment
echo.

call conda activate autotrade_32
if errorlevel 1 (
    echo ERROR: autotrade_32 environment not found!
    echo.
    echo Please run INSTALL_ANACONDA_PROMPT.bat first
    pause
    exit /b 1
)

echo Environment activated: autotrade_32
echo.

REM Check Python version
python --version
python -c "import struct; print('Architecture:', struct.calcsize('P')*8, 'bit')"
echo.

echo ================================================================
echo  Installing all packages from requirements.txt
echo ================================================================
echo This may take 5-10 minutes...
echo.

REM Upgrade pip first
python -m pip install --upgrade pip

REM Install all packages
pip install -r requirements.txt

echo.
echo ================================================================
echo  Verifying critical packages
echo ================================================================
echo.

python -c "from PyQt5.QtWidgets import QApplication; print('[OK] PyQt5')" 2>nul || echo [FAIL] PyQt5
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[OK] koapy')" 2>nul || echo [FAIL] koapy
python -c "import protobuf; print('[OK] protobuf', protobuf.__version__)" 2>nul || echo [FAIL] protobuf
python -c "from pydantic import BaseModel; print('[OK] pydantic')" 2>nul || echo [FAIL] pydantic
python -c "import pandas; print('[OK] pandas')" 2>nul || echo [FAIL] pandas
python -c "import numpy; print('[OK] numpy')" 2>nul || echo [FAIL] numpy

echo.
echo ================================================================
echo  Reinstall Complete!
echo ================================================================
echo.

pause
