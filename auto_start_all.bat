@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo   AutoTrade Pro - Complete Automation System v6.3
echo ================================================================================
echo.
echo   [v] OpenAPI Server 32-bit - Kiwoom Connection
echo   [v] Strategy Evolution Engine - 24/7 Auto Optimization
echo   [v] Web Dashboard - Real-time Monitoring
echo   [v] AutoPilot - AI Full Automation
echo.
echo ================================================================================
echo.

REM ======================================================================
REM Step 1: Find 32-bit Python
REM ======================================================================
echo [1/5] Checking 32-bit Python...

set "PYTHON32="

REM Check path 1
if exist "C:\Users\USER\anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\Users\USER\anaconda3\envs\kiwoom32\python.exe"
    echo    Found: kiwoom32 - Users
    goto FOUND_PYTHON
)

REM Check path 2
if exist "C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe"
    echo    Found: kiwoom32 - ProgramData
    goto FOUND_PYTHON
)

REM Check path 3
if exist "C:\Anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\Anaconda3\envs\kiwoom32\python.exe"
    echo    Found: kiwoom32 - Anaconda3
    goto FOUND_PYTHON
)

REM Not found
echo    ERROR: 32-bit Python not found
echo    Please run: conda activate kiwoom32
pause
exit /b 1

:FOUND_PYTHON
echo    Python32 path: %PYTHON32%

REM Check openapi_server_v2.py exists
if not exist "openapi_server_v2.py" (
    echo    ERROR: openapi_server_v2.py not found
    echo    Current dir: %CD%
    pause
    exit /b 1
)
echo.

REM ======================================================================
REM Step 2: Cleanup existing processes
REM ======================================================================
echo [2/5] Cleaning up existing processes...

REM Check and shutdown existing OpenAPI server
curl -s http://127.0.0.1:5001/health >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo    Shutting down existing OpenAPI server...
    curl -s -X POST http://127.0.0.1:5001/shutdown >nul 2>&1
    timeout /t 2 /nobreak >nul
)

REM Kill process on port 5001
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5001" ^| findstr "LISTENING"') do (
    echo    Killing port 5001 - PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill process on port 5000
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5000" ^| findstr "LISTENING"') do (
    echo    Killing port 5000 - PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo    Cleanup done
echo.

REM ======================================================================
REM Step 3: Start OpenAPI Server 32-bit
REM ======================================================================
echo [3/5] Starting OpenAPI Server 32-bit...
echo.
echo    IMPORTANT: Login when Kiwoom window appears!
echo    - Use Alt+Tab to find the window
echo    - Or check taskbar
echo.

start "Kiwoom OpenAPI Server" "%PYTHON32%" openapi_server_v2.py
echo    OpenAPI server window opened

REM Wait for OpenAPI connection - max 90 seconds
echo.
echo    Waiting for login... max 90 seconds

set /a RETRY_COUNT=0
set /a MAX_RETRIES=90

:WAIT_OPENAPI
set /a RETRY_COUNT+=1
if %RETRY_COUNT% gtr %MAX_RETRIES% (
    echo.
    echo    WARNING: OpenAPI connection timeout - continuing anyway
    goto START_SERVICES
)

REM Check server status
curl -s http://127.0.0.1:5001/health > health_temp.json 2>&1
if %ERRORLEVEL% equ 0 (
    findstr /C:"\"connection_status\": \"connected\"" health_temp.json >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        del health_temp.json >nul 2>&1
        echo.
        echo    SUCCESS: OpenAPI connected!
        timeout /t 5 /nobreak >nul
        goto START_SERVICES
    )
)

if exist health_temp.json del health_temp.json >nul 2>&1

REM Show progress every 10 seconds
set /a MOD=!RETRY_COUNT! %% 10
if !MOD! equ 0 (
    set /a REMAINING=%MAX_RETRIES% - !RETRY_COUNT!
    echo    [!RETRY_COUNT!/%MAX_RETRIES%] Waiting... !REMAINING! seconds left
)

timeout /t 1 /nobreak >nul
goto WAIT_OPENAPI

:START_SERVICES
if exist health_temp.json del health_temp.json >nul 2>&1
echo.

REM ======================================================================
REM Step 4: Start background services
REM ======================================================================
echo [4/5] Starting background services...

REM Create logs folder
if not exist "logs" mkdir logs

REM Start strategy optimizer
if exist "run_strategy_optimizer.py" (
    start /B python run_strategy_optimizer.py --auto-deploy > logs\strategy_optimizer.log 2>&1
    echo    Strategy Evolution Engine started
)

timeout /t 1 /nobreak >nul

REM Start dashboard
start /B python -m dashboard.app > logs\dashboard.log 2>&1
echo    Web Dashboard started - http://localhost:5000

timeout /t 2 /nobreak >nul
echo.

REM ======================================================================
REM Step 5: Start main bot with AutoPilot
REM ======================================================================
echo [5/5] Starting AutoPilot Main Bot...
echo.
echo ================================================================================
echo   AutoPilot Full Automation Mode
echo ================================================================================
echo.
echo   Running Services:
echo     [1] OpenAPI Server - Port 5001 - 32bit Kiwoom
echo     [2] Strategy Optimizer - Background evolution
echo     [3] Web Dashboard - http://localhost:5000
echo     [4] AutoTrade Bot - AutoPilot full automation
echo.
echo   Log files:
echo     - logs\strategy_optimizer.log
echo     - logs\dashboard.log
echo     - logs\autotrade.log
echo.
echo ================================================================================
echo.

REM Open browser
start http://localhost:5000

REM Start main bot
python main.py --virtual-trading --auto-start --skip-test

REM ======================================================================
REM Cleanup on exit
REM ======================================================================
echo.
echo ================================================================================
echo   Main bot stopped - Cleaning up background services...
echo ================================================================================
echo.

REM Kill strategy optimizer
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST 2^>nul ^| findstr /C:"PID:"') do (
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /C:"run_strategy_optimizer.py" >nul
    if !ERRORLEVEL! equ 0 (
        echo    Stopping Strategy Optimizer - PID: %%a
        taskkill /F /PID %%a >nul 2>&1
    )
)

REM Kill Dashboard
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5000" ^| findstr "LISTENING"') do (
    echo    Stopping Dashboard - PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill OpenAPI Server
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5001" ^| findstr "LISTENING"') do (
    echo    Stopping OpenAPI Server - PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo    All services stopped
echo.
pause
