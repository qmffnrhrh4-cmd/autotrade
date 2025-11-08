"""
pywin32를 사용하여 직접 키움 OpenAPI 테스트
==============================================
koapy를 사용하지 않고 직접 COM 객체를 사용합니다.
32-bit Python에서만 작동합니다.

사용법:
    conda activate autotrade_32
    python test_direct_openapi.py
"""

import sys
import struct
import os

# Qt 환경 설정
os.environ['QT_API'] = 'pyqt5'

print("=" * 80)
print("  Direct OpenAPI Test (pywin32)")
print("=" * 80)
print()

# 1. 아키텍처 확인
bits = struct.calcsize("P") * 8
print(f"Python: {bits}-bit")

if bits != 32:
    print()
    print("❌ ERROR: 32-bit Python이 필요합니다!")
    print()
    print("실행 방법:")
    print("  conda activate autotrade_32")
    print("  python test_direct_openapi.py")
    input("\n종료하려면 Enter를 누르세요...")
    sys.exit(1)

print("✅ 32-bit Python 확인")
print()

# 2. 필수 모듈 확인
print("필수 모듈 확인 중...")
try:
    import win32com.client
    print("  ✅ win32com.client")
except ImportError:
    print("  ❌ win32com.client 없음")
    print()
    print("설치:")
    print("  pip install pywin32")
    input("\n종료하려면 Enter를 누르세요...")
    sys.exit(1)

try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QEventLoop, QTimer
    print("  ✅ PyQt5")
except ImportError as e:
    print(f"  ❌ PyQt5 import 실패: {e}")
    print()

    # 더 자세한 진단
    print("진단 중...")
    try:
        import PyQt5
        print(f"  - PyQt5 모듈은 있음: {PyQt5.__file__}")
        print(f"  - 하지만 QtWidgets를 import할 수 없음")
        print()
        print("  해결책:")
        print("    pip uninstall PyQt5 PyQt5-Qt5 PyQt5-sip -y")
        print("    pip install PyQt5")
    except ImportError:
        print("  - PyQt5 모듈 자체가 없음")
        print()
        print("  설치:")
        print("    pip install PyQt5")

    print()
    import traceback
    traceback.print_exc()

    input("\n종료하려면 Enter를 누르세요...")
    sys.exit(1)

print()

# 3. Qt Application 생성
print("Qt Application 생성 중...")
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)
    print("✅ Qt Application 생성됨")
else:
    print("✅ Qt Application 이미 존재")
print()

# 4. OpenAPI COM 객체 생성
print("=" * 80)
print("  OpenAPI COM 객체 생성")
print("=" * 80)
print()

print("키움증권 OpenAPI OCX를 로드하는 중...")
print("(시간이 걸릴 수 있습니다)")
print()

try:
    # COM 객체 생성
    ocx = win32com.client.DispatchEx("KHOPENAPI.KHOpenAPICtrl.1")
    print("✅ COM 객체 생성 성공!")
    print(f"   객체 타입: {type(ocx)}")
    print()

except Exception as e:
    print(f"❌ COM 객체 생성 실패: {e}")
    print()
    print("해결 방법:")
    print("  1. 키움증권 OpenAPI+ 설치 확인")
    print("  2. 관리자 권한으로 실행")
    print("  3. Windows 재부팅")
    input("\n종료하려면 Enter를 누르세요...")
    sys.exit(1)

# 5. 이벤트 핸들러 설정
print("=" * 80)
print("  이벤트 핸들러 설정")
print("=" * 80)
print()

login_success = False
login_event_received = False

class EventHandler:
    """OpenAPI 이벤트 핸들러"""

    def OnEventConnect(self, err_code):
        """로그인 결과 이벤트"""
        global login_success, login_event_received

        print(f"\n[이벤트] OnEventConnect: err_code={err_code}")

        login_event_received = True

        if err_code == 0:
            print("✅ 로그인 성공!")
            login_success = True
        else:
            print(f"❌ 로그인 실패: {err_code}")
            login_success = False

    def OnReceiveTrData(self, *args):
        """TR 데이터 수신 이벤트"""
        print(f"[이벤트] OnReceiveTrData")

    def OnReceiveRealData(self, *args):
        """실시간 데이터 수신 이벤트"""
        pass

    def OnReceiveMsg(self, *args):
        """메시지 수신 이벤트"""
        print(f"[이벤트] OnReceiveMsg: {args}")

    def OnReceiveChejanData(self, *args):
        """체결 데이터 수신 이벤트"""
        pass

try:
    import win32com.client
    handler = win32com.client.WithEvents(ocx, EventHandler)
    print("✅ 이벤트 핸들러 등록 완료")
    print()
except Exception as e:
    print(f"❌ 이벤트 핸들러 등록 실패: {e}")
    import traceback
    traceback.print_exc()
    input("\n종료하려면 Enter를 누르세요...")
    sys.exit(1)

# 6. 로그인 시도
print("=" * 80)
print("  로그인 시도")
print("=" * 80)
print()

print("⚠️  잠시 후 키움증권 로그인 창이 나타납니다!")
print("⚠️  로그인 창에서 ID/PW를 입력하고 로그인하세요.")
print()
print("CommConnect() 호출 중...")
print()

try:
    # Qt 이벤트 처리
    app.processEvents()

    # CommConnect 호출
    ret = ocx.CommConnect()

    print(f"CommConnect() 반환값: {ret}")

    if ret == 0:
        print("✅ CommConnect() 호출 성공!")
        print()
        print("로그인 창이 나타나야 합니다...")
        print("로그인을 완료하세요. (최대 60초 대기)")
        print()

        # Qt 이벤트 루프로 대기 (로그인 창 표시)
        import time
        timeout = 60  # 60초 타임아웃

        for i in range(timeout):
            app.processEvents()  # Qt 이벤트 처리
            time.sleep(1)

            if login_event_received:
                break

            if i % 10 == 0 and i > 0:
                print(f"  대기 중... ({i}초)")

        if not login_event_received:
            print()
            print("⚠️  타임아웃: 로그인 이벤트를 받지 못했습니다")
            print("    로그인 창이 나타났나요?")
            print()

    else:
        print(f"❌ CommConnect() 실패: {ret}")

except Exception as e:
    print(f"❌ 로그인 오류: {e}")
    import traceback
    traceback.print_exc()

# 7. 결과 확인
print()
print("=" * 80)
print("  결과 확인")
print("=" * 80)
print()

if login_success:
    print("✅✅✅ 로그인 성공!")
    print()

    # 연결 상태 확인
    try:
        state = ocx.GetConnectState()
        print(f"연결 상태: {state} (1=연결됨, 0=연결안됨)")

        if state == 1:
            # 계좌 정보 조회
            try:
                account_cnt = ocx.GetLoginInfo("ACCOUNT_CNT")
                accounts = ocx.GetLoginInfo("ACCNO")
                user_id = ocx.GetLoginInfo("USER_ID")
                user_name = ocx.GetLoginInfo("USER_NM")

                print()
                print("계정 정보:")
                print(f"  사용자 ID: {user_id}")
                print(f"  사용자 이름: {user_name}")
                print(f"  계좌 개수: {account_cnt}")
                print(f"  계좌 목록: {accounts}")
                print()

                print("✅✅✅ 테스트 완료!")
                print()
                print("이제 pywin32로 OpenAPI를 사용할 수 있습니다.")

            except Exception as e:
                print(f"⚠️  계정 정보 조회 실패: {e}")
        else:
            print("⚠️  연결되지 않음")
    except Exception as e:
        print(f"⚠️  상태 확인 실패: {e}")
else:
    print("❌ 로그인 실패")
    print()
    print("문제 해결:")
    print("  1. 로그인 창이 나타났나요?")
    print("     - 안 나타남: 키움증권 OpenAPI+ 재설치")
    print("     - 나타남: ID/PW 확인")
    print("  2. 키움증권 OpenAPI+ 정상 설치 확인")
    print("  3. 다른 프로그램에서 OpenAPI 사용 중인지 확인")

print()
input("종료하려면 Enter를 누르세요...")
