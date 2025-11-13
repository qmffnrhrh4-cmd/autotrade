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
from utils.trading_date import is_any_trading_hours

logger = get_logger()


def print_separator():
    """구분선 출력"""
    print("=" * 100)


def test_data_collection(stock_codes, openapi_client):
    """데이터 수집 테스트"""
    print_separator()
    print("📊 단계 1: 데이터 수집 테스트")
    print_separator()

    # 장 시간 체크
    if not is_any_trading_hours():
        logger.warning("⚠️ 현재 장이 열려있지 않아 실시간 데이터 수집 테스트를 스킵합니다")
        logger.info("   (정규장: 09:00-15:30, NXT: 08:00-09:00, 15:30-20:00)")
        logger.info("   백테스트는 과거 데이터를 사용하므로 계속 진행됩니다")
        print()
        return

    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

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

    # 테스트 전략 정의
    test_strategy = {
        'name': 'RSI 모멘텀 전략',
        'buy_conditions': {
            'rsi_min': 30,
            'rsi_max': 40,
            'volume_ratio_min': 1.5,
            'orderbook_ratio_min': 1.2
        },
        'sell_conditions': {
            'take_profit_percent': 10.0,
            'stop_loss_percent': 5.0,
            'trailing_stop_percent': 3.0
        },
        'position_size_percent': 20.0,
        'trading_hours': {'start': '09:30', 'end': '15:00'},
        'price_range': {'min': 5000, 'max': 100000}
    }

    logger.info(f"전략: {test_strategy['name']}")
    logger.info(f"  - RSI 범위: {test_strategy['buy_conditions']['rsi_min']} ~ {test_strategy['buy_conditions']['rsi_max']}")
    logger.info(f"  - 익절: +{test_strategy['sell_conditions']['take_profit_percent']}%")
    logger.info(f"  - 손절: -{test_strategy['sell_conditions']['stop_loss_percent']}%")
    logger.info(f"  - 포지션 크기: {test_strategy['position_size_percent']}%")
    print()

    try:
        logger.info(f"백테스트 실행 중... (종목: {', '.join(stock_codes)})")

        results = backtester.backtest_strategy(
            strategy=test_strategy,
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10_000_000
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

    # 전체 통계
    print(f"\n【 전체 성과 】")
    print(f"  총 수익률: {results.get('total_return', 0):.2f}%")
    print(f"  Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
    print(f"  최대 낙폭: {results.get('max_drawdown', 0):.2f}%")
    print(f"  총 거래 횟수: {results.get('total_trades', 0)}회")
    print(f"  승률: {results.get('win_rate', 0):.1f}%")
    print(f"  손익비: {results.get('profit_loss_ratio', 0):.2f}")

    # 거래 상세
    trades = results.get('trades', [])
    if trades:
        print(f"\n【 거래 내역 】 (총 {len(trades)}건)")
        for i, trade in enumerate(trades[:10], 1):  # 최근 10건만 출력
            profit_str = f"{trade.get('profit_percent', 0):+.2f}%"
            print(f"  {i}. {trade.get('stock_code')} - {trade.get('side')} "
                  f"@ {trade.get('price'):,}원 "
                  f"(수량: {trade.get('quantity')}주) "
                  f"→ {profit_str}")

        if len(trades) > 10:
            print(f"  ... 외 {len(trades) - 10}건")
    else:
        print(f"\n【 거래 내역 】")
        print("  ⚠️  매매 신호 없음 (전략 조건 미충족)")

    # 종목별 성과
    stock_results = results.get('stock_results', {})
    if stock_results:
        print(f"\n【 종목별 성과 】")
        for stock_code, stock_data in stock_results.items():
            print(f"  {stock_code}:")
            print(f"    수익률: {stock_data.get('return', 0):.2f}%")
            print(f"    거래: {stock_data.get('trades', 0)}회")
            print(f"    승률: {stock_data.get('win_rate', 0):.1f}%")

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
