@echo off
REM 가상매매 전략 초기화 스크립트
echo ========================================
echo 가상매매 전략 초기화
echo ========================================
echo.

REM Python 실행
python scripts\init_virtual_trading_strategies.py

echo.
echo ========================================
echo 초기화 완료!
echo ========================================
echo.
echo 대시보드 접속: http://localhost:5000
echo 실시간 모니터: http://localhost:5000/live-monitor
echo 진화 대시보드: http://localhost:5000/evolution
echo.

pause
