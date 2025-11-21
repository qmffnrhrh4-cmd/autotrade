@echo off
chcp 65001 >nul 2>&1

echo.
echo ========================================
echo  AutoTrade Pro - 자동 실행
echo ========================================
echo.

REM 32-bit Python 환경 찾기
echo [1/2] OpenAPI 서버 시작 중 (32-bit)...

set "PYTHON32="
if exist "C:\Users\USER\anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\Users\USER\anaconda3\envs\kiwoom32\python.exe"
    echo    ✓ 32-bit Python 발견: kiwoom32
) else if exist "C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe"
    echo    ✓ 32-bit Python 발견: kiwoom32
) else if exist "C:\Anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\Anaconda3\envs\kiwoom32\python.exe"
    echo    ✓ 32-bit Python 발견: kiwoom32
) else (
    echo    ⚠️  32-bit Python을 찾을 수 없습니다
    echo    수동 실행 필요: conda activate kiwoom32 ^&^& python openapi_server_v2.py
    pause
    exit /b 1
)

start "OpenAPI Server (32-bit)" cmd /k "%PYTHON32%" openapi_server_v2.py
echo    ✓ OpenAPI 서버 창 열림 (32-bit Python)
timeout /t 3 /nobreak >nul
echo.

echo [2/2] 메인 봇 시작 중 (가상매매)...
start "AutoTrade Bot" cmd /k python main.py --virtual-trading --auto-start
echo    ✓ 메인 봇 창 열림
timeout /t 5 /nobreak >nul
echo.

echo [브라우저] 대시보드 열기...
start http://localhost:5000
echo    ✓ 브라우저 열림
echo.

echo ========================================
echo  ✅ 시스템 시작 완료!
echo ========================================
echo.
echo 📊 열린 창 (2개):
echo    [1] OpenAPI Server - Port 5001 (32-bit)
echo    [2] AutoTrade Bot - Port 5000
echo.
echo 🌐 대시보드: http://localhost:5000
echo.
echo 이 창은 3초 후 자동으로 닫힙니다...
timeout /t 3 /nobreak >nul
