@echo off
REM OpenAPI Comprehensive Test Runner
REM 키움 OpenAPI 종합 테스트 실행

echo ================================================================================
echo Kiwoom OpenAPI Comprehensive Test
echo ================================================================================
echo.

REM Find 32-bit Python (kiwoom32 environment)
set "PYTHON32="

if exist "C:\Users\USER\anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\Users\USER\anaconda3\envs\kiwoom32\python.exe"
    echo Found 32-bit Python: C:\Users\USER\anaconda3\envs\kiwoom32\python.exe
) else if exist "C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe"
    echo Found 32-bit Python: C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe
) else if exist "C:\Anaconda3\envs\kiwoom32\python.exe" (
    set "PYTHON32=C:\Anaconda3\envs\kiwoom32\python.exe"
    echo Found 32-bit Python: C:\Anaconda3\envs\kiwoom32\python.exe
) else (
    echo ERROR: 32-bit Python kiwoom32 environment not found!
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo TEST COVERAGE:
echo ================================================================================
echo.
echo 1. opt10001 - 주식기본정보조회 (단일 데이터)
echo 2. opt10080 - 주식분봉차트조회 (1분봉, 연속조회)
echo 3. opt10080 - 주식분봉차트조회 (5분봉, 연속조회)
echo 4. opt10081 - 주식일봉차트조회 (연속조회)
echo 5. opw00001 - 예수금상세현황요청 (계좌 정보)
echo.
echo This will take approximately 2-3 minutes
echo.
echo ================================================================================
echo.

pause

echo.
echo Starting test...
echo.

"%PYTHON32%" test_openapi_comprehensive.py

echo.
echo ================================================================================
echo Test completed!
echo ================================================================================
echo.
echo Check the generated files for detailed results:
echo   - openapi_comprehensive_test_YYYYMMDD_HHMMSS.json
echo   - openapi_comprehensive_report_YYYYMMDD_HHMMSS.txt
echo.

pause
