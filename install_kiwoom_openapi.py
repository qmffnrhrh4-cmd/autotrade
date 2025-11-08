#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
키움 OpenAPI+ 자동 설치 및 설정 스크립트

breadum/kiwoom GitHub 및 공식 문서 기반으로 작성
- OpenAPI+ 모듈 다운로드 및 설치
- KOA Studio 다운로드 및 설치
- 설치 검증
- 상세한 다음 단계 안내
"""

import os
import sys
import urllib.request
import subprocess
import zipfile
import shutil
import winreg
from pathlib import Path


def print_header(text):
    """섹션 헤더 출력"""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80 + "\n")


def print_step(step_num, text):
    """단계별 출력"""
    print(f"\n{'=' * 80}")
    print(f"STEP {step_num}: {text}")
    print("=" * 80 + "\n")


def check_prerequisites():
    """선행 조건 확인"""
    print_step(1, "선행 조건 확인")

    issues = []

    # Python 32비트 확인
    import platform
    architecture = platform.architecture()[0]
    print(f"Python 아키텍처: {architecture}")

    if architecture != "32bit":
        issues.append("⚠️  32비트 Python이 필요합니다!")
        print("   현재: 64비트 Python")
        print("   해결: conda create -n kiwoom32 python=3.10")
        print("         conda activate kiwoom32")
        print("         conda config --env --set subdir win-32")
    else:
        print("✅ 32비트 Python 확인")

    # Windows 확인
    if sys.platform != "win32":
        issues.append("⚠️  Windows 운영체제가 필요합니다!")
    else:
        print("✅ Windows 확인")

    # 관리자 권한 확인
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if is_admin:
            print("✅ 관리자 권한으로 실행 중")
        else:
            issues.append("⚠️  관리자 권한으로 실행하세요!")
            print("   우클릭 → '관리자 권한으로 실행'")
    except Exception as e:
        print(f"⚠️  관리자 권한 확인 실패: {e}")

    return issues


def download_file(url, filename):
    """파일 다운로드 with 진행률"""
    print(f"📥 다운로드 중: {filename}")
    print(f"   URL: {url}")

    def reporthook(blocknum, blocksize, totalsize):
        readsofar = blocknum * blocksize
        if totalsize > 0:
            percent = readsofar * 100 / totalsize
            s = f"\r   진행: {percent:5.1f}% ({readsofar:,} / {totalsize:,} bytes)"
            sys.stderr.write(s)
            if readsofar >= totalsize:
                sys.stderr.write("\n")
        else:
            sys.stderr.write(f"\r   진행: {readsofar:,} bytes")

    try:
        urllib.request.urlretrieve(url, filename, reporthook)
        print(f"✅ 다운로드 완료: {filename}")
        return True
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}")
        return False


def install_openapi_module():
    """OpenAPI+ 모듈 설치"""
    print_step(2, "OpenAPI+ 모듈 설치")

    setup_url = "https://download.kiwoom.com/web/openapi/OpenAPISetup.exe"
    setup_file = "OpenAPISetup.exe"

    # 다운로드
    if not download_file(setup_url, setup_file):
        print("\n❌ OpenAPI+ 모듈 다운로드 실패")
        print("\n💡 수동 다운로드:")
        print("   1. 브라우저에서 다음 URL 접속:")
        print(f"      {setup_url}")
        print("   2. 다운로드한 OpenAPISetup.exe 실행")
        return False

    # 설치 실행
    print(f"\n🔧 설치 프로그램 실행: {setup_file}")
    print("   ⚠️  설치 마법사가 나타나면 '다음'을 클릭하여 설치를 완료하세요.")
    print("   ⚠️  설치 경로는 기본값(C:\\OpenAPI\\) 사용을 권장합니다.")

    try:
        # 설치 프로그램 실행 (사용자가 수동으로 클릭해야 함)
        result = subprocess.run([setup_file], check=False)

        print("\n✅ 설치 프로그램 실행 완료")
        print("   설치가 완료되었는지 확인하세요.")

        # 설치 파일 삭제
        if os.path.exists(setup_file):
            os.remove(setup_file)
            print(f"   임시 파일 삭제: {setup_file}")

        return True

    except Exception as e:
        print(f"❌ 설치 실행 실패: {e}")
        return False


def install_koa_studio():
    """KOA Studio 설치"""
    print_step(3, "KOA Studio 설치")

    studio_url = "https://download.kiwoom.com/web/openapi/KOAStudioSA.zip"
    studio_zip = "KOAStudioSA.zip"
    install_dir = r"C:\OpenAPI"

    # 설치 디렉토리 확인
    if not os.path.exists(install_dir):
        print(f"⚠️  OpenAPI 설치 디렉토리가 없습니다: {install_dir}")
        print("   STEP 2에서 OpenAPI+ 모듈을 먼저 설치하세요.")
        return False

    # 다운로드
    if not download_file(studio_url, studio_zip):
        print("\n❌ KOA Studio 다운로드 실패")
        print("\n💡 수동 다운로드:")
        print("   1. 브라우저에서 다음 URL 접속:")
        print(f"      {studio_url}")
        print(f"   2. 다운로드한 ZIP 파일을 {install_dir}에 압축 해제")
        return False

    # 압축 해제
    print(f"\n📦 압축 해제 중: {install_dir}")
    try:
        with zipfile.ZipFile(studio_zip, 'r') as zip_ref:
            zip_ref.extractall(install_dir)

        print(f"✅ KOA Studio 설치 완료: {install_dir}")

        # ZIP 파일 삭제
        os.remove(studio_zip)
        print(f"   임시 파일 삭제: {studio_zip}")

        return True

    except Exception as e:
        print(f"❌ 압축 해제 실패: {e}")
        return False


def verify_installation():
    """설치 검증"""
    print_step(4, "설치 검증")

    # OCX 파일 확인
    ocx_paths = [
        r"C:\OpenAPI\KHOpenAPI.ocx",
        r"C:\OpenAPI\KHOpenAPICtrl.ocx",
        r"C:\Program Files (x86)\Kiwoom\OpenAPI\KHOpenAPI.ocx",
    ]

    ocx_found = False
    for path in ocx_paths:
        if os.path.exists(path):
            print(f"✅ OCX 파일 발견: {path}")
            ocx_found = True
            break

    if not ocx_found:
        print("❌ OCX 파일을 찾을 수 없습니다.")
        print("   OpenAPI+ 모듈이 제대로 설치되지 않았을 수 있습니다.")
        return False

    # KOA Studio 확인
    koa_studio_path = r"C:\OpenAPI\KOAStudioSA.exe"
    if os.path.exists(koa_studio_path):
        print(f"✅ KOA Studio 발견: {koa_studio_path}")
    else:
        print(f"⚠️  KOA Studio를 찾을 수 없습니다: {koa_studio_path}")

    # COM 등록 확인
    print("\n🔍 COM 등록 확인...")
    try:
        # CLSID 확인
        key_path = r"Software\Classes\KHOPENAPI.KHOpenAPICtrl.1"
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            winreg.CloseKey(key)
            print("✅ COM 객체가 레지스트리에 등록되어 있습니다.")
            return True
        except FileNotFoundError:
            print("❌ COM 객체가 레지스트리에 등록되어 있지 않습니다.")
            print("   OpenAPI+ 설치 프로그램이 제대로 실행되지 않았을 수 있습니다.")
            return False

    except Exception as e:
        print(f"⚠️  레지스트리 확인 실패: {e}")
        return False


def print_next_steps():
    """다음 단계 안내"""
    print_step(5, "다음 단계")

    print("""
🎯 설치 후 필수 작업:

1. **KOA Studio로 먼저 테스트** (매우 중요!)

   a) KOA Studio 실행:
      C:\\OpenAPI\\KOAStudioSA.exe

   b) 로그인 테스트:
      - 계좌번호
      - 비밀번호
      - 공인인증서 비밀번호

   c) 간단한 API 호출 테스트 (계좌 정보 조회 등)

   💡 이 단계에서 문제를 해결하면 Python에서 훨씬 쉽습니다!


2. **모의투자 신청** (아직 안 했다면)

   https://www1.kiwoom.com/h/common/bbs/VBbsPostInfo?brd_id=30&seq=1

   - 실전 계좌로 테스트하지 마세요!
   - 모의투자 계좌는 신청 후 즉시 사용 가능


3. **OpenAPI+ 서비스 신청** (아직 안 했다면)

   https://www3.kiwoom.com/h/customer/download/VOpenApiInfoView

   - 키움증권 웹사이트 로그인
   - OpenAPI+ 이용 신청
   - 승인까지 몇 분 소요


4. **Python 테스트**

   KOA Studio에서 로그인이 성공하면:

   python register_ocx_and_login.py

   또는 간단한 테스트:

   python -c "from kiwoom import Kiwoom; from PyQt5.QtWidgets import QApplication; import sys; app = QApplication(sys.argv); api = Kiwoom(); api.login()"


5. **문제 해결 체크리스트**

   로그인이 안 되면:

   ❑ 키움증권 HTS가 정상 작동하나요?
   ❑ 모의투자 계좌가 활성화되어 있나요?
   ❑ OpenAPI+ 서비스 신청이 승인되었나요?
   ❑ KOA Studio에서 로그인이 되나요?
   ❑ 32비트 Python을 사용하고 있나요?
   ❑ 백신 프로그램이 차단하고 있지 않나요?


📚 참고 자료:
   - breadum/kiwoom: https://github.com/breadum/kiwoom
   - 키움 OpenAPI+ 가이드: https://www3.kiwoom.com/h/customer/download/VOpenApiInfoView

""")


def main():
    """메인 실행 함수"""
    print_header("🔧 키움 OpenAPI+ 자동 설치 스크립트")

    print("""
이 스크립트는 다음을 수행합니다:

1. 선행 조건 확인 (32비트 Python, Windows, 관리자 권한)
2. OpenAPI+ 모듈 다운로드 및 설치
3. KOA Studio 다운로드 및 설치
4. 설치 검증
5. 다음 단계 안내

계속하시겠습니까? (y/n): """)

    response = input().strip().lower()
    if response != 'y':
        print("설치를 취소했습니다.")
        return

    # 1. 선행 조건 확인
    issues = check_prerequisites()
    if issues:
        print("\n⚠️  다음 문제를 해결한 후 다시 실행하세요:")
        for issue in issues:
            print(f"   {issue}")
        return

    # 2. OpenAPI+ 모듈 설치
    if not install_openapi_module():
        print("\n❌ OpenAPI+ 모듈 설치 실패")
        return

    input("\n⏸️  OpenAPI+ 설치가 완료되면 Enter를 누르세요...")

    # 3. KOA Studio 설치
    if not install_koa_studio():
        print("\n⚠️  KOA Studio 설치 실패 (선택사항)")

    # 4. 검증
    if verify_installation():
        print("\n✅ 설치가 성공적으로 완료되었습니다!")
    else:
        print("\n⚠️  설치가 완료되었지만 일부 검증 실패")
        print("   계속 진행할 수 있지만 문제가 발생할 수 있습니다.")

    # 5. 다음 단계
    print_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자가 취소했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
