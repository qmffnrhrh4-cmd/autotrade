@echo off
chcp 65001 >nul 2>&1

echo ================================================================
echo   Quick Fix for QtBindingsNotFoundError
echo ================================================================
echo.

REM Set QT_API environment variable
echo [Step 1/4] Setting QT_API environment variable...
setx QT_API pyqt5
set QT_API=pyqt5
echo [OK] QT_API set to pyqt5
echo.

REM Test PyQt5 import
echo [Step 2/4] Testing PyQt5 import...
python -c "from PyQt5 import QtCore; print('[OK] PyQt5 import successful')"
if errorlevel 1 (
    echo [ERROR] PyQt5 cannot be imported
    echo Reinstalling PyQt5...
    pip uninstall -y PyQt5 PyQt5-Qt5 PyQt5-sip
    pip install --no-cache-dir PyQt5
)
echo.

REM Reinstall qtpy
echo [Step 3/4] Reinstalling qtpy...
pip uninstall -y qtpy
pip install --no-cache-dir qtpy
echo [OK] qtpy reinstalled
echo.

REM Test koapy import
echo [Step 4/4] Testing koapy import...
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('[SUCCESS] koapy import OK!')"
if errorlevel 1 (
    echo [ERROR] Still failing
    echo.
    echo Please run this command manually:
    echo   set QT_API=pyqt5
    echo   python tests\manual\test_koapy_simple.py
) else (
    echo [SUCCESS] koapy is working!
)
echo.

pause
