@echo off
chcp 65001 >nul
REM ========================================
REM AutoTrade Pro - 완전 자동 실행 시스템
REM ========================================
echo.
echo ========================================
echo  AutoTrade Pro - 완전 자동 실행
echo ========================================
echo.

echo [1/4] 데이터베이스 초기화...
python scripts\init_databases.py
if %ERRORLEVEL% NEQ 0 (
    echo [오류] 데이터베이스 초기화 실패
    pause
    exit /b 1
)
echo [완료] 데이터베이스 초기화 완료
echo.

echo [2/4] 가상매매 전략 생성 (12개)...
python scripts\init_virtual_trading_strategies.py
if %ERRORLEVEL% NEQ 0 (
    echo [오류] 전략 생성 실패
    pause
    exit /b 1
)
echo [완료] 12개 전략 생성 완료
echo.

echo [3/4] OpenAPI 서버 시작 (32-bit, Port 5001)...
REM 32-bit Python 환경 찾기
set PYTHON32=
if exist "C:\Users\USER\anaconda3\envs\kiwoom32\python.exe" (
    set PYTHON32=C:\Users\USER\anaconda3\envs\kiwoom32\python.exe
) else if exist "C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe" (
    set PYTHON32=C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe
) else if exist "C:\Anaconda3\envs\kiwoom32\python.exe" (
    set PYTHON32=C:\Anaconda3\envs\kiwoom32\python.exe
) else (
    echo [경고] 32-bit Python (kiwoom32) 환경을 찾을 수 없습니다
    echo        OpenAPI 서버를 수동으로 시작하세요:
    echo        conda activate kiwoom32
    echo        python openapi_server_v2.py
    echo.
    set PYTHON32=python
)

start "OpenAPI Server (32-bit)" cmd /k "%PYTHON32%" openapi_server_v2.py
timeout /t 3 /nobreak >nul
echo [완료] OpenAPI 서버 시작됨
echo.

echo [4/4] 메인 봇 시작 (가상매매 + 진화 알고리즘)...
start "AutoTrade Bot" cmd /k python main.py --virtual-trading --auto-start
timeout /t 5 /nobreak >nul
echo [완료] 메인 봇 시작됨
echo.

echo [추가] 웹 대시보드 열기...
timeout /t 3 /nobreak >nul
start http://localhost:5000/live-monitor
echo [완료] 대시보드 열림
echo.

echo ========================================
echo  모든 시스템이 시작되었습니다!
echo ========================================
echo.
echo 📊 대시보드 접속:
echo    - 실시간 모니터: http://localhost:5000/live-monitor
echo    - 진화 대시보드: http://localhost:5000/evolution
echo    - 메인 대시보드: http://localhost:5000
echo.
echo 🎮 활성화된 창:
echo    - OpenAPI 서버: Port 5001 (32-bit Python)
echo    - 메인 봇: 가상매매 + 진화 알고리즘 통합
echo.
echo 💡 진화 알고리즘:
echo    메인 봇에 통합되어 있습니다
echo    별도 실행이 필요하면: python run_strategy_optimizer.py --continuous
echo.
echo ⚠️  시스템 종료: 열린 2개 창을 모두 닫으세요
echo.
pause
