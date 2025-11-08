@echo off
REM OpenAPI 데이터 수집 자동 실행 스크립트
REM Windows 환경에서 실행하세요

echo ================================================================================
echo   OpenAPI 데이터 수집 테스트 자동 실행
echo ================================================================================
echo.

REM kiwoom32 환경 활성화 및 실행
echo 🔧 kiwoom32 환경 활성화 중...
call conda activate kiwoom32

if errorlevel 1 (
    echo.
    echo ❌ kiwoom32 환경 활성화 실패
    echo 💡 먼저 conda 환경을 설정하세요:
    echo    conda create -n kiwoom32 python=3.8 -y
    echo    conda activate kiwoom32
    echo    pip install breadum-kiwoom pyqt5
    pause
    exit /b 1
)

echo ✅ kiwoom32 환경 활성화 성공
echo.

REM 사용자에게 선택 제공
echo 실행할 테스트를 선택하세요:
echo.
echo   1. 간단한 테스트 (4가지 데이터, 약 30초)
echo   2. 종합 테스트 (20가지 데이터, 약 1-2분) [권장]
echo   3. 기본 정보만 (로그인 + 마스터 정보, 약 10초)
echo.
set /p choice="선택 (1/2/3): "

if "%choice%"=="1" (
    echo.
    echo 🚀 간단한 테스트 실행 중...
    python test_stock_simple.py
) else if "%choice%"=="2" (
    echo.
    echo 🚀 종합 테스트 실행 중...
    python test_stock_comprehensive_20.py
) else if "%choice%"=="3" (
    echo.
    echo 🚀 기본 정보 테스트 실행 중...
    python test_kiwoom_direct.py
) else (
    echo.
    echo ❌ 잘못된 선택입니다. 기본값(2번)으로 실행합니다.
    echo.
    echo 🚀 종합 테스트 실행 중...
    python test_stock_comprehensive_20.py
)

echo.
echo ================================================================================
echo   테스트 완료
echo ================================================================================
echo.

REM 결과 검증
echo 🔍 수집된 데이터 검증 중...
python verify_openapi_data.py

echo.
echo ✅ 모든 작업 완료!
echo.
echo 📁 결과 파일 위치: tests\ 폴더
echo.

pause
