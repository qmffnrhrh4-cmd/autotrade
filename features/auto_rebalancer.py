"""
features/auto_rebalancer.py
통합 포트폴리오 자동 리밸런싱 시스템

Features:
- 목표 포트폴리오 비율 유지
- 다양한 리밸런싱 전략 (Equal Weight, Risk Parity, AI Driven, Momentum, Value)
- 시간/임계값 기반 리밸런싱
- 리스크 기반 자동 조정
- AI 신호 기반 동적 리밸런싱
- 세금 효율적 리밸런싱
- 스케줄 기반 자동 실행
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

from utils.logger_new import get_logger

logger = get_logger()


class RebalanceStrategy(Enum):
    """리밸런싱 전략"""
    EQUAL_WEIGHT = "equal_weight"  # 균등 비중
    RISK_PARITY = "risk_parity"  # 리스크 패리티
    AI_DRIVEN = "ai_driven"  # AI 신호 기반
    MOMENTUM = "momentum"  # 모멘텀 기반
    VALUE = "value"  # 가치 기반
    CUSTOM = "custom"  # 사용자 정의


@dataclass
class RebalanceAction:
    """리밸런싱 액션"""
    stock_code: str
    stock_name: str
    action: str  # 'buy', 'sell', 'hold'
    current_weight: float  # 현재 비중 (%)
    target_weight: float  # 목표 비중 (%)
    current_value: int  # 현재 평가금액
    target_value: int  # 목표 평가금액
    quantity_change: int  # 수량 변화 (+ 매수, - 매도)
    amount: int  # 거래금액
    reason: str  # 리밸런싱 이유


class AutoRebalancer:
    """
    포트폴리오 자동 리밸런싱 시스템 (v5.10)

    Features:
    - 다양한 리밸런싱 전략
    - 리스크 관리 통합
    - 세금 효율적 실행
    - 자동 스케줄링
    - 백테스팅 지원
    """

    def __init__(
        self,
        strategy: RebalanceStrategy = RebalanceStrategy.RISK_PARITY,
        rebalance_threshold: float = 5.0,  # 5% 이탈 시 리밸런싱
        min_transaction_amount: int = 100000,  # 최소 거래금액 10만원
        max_positions: int = 20  # 최대 보유 종목 수
    ):
        """
        초기화

        Args:
            strategy: 리밸런싱 전략
            rebalance_threshold: 리밸런싱 임계값 (%)
            min_transaction_amount: 최소 거래금액
            max_positions: 최대 보유 종목 수
        """
        self.strategy = strategy
        self.rebalance_threshold = rebalance_threshold
        self.min_transaction_amount = min_transaction_amount
        self.max_positions = max_positions

        # 마지막 리밸런싱 시간
        self.last_rebalance = None

        # 리밸런싱 히스토리
        self.rebalance_history: List[Dict[str, Any]] = []

        logger.info(f"Auto Rebalancer initialized - Strategy: {strategy.value}")

    def analyze_portfolio(
        self,
        holdings: List[Dict[str, Any]],
        total_portfolio_value: int,
        target_weights: Optional[Dict[str, float]] = None
    ) -> Tuple[bool, List[RebalanceAction]]:
        """
        포트폴리오 분석 및 리밸런싱 필요성 판단

        Args:
            holdings: 보유 종목 리스트
            total_portfolio_value: 총 포트폴리오 가치
            target_weights: 목표 비중 딕셔너리 (stock_code: weight%)

        Returns:
            (리밸런싱 필요 여부, 액션 리스트)
        """
        if not holdings:
            logger.info("No holdings - rebalancing not needed")
            return False, []

        # 목표 비중 계산
        if target_weights is None:
            target_weights = self._calculate_target_weights(holdings, total_portfolio_value)

        # 현재 비중 계산
        current_weights = {}
        for holding in holdings:
            stock_code = holding.get('stock_code', '')
            value = holding.get('evaluation_amount', 0)
            if total_portfolio_value > 0:
                current_weights[stock_code] = (value / total_portfolio_value) * 100

        # 리밸런싱 액션 생성
        actions = []
        needs_rebalancing = False

        for holding in holdings:
            stock_code = holding.get('stock_code', '')
            stock_name = holding.get('stock_name', '')
            current_value = holding.get('evaluation_amount', 0)
            current_price = holding.get('current_price', 0)

            current_weight = current_weights.get(stock_code, 0)
            target_weight = target_weights.get(stock_code, 0)

            # 비중 차이 계산
            weight_diff = abs(current_weight - target_weight)

            # 임계값 초과 시 리밸런싱 필요
            if weight_diff > self.rebalance_threshold:
                needs_rebalancing = True

                target_value = int(total_portfolio_value * (target_weight / 100))
                value_diff = target_value - current_value

                # 매수/매도 판단
                if value_diff > self.min_transaction_amount:
                    action = 'buy'
                    quantity_change = int(value_diff / current_price) if current_price > 0 else 0
                    reason = f"목표 비중 {target_weight:.1f}% 미달 (현재 {current_weight:.1f}%)"
                elif value_diff < -self.min_transaction_amount:
                    action = 'sell'
                    quantity_change = int(abs(value_diff) / current_price) if current_price > 0 else 0
                    reason = f"목표 비중 {target_weight:.1f}% 초과 (현재 {current_weight:.1f}%)"
                else:
                    action = 'hold'
                    quantity_change = 0
                    reason = f"거래금액 미달 (차이: {abs(value_diff):,}원)"

                actions.append(RebalanceAction(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    action=action,
                    current_weight=round(current_weight, 2),
                    target_weight=round(target_weight, 2),
                    current_value=current_value,
                    target_value=target_value,
                    quantity_change=quantity_change,
                    amount=abs(value_diff),
                    reason=reason
                ))

        logger.info(f"Portfolio analysis complete - Rebalancing needed: {needs_rebalancing}")
        logger.info(f"Generated {len(actions)} rebalance actions")

        return needs_rebalancing, actions

    def execute_rebalance(
        self,
        actions: List[RebalanceAction],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        리밸런싱 실행

        Args:
            actions: 리밸런싱 액션 리스트
            dry_run: 실제 실행 여부 (True=시뮬레이션)

        Returns:
            실행 결과
        """
        if not actions:
            return {
                'success': True,
                'message': 'No actions to execute',
                'executed_actions': []
            }

        executed = []
        failed = []

        for action in actions:
            if action.action == 'hold':
                continue

            try:
                if dry_run:
                    # 시뮬레이션 모드
                    logger.info(f"[DRY RUN] {action.action.upper()} {action.stock_name}: {action.quantity_change}주 ({action.amount:,}원)")
                    executed.append(action)
                else:
                    # 실제 주문 실행 (여기에 실제 주문 로직 추가)
                    logger.info(f"Executing {action.action.upper()} order for {action.stock_name}")
                    # TODO: 실제 주문 API 호출
                    executed.append(action)

            except Exception as e:
                logger.error(f"Failed to execute action for {action.stock_name}: {e}")
                failed.append({
                    'action': action,
                    'error': str(e)
                })

        # 리밸런싱 히스토리 저장
        self._save_rebalance_history({
            'timestamp': datetime.now().isoformat(),
            'strategy': self.strategy.value,
            'dry_run': dry_run,
            'total_actions': len(actions),
            'executed': len(executed),
            'failed': len(failed),
            'actions': [self._action_to_dict(a) for a in executed]
        })

        self.last_rebalance = datetime.now()

        return {
            'success': len(failed) == 0,
            'message': f'Executed {len(executed)} actions, {len(failed)} failed',
            'executed_actions': [self._action_to_dict(a) for a in executed],
            'failed_actions': failed
        }

    def should_rebalance(
        self,
        force: bool = False,
        min_interval_hours: int = 24
    ) -> bool:
        """
        리밸런싱 실행 여부 판단

        Args:
            force: 강제 실행 여부
            min_interval_hours: 최소 간격 (시간)

        Returns:
            실행 여부
        """
        if force:
            return True

        # 마지막 리밸런싱 시간 체크
        if self.last_rebalance:
            elapsed = datetime.now() - self.last_rebalance
            if elapsed < timedelta(hours=min_interval_hours):
                logger.info(f"Rebalancing skipped - last rebalance was {elapsed.total_seconds() / 3600:.1f} hours ago")
                return False

        return True

    def get_rebalance_summary(self, actions: List[RebalanceAction]) -> Dict[str, Any]:
        """
        리밸런싱 요약 정보

        Args:
            actions: 액션 리스트

        Returns:
            요약 정보
        """
        buy_actions = [a for a in actions if a.action == 'buy']
        sell_actions = [a for a in actions if a.action == 'sell']
        hold_actions = [a for a in actions if a.action == 'hold']

        total_buy_amount = sum(a.amount for a in buy_actions)
        total_sell_amount = sum(a.amount for a in sell_actions)

        return {
            'total_actions': len(actions),
            'buy_count': len(buy_actions),
            'sell_count': len(sell_actions),
            'hold_count': len(hold_actions),
            'total_buy_amount': total_buy_amount,
            'total_sell_amount': total_sell_amount,
            'net_cash_flow': total_sell_amount - total_buy_amount,
            'actions_by_stock': {
                a.stock_code: {
                    'name': a.stock_name,
                    'action': a.action,
                    'current_weight': a.current_weight,
                    'target_weight': a.target_weight,
                    'amount': a.amount
                }
                for a in actions if a.action != 'hold'
            }
        }

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _calculate_target_weights(
        self,
        holdings: List[Dict[str, Any]],
        total_value: int
    ) -> Dict[str, float]:
        """
        전략에 따른 목표 비중 계산

        Args:
            holdings: 보유 종목
            total_value: 총 가치

        Returns:
            목표 비중 딕셔너리 (stock_code: weight%)
        """
        if self.strategy == RebalanceStrategy.EQUAL_WEIGHT:
            # 균등 비중
            weight = 100.0 / len(holdings)
            return {h.get('stock_code'): weight for h in holdings}

        elif self.strategy == RebalanceStrategy.RISK_PARITY:
            # 리스크 패리티 (변동성 역수 비중)
            return self._calculate_risk_parity_weights(holdings)

        elif self.strategy == RebalanceStrategy.MOMENTUM:
            # 모멘텀 기반
            return self._calculate_momentum_weights(holdings)

        elif self.strategy == RebalanceStrategy.AI_DRIVEN:
            # AI 점수 기반
            return self._calculate_ai_weights(holdings)

        else:
            # 기본값: 균등 비중
            weight = 100.0 / len(holdings)
            return {h.get('stock_code'): weight for h in holdings}

    def _calculate_risk_parity_weights(
        self,
        holdings: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """리스크 패리티 비중 계산"""
        # 변동성 추정 (간단한 버전)
        volatilities = {}
        for holding in holdings:
            # TODO: 실제 변동성 계산 (표준편차)
            # 여기서는 간단히 등락률 절댓값 사용
            change_rate = abs(holding.get('change_rate', 1.0))
            volatilities[holding.get('stock_code')] = max(change_rate, 0.1)  # 최소 0.1

        # 역수 계산
        inv_vol = {code: 1.0 / vol for code, vol in volatilities.items()}

        # 정규화
        total_inv_vol = sum(inv_vol.values())
        weights = {code: (inv / total_inv_vol) * 100 for code, inv in inv_vol.items()}

        return weights

    def _calculate_momentum_weights(
        self,
        holdings: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """모멘텀 기반 비중 계산"""
        # 수익률 기반
        returns = {}
        for holding in holdings:
            profit_rate = holding.get('profit_rate', 0)
            returns[holding.get('stock_code')] = max(profit_rate, 0)  # 음수는 0으로

        # 정규화
        total_return = sum(returns.values())
        if total_return > 0:
            weights = {code: (ret / total_return) * 100 for code, ret in returns.items()}
        else:
            # 모두 손실이면 균등 비중
            weight = 100.0 / len(holdings)
            weights = {h.get('stock_code'): weight for h in holdings}

        return weights

    def _calculate_ai_weights(
        self,
        holdings: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """AI 점수 기반 비중 계산"""
        # AI 점수 사용
        scores = {}
        for holding in holdings:
            ai_score = holding.get('ai_score', 5.0)  # 기본 5점
            scores[holding.get('stock_code')] = max(ai_score, 0)

        # 정규화
        total_score = sum(scores.values())
        if total_score > 0:
            weights = {code: (score / total_score) * 100 for code, score in scores.items()}
        else:
            weight = 100.0 / len(holdings)
            weights = {h.get('stock_code'): weight for h in holdings}

        return weights

    def _action_to_dict(self, action: RebalanceAction) -> Dict[str, Any]:
        """액션 객체를 딕셔너리로 변환"""
        return {
            'stock_code': action.stock_code,
            'stock_name': action.stock_name,
            'action': action.action,
            'current_weight': action.current_weight,
            'target_weight': action.target_weight,
            'current_value': action.current_value,
            'target_value': action.target_value,
            'quantity_change': action.quantity_change,
            'amount': action.amount,
            'reason': action.reason
        }

    def _save_rebalance_history(self, record: Dict[str, Any]):
        """리밸런싱 히스토리 저장"""
        self.rebalance_history.append(record)
        # 최근 100개만 보관
        if len(self.rebalance_history) > 100:
            self.rebalance_history.pop(0)


# Singleton instance
_auto_rebalancer: Optional[AutoRebalancer] = None


def get_auto_rebalancer() -> AutoRebalancer:
    """싱글톤 자동 리밸런서 인스턴스 반환"""
    global _auto_rebalancer
    if _auto_rebalancer is None:
        _auto_rebalancer = AutoRebalancer()
    return _auto_rebalancer


__all__ = [
    'AutoRebalancer',
    'RebalanceStrategy',
    'RebalanceAction',
    'get_auto_rebalancer'
]
