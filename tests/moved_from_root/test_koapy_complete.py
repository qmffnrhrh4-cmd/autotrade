"""
완전 자동화된 koapy 테스트 스크립트
=======================================
1. 필수 패키지 확인 및 자동 설치
2. 버전 확인 및 다운그레이드 (필요 시)
3. 설치 후 재확인
4. koapy 로그인 테스트 (로그인 창 표시)

32비트 Python 환경에서 실행하세요:
    conda activate autotrade_32
    python test_koapy_complete.py
"""

import sys
import subprocess
import importlib
import struct

# ============================================================================
# 설정
# ============================================================================

REQUIRED_PACKAGES = {
    'PyQt5': None,  # 최신 버전
    'PyQt5-Qt5': None,
    'PyQt5-sip': None,
    'protobuf': '3.20.3',  # koapy 호환 버전
    'grpcio': '1.50.0',  # koapy 호환 버전
    'koapy': None,  # 최신 버전
    'flask': None,
    'flask-cors': None,
    'pywin32': None,
}

# ============================================================================
# 유틸리티 함수
# ============================================================================

def print_header(title):
    """헤더 출력"""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()


def print_step(step, total, message):
    """단계 출력"""
    print(f"[{step}/{total}] {message}")


def check_architecture():
    """Python 비트 확인"""
    bits = struct.calcsize("P") * 8
    return bits


def get_installed_version(package_name):
    """설치된 패키지 버전 확인"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'show', package_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
        return None
    except Exception as e:
        return None


def install_package(package_name, version=None):
    """패키지 설치"""
    try:
        if version:
            package_spec = f"{package_name}=={version}"
        else:
            package_spec = package_name

        print(f"   Installing: {package_spec}...")

        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package_spec, '--quiet'],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            print(f"   ✅ {package_name} installed successfully")
            return True
        else:
            print(f"   ❌ Failed to install {package_name}")
            print(f"      {result.stderr}")
            return False

    except Exception as e:
        print(f"   ❌ Error installing {package_name}: {e}")
        return False


def uninstall_package(package_name):
    """패키지 제거"""
    try:
        print(f"   Uninstalling: {package_name}...")
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'uninstall', package_name, '-y', '--quiet'],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except Exception as e:
        print(f"   ⚠️  Error uninstalling {package_name}: {e}")
        return False


# ============================================================================
# 메인 함수들
# ============================================================================

def step1_check_architecture():
    """Step 1: Python 아키텍처 확인"""
    print_step(1, 5, "Checking Python architecture...")

    bits = check_architecture()
    print(f"   Python: {bits}-bit")

    if bits != 32:
        print()
        print("   ❌ ERROR: This script requires 32-bit Python!")
        print()
        print("   Please run:")
        print("      conda activate autotrade_32")
        print("      python test_koapy_complete.py")
        print()
        return False

    print("   ✅ 32-bit Python confirmed")
    return True


def step2_check_and_install_packages():
    """Step 2: 패키지 확인 및 설치"""
    print_step(2, 5, "Checking and installing required packages...")

    all_ok = True

    for package_name, required_version in REQUIRED_PACKAGES.items():
        installed_version = get_installed_version(package_name)

        # 패키지가 설치되지 않았으면 설치
        if installed_version is None:
            print(f"   ⚠️  {package_name} not installed")
            if not install_package(package_name, required_version):
                all_ok = False
                continue
            installed_version = get_installed_version(package_name)

        # 버전 확인
        if required_version:
            if installed_version != required_version:
                print(f"   ⚠️  {package_name} version mismatch:")
                print(f"      Installed: {installed_version}")
                print(f"      Required:  {required_version}")
                print(f"   → Downgrading to {required_version}...")

                # 기존 버전 제거 후 재설치
                if uninstall_package(package_name):
                    if not install_package(package_name, required_version):
                        all_ok = False
                        continue
                else:
                    all_ok = False
                    continue

        # 최종 확인
        final_version = get_installed_version(package_name)
        if final_version:
            if required_version and final_version != required_version:
                print(f"   ❌ {package_name}: Version mismatch (got {final_version})")
                all_ok = False
            else:
                print(f"   ✅ {package_name}: {final_version}")
        else:
            print(f"   ❌ {package_name}: Installation failed")
            all_ok = False

    return all_ok


def step3_verify_imports():
    """Step 3: Import 테스트"""
    print_step(3, 5, "Verifying imports...")

    test_imports = [
        ('PyQt5.QtWidgets', 'QApplication'),
        ('koapy', 'KiwoomOpenApiPlusEntrypoint'),
        ('flask', 'Flask'),
        ('flask_cors', 'CORS'),
    ]

    all_ok = True

    for module_name, class_name in test_imports:
        try:
            module = importlib.import_module(module_name)
            if class_name:
                getattr(module, class_name)
            print(f"   ✅ {module_name}.{class_name}")
        except Exception as e:
            print(f"   ❌ {module_name}.{class_name}: {e}")
            all_ok = False

    return all_ok


def step4_test_qt_application():
    """Step 4: Qt Application 테스트"""
    print_step(4, 5, "Testing Qt Application...")

    try:
        from PyQt5.QtWidgets import QApplication

        # QApplication 생성 테스트
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            print("   ✅ Qt Application created successfully")
        else:
            print("   ✅ Qt Application already exists")

        # 이벤트 처리 테스트
        app.processEvents()
        print("   ✅ Qt event processing works")

        return True

    except Exception as e:
        print(f"   ❌ Qt Application test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def step5_test_koapy_login():
    """Step 5: koapy 로그인 테스트"""
    print_step(5, 5, "Testing koapy login...")

    try:
        import os
        os.environ['QT_API'] = 'pyqt5'

        from PyQt5.QtWidgets import QApplication
        from koapy import KiwoomOpenApiPlusEntrypoint

        print()
        print("   " + "=" * 70)
        print("   🔐 로그인 테스트 시작")
        print("   " + "=" * 70)
        print()
        print("   ⚠️  잠시 후 키움증권 로그인 창이 나타납니다!")
        print("   ⚠️  로그인 창에서 ID/PW를 입력하고 로그인하세요.")
        print()
        print("   (서버 시작에 30초~1분 정도 걸릴 수 있습니다)")
        print()

        # Qt Application 확인
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # koapy 초기화
        print("   [1/3] koapy 서버 시작 중...")
        context = KiwoomOpenApiPlusEntrypoint().__enter__()
        print("   ✅ koapy 서버 시작됨")

        print()
        print("   [2/3] 로그인 시도 중...")
        print("   → 로그인 창이 나타나야 합니다!")
        print()

        # 이벤트 처리 (GUI 표시)
        app.processEvents()

        # 로그인 시도
        context.EnsureConnected()

        print()
        print("   [3/3] 연결 상태 확인 중...")

        # 연결 확인
        state = context.GetConnectState()

        if state == 1:
            print("   ✅ 로그인 성공!")
            print()

            # 계좌 정보
            try:
                accounts = context.GetAccountList()
                print(f"   계좌 목록: {accounts}")
            except Exception as e:
                print(f"   ⚠️  계좌 조회 실패: {e}")

            print()
            print("   " + "=" * 70)
            print("   ✅✅✅ koapy 테스트 완료!")
            print("   " + "=" * 70)

            # 정리
            context.__exit__(None, None, None)
            return True
        else:
            print(f"   ❌ 로그인 실패 (상태: {state})")
            context.__exit__(None, None, None)
            return False

    except Exception as e:
        print(f"   ❌ koapy 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# 메인 실행
# ============================================================================

def main():
    """메인 함수"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              🔬 koapy 완전 자동화 테스트 스크립트                              ║
║                                                                              ║
║  이 스크립트는 다음을 자동으로 수행합니다:                                      ║
║    1. Python 아키텍처 확인 (32-bit 필수)                                      ║
║    2. 필수 패키지 확인 및 자동 설치                                            ║
║    3. 버전 불일치 시 자동 다운그레이드                                          ║
║    4. Qt Application 테스트                                                   ║
║    5. koapy 로그인 테스트 (로그인 창 표시)                                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

    print(f"Python: {sys.version}")
    print(f"실행 경로: {sys.executable}")

    # Step 1: 아키텍처 확인
    if not step1_check_architecture():
        print()
        print("❌ 테스트 중단: 32-bit Python이 필요합니다")
        input("\n계속하려면 Enter를 누르세요...")
        return 1

    # Step 2: 패키지 확인 및 설치
    if not step2_check_and_install_packages():
        print()
        print("⚠️  일부 패키지 설치 실패")
        print("계속 진행할까요? (y/n)")
        choice = input("선택: ").strip().lower()
        if choice != 'y':
            return 1

    # Step 3: Import 확인
    if not step3_verify_imports():
        print()
        print("❌ Import 테스트 실패")
        input("\n계속하려면 Enter를 누르세요...")
        return 1

    # Step 4: Qt Application 테스트
    if not step4_test_qt_application():
        print()
        print("❌ Qt Application 테스트 실패")
        input("\n계속하려면 Enter를 누르세요...")
        return 1

    # Step 5: koapy 로그인 테스트
    print()
    print("=" * 80)
    print("모든 사전 확인 완료!")
    print("=" * 80)
    print()
    print("이제 koapy 로그인 테스트를 시작합니다.")
    print("로그인 창이 나타나면 수동으로 로그인하세요.")
    print()
    input("준비되면 Enter를 누르세요...")
    print()

    if step5_test_koapy_login():
        print()
        print("=" * 80)
        print("✅✅✅ 모든 테스트 성공!")
        print("=" * 80)
        print()
        print("koapy가 정상적으로 작동합니다.")
        print("이제 openapi_server.py를 실행할 수 있습니다.")
        return 0
    else:
        print()
        print("=" * 80)
        print("❌ koapy 테스트 실패")
        print("=" * 80)
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        print()
        input("종료하려면 Enter를 누르세요...")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        input("\n종료하려면 Enter를 누르세요...")
        sys.exit(1)
