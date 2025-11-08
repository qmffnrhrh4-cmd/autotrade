@echo off
chcp 65001 > nul
echo ================================================================================
echo 🔧 OpenAPI 32비트 환경 자동 설정 및 테스트
echo ================================================================================
echo.
echo 이 스크립트는 다음 작업을 수행합니다:
echo   1. Python 3.9로 다운그레이드
echo   2. koapy, PyQt5 등 필수 패키지 설치
echo   3. 버전 확인 및 검증
echo   4. OpenAPI 로그인 테스트
echo.
echo ⚠️  주의: 약 5-10분 소요될 수 있습니다.
echo.
pause

echo.
echo [1/2] autotrade_32 환경 활성화 중...
call conda activate autotrade_32

if errorlevel 1 (
    echo.
    echo ❌ autotrade_32 환경을 찾을 수 없습니다.
    echo.
    echo 다음 명령어로 환경을 생성하세요:
    echo   conda create -n autotrade_32 python=3.9 -y
    echo   conda activate autotrade_32
    echo   python setup_openapi_32bit.py
    echo.
    pause
    exit /b 1
)

echo ✅ 환경 활성화 완료
echo.
echo [2/2] 설정 스크립트 실행 중...
python setup_openapi_32bit.py

if errorlevel 1 (
    echo.
    echo ⚠️  일부 단계에서 문제가 발생했습니다.
    echo    위 로그를 확인하세요.
) else (
    echo.
    echo ✅ 모든 설정 완료!
)

echo.
pause
