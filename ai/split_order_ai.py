"""
AI-Powered Split Order Decision System
AI 기반 분할 주문 결정 시스템

시장 상황, 종목 특성, 과거 성과를 분석하여 최적의 분할 전략 결정
"""
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .parameter_optimizer import get_parameter_optimizer
from .self_learning_system import get_self_learning_system

logger = logging.getLogger(__name__)


@dataclass
class SplitOrderDecision:
    """AI 분할 주문 결정"""
    num_splits: int
    price_gaps: List[float]  # 각 분할의 가격 간격 (%)
    time_intervals: List[float]  # 각 분할의 시간 간격 (초)
    strategy: str  # gradual_down, support_levels, immediate, vwap, twap, iceberg
    quantities: List[int]  # 각 분할의 수량
    confidence: float  # AI 신뢰도 (0-1)
    reasoning: str  # 결정 이유


class SplitOrderAI:
    """
    AI 기반 분할 주문 결정 시스템

    기능:
    - 시장 상황 실시간 분석
    - 최적 분할 횟수 AI 결정
    - 동적 가격 간격 계산
    - 시간 간격 자동 조정
    - 과거 성과 기반 학습
    """

    def __init__(self):
        self.param_optimizer = get_parameter_optimizer()
        self.learning_system = get_self_learning_system()

        # 전략별 기본 파라미터 (학습 시작점)
        self.strategy_defaults = {
            'gradual_down': {
                'base_splits': 3,
                'base_gap': 0.01,
                'base_interval': 60
            },
            'support_levels': {
                'base_splits': 3,
                'base_gap': 0.015,
                'base_interval': 120
            },
            'immediate': {
                'base_splits': 1,
                'base_gap': 0.0,
                'base_interval': 0
            },
            'vwap': {
                'base_splits': 8,
                'base_gap': 0.005,
                'base_interval': 90
            },
            'twap': {
                'base_splits': 10,
                'base_gap': 0.005,
                'base_interval': 60
            },
            'iceberg': {
                'base_splits': 15,
                'base_gap': 0.003,
                'base_interval': 30
            }
        }

        logger.info("Split Order AI initialized")

    def decide_split_buy_strategy(
        self,
        stock_code: str,
        stock_name: str,
        total_quantity: int,
        current_price: float,
        market_data: Dict[str, any],
        ai_analysis: Optional[Dict] = None
    ) -> SplitOrderDecision:
        """
        AI 기반 분할 매수 전략 결정

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            total_quantity: 총 매수 수량
            current_price: 현재가
            market_data: 시장 데이터
            ai_analysis: AI 분석 결과

        Returns:
            SplitOrderDecision
        """
        # 1. 시장 상황 분석
        market_condition = self._analyze_market_condition(market_data)

        # 2. 종목 특성 분석
        stock_features = self._analyze_stock_features(stock_code, market_data)

        # 3. 최적 전략 선택
        strategy = self._select_optimal_strategy(
            market_condition,
            stock_features,
            is_buy=True
        )

        # 4. AI로 파라미터 최적화
        optimal_params = self.param_optimizer.get_optimal_split_order_params(
            stock_code=stock_code,
            order_amount=total_quantity * current_price,
            volatility=stock_features['volatility'],
            liquidity=stock_features['avg_volume'],
            market_condition=market_condition
        )

        # 5. 분할 계획 생성
        num_splits = optimal_params['num_splits']
        price_gap_pct = optimal_params['price_gap_pct']
        time_interval = optimal_params['time_interval_sec']

        # 6. 각 분할의 세부 설정
        price_gaps = self._calculate_dynamic_price_gaps(
            num_splits,
            base_gap=price_gap_pct,
            volatility=stock_features['volatility'],
            trend=stock_features['trend'],
            is_buy=True
        )

        time_intervals = self._calculate_dynamic_time_intervals(
            num_splits,
            base_interval=time_interval,
            volume_profile=stock_features.get('volume_profile', 'normal'),
            market_condition=market_condition
        )

        quantities = self._calculate_split_quantities(
            total_quantity,
            num_splits,
            distribution=self._get_quantity_distribution(strategy, stock_features)
        )

        # 7. AI 신뢰도 계산
        confidence = self._calculate_decision_confidence(
            optimal_params.get('confidence_score', 0.7),
            ai_analysis
        )

        # 8. 결정 이유 생성
        reasoning = self._generate_reasoning(
            strategy,
            market_condition,
            stock_features,
            optimal_params
        )

        decision = SplitOrderDecision(
            num_splits=num_splits,
            price_gaps=price_gaps,
            time_intervals=time_intervals,
            strategy=strategy,
            quantities=quantities,
            confidence=confidence,
            reasoning=reasoning
        )

        logger.info(
            f"🤖 AI Split Buy Decision for {stock_name}({stock_code}): "
            f"{num_splits} splits, Strategy={strategy}, Confidence={confidence:.1%}"
        )
        logger.info(f"   Reasoning: {reasoning}")

        return decision

    def decide_split_sell_strategy(
        self,
        stock_code: str,
        stock_name: str,
        total_quantity: int,
        current_price: float,
        entry_price: float,
        market_data: Dict[str, any],
        holding_duration_hours: float = 24.0
    ) -> SplitOrderDecision:
        """
        AI 기반 분할 매도 전략 결정

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            total_quantity: 총 매도 수량
            current_price: 현재가
            entry_price: 진입가
            market_data: 시장 데이터
            holding_duration_hours: 보유 기간 (시간)

        Returns:
            SplitOrderDecision
        """
        # 1. 현재 수익률
        profit_pct = (current_price - entry_price) / entry_price

        # 2. 시장 상황 분석
        market_condition = self._analyze_market_condition(market_data)

        # 3. 종목 특성 분석
        stock_features = self._analyze_stock_features(stock_code, market_data)

        # 4. 청산 전략 선택 (수익률 기반)
        if profit_pct > 0.05:  # 5% 이상 수익
            strategy = "gradual_profit"  # 점진적 익절
            base_splits = 4
        elif profit_pct > 0.02:  # 2~5% 수익
            strategy = "quick_exit"  # 빠른 익절
            base_splits = 2
        elif profit_pct < -0.03:  # -3% 이하 손실
            strategy = "emergency_exit"  # 긴급 청산
            base_splits = 1
        else:  # 소폭 수익/손실
            strategy = "normal_exit"
            base_splits = 3

        # 5. AI 최적화
        optimal_params = self.param_optimizer.get_optimal_split_order_params(
            stock_code=stock_code,
            order_amount=total_quantity * current_price,
            volatility=stock_features['volatility'],
            liquidity=stock_features['avg_volume'],
            market_condition=market_condition
        )

        # 긴급 청산이면 즉시 전량 매도
        if strategy == "emergency_exit":
            return SplitOrderDecision(
                num_splits=1,
                price_gaps=[0.0],
                time_intervals=[0.0],
                strategy="immediate",
                quantities=[total_quantity],
                confidence=0.95,
                reasoning="손실 확대 방지를 위한 긴급 청산"
            )

        # 6. 분할 계획
        num_splits = min(base_splits, optimal_params['num_splits'])

        # 매도는 위쪽 가격 (익절)
        profit_targets = self._calculate_profit_targets(
            num_splits,
            current_profit=profit_pct,
            strategy=strategy,
            volatility=stock_features['volatility']
        )

        time_intervals = self._calculate_dynamic_time_intervals(
            num_splits,
            base_interval=optimal_params['time_interval_sec'],
            volume_profile=stock_features.get('volume_profile', 'normal'),
            market_condition=market_condition
        )

        # 수량 분배 (익절은 앞쪽에 많이)
        quantities = self._calculate_split_quantities(
            total_quantity,
            num_splits,
            distribution="front_loaded" if profit_pct > 0 else "even"
        )

        confidence = self._calculate_decision_confidence(
            optimal_params.get('confidence_score', 0.7),
            None
        )

        reasoning = (
            f"현재 수익률 {profit_pct*100:.1f}%, "
            f"{strategy} 전략으로 {num_splits}회 분할 매도"
        )

        decision = SplitOrderDecision(
            num_splits=num_splits,
            price_gaps=profit_targets,
            time_intervals=time_intervals,
            strategy=strategy,
            quantities=quantities,
            confidence=confidence,
            reasoning=reasoning
        )

        logger.info(
            f"🤖 AI Split Sell Decision for {stock_name}({stock_code}): "
            f"{num_splits} splits, Profit={profit_pct*100:.1f}%, Strategy={strategy}"
        )

        return decision

    def _analyze_market_condition(self, market_data: Dict) -> str:
        """시장 상황 분석"""
        kospi_change = market_data.get('kospi_change_pct', 0)
        kosdaq_change = market_data.get('kosdaq_change_pct', 0)
        volatility_index = market_data.get('volatility_index', 15)

        # 변동성
        if volatility_index > 25:
            return "volatile"
        # 상승 추세
        elif kospi_change > 1.5 or kosdaq_change > 2.0:
            return "bullish"
        # 하락 추세
        elif kospi_change < -1.5 or kosdaq_change < -2.0:
            return "bearish"
        # 횡보
        else:
            return "neutral"

    def _analyze_stock_features(self, stock_code: str, market_data: Dict) -> Dict:
        """종목 특성 분석"""
        return {
            'volatility': market_data.get('volatility', 0.02),
            'avg_volume': market_data.get('avg_volume', 1000000),
            'volume_ratio': market_data.get('volume_ratio', 1.0),
            'trend': market_data.get('price_change_pct', 0.0),
            'volume_profile': self._classify_volume_profile(market_data.get('volume_ratio', 1.0))
        }

    def _classify_volume_profile(self, volume_ratio: float) -> str:
        """거래량 프로파일 분류"""
        if volume_ratio > 2.0:
            return "surging"
        elif volume_ratio > 1.3:
            return "high"
        elif volume_ratio < 0.7:
            return "low"
        else:
            return "normal"

    def _select_optimal_strategy(
        self,
        market_condition: str,
        stock_features: Dict,
        is_buy: bool
    ) -> str:
        """최적 전략 선택"""
        volatility = stock_features['volatility']
        volume_profile = stock_features['volume_profile']

        # 변동성 높음
        if volatility > 0.03:
            return "iceberg"  # 소량씩 지속

        # 거래량 급증
        if volume_profile == "surging":
            return "immediate"  # 즉시 진입/청산

        # 상승장
        if market_condition == "bullish" and is_buy:
            return "gradual_down"  # 점진적 하락 시 매수

        # 하락장
        if market_condition == "bearish" and not is_buy:
            return "quick_exit"  # 빠른 청산

        # 기본
        return "vwap"  # 거래량 가중 평균

    def _calculate_dynamic_price_gaps(
        self,
        num_splits: int,
        base_gap: float,
        volatility: float,
        trend: float,
        is_buy: bool
    ) -> List[float]:
        """동적 가격 간격 계산"""
        gaps = []

        for i in range(num_splits):
            # 기본 간격에서 변동성만큼 조정
            gap = base_gap * (1 + volatility * 10)

            # 추세 반영 (상승 추세면 간격 좁게, 하락 추세면 넓게)
            if is_buy:
                gap *= (1 - trend * 0.5)  # 상승 시 간격 좁게
            else:
                gap *= (1 + trend * 0.5)  # 상승 시 간격 넓게

            # 점진적으로 간격 증가
            gap *= (1 + i * 0.2)

            gaps.append(-gap if is_buy else gap)

        return gaps

    def _calculate_dynamic_time_intervals(
        self,
        num_splits: int,
        base_interval: float,
        volume_profile: str,
        market_condition: str
    ) -> List[float]:
        """동적 시간 간격 계산"""
        intervals = []

        # 거래량 프로파일에 따른 조정
        if volume_profile == "surging":
            multiplier = 0.5  # 빠르게
        elif volume_profile == "low":
            multiplier = 1.5  # 천천히
        else:
            multiplier = 1.0

        # 변동성 높으면 빠르게
        if market_condition == "volatile":
            multiplier *= 0.7

        for i in range(num_splits):
            # 첫 주문은 즉시
            if i == 0:
                intervals.append(0.0)
            else:
                # 후반으로 갈수록 간격 증가
                interval = base_interval * multiplier * (1 + i * 0.1)
                intervals.append(interval)

        return intervals

    def _calculate_split_quantities(
        self,
        total_quantity: int,
        num_splits: int,
        distribution: str = "even"
    ) -> List[int]:
        """분할 수량 계산"""
        quantities = []

        if distribution == "even":
            # 균등 분배
            base_qty = total_quantity // num_splits
            remainder = total_quantity % num_splits

            for i in range(num_splits):
                qty = base_qty + (1 if i < remainder else 0)
                quantities.append(qty)

        elif distribution == "front_loaded":
            # 앞쪽에 많이 (익절 시)
            weights = [1.5 - i * 0.3 for i in range(num_splits)]
            weights = [max(w, 0.5) for w in weights]
            total_weight = sum(weights)

            for i, weight in enumerate(weights):
                qty = int(total_quantity * weight / total_weight)
                quantities.append(qty)

            # 남은 수량 첫 번째에 추가
            remaining = total_quantity - sum(quantities)
            quantities[0] += remaining

        elif distribution == "pyramid":
            # 피라미드형 (중간에 많이)
            weights = [1.0 + 0.5 * (1 - abs(i - num_splits//2) / (num_splits//2)) for i in range(num_splits)]
            total_weight = sum(weights)

            for i, weight in enumerate(weights):
                qty = int(total_quantity * weight / total_weight)
                quantities.append(qty)

            remaining = total_quantity - sum(quantities)
            quantities[num_splits//2] += remaining

        return quantities

    def _get_quantity_distribution(self, strategy: str, stock_features: Dict) -> str:
        """전략별 수량 분배 방식"""
        if strategy in ["gradual_down", "support_levels"]:
            return "pyramid"  # 피라미드형 (중간에 많이)
        elif strategy == "iceberg":
            return "even"  # 균등
        else:
            return "even"

    def _calculate_profit_targets(
        self,
        num_splits: int,
        current_profit: float,
        strategy: str,
        volatility: float
    ) -> List[float]:
        """익절 목표가 계산"""
        targets = []

        if strategy == "gradual_profit":
            # 점진적 익절: +2%, +4%, +7%, +10%
            base_targets = [0.02, 0.04, 0.07, 0.10]
        elif strategy == "quick_exit":
            # 빠른 익절: +1%, +2%, +3%
            base_targets = [0.01, 0.02, 0.03]
        else:
            # 일반: +3%, +5%, +8%
            base_targets = [0.03, 0.05, 0.08]

        # 변동성에 따라 조정
        volatility_mult = 1 + volatility * 5

        for i in range(num_splits):
            if i < len(base_targets):
                target = base_targets[i] * volatility_mult
            else:
                # 더 많은 분할이면 이전 목표에서 증가
                target = targets[-1] * 1.3

            targets.append(target)

        return targets

    def _calculate_decision_confidence(
        self,
        base_confidence: float,
        ai_analysis: Optional[Dict]
    ) -> float:
        """결정 신뢰도 계산"""
        confidence = base_confidence

        # AI 분석 있으면 반영
        if ai_analysis:
            ai_confidence = ai_analysis.get('confidence', 0.5)
            confidence = (confidence + ai_confidence) / 2

        # 학습 시스템 인사이트 반영
        insights = self.learning_system.get_learned_insights()
        recent_win_rate = insights.get('recent_win_rate', 0.5)

        # 최근 성과가 좋으면 신뢰도 증가
        if recent_win_rate > 0.6:
            confidence = min(confidence * 1.1, 0.95)
        elif recent_win_rate < 0.4:
            confidence = max(confidence * 0.9, 0.5)

        return confidence

    def _generate_reasoning(
        self,
        strategy: str,
        market_condition: str,
        stock_features: Dict,
        optimal_params: Dict
    ) -> str:
        """결정 이유 생성"""
        reasons = []

        # 시장 상황
        if market_condition == "volatile":
            reasons.append("변동성 높은 시장")
        elif market_condition == "bullish":
            reasons.append("상승 추세 시장")
        elif market_condition == "bearish":
            reasons.append("하락 추세 시장")

        # 종목 특성
        vol = stock_features['volatility']
        if vol > 0.03:
            reasons.append(f"높은 변동성({vol*100:.1f}%)")
        elif vol < 0.015:
            reasons.append(f"낮은 변동성({vol*100:.1f}%)")

        volume_profile = stock_features.get('volume_profile')
        if volume_profile == "surging":
            reasons.append("거래량 급증")
        elif volume_profile == "low":
            reasons.append("거래량 저조")

        # 전략
        strategy_names = {
            'gradual_down': '점진적 분할 매수',
            'support_levels': '지지선 기반 매수',
            'immediate': '즉시 진입',
            'vwap': 'VWAP 전략',
            'twap': 'TWAP 전략',
            'iceberg': '빙산 주문'
        }
        reasons.append(strategy_names.get(strategy, strategy))

        return " | ".join(reasons)


# Singleton
_split_order_ai = None


def get_split_order_ai() -> SplitOrderAI:
    """Get split order AI singleton"""
    global _split_order_ai
    if _split_order_ai is None:
        _split_order_ai = SplitOrderAI()
    return _split_order_ai


__all__ = ['SplitOrderAI', 'get_split_order_ai', 'SplitOrderDecision']
