@echo off
echo ============================================
echo Kiwoom 프로세스 강제 종료 스크립트
echo ============================================
echo.

echo 실행 중인 Kiwoom 프로세스를 확인합니다...
echo.

tasklist | findstr /I "KH"

echo.
echo 위의 프로세스들을 강제 종료합니다...
echo.

taskkill /F /IM KHOpenAPI.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ KHOpenAPI.exe 종료 완료
) else (
    echo ℹ️  KHOpenAPI.exe 실행 중이 아님
)

taskkill /F /IM KHOpenAPICtrl.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ KHOpenAPICtrl.exe 종료 완료
) else (
    echo ℹ️  KHOpenAPICtrl.exe 실행 중이 아님
)

taskkill /F /IM OpSysMsg.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ OpSysMsg.exe 종료 완료
) else (
    echo ℹ️  OpSysMsg.exe 실행 중이 아님
)

taskkill /F /IM KHOpenApi64.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ KHOpenApi64.exe 종료 완료
) else (
    echo ℹ️  KHOpenApi64.exe 실행 중이 아님
)

echo.
echo ============================================
echo 프로세스 종료 완료!
echo ============================================
echo.
echo 이제 테스트 스크립트를 다시 실행하세요:
echo   python test_samsung_1year_minute_data.py
echo.

pause
