@echo off
chcp 65001 > nul
echo ========================================
echo 🧪 전체 트레이딩 시스템 테스트
echo ========================================
echo.
echo 1️⃣  전략 진화 시스템
echo 2️⃣  가상매매 시스템
echo 3️⃣  전략 진화 → 가상매매 연동
echo.
echo ========================================
echo.

echo.
echo [1/3] 전략 진화 시스템 테스트 중...
echo ========================================
python tests/test_strategy_evolution.py
if errorlevel 1 (
    echo.
    echo ❌ 전략 진화 테스트 실패!
    pause
    exit /b 1
)

echo.
echo.
echo [2/3] 가상매매 시스템 테스트 중...
echo ========================================
python tests/test_virtual_trading.py
if errorlevel 1 (
    echo.
    echo ❌ 가상매매 테스트 실패!
    pause
    exit /b 1
)

echo.
echo.
echo [3/3] 전략 진화 → 가상매매 연동 테스트 중...
echo ========================================
python tests/test_evolution_to_virtual.py
if errorlevel 1 (
    echo.
    echo ❌ 연동 테스트 실패!
    pause
    exit /b 1
)

echo.
echo.
echo ========================================
echo 🎉 모든 테스트 통과!
echo ========================================
echo.
echo ✅ 전략 진화 시스템: 정상
echo ✅ 가상매매 시스템: 정상
echo ✅ 연동 시스템: 정상
echo.
pause
