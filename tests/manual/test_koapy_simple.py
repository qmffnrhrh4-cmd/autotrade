"""
koapy 라이브러리를 사용한 간단한 로그인 테스트

koapy는 32비트/64비트 문제를 자동으로 처리합니다:
- 32비트 서버 프로세스를 자동 실행
- gRPC로 통신
- 64비트 Python에서도 사용 가능

설치:
    pip install koapy

사전 준비:
    1. config.conf 파일 생성 (또는 .koapy.conf)
    2. 계정 정보 입력
"""
import sys
import os
from pathlib import Path

# CRITICAL: Set QT_API before any Qt imports
os.environ['QT_API'] = 'pyqt5'

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_koapy_basic():
    """koapy 기본 연결 테스트"""
    print("=" * 80)
    print("  koapy 기본 연결 테스트")
    print("=" * 80)
    print()

    try:
        from koapy import KiwoomOpenApiPlusEntrypoint
    except ImportError:
        print("❌ koapy가 설치되지 않았습니다!")
        print()
        print("설치 방법:")
        print("  pip install koapy")
        print()
        print("참고:")
        print("  - koapy는 자동으로 32비트 서버를 실행합니다")
        print("  - 64비트 Python에서도 사용 가능합니다")
        print("  - gRPC 기반 통신으로 프로세스 격리")
        return False

    print("✅ koapy 모듈 로드 성공")
    print()

    # Context Manager 패턴 사용 (권장)
    print("🔐 koapy로 키움 Open API 연결 시도...")
    print("   (32비트 서버 프로세스가 자동으로 실행됩니다)")
    print()

    try:
        with KiwoomOpenApiPlusEntrypoint() as context:
            print("✅ KiwoomOpenApiPlusEntrypoint 생성 성공")
            print("   - gRPC 서버 실행됨")
            print("   - 포트: localhost:5943 (기본값)")
            print()

            # 연결 시도
            print("🔐 로그인 시도...")
            print("   (로그인창이 나타나면 수동으로 로그인하세요)")
            print()

            # Credential 없이 연결 (수동 로그인)
            context.EnsureConnected()

            print("✅ 연결 성공!")
            print()

            # 연결 상태 확인
            state = context.GetConnectState()
            print(f"연결 상태: {state} (1=연결됨, 0=연결안됨)")

            if state == 1:
                print()
                print("✅✅✅ 로그인 성공!")
                print()

                # 계좌 정보 확인
                try:
                    accounts = context.GetAccountList()
                    print(f"계좌 목록: {accounts}")
                except Exception as e:
                    print(f"계좌 조회 실패: {e}")

                return True
            else:
                print("❌ 로그인 실패")
                return False

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_koapy_with_credential():
    """koapy 자동 로그인 테스트 (Credential 사용)"""
    print("\n" + "=" * 80)
    print("  koapy 자동 로그인 테스트")
    print("=" * 80)
    print()

    try:
        from koapy import KiwoomOpenApiPlusEntrypoint
    except ImportError:
        print("❌ koapy가 설치되지 않았습니다!")
        return False

    # Credential 설정
    credential = {
        'user_id': '',  # 여기에 아이디 입력
        'user_password': '',  # 여기에 비밀번호 입력
        'cert_password': '',  # 여기에 공인인증서 비밀번호 입력
        'is_simulation': True,  # 모의투자 모드 (실전은 False)
    }

    # Credential이 비어있는지 확인
    if not credential['user_id']:
        print("⚠️  Credential이 설정되지 않았습니다.")
        print()
        print("자동 로그인을 사용하려면:")
        print("  1. 이 파일을 열어서 credential 딕셔너리에 정보 입력")
        print("  2. 또는 config.conf 파일 생성 (.koapy.conf)")
        print()
        print("예시:")
        print("""
credential = {
    'user_id': 'your_id',
    'user_password': 'your_password',
    'cert_password': 'cert_password',
    'is_simulation': True,
}
        """)
        return False

    print("✅ Credential 설정 확인")
    print(f"   아이디: {credential['user_id']}")
    print(f"   모의투자: {credential['is_simulation']}")
    print()

    try:
        with KiwoomOpenApiPlusEntrypoint() as context:
            print("✅ KiwoomOpenApiPlusEntrypoint 생성 성공")
            print()

            # Credential로 자동 로그인
            print("🔐 자동 로그인 시도...")
            context.EnsureConnected(credential)

            state = context.GetConnectState()
            print(f"연결 상태: {state}")

            if state == 1:
                print("✅✅✅ 자동 로그인 성공!")
                print()

                # 계좌 정보
                accounts = context.GetAccountList()
                print(f"계좌 목록: {accounts}")

                return True
            else:
                print("❌ 자동 로그인 실패")
                return False

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║              🔬 koapy 라이브러리 테스트                                   ║
║                                                                          ║
║  koapy는 32비트/64비트 문제를 자동으로 해결합니다                          ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

📌 koapy의 장점:
   ✓ 32비트 서버를 자동으로 실행 (OCX 요구사항 충족)
   ✓ 64비트 Python에서 사용 가능 (gRPC 통신)
   ✓ 프로세스 격리로 안정성 향상
   ✓ High-level API 제공 (편리함)

📌 설치:
   pip install koapy

📌 Python 비트 확인:
""")

    import platform
    import struct
    bits = struct.calcsize("P") * 8
    print(f"   현재 Python: {bits}-bit")
    print()

    # 테스트 1: 기본 연결
    result1 = test_koapy_basic()

    # 테스트 2: 자동 로그인 (선택사항)
    print("\n")
    print("=" * 80)
    print("자동 로그인 테스트를 진행하시겠습니까? (y/n)")
    choice = input("선택: ").strip().lower()

    if choice == 'y':
        result2 = test_koapy_with_credential()
    else:
        result2 = None
        print("자동 로그인 테스트를 건너뜁니다.")

    # 최종 요약
    print("\n" + "=" * 80)
    print("  📊 테스트 결과")
    print("=" * 80)
    print()

    if result1:
        print("✅ 기본 연결 테스트: 성공")
        print()
        print("💡 다음 단계:")
        print("   1. koapy 라이브러리를 프로젝트에 통합")
        print("   2. config.conf 파일로 설정 관리")
        print("   3. High-level API로 데이터 조회")
        print()
        print("예시:")
        print("""
from koapy import KiwoomOpenApiPlusEntrypoint

with KiwoomOpenApiPlusEntrypoint() as context:
    context.EnsureConnected()

    # 주식 기본 정보 조회
    info = context.GetStockBasicInfoAsDict('005930')

    # 일별 시세 조회
    df = context.GetDailyStockDataAsDataFrame('005930')

    print(info)
    print(df)
        """)
    else:
        print("❌ 기본 연결 테스트: 실패")
        print()
        print("💡 해결책:")
        print("   1. koapy 설치: pip install koapy")
        print("   2. 32비트 Python 환경 설정 (koapy 서버용)")
        print("   3. 키움증권 Open API+ 설치")
        print("   4. 방화벽 설정 확인 (localhost:5943)")

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
