@echo off
REM AutoTrade Quick Run - Works from any CMD!

REM Initialize conda for this session
if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\anaconda3\Scripts\activate.bat" autotrade_32
) else if exist "%USERPROFILE%\Anaconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\Anaconda3\Scripts\activate.bat" autotrade_32
) else if exist "C:\ProgramData\Anaconda3\Scripts\activate.bat" (
    call "C:\ProgramData\Anaconda3\Scripts\activate.bat" autotrade_32
) else (
    echo ERROR: Cannot find Anaconda!
    pause
    exit /b 1
)

REM Run main.py
python main.py

pause
