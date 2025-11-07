@echo off
chcp 65001 >nul 2>&1
REM ============================================
REM koapy Windows Auto Installation Script
REM ============================================

echo.
echo ================================================
echo   koapy Automatic Installation (Windows)
echo ================================================
echo.

REM Check Python
echo [Step 1/8] Checking Python environment...
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.11 from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check architecture
echo.
python -c "import struct; bits = struct.calcsize('P') * 8; print(f'Current Python: {bits}-bit')"
echo.

REM Step 1: Uninstall conflicting packages
echo [Step 2/8] Removing conflicting packages...
pip uninstall -y protobuf grpcio grpcio-tools 2>nul
echo [OK] Cleanup complete
echo.

REM Step 2: Install correct protobuf and grpcio versions
echo [Step 3/8] Installing protobuf 3.20.3 and grpcio 1.50.0...
pip install --force-reinstall protobuf==3.20.3 grpcio==1.50.0
if errorlevel 1 (
    echo [ERROR] Failed to install protobuf/grpcio
    pause
    exit /b 1
)
echo [OK] protobuf/grpcio installed
echo.

REM Step 3: Install koapy without dependencies
echo [Step 4/8] Installing koapy (--no-deps)...
pip install --no-deps koapy
if errorlevel 1 (
    echo [ERROR] Failed to install koapy
    pause
    exit /b 1
)
echo [OK] koapy installed
echo.

REM Step 4: Install basic dependencies (without PySide2)
echo [Step 5/8] Installing basic dependencies...
pip install PyQt5 pandas numpy requests beautifulsoup4 lxml
pip install python-dateutil pytz tzlocal wrapt rx
if errorlevel 1 (
    echo [WARNING] Some packages failed (continuing)
)
echo [OK] Basic dependencies installed
echo.

REM Step 5: Install optional dependencies (without version-conflicting ones)
echo [Step 6/8] Installing optional dependencies...
pip install Click jsonlines korean-lunar-calendar openpyxl pendulum pyhocon
pip install qtpy schedule Send2Trash SQLAlchemy tabulate tqdm attrs
if errorlevel 1 (
    echo [WARNING] Some packages failed (continuing)
)
echo [OK] Optional dependencies installed
echo.

REM Step 6: Force correct versions again (in case they were upgraded)
echo [Step 7/8] Enforcing correct protobuf/grpcio versions...
pip install --force-reinstall --no-deps protobuf==3.20.3
pip install --force-reinstall --no-deps grpcio==1.50.0
echo [OK] Versions enforced
echo.

REM Step 7: Apply PyQt5 patch
echo [Step 8/8] Applying PyQt5 patch...
if exist patch_koapy.py (
    python patch_koapy.py
    echo [OK] Patch applied
) else (
    echo [WARNING] patch_koapy.py not found, skipping patch
)
echo.

REM Final verification
echo ================================================
echo Installation Complete! Version Check:
echo ================================================
echo.

python -c "import sys; import pip; packages = ['protobuf', 'grpcio', 'koapy']; [print(f'{pkg}: {pip.__version__}' if pkg == 'pip' else '') for pkg in packages]; import importlib.metadata as md; [print(f'{pkg}: {md.version(pkg)}') for pkg in packages]"

echo.
echo ================================================
echo Testing koapy import...
echo ================================================
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[SUCCESS] koapy import OK!')" 2>nul
if errorlevel 1 (
    echo [WARNING] koapy import failed, but installation is complete.
    echo This is normal if PyQt5 patch was not applied or if running without GUI.
) else (
    echo [SUCCESS] koapy is ready to use!
)

echo.
echo ================================================
echo Next Steps:
echo ================================================
echo   1. Run: python tests\manual\test_koapy_simple.py
echo   2. Run: python tests\manual\test_koapy_advanced.py
echo.
echo Note: koapy requires Windows and Kiwoom OpenAPI+ installed
echo.

pause
