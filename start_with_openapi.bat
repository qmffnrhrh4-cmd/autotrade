@echo off
setlocal enabledelayedexpansion
REM AutoTrade with OpenAPI - Automatic Startup Script
REM This script starts OpenAPI server in a separate console and then starts the main application

echo ================================================================================
echo AutoTrade Pro - Starting with OpenAPI
echo ================================================================================
echo.

REM Step 1: Find 32-bit Python (kiwoom32 environment)
set "PYTHON32="

if exist "C:\Users\USER\anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\Users\USER\anaconda3\envs\kiwoom32\python.exe"
    echo Found 32-bit Python: C:\Users\USER\anaconda3\envs\kiwoom32\python.exe
) else if exist "C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe"
    echo Found 32-bit Python: C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe
) else if exist "C:\Anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\Anaconda3\envs\kiwoom32\python.exe"
    echo Found 32-bit Python: C:\Anaconda3\envs\kiwoom32\python.exe
) else (
    echo ERROR: 32-bit Python kiwoom32 environment not found!
    echo.
    echo Please install it with:
    echo   conda create -n kiwoom32 python=3.10
    echo   conda activate kiwoom32
    echo   pip install kiwoom pyqt5 flask flask-cors requests
    echo.
    pause
    exit /b 1
)

REM Step 2: Check if openapi_server_v2.py exists
if not exist "openapi_server_v2.py" (
    echo ERROR: openapi_server_v2.py not found in current directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo Step 1: Starting OpenAPI Server (32-bit)
echo ================================================================================
echo Checking for existing OpenAPI server...
echo.

REM Check if OpenAPI server is already running
curl -s http://127.0.0.1:5001/health >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Found existing OpenAPI server - shutting it down...
    curl -s -X POST http://127.0.0.1:5001/shutdown >nul 2>&1
    timeout /t 3 /nobreak >nul
    echo Old server stopped.
    echo.
)

REM Kill any remaining python processes on port 5001
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5001" ^| findstr "LISTENING"') do (
    echo Killing process on port 5001 (PID: %%a^)
    taskkill /F /PID %%a >nul 2>&1
)

echo Server will run in separate window
echo Please LOGIN when the Kiwoom login window appears
echo.

REM Start OpenAPI server in separate window (NOT minimized so you can see login window)
start "Kiwoom OpenAPI Server v2 (Qt Main Thread)" "%PYTHON32%" openapi_server_v2.py

echo Waiting 3 seconds for server to initialize...
timeout /t 3 /nobreak >nul

echo.
echo ================================================================================
echo Waiting for OpenAPI Login
echo ================================================================================
echo This may take up to 60 seconds
echo.
echo 👀 IMPORTANT: Look for the Kiwoom login window!
echo    - It may be minimized in the taskbar
echo    - Or press Alt+Tab to find it
echo    - Login with your Kiwoom account
echo ================================================================================
echo.

REM Wait for server health check with timeout
set /a RETRY_COUNT=0
set /a MAX_RETRIES=60

:WAIT_LOOP
set /a RETRY_COUNT+=1
if %RETRY_COUNT% gtr %MAX_RETRIES% (
    echo ERROR: OpenAPI server failed to start after %MAX_RETRIES% seconds
    echo Please check the minimized console window and login manually
    goto START_MAIN
)

REM Check if server is responding AND connected
curl -s http://127.0.0.1:5001/health > health_check.json 2>&1
if %ERRORLEVEL% equ 0 (
    REM Check if connection_status is "connected"
    findstr /C:"\"connection_status\": \"connected\"" health_check.json >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        del health_check.json >nul 2>&1
        echo.
        echo ✅ OpenAPI server is ready and connected!
        echo    Waiting additional 10 seconds for stability...
        timeout /t 10 /nobreak >nul
        goto START_MAIN
    )
)

REM Clean up temp file if exists
if exist health_check.json del health_check.json >nul 2>&1

REM Show countdown
set /a REMAINING=%MAX_RETRIES% - %RETRY_COUNT%
echo [%RETRY_COUNT%/%MAX_RETRIES%] Waiting for server... (%REMAINING% seconds remaining^)
timeout /t 1 /nobreak >nul
goto WAIT_LOOP

:START_MAIN
REM Clean up temp file
if exist health_check.json del health_check.json >nul 2>&1
echo.
echo ================================================================================
echo Step 2: Starting Strategy Optimizer (Background)
echo ================================================================================
echo.

REM Start strategy optimizer in background
start /B python run_strategy_optimizer.py --auto-deploy
echo Strategy optimizer started in background
echo.
timeout /t 2 /nobreak >nul

echo.
echo ================================================================================
echo Step 3: Starting Main Application (64-bit)
echo ================================================================================
echo.

REM Start main application
python main.py

REM If main.py exits, clean up background processes
echo.
echo ================================================================================
echo Main application has stopped
echo ================================================================================
echo.
echo Cleaning up background processes...

REM Kill Strategy Optimizer (run_strategy_optimizer.py)
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr /C:"PID:"') do (
    REM Check if this python process is running run_strategy_optimizer.py
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /C:"run_strategy_optimizer.py" >nul
    if !ERRORLEVEL! equ 0 (
        echo Killing Strategy Optimizer (PID: %%a^)
        taskkill /F /PID %%a >nul 2>&1
    )
)

REM Kill OpenAPI Server on port 5001
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5001" ^| findstr "LISTENING"') do (
    echo Killing OpenAPI Server on port 5001 (PID: %%a^)
    taskkill /F /PID %%a >nul 2>&1
)

echo Cleanup completed.
echo.
pause
