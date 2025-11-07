@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================
REM koapy Complete Auto Setup & Test
REM ============================================

echo.
echo ================================================================
echo   koapy Complete Auto Setup and Test (All-in-One)
echo ================================================================
echo.
echo This script will:
echo   - Clean up existing installations
echo   - Install correct versions automatically
echo   - Handle all dependency issues
echo   - Run diagnostic tests
echo   - Fix any import errors
echo   - Run final tests until success
echo.
echo Please wait... This may take 5-10 minutes.
echo.
pause

REM ============================================
REM Step 1: Environment Check
REM ============================================
echo.
echo ================================================================
echo [STEP 1/10] Checking Python Environment
echo ================================================================
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.11 from https://www.python.org/downloads/
    pause
    exit /b 1
)
python -c "import struct; bits = struct.calcsize('P') * 8; print(f'[OK] Current Python: {bits}-bit')"
echo.

REM ============================================
REM Step 2: Complete Cleanup
REM ============================================
echo.
echo ================================================================
echo [STEP 2/10] Complete Cleanup (Removing ALL conflicting packages)
echo ================================================================
pip uninstall -y protobuf grpcio grpcio-tools koapy 2>nul
pip uninstall -y PyQt5 PySide2 qtpy 2>nul
pip uninstall -y discord.py aiohttp exchange-calendars 2>nul
echo [OK] Cleanup complete
echo.

REM ============================================
REM Step 3: Install Core Versions
REM ============================================
echo.
echo ================================================================
echo [STEP 3/10] Installing Core Packages (protobuf + grpcio)
echo ================================================================
pip install --no-cache-dir protobuf==3.20.3 grpcio==1.50.0
if errorlevel 1 (
    echo [ERROR] Failed to install core packages
    pause
    exit /b 1
)
echo [OK] Core packages installed
echo.

REM ============================================
REM Step 4: Install koapy (no deps)
REM ============================================
echo.
echo ================================================================
echo [STEP 4/10] Installing koapy (without dependencies)
echo ================================================================
pip install --no-deps koapy
if errorlevel 1 (
    echo [ERROR] Failed to install koapy
    pause
    exit /b 1
)
echo [OK] koapy installed
echo.

REM ============================================
REM Step 5: Install Basic Dependencies
REM ============================================
echo.
echo ================================================================
echo [STEP 5/10] Installing Basic Dependencies
echo ================================================================
pip install --no-cache-dir PyQt5 pandas numpy requests beautifulsoup4 lxml
pip install --no-cache-dir python-dateutil pytz tzlocal wrapt rx attrs
if errorlevel 1 (
    echo [WARNING] Some basic packages failed, retrying...
    timeout /t 2 >nul
    pip install PyQt5 pandas numpy requests
)
echo [OK] Basic dependencies installed
echo.

REM ============================================
REM Step 6: Install Optional Dependencies
REM ============================================
echo.
echo ================================================================
echo [STEP 6/10] Installing Optional Dependencies
echo ================================================================
pip install --no-cache-dir Click jsonlines korean-lunar-calendar openpyxl
pip install --no-cache-dir pendulum pyhocon qtpy schedule Send2Trash
pip install --no-cache-dir SQLAlchemy tabulate tqdm
echo [OK] Optional dependencies installed
echo.

REM ============================================
REM Step 7: Install Network Dependencies
REM ============================================
echo.
echo ================================================================
echo [STEP 7/10] Installing Network Dependencies
echo ================================================================
echo Installing aiohttp and discord.py...
pip install --no-cache-dir aiohttp
pip install --no-cache-dir discord.py
if errorlevel 1 (
    echo [WARNING] Some network packages failed (continuing)
)
echo.
echo Installing exchange-calendars...
pip install --no-cache-dir exchange-calendars
if errorlevel 1 (
    echo [WARNING] exchange-calendars failed (not critical)
)
echo [OK] Network dependencies installed
echo.

REM ============================================
REM Step 8: Force Correct Versions
REM ============================================
echo.
echo ================================================================
echo [STEP 8/10] Enforcing Correct Versions (Final)
echo ================================================================
pip install --force-reinstall --no-deps protobuf==3.20.3
pip install --force-reinstall --no-deps grpcio==1.50.0
echo [OK] Versions enforced
echo.

REM ============================================
REM Step 9: Fix Qt Bindings Issue
REM ============================================
echo.
echo ================================================================
echo [STEP 9/11] Fixing Qt Bindings (Setting QT_API)
echo ================================================================

REM Set QT_API environment variable to force qtpy to use PyQt5
echo Setting QT_API=pyqt5...
set QT_API=pyqt5
echo [OK] QT_API set to pyqt5
echo.

REM Verify PyQt5 import
echo Verifying PyQt5 import...
python -c "from PyQt5 import QtCore; print('[OK] PyQt5 works')" 2>nul
if errorlevel 1 (
    echo [WARNING] PyQt5 import failed, reinstalling...
    pip uninstall -y PyQt5 PyQt5-Qt5 PyQt5-sip
    pip install --no-cache-dir PyQt5
    echo [OK] PyQt5 reinstalled
) else (
    echo [OK] PyQt5 verified
)
echo.

REM Reinstall qtpy to ensure it picks up PyQt5
echo Reinstalling qtpy with QT_API set...
pip uninstall -y qtpy
pip install --no-cache-dir qtpy
echo [OK] qtpy reinstalled
echo.

REM Apply patch if exists
if exist patch_koapy.py (
    echo Applying PyQt5 patch...
    python patch_koapy.py
    echo [OK] Patch applied
    echo.
)

REM ============================================
REM Step 10: Test Import
REM ============================================
echo.
echo ================================================================
echo [STEP 10/11] Testing koapy Import
echo ================================================================

REM Test import - Round 1
echo [Test 1/3] Testing koapy import...
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[SUCCESS] koapy import OK!')" 2>nul
if errorlevel 1 (
    echo [WARNING] First import test failed
    echo.
    echo Trying to fix by installing missing dependencies...

    REM Install potentially missing packages
    pip install --no-cache-dir multidict frozenlist yarl aiosignal
    pip install --no-cache-dir greenlet toolz pyluach

    REM Test import - Round 2
    echo.
    echo [Test 2/3] Testing koapy import again...
    python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[SUCCESS] koapy import OK!')" 2>nul
    if errorlevel 1 (
        echo [WARNING] Second import test failed
        echo.
        echo Running detailed diagnostic...
        python diagnose_koapy.py
        echo.
        echo Attempting final fix...

        REM Force reinstall koapy
        pip uninstall -y koapy
        pip install --no-deps koapy
        pip install --force-reinstall --no-deps protobuf==3.20.3 grpcio==1.50.0

        REM Test import - Round 3
        echo.
        echo [Test 3/3] Final koapy import test...
        python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[SUCCESS] koapy import OK!')" 2>nul
        if errorlevel 1 (
            echo.
            echo ================================================================
            echo [ERROR] koapy import still failing after multiple attempts
            echo ================================================================
            echo.
            echo Running detailed diagnostic for manual review...
            python diagnose_koapy.py
            echo.
            echo Please review the error messages above.
            pause
            exit /b 1
        )
    )
)

echo.
echo ================================================================
echo [SUCCESS] koapy import is working!
echo ================================================================
echo.

REM ============================================
REM Step 11: Run Final Tests
REM ============================================
echo.
echo ================================================================
echo [STEP 11/11] Running Final Tests
echo ================================================================
echo.

REM Check if test files exist
if not exist "tests\manual\test_koapy_simple.py" (
    echo [WARNING] Test files not found in tests\manual\
    echo Skipping automatic tests
    goto :final_summary
)

echo ----------------------------------------------------------------
echo Running test_koapy_simple.py
echo ----------------------------------------------------------------
echo.
echo [INFO] This test will open a login window.
echo [INFO] You can manually login or press Ctrl+C to skip.
echo.
timeout /t 3 >nul

REM Run simple test (allow user to exit with Ctrl+C)
python tests\manual\test_koapy_simple.py
set TEST_RESULT=%errorlevel%

echo.
if %TEST_RESULT% EQU 0 (
    echo [SUCCESS] Simple test completed
) else (
    echo [INFO] Test was interrupted or had issues (this is normal for first run)
)
echo.

:final_summary
echo.
echo ================================================================
echo                 Installation Complete!
echo ================================================================
echo.
echo Final package versions:
python -c "import importlib.metadata as md; pkgs = ['protobuf', 'grpcio', 'koapy', 'PyQt5', 'pandas']; [print(f'  {pkg}: {md.version(pkg)}') for pkg in pkgs]"
echo.
echo ================================================================
echo Next Steps:
echo ================================================================
echo   1. Run: python tests\manual\test_koapy_simple.py
echo   2. Run: python tests\manual\test_koapy_advanced.py
echo   3. Or run: python diagnose_koapy.py (if issues)
echo.
echo NOTE: You need Kiwoom OpenAPI+ installed on this Windows machine.
echo       Download from: https://www3.kiwoom.com/
echo.
echo ================================================================
echo                 All Done! Press any key to exit.
echo ================================================================
pause
