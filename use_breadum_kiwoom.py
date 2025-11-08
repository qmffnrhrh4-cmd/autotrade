#!/usr/bin/env python
"""
breadum/kiwoom 라이브러리 사용
- koapy 제거
- breadum/kiwoom 설치
- 즉시 로그인 테스트
"""

import sys
import subprocess

print("="*80)
print("🔧 breadum/kiwoom 라이브러리로 전환")
print("="*80)

def run_cmd(cmd, desc):
    """명령어 실행"""
    print(f"\n🔧 {desc}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)

    if result.returncode == 0:
        print(f"✅ {desc} 완료")
        return True
    else:
        print(f"❌ {desc} 실패")
        if result.stderr:
            print(f"   에러: {result.stderr[:200]}")
        return False

print("\n" + "="*80)
print("STEP 1: 기존 라이브러리 제거")
print("="*80)

print("\n1️⃣ koapy 제거...")
run_cmd("pip uninstall koapy -y", "koapy 제거")

print("\n2️⃣ protobuf 제거 (충돌 방지)...")
run_cmd("pip uninstall protobuf -y", "protobuf 제거")

print("\n" + "="*80)
print("STEP 2: breadum/kiwoom 설치")
print("="*80)

print("\n📦 kiwoom 설치...")
if not run_cmd("pip install kiwoom --no-cache-dir", "kiwoom 설치"):
    print("\n⚠️  설치 실패. 수동 설치를 시도하세요:")
    print("   pip install kiwoom")
    sys.exit(1)

print("\n" + "="*80)
print("STEP 3: 설치 확인")
print("="*80)

try:
    import kiwoom
    print(f"✅ kiwoom 설치 확인")
    print(f"   버전: {kiwoom.__version__ if hasattr(kiwoom, '__version__') else 'N/A'}")
    print(f"   경로: {kiwoom.__file__}")
except ImportError as e:
    print(f"❌ kiwoom import 실패: {e}")
    sys.exit(1)

print("\n" + "="*80)
print("STEP 4: Kiwoom 클래스 확인")
print("="*80)

try:
    from kiwoom import Kiwoom
    print("✅ Kiwoom 클래스 import 성공")
    print(f"   from kiwoom import Kiwoom")
except ImportError as e:
    print(f"❌ Kiwoom 클래스 import 실패: {e}")

    # API 클래스 시도
    try:
        from kiwoom import API
        print("✅ API 클래스 발견")
        Kiwoom = API
    except ImportError:
        print("❌ 사용 가능한 클래스를 찾을 수 없습니다")
        sys.exit(1)

print("\n" + "="*80)
print("STEP 5: PyQt5 확인")
print("="*80)

try:
    from PyQt5.QtWidgets import QApplication
    print("✅ PyQt5 정상")
except ImportError as e:
    print(f"❌ PyQt5 오류: {e}")
    print("\nPyQt5 설치:")
    run_cmd("pip install PyQt5==5.15.9 --no-cache-dir", "PyQt5 설치")

print("\n" + "="*80)
print("STEP 6: 로그인 테스트")
print("="*80)

print("\n🔑 로그인 창을 실행하시겠습니까? (y/n): ", end='')
user_input = input().strip().lower()

if user_input != 'y':
    print("\n✅ breadum/kiwoom 설치 완료!")
    print("\n사용법:")
    print("```python")
    print("from PyQt5.QtWidgets import QApplication")
    print("from kiwoom import Kiwoom")
    print("import sys")
    print("")
    print("app = QApplication(sys.argv)")
    print("api = Kiwoom()")
    print("api.login()")
    print("```")
    sys.exit(0)

print("\n🚀 로그인 창 실행 중...")
print("="*60)
print("   - ID/PW/인증서 비밀번호를 입력하세요")
print("   - 로그인 후 잠시 기다려주세요")
print("="*60 + "\n")

try:
    from PyQt5.QtWidgets import QApplication

    print("1. QApplication 생성...")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        print("   ✅ QApplication 생성됨")

    print("2. Kiwoom API 생성...")
    api = Kiwoom()
    print("   ✅ Kiwoom 인스턴스 생성됨")

    print("3. 로그인 실행...")
    api.login()
    print("   ✅ 로그인 성공!")

    print("\n4. 계좌 정보 조회...")
    try:
        # 계좌번호 리스트 조회
        accounts = api.get_account_list()
        print(f"   📊 계좌 수: {len(accounts)}")

        if accounts:
            print(f"   📋 계좌 목록:")
            for idx, acc in enumerate(accounts, 1):
                print(f"      {idx}. {acc}")

        # 사용자 정보
        user_id = api.get_login_info("USER_ID")
        user_name = api.get_login_info("USER_NAME")

        if user_id:
            print(f"   👤 사용자 ID: {user_id}")
        if user_name:
            print(f"   👤 이름: {user_name}")

    except Exception as e:
        print(f"   ⚠️  계좌 정보 조회 실패: {e}")

    print("\n" + "="*80)
    print("✨ breadum/kiwoom 로그인 테스트 완료!")
    print("="*80)

    print("\n다음 단계:")
    print("  1. openapi_server.py를 breadum/kiwoom으로 수정")
    print("  2. main.py는 64비트에서 REST API로 통신")

    print("\n사용 예제:")
    print("```python")
    print("from kiwoom import Kiwoom")
    print("from PyQt5.QtWidgets import QApplication")
    print("import sys")
    print("")
    print("app = QApplication(sys.argv)")
    print("api = Kiwoom()")
    print("api.login()")
    print("")
    print("# 계좌 조회")
    print("accounts = api.get_account_list()")
    print("print(accounts)")
    print("```")

except ImportError as e:
    print(f"\n❌ Import 오류: {e}")
    import traceback
    traceback.print_exc()

    print("\n해결 방법:")
    print("  pip install kiwoom PyQt5==5.15.9")

except AttributeError as e:
    print(f"\n❌ 메서드 오류: {e}")

    # Kiwoom 클래스의 사용 가능한 메서드 출력
    print("\n사용 가능한 메서드:")
    for method in dir(api):
        if not method.startswith('_'):
            print(f"  - {method}")

    print("\n메서드 이름이 다를 수 있습니다. 위 목록을 확인하세요.")

except Exception as e:
    print(f"\n❌ 로그인 오류: {e}")
    import traceback
    traceback.print_exc()

    error_msg = str(e).lower()
    if "ocx" in error_msg or "com" in error_msg:
        print("\n💡 해결 방법:")
        print("  - 키움 OpenAPI+ 재설치")
        print("  - 관리자 권한으로 실행")

print("\n" + "="*80)
