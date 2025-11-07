"""
키움 Open API 64비트 사용 예제 모음

이 파일은 test_kiwoom_openapi_comprehensive.py를 활용한
다양한 실전 예제를 제공합니다.

예제 목록:
1. 기본 로그인 및 종목 정보 조회
2. 여러 종목 일봉 데이터 수집
3. 분봉 데이터 실시간 수집
4. 계좌 잔고 모니터링
5. 간단한 자동매매 봇 (시뮬레이션)
"""
import sys
from pathlib import Path
import time
from datetime import datetime

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_kiwoom_openapi_comprehensive import (
    KiwoomOpenAPI,
    print_section,
    print_candle_data,
    save_to_csv
)


def example1_basic_login():
    """
    예제 1: 기본 로그인 및 종목 정보 조회

    가장 기본적인 사용 예제입니다.
    """
    print_section("예제 1: 기본 로그인 및 종목 정보 조회")

    # API 초기화 (자동 진단 포함)
    api = KiwoomOpenAPI(auto_diagnose=True)

    try:
        # 연결
        if not api.connect():
            print("❌ 연결 실패")
            return

        # 로그인
        if not api.login(timeout=60):
            print("❌ 로그인 실패")
            return

        # 삼성전자 정보 조회
        print("\n📊 삼성전자(005930) 정보 조회")
        info = api.get_stock_info("005930")

        if info:
            print(f"\n종목명: {info['종목명']}")
            print(f"현재가: {info['현재가']:,}원")
            print(f"전일대비: {info['전일대비']:,}원 ({info['등락률']:.2f}%)")
            print(f"거래량: {info['거래량']:,}주")
            print(f"시가: {info['시가']:,}원")
            print(f"고가: {info['고가']:,}원")
            print(f"저가: {info['저가']:,}원")

        print("\n✅ 예제 1 완료!")

    finally:
        api.disconnect()


def example2_multi_stock_data():
    """
    예제 2: 여러 종목의 일봉 데이터 수집

    여러 종목의 과거 데이터를 수집하고 CSV로 저장합니다.
    """
    print_section("예제 2: 여러 종목 일봉 데이터 수집")

    api = KiwoomOpenAPI(auto_diagnose=True)

    try:
        if not api.connect() or not api.login(timeout=60):
            return

        # 수집할 종목 리스트
        stocks = {
            "005930": "삼성전자",
            "035720": "카카오",
            "000660": "SK하이닉스",
            "005380": "현대차",
            "051910": "LG화학"
        }

        print(f"\n📊 {len(stocks)}개 종목의 일봉 데이터 수집 시작\n")

        collected_data = {}

        for code, name in stocks.items():
            print(f"[{name}] 데이터 수집 중...")

            # 최근 100일 일봉 조회
            data = api.get_daily_candle(code, count=100, adjusted=True)

            if data and len(data) > 0:
                collected_data[code] = data

                # CSV 저장
                filename = f"{name}_{code}_daily.csv"
                save_to_csv(data, filename)

                # 간단한 통계
                prices = [d['close'] for d in data]
                print(f"   ✅ {len(data)}개 수집 완료")
                print(f"   최고가: {max(prices):,}원")
                print(f"   최저가: {min(prices):,}원")
                print(f"   평균가: {sum(prices)//len(prices):,}원\n")
            else:
                print(f"   ❌ 데이터 수집 실패\n")

            # API 제한 준수 (0.2초 대기)
            time.sleep(0.2)

        print(f"\n✅ 총 {len(collected_data)}개 종목 데이터 수집 완료!")

    finally:
        api.disconnect()


def example3_minute_data_collection():
    """
    예제 3: 특정 종목의 분봉 데이터 대량 수집

    연속 조회를 활용하여 많은 양의 분봉 데이터를 수집합니다.
    """
    print_section("예제 3: 분봉 데이터 대량 수집")

    api = KiwoomOpenAPI(auto_diagnose=True)

    try:
        if not api.connect() or not api.login(timeout=60):
            return

        # 삼성전자 1분봉 2000개 조회
        print("\n📊 삼성전자 1분봉 2000개 조회 시작")
        print("   (자동으로 연속 조회 처리)\n")

        start_time = time.time()

        data = api.get_minute_candle(
            stock_code="005930",
            interval=1,
            count=2000
        )

        elapsed = time.time() - start_time

        if data:
            print(f"\n✅ 데이터 수집 완료!")
            print(f"   수집 개수: {len(data):,}개")
            print(f"   소요 시간: {elapsed:.1f}초")

            # 데이터 기간 확인
            if len(data) > 0:
                first_date = data[0]['date']
                last_date = data[-1]['date']
                print(f"   데이터 기간: {last_date} ~ {first_date}")

            # 샘플 출력
            print_candle_data(data, max_rows=20, data_type="분봉")

            # CSV 저장
            save_to_csv(data, "samsung_1min_2000.csv")

    finally:
        api.disconnect()


def example4_balance_monitoring():
    """
    예제 4: 계좌 잔고 모니터링

    보유 종목과 수익률을 확인합니다.
    """
    print_section("예제 4: 계좌 잔고 모니터링")

    api = KiwoomOpenAPI(auto_diagnose=True)

    try:
        if not api.connect() or not api.login(timeout=60):
            return

        # 계좌 리스트 확인
        accounts = api.get_account_list()

        if not accounts:
            print("❌ 계좌가 없습니다.")
            return

        print(f"\n보유 계좌: {', '.join(accounts)}\n")

        # 첫 번째 계좌 잔고 조회
        balance = api.get_balance(accounts[0])

        if balance:
            print("="*100)
            print("💰 계좌 잔고 현황")
            print("="*100)

            # 예수금
            deposit = balance.get('deposit', 0)
            print(f"\n예수금: {deposit:,}원")

            # 보유 종목
            stocks = balance.get('data', [])

            if stocks:
                print(f"\n보유 종목: {len(stocks)}개\n")

                # 테이블 헤더
                print(f"{'종목명':15} {'보유수량':>10} {'매입가':>12} {'현재가':>12} "
                      f"{'평가손익':>12} {'수익률':>10}")
                print("-" * 100)

                total_profit = 0

                for stock in stocks:
                    print(f"{stock['종목명']:15} "
                          f"{stock['보유수량']:>10,}주 "
                          f"{stock['매입가']:>12,}원 "
                          f"{stock['현재가']:>12,}원 "
                          f"{stock['평가손익']:>12,}원 "
                          f"{stock['수익률']:>9.2f}%")

                    total_profit += stock['평가손익']

                print("-" * 100)
                print(f"{'총 평가손익':30} {total_profit:>12,}원")

                # 총 평가금액
                total_value = sum(s['현재가'] * s['보유수량'] for s in stocks)
                total_asset = total_value + deposit

                print(f"\n총 평가금액: {total_value:,}원")
                print(f"총 자산: {total_asset:,}원")

            else:
                print("\n보유 종목이 없습니다.")

            print("\n" + "="*100)

    finally:
        api.disconnect()


def example5_simple_trading_bot():
    """
    예제 5: 간단한 자동매매 봇 시뮬레이션

    실제 주문은 하지 않고, 매매 신호만 출력합니다.
    (실제 주문 기능은 매우 신중하게 구현해야 합니다!)
    """
    print_section("예제 5: 간단한 자동매매 봇 (시뮬레이션)")

    api = KiwoomOpenAPI(auto_diagnose=True)

    try:
        if not api.connect() or not api.login(timeout=60):
            return

        print("\n📊 삼성전자(005930) 자동매매 봇 시뮬레이션")
        print("   전략: 5일 이동평균선 돌파 전략")
        print("   (실제 주문은 하지 않습니다)\n")

        # 최근 10일 일봉 데이터 조회
        data = api.get_daily_candle("005930", count=10, adjusted=True)

        if not data or len(data) < 5:
            print("❌ 데이터 부족")
            return

        # 최근 5일 종가로 이동평균 계산
        recent_5days = data[:5]
        ma5 = sum(d['close'] for d in recent_5days) / 5

        # 현재가 조회
        info = api.get_stock_info("005930")
        current_price = info['현재가']

        print(f"현재가: {current_price:,}원")
        print(f"5일 이동평균: {ma5:,.0f}원")

        # 매매 신호 판단
        if current_price > ma5:
            signal = "매수"
            print(f"\n🔵 {signal} 신호!")
            print(f"   현재가({current_price:,})가 5일 이동평균({ma5:,.0f})보다 높습니다.")
            print(f"   → (시뮬레이션이므로 실제 주문은 하지 않습니다)")
        elif current_price < ma5:
            signal = "매도"
            print(f"\n🔴 {signal} 신호!")
            print(f"   현재가({current_price:,})가 5일 이동평균({ma5:,.0f})보다 낮습니다.")
            print(f"   → (시뮬레이션이므로 실제 주문은 하지 않습니다)")
        else:
            signal = "관망"
            print(f"\n⚪ {signal}")
            print(f"   현재가({current_price:,})와 5일 이동평균({ma5:,.0f})이 같습니다.")

        print("\n⚠️  주의:")
        print("   - 실제 자동매매는 충분한 백테스팅과 리스크 관리가 필요합니다")
        print("   - 이 예제는 단순 시뮬레이션이며, 실전 사용을 권장하지 않습니다")
        print("   - 투자 손실에 대한 책임은 투자자 본인에게 있습니다")

    finally:
        api.disconnect()


def example6_data_analysis():
    """
    예제 6: 수집한 데이터 분석

    과거 데이터를 활용한 간단한 분석 예제
    """
    print_section("예제 6: 데이터 분석")

    api = KiwoomOpenAPI(auto_diagnose=True)

    try:
        if not api.connect() or not api.login(timeout=60):
            return

        print("\n📊 삼성전자 최근 100일 데이터 분석\n")

        # 100일 일봉 조회
        data = api.get_daily_candle("005930", count=100, adjusted=True)

        if not data or len(data) < 20:
            print("❌ 데이터 부족")
            return

        # 기본 통계
        prices = [d['close'] for d in data]
        volumes = [d['volume'] for d in data]

        print("📈 가격 통계:")
        print(f"   최고가: {max(prices):,}원 ({data[prices.index(max(prices))]['date']})")
        print(f"   최저가: {min(prices):,}원 ({data[prices.index(min(prices))]['date']})")
        print(f"   평균가: {sum(prices)//len(prices):,}원")
        print(f"   현재가: {prices[0]:,}원")

        # 변동성
        avg_price = sum(prices) / len(prices)
        variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5
        volatility = (std_dev / avg_price) * 100

        print(f"\n📊 변동성:")
        print(f"   표준편차: {std_dev:,.0f}원")
        print(f"   변동성: {volatility:.2f}%")

        # 이동평균선
        ma5 = sum(prices[:5]) / 5
        ma20 = sum(prices[:20]) / 20
        ma60 = sum(prices[:60]) / 60

        print(f"\n📉 이동평균선:")
        print(f"   5일선: {ma5:,.0f}원")
        print(f"   20일선: {ma20:,.0f}원")
        print(f"   60일선: {ma60:,.0f}원")

        # 추세 판단
        if ma5 > ma20 > ma60:
            trend = "강한 상승 추세"
        elif ma5 > ma20:
            trend = "상승 추세"
        elif ma5 < ma20 < ma60:
            trend = "강한 하락 추세"
        elif ma5 < ma20:
            trend = "하락 추세"
        else:
            trend = "횡보"

        print(f"\n📌 추세 분석: {trend}")

        # 거래량 분석
        avg_volume = sum(volumes) / len(volumes)
        recent_volume = volumes[0]

        print(f"\n📊 거래량 분석:")
        print(f"   평균 거래량: {avg_volume:,.0f}주")
        print(f"   최근 거래량: {recent_volume:,}주")

        if recent_volume > avg_volume * 1.5:
            print(f"   → 평균 대비 {(recent_volume/avg_volume):.1f}배 증가 (거래 활발)")
        elif recent_volume < avg_volume * 0.5:
            print(f"   → 평균 대비 {(recent_volume/avg_volume):.1f}배 감소 (거래 저조)")
        else:
            print(f"   → 평균 수준")

    finally:
        api.disconnect()


def main():
    """메인 메뉴"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║                  키움 Open API 64비트 사용 예제 모음                                    ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

예제 목록:

1. 기본 로그인 및 종목 정보 조회
2. 여러 종목 일봉 데이터 수집
3. 분봉 데이터 대량 수집 (2000개)
4. 계좌 잔고 모니터링
5. 간단한 자동매매 봇 시뮬레이션
6. 데이터 분석
0. 종료

""")

    while True:
        try:
            choice = input("실행할 예제 번호를 선택하세요 (0-6): ").strip()

            if choice == "0":
                print("\n프로그램을 종료합니다.")
                break
            elif choice == "1":
                example1_basic_login()
            elif choice == "2":
                example2_multi_stock_data()
            elif choice == "3":
                example3_minute_data_collection()
            elif choice == "4":
                example4_balance_monitoring()
            elif choice == "5":
                example5_simple_trading_bot()
            elif choice == "6":
                example6_data_analysis()
            else:
                print("⚠️  잘못된 선택입니다. 0-6 사이의 숫자를 입력하세요.")

            print("\n" + "="*100 + "\n")

        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
