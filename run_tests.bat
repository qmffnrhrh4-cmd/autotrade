@echo off
chcp 65001 >nul
REM UTF-8 설정

:MENU
cls
echo ========================================
echo  진화 알고리즘 시스템 테스트 메뉴
echo ========================================
echo.
echo  [1] 간단 테스트 (파일구조, 스레드, 지표)
echo  [2] 전체 테스트 (진화엔진 상세)
echo  [3] 모두 실행
echo  [0] 종료
echo.
echo ========================================
set /p choice=선택:

if "%choice%"=="1" goto SIMPLE
if "%choice%"=="2" goto FULL
if "%choice%"=="3" goto ALL
if "%choice%"=="0" goto END
goto MENU

:SIMPLE
cls
echo ========================================
echo  간단 테스트 실행 중...
echo ========================================
echo.
python3 tests\test_simple_evolution.py
echo.
pause
goto MENU

:FULL
cls
echo ========================================
echo  전체 테스트 실행 중...
echo ========================================
echo.
python3 tests\test_evolution_engine.py
echo.
pause
goto MENU

:ALL
cls
echo ========================================
echo  모든 테스트 실행 중...
echo ========================================
echo.
echo [1/2] 간단 테스트...
python3 tests\test_simple_evolution.py
echo.
echo ----------------------------------------
echo.
echo [2/2] 전체 테스트...
python3 tests\test_evolution_engine.py
echo.
echo ========================================
echo  모든 테스트 완료!
echo ========================================
pause
goto MENU

:END
exit
