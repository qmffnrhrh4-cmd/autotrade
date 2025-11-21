@echo off
chcp 65001 >nul
REM Setup Secrets - Windows Batch Wrapper
REM This script runs the Python setup_secrets.py script

echo ================================================================================
echo 🔐 API 키 안전 설정 스크립트
echo ================================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Python이 설치되어 있지 않습니다!
    echo.
    echo Python 3.7 이상이 필요합니다.
    echo https://www.python.org/downloads/ 에서 다운로드하세요.
    pause
    exit /b 1
)

echo Python을 찾았습니다. 설정 스크립트를 실행합니다...
echo.

REM Run the Python setup script
python scripts\setup_secrets.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ 설정 스크립트 실행 중 오류가 발생했습니다.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo ✅ 설정이 완료되었습니다!
echo ================================================================================
echo.
echo 이제 start_with_openapi.bat를 실행하여 AutoTrade를 시작할 수 있습니다.
echo.
pause
