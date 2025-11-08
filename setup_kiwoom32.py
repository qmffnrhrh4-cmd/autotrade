#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kiwoom32 환경 통합 설정 스크립트

이 스크립트는 다음을 수행합니다:
1. 32비트 Python 환경 생성/확인
2. 필수 패키지 설치
3. OpenAPI+ 설치 확인
4. 환경 검증

사용법:
    python setup_kiwoom32.py
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def print_header(text):
    """섹션 헤더 출력"""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80 + "\n")


def find_conda():
    """Anaconda 경로 찾기"""
    possible_paths = [
        Path(os.environ.get('CONDA_EXE', '')).parent.parent if 'CONDA_EXE' in os.environ else None,
        Path.home() / 'anaconda3',
        Path.home() / 'miniconda3',
        Path('C:/ProgramData/anaconda3'),
        Path('C:/ProgramData/miniconda3'),
    ]

    for path in possible_paths:
        if path and path.exists() and (path / 'Scripts' / 'conda.exe').exists():
            return path

    return None


def check_32bit():
    """현재 Python이 32비트인지 확인"""
    return platform.architecture()[0] == '32bit'


def create_or_verify_env():
    """kiwoom32 환경 생성 또는 확인"""
    print_header("1. 32비트 Python 환경 확인")

    # 현재 환경이 32비트인지 확인
    if check_32bit():
        env_name = os.environ.get('CONDA_DEFAULT_ENV', 'unknown')
        print(f"✅ 현재 환경이 이미 32비트입니다: {env_name}")
        return True

    # Conda 찾기
    conda_path = find_conda()
    if not conda_path:
        print("❌ Anaconda를 찾을 수 없습니다")
        print("   https://www.anaconda.com/download 에서 설치하세요")
        return False

    print(f"📁 Anaconda 경로: {conda_path}")

    # kiwoom32 환경 확인
    env_path = conda_path / "envs" / "kiwoom32"
    if env_path.exists():
        print("✅ kiwoom32 환경이 이미 존재합니다")
        print("\n환경을 활성화하세요:")
        print("   conda activate kiwoom32")
        return True

    # 환경 생성
    print("🔧 kiwoom32 환경을 생성합니다...")
    print("   (2-3분 소요)")

    commands = [
        ('conda create -n kiwoom32 python=3.9 -y', '환경 생성'),
        ('conda config --env --set subdir win-32', '32비트 설정'),
    ]

    for cmd, desc in commands:
        print(f"\n   {desc}...")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            print(f"   ✅ {desc} 완료")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ {desc} 실패")
            print(f"   에러: {e.stderr}")
            return False

    print("\n✅ kiwoom32 환경 생성 완료!")
    print("\n환경을 활성화하세요:")
    print("   conda activate kiwoom32")
    print("   python setup_kiwoom32.py")

    return False  # 환경을 활성화하고 다시 실행해야 함


def install_packages():
    """필수 패키지 설치"""
    print_header("2. 필수 패키지 설치")

    if not check_32bit():
        print("⚠️  32비트 환경이 아닙니다. 먼저 kiwoom32 환경을 활성화하세요:")
        print("   conda activate kiwoom32")
        return False

    packages = [
        ('flask', 'Flask'),
        ('flask-cors', 'Flask-CORS'),
        ('PyQt5==5.15.10', 'PyQt5'),
        ('pandas<2.0', 'pandas'),
        ('numpy', 'numpy'),
        ('requests', 'requests'),
        ('kiwoom', 'kiwoom'),
    ]

    print("📦 패키지 설치 중...")
    print("   (3-5분 소요)\n")

    for package, name in packages:
        print(f"   Installing {name}...", end=' ', flush=True)
        try:
            result = subprocess.run(
                f'pip install -q {package}',
                shell=True,
                check=True,
                capture_output=True
            )
            print("✅")
        except subprocess.CalledProcessError as e:
            print("❌")
            print(f"   에러: {e.stderr.decode('utf-8', errors='ignore')[:200]}")
            return False

    print("\n✅ 패키지 설치 완료!")
    return True


def verify_installation():
    """설치 검증"""
    print_header("3. 설치 검증")

    # Python 아키텍처
    arch = platform.architecture()[0]
    print(f"Python 아키텍처: {arch}")
    if arch != '32bit':
        print("   ⚠️  32비트가 아닙니다!")
        return False
    print("   ✅ 32비트 확인")

    # 패키지 테스트
    tests = [
        ('flask', 'Flask'),
        ('kiwoom', 'kiwoom'),
        ('PyQt5.QtWidgets', 'PyQt5'),
        ('pandas', 'pandas'),
    ]

    print("\n패키지 확인:")
    for module, name in tests:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError as e:
            print(f"   ❌ {name}: {e}")
            return False

    print("\n✅ 모든 검증 통과!")
    return True


def check_openapi():
    """OpenAPI+ 설치 확인"""
    print_header("4. OpenAPI+ 확인")

    ocx_paths = [
        Path("C:/OpenAPI/KHOpenAPI.ocx"),
        Path("C:/Program Files (x86)/Kiwoom/OpenAPI/KHOpenAPI.ocx"),
    ]

    for path in ocx_paths:
        if path.exists():
            print(f"✅ OpenAPI+ OCX 발견: {path}")
            return True

    print("⚠️  OpenAPI+ OCX를 찾을 수 없습니다")
    print("\nOpenAPI+ 설치:")
    print("   python install_kiwoom_openapi.py")
    print("\n   또는 수동 다운로드:")
    print("   https://download.kiwoom.com/web/openapi/OpenAPISetup.exe")

    return False


def main():
    """메인 함수"""
    print_header("🔧 Kiwoom32 환경 통합 설정")

    print("이 스크립트는 다음을 수행합니다:")
    print("1. 32비트 Python 환경 생성/확인 (kiwoom32)")
    print("2. 필수 패키지 설치 (Flask, kiwoom, PyQt5, pandas 등)")
    print("3. OpenAPI+ 설치 확인")
    print("4. 환경 검증\n")

    # Step 1: 환경 생성/확인
    if not create_or_verify_env():
        print("\n⚠️  환경을 활성화하고 다시 실행하세요")
        return

    # Step 2: 패키지 설치
    if not install_packages():
        print("\n❌ 패키지 설치 실패")
        return

    # Step 3: 검증
    if not verify_installation():
        print("\n❌ 검증 실패")
        return

    # Step 4: OpenAPI 확인
    openapi_ok = check_openapi()

    # 최종 안내
    print_header("✅ 설정 완료!")

    if openapi_ok:
        print("모든 준비가 완료되었습니다!")
        print("\n다음 단계:")
        print("   1. OpenAPI 서버 테스트:")
        print("      python openapi_server.py")
        print("")
        print("   2. 메인 봇 실행:")
        print("      python main.py")
    else:
        print("환경은 준비되었지만 OpenAPI+가 설치되지 않았습니다.")
        print("\nOpenAPI+ 설치 후:")
        print("   python install_kiwoom_openapi.py")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자가 취소했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
