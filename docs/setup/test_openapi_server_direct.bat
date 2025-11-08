@echo off
REM openapi_server.py를 32비트 환경에서 직접 실행하는 테스트

echo ================================================================
echo  OpenAPI Server 직접 실행 테스트
echo ================================================================
echo.

REM Anaconda 경로 찾기
set ANACONDA_PATH=C:\ProgramData\anaconda3
if not exist "%ANACONDA_PATH%" (
    set ANACONDA_PATH=%USERPROFILE%\anaconda3
)

if not exist "%ANACONDA_PATH%" (
    echo ERROR: Anaconda를 찾을 수 없습니다
    pause
    exit /b 1
)

echo Anaconda 경로: %ANACONDA_PATH%
echo.

REM 32비트 환경 활성화 및 서버 실행
echo 32비트 환경에서 서버 시작 중...
echo (로그인 창이 나타나야 합니다)
echo.

call "%ANACONDA_PATH%\Scripts\activate.bat" autotrade_32
python openapi_server.py

pause
