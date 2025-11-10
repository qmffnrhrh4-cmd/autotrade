"""
AI-based Trading Timing Optimizer
AI 기반 매수/매도 타이밍 최적화 시스템

Features:
- 호가창 분석 (order book analysis)
- 체결강도 분석 (trade strength analysis)
- 시간대별 매매 패턴 학습
- 분할 매수/매도 최적화
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class TradingTimeSlot:
    """거래 시간대 분류"""
    OPENING = "장 시작"      # 09:00-09:30
    MORNING = "오전장"        # 09:30-11:00
    MIDDAY = "중간장"         # 11:00-13:00
    AFTERNOON = "오후장"      # 13:00-14:30
    CLOSING = "장 마감"       # 14:30-15:20


class OrderStrength:
    """주문 강도"""
    VERY_STRONG_BUY = "매수 매우 강함"
    STRONG_BUY = "매수 강함"
    WEAK_BUY = "매수 약함"
    NEUTRAL = "중립"
    WEAK_SELL = "매도 약함"
    STRONG_SELL = "매도 강함"
    VERY_STRONG_SELL = "매도 매우 강함"


class TimingOptimizer:
    """
    AI-based Trading Timing Optimizer
    AI 기반 거래 타이밍 최적화
    """

    def __init__(self, openapi_client=None):
        """
        Initialize Timing Optimizer

        Args:
            openapi_client: OpenAPI client for real-time data
        """
        self.openapi_client = openapi_client

        # Historical patterns (학습된 패턴)
        self.time_patterns = {
            TradingTimeSlot.OPENING: {'volatility': 'high', 'volume': 'high', 'strategy': '관망 후 진입'},
            TradingTimeSlot.MORNING: {'volatility': 'medium', 'volume': 'high', 'strategy': '주 매매 시간'},
            TradingTimeSlot.MIDDAY: {'volatility': 'low', 'volume': 'low', 'strategy': '추세 확인'},
            TradingTimeSlot.AFTERNOON: {'volatility': 'medium', 'volume': 'medium', 'strategy': '포지션 조정'},
            TradingTimeSlot.CLOSING: {'volatility': 'high', 'volume': 'high', 'strategy': '데이 트레이딩 청산'},
        }

    def analyze_order_book(self, stock_code: str) -> Dict:
        """
        Analyze order book (호가창 분석)

        Args:
            stock_code: 종목 코드

        Returns:
            {
                'buy_pressure': float,    # 매수 압력 (0-100)
                'sell_pressure': float,   # 매도 압력 (0-100)
                'net_pressure': float,    # 순압력 (-100 to +100)
                'strength': OrderStrength,
                'recommended_action': str
            }
        """
        try:
            if not self.openapi_client or not self.openapi_client.is_connected:
                return self._default_order_book_result()

            # Get order book data
            orderbook = self.openapi_client.get_orderbook(stock_code)

            if not orderbook:
                return self._default_order_book_result()

            # Calculate buy/sell pressure
            buy_volume = sum([level.get('quantity', 0) for level in orderbook.get('bids', [])])
            sell_volume = sum([level.get('quantity', 0) for level in orderbook.get('asks', [])])

            total_volume = buy_volume + sell_volume
            if total_volume == 0:
                return self._default_order_book_result()

            buy_pressure = (buy_volume / total_volume) * 100
            sell_pressure = (sell_volume / total_volume) * 100
            net_pressure = buy_pressure - sell_pressure

            # Determine strength
            strength = self._classify_order_strength(net_pressure)

            # Recommended action
            recommended_action = self._recommend_action_from_orderbook(net_pressure, strength)

            return {
                'buy_pressure': buy_pressure,
                'sell_pressure': sell_pressure,
                'net_pressure': net_pressure,
                'strength': strength,
                'recommended_action': recommended_action
            }

        except Exception as e:
            logger.error(f"호가창 분석 실패: {e}")
            return self._default_order_book_result()

    def _default_order_book_result(self) -> Dict:
        """Default result when order book is unavailable"""
        return {
            'buy_pressure': 50.0,
            'sell_pressure': 50.0,
            'net_pressure': 0.0,
            'strength': OrderStrength.NEUTRAL,
            'recommended_action': '데이터 부족 - 관망'
        }

    def _classify_order_strength(self, net_pressure: float) -> str:
        """Classify order strength based on net pressure"""
        if net_pressure > 30:
            return OrderStrength.VERY_STRONG_BUY
        elif net_pressure > 15:
            return OrderStrength.STRONG_BUY
        elif net_pressure > 5:
            return OrderStrength.WEAK_BUY
        elif net_pressure > -5:
            return OrderStrength.NEUTRAL
        elif net_pressure > -15:
            return OrderStrength.WEAK_SELL
        elif net_pressure > -30:
            return OrderStrength.STRONG_SELL
        else:
            return OrderStrength.VERY_STRONG_SELL

    def _recommend_action_from_orderbook(self, net_pressure: float, strength: str) -> str:
        """Recommend action based on orderbook analysis"""
        if strength in [OrderStrength.VERY_STRONG_BUY, OrderStrength.STRONG_BUY]:
            return f"매수 추천 (매수 압력 강함, {net_pressure:+.1f}%)"
        elif strength in [OrderStrength.VERY_STRONG_SELL, OrderStrength.STRONG_SELL]:
            return f"매도 추천 (매도 압력 강함, {net_pressure:+.1f}%)"
        elif strength == OrderStrength.WEAK_BUY:
            return "약한 매수 신호 - 관망 후 진입 고려"
        elif strength == OrderStrength.WEAK_SELL:
            return "약한 매도 신호 - 부분 매도 고려"
        else:
            return "중립 - 추가 신호 대기"

    def analyze_trading_time(self) -> Dict:
        """
        Analyze current trading time slot
        현재 거래 시간대 분석

        Returns:
            {
                'time_slot': TradingTimeSlot,
                'pattern': Dict,
                'recommendation': str
            }
        """
        now = datetime.now().time()

        # Determine time slot
        if time(9, 0) <= now < time(9, 30):
            time_slot = TradingTimeSlot.OPENING
        elif time(9, 30) <= now < time(11, 0):
            time_slot = TradingTimeSlot.MORNING
        elif time(11, 0) <= now < time(13, 0):
            time_slot = TradingTimeSlot.MIDDAY
        elif time(13, 0) <= now < time(14, 30):
            time_slot = TradingTimeSlot.AFTERNOON
        elif time(14, 30) <= now < time(15, 20):
            time_slot = TradingTimeSlot.CLOSING
        else:
            time_slot = "장 외 시간"

        pattern = self.time_patterns.get(time_slot, {})
        recommendation = self._generate_time_recommendation(time_slot, pattern)

        return {
            'time_slot': time_slot,
            'pattern': pattern,
            'recommendation': recommendation,
            'current_time': now.strftime('%H:%M:%S')
        }

    def _generate_time_recommendation(self, time_slot: str, pattern: Dict) -> str:
        """Generate recommendation based on time slot"""
        strategy = pattern.get('strategy', '')

        if time_slot == TradingTimeSlot.OPENING:
            return "🌅 장 시작: 변동성 큼, 급등/급락 주의, 관망 후 진입 추천"
        elif time_slot == TradingTimeSlot.MORNING:
            return "☀️ 오전장: 주 매매 시간, 거래량 많고 추세 형성"
        elif time_slot == TradingTimeSlot.MIDDAY:
            return "🌤️ 중간장: 거래량 감소, 추세 확인 및 포지션 조정"
        elif time_slot == TradingTimeSlot.AFTERNOON:
            return "🌆 오후장: 마감 전 포지션 정리 시작"
        elif time_slot == TradingTimeSlot.CLOSING:
            return "🌇 장 마감: 데이 트레이딩 청산, 익일 대비 포지션 조정"
        else:
            return "🌙 장 외 시간: 매매 불가, 전략 수립 및 분석"

    def optimize_entry_timing(self, stock_code: str, target_quantity: int) -> Dict:
        """
        Optimize entry timing (매수 타이밍 최적화)

        Args:
            stock_code: 종목 코드
            target_quantity: 목표 매수 수량

        Returns:
            {
                'strategy': str,           # 'immediate', 'split_3', 'split_5', 'wait'
                'split_plan': List[Dict],  # [{quantity, timing, reason}]
                'total_quantity': int,
                'reason': str
            }
        """
        # Analyze order book
        orderbook_analysis = self.analyze_order_book(stock_code)

        # Analyze time slot
        time_analysis = self.analyze_trading_time()

        # Decision logic
        net_pressure = orderbook_analysis['net_pressure']
        strength = orderbook_analysis['strength']
        time_slot = time_analysis['time_slot']

        # Very strong buy pressure -> immediate entry
        if strength == OrderStrength.VERY_STRONG_BUY and net_pressure > 40:
            return {
                'strategy': 'immediate',
                'split_plan': [
                    {'quantity': target_quantity, 'timing': '즉시', 'reason': '매우 강한 매수 압력'}
                ],
                'total_quantity': target_quantity,
                'reason': '강한 매수 신호 - 전량 즉시 매수'
            }

        # Strong buy but not overwhelming -> split into 3
        if strength in [OrderStrength.STRONG_BUY, OrderStrength.WEAK_BUY]:
            q1 = target_quantity // 3
            q2 = target_quantity // 3
            q3 = target_quantity - q1 - q2

            return {
                'strategy': 'split_3',
                'split_plan': [
                    {'quantity': q1, 'timing': '즉시', 'reason': '초기 진입'},
                    {'quantity': q2, 'timing': '5분 후', 'reason': '추세 확인 후 추가'},
                    {'quantity': q3, 'timing': '10분 후', 'reason': '평단가 최적화'}
                ],
                'total_quantity': target_quantity,
                'reason': '분할 매수로 리스크 분산'
            }

        # Neutral or weak -> wait or split into 5
        if strength == OrderStrength.NEUTRAL:
            q1 = target_quantity // 5
            q2 = target_quantity // 5
            q3 = target_quantity // 5
            q4 = target_quantity // 5
            q5 = target_quantity - q1 - q2 - q3 - q4

            return {
                'strategy': 'split_5',
                'split_plan': [
                    {'quantity': q1, 'timing': '즉시', 'reason': '테스트 진입'},
                    {'quantity': q2, 'timing': '3분 후', 'reason': '시장 반응 확인'},
                    {'quantity': q3, 'timing': '6분 후', 'reason': '추세 확인'},
                    {'quantity': q4, 'timing': '10분 후', 'reason': '평단가 조정'},
                    {'quantity': q5, 'timing': '15분 후', 'reason': '최종 진입'}
                ],
                'total_quantity': target_quantity,
                'reason': '세밀한 분할 매수로 최적 진입가 탐색'
            }

        # Sell pressure -> wait
        return {
            'strategy': 'wait',
            'split_plan': [],
            'total_quantity': 0,
            'reason': f'매도 압력 감지 ({net_pressure:+.1f}%) - 진입 대기'
        }

    def optimize_exit_timing(self, stock_code: str, current_quantity: int, entry_price: float, current_price: float) -> Dict:
        """
        Optimize exit timing (매도 타이밍 최적화)

        Args:
            stock_code: 종목 코드
            current_quantity: 보유 수량
            entry_price: 매수가
            current_price: 현재가

        Returns:
            {
                'strategy': str,           # 'hold', 'partial_exit', 'full_exit'
                'split_plan': List[Dict],  # [{quantity, timing, reason}]
                'reason': str
            }
        """
        # Calculate profit/loss
        profit_pct = ((current_price - entry_price) / entry_price) * 100

        # Analyze order book
        orderbook_analysis = self.analyze_order_book(stock_code)
        net_pressure = orderbook_analysis['net_pressure']
        strength = orderbook_analysis['strength']

        # Analyze time
        time_analysis = self.analyze_trading_time()
        time_slot = time_analysis['time_slot']

        # Decision logic

        # Strong sell pressure + profit -> take profit
        if strength in [OrderStrength.STRONG_SELL, OrderStrength.VERY_STRONG_SELL] and profit_pct > 2:
            return {
                'strategy': 'full_exit',
                'split_plan': [
                    {'quantity': current_quantity, 'timing': '즉시', 'reason': f'익절 실현 (+{profit_pct:.2f}%)'}
                ],
                'reason': '강한 매도 압력 + 수익 중 - 전량 익절'
            }

        # Moderate profit + weak sell -> partial exit
        if profit_pct > 5 and strength in [OrderStrength.WEAK_SELL, OrderStrength.NEUTRAL]:
            partial_quantity = current_quantity // 2
            remaining = current_quantity - partial_quantity

            return {
                'strategy': 'partial_exit',
                'split_plan': [
                    {'quantity': partial_quantity, 'timing': '즉시', 'reason': f'부분 익절 (+{profit_pct:.2f}%)'},
                    {'quantity': remaining, 'timing': '추가 상승 시', 'reason': '추가 수익 추구'}
                ],
                'reason': '부분 익절로 수익 실현 + 추가 상승 기대'
            }

        # Loss + strong sell -> cut loss
        if profit_pct < -3 and strength in [OrderStrength.STRONG_SELL, OrderStrength.VERY_STRONG_SELL]:
            return {
                'strategy': 'full_exit',
                'split_plan': [
                    {'quantity': current_quantity, 'timing': '즉시', 'reason': f'손절 ({profit_pct:.2f}%)'}
                ],
                'reason': '매도 압력 + 손실 중 - 손절'
            }

        # Closing time -> exit day trading
        if time_slot == TradingTimeSlot.CLOSING and profit_pct > 0:
            return {
                'strategy': 'full_exit',
                'split_plan': [
                    {'quantity': current_quantity, 'timing': '장 마감 전', 'reason': '데이 트레이딩 청산'}
                ],
                'reason': '장 마감 임박 - 익일 리스크 회피'
            }

        # Hold
        return {
            'strategy': 'hold',
            'split_plan': [],
            'reason': f'보유 유지 (손익: {profit_pct:+.2f}%, 압력: {net_pressure:+.1f}%)'
        }


# ==============================================================================
# Integration Example
# ==============================================================================

def integrate_with_bot(bot_instance):
    """
    Integrate Timing Optimizer with Trading Bot
    트레이딩 봇에 타이밍 최적화 시스템 통합

    Usage:
        optimizer = integrate_with_bot(bot_instance)
        result = optimizer.optimize_entry_timing('005930', 10)
        print(result)
    """
    openapi_client = bot_instance.openapi_client if hasattr(bot_instance, 'openapi_client') else None
    optimizer = TimingOptimizer(openapi_client)

    logger.info("✅ Timing Optimizer integrated with Trading Bot")
    return optimizer
