"""
Kiwoom 64비트 OpenAPI 진단 도구

목적: CommConnect 오류(0x8000FFFF) 원인 진단 및 해결

오류 코드 0x8000FFFF (E_UNEXPECTED) 원인:
1. 다른 Kiwoom 프로세스 실행 중 (가장 흔함) ⭐
2. 로그인 서버 연결 실패
3. 방화벽/백신 차단
4. OCX 등록 문제
"""
import sys
import subprocess
import winreg
from pathlib import Path

def print_header(title):
    """헤더 출력"""
    print(f"\n{'='*100}")
    print(f"  {title}")
    print(f"{'='*100}\n")

def kill_kiwoom_processes():
    """Kiwoom 프로세스 강제 종료"""
    print("\n🔧 Kiwoom 프로세스 강제 종료 시도 중...")

    processes = ["KHOpenAPI.exe", "KHOpenAPICtrl.exe", "OpSysMsg.exe", "KHOpenApi64.exe"]
    killed_any = False

    for proc in processes:
        try:
            result = subprocess.run(
                ['taskkill', '/F', '/IM', proc],
                capture_output=True,
                text=True,
                encoding='cp949'
            )
            if result.returncode == 0:
                print(f"   ✅ {proc} 종료 완료")
                killed_any = True
            else:
                print(f"   ℹ️  {proc} 실행 중이 아님")
        except Exception as e:
            print(f"   ⚠️  {proc} 종료 실패: {e}")

    if killed_any:
        print("\n💡 프로세스 종료 후 1초 대기 중...")
        time.sleep(1)

    return killed_any

def check_kiwoom_processes():
    """실행 중인 Kiwoom 프로세스 확인"""
    print("📌 Step 1: Kiwoom 관련 프로세스 확인\n")

    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq KH*', '/FO', 'CSV'],
            capture_output=True,
            text=True,
            encoding='cp949'
        )

        lines = result.stdout.strip().split('\n')

        if len(lines) <= 1 or '정보: 지정한 조건을' in result.stdout:
            print("✅ Kiwoom 관련 프로세스 없음 (정상)")
            return True
        else:
            print("⚠️  다음 Kiwoom 프로세스가 실행 중입니다:\n")
            processes_found = []
            for line in lines[1:]:
                if line.strip():
                    parts = line.split(',')
                    if len(parts) > 0:
                        process_name = parts[0].strip('"')
                        print(f"   - {process_name}")
                        processes_found.append(process_name)

            print("\n🔧 해결 방법:")
            print("   1. 키움증권 HTS (영웅문) 종료")
            print("   2. 다른 Open API 기반 프로그램 종료")
            print("   3. 작업 관리자에서 모든 KH* 프로세스 강제 종료")
            print("\n   또는 자동으로 종료하시겠습니까? (y/n): ", end="")

            try:
                choice = input().strip().lower()
                if choice == 'y':
                    if kill_kiwoom_processes():
                        print("\n✅ 프로세스 종료 완료! 계속 진행합니다...")
                        return True
            except:
                pass

            return False

    except Exception as e:
        print(f"⚠️  프로세스 확인 실패: {e}")
        return True

def find_ocx_file():
    """OCX 파일 경로 찾기"""
    possible_paths = [
        Path("C:/OpenApi/KHOpenAPI64.ocx"),
        Path("C:/OpenAPI/KHOpenAPI64.ocx"),
        Path("C:/Program Files/Kiwoom/OpenAPI/KHOpenAPI64.ocx"),
        Path("C:/Program Files (x86)/Kiwoom/OpenAPI/KHOpenAPI64.ocx"),
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None

def check_ocx_registration():
    """OCX 등록 상태 확인"""
    print("\n📌 Step 2: OCX 등록 상태 확인\n")

    # 먼저 OCX 파일 존재 여부 확인
    print("🔍 OCX 파일 검색 중...")
    ocx_path = find_ocx_file()

    if ocx_path:
        print(f"✅ OCX 파일 발견: {ocx_path}")
        print(f"   파일 크기: {ocx_path.stat().st_size:,} bytes")
    else:
        print("❌ OCX 파일을 찾을 수 없습니다!")
        print("\n🔧 해결 방법:")
        print("   1. 64bit-kiwoom-openapi 설치:")
        print("      https://github.com/teranum/64bit-kiwoom-openapi")
        print("   2. OCX 파일이 다음 경로 중 하나에 있어야 합니다:")
        print("      - C:\\OpenApi\\KHOpenAPI64.ocx")
        print("      - C:\\OpenAPI\\KHOpenAPI64.ocx")
        return False

    # ProgID 레지스트리 확인
    print("\n🔍 레지스트리 확인 중...")
    try:
        # ProgID 확인
        key = winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT,
            "KHOPENAPI.KHOpenAPICtrl.1",
            0,
            winreg.KEY_READ
        )

        print("✅ ProgID 등록 확인됨: KHOPENAPI.KHOpenAPICtrl.1")

        # CLSID 확인
        clsid_value = winreg.QueryValue(key, "CLSID")
        print(f"   CLSID: {clsid_value}")

        winreg.CloseKey(key)

        # OCX 파일 위치 확인
        try:
            clsid_key = winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                f"CLSID\\{clsid_value}\\InprocServer32",
                0,
                winreg.KEY_READ
            )

            registered_ocx_path = winreg.QueryValue(clsid_key, "")
            print(f"   등록된 OCX 경로: {registered_ocx_path}")

            if Path(registered_ocx_path).exists():
                print(f"   ✅ 등록된 OCX 파일 존재 확인")
            else:
                print(f"   ⚠️  등록된 OCX 파일이 존재하지 않습니다!")
                print(f"\n   현재 발견된 OCX: {ocx_path}")
                print(f"   등록된 경로: {registered_ocx_path}")
                print("\n   → OCX 재등록이 필요합니다!")

            winreg.CloseKey(clsid_key)

        except Exception as e:
            print(f"   ⚠️  OCX 경로 확인 실패: {e}")

        return True

    except FileNotFoundError:
        print("❌ ProgID가 등록되지 않았습니다!")
        print("\n🔧 자동 등록 시도 가능:")
        print("   이 스크립트를 관리자 권한으로 실행하면 자동으로 OCX를 등록할 수 있습니다.")
        print("\n🔧 수동 등록 방법:")
        print("   1. 관리자 권한으로 명령 프롬프트 실행")
        print(f"   2. 다음 명령 실행:")
        print(f"      regsvr32 \"{ocx_path}\"")

        # 관리자 권한 확인
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if is_admin:
                print("\n✅ 관리자 권한 감지!")
                print("   자동으로 OCX 등록을 시도하시겠습니까? (y/n): ", end="")
                choice = input().strip().lower()

                if choice == 'y':
                    return register_ocx(ocx_path)
            else:
                print("\n⚠️  관리자 권한이 필요합니다.")
                print("   이 스크립트를 마우스 오른쪽 버튼 → '관리자 권한으로 실행'으로 다시 실행하세요.")
        except:
            pass

        return False

    except Exception as e:
        print(f"❌ 레지스트리 확인 실패: {e}")
        return False

def register_ocx(ocx_path):
    """OCX 등록 시도"""
    print(f"\n🔧 OCX 등록 시도 중: {ocx_path}")

    try:
        result = subprocess.run(
            ['regsvr32', '/s', str(ocx_path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ OCX 등록 성공!")
            print("   이제 테스트를 다시 실행해보세요.")
            return True
        else:
            print(f"❌ OCX 등록 실패 (return code: {result.returncode})")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ OCX 등록 중 오류: {e}")
        return False

def check_firewall():
    """방화벽 설정 확인"""
    print("\n📌 Step 3: 방화벽 설정 확인\n")

    print("💡 수동 확인 필요:")
    print("   1. Windows Defender 방화벽 설정 확인")
    print("   2. 백신 프로그램 실시간 감시 일시 중지")
    print("   3. Kiwoom OpenAPI 통신 허용 확인")
    print()

def check_python_arch():
    """Python 아키텍처 확인"""
    print("📌 Step 4: Python 환경 확인\n")

    import struct
    import platform

    bits = struct.calcsize("P") * 8

    print(f"   Python 버전: {platform.python_version()}")
    print(f"   Python 아키텍처: {bits}비트")

    if bits == 64:
        print("   ✅ 64비트 Python (정상)")
        return True
    else:
        print("   ❌ 32비트 Python 감지!")
        print("\n🔧 해결 방법:")
        print("   64비트 Python 3.11.9 설치 필요")
        print("   https://www.python.org/downloads/")
        return False

def test_com_initialization():
    """COM 초기화 테스트"""
    print("\n📌 Step 5: COM 초기화 테스트\n")

    try:
        import pythoncom
        pythoncom.CoInitialize()
        print("✅ COM 초기화 성공")
        pythoncom.CoUninitialize()
        return True
    except Exception as e:
        print(f"❌ COM 초기화 실패: {e}")
        return False

def test_activex_creation():
    """ActiveX 컨트롤 생성 테스트"""
    print("\n📌 Step 6: ActiveX 컨트롤 생성 테스트\n")

    try:
        import win32com.client
        import pythoncom

        pythoncom.CoInitialize()

        ocx = win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")
        print("✅ ActiveX 컨트롤 생성 성공")

        # 간단한 메서드 호출 테스트
        try:
            # GetAPIModulePath는 로그인 없이도 호출 가능
            path = ocx.GetAPIModulePath()
            print(f"   API 모듈 경로: {path}")
        except Exception as e:
            print(f"   ⚠️  API 모듈 경로 확인 실패: {e}")

        pythoncom.CoUninitialize()
        return True

    except Exception as e:
        print(f"❌ ActiveX 컨트롤 생성 실패: {e}")
        print("\n🔧 해결 방법:")
        print("   1. OCX 재등록:")
        print("      regsvr32 /u C:\\OpenApi\\KHOpenAPI64.ocx")
        print("      regsvr32 C:\\OpenApi\\KHOpenAPI64.ocx")
        print("   2. PC 재부팅")
        return False

def create_helper_scripts(ocx_path):
    """헬퍼 배치 파일들 생성"""
    scripts_created = []

    # 1. OCX 등록 스크립트
    try:
        register_batch = f"""@echo off
echo ============================================
echo Kiwoom 64-bit OpenAPI OCX 등록 스크립트
echo ============================================
echo.

echo OCX 파일: {ocx_path}
echo.

echo 기존 등록 해제 중...
regsvr32 /u /s "{ocx_path}"

echo 새로 등록 중...
regsvr32 /s "{ocx_path}"

if %errorlevel% equ 0 (
    echo.
    echo ✅ OCX 등록 성공!
    echo.
) else (
    echo.
    echo ❌ OCX 등록 실패!
    echo 관리자 권한으로 실행했는지 확인하세요.
    echo.
)

pause
"""
        batch_file = Path(__file__).parent / "register_kiwoom_ocx.bat"
        with open(batch_file, 'w', encoding='cp949') as f:
            f.write(register_batch)
        scripts_created.append(batch_file)
        print(f"\n💾 OCX 등록 스크립트 생성: {batch_file}")

    except Exception as e:
        print(f"❌ OCX 등록 스크립트 생성 실패: {e}")

    # 2. 프로세스 종료 스크립트
    try:
        kill_batch = """@echo off
echo ============================================
echo Kiwoom 프로세스 강제 종료 스크립트
echo ============================================
echo.

echo 실행 중인 Kiwoom 프로세스를 확인합니다...
echo.

tasklist | findstr /I "KH"

echo.
echo 위의 프로세스들을 강제 종료합니다...
echo.

taskkill /F /IM KHOpenAPI.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ KHOpenAPI.exe 종료 완료
) else (
    echo ℹ️  KHOpenAPI.exe 실행 중이 아님
)

taskkill /F /IM KHOpenAPICtrl.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ KHOpenAPICtrl.exe 종료 완료
) else (
    echo ℹ️  KHOpenAPICtrl.exe 실행 중이 아님
)

taskkill /F /IM OpSysMsg.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ OpSysMsg.exe 종료 완료
) else (
    echo ℹ️  OpSysMsg.exe 실행 중이 아님
)

taskkill /F /IM KHOpenApi64.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ KHOpenApi64.exe 종료 완료
) else (
    echo ℹ️  KHOpenApi64.exe 실행 중이 아님
)

echo.
echo ============================================
echo 프로세스 종료 완료!
echo ============================================
echo.

pause
"""
        kill_file = Path(__file__).parent / "kill_kiwoom_processes.bat"
        with open(kill_file, 'w', encoding='cp949') as f:
            f.write(kill_batch)
        scripts_created.append(kill_file)
        print(f"💾 프로세스 종료 스크립트 생성: {kill_file}")

    except Exception as e:
        print(f"❌ 프로세스 종료 스크립트 생성 실패: {e}")

    if scripts_created:
        print("\n   생성된 헬퍼 스크립트:")
        for script in scripts_created:
            print(f"   - {script.name}")

    return scripts_created

def print_solution_summary(ocx_path=None):
    """종합 해결 방법"""
    print_header("💡 종합 해결 방법")

    print("🔧 0x8000FFFF 오류 해결 순서:\n")

    print("1️⃣  모든 Kiwoom 프로세스 종료 (가장 중요!) ⭐")
    print("   - HTS (영웅문) 종료")
    print("   - 다른 API 프로그램 종료")
    print("   - 작업 관리자에서 KH* 프로세스 강제 종료:")
    print("     taskkill /F /IM KHOpenAPI.exe")
    print("     taskkill /F /IM OpSysMsg.exe")
    print()

    print("2️⃣  OCX 등록 (관리자 권한)")
    if ocx_path:
        print(f"   수동 등록:")
        print(f"     regsvr32 \"{ocx_path}\"")
        print()
        print("   또는 생성된 헬퍼 스크립트 사용:")
        scripts = create_helper_scripts(ocx_path)
    else:
        print("   regsvr32 C:\\OpenApi\\KHOpenAPI64.ocx")
    print()

    print("3️⃣  PC 재부팅 (권장)")
    print("   - 완전한 프로세스 종료")
    print("   - COM 객체 정리")
    print()

    print("4️⃣  관리자 권한으로 실행")
    print("   - 명령 프롬프트를 관리자 권한으로 실행")
    print("   - python test_samsung_1year_minute_data.py")
    print()

    print("5️⃣  방화벽/백신 일시 중지")
    print("   - Windows Defender 실시간 보호 일시 중지")
    print("   - 백신 프로그램 일시 중지")
    print()

def main():
    """메인 진단 함수"""

    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║                  🔍 Kiwoom 64비트 OpenAPI 진단 도구                                    ║
║                                                                                      ║
║  목적: CommConnect 오류 (0x8000FFFF) 원인 진단 및 해결                                  ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
""")

    print_header("🚀 진단 시작")

    # OCX 파일 경로 저장 (솔루션 요약에서 사용)
    ocx_file_path = find_ocx_file()

    results = {
        "프로세스 확인": check_kiwoom_processes(),
        "OCX 등록": check_ocx_registration(),
        "Python 아키텍처": check_python_arch(),
        "COM 초기화": test_com_initialization(),
        "ActiveX 생성": test_activex_creation(),
    }

    check_firewall()

    # 결과 요약
    print_header("📊 진단 결과 요약")

    for test_name, result in results.items():
        status = "✅ 통과" if result else "❌ 실패"
        print(f"   {test_name:20} : {status}")

    # 모든 테스트 통과 여부
    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 모든 진단 항목 통과!")
        print("\n그래도 로그인 오류가 발생한다면:")
        print("   1. PC 재부팅 (중요!)")
        print("   2. 재부팅 후 다른 프로그램 실행하지 말고 바로 테스트")
        print("   3. 관리자 권한으로 실행")
    else:
        print("\n⚠️  일부 진단 항목 실패")
        print("위의 해결 방법을 참고하여 문제를 해결하세요.")

    print_solution_summary(ocx_file_path)

    print("\n" + "="*100)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  진단이 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 진단 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    print("\n진단 종료. 창을 닫으려면 Enter를 누르세요...")
    input()
