"""
Liquidity-Based Order Splitting
유동성 기반 자동 주문 분할

시장 충격을 최소화하기 위한 지능형 주문 분할
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)


@dataclass
class SplitOrder:
    """분할 주문"""
    order_number: int
    quantity: int
    estimated_price: float
    delay_seconds: float  # 이전 주문과의 시간 간격


class LiquiditySplitter:
    """
    유동성 기반 주문 분할기

    기능:
    - 거래량 분석
    - 시장 충격 최소화
    - 최적 분할 횟수 계산
    - TWAP/VWAP 전략 지원
    """

    def __init__(self, config=None):
        """
        Args:
            config: automation_features 설정
        """
        self.config = config or {}
        self.enabled = self.config.get('liquidity_based_order_split', True)
        self.max_impact_pct = self.config.get('max_order_impact_pct', 0.05)  # 5%

        logger.info(f"LiquiditySplitter initialized - Enabled: {self.enabled}, Max Impact: {self.max_impact_pct*100}%")

    def calculate_split_orders(
        self,
        target_quantity: int,
        current_price: float,
        avg_daily_volume: int,
        avg_volume_per_minute: Optional[int] = None,
        strategy: str = "liquidity_adaptive"
    ) -> List[SplitOrder]:
        """
        주문 분할 계산

        Args:
            target_quantity: 목표 주문 수량
            current_price: 현재가
            avg_daily_volume: 평균 일일 거래량
            avg_volume_per_minute: 평균 분당 거래량 (옵션)
            strategy: 분할 전략
                - "liquidity_adaptive": 유동성 적응형 (기본)
                - "twap": 시간 가중 평균
                - "vwap": 거래량 가중 평균
                - "iceberg": 빙산 주문 (소량씩 지속)

        Returns:
            분할 주문 리스트
        """
        if not self.enabled:
            # 비활성화 시 전량 1회 주문
            return [SplitOrder(
                order_number=1,
                quantity=target_quantity,
                estimated_price=current_price,
                delay_seconds=0
            )]

        # 분당 거래량 추정 (없으면 일일 거래량 / 360분으로 추정)
        if avg_volume_per_minute is None:
            avg_volume_per_minute = avg_daily_volume // 360

        if avg_volume_per_minute == 0:
            avg_volume_per_minute = 100  # 최소값

        # 전략별 분할
        if strategy == "twap":
            return self._split_twap(target_quantity, current_price)
        elif strategy == "vwap":
            return self._split_vwap(target_quantity, current_price, avg_volume_per_minute)
        elif strategy == "iceberg":
            return self._split_iceberg(target_quantity, current_price, avg_volume_per_minute)
        else:  # liquidity_adaptive
            return self._split_adaptive(
                target_quantity,
                current_price,
                avg_daily_volume,
                avg_volume_per_minute
            )

    def _split_adaptive(
        self,
        target_quantity: int,
        current_price: float,
        avg_daily_volume: int,
        avg_volume_per_minute: int
    ) -> List[SplitOrder]:
        """
        유동성 적응형 분할

        주문이 거래량의 일정 비율을 넘지 않도록 분할
        """
        # 1. 시장 충격 계산
        order_value = target_quantity * current_price
        daily_volume_value = avg_daily_volume * current_price
        order_to_volume_ratio = order_value / daily_volume_value if daily_volume_value > 0 else 1.0

        # 2. 분할 필요 여부 판단
        if order_to_volume_ratio <= self.max_impact_pct:
            # 충격이 작으면 분할 불필요
            return [SplitOrder(
                order_number=1,
                quantity=target_quantity,
                estimated_price=current_price,
                delay_seconds=0
            )]

        # 3. 분할 횟수 계산
        # 각 분할이 최대 충격 이하가 되도록
        min_splits = math.ceil(order_to_volume_ratio / self.max_impact_pct)

        # 최대 10회로 제한
        num_splits = min(min_splits, 10)

        # 4. 각 분할 수량 계산
        base_quantity = target_quantity // num_splits
        remainder = target_quantity % num_splits

        split_orders = []

        for i in range(num_splits):
            # 나머지를 앞쪽 주문에 배분
            quantity = base_quantity + (1 if i < remainder else 0)

            # 지연 시간 계산 (각 주문 사이에 간격)
            # 분당 거래량의 일부가 처리될 때까지 대기
            delay = self._calculate_delay(quantity, avg_volume_per_minute)

            split_orders.append(SplitOrder(
                order_number=i + 1,
                quantity=quantity,
                estimated_price=current_price,  # 실제로는 슬리피지 고려해야 함
                delay_seconds=delay if i > 0 else 0  # 첫 주문은 즉시
            ))

        logger.info(f"Adaptive split: {target_quantity}주 → {num_splits}회 분할 (충격 {order_to_volume_ratio*100:.2f}% → {order_to_volume_ratio/num_splits*100:.2f}%)")

        return split_orders

    def _split_twap(
        self,
        target_quantity: int,
        current_price: float
    ) -> List[SplitOrder]:
        """
        TWAP (Time-Weighted Average Price) 분할

        일정 시간 간격으로 균등 분할
        """
        # 10분 동안 1분마다 주문
        num_splits = 10
        base_quantity = target_quantity // num_splits
        remainder = target_quantity % num_splits

        split_orders = []

        for i in range(num_splits):
            quantity = base_quantity + (1 if i < remainder else 0)

            split_orders.append(SplitOrder(
                order_number=i + 1,
                quantity=quantity,
                estimated_price=current_price,
                delay_seconds=60 if i > 0 else 0  # 1분 간격
            ))

        logger.info(f"TWAP split: {target_quantity}주 → {num_splits}회 분할 (1분 간격)")

        return split_orders

    def _split_vwap(
        self,
        target_quantity: int,
        current_price: float,
        avg_volume_per_minute: int
    ) -> List[SplitOrder]:
        """
        VWAP (Volume-Weighted Average Price) 분할

        거래량 패턴에 따라 분할 (장 초반과 후반에 많이)
        """
        # 간단한 VWAP 근사: U자형 거래량 패턴 가정
        # 장 초반 30%, 중반 40%, 후반 30%

        split_ratios = [0.15, 0.15, 0.10, 0.10, 0.10, 0.10, 0.15, 0.15]  # 8개 구간
        split_orders = []

        for i, ratio in enumerate(split_ratios):
            quantity = int(target_quantity * ratio)

            if quantity > 0:
                split_orders.append(SplitOrder(
                    order_number=i + 1,
                    quantity=quantity,
                    estimated_price=current_price,
                    delay_seconds=90 if i > 0 else 0  # 1.5분 간격
                ))

        logger.info(f"VWAP split: {target_quantity}주 → {len(split_orders)}회 분할 (거래량 가중)")

        return split_orders

    def _split_iceberg(
        self,
        target_quantity: int,
        current_price: float,
        avg_volume_per_minute: int
    ) -> List[SplitOrder]:
        """
        빙산 주문 (Iceberg Order)

        소량씩 지속적으로 주문하여 큰 주문을 숨김
        """
        # 분당 거래량의 5%씩 주문
        order_size = max(int(avg_volume_per_minute * 0.05), 1)

        num_splits = math.ceil(target_quantity / order_size)

        # 최대 20회로 제한
        if num_splits > 20:
            num_splits = 20
            order_size = target_quantity // num_splits

        split_orders = []

        for i in range(num_splits):
            remaining = target_quantity - sum(o.quantity for o in split_orders)
            quantity = min(order_size, remaining)

            if quantity > 0:
                split_orders.append(SplitOrder(
                    order_number=i + 1,
                    quantity=quantity,
                    estimated_price=current_price,
                    delay_seconds=30 if i > 0 else 0  # 30초 간격
                ))

        logger.info(f"Iceberg split: {target_quantity}주 → {len(split_orders)}회 분할 (소량씩)")

        return split_orders

    def _calculate_delay(self, quantity: int, avg_volume_per_minute: int) -> float:
        """
        지연 시간 계산

        해당 수량이 시장에서 흡수될 시간 추정

        Args:
            quantity: 주문 수량
            avg_volume_per_minute: 분당 평균 거래량

        Returns:
            지연 시간 (초)
        """
        if avg_volume_per_minute == 0:
            return 60.0  # 기본 1분

        # 주문 수량이 분당 거래량의 10%로 흡수될 시간
        minutes_to_absorb = quantity / (avg_volume_per_minute * 0.1)

        # 초 단위로 변환 (최소 10초, 최대 5분)
        delay_seconds = minutes_to_absorb * 60
        delay_seconds = max(10, min(delay_seconds, 300))

        return delay_seconds

    def estimate_market_impact(
        self,
        order_quantity: int,
        current_price: float,
        avg_daily_volume: int
    ) -> Dict[str, float]:
        """
        시장 충격 추정

        Args:
            order_quantity: 주문 수량
            current_price: 현재가
            avg_daily_volume: 평균 일일 거래량

        Returns:
            충격 추정 결과
        """
        order_value = order_quantity * current_price
        daily_volume_value = avg_daily_volume * current_price

        if daily_volume_value == 0:
            return {
                'impact_ratio': 1.0,
                'estimated_slippage_pct': 1.0,
                'recommendation': "거래량 데이터 부족"
            }

        # 주문 비율 (거래량 대비)
        impact_ratio = order_value / daily_volume_value

        # 슬리피지 추정 (간단한 모델)
        # 영향 = k * sqrt(주문비율)
        k = 0.5  # 충격 계수
        estimated_slippage_pct = k * math.sqrt(impact_ratio) * 100

        # 권장사항
        if impact_ratio <= 0.01:  # 1% 이하
            recommendation = "시장 충격 무시 가능"
        elif impact_ratio <= 0.05:  # 5% 이하
            recommendation = "적당한 주문 크기"
        elif impact_ratio <= 0.10:  # 10% 이하
            recommendation = "분할 주문 권장"
        else:
            recommendation = "대량 주문 - 여러 날에 걸쳐 분할 필요"

        return {
            'impact_ratio': impact_ratio,
            'estimated_slippage_pct': estimated_slippage_pct,
            'recommendation': recommendation
        }


# Singleton instance
_liquidity_splitter = None


def get_liquidity_splitter(config=None):
    """Get liquidity splitter singleton"""
    global _liquidity_splitter
    if _liquidity_splitter is None:
        _liquidity_splitter = LiquiditySplitter(config)
    return _liquidity_splitter


__all__ = ['LiquiditySplitter', 'SplitOrder', 'get_liquidity_splitter']
