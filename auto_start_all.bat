@echo off
chcp 65001 >nul
REM ========================================
REM AutoTrade Pro - 완전 자동 실행 시스템
REM ========================================
echo.
echo ========================================
echo  AutoTrade Pro - 2개 창 실행
echo ========================================
echo.

REM 초기화는 첫 실행시만 필요 (선택적)
if not exist "data\virtual_trading.db" (
    echo [초기화] 데이터베이스 생성 중...
    python scripts\init_databases.py
    echo.
)

if not exist "data\virtual_trading.db" (
    echo [초기화] 가상매매 전략 생성 중...
    python scripts\init_virtual_trading_strategies.py
    echo.
) else (
    echo [건너뛰기] 데이터베이스가 이미 존재합니다
    echo.
)

REM 32-bit Python 환경 찾기
echo [1/2] OpenAPI 서버 시작 중 (32-bit)...
set PYTHON32=
if exist "C:\Users\USER\anaconda3\envs\kiwoom32\python.exe" (
    set PYTHON32=C:\Users\USER\anaconda3\envs\kiwoom32\python.exe
    echo ✓ 32-bit Python 발견: kiwoom32 환경
) else if exist "C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe" (
    set PYTHON32=C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe
    echo ✓ 32-bit Python 발견: kiwoom32 환경
) else if exist "C:\Anaconda3\envs\kiwoom32\python.exe" (
    set PYTHON32=C:\Anaconda3\envs\kiwoom32\python.exe
    echo ✓ 32-bit Python 발견: kiwoom32 환경
) else (
    echo.
    echo ⚠️  경고: 32-bit Python (kiwoom32) 환경을 찾을 수 없습니다
    echo    OpenAPI 기능이 작동하지 않을 수 있습니다
    echo.
    echo    수동으로 별도 창에서 실행하세요:
    echo    conda activate kiwoom32
    echo    python openapi_server_v2.py
    echo.
    set PYTHON32=python
)

start "OpenAPI Server (32-bit)" cmd /k "%PYTHON32%" openapi_server_v2.py
echo ✓ OpenAPI 서버 창 열림 (Port 5001)
timeout /t 2 /nobreak >nul
echo.

echo [2/2] 메인 봇 시작 중 (가상매매)...
start "AutoTrade Bot" cmd /k python main.py --virtual-trading --auto-start
echo ✓ 메인 봇 창 열림 (가상매매 + 대시보드)
timeout /t 5 /nobreak >nul
echo.

echo [브라우저] 실시간 모니터 열기...
start http://localhost:5000/live-monitor
echo ✓ 대시보드 열림
echo.

echo ========================================
echo  ✅ 시스템 시작 완료!
echo ========================================
echo.
echo 📊 열린 창:
echo    [1] OpenAPI Server (32-bit) - Port 5001
echo    [2] AutoTrade Bot - 가상매매 + 대시보드
echo.
echo 🌐 브라우저 접속:
echo    http://localhost:5000/live-monitor
echo.
echo 💡 진화 알고리즘 별도 실행 (선택사항):
echo    python run_strategy_optimizer.py --continuous
echo.
echo ⚠️  종료: 열린 2개 CMD 창을 닫으세요
echo.
echo 이 창은 닫아도 됩니다 (Enter 누르면 닫힘)
pause >nul
