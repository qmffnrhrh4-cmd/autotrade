@echo off
REM ===================================================================
REM 로컬 불필요한 파일 정리 스크립트
REM Windows PC의 테스트 파일, MD 파일, 로그 등 정리
REM ===================================================================

echo ========================================
echo 불필요한 파일 정리 중...
echo ========================================
echo.

REM MD 파일 삭제 (README.md, START_HERE.md 제외)
echo [1/4] MD 파일 정리...
for %%f in (*.md) do (
    if /i not "%%f"=="README.md" (
        if /i not "%%f"=="START_HERE.md" (
            if /i not "%%f"=="QUICK_START.md" (
                echo   - 삭제: %%f
                del "%%f" 2>nul
            )
        )
    )
)

REM 테스트 파일 삭제
echo [2/4] 테스트 파일 정리...
for %%f in (test_*.py) do (
    echo   - 삭제: %%f
    del "%%f" 2>nul
)

REM BAT 파일 정리 (주요 실행 파일 제외)
echo [3/4] BAT 파일 정리...
for %%f in (*.bat) do (
    if /i not "%%f"=="run.bat" (
        if /i not "%%f"=="run_openapi.bat" (
            if /i not "%%f"=="start_with_openapi.bat" (
                if /i not "%%f"=="cleanup.bat" (
                    echo   - 삭제: %%f
                    del "%%f" 2>nul
                )
            )
        )
    )
)

REM 로그 파일 정리 (logs 폴더 내 .log 파일)
echo [4/4] 로그 파일 정리...
if exist logs (
    del /q logs\*.log 2>nul
    echo   - logs 폴더 내 모든 로그 삭제 완료
)

echo.
echo ========================================
echo 정리 완료!
echo ========================================
echo.
echo 유지된 파일:
echo   - README.md
echo   - START_HERE.md
echo   - QUICK_START.md
echo   - run.bat
echo   - run_openapi.bat
echo   - start_with_openapi.bat
echo   - cleanup.bat (이 파일)
echo.
pause
