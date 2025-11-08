#!/usr/bin/env python
"""
키움 OCX 등록 및 로그인 테스트
- OCX 파일 자동 탐색
- regsvr32로 자동 등록
- breadum/kiwoom으로 로그인 테스트
"""

import sys
import subprocess
import os
from pathlib import Path

print("="*80)
print("🔧 키움 OCX 등록 및 로그인 테스트")
print("="*80)

def run_cmd_admin(cmd, desc):
    """관리자 권한으로 명령 실행"""
    print(f"\n🔧 {desc}...")
    print(f"   명령어: {cmd}")

    try:
        # PowerShell을 사용하여 관리자 권한으로 실행
        powershell_cmd = f'Start-Process cmd.exe -ArgumentList "/c {cmd}" -Verb RunAs -Wait'

        result = subprocess.run(
            ["powershell", "-Command", powershell_cmd],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"✅ {desc} 완료")
            return True
        else:
            print(f"⚠️  {desc} - 사용자가 관리자 권한을 거부했거나 오류 발생")
            return False

    except Exception as e:
        print(f"❌ {desc} 실패: {e}")
        return False

print("\n" + "="*80)
print("STEP 1: OCX 파일 찾기")
print("="*80)

ocx_paths = [
    r"C:\OpenAPI\KHOpenAPI.ocx",
    r"C:\OpenAPI\KHOpenAPICtrl.ocx",
    r"C:\Program Files (x86)\Kiwoom\OpenAPI\KHOpenAPI.ocx",
    r"C:\KiwoomFlash3\OpenAPI\KHOpenAPI.ocx",
]

ocx_file = None
for path in ocx_paths:
    if os.path.exists(path):
        print(f"✅ OCX 파일 발견: {path}")
        ocx_file = path
        break

if not ocx_file:
    print("\n❌ OCX 파일을 찾을 수 없습니다.")
    print("\n키움 OpenAPI+ 설치:")
    print("   https://www.kiwoom.com/nkw.templateFrameSet.do?m=m1408000000")
    print("\n설치 후 다시 실행하세요:")
    print("   python register_ocx_and_login.py")
    sys.exit(1)

print("\n" + "="*80)
print("STEP 2: OCX 등록 (관리자 권한 필요)")
print("="*80)

print("\n⚠️  UAC (사용자 계정 컨트롤) 창이 나타나면 '예'를 클릭하세요.")
print("   OCX 파일을 Windows COM으로 등록합니다.\n")

# regsvr32 명령어
register_cmd = f'regsvr32 /s "{ocx_file}"'

success = run_cmd_admin(register_cmd, "OCX 등록")

if not success:
    print("\n⚠️  자동 등록 실패. 수동으로 시도하세요:")
    print(f"\n   1. 명령 프롬프트를 관리자 권한으로 실행")
    print(f"   2. 다음 명령어 실행:")
    print(f"      regsvr32 /s \"{ocx_file}\"")
    print(f"\n   또는:")
    print(f"      regsvr32 \"{ocx_file}\"")
    print(f"\n등록 후 이 스크립트를 다시 실행하세요.")

    # 그래도 계속 진행
    print(f"\n계속 진행하시겠습니까? (y/n): ", end='')
    if input().strip().lower() != 'y':
        sys.exit(1)

print("\n" + "="*80)
print("STEP 3: breadum/kiwoom 설치 확인")
print("="*80)

try:
    import kiwoom
    print(f"✅ kiwoom 라이브러리 설치됨")
except ImportError:
    print(f"❌ kiwoom 미설치. 설치 중...")
    subprocess.run([sys.executable, "-m", "pip", "install", "kiwoom", "--no-cache-dir"], check=True)
    import kiwoom
    print(f"✅ kiwoom 설치 완료")

print("\n" + "="*80)
print("STEP 4: PyQt5 확인")
print("="*80)

try:
    from PyQt5.QtWidgets import QApplication
    print("✅ PyQt5 정상")
except ImportError:
    print("❌ PyQt5 미설치. 설치 중...")
    subprocess.run([sys.executable, "-m", "pip", "install", "PyQt5==5.15.9", "--no-cache-dir"], check=True)
    from PyQt5.QtWidgets import QApplication
    print("✅ PyQt5 설치 완료")

print("\n" + "="*80)
print("STEP 5: COM 객체 직접 테스트")
print("="*80)

print("\nCOM 객체 생성 테스트...")

try:
    from PyQt5.QAxContainer import QAxWidget

    print("1. QApplication 생성...")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    print("2. QAxWidget으로 OCX 로드...")
    ocx = QAxWidget()

    # 여러 ProgID 시도
    prog_ids = [
        "KHOPENAPI.KHOpenAPICtrl.1",
        "KHOPENAPI.KHOpenAPICtrl",
        "KHOpenAPI.KHOpenAPICtrl.1",
    ]

    loaded = False
    for prog_id in prog_ids:
        print(f"\n   시도: {prog_id}")
        result = ocx.setControl(prog_id)

        if result:
            print(f"   ✅ 성공! {prog_id}")
            loaded = True
            break
        else:
            print(f"   ❌ 실패")

    if not loaded:
        print("\n❌ 모든 ProgID 로드 실패")
        print("\n💡 문제 해결:")
        print("\n1. 명령 프롬프트를 관리자 권한으로 열고:")
        print(f"   regsvr32 \"{ocx_file}\"")
        print(f"\n2. 성공 메시지가 나타나는지 확인")
        print(f"\n3. 컴퓨터 재부팅")
        print(f"\n4. 이 스크립트 다시 실행")
        sys.exit(1)

    print(f"\n✅ COM 객체 로드 성공!")

except Exception as e:
    print(f"\n❌ COM 객체 테스트 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("STEP 6: breadum/kiwoom 로그인 테스트")
print("="*80)

print("\n🔑 로그인 창을 실행하시겠습니까? (y/n): ", end='')
if input().strip().lower() != 'y':
    print("\n✅ OCX 등록 완료!")
    sys.exit(0)

try:
    from kiwoom import Kiwoom

    print("\n🚀 로그인 창 실행 중...")
    print("="*60)
    print("   - ID/PW/인증서 비밀번호를 입력하세요")
    print("="*60 + "\n")

    api = Kiwoom()
    print("✅ Kiwoom 인스턴스 생성 성공!")

    api.login()
    print("✅ 로그인 성공!")

    # 계좌 정보
    try:
        accounts = api.get_account_list()
        print(f"\n📊 계좌 수: {len(accounts)}")

        if accounts:
            print(f"📋 계좌 목록:")
            for idx, acc in enumerate(accounts, 1):
                print(f"   {idx}. {acc}")

        user_id = api.get_login_info("USER_ID")
        user_name = api.get_login_info("USER_NAME")

        if user_id:
            print(f"👤 사용자 ID: {user_id}")
        if user_name:
            print(f"👤 이름: {user_name}")

    except Exception as e:
        print(f"⚠️  계좌 정보 조회 실패: {e}")

    print("\n" + "="*80)
    print("✨ 모든 테스트 완료!")
    print("="*80)

    print("\n다음 단계:")
    print("  1. openapi_server.py 수정 (breadum/kiwoom 사용)")
    print("  2. main.py는 64비트에서 REST API로 통신")

except Exception as e:
    print(f"\n❌ 로그인 실패: {e}")
    import traceback
    traceback.print_exc()

    print("\n💡 추가 해결 방법:")
    print("\n1. 키움증권 영웅문 실행 → 로그인 → 종료")
    print("2. Windows 재부팅")
    print("3. 스크립트 다시 실행")

print("\n" + "="*80)
