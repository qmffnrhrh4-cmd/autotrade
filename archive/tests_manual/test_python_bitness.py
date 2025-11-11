"""
Python 비트 및 환경 상세 확인 스크립트

64비트 OCX는 반드시 64비트 Python에서만 작동합니다.
"""
import sys
import platform
import struct


def check_python_bitness():
    """Python 32/64비트 확인"""
    print("=" * 80)
    print("  🐍 Python 환경 정보")
    print("=" * 80)
    print()

    # 방법 1: struct.calcsize
    bits = struct.calcsize("P") * 8
    print(f"✓ Python 비트 (struct.calcsize): {bits}-bit")

    # 방법 2: platform.architecture
    arch = platform.architecture()
    print(f"✓ Platform architecture: {arch[0]} ({arch[1]})")

    # 방법 3: sys.maxsize
    is_64bit = sys.maxsize > 2**32
    print(f"✓ sys.maxsize 기반: {'64-bit' if is_64bit else '32-bit'}")

    # Python 버전
    print(f"✓ Python 버전: {sys.version}")
    print(f"✓ Python 실행 파일: {sys.executable}")

    # 플랫폼 정보
    print(f"✓ 플랫폼: {platform.platform()}")
    print(f"✓ 머신: {platform.machine()}")
    print(f"✓ 프로세서: {platform.processor()}")

    print()

    # 경고 메시지
    if bits == 32:
        print("⚠️  경고: 32비트 Python 감지!")
        print("   64비트 OCX(KHOpenAPI64.ocx)는 32비트 Python에서 작동하지 않습니다.")
        print()
        print("   해결 방법:")
        print("   1. 64비트 Python 설치")
        print("   2. 또는 32비트 OCX(KHOpenAPI.ocx) 사용")
        print()
        return False
    else:
        print("✅ 64비트 Python 확인")
        print("   64비트 OCX를 사용할 수 있습니다.")
        print()
        return True


def check_pywin32():
    """pywin32 모듈 확인"""
    print("=" * 80)
    print("  📦 pywin32 모듈 정보")
    print("=" * 80)
    print()

    try:
        import win32com
        import win32com.client
        import pythoncom
        import pywintypes

        print("✅ pywin32 모듈 설치됨")

        # pywin32 경로
        import win32com
        print(f"✓ win32com 위치: {win32com.__file__}")

        # 버전 확인 시도
        try:
            import win32api
            pywin32_version = win32api.GetFileVersionInfo(
                win32api.__file__, '\\'
            )
            print(f"✓ pywin32 버전 정보: {pywin32_version}")
        except:
            pass

        print()
        return True

    except ImportError as e:
        print(f"❌ pywin32 모듈 미설치: {e}")
        print()
        print("   설치 방법:")
        print("   pip install pywin32")
        print()
        return False


def check_registry_access():
    """레지스트리 접근 권한 확인"""
    print("=" * 80)
    print("  🔑 레지스트리 접근 확인")
    print("=" * 80)
    print()

    try:
        import winreg

        # 64비트 레지스트리 뷰
        KEY_WOW64_64KEY = 0x0100
        KEY_WOW64_32KEY = 0x0200

        # 64비트 레지스트리에서 확인
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                r"KHOPENAPI.KHOpenAPICtrl.1\CLSID",
                0,
                winreg.KEY_READ | KEY_WOW64_64KEY
            )
            clsid, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            print(f"✅ 64비트 레지스트리: CLSID = {clsid}")
        except WindowsError as e:
            print(f"⚠️  64비트 레지스트리 접근 실패: {e}")

        # 32비트 레지스트리에서 확인
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                r"KHOPENAPI.KHOpenAPICtrl.1\CLSID",
                0,
                winreg.KEY_READ | KEY_WOW64_32KEY
            )
            clsid, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            print(f"✅ 32비트 레지스트리: CLSID = {clsid}")
        except WindowsError as e:
            print(f"⚠️  32비트 레지스트리 접근 실패: {e}")

        print()
        return True

    except Exception as e:
        print(f"❌ 레지스트리 접근 오류: {e}")
        print()
        return False


def check_ocx_file():
    """OCX 파일 상세 확인"""
    print("=" * 80)
    print("  📄 OCX 파일 상세 정보")
    print("=" * 80)
    print()

    from pathlib import Path
    import os

    ocx_paths = [
        r"C:\OpenAPI\KHOpenAPI64.ocx",
        r"C:\OpenAPI\KHOpenAPI.ocx",
    ]

    for ocx_path in ocx_paths:
        print(f"검사: {ocx_path}")

        if Path(ocx_path).exists():
            print(f"  ✅ 파일 존재")

            # 파일 크기
            size = os.path.getsize(ocx_path)
            print(f"  ✓ 크기: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")

            # 수정 시간
            import time
            mtime = os.path.getmtime(ocx_path)
            mtime_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
            print(f"  ✓ 수정 시간: {mtime_str}")

            # 파일 속성
            try:
                import win32api

                # 파일 버전 정보
                try:
                    info = win32api.GetFileVersionInfo(ocx_path, '\\')
                    ms = info['FileVersionMS']
                    ls = info['FileVersionLS']
                    version = f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
                    print(f"  ✓ 버전: {version}")
                except:
                    print(f"  ⚠️  버전 정보 없음")

            except ImportError:
                pass

        else:
            print(f"  ❌ 파일 없음")

        print()


def check_dependencies():
    """OCX 의존성 DLL 확인"""
    print("=" * 80)
    print("  🔗 OCX 의존성 확인")
    print("=" * 80)
    print()

    # 일반적인 의존성 DLL들
    dependencies = [
        "mfc140u.dll",
        "msvcp140.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "ucrtbase.dll",
    ]

    import ctypes
    import os

    print("Visual C++ 런타임 DLL 확인:")
    for dll in dependencies:
        try:
            # 시스템에서 DLL 로드 시도
            handle = ctypes.windll.kernel32.LoadLibraryW(dll)
            if handle:
                print(f"  ✅ {dll} - 로드 가능")
                ctypes.windll.kernel32.FreeLibrary(handle)
            else:
                print(f"  ❌ {dll} - 로드 실패")
        except Exception as e:
            print(f"  ❌ {dll} - 오류: {e}")

    print()
    print("💡 누락된 DLL이 있다면:")
    print("   'Visual C++ Redistributable for Visual Studio 2015-2022' 설치")
    print("   https://aka.ms/vs/17/release/vc_redist.x64.exe")
    print()


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║           🔍 Python 환경 및 64비트 호환성 진단                            ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
""")

    results = []

    # Python 비트 확인 (가장 중요!)
    results.append(("Python 64비트", check_python_bitness()))

    # pywin32 확인
    results.append(("pywin32 모듈", check_pywin32()))

    # 레지스트리 접근
    results.append(("레지스트리 접근", check_registry_access()))

    # OCX 파일 확인
    check_ocx_file()

    # 의존성 확인
    check_dependencies()

    # 최종 요약
    print("=" * 80)
    print("  📊 진단 결과 요약")
    print("=" * 80)
    print()

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print()

    if all(r for _, r in results):
        print("✅ 모든 환경 검사 통과!")
        print("   64비트 Open API를 사용할 수 있는 환경입니다.")
    else:
        print("⚠️  일부 환경 문제 발견")
        print("   위의 경고 메시지를 확인하세요.")

    print()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    print("\n창을 닫으려면 Enter를 누르세요...")
    input()
