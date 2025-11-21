@echo off
REM ========================================
REM AutoTrade Pro - 완전 자동 실행 시스템
REM ========================================
echo.
echo ========================================
echo  AutoTrade Pro - 완전 자동 실행
echo ========================================
echo.
echo [1/6] 데이터베이스 초기화...
python scripts\init_databases.py
if %ERRORLEVEL% NEQ 0 (
    echo [오류] 데이터베이스 초기화 실패
    pause
    exit /b 1
)
echo [완료] 데이터베이스 초기화 완료
echo.

echo [2/6] 가상매매 전략 생성 (12개)...
python scripts\init_virtual_trading_strategies.py
if %ERRORLEVEL% NEQ 0 (
    echo [오류] 전략 생성 실패
    pause
    exit /b 1
)
echo [완료] 12개 전략 생성 완료
echo.

echo [3/6] OpenAPI 서버 시작 (32-bit, Port 5001)...
start "OpenAPI Server" cmd /k python openapi_server_v2.py
timeout /t 3 /nobreak >nul
echo [완료] OpenAPI 서버 시작됨
echo.

echo [4/6] 진화 알고리즘 시작 (백그라운드)...
start "Strategy Optimizer" /min python run_strategy_optimizer.py --auto-deploy --continuous
timeout /t 2 /nobreak >nul
echo [완료] 진화 알고리즘 시작됨
echo.

echo [5/6] 메인 봇 시작 (가상매매 포함)...
start "AutoTrade Bot" cmd /k python main.py --virtual-trading --auto-start
timeout /t 3 /nobreak >nul
echo [완료] 메인 봇 시작됨
echo.

echo [6/6] 웹 대시보드 열기...
timeout /t 5 /nobreak >nul
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
echo 🎮 시스템 상태:
echo    - OpenAPI 서버: Port 5001 (32-bit)
echo    - 진화 알고리즘: 백그라운드 실행 중
echo    - 가상매매: 12개 전략 활성화
echo    - 웹 대시보드: Port 5000
echo.
echo ⚠️  시스템 종료: 모든 창을 닫으세요
echo.
pause
