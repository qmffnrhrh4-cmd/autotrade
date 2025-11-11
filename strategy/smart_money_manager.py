"""
Smart Money Management System
스마트 자금 관리 시스템

동적 포지션 사이징, 리스크 관리, 자금 배분 최적화
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """리스크 레벨"""
    CONSERVATIVE = "conservative"  # 보수적 (5-10%)
    MODERATE = "moderate"          # 중립적 (10-20%)
    AGGRESSIVE = "aggressive"      # 공격적 (20-30%)


@dataclass
class PositionSize:
    """포지션 사이즈 계산 결과"""
    stock_code: str
    recommended_quantity: int
    recommended_amount: float
    position_ratio: float  # 전체 자산 대비 비율
    risk_amount: float     # 리스크 금액 (손실 시)
    confidence_level: float  # 신뢰도 (0-1)
    reasoning: str  # 계산 근거


class SmartMoneyManager:
    """
    스마트 자금 관리 시스템

    기능:
    - 동적 포지션 사이징 (Kelly Criterion, Fixed Fractional)
    - 리스크 기반 자금 배분
    - 변동성 기반 조정
    - 승률 기반 최적화
    """

    def __init__(self, config=None):
        """
        Args:
            config: 설정 (automation_features)
        """
        self.config = config or {}
        self.enabled = self.config.get('smart_money_management', True)
        self.dynamic_sizing = self.config.get('dynamic_position_sizing', True)

        # 기본 설정
        self.max_position_ratio = 0.25  # 최대 25%
        self.min_position_ratio = 0.05  # 최소 5%
        self.default_risk_per_trade = 0.02  # 거래당 2% 리스크

        logger.info(f"SmartMoneyManager initialized - Enabled: {self.enabled}, Dynamic: {self.dynamic_sizing}")

    def calculate_position_size(
        self,
        stock_code: str,
        current_price: float,
        available_capital: float,
        strategy_confidence: float = 0.7,
        win_rate: float = 0.5,
        avg_win_loss_ratio: float = 1.5,
        volatility: float = 0.02,
        risk_level: RiskLevel = RiskLevel.MODERATE
    ) -> PositionSize:
        """
        포지션 사이즈 계산

        Args:
            stock_code: 종목 코드
            current_price: 현재가
            available_capital: 사용 가능 자본
            strategy_confidence: 전략 신뢰도 (0-1)
            win_rate: 승률 (0-1)
            avg_win_loss_ratio: 평균 수익/손실 비율
            volatility: 변동성 (일일 표준편차)
            risk_level: 리스크 레벨

        Returns:
            PositionSize 객체
        """
        if not self.enabled:
            # 비활성화 시 기본 계산
            return self._calculate_fixed_size(stock_code, current_price, available_capital, 0.15)

        # 1. 리스크 레벨에 따른 기본 비율
        if risk_level == RiskLevel.CONSERVATIVE:
            base_ratio = 0.10  # 10%
        elif risk_level == RiskLevel.AGGRESSIVE:
            base_ratio = 0.25  # 25%
        else:  # MODERATE
            base_ratio = 0.15  # 15%

        # 2. Kelly Criterion 계산 (선택적)
        kelly_ratio = self._calculate_kelly_criterion(
            win_rate=win_rate,
            avg_win_loss_ratio=avg_win_loss_ratio
        )

        # 3. 변동성 조정
        volatility_adjusted_ratio = self._adjust_for_volatility(
            base_ratio=base_ratio,
            volatility=volatility
        )

        # 4. 신뢰도 조정
        confidence_adjusted_ratio = volatility_adjusted_ratio * strategy_confidence

        # 5. Kelly와 조합 (dynamic sizing이 활성화된 경우)
        if self.dynamic_sizing and kelly_ratio > 0:
            # Kelly의 절반만 사용 (안전성)
            kelly_weight = 0.3
            final_ratio = (
                confidence_adjusted_ratio * (1 - kelly_weight) +
                kelly_ratio * 0.5 * kelly_weight
            )
        else:
            final_ratio = confidence_adjusted_ratio

        # 6. 최소/최대 제한
        final_ratio = np.clip(final_ratio, self.min_position_ratio, self.max_position_ratio)

        # 7. 실제 금액 및 수량 계산
        position_amount = available_capital * final_ratio
        quantity = int(position_amount / current_price)

        # 최소 1주
        if quantity == 0 and position_amount >= current_price:
            quantity = 1

        actual_amount = quantity * current_price
        actual_ratio = actual_amount / available_capital if available_capital > 0 else 0

        # 8. 리스크 금액 계산 (손절 시 예상 손실)
        risk_amount = actual_amount * self.default_risk_per_trade

        # 9. 계산 근거 생성
        reasoning = self._generate_reasoning(
            base_ratio=base_ratio,
            kelly_ratio=kelly_ratio,
            volatility=volatility,
            confidence=strategy_confidence,
            final_ratio=final_ratio
        )

        return PositionSize(
            stock_code=stock_code,
            recommended_quantity=quantity,
            recommended_amount=actual_amount,
            position_ratio=actual_ratio,
            risk_amount=risk_amount,
            confidence_level=strategy_confidence,
            reasoning=reasoning
        )

    def allocate_capital_multi_stock(
        self,
        stock_list: List[Dict],
        available_capital: float,
        risk_level: RiskLevel = RiskLevel.MODERATE
    ) -> Dict[str, PositionSize]:
        """
        여러 종목에 자본 배분

        Args:
            stock_list: 종목 리스트
                [
                    {
                        'stock_code': '005930',
                        'current_price': 73000,
                        'confidence': 0.8,
                        'win_rate': 0.6,
                        'volatility': 0.025
                    },
                    ...
                ]
            available_capital: 사용 가능 자본
            risk_level: 리스크 레벨

        Returns:
            종목별 PositionSize 딕셔너리
        """
        if not stock_list:
            return {}

        # 총 신뢰도 계산
        total_confidence = sum(s.get('confidence', 0.5) for s in stock_list)

        if total_confidence == 0:
            total_confidence = len(stock_list) * 0.5

        # 신뢰도 비율로 자본 배분
        allocations = {}
        remaining_capital = available_capital

        for stock in stock_list:
            # 신뢰도 기반 비율
            confidence = stock.get('confidence', 0.5)
            allocation_ratio = confidence / total_confidence

            # 해당 종목에 배분된 자본
            allocated_capital = available_capital * allocation_ratio

            # 포지션 사이즈 계산
            position = self.calculate_position_size(
                stock_code=stock['stock_code'],
                current_price=stock['current_price'],
                available_capital=allocated_capital,
                strategy_confidence=confidence,
                win_rate=stock.get('win_rate', 0.5),
                avg_win_loss_ratio=stock.get('avg_win_loss_ratio', 1.5),
                volatility=stock.get('volatility', 0.02),
                risk_level=risk_level
            )

            allocations[stock['stock_code']] = position

        return allocations

    def should_reduce_position(
        self,
        current_loss_pct: float,
        max_drawdown_pct: float,
        consecutive_losses: int
    ) -> Tuple[bool, float]:
        """
        포지션 축소 필요 여부 판단

        Args:
            current_loss_pct: 현재 손실률 (%)
            max_drawdown_pct: 최대 낙폭 (%)
            consecutive_losses: 연속 손실 횟수

        Returns:
            (축소 필요 여부, 권장 축소 비율)
        """
        should_reduce = False
        reduction_ratio = 1.0  # 1.0 = 유지, 0.5 = 50% 축소

        # 조건 1: 큰 손실 발생
        if current_loss_pct > 5.0:  # 5% 이상 손실
            should_reduce = True
            reduction_ratio = 0.7  # 30% 축소

        if current_loss_pct > 10.0:  # 10% 이상 손실
            reduction_ratio = 0.5  # 50% 축소

        # 조건 2: 최대 낙폭 경고
        if max_drawdown_pct > 15.0:  # 15% 이상 낙폭
            should_reduce = True
            reduction_ratio = min(reduction_ratio, 0.6)

        # 조건 3: 연속 손실
        if consecutive_losses >= 3:
            should_reduce = True
            # 연속 손실 횟수에 따라 추가 축소
            penalty = 0.9 ** (consecutive_losses - 2)  # 3회부터 10%씩 추가 축소
            reduction_ratio = min(reduction_ratio, penalty)

        return should_reduce, reduction_ratio

    def _calculate_kelly_criterion(
        self,
        win_rate: float,
        avg_win_loss_ratio: float
    ) -> float:
        """
        Kelly Criterion 계산

        K = W - [(1-W) / R]
        where:
            W = 승률
            R = 평균 수익/손실 비율

        Returns:
            Kelly 비율 (0-1)
        """
        if avg_win_loss_ratio <= 0:
            return 0.0

        kelly = win_rate - ((1 - win_rate) / avg_win_loss_ratio)

        # 음수면 0으로 (배팅하지 않음)
        kelly = max(0, kelly)

        # 최대 0.25 (25%)로 제한
        kelly = min(kelly, 0.25)

        return kelly

    def _adjust_for_volatility(
        self,
        base_ratio: float,
        volatility: float
    ) -> float:
        """
        변동성 기반 조정

        변동성이 높으면 포지션 축소, 낮으면 확대

        Args:
            base_ratio: 기본 비율
            volatility: 변동성 (일일 표준편차)

        Returns:
            조정된 비율
        """
        # 기준 변동성: 2% (일반적인 주식)
        reference_volatility = 0.02

        if volatility <= 0:
            return base_ratio

        # 변동성 비율
        volatility_ratio = reference_volatility / volatility

        # 변동성이 2배면 포지션 50% 축소
        # 변동성이 절반이면 포지션 2배 확대 (최대 제한 적용)
        adjusted_ratio = base_ratio * volatility_ratio

        return adjusted_ratio

    def _calculate_fixed_size(
        self,
        stock_code: str,
        current_price: float,
        available_capital: float,
        fixed_ratio: float
    ) -> PositionSize:
        """고정 비율 계산 (백업용)"""
        position_amount = available_capital * fixed_ratio
        quantity = int(position_amount / current_price)

        if quantity == 0 and position_amount >= current_price:
            quantity = 1

        actual_amount = quantity * current_price
        actual_ratio = actual_amount / available_capital if available_capital > 0 else 0

        return PositionSize(
            stock_code=stock_code,
            recommended_quantity=quantity,
            recommended_amount=actual_amount,
            position_ratio=actual_ratio,
            risk_amount=actual_amount * 0.02,
            confidence_level=0.5,
            reasoning="Fixed ratio calculation (smart money management disabled)"
        )

    def _generate_reasoning(
        self,
        base_ratio: float,
        kelly_ratio: float,
        volatility: float,
        confidence: float,
        final_ratio: float
    ) -> str:
        """계산 근거 생성"""
        parts = []

        parts.append(f"기본 비율: {base_ratio*100:.1f}%")

        if kelly_ratio > 0:
            parts.append(f"Kelly: {kelly_ratio*100:.1f}%")

        parts.append(f"변동성: {volatility*100:.1f}%")
        parts.append(f"신뢰도: {confidence*100:.0f}%")
        parts.append(f"→ 최종: {final_ratio*100:.1f}%")

        return " | ".join(parts)


# Singleton instance
_smart_money_manager = None


def get_smart_money_manager(config=None):
    """Get smart money manager singleton"""
    global _smart_money_manager
    if _smart_money_manager is None:
        _smart_money_manager = SmartMoneyManager(config)
    return _smart_money_manager


__all__ = ['SmartMoneyManager', 'PositionSize', 'RiskLevel', 'get_smart_money_manager']
