"""
koapy 라이브러리의 패턴을 적용한 64비트 OCX 테스트

koapy는 실제로 32비트를 사용하지만, 그들이 사용하는 패턴을 적용해봅니다.
"""
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import win32com.client
    import pythoncom
    import pywintypes
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QAxContainer import QAxWidget
except ImportError as e:
    print(f"❌ 필요한 모듈이 설치되지 않았습니다: {e}")
    print("\n설치 방법:")
    print("  pip install pywin32 PyQt5")
    sys.exit(1)


class KiwoomOCX:
    """koapy 패턴을 적용한 키움 OCX 래퍼"""

    CLSID = "{A1574A0D-6BFA-4BD7-9020-DED88711818D}"
    PROGID = "KHOPENAPI.KHOpenAPICtrl.1"

    def __init__(self):
        self.control = None
        self.login_event_received = False
        self.login_err_code = None

    def on_exception(self, code, source, desc, help_):
        """Exception 핸들러"""
        print(f"   [Exception] code={code}, source={source}, desc={desc}")

    def on_event_connect(self, err_code):
        """OnEventConnect 이벤트 핸들러"""
        print(f"   [OnEventConnect] err_code={err_code}")
        self.login_event_received = True
        self.login_err_code = err_code

        if err_code == 0:
            print("   ✅ 로그인 성공!")
        else:
            print(f"   ❌ 로그인 실패: {err_code}")


def test_pattern_1_qapplication_instance():
    """패턴 1: QApplication.instance() 체크"""
    print("=" * 80)
    print("  패턴 1: QApplication.instance() 재사용 패턴")
    print("=" * 80)
    print()

    try:
        # QApplication.instance() 먼저 확인 (koapy 패턴)
        app = QApplication.instance()
        if app is None:
            print("✓ QApplication 새로 생성")
            app = QApplication(sys.argv)
        else:
            print("✓ 기존 QApplication 재사용")

        # QAxWidget 생성
        print("✓ QAxWidget 생성 시도...")
        control = QAxWidget()

        # Control 설정
        success = control.setControl(KiwoomOCX.PROGID)
        if not success:
            print(f"❌ setControl 실패")
            return False

        print("✅ QAxWidget 생성 성공")

        # isNull() 체크 (koapy 패턴)
        if control.isNull():
            print("❌ Control이 null입니다!")
            return False

        print("✅ Control null이 아님 확인")

        # Exception 핸들러 연결 (koapy 패턴)
        ocx = KiwoomOCX()
        ocx.control = control

        try:
            control.exception.connect(ocx.on_exception)
            print("✅ Exception 핸들러 연결 성공")
        except Exception as e:
            print(f"⚠️  Exception 핸들러 연결 실패: {e}")

        # OnEventConnect 먼저 연결 (koapy 패턴)
        try:
            control.OnEventConnect.connect(ocx.on_event_connect)
            print("✅ OnEventConnect 이벤트 핸들러 연결 성공")
        except Exception as e:
            print(f"❌ OnEventConnect 연결 실패: {e}")
            return False

        # CommConnect 호출
        print()
        print("🔐 CommConnect() 호출...")

        try:
            ret = control.dynamicCall("CommConnect()")
            print(f"   반환값: {ret}")

            if ret == 0:
                print("✅ CommConnect() 호출 성공!")
                print()
                print("   이벤트 대기 중 (20초)...")

                # 이벤트 루프 실행
                start_time = time.time()
                while time.time() - start_time < 20:
                    app.processEvents()
                    time.sleep(0.1)

                    if ocx.login_event_received:
                        print(f"\n✅✅✅ 로그인 이벤트 수신! err_code={ocx.login_err_code}")
                        return True

                    # 5초마다 상태 출력
                    elapsed = int(time.time() - start_time)
                    if elapsed > 0 and elapsed % 5 == 0:
                        print(f"   [{elapsed}초 경과]")

                if ocx.login_event_received:
                    return True
                else:
                    print("\n⚠️  타임아웃: 로그인 이벤트를 받지 못했습니다")
                    return False
            else:
                print(f"❌ CommConnect() 반환값 오류: {ret}")
                return False

        except Exception as e:
            print(f"❌ CommConnect() 호출 실패: {e}")
            return False

    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pattern_2_pywin32_with_koapy_order():
    """패턴 2: pywin32 + koapy 순서 패턴"""
    print("\n" + "=" * 80)
    print("  패턴 2: pywin32 + OnEventConnect 먼저 연결")
    print("=" * 80)
    print()

    try:
        # COM 초기화
        pythoncom.CoInitialize()
        print("✅ CoInitialize() 성공")

        # Dispatch
        control = win32com.client.Dispatch(KiwoomOCX.PROGID)
        print("✅ Dispatch 성공")

        # 이벤트 핸들러 객체
        ocx = KiwoomOCX()

        # WithEvents로 이벤트 핸들러 연결 (koapy처럼 CommConnect 전에)
        class EventHandler:
            def __init__(self, parent):
                self.parent = parent

            def OnEventConnect(self, err_code):
                print(f"   [OnEventConnect] err_code={err_code}")
                self.parent.login_event_received = True
                self.parent.login_err_code = err_code

                if err_code == 0:
                    print("   ✅ 로그인 성공!")
                else:
                    print(f"   ❌ 로그인 실패: {err_code}")

        # 이벤트 먼저 연결!
        handler = EventHandler(ocx)
        events = win32com.client.WithEvents(control, EventHandler)
        events.parent = ocx
        print("✅ 이벤트 핸들러 먼저 연결 성공")

        # 이제 CommConnect 호출
        print()
        print("🔐 CommConnect() 호출...")

        try:
            ret = control.CommConnect()
            print(f"   반환값: {ret}")

            if ret == 0:
                print("✅ CommConnect() 호출 성공!")
                print()
                print("   이벤트 대기 중 (20초)...")

                # 이벤트 펌프
                start_time = time.time()
                while time.time() - start_time < 20:
                    pythoncom.PumpWaitingMessages()
                    time.sleep(0.1)

                    if ocx.login_event_received:
                        print(f"\n✅✅✅ 로그인 이벤트 수신! err_code={ocx.login_err_code}")
                        return True

                    elapsed = int(time.time() - start_time)
                    if elapsed > 0 and elapsed % 5 == 0:
                        print(f"   [{elapsed}초 경과]")

                if ocx.login_event_received:
                    return True
                else:
                    print("\n⚠️  타임아웃: 로그인 이벤트를 받지 못했습니다")
                    return False
            else:
                print(f"❌ CommConnect() 반환값 오류: {ret}")
                return False

        except Exception as e:
            print(f"❌ CommConnect() 호출 실패: {e}")
            return False

    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║           🔬 koapy 패턴 적용 테스트                                       ║
║                                                                          ║
║  koapy 라이브러리의 패턴을 64비트 OCX에 적용해봅니다                       ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

⚠️  주의: koapy는 실제로 32비트 Python을 사용합니다.
   64비트 OCX 자체에 버그가 있을 가능성이 높습니다.

   하지만 koapy의 패턴이 도움이 될 수 있습니다:
   - QApplication.instance() 재사용
   - OnEventConnect를 CommConnect 전에 연결
   - Exception 핸들러 연결
   - isNull() 체크

""")

    # Python 비트 확인
    import platform
    import struct
    bits = struct.calcsize("P") * 8
    print(f"현재 Python: {bits}-bit")
    print()

    methods = [
        ("QAxWidget + QApplication 패턴", test_pattern_1_qapplication_instance),
        ("pywin32 + 이벤트 우선 연결", test_pattern_2_pywin32_with_koapy_order),
    ]

    results = []

    for method_name, test_func in methods:
        try:
            result = test_func()
            results.append((method_name, result))

            if result:
                print(f"\n\n🎉🎉🎉 성공한 방법: {method_name}")
                break
        except Exception as e:
            print(f"\n❌ {method_name} 테스트 중 예외: {e}")
            results.append((method_name, False))

        time.sleep(1)

    # 최종 요약
    print("\n" + "=" * 80)
    print("  📊 테스트 결과")
    print("=" * 80)
    print()

    success_methods = [name for name, result in results if result]

    if success_methods:
        print("✅ 성공한 방법:")
        for method in success_methods:
            print(f"   ✓ {method}")
    else:
        print("❌ 모든 방법이 실패했습니다.")
        print()
        print("💡 결론:")
        print("   64비트 OCX(KHOpenAPI64.ocx)에 근본적인 문제가 있습니다.")
        print()
        print("📌 권장 해결책:")
        print("   1. 32비트 OCX(KHOpenAPI.ocx) 사용")
        print("   2. 32비트 Python 환경 구축")
        print("   3. 또는 koapy 라이브러리 사용 (32비트 서버 + gRPC)")
        print()
        print("   koapy도 32비트 환경을 assertion으로 강제합니다:")
        print('   assert platform.architecture()[0] == "32bit"')

    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()

    print("\n창을 닫으려면 Enter를 누르세요...")
    input()
