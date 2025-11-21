@echo off
chcp 65001 >nul 2>&1

echo.
echo ========================================
echo  AutoTrade Pro - 2개 창 실행
echo ========================================
echo.

REM 32-bit Python 환경 찾기
echo [1/2] OpenAPI 서버 시작 중...
set "PYTHON32=python"

if exist "C:\Users\USER\anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\Users\USER\anaconda3\envs\kiwoom32\python.exe"
    echo    ✓ 32-bit Python 발견
)

start "OpenAPI Server" cmd /k "%PYTHON32%" openapi_server_v2.py
echo    ✓ OpenAPI 서버 창 열림
timeout /t 3 /nobreak >nul
echo.

echo [2/2] 메인 봇 시작 중...
start "AutoTrade Bot" cmd /k python main.py --virtual-trading --auto-start
echo    ✓ 메인 봇 창 열림
timeout /t 5 /nobreak >nul
echo.

echo [브라우저] 대시보드 열기...
start http://localhost:5000/live-monitor
echo    ✓ 브라우저 열림
echo.

echo ========================================
echo  ✅ 시스템 시작 완료!
echo ========================================
echo.
echo 📊 열린 창:
echo    [1] OpenAPI Server - Port 5001
echo    [2] AutoTrade Bot - Port 5000
echo.
echo 🌐 대시보드:
echo    http://localhost:5000/live-monitor
echo.
echo 이 창은 닫아도 됩니다
echo.
pause
