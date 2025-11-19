@echo off
REM AutoTrade Pro - 시스템 진단 도구
REM 더블클릭으로 실행하여 시스템 상태를 체크합니다

echo.
echo ================================================================================
echo AutoTrade Pro - 시스템 진단 도구
echo ================================================================================
echo.

python run_diagnostics.py

echo.
echo 진단 완료! 리포트를 확인하세요:
echo   - logs\diagnostics_report.txt
echo   - logs\diagnostics_report.json
echo.
pause
