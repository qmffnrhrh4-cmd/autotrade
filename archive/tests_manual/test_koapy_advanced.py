"""
koapy 라이브러리를 사용한 고급 예제

실제 데이터 조회 및 거래 예제를 포함합니다.

참고:
    - AutomaticPosting-koapy: https://github.com/meteormin/AutomaticPosting-koapy
    - koapy 공식: https://github.com/elbakramer/koapy
"""
import sys
import os
from pathlib import Path

# CRITICAL: Set QT_API before any Qt imports
os.environ['QT_API'] = 'pyqt5'

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_stock_basic_info():
    """주식 기본 정보 조회"""
    print("=" * 80)
    print("  주식 기본 정보 조회")
    print("=" * 80)
    print()

    try:
        from koapy import KiwoomOpenApiPlusEntrypoint
    except ImportError:
        print("❌ koapy가 설치되지 않았습니다!")
        return False

    try:
        with KiwoomOpenApiPlusEntrypoint() as context:
            print("✅ koapy 연결 성공")

            # 로그인
            context.EnsureConnected()
            print("✅ 로그인 성공")
            print()

            # 삼성전자 기본 정보 조회
            code = '005930'  # 삼성전자
            print(f"📊 [{code}] 삼성전자 기본 정보 조회...")
            print()

            # 방법 1: High-level API (권장)
            info = context.GetStockBasicInfoAsDict(code)

            print("기본 정보:")
            for key, value in info.items():
                print(f"  {key}: {value}")

            print()

            # 종목명 조회
            name = context.GetMasterCodeName(code)
            print(f"종목명: {name}")

            # 현재가 조회
            current_price = context.GetMasterLastPrice(code)
            print(f"현재가: {current_price:,}원")

            # 상장주식수
            stocks = context.GetMasterStockAmount(code)
            print(f"상장주식수: {stocks:,}주")

            print()
            print("✅ 기본 정보 조회 성공")

            return True

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_daily_stock_data():
    """일별 주가 데이터 조회"""
    print("\n" + "=" * 80)
    print("  일별 주가 데이터 조회")
    print("=" * 80)
    print()

    try:
        from koapy import KiwoomOpenApiPlusEntrypoint
        import pandas as pd
    except ImportError as e:
        print(f"❌ 필요한 모듈이 설치되지 않았습니다: {e}")
        print("설치: pip install koapy pandas")
        return False

    try:
        with KiwoomOpenApiPlusEntrypoint() as context:
            context.EnsureConnected()
            print("✅ 로그인 성공")
            print()

            # 삼성전자 일별 데이터 조회
            code = '005930'
            print(f"📈 [{code}] 일별 주가 데이터 조회 (최근 20일)...")
            print()

            # DataFrame으로 조회
            df = context.GetDailyStockDataAsDataFrame(
                code,
                adjusted_price=True  # 수정주가 사용
            )

            # 최근 20일만 표시
            df = df.head(20)

            print(df)
            print()

            # 통계 정보
            print("통계 정보:")
            print(f"  평균 종가: {df['현재가'].mean():,.0f}원")
            print(f"  최고가: {df['현재가'].max():,.0f}원")
            print(f"  최저가: {df['현재가'].min():,.0f}원")
            print(f"  평균 거래량: {df['거래량'].mean():,.0f}주")

            print()
            print("✅ 일별 데이터 조회 성공")

            return True

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_account_info():
    """계좌 정보 조회"""
    print("\n" + "=" * 80)
    print("  계좌 정보 조회")
    print("=" * 80)
    print()

    try:
        from koapy import KiwoomOpenApiPlusEntrypoint
    except ImportError:
        print("❌ koapy가 설치되지 않았습니다!")
        return False

    try:
        with KiwoomOpenApiPlusEntrypoint() as context:
            context.EnsureConnected()
            print("✅ 로그인 성공")
            print()

            # 계좌 목록 조회
            accounts = context.GetAccountList()
            print(f"계좌 목록: {accounts}")
            print()

            if not accounts:
                print("⚠️  계좌가 없습니다.")
                return False

            # 첫 번째 계좌 선택
            account = accounts[0]
            print(f"선택된 계좌: {account}")
            print()

            # 예수금 조회
            try:
                deposit = context.GetDepositInfo(account)
                print("예수금 정보:")
                for key, value in deposit.items():
                    print(f"  {key}: {value}")
                print()
            except Exception as e:
                print(f"⚠️  예수금 조회 실패: {e}")

            # 보유 종목 조회
            try:
                print("보유 종목 조회...")
                stocks = context.GetAccountStockInfo(account)

                if stocks:
                    print("보유 종목:")
                    for stock in stocks:
                        print(f"  {stock}")
                else:
                    print("  보유 종목 없음")
                print()
            except Exception as e:
                print(f"⚠️  보유 종목 조회 실패: {e}")

            print("✅ 계좌 정보 조회 성공")
            return True

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_condition_search():
    """조건 검색식 사용"""
    print("\n" + "=" * 80)
    print("  조건 검색식 사용")
    print("=" * 80)
    print()

    try:
        from koapy import KiwoomOpenApiPlusEntrypoint
    except ImportError:
        print("❌ koapy가 설치되지 않았습니다!")
        return False

    try:
        with KiwoomOpenApiPlusEntrypoint() as context:
            context.EnsureConnected()
            print("✅ 로그인 성공")
            print()

            # 조건 검색식 로드
            print("📋 조건 검색식 로드 중...")
            context.EnsureConditionLoaded()
            print("✅ 조건 검색식 로드 완료")
            print()

            # 조건 목록 가져오기
            conditions = context.GetConditionNameListAsList()

            if not conditions:
                print("⚠️  저장된 조건 검색식이 없습니다.")
                print()
                print("💡 HTS(영웅문)에서 조건 검색식을 먼저 만들어야 합니다:")
                print("   1. 영웅문 실행")
                print("   2. [0150] 조건검색 메뉴")
                print("   3. 조건식 저장")
                return False

            print(f"조건 검색식 목록 ({len(conditions)}개):")
            for idx, (index, name) in enumerate(conditions, 1):
                print(f"  {idx}. [{index}] {name}")
            print()

            # 첫 번째 조건으로 검색
            if conditions:
                condition_index, condition_name = conditions[0]
                print(f"'{condition_name}' 조건으로 종목 검색 중...")
                print()

                codes = context.GetCodeListByCondition(condition_name)

                print(f"검색 결과: {len(codes)}개 종목")
                for i, code in enumerate(codes[:10], 1):  # 최대 10개만 표시
                    name = context.GetMasterCodeName(code)
                    price = context.GetMasterLastPrice(code)
                    print(f"  {i}. [{code}] {name}: {price:,}원")

                if len(codes) > 10:
                    print(f"  ... 외 {len(codes) - 10}개")

                print()

            print("✅ 조건 검색 성공")
            return True

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_low_level_tr_call():
    """Low-level TR 호출 (고급)"""
    print("\n" + "=" * 80)
    print("  Low-level TR 호출 (고급)")
    print("=" * 80)
    print()

    try:
        from koapy import KiwoomOpenApiPlusEntrypoint
    except ImportError:
        print("❌ koapy가 설치되지 않았습니다!")
        return False

    try:
        with KiwoomOpenApiPlusEntrypoint() as context:
            context.EnsureConnected()
            print("✅ 로그인 성공")
            print()

            # OPT10001: 주식기본정보요청
            rqname = "주식기본정보"
            trcode = "OPT10001"
            screenno = "0001"

            inputs = {
                "종목코드": "005930"  # 삼성전자
            }

            print(f"📡 TR 호출: {trcode} ({rqname})")
            print(f"   입력값: {inputs}")
            print()

            # TR 호출 (이벤트 스트림)
            for event in context.TransactionCall(rqname, trcode, screenno, inputs):
                print(f"이벤트 수신: {event.name}")

                # 단일 데이터
                if event.single_data.names:
                    print("\n단일 데이터:")
                    single_dict = dict(zip(event.single_data.names, event.single_data.values))
                    for key, value in single_dict.items():
                        print(f"  {key}: {value}")

                # 멀티 데이터
                if event.multi_data.names:
                    print("\n멀티 데이터:")
                    for row in event.multi_data.values:
                        row_dict = dict(zip(event.multi_data.names, row.values))
                        print(f"  {row_dict}")

            print()
            print("✅ TR 호출 성공")
            return True

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║             🔬 koapy 고급 기능 테스트                                     ║
║                                                                          ║
║  실제 데이터 조회 및 거래 기능을 테스트합니다                              ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

⚠️  주의사항:
   - 실제 계좌로 테스트하기 전에 모의투자로 먼저 테스트하세요
   - is_simulation=True로 설정하면 모의투자 모드입니다

📌 테스트 목록:
   1. 주식 기본 정보 조회 (삼성전자)
   2. 일별 주가 데이터 조회
   3. 계좌 정보 조회
   4. 조건 검색식 사용
   5. Low-level TR 호출 (고급)

""")

    # Python 비트 확인
    import platform
    import struct
    bits = struct.calcsize("P") * 8
    print(f"현재 Python: {bits}-bit")
    print("(koapy는 32/64비트 모두 지원합니다)")
    print()

    # 메뉴
    tests = [
        ("주식 기본 정보 조회", test_stock_basic_info),
        ("일별 주가 데이터 조회", test_daily_stock_data),
        ("계좌 정보 조회", test_account_info),
        ("조건 검색식 사용", test_condition_search),
        ("Low-level TR 호출", test_low_level_tr_call),
    ]

    print("실행할 테스트를 선택하세요:")
    for i, (name, _) in enumerate(tests, 1):
        print(f"  {i}. {name}")
    print("  0. 모두 실행")
    print()

    try:
        choice = input("선택 (0-5): ").strip()
        choice = int(choice)
    except (ValueError, KeyboardInterrupt):
        print("\n테스트를 취소했습니다.")
        return

    print()

    if choice == 0:
        # 모두 실행
        for name, test_func in tests:
            print(f"\n{'=' * 80}")
            print(f"  테스트: {name}")
            print(f"{'=' * 80}\n")
            test_func()
    elif 1 <= choice <= len(tests):
        # 선택한 테스트 실행
        name, test_func = tests[choice - 1]
        test_func()
    else:
        print("잘못된 선택입니다.")

    print("\n\n" + "=" * 80)
    print("  테스트 완료")
    print("=" * 80)


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
