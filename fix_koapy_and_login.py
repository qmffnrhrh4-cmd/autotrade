#!/usr/bin/env python
"""
koapy 자동 수정 및 로그인 테스트
- koapy 0.9.0 → 0.8.4 다운그레이드
- 올바른 import 방법 확인
- 로그인 창 자동 실행
"""

import sys
import subprocess
import time

print("="*80)
print("🔧 koapy 자동 수정 및 로그인 테스트")
print("="*80)

def run_cmd(cmd, desc):
    """명령어 실행"""
    print(f"\n🔧 {desc}...")
    print(f"   명령어: {cmd}")

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=300
    )

    if result.returncode == 0:
        print(f"✅ {desc} 완료")
        if result.stdout and len(result.stdout.strip()) > 0:
            lines = result.stdout.strip().split('\n')
            for line in lines[-5:]:  # 마지막 5줄만
                print(f"   {line}")
        return True
    else:
        print(f"❌ {desc} 실패")
        if result.stderr:
            print(f"   에러: {result.stderr[:200]}")
        return False

print("\n" + "="*80)
print("STEP 1: 현재 koapy 버전 확인")
print("="*80)

try:
    import koapy
    current_version = koapy.__version__
    print(f"현재 koapy 버전: v{current_version}")
except:
    print("koapy가 설치되지 않았습니다.")
    current_version = None

print("\n" + "="*80)
print("STEP 2: koapy 재설치 (0.8.4)")
print("="*80)

print("\n1️⃣ 기존 koapy 제거...")
run_cmd("pip uninstall koapy -y", "koapy 제거")

print("\n2️⃣ koapy 0.8.4 설치...")
versions_to_try = ['0.8.4', '0.8.3', '0.8.2']

installed = False
for ver in versions_to_try:
    print(f"\n📦 koapy v{ver} 시도...")
    if run_cmd(f"pip install koapy=={ver} --no-cache-dir", f"koapy {ver} 설치"):
        installed = True
        print(f"✅ koapy v{ver} 설치 성공!")
        break
    else:
        print(f"⚠️  koapy v{ver} 설치 실패, 다음 버전 시도...")

if not installed:
    print("\n❌ 모든 버전 설치 실패")
    print("\n수동으로 설치하세요:")
    print("   pip install koapy==0.8.4")
    sys.exit(1)

print("\n" + "="*80)
print("STEP 3: koapy 설치 확인")
print("="*80)

# Python 재시작 없이 모듈 재로드
if 'koapy' in sys.modules:
    del sys.modules['koapy']

try:
    import koapy
    print(f"✅ koapy v{koapy.__version__} 설치 확인")
    print(f"   경로: {koapy.__file__}")
except ImportError as e:
    print(f"❌ koapy import 실패: {e}")
    sys.exit(1)

print("\n" + "="*80)
print("STEP 4: KiwoomOpenApiContext import 테스트")
print("="*80)

import_methods = [
    ("from koapy import KiwoomOpenApiContext",
     lambda: getattr(__import__('koapy'), 'KiwoomOpenApiContext')),

    ("from koapy.context import KiwoomOpenApiContext",
     lambda: getattr(__import__('koapy.context', fromlist=['KiwoomOpenApiContext']), 'KiwoomOpenApiContext')),

    ("from koapy.openapi import KiwoomOpenApiContext",
     lambda: getattr(__import__('koapy.openapi', fromlist=['KiwoomOpenApiContext']), 'KiwoomOpenApiContext')),
]

KiwoomOpenApiContext = None
successful_import = None

for import_str, import_func in import_methods:
    try:
        KiwoomOpenApiContext = import_func()
        print(f"✅ 성공: {import_str}")
        successful_import = import_str
        break
    except (ImportError, AttributeError) as e:
        print(f"❌ 실패: {import_str}")

if KiwoomOpenApiContext is None:
    print("\n❌ KiwoomOpenApiContext를 찾을 수 없습니다.")
    print("\n환경 재생성을 권장합니다:")
    print("   conda remove -n autotrade_32 --all -y")
    print("   conda create -n autotrade_32 python=3.9 -y")
    print("   conda activate autotrade_32")
    print("   pip install koapy==0.8.3 PyQt5==5.15.9")
    sys.exit(1)

print(f"\n✅ Import 성공: {successful_import}")

print("\n" + "="*80)
print("STEP 5: PyQt5 확인")
print("="*80)

try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QAxContainer import QAxWidget
    print("✅ PyQt5 정상")
except ImportError as e:
    print(f"❌ PyQt5 오류: {e}")
    print("\nPyQt5 재설치:")
    run_cmd("pip install PyQt5==5.15.9 --no-cache-dir", "PyQt5 설치")

print("\n" + "="*80)
print("STEP 6: 로그인 창 실행")
print("="*80)

print("\n🔑 로그인 창을 실행하시겠습니까? (y/n): ", end='')
user_input = input().strip().lower()

if user_input != 'y':
    print("\n✅ koapy 수정 완료!")
    print(f"   사용법: {successful_import}")
    print("\n다음 명령어로 로그인 테스트:")
    print("   python fix_koapy_and_login.py")
    sys.exit(0)

print("\n🚀 로그인 창 실행 중...")
print("="*60)
print("   - ID/PW/인증서 비밀번호를 입력하세요")
print("   - 로그인 후 잠시 기다려주세요")
print("="*60 + "\n")

try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QCoreApplication
    import logging

    logging.basicConfig(level=logging.INFO)

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        print("✅ QApplication 생성")

    # Qt 속성 설정
    try:
        QCoreApplication.setAttribute(0x10000)  # AA_EnableHighDpiScaling
    except:
        pass

    print("✅ 로그인 창 표시 중...\n")

    with KiwoomOpenApiContext() as context:
        print("\n✅ 로그인 성공!")

        try:
            accounts = context.GetAccountList()
            print(f"   📊 계좌 수: {len(accounts)}")

            if accounts:
                print(f"   📋 계좌 목록:")
                for idx, acc in enumerate(accounts, 1):
                    print(f"      {idx}. {acc}")

            user_id = context.GetLoginInfo("USER_ID")
            user_name = context.GetLoginInfo("USER_NAME")

            if user_id:
                print(f"   👤 사용자 ID: {user_id}")
            if user_name:
                print(f"   👤 이름: {user_name}")

        except Exception as e:
            print(f"   ⚠️  계좌 정보 조회 실패: {e}")

        print("\n✨ OpenAPI 로그인 테스트 완료!")

    print("\n" + "="*80)
    print("✅ 모든 테스트 완료!")
    print("="*80)
    print(f"\n올바른 import 방법:")
    print(f"   {successful_import}")
    print(f"\n다음 단계:")
    print(f"   1. openapi_server.py 실행 (이 환경에서)")
    print(f"   2. main.py 실행 (64비트 환경에서)")

except ImportError as e:
    print(f"\n❌ Import 오류: {e}")
    import traceback
    traceback.print_exc()

    print("\n해결 방법:")
    print("   pip install PyQt5==5.15.9 --no-cache-dir")

except Exception as e:
    print(f"\n❌ 로그인 오류: {e}")
    import traceback
    traceback.print_exc()

    error_msg = str(e).lower()
    if "timeout" in error_msg:
        print("\n💡 로그인 시간 초과")
        print("   - 로그인 창에서 정보를 입력했는지 확인")
        print("   - 인터넷 연결 확인")
    elif "ocx" in error_msg or "com" in error_msg:
        print("\n💡 OCX 오류")
        print("   - 키움 OpenAPI+ 재설치")
        print("   - 관리자 권한으로 실행")

print("\n" + "="*80)
