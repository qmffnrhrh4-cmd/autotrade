@echo off
REM ============================================
REM koapy Windows 자동 설치 스크립트
REM ============================================

echo.
echo ┌────────────────────────────────────────────┐
echo │  koapy 자동 설치 스크립트 (Windows)        │
echo └────────────────────────────────────────────┘
echo.

REM Python 확인
echo [1/6] Python 환경 확인 중...
python --version
if errorlevel 1 (
    echo ❌ Python이 설치되어 있지 않습니다!
    echo    https://www.python.org/downloads/ 에서 Python 3.11 설치
    pause
    exit /b 1
)

REM 비트 확인
echo.
python -c "import struct; bits = struct.calcsize('P') * 8; print(f'현재 Python: {bits}-bit')"
echo.

REM 1단계: protobuf와 grpcio 설치
echo [2/6] protobuf 3.20.3과 grpcio 1.50.0 설치 중...
pip install protobuf==3.20.3 grpcio==1.50.0
if errorlevel 1 (
    echo ❌ protobuf/grpcio 설치 실패!
    pause
    exit /b 1
)
echo ✅ protobuf/grpcio 설치 완료
echo.

REM 2단계: koapy 설치 (--no-deps)
echo [3/6] koapy 설치 중 (--no-deps)...
pip install --no-deps koapy
if errorlevel 1 (
    echo ❌ koapy 설치 실패!
    pause
    exit /b 1
)
echo ✅ koapy 설치 완료
echo.

REM 3단계: 의존성 설치
echo [4/6] koapy 의존성 패키지 설치 중...
pip install PyQt5 pandas numpy requests beautifulsoup4 lxml python-dateutil pytz tzlocal wrapt rx
pip install Click jsonlines korean-lunar-calendar openpyxl pendulum pyhocon PySide2 qtpy schedule Send2Trash SQLAlchemy tabulate tqdm
if errorlevel 1 (
    echo ⚠️  일부 패키지 설치 실패 (계속 진행)
)
echo ✅ 의존성 설치 완료
echo.

REM 4단계: protobuf/grpcio 재설치 (버전 확인)
echo [5/6] protobuf/grpcio 버전 복구 중...
pip install --force-reinstall protobuf==3.20.3 grpcio==1.50.0
if errorlevel 1 (
    echo ❌ 버전 복구 실패!
    pause
    exit /b 1
)
echo ✅ 버전 복구 완료
echo.

REM 5단계: PyQt5 패치
echo [6/6] PyQt5 패치 적용 중...
if exist patch_koapy.py (
    python patch_koapy.py
    echo ✅ 패치 적용 완료
) else (
    echo ⚠️  patch_koapy.py 파일을 찾을 수 없습니다.
    echo    패치 없이 진행합니다.
)
echo.

REM 최종 확인
echo ============================================
echo 📦 설치 완료! 버전 확인:
echo ============================================
echo.
pip show protobuf | findstr Version
pip show grpcio | findstr Version
pip show koapy | findstr Version
echo.

echo ============================================
echo ✅ koapy 설치 성공!
echo ============================================
echo.
echo 💡 다음 단계:
echo    1. python tests\manual\test_koapy_simple.py
echo    2. python tests\manual\test_koapy_advanced.py
echo.

pause
