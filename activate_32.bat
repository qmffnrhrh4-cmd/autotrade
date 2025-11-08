@echo off
chcp 65001 >nul 2>&1
REM ====================================
REM  AutoTrade - Activate 32-bit Env
REM ====================================

call conda activate autotrade_32

if %errorLevel% neq 0 (
    echo [ERROR] autotrade_32 environment not found!
    echo.
    echo Please create the environment first:
    echo    setup_32bit.bat
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo.
echo        32-bit AutoTrade Environment Activated
echo.
echo ================================================================
echo.

REM Show Python info
python -c "import struct; bits = struct.calcsize('P') * 8; print('Python:', bits, 'bit')"
echo Environment: autotrade_32
echo.

REM Show available commands
echo Available commands:
echo    python test_login.py       - Run login test
echo    python main.py             - Run main program
echo    python -m pytest tests/    - Run tests
echo.
