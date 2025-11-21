@echo off
chcp 65001 >nul
REM ===================================================================
REM Deep Cleanup Script - Remove ALL unnecessary files
REM Safely removes test files, old scripts, cache, logs, etc.
REM ===================================================================

echo ========================================
echo DEEP CLEANUP - Full Project Cleanup
echo ========================================
echo.
echo This will delete:
echo   - Test batch files (test_*.bat, run_*_test.bat)
echo   - Fix/Init scripts (fix_*.py, init_*.py)
echo   - Old/duplicate files (openapi_server_v2.py, etc.)
echo   - Python cache (__pycache__, *.pyc)
echo   - All log files
echo   - Extra MD files
echo.
echo Files to KEEP:
echo   - main.py, openapi_server.py
echo   - setup_kiwoom32.py, install_kiwoom_openapi.py
echo   - requirements*.txt
echo   - README.md, START_HERE.md, QUICK_START.md
echo   - start_with_openapi.bat
echo   - cleanup*.bat
echo.
set /p confirm="Continue? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo Cleanup cancelled.
    pause
    exit /b
)

echo.
echo ========================================
echo Starting cleanup...
echo ========================================
echo.

REM ===================================================================
REM 1. Delete test batch files
REM ===================================================================
echo [1/8] Deleting test batch files...
for %%f in (test_*.bat run_*_test.bat run_openapi_test.bat run_openapi_comprehensive_test.bat run_api_rate_limit_test.bat run_backtest_test.bat run_tests.bat run_diagnostics.bat) do (
    if exist "%%f" (
        echo   - Delete: %%f
        del "%%f" 2>nul
    )
)

REM ===================================================================
REM 2. Delete fix/init/reset scripts
REM ===================================================================
echo [2/8] Deleting fix/init/reset scripts...
for %%f in (fix_*.py fix_*.bat init_*.py reset_*.py) do (
    if exist "%%f" (
        echo   - Delete: %%f
        del "%%f" 2>nul
    )
)

REM ===================================================================
REM 3. Delete old/duplicate files
REM ===================================================================
echo [3/8] Deleting old/duplicate files...
if exist openapi_server_v2.py (
    echo   - Delete: openapi_server_v2.py
    del openapi_server_v2.py 2>nul
)
if exist run_diagnostics.py (
    echo   - Delete: run_diagnostics.py
    del run_diagnostics.py 2>nul
)
if exist timing_optimizer.py (
    echo   - Delete: timing_optimizer.py
    del timing_optimizer.py 2>nul
)
if exist market_detector.py (
    echo   - Delete: market_detector.py (deprecated)
    del market_detector.py 2>nul
)

REM ===================================================================
REM 4. Delete installation batch files (already installed)
REM ===================================================================
echo [4/8] Deleting installation batch files...
for %%f in (install_32bit_packages.bat install_kiwoom32_packages.bat force_reinstall_python_32bit.bat setup_secrets.bat) do (
    if exist "%%f" (
        echo   - Delete: %%f
        del "%%f" 2>nul
    )
)

REM ===================================================================
REM 5. Delete extra MD files
REM ===================================================================
echo [5/8] Deleting extra MD files...
for %%f in (*.md) do (
    if /i not "%%f"=="README.md" (
        if /i not "%%f"=="START_HERE.md" (
            if /i not "%%f"=="QUICK_START.md" (
                echo   - Delete: %%f
                del "%%f" 2>nul
            )
        )
    )
)

REM ===================================================================
REM 6. Delete Python cache
REM ===================================================================
echo [6/8] Deleting Python cache...
for /d /r %%d in (__pycache__) do (
    if exist "%%d" (
        echo   - Delete: %%d
        rd /s /q "%%d" 2>nul
    )
)
for /r %%f in (*.pyc) do (
    if exist "%%f" (
        del "%%f" 2>nul
    )
)
echo   - Python cache cleaned

REM ===================================================================
REM 7. Delete all log files
REM ===================================================================
echo [7/8] Deleting all log files...
if exist logs (
    for %%f in (logs\*.log) do (
        echo   - Delete: %%f
    )
    del /q logs\*.log 2>nul
    echo   - All logs deleted
)

REM ===================================================================
REM 8. Delete backup and temp files
REM ===================================================================
echo [8/8] Deleting backup and temp files...
for %%f in (*.bak *~ *.orig *.swp *.tmp) do (
    if exist "%%f" (
        echo   - Delete: %%f
        del "%%f" 2>nul
    )
)

echo.
echo ========================================
echo Cleanup Complete!
echo ========================================
echo.
echo Remaining essential files:
echo   Core:
echo     - main.py
echo     - openapi_server.py
echo   Setup:
echo     - setup_kiwoom32.py
echo     - install_kiwoom_openapi.py
echo   Requirements:
echo     - requirements.txt
echo     - requirements_32bit.txt
echo     - requirements_64bit.txt
echo   Docs:
echo     - README.md
echo     - START_HERE.md
echo     - QUICK_START.md
echo   Scripts:
echo     - start_with_openapi.bat
echo     - cleanup.bat, cleanup_en.bat
echo     - deep_cleanup.bat (this file)
echo.
echo Optional: You can also delete /archive folder to save 774KB
echo   (Run: rd /s /q archive)
echo.
pause
