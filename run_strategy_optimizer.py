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


def initialize_market_api():
    """Market API 초기화"""
    try:
        # Fix: RealTimeMarketAPI가 없으므로 시뮬레이션 모드로 실행
        # 실제 API가 필요한 경우 main.py의 market_api를 사용해야 함
        logger.info("⚠️ 전략 최적화는 시뮬레이션 모드로 실행됩니다")
        logger.info("💡 실제 데이터가 필요한 경우 main.py에서 연동 필요")
        return None

    except Exception as e:
        logger.warning(f"⚠️ Market API 초기화 실패: {e}")
        logger.warning("⚠️ 시뮬레이션 모드로 실행됩니다")
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
    logger.info("=" * 100)

    # Market API 초기화 (시뮬레이션 모드가 아닌 경우)
    market_api = None if args.simulation else initialize_market_api()

    # Virtual Trading Manager 초기화 (자동 배포 모드인 경우)
    vt_manager = initialize_virtual_trading() if args.auto_deploy else None

    global engine
    engine = StrategyOptimizationEngine(
        population_size=args.population_size,
        mutation_rate=args.mutation_rate,
        crossover_rate=args.crossover_rate,
        market_api=market_api,
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
