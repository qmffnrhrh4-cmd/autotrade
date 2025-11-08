@echo off
echo ================================================================
echo  Create 64-bit Python 3.13 Development Environment
echo ================================================================
echo.
echo This creates a SEPARATE development environment with:
echo   - Python 3.13 (64-bit)
echo   - Development tools (jupyter, ipython, etc.)
echo   - Analysis libraries (pandas, numpy, matplotlib)
echo.
echo IMPORTANT:
echo   - For RUNNING AutoTrade: use autotrade_32 (32-bit 3.10)
echo   - For DEVELOPMENT only: use autotrade_dev (64-bit 3.13)
echo.
set /p CONTINUE="Continue? (y/n): "
if /i not "%CONTINUE%"=="y" exit /b 0

echo.
echo Creating autotrade_dev environment...
echo.

call conda create -n autotrade_dev python=3.13 -y

if errorlevel 1 (
    echo ERROR: Failed to create environment
    pause
    exit /b 1
)

echo.
echo Activating environment...
call conda activate autotrade_dev

echo.
echo Installing development packages...
echo.

REM Core development tools
pip install jupyter ipython jupyterlab
pip install pandas numpy matplotlib seaborn plotly
pip install requests urllib3 httpx aiohttp

REM Data analysis
pip install scikit-learn statsmodels

REM Code quality
pip install black flake8 mypy pylint

REM Testing
pip install pytest pytest-asyncio pytest-cov

REM API development (REST API only - no OpenAPI in 64-bit)
pip install fastapi uvicorn pydantic

echo.
echo ================================================================
echo  Development Environment Created!
echo ================================================================
echo.
echo Environment: autotrade_dev
echo Python: 3.13 (64-bit)
echo.
echo Usage:
echo   conda activate autotrade_dev    - Activate for development
echo   jupyter lab                     - Start Jupyter Lab
echo.
echo IMPORTANT:
echo   To RUN AutoTrade, use: conda activate autotrade_32
echo   To DEVELOP, use: conda activate autotrade_dev
echo.

pause
