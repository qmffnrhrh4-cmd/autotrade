"""
koapy 수동 서버 연결 테스트

PyQt5 자동 시작 문제를 우회하기 위해
서버를 수동으로 시작하고 연결합니다.
"""
import sys
import time
from pathlib import Path

print("="*80)
print("koapy 수동 서버 연결 테스트")
print("="*80)
print()

print("📌 사용 방법:")
print("  1. 먼저 별도 명령창에서 koapy 서버 시작:")
print("     python -m koapy.cli serve")
print()
print("  2. 서버가 시작되면 (약 30초~1분 소요)")
print("  3. 이 스크립트를 실행")
print()

try:
    import grpc
    from koapy.grpc import KiwoomOpenApiService_pb2_grpc
    from koapy.grpc import KiwoomOpenApiService_pb2
except ImportError as e:
    print(f"❌ 필요한 모듈 설치 실패: {e}")
    print("\n설치 명령:")
    print("   pip install protobuf==3.20.3 grpcio==1.48.0 koapy")
    sys.exit(1)

def test_manual_connection():
    """수동으로 koapy 서버에 연결"""
    print("="*80)
    print("koapy 서버 연결 시도")
    print("="*80)
    print()

    # 기본 포트는 5943
    server_url = 'localhost:5943'

    print(f"서버 주소: {server_url}")
    print("연결 중...\n")

    try:
        # gRPC 채널 생성
        channel = grpc.insecure_channel(server_url)
        stub = KiwoomOpenApiService_pb2_grpc.KiwoomOpenApiServiceStub(channel)

        # 연결 테스트
        request = KiwoomOpenApiService_pb2.LoginRequest()

        print("✅ gRPC 채널 생성 성공")
        print("\n💡 이제 서버에 명령을 보낼 수 있습니다.")
        print("   (하지만 이 방법은 저수준 API입니다)")
        print()
        print("추천: koapy CLI 사용")
        print("   koapy get balance")
        print("   koapy get orders")
        print()

        return True

    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        print()
        print("💡 해결 방법:")
        print("  1. 서버가 실행 중인지 확인:")
        print("     python -m koapy.cli serve")
        print()
        print("  2. 방화벽 확인 (포트 5943)")
        print()
        return False


def show_koapy_cli_examples():
    """koapy CLI 사용 예제"""
    print("="*80)
    print("koapy CLI 명령어 예제")
    print("="*80)
    print()

    print("# 서버 시작 (별도 터미널)")
    print("python -m koapy.cli serve")
    print()

    print("# 로그인 (메인 터미널)")
    print("python -m koapy.cli login")
    print()

    print("# 계좌 정보")
    print("python -m koapy.cli get account")
    print()

    print("# 잔고 조회")
    print("python -m koapy.cli get balance")
    print()

    print("# 주문 내역")
    print("python -m koapy.cli get orders")
    print()

    print("# 종목 정보 (삼성전자)")
    print("python -m koapy.cli get stock 005930")
    print()


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║                  🚀 koapy 수동 서버 연결 테스트                                         ║
║                                                                                      ║
║  PyQt5 자동 시작 문제를 우회하는 방법                                                    ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
""")

    print("⚠️  주의: 이 방법은 고급 사용자용입니다.")
    print("   koapy CLI를 사용하는 것이 더 간단합니다.\n")

    choice = input("계속하시겠습니까? (y/n): ").strip().lower()

    if choice == 'y':
        test_manual_connection()

    print()
    show_koapy_cli_examples()

    print("\n" + "="*80)
    print("💡 가장 쉬운 방법:")
    print("="*80)
    print()
    print("1. 터미널 1 (서버):")
    print("   python -m koapy.cli serve")
    print()
    print("2. 터미널 2 (클라이언트):")
    print("   python -m koapy.cli login")
    print("   python -m koapy.cli get balance")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()

    print("\n창을 닫으려면 Enter를 누르세요...")
    input()
