@echo off
chcp 65001 >nul 2>&1

echo ================================================================
echo   SIGNAL Fix (Direct File Edit)
echo ================================================================
echo.

REM Get koapy location
for /f "tokens=2" %%i in ('pip show koapy ^| findstr Location') do set KOAPY_PATH=%%i

if "%KOAPY_PATH%"=="" (
    echo [ERROR] Cannot find koapy installation
    pause
    exit /b 1
)

echo koapy path: %KOAPY_PATH%
echo.

set QTCORE_FILE=%KOAPY_PATH%\koapy\compat\pyside2\QtCore.py

if not exist "%QTCORE_FILE%" (
    echo [ERROR] QtCore.py not found at: %QTCORE_FILE%
    pause
    exit /b 1
)

echo Target file: %QTCORE_FILE%
echo.

REM Backup
copy "%QTCORE_FILE%" "%QTCORE_FILE%.bak" >nul
echo [OK] Backup created

REM Add SIGNAL function
echo. >> "%QTCORE_FILE%"
echo # SIGNAL compatibility for Python 3.11 >> "%QTCORE_FILE%"
echo def SIGNAL(signal_name): >> "%QTCORE_FILE%"
echo     return signal_name >> "%QTCORE_FILE%"

echo [OK] SIGNAL function added
echo.

echo ================================================================
echo Testing koapy import...
echo ================================================================
python quick_test.py

pause
