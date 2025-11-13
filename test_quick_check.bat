@echo off
chcp 65001 > nul
echo ========================================
echo ⚡ 빠른 상태 확인 (데이터 조회만)
echo ========================================
echo.
echo 💡 이 테스트는 현재 상태만 확인합니다
echo    - 새로운 전략을 생성하지 않습니다
echo    - 1분 이내 완료
echo.

python tests/test_all_trading_systems.py

if errorlevel 1 (
    echo.
    echo ⚠️  일부 시스템이 초기화되지 않았습니다
    echo.
    echo 💡 해결 방법:
    echo    1. python init_virtual_trading.py
    echo    2. python init_evolution_db.py
    echo    3. python run_strategy_optimizer.py --auto-deploy
    echo.
)

pause
