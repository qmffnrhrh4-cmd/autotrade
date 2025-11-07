"""
간단한 COM 초기화 및 CommConnect 테스트

여러 가지 COM 초기화 방식을 시도합니다.
"""
import sys
import time

try:
    import win32com.client
    import pythoncom
    import pywintypes
except ImportError:
    print("❌ pywin32 모듈이 설치되지 않았습니다!")
    print("   pip install pywin32")
    sys.exit(1)


def test_method_1():
    """방법 1: CoInitialize"""
    print("\n" + "="*80)
    print("테스트 1: CoInitialize (기본)")
    print("="*80)

    try:
        pythoncom.CoInitialize()
        print("✅ COM 초기화 성공")

        ocx = win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")
        print("✅ ActiveX 생성 성공")

        # GetAPIModulePath 테스트
        try:
            path = ocx.GetAPIModulePath()
            print(f"✅ GetAPIModulePath 성공: {path}")
        except Exception as e:
            print(f"❌ GetAPIModulePath 실패: {e}")

        # CommConnect 테스트
        print("\n⏳ CommConnect 호출 중...")
        ret = ocx.CommConnect()
        print(f"   반환값: {ret}")

        if ret == 0:
            print("✅ CommConnect 성공!")
            print("   (로그인 창이 나타나야 합니다)")

            # 5초 대기
            for i in range(5):
                pythoncom.PumpWaitingMessages()
                time.sleep(1)
                print(f"   {i+1}/5 대기 중...")
        else:
            print(f"❌ CommConnect 실패: {ret}")

        pythoncom.CoUninitialize()
        return True

    except pywintypes.com_error as e:
        error_code = e.args[0]
        print(f"❌ COM 오류: {error_code} (0x{error_code & 0xFFFFFFFF:08X})")
        print(f"   메시지: {e.args[1]}")
        return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_method_2():
    """방법 2: CoInitializeEx APARTMENTTHREADED"""
    print("\n" + "="*80)
    print("테스트 2: CoInitializeEx(COINIT_APARTMENTTHREADED)")
    print("="*80)

    try:
        pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
        print("✅ COM 초기화 성공 (APARTMENTTHREADED)")

        ocx = win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")
        print("✅ ActiveX 생성 성공")

        # GetAPIModulePath 테스트
        try:
            path = ocx.GetAPIModulePath()
            print(f"✅ GetAPIModulePath 성공: {path}")
        except Exception as e:
            print(f"❌ GetAPIModulePath 실패: {e}")

        # CommConnect 테스트
        print("\n⏳ CommConnect 호출 중...")
        ret = ocx.CommConnect()
        print(f"   반환값: {ret}")

        if ret == 0:
            print("✅ CommConnect 성공!")
            print("   (로그인 창이 나타나야 합니다)")

            # 5초 대기
            for i in range(5):
                pythoncom.PumpWaitingMessages()
                time.sleep(1)
                print(f"   {i+1}/5 대기 중...")
        else:
            print(f"❌ CommConnect 실패: {ret}")

        pythoncom.CoUninitialize()
        return True

    except pywintypes.com_error as e:
        error_code = e.args[0]
        print(f"❌ COM 오류: {error_code} (0x{error_code & 0xFFFFFFFF:08X})")
        print(f"   메시지: {e.args[1]}")
        return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_method_3():
    """방법 3: CoInitializeEx MULTITHREADED"""
    print("\n" + "="*80)
    print("테스트 3: CoInitializeEx(COINIT_MULTITHREADED)")
    print("="*80)

    try:
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
        print("✅ COM 초기화 성공 (MULTITHREADED)")

        ocx = win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")
        print("✅ ActiveX 생성 성공")

        # GetAPIModulePath 테스트
        try:
            path = ocx.GetAPIModulePath()
            print(f"✅ GetAPIModulePath 성공: {path}")
        except Exception as e:
            print(f"❌ GetAPIModulePath 실패: {e}")

        # CommConnect 테스트
        print("\n⏳ CommConnect 호출 중...")
        ret = ocx.CommConnect()
        print(f"   반환값: {ret}")

        if ret == 0:
            print("✅ CommConnect 성공!")
            print("   (로그인 창이 나타나야 합니다)")

            # 5초 대기
            for i in range(5):
                pythoncom.PumpWaitingMessages()
                time.sleep(1)
                print(f"   {i+1}/5 대기 중...")
        else:
            print(f"❌ CommConnect 실패: {ret}")

        pythoncom.CoUninitialize()
        return True

    except pywintypes.com_error as e:
        error_code = e.args[0]
        print(f"❌ COM 오류: {error_code} (0x{error_code & 0xFFFFFFFF:08X})")
        print(f"   메시지: {e.args[1]}")
        return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║                  🔍 COM 초기화 방식 테스트                                              ║
║                                                                                      ║
║  목적: 어떤 COM 초기화 방식이 작동하는지 확인                                             ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
""")

    print("⚠️  중요: 이 테스트는 관리자 권한으로 실행해야 합니다!")
    print("   명령 프롬프트를 우클릭 → '관리자 권한으로 실행'\n")

    input("계속하려면 Enter를 누르세요...")

    results = []

    # 테스트 1
    try:
        result1 = test_method_1()
        results.append(("CoInitialize", result1))
    except Exception as e:
        print(f"테스트 1 실패: {e}")
        results.append(("CoInitialize", False))

    time.sleep(2)

    # 테스트 2
    try:
        result2 = test_method_2()
        results.append(("CoInitializeEx APARTMENTTHREADED", result2))
    except Exception as e:
        print(f"테스트 2 실패: {e}")
        results.append(("CoInitializeEx APARTMENTTHREADED", False))

    time.sleep(2)

    # 테스트 3
    try:
        result3 = test_method_3()
        results.append(("CoInitializeEx MULTITHREADED", result3))
    except Exception as e:
        print(f"테스트 3 실패: {e}")
        results.append(("CoInitializeEx MULTITHREADED", False))

    # 결과 요약
    print("\n" + "="*80)
    print("📊 테스트 결과 요약")
    print("="*80)

    for method, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"   {method:40} : {status}")

    print("\n" + "="*80)

    if all(not success for _, success in results):
        print("\n⚠️  모든 테스트 실패!")
        print("\n💡 해결 방법:")
        print("   1. 64bit-kiwoom-openapi 재설치")
        print("   2. PC 재부팅")
        print("   3. Windows 방화벽 설정")
        print("   4. 백신 프로그램 일시 중지")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    print("\n창을 닫으려면 Enter를 누르세요...")
    input()
