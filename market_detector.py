"""
Market Condition Detector & Auto Response System
시장 상황 자동 감지 및 대응 시스템

Features:
- 급등/급락 감지
- 거래량 폭증 감지
- 변동성 확대 감지
- 시장 국면 분류 (강세장/약세장/박스권/변동장)
- 자동 대응 (방어 모드 전환, 포지션 축소, 현금 비중 증가)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MarketCondition:
    """시장 상황 분류"""
    BULLISH = "강세장"      # Bull market
    BEARISH = "약세장"      # Bear market
    SIDEWAYS = "박스권"     # Sideways / Range-bound
    VOLATILE = "변동장"     # High volatility


class MarketAlert:
    """시장 경고 유형"""
    SURGE = "급등"          # Price surge
    PLUNGE = "급락"         # Price plunge
    VOLUME_SPIKE = "거래량폭증"   # Volume spike
    HIGH_VOLATILITY = "고변동성"  # High volatility
    TREND_CHANGE = "추세전환"     # Trend change


class MarketDetector:
    """
    Market Condition Detector
    시장 상황 자동 감지 시스템
    """

    def __init__(self, data_fetcher=None):
        """
        Initialize Market Detector

        Args:
            data_fetcher: DataFetcher instance for fetching market data
        """
        self.data_fetcher = data_fetcher

        # Detection thresholds
        self.surge_threshold = 5.0      # 5% 이상 상승 시 급등
        self.plunge_threshold = -5.0    # 5% 이상 하락 시 급락
        self.volume_spike_ratio = 3.0   # 평균 대비 3배 이상 시 거래량 폭증
        self.volatility_threshold = 0.03  # 3% 이상 일일 변동성

        # Market regime parameters
        self.trend_period = 20          # 추세 판단 기간 (일)
        self.volatility_period = 20     # 변동성 계산 기간

    def detect_market_condition(self, stock_code: str) -> Dict:
        """
        Detect current market condition
        현재 시장 상황 감지

        Args:
            stock_code: 종목 코드

        Returns:
            {
                'condition': MarketCondition,
                'alerts': List[MarketAlert],
                'metrics': Dict,
                'recommendation': str
            }
        """
        try:
            # Fetch recent price data
            data = self._fetch_market_data(stock_code)

            if not data or len(data) < self.trend_period:
                return {
                    'condition': None,
                    'alerts': [],
                    'metrics': {},
                    'recommendation': '데이터 부족'
                }

            # Calculate metrics
            metrics = self._calculate_metrics(data)

            # Detect market condition
            condition = self._classify_market_condition(metrics)

            # Detect alerts
            alerts = self._detect_alerts(metrics)

            # Generate recommendation
            recommendation = self._generate_recommendation(condition, alerts, metrics)

            return {
                'condition': condition,
                'alerts': alerts,
                'metrics': metrics,
                'recommendation': recommendation
            }

        except Exception as e:
            logger.error(f"❌ Market detection failed for {stock_code}: {e}")
            return {
                'condition': None,
                'alerts': [],
                'metrics': {},
                'recommendation': '감지 실패'
            }

    def _fetch_market_data(self, stock_code: str) -> List[Dict]:
        """Fetch market data for analysis"""
        if not self.data_fetcher:
            return []

        try:
            # Fetch recent 60 days of data
            data = self.data_fetcher.get_daily_price(stock_code, days=60)
            return data
        except Exception as e:
            logger.error(f"데이터 가져오기 실패: {e}")
            return []

    def _calculate_metrics(self, data: List[Dict]) -> Dict:
        """
        Calculate market metrics
        시장 지표 계산
        """
        df = pd.DataFrame(data)

        # Price changes
        df['close'] = df['close'].astype(float)
        df['daily_return'] = df['close'].pct_change() * 100

        # Volume
        df['volume'] = df.get('volume', pd.Series([0] * len(df))).astype(float)
        volume_avg = df['volume'].rolling(window=20).mean()

        # Volatility
        volatility = df['daily_return'].rolling(window=self.volatility_period).std()

        # Trend (SMA 20, 60)
        sma_20 = df['close'].rolling(window=20).mean()
        sma_60 = df['close'].rolling(window=60).mean() if len(df) >= 60 else None

        # Latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        metrics = {
            'current_price': float(latest['close']),
            'daily_change': float(latest['daily_return']) if not pd.isna(latest['daily_return']) else 0.0,
            'volume': float(latest['volume']),
            'volume_avg': float(volume_avg.iloc[-1]) if not pd.isna(volume_avg.iloc[-1]) else 1.0,
            'volume_ratio': float(latest['volume'] / volume_avg.iloc[-1]) if not pd.isna(volume_avg.iloc[-1]) and volume_avg.iloc[-1] > 0 else 1.0,
            'volatility': float(volatility.iloc[-1]) if not pd.isna(volatility.iloc[-1]) else 0.0,
            'sma_20': float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else 0.0,
            'sma_60': float(sma_60.iloc[-1]) if sma_60 is not None and not pd.isna(sma_60.iloc[-1]) else 0.0,
            'trend_20': 'up' if latest['close'] > sma_20.iloc[-1] else 'down' if not pd.isna(sma_20.iloc[-1]) else 'neutral',
            'trend_60': 'up' if sma_60 is not None and latest['close'] > sma_60.iloc[-1] else 'down' if sma_60 is not None and not pd.isna(sma_60.iloc[-1]) else 'neutral',
        }

        return metrics

    def _classify_market_condition(self, metrics: Dict) -> str:
        """
        Classify market condition
        시장 국면 분류
        """
        price = metrics['current_price']
        sma_20 = metrics['sma_20']
        sma_60 = metrics['sma_60']
        volatility = metrics['volatility']
        daily_change = metrics['daily_change']

        # High volatility market
        if volatility > self.volatility_threshold:
            return MarketCondition.VOLATILE

        # Bullish market (강세장)
        if sma_20 > 0 and sma_60 > 0:
            if price > sma_20 > sma_60 and daily_change > 0:
                return MarketCondition.BULLISH

        # Bearish market (약세장)
        if sma_20 > 0 and sma_60 > 0:
            if price < sma_20 < sma_60 and daily_change < 0:
                return MarketCondition.BEARISH

        # Sideways market (박스권)
        return MarketCondition.SIDEWAYS

    def _detect_alerts(self, metrics: Dict) -> List[str]:
        """
        Detect market alerts
        시장 경고 감지
        """
        alerts = []

        daily_change = metrics['daily_change']
        volume_ratio = metrics['volume_ratio']
        volatility = metrics['volatility']

        # 급등 감지
        if daily_change >= self.surge_threshold:
            alerts.append(MarketAlert.SURGE)

        # 급락 감지
        if daily_change <= self.plunge_threshold:
            alerts.append(MarketAlert.PLUNGE)

        # 거래량 폭증 감지
        if volume_ratio >= self.volume_spike_ratio:
            alerts.append(MarketAlert.VOLUME_SPIKE)

        # 고변동성 감지
        if volatility > self.volatility_threshold:
            alerts.append(MarketAlert.HIGH_VOLATILITY)

        # 추세 전환 감지
        if metrics['trend_20'] != metrics['trend_60']:
            alerts.append(MarketAlert.TREND_CHANGE)

        return alerts

    def _generate_recommendation(self, condition: str, alerts: List[str], metrics: Dict) -> str:
        """
        Generate trading recommendation
        거래 추천 생성
        """
        # High risk conditions
        if MarketAlert.PLUNGE in alerts or MarketAlert.HIGH_VOLATILITY in alerts:
            return "🛡️ 방어 모드: 포지션 축소 및 손절 타이트하게 관리"

        if condition == MarketCondition.BEARISH:
            return "⚠️ 약세장: 현금 비중 증가, 신규 매수 자제"

        if MarketAlert.SURGE in alerts and MarketAlert.VOLUME_SPIKE in alerts:
            return "🚀 매수 기회: 강한 상승 추세 + 거래량 증가"

        if condition == MarketCondition.BULLISH:
            return "📈 강세장: 정상 운영, 추세 추종 전략 유지"

        if condition == MarketCondition.SIDEWAYS:
            return "➡️ 박스권: 단기 매매 전략, 상하단 대응"

        if condition == MarketCondition.VOLATILE:
            return "⚡ 변동장: 변동성 전략, 리스크 관리 강화"

        return "🔄 정상 운영"

    def auto_response(self, stock_code: str, current_positions: List[Dict]) -> Dict:
        """
        Auto response to market condition
        시장 상황에 따른 자동 대응

        Args:
            stock_code: 종목 코드
            current_positions: 현재 보유 포지션 목록

        Returns:
            {
                'action': str,  # 'reduce_position', 'increase_cash', 'tighten_stop', 'normal'
                'suggested_ratio': float,  # 조정 비율
                'reason': str
            }
        """
        detection = self.detect_market_condition(stock_code)
        condition = detection['condition']
        alerts = detection['alerts']

        # Emergency response (급락 또는 고변동성)
        if MarketAlert.PLUNGE in alerts or MarketAlert.HIGH_VOLATILITY in alerts:
            return {
                'action': 'reduce_position',
                'suggested_ratio': 0.5,  # 50% 포지션 축소
                'reason': '급락 또는 고변동성 감지 - 긴급 리스크 관리'
            }

        # Bearish market (약세장)
        if condition == MarketCondition.BEARISH:
            return {
                'action': 'increase_cash',
                'suggested_ratio': 0.7,  # 현금 70% 유지
                'reason': '약세장 진입 - 현금 비중 증가'
            }

        # Volatile market (변동장)
        if condition == MarketCondition.VOLATILE:
            return {
                'action': 'tighten_stop',
                'suggested_ratio': 0.02,  # 손절 2%로 축소
                'reason': '변동장 - 손절 타이트하게 관리'
            }

        # Bullish market (강세장)
        if condition == MarketCondition.BULLISH:
            return {
                'action': 'normal',
                'suggested_ratio': 1.0,
                'reason': '강세장 - 정상 운영'
            }

        return {
            'action': 'normal',
            'suggested_ratio': 1.0,
            'reason': '정상 시장 상황'
        }


# ==============================================================================
# Integration Example
# ==============================================================================

def integrate_with_bot(bot_instance):
    """
    Integrate Market Detector with Trading Bot
    트레이딩 봇에 시장 감지 시스템 통합

    Usage:
        detector = integrate_with_bot(bot_instance)
        result = detector.detect_market_condition('005930')
        print(result)
    """
    detector = MarketDetector(bot_instance.data_fetcher if hasattr(bot_instance, 'data_fetcher') else None)

    logger.info("✅ Market Detector integrated with Trading Bot")
    return detector
