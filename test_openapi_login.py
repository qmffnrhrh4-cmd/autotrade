#!/usr/bin/env python
import sys
import os
import subprocess
import importlib.metadata
from pathlib import Path

print("="*80)
print("🔍 OpenAPI 로그인 창 종합 테스트 & 자동 수정")
print("="*80)

REQUIRED_KOAPY_VERSION = "0.5.8"
REQUIRED_PYQT5_VERSION = "5.15.9"

def print_step(step_num, message):
    print(f"\n{'='*80}")
    print(f"📌 STEP {step_num}: {message}")
    print(f"{'='*80}")

def get_package_version(package_name):
    try:
        version = importlib.metadata.version(package_name)
        print(f"✅ {package_name} 설치됨: v{version}")
        return version
    except importlib.metadata.PackageNotFoundError:
        print(f"❌ {package_name} 설치되지 않음")
        return None

def install_package(package_name, version=None):
    if version:
        package_spec = f"{package_name}=={version}"
        print(f"📦 {package_name} v{version} 설치 중...")
    else:
        package_spec = package_name
        print(f"📦 {package_name} 설치 중...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_spec, "--no-cache-dir"],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            print(f"✅ {package_spec} 설치 완료")
            return True
        else:
            print(f"❌ 설치 실패: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ 설치 시간 초과")
        return False
    except Exception as e:
        print(f"❌ 설치 중 오류: {e}")
        return False

def uninstall_package(package_name):
    print(f"🗑️  {package_name} 제거 중...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", package_name, "-y"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print(f"✅ {package_name} 제거 완료")
            return True
        else:
            print(f"⚠️  제거 실패 (무시하고 진행): {result.stderr}")
            return False
    except Exception as e:
        print(f"⚠️  제거 중 오류 (무시하고 진행): {e}")
        return False

def check_python_architecture():
    import platform
    is_64bit = sys.maxsize > 2**32
    arch = "64비트" if is_64bit else "32비트"
    print(f"🐍 Python 버전: {sys.version}")
    print(f"📐 Python 아키텍처: {arch}")
    print(f"📍 Python 경로: {sys.executable}")
    return is_64bit

def check_kiwoom_ocx():
    print("\n🔍 키움 OpenAPI OCX 파일 확인...")

    possible_paths = [
        r"C:\OpenAPI\KHOpenAPI.ocx",
        r"C:\OpenAPI\KHOpenAPICtrl.ocx",
        r"C:\Program Files (x86)\Kiwoom\OpenAPI\KHOpenAPI.ocx",
        r"C:\KiwoomFlash3\OpenAPI\KHOpenAPI.ocx",
    ]

    found = False
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ OCX 파일 발견: {path}")
            found = True
            break

    if not found:
        print("❌ OCX 파일을 찾을 수 없습니다.")
        print("   키움증권 OpenAPI+가 설치되어 있는지 확인하세요.")

    return found

def test_koapy_import():
    print("\n🔍 koapy 라이브러리 import 테스트...")

    try:
        print("  - koapy 모듈 import...")
        import koapy
        print(f"✅ koapy import 성공 (경로: {koapy.__file__})")

        print("  - koapy.context 모듈 import...")
        from koapy import KiwoomOpenApiContext
        print("✅ KiwoomOpenApiContext import 성공")

        print("  - koapy.backend.kiwoom_open_api_plus import...")
        from koapy.backend.kiwoom_open_api_plus.core.KiwoomOpenApiPlusQAxWidget import KiwoomOpenApiPlusQAxWidget
        print("✅ KiwoomOpenApiPlusQAxWidget import 성공")

        return True

    except ImportError as e:
        print(f"❌ Import 실패: {e}")
        print(f"   상세 에러: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pyqt5():
    print("\n🔍 PyQt5 테스트...")

    try:
        print("  - PyQt5.QtWidgets import...")
        from PyQt5.QtWidgets import QApplication
        print("✅ PyQt5.QtWidgets import 성공")

        print("  - PyQt5.QAxContainer import...")
        from PyQt5.QAxContainer import QAxWidget
        print("✅ PyQt5.QAxContainer import 성공")

        print("  - QApplication 생성 테스트...")
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        print("✅ QApplication 생성 성공")

        return True

    except ImportError as e:
        print(f"❌ PyQt5 Import 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ PyQt5 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_login_window():
    print("\n🚀 OpenAPI 로그인 창 실행 시도...")

    try:
        print("  1. 필요한 모듈 import...")
        from PyQt5.QtWidgets import QApplication
        from koapy import KiwoomOpenApiContext
        import logging

        print("  2. 로깅 설정...")
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )

        print("  3. QApplication 생성...")
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            print("     ✅ 새 QApplication 생성됨")
        else:
            print("     ✅ 기존 QApplication 사용")

        print("  4. KiwoomOpenApiContext 생성...")
        print("     (로그인 창이 표시됩니다...)")
        print("     ⚠️  로그인 후 창을 닫으면 테스트가 종료됩니다.")
        print()

        with KiwoomOpenApiContext() as context:
            print("✅ 로그인 성공!")
            print(f"   계좌 수: {len(context.GetAccountList())}")

            if context.GetAccountList():
                print(f"   계좌 목록: {context.GetAccountList()}")

            print("\n✨ OpenAPI 로그인 창 테스트 완료!")
            print("   로그인이 정상적으로 작동합니다.")

        return True

    except ImportError as e:
        print(f"❌ Import 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ 로그인 창 실행 실패: {e}")
        print(f"   에러 타입: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print_step(1, "시스템 환경 확인")
    is_64bit = check_python_architecture()

    if is_64bit:
        print("\n⚠️  경고: 64비트 Python이 감지되었습니다.")
        print("   OpenAPI는 32비트에서만 작동합니다.")
        print("   하지만 koapy는 64비트에서 32비트 프로세스를 자동으로 생성합니다.")

    ocx_found = check_kiwoom_ocx()

    print_step(2, "패키지 버전 확인")
    koapy_version = get_package_version("koapy")
    pyqt5_version = get_package_version("PyQt5")
    pyqt5_tools_version = get_package_version("pyqt5-tools")

    need_reinstall = False

    if koapy_version is None:
        print("\n❌ koapy가 설치되지 않았습니다.")
        need_reinstall = True
    elif koapy_version != REQUIRED_KOAPY_VERSION:
        print(f"\n⚠️  koapy 버전 불일치: 현재 v{koapy_version}, 권장 v{REQUIRED_KOAPY_VERSION}")
        need_reinstall = True

    if pyqt5_version is None:
        print("\n❌ PyQt5가 설치되지 않았습니다.")
        need_reinstall = True
    elif pyqt5_version != REQUIRED_PYQT5_VERSION:
        print(f"\n⚠️  PyQt5 버전 불일치: 현재 v{pyqt5_version}, 권장 v{REQUIRED_PYQT5_VERSION}")
        need_reinstall = True

    if need_reinstall:
        print_step(3, "패키지 재설치")

        print("\n🔄 기존 패키지 제거...")
        if koapy_version:
            uninstall_package("koapy")
        if pyqt5_version:
            uninstall_package("PyQt5")
            uninstall_package("PyQt5-Qt5")
            uninstall_package("PyQt5-sip")
        if pyqt5_tools_version:
            uninstall_package("pyqt5-tools")

        print("\n📦 권장 버전 설치...")

        print("\n1️⃣  PyQt5 설치...")
        if not install_package("PyQt5", REQUIRED_PYQT5_VERSION):
            print("❌ PyQt5 설치 실패. 수동으로 설치해주세요:")
            print(f"   pip install PyQt5=={REQUIRED_PYQT5_VERSION}")
            return False

        print("\n2️⃣  koapy 설치...")
        if not install_package("koapy", REQUIRED_KOAPY_VERSION):
            print("❌ koapy 설치 실패. 수동으로 설치해주세요:")
            print(f"   pip install koapy=={REQUIRED_KOAPY_VERSION}")
            return False

        print("\n✅ 모든 패키지 재설치 완료!")
        print("\n🔄 설치 확인...")
        koapy_version = get_package_version("koapy")
        pyqt5_version = get_package_version("PyQt5")
    else:
        print("\n✅ 모든 패키지 버전이 올바릅니다!")

    print_step(4, "Import 테스트")

    if not test_pyqt5():
        print("\n❌ PyQt5 테스트 실패")
        print("   다음 명령어로 재설치를 시도하세요:")
        print(f"   pip uninstall PyQt5 PyQt5-Qt5 PyQt5-sip -y")
        print(f"   pip install PyQt5=={REQUIRED_PYQT5_VERSION}")
        return False

    if not test_koapy_import():
        print("\n❌ koapy 테스트 실패")
        print("   다음 명령어로 재설치를 시도하세요:")
        print(f"   pip uninstall koapy -y")
        print(f"   pip install koapy=={REQUIRED_KOAPY_VERSION}")
        return False

    print("\n✅ 모든 Import 테스트 통과!")

    print_step(5, "로그인 창 실행")

    if not ocx_found:
        print("\n⚠️  OCX 파일이 확인되지 않았지만, 로그인을 시도합니다.")
        print("   (koapy가 자동으로 OCX를 찾을 수 있습니다.)")

    success = show_login_window()

    if success:
        print("\n" + "="*80)
        print("✨ 모든 테스트 성공!")
        print("="*80)
        print("\n다음 단계:")
        print("  1. OpenAPI 로그인이 정상적으로 작동합니다")
        print("  2. main.py에서 OpenAPI를 사용할 수 있습니다")
        print("  3. 필요시 openapi_server.py를 실행하세요")
        return True
    else:
        print("\n" + "="*80)
        print("❌ 로그인 창 실행 실패")
        print("="*80)
        print("\n문제 해결 방법:")
        print("  1. 키움증권 OpenAPI+ 설치 확인:")
        print("     https://www.kiwoom.com/nkw.templateFrameSet.do?m=m1408000000")
        print()
        print("  2. 32비트 Python 사용 (권장):")
        print("     OpenAPI는 32비트에서 더 안정적입니다")
        print()
        print("  3. 수동 패키지 재설치:")
        print(f"     pip uninstall koapy PyQt5 -y")
        print(f"     pip install PyQt5=={REQUIRED_PYQT5_VERSION}")
        print(f"     pip install koapy=={REQUIRED_KOAPY_VERSION}")
        print()
        print("  4. 관리자 권한으로 실행:")
        print("     일부 환경에서는 관리자 권한이 필요합니다")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
