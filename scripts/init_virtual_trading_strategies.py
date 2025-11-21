#!/usr/bin/env python3
"""
scripts/init_virtual_trading_strategies.py
가상매매 전략 초기화 및 자동 생성

12개 기본 전략을 생성하고, 각 전략을 데이터베이스에 등록합니다.
"""
import sys
from pathlib import Path

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import logging
from virtual_trading import VirtualTradingManager
from virtual_trading.diverse_strategies import create_all_diverse_strategies, get_strategy_descriptions

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_strategies():
    """12개 기본 전략 초기화"""
    logger.info("=" * 80)
    logger.info("가상매매 전략 초기화 시작")
    logger.info("=" * 80)

    # 가상매매 매니저 생성
    manager = VirtualTradingManager(db_path="data/virtual_trading.db")

    # 기존 전략 확인
    existing_strategies = manager.get_strategy_summary()
    logger.info(f"📊 기존 전략 개수: {len(existing_strategies)}개")

    # 12개 다양한 전략 생성
    strategies = create_all_diverse_strategies()
    descriptions = get_strategy_descriptions()

    created_count = 0
    skipped_count = 0

    for strategy in strategies:
        strategy_name = strategy.name
        strategy_description = descriptions.get(strategy_name, strategy.description)

        # 이미 존재하는 전략인지 확인
        exists = any(s.get('name') == strategy_name for s in existing_strategies)

        if exists:
            logger.info(f"⏭️  건너뛰기: {strategy_name} (이미 존재)")
            skipped_count += 1
            continue

        try:
            # 전략 생성 (초기 자본: 1천만원)
            strategy_id = manager.create_strategy(
                name=strategy_name,
                description=strategy_description,
                initial_capital=10_000_000
            )

            logger.info(f"✅ 생성 완료: {strategy_name} (ID: {strategy_id})")
            logger.info(f"   📝 설명: {strategy_description}")
            logger.info(f"   💰 초기 자본: 10,000,000원")
            logger.info(f"   📊 최대 포지션: {strategy.max_positions}개")
            logger.info(f"   💵 포지션 크기: {strategy.position_size_rate*100:.1f}%")
            created_count += 1

        except Exception as e:
            logger.error(f"❌ 생성 실패: {strategy_name} - {e}")

    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 초기화 완료")
    logger.info(f"   ✅ 새로 생성: {created_count}개")
    logger.info(f"   ⏭️  건너뛰기: {skipped_count}개")
    logger.info(f"   📊 총 전략: {len(existing_strategies) + created_count}개")
    logger.info("=" * 80)

    # 전략 목록 출력
    all_strategies = manager.get_strategy_summary()
    logger.info("")
    logger.info("📋 전체 전략 목록:")
    logger.info("-" * 80)

    for i, s in enumerate(all_strategies, 1):
        strategy_id = s.get('strategy_id') or s.get('id')
        name = s.get('name', 'Unknown')
        capital = s.get('current_capital', s.get('initial_capital', 0))
        trades = s.get('trade_count', 0)
        win_rate = s.get('win_rate', 0)

        logger.info(f"{i:2d}. [{strategy_id:3d}] {name:20s} | "
                   f"자본: {capital:>12,.0f}원 | "
                   f"거래: {trades:3d}회 | "
                   f"승률: {win_rate:5.1f}%")

    logger.info("-" * 80)
    logger.info("")
    logger.info("🎯 다음 단계:")
    logger.info("   1. 대시보드 접속: http://localhost:5000")
    logger.info("   2. 실시간 모니터: http://localhost:5000/live-monitor")
    logger.info("   3. 진화 대시보드: http://localhost:5000/evolution")
    logger.info("")
    logger.info("💡 가상매매 시작:")
    logger.info("   python main.py --virtual-trading")
    logger.info("")


if __name__ == '__main__':
    try:
        init_strategies()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"\n\n❌ 오류 발생: {e}", exc_info=True)
        sys.exit(1)
