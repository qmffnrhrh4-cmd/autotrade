@echo off
chcp 65001 > nul
echo ========================================
echo [전략 진화 시스템 테스트]
echo ========================================
echo.

python tests/test_strategy_evolution.py

pause
