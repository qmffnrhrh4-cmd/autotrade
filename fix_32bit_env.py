#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
conda 환경을 32비트로 수정하는 스크립트

현재 환경이 64비트면 32비트로 전환
"""

import os
import sys
import platform
import subprocess


def print_header(text):
    """섹션 헤더 출력"""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80 + "\n")


def check_current_env():
    """현재 환경 확인"""
    print_header("현재 환경 확인")

    # Python 비트 확인
    architecture = platform.architecture()[0]
    print(f"Python 아키텍처: {architecture}")
    print(f"Python 버전: {sys.version}")
    print(f"Python 경로: {sys.executable}")

    # Conda 환경 확인
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', 'None')
    print(f"Conda 환경: {conda_env}")

    return architecture == "32bit"


def fix_to_32bit():
    """32비트로 전환"""
    print_header("32비트 환경으로 전환")

    print("""
🔧 현재 환경을 32비트로 전환합니다.

다음 명령어들을 실행합니다:
1. conda config --env --set subdir win-32
2. conda install python=3.10 --force-reinstall
3. conda install pyqt5 pandas numpy requests --force-reinstall

계속하시겠습니까? (y/n): """)

    response = input().strip().lower()
    if response != 'y':
        print("취소했습니다.")
        return False

    commands = [
        ('conda config --env --set subdir win-32', '32비트 채널 설정'),
        ('conda install python=3.10 -y --force-reinstall', 'Python 3.10 32비트 재설치'),
        ('conda install pyqt5 -y', 'PyQt5 설치'),
        ('conda install pandas -y', 'pandas 설치'),
        ('conda install numpy -y', 'numpy 설치'),
        ('conda install requests -y', 'requests 설치'),
    ]

    for cmd, description in commands:
        print(f"\n🔧 {description}...")
        print(f"   명령어: {cmd}")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                capture_output=False,
                text=True
            )
            print(f"   ✅ 성공")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ 실패: {e}")
            return False

    return True


def verify_32bit():
    """32비트 확인"""
    print_header("검증")

    print("환경을 다시 로드해야 합니다.")
    print("\n다음 명령어를 실행하세요:\n")
    print("   conda deactivate")
    print("   conda activate autotrade_32")
    print("   python -c \"import platform; print(platform.architecture())\"")
    print("\n'32bit'가 출력되면 성공입니다.")


def create_new_32bit_env():
    """새 32비트 환경 생성"""
    print_header("새 32비트 환경 생성")

    print("""
기존 환경을 수정하는 대신 새로운 32비트 환경을 만듭니다.

환경 이름: kiwoom32

다음 명령어들을 실행합니다:
1. conda create -n kiwoom32 python=3.10 -y
2. conda activate kiwoom32
3. conda config --env --set subdir win-32
4. conda install python=3.10 --force-reinstall -y

계속하시겠습니까? (y/n): """)

    response = input().strip().lower()
    if response != 'y':
        print("취소했습니다.")
        return False

    print("\n🔧 새 환경 생성 중...")

    # 배치 파일로 생성 (conda activate를 위해)
    batch_script = """@echo off
echo ==========================================
echo 새 32비트 환경 생성 중...
echo ==========================================

echo.
echo [1/5] 환경 생성...
call conda create -n kiwoom32 python=3.10 -y
if %errorlevel% neq 0 goto :error

echo.
echo [2/5] 환경 활성화...
call conda activate kiwoom32
if %errorlevel% neq 0 goto :error

echo.
echo [3/5] 32비트 채널 설정...
call conda config --env --set subdir win-32
if %errorlevel% neq 0 goto :error

echo.
echo [4/5] Python 32비트 재설치...
call conda install python=3.10 -y --force-reinstall
if %errorlevel% neq 0 goto :error

echo.
echo [5/5] 필수 패키지 설치...
call conda install pyqt5 pandas numpy requests -y
if %errorlevel% neq 0 goto :error

echo.
echo ==========================================
echo ^✅ 성공!
echo ==========================================
echo.
echo 다음 명령어로 환경을 활성화하세요:
echo    conda activate kiwoom32
echo.
echo 그 다음:
echo    python install_kiwoom_openapi.py
echo.
pause
goto :end

:error
echo.
echo ==========================================
echo ^❌ 오류 발생
echo ==========================================
pause
exit /b 1

:end
"""

    with open('create_kiwoom32.bat', 'w', encoding='utf-8') as f:
        f.write(batch_script)

    print("✅ 배치 파일 생성: create_kiwoom32.bat")
    print("\n다음 명령어를 실행하세요:")
    print("   create_kiwoom32.bat")

    return True


def main():
    """메인 함수"""
    print_header("🔧 32비트 Python 환경 수정/생성 스크립트")

    # 현재 환경 확인
    is_32bit = check_current_env()

    if is_32bit:
        print("\n✅ 이미 32비트 환경입니다!")
        print("   install_kiwoom_openapi.py를 실행하세요.")
        return

    print("\n현재 64비트 Python이 설치되어 있습니다.")
    print("\n다음 중 선택하세요:")
    print("   1. 현재 환경(autotrade_32)을 32비트로 전환")
    print("   2. 새 환경(kiwoom32) 생성")
    print("   3. 취소")
    print("\n선택 (1/2/3): ", end='')

    choice = input().strip()

    if choice == '1':
        if fix_to_32bit():
            verify_32bit()
    elif choice == '2':
        create_new_32bit_env()
    else:
        print("취소했습니다.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자가 취소했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
