"""
전략 로더 - 진화된 최우수 전략을 실제 매매에 적용
"""
import sqlite3
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class EvolvedStrategyParams:
    """진화된 전략 파라미터"""
    # 식별 정보
    strategy_id: int
    generation: int
    fitness_score: float

    # RSI 조건
    buy_rsi_min: float
    buy_rsi_max: float
    sell_rsi_min: float
    sell_rsi_max: float

    # 거래량 조건
    buy_volume_ratio_min: float
    buy_volume_ratio_max: float

    # 호가 조건
    buy_bid_ask_ratio_min: float

    # 매도 조건
    sell_take_profit: float  # 익절 비율 (0.10 = 10%)
    sell_stop_loss: float    # 손절 비율 (-0.05 = -5%)
    sell_trailing_stop: float  # 추적 손절 비율

    # 포지션 크기
    position_size_pct: float  # 계좌의 몇 %를 사용할지
    max_positions: int

    # 시간 필터
    trade_time_start: str
    trade_time_end: str
    avoid_first_30min: bool
    avoid_last_30min: bool

    # 종목 필터
    min_price: float
    max_price: float

    # 백테스팅 성과
    backtest_return_pct: float
    backtest_win_rate: float
    backtest_sharpe_ratio: float

    # 로드 시간
    loaded_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'strategy_id': self.strategy_id,
            'generation': self.generation,
            'fitness_score': self.fitness_score,
            'buy_rsi_min': self.buy_rsi_min,
            'buy_rsi_max': self.buy_rsi_max,
            'sell_rsi_min': self.sell_rsi_min,
            'sell_rsi_max': self.sell_rsi_max,
            'buy_volume_ratio_min': self.buy_volume_ratio_min,
            'buy_volume_ratio_max': self.buy_volume_ratio_max,
            'buy_bid_ask_ratio_min': self.buy_bid_ask_ratio_min,
            'sell_take_profit': self.sell_take_profit,
            'sell_stop_loss': self.sell_stop_loss,
            'sell_trailing_stop': self.sell_trailing_stop,
            'position_size_pct': self.position_size_pct,
            'max_positions': self.max_positions,
            'trade_time_start': self.trade_time_start,
            'trade_time_end': self.trade_time_end,
            'avoid_first_30min': self.avoid_first_30min,
            'avoid_last_30min': self.avoid_last_30min,
            'min_price': self.min_price,
            'max_price': self.max_price,
            'backtest_return_pct': self.backtest_return_pct,
            'backtest_win_rate': self.backtest_win_rate,
            'backtest_sharpe_ratio': self.backtest_sharpe_ratio,
            'loaded_at': self.loaded_at.isoformat()
        }


class StrategyLoader:
    """진화된 전략 로더"""

    def __init__(self, db_path: str = "data/strategy_evolution.db"):
        """
        초기화

        Args:
            db_path: 전략 진화 DB 경로
        """
        self.db_path = db_path
        self.current_strategy: Optional[EvolvedStrategyParams] = None
        self.last_load_time: Optional[datetime] = None
        self.reload_interval = timedelta(hours=1)  # 1시간마다 재로드

        logger.info(f"전략 로더 초기화: {db_path}")

    def load_best_strategy(self, force_reload: bool = False) -> Optional[EvolvedStrategyParams]:
        """
        최우수 전략 로드

        Args:
            force_reload: 강제 재로드 여부

        Returns:
            진화된 전략 파라미터 (없으면 None)
        """
        # 캐시 확인 (1시간 이내면 재사용)
        if not force_reload and self.current_strategy:
            if self.last_load_time and (datetime.now() - self.last_load_time) < self.reload_interval:
                logger.debug(f"캐시된 전략 사용: G{self.current_strategy.generation} (F{self.current_strategy.fitness_score:.2f})")
                return self.current_strategy

        try:
            import os
            if not os.path.exists(self.db_path):
                logger.warning(f"전략 진화 DB가 없습니다: {self.db_path}")
                logger.info("기본 전략을 사용합니다. 전략 진화를 시작하려면: python run_strategy_optimizer.py")
                return None

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 최우수 전략 조회 (fitness_score 기준)
            cursor.execute("""
                SELECT
                    es.id, es.generation, es.genes,
                    fr.fitness_score, fr.total_return_pct, fr.win_rate, fr.sharpe_ratio
                FROM evolved_strategies es
                JOIN fitness_results fr ON es.id = fr.strategy_id
                ORDER BY fr.fitness_score DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            conn.close()

            if not row:
                logger.warning("진화된 전략이 없습니다. 기본 전략을 사용합니다.")
                return None

            # 유전자 파싱
            genes = json.loads(row['genes'])

            # EvolvedStrategyParams 생성
            strategy = EvolvedStrategyParams(
                strategy_id=row['id'],
                generation=row['generation'],
                fitness_score=row['fitness_score'],
                buy_rsi_min=genes.get('buy_rsi_min', 20.0),
                buy_rsi_max=genes.get('buy_rsi_max', 40.0),
                sell_rsi_min=genes.get('sell_rsi_min', 60.0),
                sell_rsi_max=genes.get('sell_rsi_max', 80.0),
                buy_volume_ratio_min=genes.get('buy_volume_ratio_min', 1.2),
                buy_volume_ratio_max=genes.get('buy_volume_ratio_max', 3.0),
                buy_bid_ask_ratio_min=genes.get('buy_bid_ask_ratio_min', 1.1),
                sell_take_profit=genes.get('sell_take_profit', 0.10),
                sell_stop_loss=genes.get('sell_stop_loss', -0.05),
                sell_trailing_stop=genes.get('sell_trailing_stop', 0.03),
                # Fix: 포지션 크기 단위 변환
                # evolution_engine은 10-25 (백분율)로 저장하지만, 여기서는 0.10-0.25 (비율) 필요
                # 값이 1보다 크면 백분율이므로 100으로 나눔
                position_size_pct=genes.get('position_size_pct', 30) / 100 if genes.get('position_size_pct', 30) > 1 else genes.get('position_size_pct', 0.30),
                max_positions=genes.get('max_positions', 5),
                trade_time_start=genes.get('trade_time_start', '08:00'),
                trade_time_end=genes.get('trade_time_end', '20:00'),
                avoid_first_30min=genes.get('avoid_first_30min', False),
                avoid_last_30min=genes.get('avoid_last_30min', False),
                min_price=genes.get('min_price', 10000.0),
                max_price=genes.get('max_price', 200000.0),
                backtest_return_pct=row['total_return_pct'] or 0.0,
                backtest_win_rate=row['win_rate'] or 0.0,
                backtest_sharpe_ratio=row['sharpe_ratio'] or 0.0,
                loaded_at=datetime.now()
            )

            self.current_strategy = strategy
            self.last_load_time = datetime.now()

            logger.info("=" * 80)
            logger.info("✅ 진화된 최우수 전략 로드 완료")
            logger.info("=" * 80)
            logger.info(f"  전략 ID: {strategy.strategy_id}")
            logger.info(f"  세대: {strategy.generation}")
            logger.info(f"  적합도: {strategy.fitness_score:.2f}")
            logger.info(f"  백테스팅 수익률: {strategy.backtest_return_pct:+.2f}%")
            logger.info(f"  백테스팅 승률: {strategy.backtest_win_rate:.2f}%")
            logger.info(f"  샤프비율: {strategy.backtest_sharpe_ratio:.2f}")
            logger.info("")
            logger.info("매수 조건:")
            logger.info(f"  - RSI: {strategy.buy_rsi_min:.1f} ~ {strategy.buy_rsi_max:.1f}")
            logger.info(f"  - 거래량비율: {strategy.buy_volume_ratio_min:.2f}x 이상")
            logger.info(f"  - 호가비율: {strategy.buy_bid_ask_ratio_min:.2f}x 이상")
            logger.info(f"  - 가격범위: {strategy.min_price:,.0f}원 ~ {strategy.max_price:,.0f}원")
            logger.info("")
            logger.info("매도 조건:")
            logger.info(f"  - 익절: +{strategy.sell_take_profit * 100:.1f}%")
            logger.info(f"  - 손절: {strategy.sell_stop_loss * 100:.1f}%")
            logger.info(f"  - 추적손절: -{strategy.sell_trailing_stop * 100:.1f}%")
            logger.info("")
            logger.info("포지션 관리:")
            logger.info(f"  - 포지션 크기: 계좌의 {strategy.position_size_pct * 100:.1f}%")
            logger.info(f"  - 최대 포지션: {strategy.max_positions}개")
            logger.info("=" * 80)

            return strategy

        except Exception as e:
            logger.error(f"전략 로드 실패: {e}", exc_info=True)
            return None

    def get_current_strategy(self) -> Optional[EvolvedStrategyParams]:
        """
        현재 전략 반환 (없으면 자동 로드)

        Returns:
            진화된 전략 파라미터 (없으면 None)
        """
        if not self.current_strategy:
            return self.load_best_strategy()
        return self.current_strategy

    def get_strategy_summary(self) -> Dict[str, Any]:
        """
        전략 요약 정보

        Returns:
            전략 요약 딕셔너리
        """
        if not self.current_strategy:
            return {
                'enabled': False,
                'message': '진화된 전략 없음 - 기본 전략 사용 중'
            }

        strategy = self.current_strategy
        return {
            'enabled': True,
            'strategy_id': strategy.strategy_id,
            'generation': strategy.generation,
            'fitness_score': round(strategy.fitness_score, 2),
            'backtest_return_pct': round(strategy.backtest_return_pct, 2),
            'backtest_win_rate': round(strategy.backtest_win_rate, 2),
            'take_profit': f"+{strategy.sell_take_profit * 100:.1f}%",
            'stop_loss': f"{strategy.sell_stop_loss * 100:.1f}%",
            'position_size': f"{strategy.position_size_pct * 100:.1f}%",
            'max_positions': strategy.max_positions,
            'loaded_at': strategy.loaded_at.strftime('%Y-%m-%d %H:%M:%S')
        }


# 싱글톤 인스턴스
_strategy_loader_instance: Optional[StrategyLoader] = None


def get_strategy_loader() -> StrategyLoader:
    """전역 전략 로더 인스턴스 반환"""
    global _strategy_loader_instance
    if _strategy_loader_instance is None:
        _strategy_loader_instance = StrategyLoader()
    return _strategy_loader_instance


__all__ = ['StrategyLoader', 'EvolvedStrategyParams', 'get_strategy_loader']
