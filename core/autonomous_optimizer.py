"""
Autonomous Optimizer - 자율 최적화 엔진
자동 튜닝, 포트폴리오 리밸런싱, 성능 최적화
"""
import time
import threading
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import statistics

from utils.logger_new import get_logger

logger = get_logger()


class OptimizationMode(Enum):
    """최적화 모드"""
    CONSERVATIVE = "conservative"  # 보수적
    BALANCED = "balanced"          # 균형
    AGGRESSIVE = "aggressive"      # 공격적


class MarketCondition(Enum):
    """시장 상황"""
    BULL = "bull"        # 상승장
    BEAR = "bear"        # 하락장
    SIDEWAYS = "sideways" # 횡보장
    VOLATILE = "volatile" # 변동성 높음


@dataclass
class OptimizationTarget:
    """최적화 대상"""
    name: str
    current_value: float
    min_value: float
    max_value: float
    step: float
    getter: Callable[[], float]
    setter: Callable[[float], None]


@dataclass
class PerformanceMetrics:
    """성능 지표"""
    win_rate: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    total_trades: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class AutonomousOptimizer:
    """자율 최적화 엔진

    특징:
    - 시장 상황 자동 감지
    - 파라미터 자동 튜닝
    - 포트폴리오 자동 리밸런싱
    - 전략 성능 모니터링
    - 자동 위험 조정
    """

    def __init__(self):
        self._mode = OptimizationMode.BALANCED
        self._market_condition = MarketCondition.SIDEWAYS
        self._lock = threading.RLock()

        # 최적화 대상 파라미터
        self._targets: Dict[str, OptimizationTarget] = {}

        # 성능 이력
        self._performance_history: deque = deque(maxlen=100)
        self._daily_returns: deque = deque(maxlen=30)

        # 리밸런싱 설정
        self._target_allocations: Dict[str, float] = {}
        self._rebalance_threshold = 0.10  # 10% 이탈 시 리밸런싱
        self._last_rebalance: Optional[datetime] = None
        self._min_rebalance_interval = timedelta(hours=1)

        # 튜닝 설정
        self._tuning_enabled = True
        self._tuning_interval = timedelta(hours=4)
        self._last_tuning: Optional[datetime] = None

        # 콜백
        self._on_rebalance_callbacks: List[Callable] = []
        self._on_tune_callbacks: List[Callable] = []

        # 스레드
        self._running = False
        self._stop_event = threading.Event()
        self._optimizer_thread: Optional[threading.Thread] = None

        # 통계
        self._stats = {
            'rebalances': 0,
            'tunings': 0,
            'market_condition_changes': 0,
            'mode_changes': 0
        }

        logger.info("AutonomousOptimizer 초기화")

    # === 시장 상황 감지 ===

    def detect_market_condition(self, market_data: Dict) -> MarketCondition:
        """시장 상황 감지

        Args:
            market_data: {
                'kospi_change': float,
                'kosdaq_change': float,
                'volatility': float,
                'advance_decline_ratio': float
            }
        """
        kospi_change = market_data.get('kospi_change', 0)
        volatility = market_data.get('volatility', 0.02)
        adv_dec_ratio = market_data.get('advance_decline_ratio', 1.0)

        old_condition = self._market_condition

        # 변동성 기준
        if volatility > 0.03:
            self._market_condition = MarketCondition.VOLATILE
        # 추세 기준
        elif kospi_change > 1.0 and adv_dec_ratio > 1.2:
            self._market_condition = MarketCondition.BULL
        elif kospi_change < -1.0 and adv_dec_ratio < 0.8:
            self._market_condition = MarketCondition.BEAR
        else:
            self._market_condition = MarketCondition.SIDEWAYS

        if old_condition != self._market_condition:
            self._stats['market_condition_changes'] += 1
            logger.info(f"시장 상황 변경: {old_condition.value} → {self._market_condition.value}")
            self._adjust_mode_for_market()

        return self._market_condition

    def _adjust_mode_for_market(self):
        """시장 상황에 따른 모드 자동 조정"""
        old_mode = self._mode

        if self._market_condition == MarketCondition.BULL:
            self._mode = OptimizationMode.AGGRESSIVE
        elif self._market_condition == MarketCondition.BEAR:
            self._mode = OptimizationMode.CONSERVATIVE
        elif self._market_condition == MarketCondition.VOLATILE:
            self._mode = OptimizationMode.CONSERVATIVE
        else:
            self._mode = OptimizationMode.BALANCED

        if old_mode != self._mode:
            self._stats['mode_changes'] += 1
            logger.info(f"최적화 모드 변경: {old_mode.value} → {self._mode.value}")

    # === 포트폴리오 리밸런싱 ===

    def set_target_allocation(self, allocations: Dict[str, float]):
        """목표 자산 배분 설정

        Args:
            allocations: {'cash': 0.2, 'stocks': 0.8} (합계 1.0)
        """
        total = sum(allocations.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"배분 합계가 1.0이 아님: {total}")

        self._target_allocations = allocations.copy()
        logger.info(f"목표 배분 설정: {allocations}")

    def check_rebalance_needed(self, current_allocation: Dict[str, float]) -> Tuple[bool, Dict[str, float]]:
        """리밸런싱 필요 여부 확인

        Returns:
            (필요 여부, 조정량 딕셔너리)
        """
        if not self._target_allocations:
            return False, {}

        adjustments = {}
        needs_rebalance = False

        for asset, target in self._target_allocations.items():
            current = current_allocation.get(asset, 0)
            diff = current - target

            if abs(diff) > self._rebalance_threshold:
                needs_rebalance = True

            adjustments[asset] = -diff  # 양수면 매수, 음수면 매도

        return needs_rebalance, adjustments

    def execute_rebalance(
        self,
        current_portfolio: Dict,
        buy_func: Callable,
        sell_func: Callable
    ) -> Dict[str, Any]:
        """리밸런싱 실행

        Args:
            current_portfolio: {'cash': 금액, 'positions': [포지션 목록]}
            buy_func: 매수 함수
            sell_func: 매도 함수

        Returns:
            리밸런싱 결과
        """
        # 최소 간격 체크
        if self._last_rebalance:
            if datetime.now() - self._last_rebalance < self._min_rebalance_interval:
                return {'success': False, 'reason': '최소 간격 미충족'}

        cash = current_portfolio.get('cash', 0)
        positions = current_portfolio.get('positions', [])

        total_value = cash + sum(p.get('value', 0) for p in positions)

        if total_value <= 0:
            return {'success': False, 'reason': '포트폴리오 가치 0'}

        # 현재 배분 계산
        current_allocation = {
            'cash': cash / total_value,
            'stocks': (total_value - cash) / total_value
        }

        needs_rebalance, adjustments = self.check_rebalance_needed(current_allocation)

        if not needs_rebalance:
            return {'success': True, 'reason': '리밸런싱 불필요'}

        result = {
            'success': True,
            'before': current_allocation.copy(),
            'adjustments': adjustments,
            'actions': []
        }

        # 모드에 따른 조정 비율
        adjust_factor = {
            OptimizationMode.CONSERVATIVE: 0.5,
            OptimizationMode.BALANCED: 0.75,
            OptimizationMode.AGGRESSIVE: 1.0
        }.get(self._mode, 0.75)

        try:
            for asset, adjustment in adjustments.items():
                if asset == 'stocks' and adjustment > 0:
                    # 주식 비중 증가 → 매수
                    amount = int(total_value * adjustment * adjust_factor)
                    if amount > 10000:  # 최소 1만원
                        result['actions'].append({
                            'type': 'buy',
                            'amount': amount
                        })
                        # buy_func(amount)  # 실제 매수는 호출자가 처리

                elif asset == 'stocks' and adjustment < 0:
                    # 주식 비중 감소 → 매도
                    amount = int(total_value * abs(adjustment) * adjust_factor)
                    if amount > 10000:
                        result['actions'].append({
                            'type': 'sell',
                            'amount': amount
                        })

            self._last_rebalance = datetime.now()
            self._stats['rebalances'] += 1

            # 콜백 호출
            for callback in self._on_rebalance_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"리밸런싱 콜백 오류: {e}")

        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            logger.error(f"리밸런싱 실행 오류: {e}")

        return result

    # === 파라미터 자동 튜닝 ===

    def register_tuning_target(self, target: OptimizationTarget):
        """튜닝 대상 등록"""
        self._targets[target.name] = target
        logger.info(f"튜닝 대상 등록: {target.name} (범위: {target.min_value}~{target.max_value})")

    def record_performance(self, metrics: PerformanceMetrics):
        """성능 기록"""
        self._performance_history.append(metrics)

    def auto_tune(self) -> Dict[str, Any]:
        """자동 튜닝 실행"""
        if not self._tuning_enabled:
            return {'success': False, 'reason': '튜닝 비활성화'}

        if self._last_tuning:
            if datetime.now() - self._last_tuning < self._tuning_interval:
                return {'success': False, 'reason': '튜닝 간격 미충족'}

        if len(self._performance_history) < 10:
            return {'success': False, 'reason': '데이터 부족'}

        result = {
            'success': True,
            'adjustments': [],
            'timestamp': datetime.now().isoformat()
        }

        try:
            # 최근 성능 분석
            recent = list(self._performance_history)[-20:]
            avg_win_rate = statistics.mean(m.win_rate for m in recent)
            avg_profit_factor = statistics.mean(m.profit_factor for m in recent if m.profit_factor > 0)

            # 성능에 따른 조정 방향 결정
            if avg_win_rate < 0.4 or avg_profit_factor < 1.0:
                # 성능 저조 → 보수적으로 조정
                direction = -1
                reason = "성능 저조로 보수적 조정"
            elif avg_win_rate > 0.6 and avg_profit_factor > 1.5:
                # 성능 우수 → 공격적으로 조정 가능
                direction = 1
                reason = "성능 우수로 공격적 조정 가능"
            else:
                direction = 0
                reason = "현재 파라미터 유지"

            if direction != 0:
                for name, target in self._targets.items():
                    current = target.getter()
                    new_value = current + (target.step * direction)

                    # 범위 제한
                    new_value = max(target.min_value, min(target.max_value, new_value))

                    if new_value != current:
                        target.setter(new_value)
                        result['adjustments'].append({
                            'name': name,
                            'old_value': current,
                            'new_value': new_value,
                            'direction': 'up' if direction > 0 else 'down'
                        })

            result['reason'] = reason
            self._last_tuning = datetime.now()
            self._stats['tunings'] += 1

            # 콜백 호출
            for callback in self._on_tune_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"튜닝 콜백 오류: {e}")

            logger.info(f"자동 튜닝 완료: {reason}, 조정 {len(result['adjustments'])}개")

        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            logger.error(f"자동 튜닝 오류: {e}")

        return result

    # === 위험 자동 조정 ===

    def adjust_risk_for_drawdown(
        self,
        current_drawdown: float,
        risk_manager
    ) -> bool:
        """드로우다운에 따른 위험 자동 조정

        Args:
            current_drawdown: 현재 드로우다운 (0.0 ~ 1.0)
            risk_manager: DynamicRiskManager 인스턴스

        Returns:
            조정 여부
        """
        if not risk_manager:
            return False

        try:
            from strategy.dynamic_risk_manager import RiskMode

            if current_drawdown > 0.15:
                # 15% 이상 손실 → 매우 보수적
                risk_manager.set_mode(RiskMode.VERY_CONSERVATIVE)
                logger.warning(f"드로우다운 {current_drawdown*100:.1f}% → VERY_CONSERVATIVE 모드")
                return True

            elif current_drawdown > 0.10:
                # 10% 이상 손실 → 보수적
                risk_manager.set_mode(RiskMode.CONSERVATIVE)
                logger.warning(f"드로우다운 {current_drawdown*100:.1f}% → CONSERVATIVE 모드")
                return True

            elif current_drawdown < 0.03 and self._market_condition == MarketCondition.BULL:
                # 손실 적고 상승장 → 공격적 가능
                risk_manager.set_mode(RiskMode.AGGRESSIVE)
                return True

        except Exception as e:
            logger.error(f"위험 조정 오류: {e}")

        return False

    # === 스레드 관리 ===

    def start(self):
        """최적화 엔진 시작"""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        self._optimizer_thread = threading.Thread(
            target=self._optimizer_loop,
            name="AutonomousOptimizer",
            daemon=True
        )
        self._optimizer_thread.start()

        logger.info("AutonomousOptimizer 시작")

    def stop(self):
        """최적화 엔진 중지"""
        self._running = False
        self._stop_event.set()

        if self._optimizer_thread:
            self._optimizer_thread.join(timeout=5)

        logger.info("AutonomousOptimizer 중지")

    def _optimizer_loop(self):
        """최적화 루프"""
        while self._running:
            try:
                # 주기적 자동 튜닝
                if self._tuning_enabled:
                    self.auto_tune()

                self._stop_event.wait(timeout=300)  # 5분마다

            except Exception as e:
                logger.error(f"최적화 루프 오류: {e}")
                time.sleep(60)

    # === 콜백 등록 ===

    def on_rebalance(self, callback: Callable):
        """리밸런싱 콜백 등록"""
        self._on_rebalance_callbacks.append(callback)

    def on_tune(self, callback: Callable):
        """튜닝 콜백 등록"""
        self._on_tune_callbacks.append(callback)

    # === 상태 조회 ===

    def get_status(self) -> Dict:
        """상태 반환"""
        return {
            'mode': self._mode.value,
            'market_condition': self._market_condition.value,
            'tuning_enabled': self._tuning_enabled,
            'last_rebalance': self._last_rebalance.isoformat() if self._last_rebalance else None,
            'last_tuning': self._last_tuning.isoformat() if self._last_tuning else None,
            'target_allocations': self._target_allocations,
            'tuning_targets': list(self._targets.keys()),
            'performance_history_size': len(self._performance_history),
            'stats': self._stats.copy(),
            'running': self._running
        }


# 싱글톤 인스턴스
_optimizer: Optional[AutonomousOptimizer] = None
_instance_lock = threading.Lock()


def get_autonomous_optimizer() -> AutonomousOptimizer:
    """AutonomousOptimizer 싱글톤 인스턴스 반환"""
    global _optimizer

    with _instance_lock:
        if _optimizer is None:
            _optimizer = AutonomousOptimizer()

    return _optimizer
