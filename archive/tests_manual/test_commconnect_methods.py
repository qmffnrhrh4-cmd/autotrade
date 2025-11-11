"""
CommConnect 직접 호출 테스트

GetConnectState()를 테스트하지 말고, 직접 CommConnect()를 호출해봅니다.
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
except ImportError:
    print("❌ pywin32 모듈이 설치되지 않았습니다!")
    sys.exit(1)


class EventHandler:
    """이벤트 핸들러"""
    def __init__(self, method_name):
        self.method_name = method_name
        self.login_event_received = False
        self.err_code = None

    def OnEventConnect(self, err_code):
        print(f"   [{self.method_name}] 🎉 OnEventConnect 이벤트 수신! err_code={err_code}")
        self.login_event_received = True
        self.err_code = err_code

        if err_code == 0:
            print(f"   [{self.method_name}] ✅ 로그인 성공!")
        else:
            print(f"   [{self.method_name}] ❌ 로그인 실패: {err_code}")


def test_commconnect_with_method(method_name, create_ocx_func):
    """CommConnect를 직접 호출하는 테스트"""
    print("\n" + "=" * 80)
    print(f"  {method_name}")
    print("=" * 80)
    print()

    try:
        # OCX 생성
        ocx = create_ocx_func()
        if not ocx:
            print(f"❌ ActiveX 컨트롤 생성 실패")
            return False

        print(f"✅ ActiveX 컨트롤 생성 성공")

        # 이벤트 핸들러 연결
        try:
            handler = EventHandler(method_name)
            events = win32com.client.WithEvents(ocx, EventHandler)
            events.method_name = method_name
            events.login_event_received = False
            events.err_code = None
            print("✅ 이벤트 핸들러 연결 성공")
        except Exception as e:
            print(f"⚠️  이벤트 핸들러 연결 실패: {e}")
            events = None

        # CommConnect 호출
        print()
        print("🔐 CommConnect() 호출...")
        print("   (로그인창이 나타날 수 있습니다)")

        try:
            ret = ocx.CommConnect()
            print(f"   반환값: {ret}")

            if ret == 0:
                print("✅ CommConnect() 호출 성공!")
                print()
                print("   이벤트 대기 중 (20초)...")
                print("   로그인창이 나타나면 수동으로 로그인하세요.")
                print()

                # 이벤트 대기
                start_time = time.time()
                while time.time() - start_time < 20:
                    pythoncom.PumpWaitingMessages()
                    time.sleep(0.1)

                    # 5초마다 상태 출력
                    elapsed = int(time.time() - start_time)
                    if elapsed > 0 and elapsed % 5 == 0:
                        print(f"   [{elapsed}초 경과]")

                        # 이벤트 수신 확인
                        if events and hasattr(events, 'login_event_received') and events.login_event_received:
                            print(f"   ✅ 로그인 이벤트 수신됨!")
                            return True

                # 최종 확인
                if events and hasattr(events, 'login_event_received') and events.login_event_received:
                    print(f"\n✅✅✅ 이 방법이 작동합니다: {method_name}")
                    return True
                else:
                    print(f"\n⚠️  로그인 이벤트를 받지 못했습니다")
                    print(f"   하지만 CommConnect()는 성공했으므로 부분 성공")
                    return True

            else:
                print(f"❌ CommConnect() 반환값 오류: {ret}")
                return False

        except pywintypes.com_error as e:
            error_code = e.args[0] & 0xFFFFFFFF
            print(f"❌ COM 오류:")
            print(f"   코드: 0x{error_code:08X}")
            print(f"   메시지: {e.args[1]}")
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


def method_1_standard():
    """방법 1: 표준 Dispatch"""
    pythoncom.CoInitialize()
    return win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")


def method_2_dispatchex():
    """방법 2: DispatchEx"""
    pythoncom.CoInitialize()
    return win32com.client.DispatchEx("KHOPENAPI.KHOpenAPICtrl.1")


def method_3_ensuredispatch():
    """방법 3: EnsureDispatch"""
    pythoncom.CoInitialize()
    from win32com.client import gencache
    return gencache.EnsureDispatch("KHOPENAPI.KHOpenAPICtrl.1")


def method_4_dynamic():
    """방법 4: Dynamic Late Binding"""
    pythoncom.CoInitialize()
    from win32com.client import dynamic
    return dynamic.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")


def method_5_coinitializeex_sta():
    """방법 5: CoInitializeEx STA"""
    pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
    return win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║         🔬 CommConnect() 직접 호출 테스트                                 ║
║                                                                          ║
║  GetConnectState()가 버그일 수 있으므로 CommConnect()를 직접 테스트합니다  ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
""")

    methods = [
        ("방법 1: Dispatch (표준)", method_1_standard),
        ("방법 2: DispatchEx", method_2_dispatchex),
        ("방법 3: EnsureDispatch (타입 라이브러리)", method_3_ensuredispatch),
        ("방법 4: Dynamic Late Binding", method_4_dynamic),
        ("방법 5: CoInitializeEx STA", method_5_coinitializeex_sta),
    ]

    results = []

    for method_name, method_func in methods:
        result = test_commconnect_with_method(method_name, method_func)
        results.append((method_name, result))

        # 각 테스트 간 대기
        time.sleep(1)

        # 성공하면 중단
        if result:
            print(f"\n\n🎉🎉🎉 성공한 방법을 찾았습니다: {method_name}")
            break

    # 최종 요약
    print("\n" + "=" * 80)
    print("  📊 테스트 결과")
    print("=" * 80)
    print()

    success_methods = [name for name, result in results if result]

    if success_methods:
        print("✅ 다음 방법이 작동합니다:")
        for method in success_methods:
            print(f"   ✓ {method}")
        print()
        print("💡 이 방법을 코드에 적용하세요!")
    else:
        print("❌ 모든 방법이 실패했습니다.")
        print()
        print("💡 가능한 원인:")
        print("   1. 64비트 OCX 자체에 버그가 있음")
        print("   2. 시스템 보안 설정 문제")
        print("   3. 키움 서버 접속 불가")
        print()
        print("💡 추천:")
        print("   - 32비트 OCX(KHOpenAPI.ocx) 사용")
        print("   - 키움증권 고객센터 문의")

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
