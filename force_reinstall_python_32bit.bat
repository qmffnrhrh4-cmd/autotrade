@echo off
echo ==========================================
echo Python 32비트 강제 재설치
echo ==========================================

echo.
echo 현재 Python 확인:
python -c "import platform; print('아키텍처:', platform.architecture()[0])"

echo.
echo ==========================================
echo 경고: Python을 재설치합니다
echo ==========================================
echo.
echo 이 작업은 현재 환경의 Python을 32비트로 교체합니다.
echo 일부 패키지가 제거될 수 있습니다.
echo.
set /p confirm="계속하시겠습니까? (y/n): "
if /i not "%confirm%"=="y" (
    echo 취소했습니다.
    pause
    exit /b 0
)

echo.
echo [1/4] 32비트 채널 설정 확인...
call conda config --env --set subdir win-32
call conda config --show subdir

echo.
echo [2/4] Python 3.10 32비트 강제 재설치...
echo    이 작업은 몇 분 소요될 수 있습니다...
call conda install python=3.10 -y --force-reinstall

echo.
echo [3/4] pip 재설치...
python -m ensurepip --upgrade
python -m pip install --upgrade pip

echo.
echo [4/4] 필수 패키지 재설치...
pip install PyQt5==5.15.10 pandas numpy requests kiwoom

echo.
echo ==========================================
echo 검증
echo ==========================================

echo.
echo Python 아키텍처:
python -c "import platform; print('아키텍처:', platform.architecture()[0])" || echo    ❌ Python 실행 실패

echo.
echo PyQt5 확인:
python -c "from PyQt5.QtWidgets import QApplication; print('PyQt5: OK')" 2>nul && echo    ✅ PyQt5 정상 || echo    ❌ PyQt5 실패

echo.
echo kiwoom 확인:
python -c "from kiwoom import Kiwoom; print('kiwoom: OK')" 2>nul && echo    ✅ kiwoom 정상 || echo    ❌ kiwoom 실패

echo.
echo ==========================================
if errorlevel 1 (
    echo ❌ 일부 작업 실패
    echo.
    echo 문제가 계속되면 새 환경을 만드세요:
    echo    conda deactivate
    echo    conda remove -n autotrade_32 --all -y
    echo    conda create -n kiwoom32 python=3.10 -y
    echo    conda activate kiwoom32
    echo    conda config --env --set subdir win-32
    echo    conda install python=3.10 -y --force-reinstall
    echo    pip install PyQt5 pandas numpy requests kiwoom
) else (
    echo ✅ 완료!
    echo.
    echo 다음 단계:
    echo    python install_kiwoom_openapi.py
)
echo ==========================================

echo.
pause
