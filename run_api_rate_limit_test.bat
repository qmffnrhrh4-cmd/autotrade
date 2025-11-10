@echo off
REM API Rate Limit Test Runner
REM 키움 OpenAPI 연속 조회 제한 테스트 실행

echo ================================================================================
echo Kiwoom OpenAPI Rate Limit Test
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
echo IMPORTANT NOTES:
echo ================================================================================
echo.
echo 1. This test will take approximately 10-15 minutes
echo 2. You will need to login to Kiwoom when prompted
echo 3. The test will try various delay times (1s, 3s, 5s, 10s, 15s, 20s, 30s)
echo 4. Results will be saved to:
echo    - api_rate_limit_test_YYYYMMDD_HHMMSS.json
echo    - api_rate_limit_report_YYYYMMDD_HHMMSS.txt
echo.
echo ================================================================================
echo.

pause

echo.
echo Starting test...
echo.

"%PYTHON32%" test_api_rate_limits.py

echo.
echo ================================================================================
echo Test completed!
echo ================================================================================
echo.
echo Check the generated files for detailed results.
echo.

pause
