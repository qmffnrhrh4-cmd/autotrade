#!/usr/bin/env python3
"""
전략 최적화 엔진 실행 스크립트

24/7 백테스팅과 가상매매를 통한 자기진화 시스템을 백그라운드에서 실행
"""
import sys
import os
import argparse
import signal
from ai.strategy_optimizer import StrategyOptimizationEngine
from utils.logger_new import get_logger

logger = get_logger()

# 전역 엔진 인스턴스
engine = None


def signal_handler(sig, frame):
    """SIGINT/SIGTERM 핸들러"""
    logger.info("\n\n⚠️  종료 신호 수신됨. 안전하게 종료 중...")
    if engine:
        engine.stop()
    sys.exit(0)


def initialize_apis():
    """Market API, Chart API, OpenAPI 초기화 - 실제 Kiwoom OpenAPI 연동"""
    try:
        from core import KiwoomRESTClient
        from api import MarketAPI
        from api.market import ChartDataAPI
        from core.openapi_client import KiwoomOpenAPIClient

        logger.info("🔗 API 초기화 중...")

        # KiwoomRESTClient 초기화 (싱글톤 - 파라미터 없음)
        client = KiwoomRESTClient()

        # MarketAPI 초기화
        market_api = MarketAPI(client)

        # ChartDataAPI 초기화 (백테스팅용 차트 데이터)
        chart_api = ChartDataAPI(client)

        # OpenAPI 클라이언트 초기화 (백테스팅용 분봉 데이터 - REST API보다 안정적)
        openapi_client = None
        try:
            logger.info("🔗 OpenAPI 클라이언트 초기화 중...")
            openapi_client = KiwoomOpenAPIClient(auto_connect=True)
            if openapi_client.is_connected:
                logger.info("✅ OpenAPI 클라이언트 연결 완료 - 백테스팅에 OpenAPI 사용")
            else:
                logger.warning("⚠️ OpenAPI 클라이언트 연결 실패 - REST API로 폴백")
                openapi_client = None
        except Exception as e:
            logger.warning(f"⚠️ OpenAPI 클라이언트 초기화 실패: {e}")
            logger.warning("   → REST API로 폴백")
            openapi_client = None

        logger.info("✅ API 초기화 완료 - 실제 데이터 사용")
        logger.info("  - MarketAPI: 시장 데이터 조회")
        logger.info("  - ChartDataAPI: 차트 데이터 조회 (REST API)")
        logger.info(f"  - OpenAPI Client: {'연결됨 (분봉 데이터 우선 사용)' if openapi_client and openapi_client.is_connected else '미연결 (REST API 사용)'}")

        return {
            'market_api': market_api,
            'chart_api': chart_api,
            'openapi_client': openapi_client
        }

    except Exception as e:
        logger.warning(f"⚠️ API 초기화 실패: {e}")
        logger.warning("💡 시뮬레이션 모드로 전환 - 가상 데이터 사용")
        return None


def initialize_virtual_trading():
    """Virtual Trading Manager 초기화"""
    try:
        from virtual_trading.manager import VirtualTradingManager
        vt_manager = VirtualTradingManager(db_path="data/virtual_trading.db")
        logger.info("✅ Virtual Trading Manager 초기화 완료")
        return vt_manager
    except Exception as e:
        logger.warning(f"⚠️ Virtual Trading Manager 초기화 실패: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='전략 최적화 엔진')
    parser.add_argument('--population-size', type=int, default=20, help='세대당 전략 개수')
    parser.add_argument('--mutation-rate', type=float, default=0.15, help='변이 확률')
    parser.add_argument('--crossover-rate', type=float, default=0.7, help='교차 확률')
    parser.add_argument('--interval', type=int, default=600, help='세대 간 대기 시간 (초)')
    parser.add_argument('--max-generations', type=int, default=None, help='최대 세대 수 (None=무한)')
    parser.add_argument('--stocks', type=str, default='005930,000660,035720', help='테스트 종목 (쉼표 구분)')
    parser.add_argument('--simulation', action='store_true', help='시뮬레이션 모드 강제 (Market API 없이 실행)')
    parser.add_argument('--auto-deploy', action='store_true', help='최우수 전략 자동 배포 (가상매매 연동)')
    parser.add_argument('--continuous', action='store_true', help='연속 실행 모드 (무한 반복)')

    args = parser.parse_args()

    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 100)
    logger.info("🧬 전략 최적화 엔진 시작")
    logger.info("=" * 100)
    logger.info(f"설정:")
    logger.info(f"  - 세대당 전략 수: {args.population_size}")
    logger.info(f"  - 변이 확률: {args.mutation_rate * 100}%")
    logger.info(f"  - 교차 확률: {args.crossover_rate * 100}%")
    logger.info(f"  - 세대 간 대기: {args.interval}초")
    logger.info(f"  - 최대 세대: {args.max_generations or '무한'}")
    logger.info(f"  - 테스트 종목: {args.stocks}")
    logger.info(f"  - 자동 배포: {'활성화' if args.auto_deploy else '비활성화'}")
    logger.info(f"  - 연속 실행: {'활성화 (무한 반복)' if args.continuous else '비활성화'}")
    logger.info("=" * 100)

    # 연속 실행 모드면 무한 세대 설정
    if args.continuous and args.max_generations is None:
        args.max_generations = None  # 무한 반복
        logger.info("🔄 연속 실행 모드: 무한 세대 진화")

    # API 초기화 (시뮬레이션 모드가 아닌 경우)
    apis = None if args.simulation else initialize_apis()

    # Virtual Trading Manager 초기화 (자동 배포 모드인 경우)
    vt_manager = initialize_virtual_trading() if args.auto_deploy else None

    # API dict에서 개별 API 추출
    market_api = apis['market_api'] if apis else None
    chart_api = apis['chart_api'] if apis else None
    openapi_client = apis.get('openapi_client') if apis else None

    global engine
    engine = StrategyOptimizationEngine(
        population_size=args.population_size,
        mutation_rate=args.mutation_rate,
        crossover_rate=args.crossover_rate,
        market_api=market_api,
        chart_api=chart_api,
        openapi_client=openapi_client,
        virtual_trading_manager=vt_manager,
        auto_deploy=args.auto_deploy
    )

    stock_codes = args.stocks.split(',')

    # 최적화 실행
    try:
        engine.run_continuous_optimization(
            stock_codes=stock_codes,
            max_generations=args.max_generations,
            interval_seconds=args.interval
        )
    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"최적화 중 오류 발생: {e}", exc_info=True)
    finally:
        logger.info("전략 최적화 엔진 종료")


if __name__ == "__main__":
    main()
