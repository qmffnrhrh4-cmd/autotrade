@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo  🤖 AutoTrade Pro - 완전 자동화 시스템 v6.3
echo ================================================================================
echo.
echo  ✅ OpenAPI 서버 (32비트) - Kiwoom 연결
echo  ✅ 전략 진화 엔진 - 24/7 자동 최적화
echo  ✅ 웹 대시보드 - 실시간 모니터링
echo  ✅ AutoPilot - AI 완전 자동 매매
echo.
echo ================================================================================
echo.

REM ======================================================================
REM Step 1: 32-bit Python 환경 찾기
REM ======================================================================
echo [1/5] 32-bit Python 환경 확인 중...

set "PYTHON32="
if exist "C:\Users\USER\anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\Users\USER\anaconda3\envs\kiwoom32\python.exe"
    echo    ✓ 32-bit Python 발견: kiwoom32
) else if exist "C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe"
    echo    ✓ 32-bit Python 발견: kiwoom32 (ProgramData)
) else if exist "C:\Anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\Anaconda3\envs\kiwoom32\python.exe"
    echo    ✓ 32-bit Python 발견: kiwoom32 (Anaconda3)
) else (
    echo    ⚠️  32-bit Python을 찾을 수 없습니다
    echo    수동 실행 필요: conda activate kiwoom32 ^&^& python openapi_server_v2.py
    pause
    exit /b 1
)

REM openapi_server_v2.py 존재 확인
if not exist "openapi_server_v2.py" (
    echo    ❌ openapi_server_v2.py 파일이 없습니다
    echo    현재 디렉토리: %CD%
    pause
    exit /b 1
)
echo.

REM ======================================================================
REM Step 2: 기존 프로세스 정리
REM ======================================================================
echo [2/5] 기존 프로세스 정리 중...

REM 기존 OpenAPI 서버 확인 및 종료
curl -s http://127.0.0.1:5001/health >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo    ↻ 기존 OpenAPI 서버 종료 중...
    curl -s -X POST http://127.0.0.1:5001/shutdown >nul 2>&1
    timeout /t 2 /nobreak >nul
)

REM 포트 5001 사용 중인 프로세스 종료
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5001" ^| findstr "LISTENING" 2^>nul') do (
    echo    ↻ 포트 5001 프로세스 종료 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

REM 포트 5000 사용 중인 프로세스 종료
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING" 2^>nul') do (
    echo    ↻ 포트 5000 프로세스 종료 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

echo    ✓ 정리 완료
echo.

REM ======================================================================
REM Step 3: OpenAPI 서버 시작 (32-bit)
REM ======================================================================
echo [3/5] OpenAPI 서버 시작 중 (32-bit)...
echo.
echo    ⚠️  중요: 키움증권 로그인 창이 나타나면 로그인하세요!
echo    - Alt+Tab 으로 창을 찾거나
echo    - 작업 표시줄에서 창을 확인하세요
echo.

start "Kiwoom OpenAPI Server (32-bit)" "%PYTHON32%" openapi_server_v2.py
echo    ✓ OpenAPI 서버 창 열림

REM OpenAPI 연결 대기 (최대 90초)
echo.
echo    로그인 대기 중... (최대 90초)

set /a RETRY_COUNT=0
set /a MAX_RETRIES=90

:WAIT_OPENAPI
set /a RETRY_COUNT+=1
if %RETRY_COUNT% gtr %MAX_RETRIES% (
    echo.
    echo    ⚠️  OpenAPI 연결 시간 초과 - 수동 로그인 후 계속됩니다
    goto START_SERVICES
)

REM 서버 상태 확인
curl -s http://127.0.0.1:5001/health > health_temp.json 2>&1
if %ERRORLEVEL% equ 0 (
    findstr /C:"\"connection_status\": \"connected\"" health_temp.json >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        del health_temp.json >nul 2>&1
        echo.
        echo    ✅ OpenAPI 연결 성공!
        timeout /t 5 /nobreak >nul
        goto START_SERVICES
    )
)

if exist health_temp.json del health_temp.json >nul 2>&1

REM 진행 상태 표시 (10초마다)
set /a MOD=%RETRY_COUNT% %% 10
if %MOD% equ 0 (
    set /a REMAINING=%MAX_RETRIES% - %RETRY_COUNT%
    echo    [%RETRY_COUNT%/%MAX_RETRIES%] 대기 중... (남은 시간: %REMAINING%초)
)

timeout /t 1 /nobreak >nul
goto WAIT_OPENAPI

:START_SERVICES
if exist health_temp.json del health_temp.json >nul 2>&1
echo.

REM ======================================================================
REM Step 4: 백그라운드 서비스 시작
REM ======================================================================
echo [4/5] 백그라운드 서비스 시작 중...

REM logs 폴더 생성
if not exist "logs" mkdir logs

REM 전략 최적화 엔진 시작
if exist "run_strategy_optimizer.py" (
    start /B python run_strategy_optimizer.py --auto-deploy > logs\strategy_optimizer.log 2>&1
    echo    ✓ 전략 진화 엔진 시작 (logs\strategy_optimizer.log)
) else (
    echo    ⚠️  전략 최적화 파일 없음 - 건너뜀
)

timeout /t 1 /nobreak >nul

REM 대시보드 서버 시작
start /B python -m dashboard.app > logs\dashboard.log 2>&1
echo    ✓ 웹 대시보드 시작 (http://localhost:5000)

timeout /t 2 /nobreak >nul
echo.

REM ======================================================================
REM Step 5: 메인 봇 시작 (AutoPilot 완전 자동화)
REM ======================================================================
echo [5/5] AutoPilot 메인 봇 시작 중...
echo.
echo ================================================================================
echo  🤖 AutoPilot 완전 자동화 모드
echo ================================================================================
echo.
echo  실행 중인 서비스:
echo    [1] OpenAPI Server - Port 5001 (32-bit Kiwoom)
echo    [2] Strategy Optimizer - 백그라운드 진화
echo    [3] Web Dashboard - http://localhost:5000
echo    [4] AutoTrade Bot - AutoPilot 완전 자동화
echo.
echo  로그 위치:
echo    - logs\strategy_optimizer.log
echo    - logs\dashboard.log
echo    - logs\autotrade.log
echo.
echo ================================================================================
echo.

REM 브라우저 열기
start http://localhost:5000

REM 메인 봇 시작 (가상매매 + 자동시작 + 테스트 건너뛰기)
python main.py --virtual-trading --auto-start --skip-test

REM ======================================================================
REM 종료 시 정리
REM ======================================================================
echo.
echo ================================================================================
echo  메인 봇 종료됨 - 백그라운드 서비스 정리 중...
echo ================================================================================
echo.

REM 전략 최적화 종료
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr /C:"PID:"') do (
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /C:"run_strategy_optimizer.py" >nul
    if !ERRORLEVEL! equ 0 (
        echo    ↻ Strategy Optimizer 종료 (PID: %%a)
        taskkill /F /PID %%a >nul 2>&1
    )
)

REM 대시보드 종료
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING" 2^>nul') do (
    echo    ↻ Dashboard 종료 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

REM OpenAPI 서버 종료
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5001" ^| findstr "LISTENING" 2^>nul') do (
    echo    ↻ OpenAPI Server 종료 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo    ✅ 모든 서비스 종료 완료
echo.
pause
