@echo off
echo ==========================================
echo kiwoom32 환경 패키지 설치
echo ==========================================

echo.
echo [1/6] Python 32비트 확인...
python -c "import platform; print('아키텍처:', platform.architecture()[0])"

echo.
echo [2/6] PyQt5 설치...
pip install "PyQt5==5.15.10"

echo.
echo [3/6] pandas 1.5.x 설치 (32비트 호환)...
pip install "pandas<2.0"

echo.
echo [4/6] numpy 설치...
pip install numpy

echo.
echo [5/6] requests 설치...
pip install requests

echo.
echo [6/6] kiwoom 라이브러리 설치...
pip install kiwoom

echo.
echo ==========================================
echo 설치 완료 검증
echo ==========================================

echo.
echo Python 아키텍처:
python -c "import platform; print('아키텍처:', platform.architecture()[0])"

echo.
echo PyQt5 확인:
python -c "from PyQt5.QtWidgets import QApplication; print('PyQt5: OK')" 2>nul && echo    ✅ PyQt5 정상 || echo    ❌ PyQt5 실패

echo.
echo pandas 확인:
python -c "import pandas; print('pandas:', pandas.__version__)" 2>nul && echo    ✅ pandas 정상 || echo    ❌ pandas 실패

echo.
echo kiwoom 확인:
python -c "from kiwoom import Kiwoom; print('kiwoom: OK')" 2>nul && echo    ✅ kiwoom 정상 || echo    ❌ kiwoom 실패

echo.
echo ==========================================
echo 다음 단계
echo ==========================================
echo.
echo OpenAPI+ 설치:
echo    python install_kiwoom_openapi.py
echo.
pause
