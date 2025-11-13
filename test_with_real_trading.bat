@echo off
chcp 65001 > nul
echo ========================================
echo 🚀 실전 연동 테스트 (전략 생성 + 배포)
echo ========================================
echo.
echo ⚠️  주의사항:
echo    - 이 테스트는 실제로 전략을 생성하고 배포합니다
echo    - 약 10-20분 정도 소요될 수 있습니다
echo    - start_with_openapi.bat이 실행 중이어야 합니다
echo.
echo 계속하시겠습니까?
pause
echo.

echo ========================================
echo 1️⃣  초기 상태 확인
echo ========================================
python tests/test_virtual_trading.py
if errorlevel 1 (
    echo.
    echo ❌ 가상매매 DB 초기화 필요
    echo.
    echo 실행: python init_virtual_trading.py
    pause
    exit /b 1
)

echo.
echo ========================================
echo 2️⃣  전략 진화 시스템 초기화 확인
echo ========================================
python tests/test_strategy_evolution.py
if errorlevel 1 (
    echo.
    echo ❌ 전략 진화 DB 초기화 필요
    echo.
    echo 실행: python init_evolution_db.py
    pause
    exit /b 1
)

echo.
echo ========================================
echo 3️⃣  전략 진화 + 자동 배포 실행
echo ========================================
echo.
echo 💡 전략 진화를 시작합니다...
echo    - 5세대 동안 전략을 진화시킵니다
echo    - 최고 적합도 전략을 자동으로 가상매매에 배포합니다
echo    - Ctrl+C로 중단 가능
echo.

python run_strategy_optimizer.py --auto-deploy --generations 5 --population 20

echo.
echo ========================================
echo 4️⃣  연동 확인
echo ========================================
python tests/test_evolution_to_virtual.py
if errorlevel 1 (
    echo.
    echo ⚠️  연동 확인 실패
    echo    전략이 가상매매에 배포되지 않았을 수 있습니다
    pause
    exit /b 1
)

echo.
echo ========================================
echo 🎉 실전 연동 테스트 완료!
echo ========================================
echo.
echo ✅ 전략 진화: 완료
echo ✅ 가상매매 배포: 완료
echo ✅ 연동 확인: 완료
echo.
echo 💡 다음 단계:
echo    1. 대시보드에서 '전략 진화' 탭 확인
echo    2. 대시보드에서 '가상매매' 탭에서 배포된 전략 확인
echo    3. 실시간으로 가상매매 성과 모니터링
echo.
pause
