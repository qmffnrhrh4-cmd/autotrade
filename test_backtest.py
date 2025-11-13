#!/usr/bin/env python3
"""
백테스팅 테스트 스크립트

데이터 수집 → 백테스트 실행 → 결과 확인을 한번에 수행
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger_new import get_logger
from core import KiwoomRESTClient
from api.market import ChartDataAPI
from core.openapi_client import KiwoomOpenAPIClient
from ai.strategy_backtester import StrategyBacktester

logger = get_logger()


def print_separator():
    """구분선 출력"""
    print("=" * 100)


def test_data_collection(stock_codes, openapi_client):
    """데이터 수집 테스트"""
    print_separator()
    print("📊 단계 1: 데이터 수집 테스트")
    print_separator()

    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

    logger.info(f"기간: {start_date} ~ {end_date}")
    logger.info("📝 참고: OpenAPI는 장 마감 후에도 과거 데이터 조회 가능")
    print()

    for stock_code in stock_codes:
        logger.info(f"\n종목: {stock_code}")
        logger.info(f"  기간: {start_date} ~ {end_date}")

        try:
            # 1분봉 데이터 수집
            minute_data = openapi_client.get_minute_data(stock_code, interval=1)

            if minute_data and len(minute_data) > 0:
                logger.info(f"  ✅ 1분봉 데이터: {len(minute_data)}개 수신")
                logger.info(f"     샘플: {minute_data[0]}")
            else:
                logger.warning(f"  ⚠️  1분봉 데이터 없음")

        except Exception as e:
            logger.error(f"  ❌ 데이터 수집 실패: {e}")

    print()


def test_backtest_execution(stock_codes, backtester):
    """백테스트 실행 테스트"""
    print_separator()
    print("🧪 단계 2: 백테스트 실행")
    print_separator()

    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

    logger.info(f"기간: {start_date} ~ {end_date}")
    logger.info(f"종목: {', '.join(stock_codes)}")
    logger.info(f"전략 개수: {len(backtester.strategies)}개")

    # 사용 가능한 전략 출력
    for strategy in backtester.strategies:
        logger.info(f"  - {strategy.name}")
    print()

    try:
        logger.info(f"백테스트 실행 중...")

        results = backtester.run_backtest(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            interval='1',
            parallel=True
        )

        return results

    except Exception as e:
        logger.error(f"❌ 백테스트 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def print_backtest_results(results):
    """백테스트 결과 출력"""
    print_separator()
    print("📈 단계 3: 백테스트 결과")
    print_separator()

    if not results:
        logger.error("결과 없음")
        return

    print(f"\n총 {len(results)}개 전략 실행 완료\n")

    # 전략별 결과 출력
    for strategy_name, result in results.items():
        print(f"【 {strategy_name} 】")
        print(f"  총 수익률: {result.total_return_pct:+.2f}%")
        print(f"  최종 자산: {result.final_cash:,.0f}원 (초기: {result.initial_cash:,.0f}원)")
        print(f"  총 거래: {result.total_trades}회 (승: {result.winning_trades}, 패: {result.losing_trades})")
        print(f"  승률: {result.win_rate:.1f}%")
        print(f"  최대 낙폭: {result.max_drawdown_pct:.2f}%")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Sortino Ratio: {result.sortino_ratio:.2f}")

        # 거래 내역
        if result.trades:
            print(f"\n  최근 거래 5건:")
            for i, trade in enumerate(result.trades[:5], 1):
                stock_code = trade.get('stock_code', 'N/A')
                buy_price = trade.get('buy_price', 0)
                sell_price = trade.get('sell_price', 0)
                quantity = trade.get('quantity', 0)
                profit = trade.get('profit', 0)
                profit_pct = trade.get('profit_pct', 0)
                buy_date = trade.get('buy_date', '')
                sell_date = trade.get('sell_date', '')

                # 날짜 포맷팅
                if hasattr(buy_date, 'strftime'):
                    buy_date_str = buy_date.strftime('%m/%d %H:%M')
                else:
                    buy_date_str = str(buy_date)[:10] if buy_date else 'N/A'

                if hasattr(sell_date, 'strftime'):
                    sell_date_str = sell_date.strftime('%m/%d %H:%M')
                else:
                    sell_date_str = str(sell_date)[:10] if sell_date else 'N/A'

                print(f"    {i}. {stock_code} 매수 {buy_price:,.0f}원 → 매도 {sell_price:,.0f}원 x {quantity}주")
                print(f"       ({buy_date_str} ~ {sell_date_str}) 손익: {profit:+,.0f}원 ({profit_pct:+.2f}%)")
        else:
            print(f"\n  거래 내역 없음")

        print()

    # 전략 순위
    sorted_results = sorted(results.items(), key=lambda x: x[1].total_return_pct, reverse=True)
    print("【 전략 순위 】")
    for i, (strategy_name, result) in enumerate(sorted_results, 1):
        print(f"  {i}위. {strategy_name}: {result.total_return_pct:+.2f}%")

    print()


def main():
    """메인 실행 함수"""
    print_separator()
    print("🧪 백테스팅 통합 테스트")
    print_separator()
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator()

    # 테스트 종목
    test_stocks = ['005930', '000660', '035720']  # 삼성전자, SK하이닉스, 카카오

    logger.info(f"테스트 종목: {', '.join(test_stocks)}")
    print()

    try:
        # API 초기화
        logger.info("API 초기화 중...")
        client = KiwoomRESTClient()

        # MarketAPI 초기화
        from api import MarketAPI
        market_api = MarketAPI(client)

        chart_api = ChartDataAPI(client)

        # OpenAPI 클라이언트 초기화
        logger.info("OpenAPI 클라이언트 연결 중...")
        openapi_client = KiwoomOpenAPIClient(auto_connect=True)

        if not openapi_client.is_connected:
            logger.error("❌ OpenAPI 클라이언트 연결 실패")
            logger.error("   → openapi_server_v2.py가 실행 중인지 확인하세요")
            return

        logger.info("✅ API 초기화 완료")
        print()

        # 백테스터 초기화
        backtester = StrategyBacktester(
            market_api=market_api,
            chart_api=chart_api,
            openapi_client=openapi_client
        )

        # 1. 데이터 수집 테스트
        test_data_collection(test_stocks, openapi_client)

        # 2. 백테스트 실행
        results = test_backtest_execution(test_stocks, backtester)

        # 3. 결과 출력
        print_backtest_results(results)

        print_separator()
        print("✅ 테스트 완료")
        print_separator()

    except KeyboardInterrupt:
        logger.info("\n\n⚠️  사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"\n\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
