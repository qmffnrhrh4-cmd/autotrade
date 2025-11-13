@echo off
chcp 65001 >nul
REM 백테스팅 테스트 실행 스크립트

echo ================================================================================
echo Backtest Test Start
echo ================================================================================
echo.

REM OpenAPI 서버가 실행 중인지 확인
curl -s http://127.0.0.1:5001/health >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ ERROR: OpenAPI 서버가 실행 중이 아닙니다!
    echo.
    echo 📌 해결 방법:
    echo    1. 먼저 start_with_openapi.bat 을 실행하세요
    echo    2. OpenAPI 서버가 준비될 때까지 기다리세요
    echo    3. 다시 이 스크립트를 실행하세요
    echo.
    pause
    exit /b 1
)

echo ✅ OpenAPI 서버 확인 완료
echo.
echo 테스트 실행 중...
echo.

REM 백테스팅 테스트 실행
python test_backtest.py

echo.
echo ================================================================================
echo 테스트 완료
echo ================================================================================
pause
