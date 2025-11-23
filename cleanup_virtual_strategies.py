#!/usr/bin/env python3
"""
가상매매 전략 정리 스크립트
- 오래된 전략 비활성화
- 성과 낮은 전략 제거
- 활성 전략 수를 30-40개로 유지
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from virtual_trading import VirtualTradingManager
from utils.logger_new import get_logger

logger = get_logger()

MAX_ACTIVE_STRATEGIES = 40
MIN_DAYS_TO_KEEP = 7
PERFORMANCE_THRESHOLD = -20.0


def cleanup_strategies():
    """전략 정리 실행"""
    logger.info("=" * 60)
    logger.info("🧹 가상매매 전략 정리 시작")
    logger.info("=" * 60)

    vm = VirtualTradingManager()

    all_strategies = vm.db.get_all_strategies()
    active_strategies = [s for s in all_strategies if s.get('is_active', 1) == 1]

    logger.info(f"📊 현재 상태:")
    logger.info(f"  - 전체 전략: {len(all_strategies)}개")
    logger.info(f"  - 활성 전략: {len(active_strategies)}개")
    logger.info(f"  - 목표: {MAX_ACTIVE_STRATEGIES}개 이하")

    if len(active_strategies) <= MAX_ACTIVE_STRATEGIES:
        logger.info("✅ 정리 불필요 - 전략 수가 적정 범위입니다.")
        return

    cleanup_count = 0

    # 1. 오래되고 성과 나쁜 전략 제거
    logger.info("\n📋 정리 기준:")
    logger.info(f"  1. 생성일: {MIN_DAYS_TO_KEEP}일 이상 경과")
    logger.info(f"  2. 수익률: {PERFORMANCE_THRESHOLD}% 이하")
    logger.info(f"  3. 우선순위: 진화 알고리즘 오래된 세대")

    now = datetime.now()
    cutoff_date = now - timedelta(days=MIN_DAYS_TO_KEEP)

    strategies_to_remove = []

    for strategy in active_strategies:
        strategy_id = strategy['id']
        name = strategy['name']
        created_at = strategy.get('created_at')
        current_capital = strategy.get('current_capital', 0)
        initial_capital = strategy.get('initial_capital', 1)

        # 수익률 계산
        profit_rate = ((current_capital - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0

        # 생성일 파싱
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            days_old = (now - created_date).days
        except:
            days_old = 0

        should_remove = False
        reason = ""

        # 제거 조건
        if days_old >= MIN_DAYS_TO_KEEP and profit_rate <= PERFORMANCE_THRESHOLD:
            should_remove = True
            reason = f"{days_old}일 경과, 수익률 {profit_rate:.1f}%"
        elif '진화-G' in name:
            # 진화 알고리즘 전략 - 세대 번호 추출
            try:
                gen_num = int(name.split('G')[1].split('-')[0])
                # 최근 50세대만 유지
                if gen_num < (max(int(s['name'].split('G')[1].split('-')[0]) for s in active_strategies if '진화-G' in s['name']) - 50):
                    should_remove = True
                    reason = f"오래된 세대 (G{gen_num})"
            except:
                pass

        if should_remove:
            strategies_to_remove.append({
                'id': strategy_id,
                'name': name,
                'reason': reason,
                'profit_rate': profit_rate
            })

    # 정렬: 수익률 낮은 것부터
    strategies_to_remove.sort(key=lambda x: x['profit_rate'])

    # 최대 제거 개수 제한 (현재 - 목표 개수만큼만)
    max_to_remove = len(active_strategies) - MAX_ACTIVE_STRATEGIES
    strategies_to_remove = strategies_to_remove[:max_to_remove]

    logger.info(f"\n🗑️  제거 대상: {len(strategies_to_remove)}개")

    for strategy in strategies_to_remove[:10]:  # 처음 10개만 표시
        logger.info(f"  - {strategy['name']}: {strategy['reason']}")

    if len(strategies_to_remove) > 10:
        logger.info(f"  ... 외 {len(strategies_to_remove) - 10}개")

    # 확인 (자동 실행 모드)
    if len(strategies_to_remove) > 0:
        logger.info("\n⚠️  정리를 실행합니다...")

        for strategy in strategies_to_remove:
            try:
                # 전략 비활성화
                vm.db.execute(
                    "UPDATE strategies SET is_active = 0, updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), strategy['id'])
                )
                cleanup_count += 1
                logger.debug(f"  ✓ {strategy['name']} 비활성화")
            except Exception as e:
                logger.error(f"  ✗ {strategy['name']} 실패: {e}")

        vm.db.conn.commit()

    # 최종 상태
    final_active = [s for s in vm.db.get_all_strategies() if s.get('is_active', 1) == 1]

    logger.info("\n" + "=" * 60)
    logger.info("✅ 정리 완료!")
    logger.info(f"  - 비활성화: {cleanup_count}개")
    logger.info(f"  - 활성 전략: {len(active_strategies)}개 → {len(final_active)}개")
    logger.info("=" * 60)


def cleanup_old_positions():
    """오래된 포지션 정리 (30일 이상 보유)"""
    logger.info("\n🧹 오래된 포지션 정리...")

    vm = VirtualTradingManager()

    # 30일 이상 보유 포지션 조회
    cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()

    old_positions = vm.db.query(
        """
        SELECT * FROM positions
        WHERE status IN ('open', 'holding')
        AND entry_time < ?
        """,
        (cutoff_date,)
    )

    if not old_positions:
        logger.info("  ✅ 정리할 오래된 포지션 없음")
        return

    logger.info(f"  📋 30일 이상 보유 포지션: {len(old_positions)}개")

    closed_count = 0
    for pos in old_positions[:20]:  # 최대 20개만 정리
        try:
            # 포지션 강제 청산
            vm.db.execute(
                """
                UPDATE positions
                SET status = 'closed',
                    exit_time = ?,
                    exit_reason = 'Auto cleanup - 30 days holding'
                WHERE id = ?
                """,
                (datetime.now().isoformat(), pos['id'])
            )
            closed_count += 1
        except Exception as e:
            logger.error(f"  ✗ 포지션 {pos['id']} 청산 실패: {e}")

    vm.db.conn.commit()
    logger.info(f"  ✅ {closed_count}개 포지션 청산 완료")


if __name__ == "__main__":
    try:
        cleanup_strategies()
        cleanup_old_positions()

        logger.info("\n🎉 모든 정리 작업 완료!")

    except Exception as e:
        logger.error(f"❌ 정리 실패: {e}", exc_info=True)
        sys.exit(1)
