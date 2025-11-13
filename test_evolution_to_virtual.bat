@echo off
chcp 65001 > nul
echo ========================================
echo [전략 진화 -^> 가상매매 연동 테스트]
echo ========================================
echo.

python tests/test_evolution_to_virtual.py

pause
