"""
koapy 초상세 로그 테스트
로그인 창이 어디서 막히는지 정확히 확인합니다.
"""
import sys
import os
import logging

os.environ['QT_API'] = 'pyqt5'

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)

koapy_logger = logging.getLogger('koapy')
koapy_logger.setLevel(logging.DEBUG)

print("=" * 70)
print("koapy 초상세 로그 테스트")
print("=" * 70)
print()

print("[1] Qt Application 생성...")
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
print("    ✅ 완료\n")

print("[2] koapy 임포트...")
from koapy import KiwoomOpenApiPlusEntrypoint
print("    ✅ 완료\n")

print("[3] OpenAPI+ OCX 상태 확인...")
import winreg

try:
    key = winreg.OpenKey(
        winreg.HKEY_CLASSES_ROOT,
        r"CLSID\{A1574A0D-6BFA-4BD7-9020-DED88711818D}"
    )
    print("    ✅ OCX가 레지스트리에 등록되어 있습니다")

    ocx_path = winreg.QueryValue(key, "InprocServer32")
    print(f"    ✅ OCX 경로: {ocx_path}")

    if os.path.exists(ocx_path):
        print("    ✅ OCX 파일이 존재합니다")
        size = os.path.getsize(ocx_path) / (1024 * 1024)
        print(f"    ✅ 파일 크기: {size:.2f} MB")
    else:
        print(f"    ❌ OCX 파일이 존재하지 않습니다: {ocx_path}")
        print()
        print("해결 방법:")
        print("1. 키움증권 OpenAPI+ 재설치")
        print("2. 재부팅")
        print("3. 관리자 CMD에서: regsvr32 KHOpenAPI.ocx")
        sys.exit(1)

    winreg.CloseKey(key)
except FileNotFoundError:
    print("    ❌ OCX가 레지스트리에 등록되어 있지 않습니다!")
    print()
    print("해결 방법:")
    print("1. 키움증권 홈페이지 → 투자정보 → HTS/API")
    print("2. 'OpenAPI+' 다운로드 및 설치")
    print("3. 재부팅")
    print("4. 관리자 CMD에서:")
    print("   cd C:\\OpenAPI")
    print("   regsvr32 KHOpenAPI.ocx")
    sys.exit(1)
except Exception as e:
    print(f"    ⚠️  레지스트리 확인 중 오류: {e}")

print()
print("[4] Entrypoint 생성...")
try:
    context = KiwoomOpenApiPlusEntrypoint().__enter__()
    print("    ✅ 완료")
except Exception as e:
    print(f"    ❌ 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("[5] 작업 관리자 확인...")
print("    Ctrl+Shift+Esc를 눌러 작업 관리자를 열고")
print("    '프로세스' 탭에서 다음을 찾아보세요:")
print("    - KHOpenAPI")
print("    - 키움")
print("    - versacomm")
print("    - 이 중 하나라도 있으면 OCX가 로드된 것입니다")
print()
input("확인했으면 Enter 누르세요...")

print()
print("[6] EnsureConnected 호출...")
print("=" * 70)
print("⚠️  로그인 창이 나타나야 합니다!")
print()
print("창이 안 보이면:")
print("  1. Alt+Tab (모든 창 보기)")
print("  2. 작업 표시줄 깜빡임 확인")
print("  3. Win+Tab (가상 데스크톱)")
print("  4. 다른 모니터 확인")
print("=" * 70)
print()

try:
    print("Qt 이벤트 처리 중...")
    for i in range(20):
        app.processEvents()
        import time
        time.sleep(0.1)
        if i % 5 == 0:
            print(f"  ... {i}/20 (지금 Alt+Tab 눌러보세요)")

    print()
    print("EnsureConnected() 호출 중...")
    context.EnsureConnected()

    print()
    print("연결 상태 확인 중...")
    state = context.GetConnectState()

    if state == 1:
        print()
        print("=" * 70)
        print("✅ 로그인 성공!")
        print("=" * 70)
        accounts = context.GetAccountList()
        print(f"계좌: {accounts}")
    else:
        print()
        print("=" * 70)
        print("❌ 로그인 실패")
        print("=" * 70)
        print(f"상태 코드: {state} (1이어야 정상)")

except Exception as e:
    print()
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        context.__exit__(None, None, None)
    except:
        pass

print()
print("=" * 70)
print("테스트 종료")
print("=" * 70)
