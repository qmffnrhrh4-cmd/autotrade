"""
koapy를 사용한 키움 Open API 테스트

64bit-kiwoom-openapi가 작동하지 않을 때 대안으로 사용
koapy는 32비트 프로세스를 백그라운드에서 실행하고 gRPC로 통신
"""
import sys
from pathlib import Path

print("="*80)
print("koapy 설치 확인 중...")
print("="*80)

try:
    from koapy import KiwoomOpenApiContext
    print("✅ koapy 설치 확인됨\n")
except ImportError:
    print("❌ koapy가 설치되지 않았습니다!")
    print("\n설치 방법:")
    print("   pip install koapy\n")
    print("설치 후 다시 실행하세요.")
    input("\n종료하려면 Enter를 누르세요...")
    sys.exit(1)


def test_koapy_login():
    """koapy 로그인 테스트"""
    print("="*80)
    print("koapy 로그인 테스트")
    print("="*80)
    print()

    print("📌 중요:")
    print("  1. 처음 실행 시 32비트 서버가 자동으로 시작됩니다")
    print("  2. 로그인 창이 나타나면 ID/PW를 입력하세요")
    print("  3. 서버 시작에 시간이 걸릴 수 있습니다 (30초~1분)\n")

    try:
        # koapy 컨텍스트 생성 (자동으로 서버 시작)
        with KiwoomOpenApiContext() as context:
            print("✅ koapy 서버 연결 성공!")

            # 로그인
            print("\n🔐 로그인 시도 중...")
            print("   (로그인 창이 나타날 때까지 기다려주세요...)\n")

            context.EnsureConnected()
            print("✅ 로그인 성공!\n")

            # 계정 정보 조회
            print("="*80)
            print("📋 계정 정보")
            print("="*80)

            account_count = context.GetLoginInfo("ACCOUNT_CNT")
            accounts = context.GetLoginInfo("ACCNO")
            user_id = context.GetLoginInfo("USER_ID")
            user_name = context.GetLoginInfo("USER_NM")

            print(f"사용자 ID: {user_id}")
            print(f"사용자 이름: {user_name}")
            print(f"계좌 개수: {account_count}")
            print(f"계좌 목록: {accounts}\n")

            # 삼성전자 현재가 조회 테스트
            print("="*80)
            print("📊 삼성전자(005930) 현재가 조회")
            print("="*80)

            # TR 요청 준비
            context.SetInputValue("종목코드", "005930")

            # TR 요청 (opt10001 = 주식기본정보)
            context.CommRqData("주식기본정보", "opt10001", 0, "0101")

            # 이벤트 대기
            event = context.api.OnReceiveTrData.wait()

            if event:
                # 데이터 파싱
                stock_name = context.GetCommData("opt10001", "주식기본정보", 0, "종목명").strip()
                current_price = context.GetCommData("opt10001", "주식기본정보", 0, "현재가").strip()
                prev_diff = context.GetCommData("opt10001", "주식기본정보", 0, "전일대비").strip()

                print(f"종목명: {stock_name}")
                print(f"현재가: {current_price}원")
                print(f"전일대비: {prev_diff}원\n")

                print("✅ koapy 테스트 성공!")
            else:
                print("⚠️  데이터 수신 실패")

    except Exception as e:
        print(f"❌ koapy 오류: {e}")
        import traceback
        traceback.print_exc()

        print("\n💡 문제 해결:")
        print("  1. 키움증권 로그인 ID/PW 확인")
        print("  2. 인증서 확인")
        print("  3. koapy 재설치: pip uninstall koapy && pip install koapy")
        print("  4. PC 재부팅 후 재시도")
        return False

    return True


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║                  🚀 koapy - 키움 Open API 대안 테스트                                   ║
║                                                                                      ║
║  64bit-kiwoom-openapi가 작동하지 않을 때 사용하는 안정적인 대안                            ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
""")

    try:
        success = test_koapy_login()

        if success:
            print("\n" + "="*80)
            print("✅ koapy 사용 가능!")
            print("="*80)
            print("\n이제 koapy를 사용하여 자동매매를 구현할 수 있습니다.")
            print("기존 코드를 koapy 방식으로 변환하거나,")
            print("통합 예제 파일을 참고하세요.")

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("테스트 종료.")
    print("="*80)


if __name__ == '__main__':
    main()
    print("\n창을 닫으려면 Enter를 누르세요...")
    input()
