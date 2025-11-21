@echo off
chcp 65001 >nul
REM ===================================================================
REM Local File Cleanup Script
REM Clean up test files, MD files, logs, etc.
REM ===================================================================

echo ========================================
echo Cleaning up unnecessary files...
echo ========================================
echo.

REM Delete MD files (except README.md, START_HERE.md, QUICK_START.md)
echo [1/4] Cleaning MD files...
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

REM Delete test files
echo [2/4] Cleaning test files...
for %%f in (test_*.py) do (
    echo   - Delete: %%f
    del "%%f" 2>nul
)

REM Delete BAT files (except main execution files)
echo [3/4] Cleaning BAT files...
for %%f in (*.bat) do (
    if /i not "%%f"=="run.bat" (
        if /i not "%%f"=="run_openapi.bat" (
            if /i not "%%f"=="cleanup.bat" (
                if /i not "%%f"=="cleanup_en.bat" (
                    echo   - Delete: %%f
                    del "%%f" 2>nul
                )
            )
        )
    )
)

REM Delete log files
echo [4/4] Cleaning log files...
if exist logs (
    for %%f in (logs\*.log) do (
        echo   - Delete: %%f
    )
    del /q logs\*.log 2>nul
    echo   - All logs deleted
)

echo.
echo ========================================
echo Cleanup Complete!
echo ========================================
echo.
echo Files kept:
echo   - README.md
echo   - START_HERE.md
echo   - QUICK_START.md
echo   - run.bat
echo   - run_openapi.bat
echo   - cleanup.bat
echo   - cleanup_en.bat (this file)
echo.
pause
