"""
다양한 COM 초기화 방법 테스트

64비트 OCX가 특정 COM 초기화 방법에서만 작동할 수 있습니다.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import win32com.client
    import pythoncom
    import pywintypes
except ImportError:
    print("❌ pywin32 모듈이 설치되지 않았습니다!")
    print("   pip install pywin32")
    sys.exit(1)


def test_method_1_coinitialize():
    """방법 1: pythoncom.CoInitialize() - STA 모드"""
    print("=" * 80)
    print("  방법 1: CoInitialize() - Single Threaded Apartment")
    print("=" * 80)
    print()

    try:
        # COM 초기화
        pythoncom.CoInitialize()
        print("✅ CoInitialize() 성공")

        # ActiveX 생성
        ocx = win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")
        print("✅ ActiveX 컨트롤 생성 성공")

        # GetConnectState 테스트
        try:
            state = ocx.GetConnectState()
            print(f"✅ GetConnectState() 호출 성공: {state}")
            return True
        except Exception as e:
            print(f"❌ GetConnectState() 실패: {e}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass


def test_method_2_coinitializeex_sta():
    """방법 2: pythoncom.CoInitializeEx(COINIT_APARTMENTTHREADED)"""
    print("\n" + "=" * 80)
    print("  방법 2: CoInitializeEx(COINIT_APARTMENTTHREADED)")
    print("=" * 80)
    print()

    try:
        # COM 초기화
        pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
        print("✅ CoInitializeEx(COINIT_APARTMENTTHREADED) 성공")

        # ActiveX 생성
        ocx = win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")
        print("✅ ActiveX 컨트롤 생성 성공")

        # GetConnectState 테스트
        try:
            state = ocx.GetConnectState()
            print(f"✅ GetConnectState() 호출 성공: {state}")
            return True
        except Exception as e:
            print(f"❌ GetConnectState() 실패: {e}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass


def test_method_3_coinitializeex_mta():
    """방법 3: pythoncom.CoInitializeEx(COINIT_MULTITHREADED)"""
    print("\n" + "=" * 80)
    print("  방법 3: CoInitializeEx(COINIT_MULTITHREADED)")
    print("=" * 80)
    print()

    try:
        # COM 초기화
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
        print("✅ CoInitializeEx(COINIT_MULTITHREADED) 성공")

        # ActiveX 생성
        ocx = win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")
        print("✅ ActiveX 컨트롤 생성 성공")

        # GetConnectState 테스트
        try:
            state = ocx.GetConnectState()
            print(f"✅ GetConnectState() 호출 성공: {state}")
            return True
        except Exception as e:
            print(f"❌ GetConnectState() 실패: {e}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass


def test_method_4_dispatchex():
    """방법 4: DispatchEx 사용"""
    print("\n" + "=" * 80)
    print("  방법 4: DispatchEx (로컬 서버 강제)")
    print("=" * 80)
    print()

    try:
        # COM 초기화
        pythoncom.CoInitialize()
        print("✅ CoInitialize() 성공")

        # DispatchEx 사용 (로컬 서버 강제)
        ocx = win32com.client.DispatchEx("KHOPENAPI.KHOpenAPICtrl.1")
        print("✅ DispatchEx로 ActiveX 컨트롤 생성 성공")

        # GetConnectState 테스트
        try:
            state = ocx.GetConnectState()
            print(f"✅ GetConnectState() 호출 성공: {state}")
            return True
        except Exception as e:
            print(f"❌ GetConnectState() 실패: {e}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass


def test_method_5_gencache():
    """방법 5: EnsureDispatch (타입 라이브러리 생성)"""
    print("\n" + "=" * 80)
    print("  방법 5: EnsureDispatch (타입 라이브러리 캐싱)")
    print("=" * 80)
    print()

    try:
        # COM 초기화
        pythoncom.CoInitialize()
        print("✅ CoInitialize() 성공")

        # gencache 사용
        from win32com.client import gencache
        print("✓ gencache 모듈 로드")

        # EnsureDispatch로 타입 라이브러리 생성
        ocx = gencache.EnsureDispatch("KHOPENAPI.KHOpenAPICtrl.1")
        print("✅ EnsureDispatch로 ActiveX 컨트롤 생성 성공")

        # GetConnectState 테스트
        try:
            state = ocx.GetConnectState()
            print(f"✅ GetConnectState() 호출 성공: {state}")
            return True
        except Exception as e:
            print(f"❌ GetConnectState() 실패: {e}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass


def test_method_6_clsid_direct():
    """방법 6: CLSID로 직접 생성"""
    print("\n" + "=" * 80)
    print("  방법 6: CLSID로 직접 생성")
    print("=" * 80)
    print()

    try:
        # COM 초기화
        pythoncom.CoInitialize()
        print("✅ CoInitialize() 성공")

        # CLSID로 직접 생성
        clsid = "{A1574A0D-6BFA-4BD7-9020-DED88711818D}"
        ocx = win32com.client.Dispatch(clsid)
        print(f"✅ CLSID {clsid}로 ActiveX 컨트롤 생성 성공")

        # GetConnectState 테스트
        try:
            state = ocx.GetConnectState()
            print(f"✅ GetConnectState() 호출 성공: {state}")
            return True
        except Exception as e:
            print(f"❌ GetConnectState() 실패: {e}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass


def test_method_7_dynamic_late_binding():
    """방법 7: Late Binding (동적) vs Early Binding"""
    print("\n" + "=" * 80)
    print("  방법 7: Late Binding 명시적 사용")
    print("=" * 80)
    print()

    try:
        # COM 초기화
        pythoncom.CoInitialize()
        print("✅ CoInitialize() 성공")

        # Late Binding 명시적으로
        from win32com.client import dynamic
        ocx = dynamic.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")
        print("✅ dynamic.Dispatch로 ActiveX 컨트롤 생성 성공")

        # GetConnectState 테스트
        try:
            state = ocx.GetConnectState()
            print(f"✅ GetConnectState() 호출 성공: {state}")
            return True
        except Exception as e:
            print(f"❌ GetConnectState() 실패: {e}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
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
║           🔬 다양한 COM 초기화 방법 테스트                                ║
║                                                                          ║
║  64비트 OCX가 특정 초기화 방법에서만 작동할 수 있습니다                    ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
""")

    methods = [
        ("CoInitialize()", test_method_1_coinitialize),
        ("CoInitializeEx(STA)", test_method_2_coinitializeex_sta),
        ("CoInitializeEx(MTA)", test_method_3_coinitializeex_mta),
        ("DispatchEx", test_method_4_dispatchex),
        ("EnsureDispatch", test_method_5_gencache),
        ("CLSID 직접", test_method_6_clsid_direct),
        ("Late Binding", test_method_7_dynamic_late_binding),
    ]

    results = []

    for name, test_func in methods:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 테스트 중 예외 발생: {e}")
            results.append((name, False))

        # 각 테스트 간 대기
        import time
        time.sleep(0.5)

    # 최종 요약
    print("\n" + "=" * 80)
    print("  📊 테스트 결과 요약")
    print("=" * 80)
    print()

    success_count = 0
    for name, result in results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{status} - {name}")
        if result:
            success_count += 1

    print()

    if success_count > 0:
        print(f"✅ {success_count}개 방법이 작동합니다!")
        print()
        print("💡 성공한 방법을 코드에 적용하세요:")
        print()
        for name, result in results:
            if result:
                print(f"   - {name}")
    else:
        print("❌ 모든 방법이 실패했습니다.")
        print()
        print("💡 가능한 원인:")
        print("   1. Python이 32비트 (64비트 필요)")
        print("      → python tests/manual/test_python_bitness.py 실행")
        print("   2. OCX 파일 손상")
        print("      → C:\\OpenAPI\\register.bat 재등록")
        print("   3. Visual C++ 런타임 누락")
        print("      → VC++ Redistributable 2015-2022 x64 설치")
        print("   4. 64비트 OCX 자체 버그")
        print("      → 32비트 버전 사용 고려")

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
