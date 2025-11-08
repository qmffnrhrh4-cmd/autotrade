"""
OCX 파일 경로 확인 및 수정 도구

문제: 레지스트리에 등록된 경로와 실제 파일 경로가 다를 때
해결: 자동으로 파일 복사 및 재등록
"""
import os
import sys
import subprocess
import winreg
from pathlib import Path


def check_ocx_files():
    """OCX 파일 위치 확인"""
    print("="*80)
    print("📂 OCX 파일 위치 확인")
    print("="*80 + "\n")

    possible_paths = [
        Path("C:/OpenApi/KHOpenAPI64.ocx"),      # 소문자 i
        Path("C:/OpenAPI/KHOpenAPI64.ocx"),      # 대문자 I
        Path("C:/Openapi/KHOpenAPI64.ocx"),      # 소문자 api
        Path("C:/openapi/KHOpenAPI64.ocx"),      # 모두 소문자
    ]

    found_files = []

    for path in possible_paths:
        if path.exists():
            size = path.stat().st_size
            print(f"✅ 발견: {path}")
            print(f"   크기: {size:,} bytes\n")
            found_files.append(path)
        else:
            print(f"❌ 없음: {path}\n")

    return found_files


def check_registry():
    """레지스트리에 등록된 경로 확인"""
    print("="*80)
    print("📋 레지스트리 확인")
    print("="*80 + "\n")

    try:
        # ProgID 확인
        key = winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT,
            "KHOPENAPI.KHOpenAPICtrl.1",
            0,
            winreg.KEY_READ
        )
        clsid_value = winreg.QueryValue(key, "CLSID")
        print(f"✅ ProgID: KHOPENAPI.KHOpenAPICtrl.1")
        print(f"   CLSID: {clsid_value}\n")
        winreg.CloseKey(key)

        # InprocServer32 확인 (실제 OCX 경로)
        clsid_key = winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT,
            f"CLSID\\{clsid_value}\\InprocServer32",
            0,
            winreg.KEY_READ
        )
        registered_path = winreg.QueryValue(clsid_key, "")
        print(f"📌 레지스트리 등록 경로:")
        print(f"   {registered_path}\n")
        winreg.CloseKey(clsid_key)

        # 등록된 파일이 실제로 존재하는지 확인
        if Path(registered_path).exists():
            print(f"✅ 등록된 경로에 파일 존재")
        else:
            print(f"❌ 등록된 경로에 파일 없음!")
            print(f"   → 경로 불일치 문제!")

        return registered_path

    except Exception as e:
        print(f"❌ 레지스트리 확인 실패: {e}")
        return None


def fix_path_mismatch(found_files, registered_path):
    """경로 불일치 수정"""
    print("\n" + "="*80)
    print("🔧 경로 불일치 수정")
    print("="*80 + "\n")

    if not found_files:
        print("❌ OCX 파일을 찾을 수 없습니다.")
        print("   64bit-kiwoom-openapi를 먼저 설치하세요.")
        return False

    if not registered_path:
        print("❌ 레지스트리 정보를 찾을 수 없습니다.")
        return False

    registered_path_obj = Path(registered_path)

    # 실제 파일이 등록된 경로에 있는지 확인
    if registered_path_obj.exists():
        print("✅ 경로 일치 - 수정 불필요")
        return True

    # 경로 불일치 - 수정 필요
    print(f"⚠️  경로 불일치 발견!")
    print(f"   레지스트리: {registered_path}")
    print(f"   실제 파일: {found_files[0]}\n")

    print("수정 방법:")
    print(f"1. 파일 복사: {found_files[0]} → {registered_path}")
    print(f"2. OCX 재등록\n")

    choice = input("자동으로 수정하시겠습니까? (y/n): ").strip().lower()

    if choice != 'y':
        print("\n수동 수정 명령:")
        print(f"   mkdir {registered_path_obj.parent}")
        print(f"   copy {found_files[0]} {registered_path}")
        print(f"   regsvr32 /u {registered_path}")
        print(f"   regsvr32 {registered_path}")
        return False

    # 자동 수정
    try:
        # 1. 디렉토리 생성
        registered_path_obj.parent.mkdir(parents=True, exist_ok=True)
        print(f"✅ 폴더 생성/확인: {registered_path_obj.parent}")

        # 2. 파일 복사
        import shutil
        shutil.copy2(found_files[0], registered_path)
        print(f"✅ 파일 복사 완료")

        # 3. OCX 등록 해제
        result = subprocess.run(
            ['regsvr32', '/s', '/u', str(registered_path)],
            capture_output=True
        )
        print(f"✅ 기존 등록 해제")

        # 4. OCX 재등록
        result = subprocess.run(
            ['regsvr32', '/s', str(registered_path)],
            capture_output=True
        )

        if result.returncode == 0:
            print(f"✅ OCX 재등록 성공!")
            print(f"\n🎉 수정 완료!")
            print(f"   이제 다시 테스트해보세요.")
            return True
        else:
            print(f"❌ OCX 재등록 실패")
            print(f"   수동으로 실행: regsvr32 {registered_path}")
            return False

    except Exception as e:
        print(f"❌ 자동 수정 실패: {e}")
        print(f"\n수동으로 다음 명령을 실행하세요:")
        print(f"   copy {found_files[0]} {registered_path}")
        print(f"   regsvr32 {registered_path}")
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║                  🔍 OCX 파일 경로 확인 및 수정 도구                                      ║
║                                                                                      ║
║  목적: 레지스트리 경로와 실제 파일 경로 불일치 해결                                        ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
""")

    print("⚠️  이 도구는 관리자 권한으로 실행해야 합니다!\n")

    # 관리자 권한 확인
    import ctypes
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            print("❌ 관리자 권한이 없습니다!")
            print("   명령 프롬프트를 우클릭 → '관리자 권한으로 실행'\n")
            input("종료하려면 Enter를 누르세요...")
            sys.exit(1)
        else:
            print("✅ 관리자 권한 확인\n")
    except:
        print("⚠️  관리자 권한 확인 실패 (계속 진행)\n")

    # 1. OCX 파일 찾기
    found_files = check_ocx_files()

    # 2. 레지스트리 확인
    registered_path = check_registry()

    # 3. 경로 불일치 수정
    if found_files and registered_path:
        success = fix_path_mismatch(found_files, registered_path)

        if success:
            print("\n" + "="*80)
            print("✅ 모든 작업 완료!")
            print("="*80)
            print("\n다음 명령으로 테스트하세요:")
            print("   python test_simple_com_init.py")
    else:
        print("\n" + "="*80)
        print("❌ 수정 필요")
        print("="*80)

        if not found_files:
            print("\n64bit-kiwoom-openapi를 먼저 설치하세요:")
            print("   https://github.com/teranum/64bit-kiwoom-openapi/releases")

    print("\n" + "="*80)


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
