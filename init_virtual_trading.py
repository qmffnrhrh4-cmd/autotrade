#!/usr/bin/env python3
"""
가상매매 DB 초기화 및 전략 생성 스크립트
"""
import logging
from virtual_trading import VirtualTradingManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """가상매매 초기화"""
    logger.info("🚀 가상매매 초기화 시작...")

    # VirtualTradingManager 생성 (DB 자동 생성됨)
    vm = VirtualTradingManager(db_path="data/virtual_trading.db")
    logger.info("✅ DB 초기화 완료")

    # 5가지 전략 생성
    strategies = [
        {
            'name': 'AI-보수형',
            'description': '안정적인 수익을 추구하는 보수적 전략',
            'initial_capital': 10000000
        },
        {
            'name': 'AI-균형형',
            'description': '수익과 안정성의 균형을 추구하는 전략',
            'initial_capital': 10000000
        },
        {
            'name': 'AI-공격형',
            'description': '높은 수익을 목표로 하는 공격적 전략',
            'initial_capital': 10000000
        },
        {
            'name': 'AI-가치투자형',
            'description': '저평가 종목 중심의 가치투자 전략',
            'initial_capital': 10000000
        },
        {
            'name': 'AI-모멘텀형',
            'description': '추세를 따르는 모멘텀 전략',
            'initial_capital': 10000000
        }
    ]

    created_count = 0
    for strategy in strategies:
        try:
            strategy_id = vm.create_strategy(
                name=strategy['name'],
                description=strategy['description'],
                initial_capital=strategy['initial_capital']
            )
            logger.info(f"✅ {strategy['name']} 생성 완료 (ID: {strategy_id})")
            created_count += 1
        except Exception as e:
            logger.error(f"❌ {strategy['name']} 생성 실패: {e}")

    logger.info(f"\n🎉 초기화 완료: {created_count}/{len(strategies)} 전략 생성됨")

    # 전략 목록 확인
    all_strategies = vm.get_all_strategies()
    logger.info(f"\n📊 현재 등록된 전략 ({len(all_strategies)}개):")
    for s in all_strategies:
        logger.info(f"  - {s['name']} (초기자본: {s['initial_capital']:,.0f}원, 현재자본: {s['current_capital']:,.0f}원)")

if __name__ == "__main__":
    main()
