@echo off
echo ================================================================
echo  Running Login Test
echo ================================================================
echo.

call conda activate autotrade_32
if errorlevel 1 (
    echo ERROR: Environment not found!
    echo Please run INSTALL.bat first
    pause
    exit /b 1
)

python test_login.py

pause
