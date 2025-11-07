@echo off
REM ====================================
REM  AutoTrade - 32비트 환경 활성화
REM ====================================

call conda activate autotrade_32

if %errorLevel% neq 0 (
    echo ❌ autotrade_32 환경이 존재하지 않습니다!
    echo.
    echo 💡 먼저 환경을 생성하세요:
    echo    setup_32bit.bat
    echo.
    pause
    exit /b 1
)

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║     ✅ 32비트 AutoTrade 환경 활성화됨                     ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM 비트 확인
python -c "import struct; bits = struct.calcsize('P') * 8; print(f'🐍 Python: {bits}-bit')"
echo 📁 환경: autotrade_32
echo.

REM 사용 가능한 명령어 표시
echo 💡 사용 가능한 명령어:
echo    python test_login.py       - 로그인 테스트
echo    python main.py             - 메인 프로그램 실행
echo    python -m pytest tests/    - 테스트 실행
echo.
