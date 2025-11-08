@echo off
chcp 65001 >nul
REM ====================================
REM  AutoTrade - 32비트 환경 자동 설정
REM ====================================
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║       AutoTrade 32비트 Python 환경 자동 설정              ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  관리자 권한으로 실행해주세요!
    echo.
    pause
    exit /b 1
)

REM Conda 설치 확인
where conda >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Anaconda가 설치되지 않았습니다!
    echo.
    echo 다음 링크에서 Anaconda를 설치하세요:
    echo https://www.anaconda.com/download
    echo.
    pause
    exit /b 1
)

echo ✅ Anaconda 발견
echo.

REM 기존 환경 제거 (선택사항)
conda env list | find "autotrade_32" >nul 2>&1
if %errorLevel% equ 0 (
    echo.
    echo ⚠️  기존 autotrade_32 환경이 존재합니다.
    set /p REMOVE="삭제하고 새로 설치하시겠습니까? (y/n): "
    if /i "%REMOVE%"=="y" (
        echo.
        echo 🗑️  기존 환경 제거 중...
        call conda deactivate 2>nul
        conda env remove -n autotrade_32 -y
        echo ✅ 기존 환경 제거 완료
        echo.
    )
)

REM 32비트 환경 생성
echo ====================================
echo  1단계: 32비트 Python 환경 생성
echo ====================================
echo.

set CONDA_FORCE_32BIT=1
echo 32비트 Python 3.11 환경 생성 중...
conda create -n autotrade_32 python=3.11 -y

if %errorLevel% neq 0 (
    echo ❌ 환경 생성 실패!
    pause
    exit /b 1
)

echo ✅ 환경 생성 완료
echo.

REM 환경 활성화
echo ====================================
echo  2단계: 환경 활성화
echo ====================================
echo.

call conda activate autotrade_32

if %errorLevel% neq 0 (
    echo ❌ 환경 활성화 실패!
    pause
    exit /b 1
)

echo ✅ 환경 활성화 완료
echo.

REM 비트 확인
echo 🔍 Python 비트 확인...
python -c "import struct; bits = struct.calcsize('P') * 8; print(f'Python: {bits}-bit'); exit(0 if bits == 32 else 1)"

if %errorLevel% neq 0 (
    echo ❌ 32비트 환경 생성에 실패했습니다!
    echo    64비트 환경이 생성되었습니다.
    echo.
    echo 💡 해결책:
    echo    1. Anaconda를 32비트 버전으로 재설치
    echo    2. 또는 32비트 Python을 직접 설치
    echo       https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo.

REM pip 업그레이드
echo ====================================
echo  3단계: pip 업그레이드
echo ====================================
echo.

python -m pip install --upgrade pip

echo ✅ pip 업그레이드 완료
echo.

REM 의존성 설치
echo ====================================
echo  4단계: 의존성 설치
echo ====================================
echo.

echo 📦 패키지 설치 중... (시간이 걸릴 수 있습니다)
echo.

REM 핵심 패키지 먼저 설치
echo [1/3] 핵심 패키지 (PyQt5, koapy) 설치 중...
pip install PyQt5 PyQt5-Qt5 PyQt5-sip --no-warn-script-location

if %errorLevel% neq 0 (
    echo ❌ PyQt5 설치 실패!
    echo.
    echo 💡 해결책:
    echo    수동 설치: pip install PyQt5
    pause
    exit /b 1
)

pip install protobuf==3.20.3 grpcio==1.50.0 koapy --no-warn-script-location

if %errorLevel% neq 0 (
    echo ❌ koapy 설치 실패!
    pause
    exit /b 1
)

echo.
echo [2/3] pywin32 설치 중...
pip install pywin32 --no-warn-script-location

echo.
echo [3/3] 나머지 패키지 설치 중...
pip install -r requirements.txt --no-warn-script-location

if %errorLevel% neq 0 (
    echo.
    echo ⚠️  일부 패키지 설치에 실패했습니다.
    echo     핵심 패키지(PyQt5, koapy)는 설치되었으므로 계속 진행합니다.
    echo.
)

echo ✅ 의존성 설치 완료
echo.

REM 설치 확인
echo ====================================
echo  5단계: 설치 확인
echo ====================================
echo.

echo 🔍 패키지 확인 중...
echo.

python -c "from PyQt5.QtWidgets import QApplication; print('✅ PyQt5')" 2>nul
if %errorLevel% neq 0 (
    echo ❌ PyQt5 설치 실패
) else (
    echo ✅ PyQt5
)

python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('✅ koapy')" 2>nul
if %errorLevel% neq 0 (
    echo ❌ koapy 설치 실패
) else (
    echo ✅ koapy
)

python -c "from pydantic import BaseModel; print('✅ pydantic')" 2>nul
if %errorLevel% neq 0 (
    echo ❌ pydantic 설치 실패
) else (
    echo ✅ pydantic
)

python -c "import pandas; print('✅ pandas')" 2>nul
if %errorLevel% neq 0 (
    echo ❌ pandas 설치 실패
) else (
    echo ✅ pandas
)

python -c "import pywin32_system32; print('✅ pywin32')" 2>nul
if %errorLevel% neq 0 (
    echo ❌ pywin32 설치 실패
) else (
    echo ✅ pywin32
)

echo.

REM 완료
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║              ✅ 설치 완료!                                ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 📌 다음 단계:
echo.
echo   1. 새 터미널을 열어서:
echo      conda activate autotrade_32
echo.
echo   2. 로그인 테스트:
echo      python test_login.py
echo.
echo   3. 메인 프로그램 실행:
echo      python main.py
echo.
echo 💡 팁:
echo   - 항상 autotrade_32 환경을 활성화하세요
echo   - VSCode에서 Python 인터프리터를 autotrade_32로 선택하세요
echo   - activate_32.bat 스크립트로 빠르게 활성화 가능
echo.
echo 📚 자세한 설명:
echo   docs\SETUP_32BIT_ENVIRONMENT.md 참고
echo.

pause
