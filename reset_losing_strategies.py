#!/usr/bin/env python3
"""
손실 전략 리셋 스크립트
-30% 이상 손실인 가상매매 전략을 자동으로 리셋
"""
import logging
from virtual_trading import VirtualTradingManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """손실 전략 리셋"""
    logger.info("🔍 손실 전략 확인 중...")

    vm = VirtualTradingManager(db_path="data/virtual_trading.db")

    # 모든 전략 조회
    all_strategies = vm.get_all_strategies()

    if not all_strategies:
        logger.info("등록된 전략이 없습니다.")
        return

    logger.info(f"\n📊 현재 등록된 전략 ({len(all_strategies)}개):")

    reset_count = 0
    for strategy in all_strategies:
        name = strategy['name']
        initial = strategy['initial_capital']
        current = strategy['current_capital']
        profit = current - initial
        profit_rate = (profit / initial * 100) if initial > 0 else 0

        status = "✅" if profit >= 0 else "❌"
        logger.info(f"  {status} {name}: {current:,.0f}원 ({profit:+,.0f}원, {profit_rate:+.2f}%)")

        # -20% 이상 손실인 전략 리셋
        if profit_rate < -20:
            logger.warning(f"  ⚠️  {name} 손실률 {profit_rate:.2f}% - 리셋 필요")

            try:
                # 전략 비활성화 또는 자본 리셋
                vm.db.execute(
                    "UPDATE strategies SET current_capital = ?, updated_at = datetime('now') WHERE id = ?",
                    (initial, strategy['id'])
                )

                # 해당 전략의 모든 포지션 청산
                vm.db.execute(
                    "DELETE FROM positions WHERE strategy_id = ? AND status = 'open'",
                    (strategy['id'],)
                )

                vm.db.connection.commit()

                logger.info(f"  ✅ {name} 리셋 완료 (자본: {initial:,.0f}원)")
                reset_count += 1

            except Exception as e:
                logger.error(f"  ❌ {name} 리셋 실패: {e}")

    if reset_count > 0:
        logger.info(f"\n🎉 완료: {reset_count}개 전략 리셋됨")
    else:
        logger.info(f"\n✅ 리셋이 필요한 전략이 없습니다.")

    # 업데이트 후 전략 목록 확인
    logger.info(f"\n📊 업데이트 후 전략 상태:")
    all_strategies = vm.get_all_strategies()
    for s in all_strategies:
        profit = s['current_capital'] - s['initial_capital']
        profit_rate = (profit / s['initial_capital'] * 100) if s['initial_capital'] > 0 else 0
        logger.info(f"  - {s['name']}: {s['current_capital']:,.0f}원 ({profit:+,.0f}원, {profit_rate:+.2f}%)")

if __name__ == "__main__":
    main()
