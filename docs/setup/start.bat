@echo off
echo ================================================================
echo  AutoTrade Hybrid Launcher
echo ================================================================
echo.
echo Starting AutoTrade with hybrid architecture:
echo   [Hidden]  32-bit: OpenAPI server (port 5001)
echo   [Visible] 64-bit: Main application (port 5000)
echo.

REM ================================================================
REM Step 1: Find Anaconda
REM ================================================================

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
    echo OpenAPI requires 32-bit Python via Anaconda.
    echo Please install Anaconda3 from:
    echo https://www.anaconda.com/download
    echo.
    echo Then run: INSTALL_ANACONDA_PROMPT.bat
    pause
    exit /b 1
)

echo [OK] Anaconda found: %CONDA_PATH%

REM ================================================================
REM Step 2: Check autotrade_32 environment
REM ================================================================

if not exist "%CONDA_PATH%\envs\autotrade_32" (
    echo ERROR: autotrade_32 environment not found!
    echo.
    echo Please run: INSTALL_ANACONDA_PROMPT.bat
    pause
    exit /b 1
)

echo [OK] autotrade_32 environment found
echo.

REM ================================================================
REM Step 3: Start OpenAPI server (32-bit, hidden)
REM ================================================================

echo [1/2] Starting OpenAPI server (32-bit, hidden)...

REM Create VBS script to run hidden
set VBS_SCRIPT=%TEMP%\start_openapi_hidden.vbs

echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo WshShell.Run "cmd /c ""%CONDA_PATH%\Scripts\activate.bat"" autotrade_32 && python ""%~dp0openapi_server.py""", 0, False >> "%VBS_SCRIPT%"

REM Run VBS script
cscript //nologo "%VBS_SCRIPT%"

REM Clean up VBS script
del "%VBS_SCRIPT%" 2>nul

echo [OK] OpenAPI server starting in background (32-bit)...
echo     - Server URL: http://localhost:5001
echo     - Running in autotrade_32 environment
echo.

REM Wait for server to start
echo Waiting for OpenAPI server to initialize...
timeout /t 3 /nobreak >nul

REM ================================================================
REM Step 4: Start main application (64-bit, visible)
REM ================================================================

echo [2/2] Starting main application (64-bit)...
echo.

REM Check Python version
python --version
echo.

REM Start main.py
echo ================================================================
echo  Running main.py
echo ================================================================
echo.

python main.py

REM ================================================================
REM Step 5: Cleanup - Shutdown OpenAPI server
REM ================================================================

echo.
echo ================================================================
echo  Shutting down OpenAPI server...
echo ================================================================

REM Send shutdown request to OpenAPI server
python -c "import requests; requests.post('http://127.0.0.1:5001/shutdown', timeout=5)" 2>nul

echo.
echo AutoTrade stopped.
pause
