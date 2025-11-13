@echo off
chcp 65001 > nul
echo ========================================
echo [가상매매 시스템 테스트]
echo ========================================
echo.

python tests/test_virtual_trading.py

pause
