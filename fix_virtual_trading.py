#!/usr/bin/env python3
"""
가상매매 전략 수정 스크립트
- 자본금 0인 전략 복구
- 비활성화된 전략 활성화
"""
import logging
from virtual_trading import VirtualTradingManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """가상매매 전략 수정"""
    logger.info("🔧 가상매매 전략 수정 시작...")

    vm = VirtualTradingManager(db_path="data/virtual_trading.db")

    # 모든 전략 조회
    all_strategies = vm.get_all_strategies()
    logger.info(f"📊 총 {len(all_strategies)}개 전략 발견")

    if len(all_strategies) == 0:
        logger.warning("⚠️ 전략이 하나도 없습니다. init_virtual_trading.py를 먼저 실행하세요.")
        return

    fixed_count = 0

    for strategy in all_strategies:
        strategy_id = strategy['id']
        name = strategy['name']
        initial_capital = strategy['initial_capital']
        current_capital = strategy['current_capital']
        is_active = strategy.get('is_active', 1)

        needs_fix = False
        fix_reasons = []

        # 1. 자본금이 0인 경우
        if current_capital == 0 and initial_capital > 0:
            needs_fix = True
            fix_reasons.append(f"자본금 0원 → {initial_capital:,.0f}원으로 복구")

        # 2. 자본금이 0이고 초기자본도 0인 경우 (기본값 설정)
        if current_capital == 0 and initial_capital == 0:
            needs_fix = True
            initial_capital = 10000000
            fix_reasons.append(f"초기자본/현재자본 모두 0 → 1,000만원으로 설정")

        # 3. 비활성화된 경우
        if is_active == 0:
            needs_fix = True
            fix_reasons.append("비활성 → 활성화")

        if needs_fix:
            logger.info(f"\n🔧 수정: {name} (ID: {strategy_id})")
            for reason in fix_reasons:
                logger.info(f"   - {reason}")

            # DB 업데이트
            vm.db.conn.execute("""
                UPDATE virtual_strategies
                SET current_capital = ?,
                    initial_capital = ?,
                    is_active = 1,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (initial_capital, initial_capital, strategy_id))
            vm.db.conn.commit()

            fixed_count += 1

    logger.info(f"\n✅ 수정 완료: {fixed_count}/{len(all_strategies)} 전략 수정됨")

    # 수정 후 전략 목록 재확인
    all_strategies = vm.get_all_strategies()
    logger.info(f"\n📊 현재 전략 상태:")
    logger.info(f"{'ID':<5} {'이름':<30} {'초기자본':>15} {'현재자본':>15} {'활성':>5} {'거래':>5}")
    logger.info("-" * 85)

    for s in all_strategies:
        logger.info(
            f"{s['id']:<5} {s['name'][:30]:<30} "
            f"{s['initial_capital']:>15,.0f} {s['current_capital']:>15,.0f} "
            f"{'✓' if s.get('is_active', 1) == 1 else '✗':>5} "
            f"{s.get('trade_count', 0):>5}"
        )

    logger.info("\n💡 다음 단계:")
    logger.info("   1. 대시보드를 새로고침하세요")
    logger.info("   2. 가상매매 페이지에서 전략이 정상적으로 표시되는지 확인하세요")
    logger.info("   3. start_with_openapi.bat를 실행하면 자동으로 매매가 시작됩니다")

if __name__ == "__main__":
    main()
