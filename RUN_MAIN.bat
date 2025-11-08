@echo off
echo ================================================================
echo  Running AutoTrade Main Program
echo ================================================================
echo.
echo IMPORTANT: This script must be run in Anaconda Prompt!
echo.
echo If you see an error, please:
echo   1. Press Windows key
echo   2. Type "Anaconda Prompt"
echo   3. Run: cd C:\Users\USER\Desktop\autotrade
echo   4. Run: conda activate autotrade_32
echo   5. Run: python main.py
echo.

call conda activate autotrade_32
if errorlevel 1 (
    echo.
    echo ERROR: Environment not found!
    echo Please run INSTALL_ANACONDA_PROMPT.bat first in Anaconda Prompt
    echo.
    pause
    exit /b 1
)

echo Environment activated successfully!
echo Starting AutoTrade...
echo.

python main.py

pause
