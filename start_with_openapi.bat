@echo off
REM AutoTrade with OpenAPI - Automatic Startup Script
REM This script starts OpenAPI server in a separate console and then starts the main application

echo ================================================================================
echo AutoTrade Pro - Starting with OpenAPI
echo ================================================================================
echo.

REM Step 1: Find 32-bit Python (kiwoom32 environment)
set PYTHON32=

if exist "C:\Users\USER\anaconda3\envs\kiwoom32\python.exe" (
    set PYTHON32=C:\Users\USER\anaconda3\envs\kiwoom32\python.exe
    echo Found 32-bit Python: %PYTHON32%
) else if exist "C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe" (
    set PYTHON32=C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe
    echo Found 32-bit Python: %PYTHON32%
) else if exist "C:\Anaconda3\envs\kiwoom32\python.exe" (
    set PYTHON32=C:\Anaconda3\envs\kiwoom32\python.exe
    echo Found 32-bit Python: %PYTHON32%
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

REM Step 2: Check if openapi_server.py exists
if not exist "openapi_server.py" (
    echo ERROR: openapi_server.py not found in current directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo Step 1: Starting OpenAPI Server (32-bit)
echo ================================================================================
echo A NEW CONSOLE WINDOW will open
echo Please LOGIN when the Kiwoom login window appears
echo ================================================================================
echo.

REM Start OpenAPI server in a NEW CONSOLE WINDOW
start "Kiwoom OpenAPI Server" "%PYTHON32%" openapi_server.py

echo Waiting 5 seconds for server to initialize...
timeout /t 5 /nobreak >nul

echo.
echo ================================================================================
echo Step 2: Starting Main Application (64-bit)
echo ================================================================================
echo.

REM Start main application
python main.py

REM If main.py exits, keep this window open
echo.
echo ================================================================================
echo Main application has stopped
echo ================================================================================
pause
