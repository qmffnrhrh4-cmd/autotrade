@echo off
echo ==========================================
echo 32비트 환경 패키지 설치
echo ==========================================

echo.
echo [1/6] conda-forge 채널 추가...
call conda config --env --add channels conda-forge
if %errorlevel% neq 0 (
    echo    경고: conda-forge 추가 실패, 계속 진행...
)

echo.
echo [2/6] 채널 우선순위 설정...
call conda config --env --set channel_priority flexible
if %errorlevel% neq 0 (
    echo    경고: 우선순위 설정 실패, 계속 진행...
)

echo.
echo [3/6] pip 업그레이드...
python -m pip install --upgrade pip

echo.
echo [4/6] PyQt5 설치 (pip 사용)...
pip install PyQt5==5.15.10

echo.
echo [5/6] 기타 필수 패키지 설치...
pip install pandas numpy requests

echo.
echo [6/6] kiwoom 라이브러리 설치...
pip uninstall koapy -y
pip install kiwoom

echo.
echo ==========================================
echo 설치 완료 확인
echo ==========================================

echo.
echo Python 아키텍처 확인:
python -c "import platform; print('아키텍처:', platform.architecture()[0])"

echo.
echo PyQt5 설치 확인:
python -c "from PyQt5.QtWidgets import QApplication; print('PyQt5: OK')" 2>nul && echo    ✅ PyQt5 정상 || echo    ❌ PyQt5 실패

echo.
echo kiwoom 설치 확인:
python -c "from kiwoom import Kiwoom; print('kiwoom: OK')" 2>nul && echo    ✅ kiwoom 정상 || echo    ❌ kiwoom 실패

echo.
echo ==========================================
echo 다음 단계
echo ==========================================
echo.
echo 1. 32비트 확인:
echo    python -c "import platform; print(platform.architecture())"
echo.
echo 2. OpenAPI+ 설치:
echo    python install_kiwoom_openapi.py
echo.
pause
