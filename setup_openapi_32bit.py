#!/usr/bin/env python
"""
OpenAPI 32비트 환경 자동 설정 및 테스트
- Python 3.9 다운그레이드
- 필요한 라이브러리 자동 설치
- 버전 확인 및 검증
- OpenAPI 로그인 테스트
- 문제 자동 진단 및 해결
"""

import sys
import os
import subprocess
import time
from pathlib import Path

print("="*80)
print("🔧 OpenAPI 32비트 환경 자동 설정 및 테스트")
print("="*80)

VENV_NAME = "autotrade_32"
TARGET_PYTHON_VERSION = "3.9"
REQUIRED_PACKAGES = {
    'koapy': '0.8.3',
    'PyQt5': '5.15.9',
    'requests': None,
    'pandas': None,
    'numpy': None,
}

def print_step(step_num, message):
    print(f"\n{'='*80}")
    print(f"📌 STEP {step_num}: {message}")
    print(f"{'='*80}")

def run_command(command, description, timeout=600, check=True):
    """명령어 실행 (상세 로그 포함)"""
    print(f"\n🔧 {description}...")
    print(f"   명령어: {command}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='ignore'
        )

        if result.stdout:
            print(f"   출력:\n{result.stdout[:500]}")

        if result.returncode == 0:
            print(f"✅ {description} 완료")
            return True, result.stdout, result.stderr
        else:
            if check:
                print(f"❌ {description} 실패 (코드: {result.returncode})")
                if result.stderr:
                    print(f"   에러:\n{result.stderr[:500]}")
            return False, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        print(f"⏰ {description} 시간 초과")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ {description} 예외 발생: {e}")
        return False, "", str(e)

def check_conda_available():
    """conda 사용 가능 여부 확인"""
    print_step(1, "Conda 환경 확인")

    success, stdout, stderr = run_command(
        "conda --version",
        "Conda 버전 확인",
        timeout=10
    )

    if success:
        print(f"✅ Conda 사용 가능")
        return True
    else:
        print(f"❌ Conda를 찾을 수 없습니다.")
        print(f"   Anaconda 또는 Miniconda가 설치되어 있는지 확인하세요.")
        return False

def check_current_environment():
    """현재 Python 환경 정보 확인"""
    print_step(2, "현재 환경 확인")

    is_64bit = sys.maxsize > 2**32
    arch = "64비트" if is_64bit else "32비트"
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    print(f"🐍 현재 Python 버전: {python_version}")
    print(f"📐 아키텍처: {arch}")
    print(f"📍 Python 경로: {sys.executable}")
    print(f"🌍 가상환경: {os.environ.get('CONDA_DEFAULT_ENV', 'None')}")

    current_env = os.environ.get('CONDA_DEFAULT_ENV', '')

    if VENV_NAME not in current_env:
        print(f"\n⚠️  현재 {VENV_NAME} 환경이 아닙니다!")
        print(f"   다음 명령어로 환경을 활성화하세요:")
        print(f"   conda activate {VENV_NAME}")
        return False

    if sys.version_info.major != 3 or sys.version_info.minor != 9:
        print(f"\n⚠️  Python 버전이 3.9가 아닙니다. 다운그레이드가 필요합니다.")
        return False

    print(f"\n✅ 올바른 환경입니다!")
    return True

def downgrade_python():
    """Python 3.9로 다운그레이드"""
    print_step(3, f"Python {TARGET_PYTHON_VERSION} 다운그레이드")

    print(f"\n⚠️  주의: Python 다운그레이드 시 기존 패키지가 제거될 수 있습니다.")
    print(f"   약 5-10분 소요될 수 있습니다...\n")

    # Python 3.9 설치
    success, stdout, stderr = run_command(
        f"conda install python={TARGET_PYTHON_VERSION} -y",
        f"Python {TARGET_PYTHON_VERSION} 설치",
        timeout=600
    )

    if not success:
        print(f"\n❌ Python 다운그레이드 실패")
        print(f"   수동으로 시도하세요:")
        print(f"   conda install python={TARGET_PYTHON_VERSION} -y")
        return False

    # 설치 확인
    success, stdout, stderr = run_command(
        "python --version",
        "Python 버전 재확인",
        timeout=10
    )

    if success and "3.9" in stdout:
        print(f"\n✅ Python {TARGET_PYTHON_VERSION} 다운그레이드 완료!")
        return True
    else:
        print(f"\n⚠️  Python 버전 확인 실패. 재시작이 필요할 수 있습니다.")
        return False

def install_packages():
    """필요한 패키지 설치"""
    print_step(4, "필수 패키지 설치")

    failed_packages = []

    for package_name, version in REQUIRED_PACKAGES.items():
        print(f"\n📦 {package_name} 설치 중...")

        if version:
            package_spec = f"{package_name}=={version}"
        else:
            package_spec = package_name

        # pip로 설치
        success, stdout, stderr = run_command(
            f"pip install {package_spec} --no-cache-dir",
            f"{package_spec} 설치",
            timeout=300,
            check=False
        )

        if not success:
            print(f"⚠️  pip 설치 실패, conda로 재시도...")

            # conda로 재시도
            conda_spec = f"{package_name}={version}" if version else package_name
            success, stdout, stderr = run_command(
                f"conda install {conda_spec} -y",
                f"{conda_spec} conda 설치",
                timeout=300,
                check=False
            )

            if not success:
                print(f"❌ {package_name} 설치 실패")
                failed_packages.append(package_name)
            else:
                print(f"✅ {package_name} conda 설치 완료")
        else:
            print(f"✅ {package_name} pip 설치 완료")

    if failed_packages:
        print(f"\n⚠️  설치 실패한 패키지: {', '.join(failed_packages)}")
        return False

    print(f"\n✅ 모든 패키지 설치 완료!")
    return True

def verify_installation():
    """설치된 패키지 검증"""
    print_step(5, "패키지 검증")

    verification_code = """
import sys
import importlib.metadata

packages = ['koapy', 'PyQt5', 'requests', 'pandas', 'numpy']
failed = []

for pkg in packages:
    try:
        version = importlib.metadata.version(pkg)
        print(f"✅ {pkg}: v{version}")
    except:
        print(f"❌ {pkg}: 설치 안됨")
        failed.append(pkg)

if failed:
    print(f"\\n설치 실패: {', '.join(failed)}")
    sys.exit(1)
else:
    print(f"\\n✅ 모든 패키지 정상 설치됨")
    sys.exit(0)
"""

    success, stdout, stderr = run_command(
        f'python -c "{verification_code}"',
        "패키지 버전 확인",
        timeout=30
    )

    return success

def test_pyqt5():
    """PyQt5 테스트"""
    print_step(6, "PyQt5 Import 테스트")

    test_code = """
try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QAxContainer import QAxWidget
    from PyQt5.QtCore import QCoreApplication
    print("✅ PyQt5 모듈 import 성공")

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    print("✅ QApplication 생성 성공")
    print("✅ PyQt5 테스트 완료")
except Exception as e:
    print(f"❌ PyQt5 테스트 실패: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
"""

    success, stdout, stderr = run_command(
        f'python -c "{test_code}"',
        "PyQt5 기능 테스트",
        timeout=30
    )

    return success

def test_koapy():
    """koapy 테스트"""
    print_step(7, "koapy Import 테스트")

    test_code = """
try:
    import koapy
    print(f"✅ koapy 모듈 import 성공 (v{koapy.__version__})")

    from koapy import KiwoomOpenApiContext
    print("✅ KiwoomOpenApiContext import 성공")

    from koapy.backend.kiwoom_open_api_plus.core.KiwoomOpenApiPlusQAxWidget import KiwoomOpenApiPlusQAxWidget
    print("✅ KiwoomOpenApiPlusQAxWidget import 성공")

    print("✅ koapy 테스트 완료")
except Exception as e:
    print(f"❌ koapy 테스트 실패: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
"""

    success, stdout, stderr = run_command(
        f'python -c "{test_code}"',
        "koapy 기능 테스트",
        timeout=30
    )

    return success

def check_kiwoom_ocx():
    """키움 OCX 파일 확인"""
    print_step(8, "키움 OpenAPI OCX 확인")

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
        print("⚠️  OCX 파일을 찾을 수 없습니다.")
        print("   키움증권 OpenAPI+가 설치되어 있는지 확인하세요.")
        print("   다운로드: https://www.kiwoom.com/nkw.templateFrameSet.do?m=m1408000000")

    return found

def run_login_test():
    """로그인 창 테스트"""
    print_step(9, "OpenAPI 로그인 테스트")

    login_test_code = '''
import sys
import logging

try:
    print("  1. 모듈 import...")
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QCoreApplication
    from koapy import KiwoomOpenApiContext

    print("  2. 로깅 설정...")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    print("  3. QApplication 생성...")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        print("     ✅ QApplication 생성됨")

    print("  4. 로그인 창 실행...")
    print()
    print("="*60)
    print("🔑 로그인 창이 표시됩니다")
    print("   - ID/PW/인증서 비밀번호 입력")
    print("   - 로그인 후 잠시 대기")
    print("="*60)
    print()

    with KiwoomOpenApiContext() as context:
        print("\\n✅ 로그인 성공!")

        try:
            accounts = context.GetAccountList()
            print(f"   📊 계좌 수: {len(accounts)}")

            if accounts:
                print(f"   📋 계좌 목록:")
                for i, acc in enumerate(accounts, 1):
                    print(f"      {i}. {acc}")

            user_id = context.GetLoginInfo("USER_ID")
            user_name = context.GetLoginInfo("USER_NAME")

            if user_id:
                print(f"   👤 사용자 ID: {user_id}")
            if user_name:
                print(f"   👤 이름: {user_name}")

        except Exception as e:
            print(f"   ⚠️  계좌 정보 조회 실패: {e}")

        print("\\n✨ OpenAPI 로그인 테스트 완료!")

except ImportError as e:
    print(f"❌ Import 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

except Exception as e:
    print(f"❌ 로그인 실패: {e}")
    import traceback
    traceback.print_exc()

    error_msg = str(e).lower()
    if "timeout" in error_msg:
        print("\\n💡 해결방법: 로그인 완료 확인, 인터넷 연결 확인")
    elif "ocx" in error_msg or "com" in error_msg:
        print("\\n💡 해결방법: OpenAPI+ 재설치, 관리자 권한 실행")

    sys.exit(1)
'''

    # 별도 파일로 저장
    test_file = Path("_temp_login_test.py")
    test_file.write_text(login_test_code, encoding='utf-8')

    print("\n🚀 로그인 창 테스트 시작...")
    print("   (테스트 파일: _temp_login_test.py)\n")

    success, stdout, stderr = run_command(
        "python _temp_login_test.py",
        "로그인 창 실행",
        timeout=300,
        check=False
    )

    # 임시 파일 삭제
    try:
        test_file.unlink()
    except:
        pass

    return success

def create_quick_test_script():
    """빠른 테스트 스크립트 생성"""
    print_step(10, "빠른 테스트 스크립트 생성")

    script_content = '''@echo off
echo ========================================
echo OpenAPI 빠른 로그인 테스트
echo ========================================

call conda activate autotrade_32

python -c "from PyQt5.QtWidgets import QApplication; from koapy import KiwoomOpenApiContext; import sys; app = QApplication(sys.argv); print('로그인 창 실행...'); context = KiwoomOpenApiContext(); context.__enter__(); print(f'계좌: {context.GetAccountList()}'); context.__exit__(None, None, None)"

pause
'''

    script_path = Path("quick_login_test.bat")
    script_path.write_text(script_content, encoding='utf-8')

    print(f"✅ 빠른 테스트 스크립트 생성: {script_path}")
    print(f"   실행: quick_login_test.bat")

def main():
    """메인 실행 함수"""

    # STEP 1: Conda 확인
    if not check_conda_available():
        return False

    # STEP 2: 현재 환경 확인
    env_ok = check_current_environment()

    # STEP 3: Python 다운그레이드 (필요시)
    if not env_ok:
        print(f"\n⚠️  Python {TARGET_PYTHON_VERSION} 다운그레이드를 진행합니다...")

        current_env = os.environ.get('CONDA_DEFAULT_ENV', '')
        if VENV_NAME not in current_env:
            print(f"\n❌ {VENV_NAME} 환경이 활성화되지 않았습니다.")
            print(f"   다음 명령어를 실행하세요:")
            print(f"   1. conda activate {VENV_NAME}")
            print(f"   2. python setup_openapi_32bit.py")
            return False

        if not downgrade_python():
            print(f"\n❌ Python 다운그레이드 실패")
            print(f"   환경을 다시 활성화한 후 재시도하세요:")
            print(f"   conda deactivate")
            print(f"   conda activate {VENV_NAME}")
            return False

        print(f"\n✅ Python 다운그레이드 완료. 환경을 다시 활성화하세요:")
        print(f"   conda deactivate")
        print(f"   conda activate {VENV_NAME}")
        print(f"   python setup_openapi_32bit.py")
        return True

    # STEP 4: 패키지 설치
    if not install_packages():
        print(f"\n⚠️  일부 패키지 설치 실패. 계속 진행합니다...")

    # STEP 5: 패키지 검증
    if not verify_installation():
        print(f"\n❌ 패키지 검증 실패")
        return False

    # STEP 6: PyQt5 테스트
    if not test_pyqt5():
        print(f"\n❌ PyQt5 테스트 실패")
        return False

    # STEP 7: koapy 테스트
    if not test_koapy():
        print(f"\n❌ koapy 테스트 실패")
        return False

    # STEP 8: OCX 확인
    ocx_found = check_kiwoom_ocx()

    # STEP 9: 로그인 테스트
    if ocx_found:
        print(f"\n✅ 모든 사전 테스트 통과!")
        print(f"\n🔑 로그인 테스트를 시작합니다...")

        login_success = run_login_test()

        if login_success:
            print(f"\n" + "="*80)
            print(f"✨ 모든 설정 및 테스트 완료!")
            print(f"="*80)
            print(f"\n다음 단계:")
            print(f"  1. OpenAPI 로그인 성공 ✅")
            print(f"  2. openapi_server.py 실행 가능")
            print(f"  3. main.py에서 REST API 사용 가능")
        else:
            print(f"\n⚠️  로그인 테스트 실패")
            print(f"   하지만 환경 설정은 완료되었습니다.")
    else:
        print(f"\n⚠️  OCX 파일 미확인. 키움 OpenAPI+ 설치 후 재시도하세요.")

    # STEP 10: 빠른 테스트 스크립트 생성
    create_quick_test_script()

    print(f"\n" + "="*80)
    print(f"📝 설정 완료 요약")
    print(f"="*80)
    print(f"✅ Python 3.9 환경 구성")
    print(f"✅ koapy, PyQt5 설치")
    print(f"✅ Import 테스트 완료")
    print(f"{'✅' if ocx_found else '⚠️ '} OCX 파일 {'확인됨' if ocx_found else '미확인'}")
    print(f"\n빠른 테스트: quick_login_test.bat 실행")

    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
