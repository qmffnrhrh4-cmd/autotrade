"""
research/market_analyzer.py
Market Condition Analyzer - 시장 전체 상황 분석

Features:
- KOSPI/KOSDAQ index trend analysis
- Sector strength analysis
- Stock momentum vs market momentum comparison
- Fear & Greed index calculation
- Trading signal light (Green/Yellow/Red)
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from utils.logger_new import get_logger


logger = get_logger()


class MarketSignal(Enum):
    """시장 신호등"""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class MarketCondition:
    """시장 상태"""
    signal: MarketSignal
    kospi_trend: str
    kosdaq_trend: str
    fear_greed_index: float
    sector_strength: Dict[str, float]
    momentum_score: float
    recommendation: str
    timestamp: datetime


class MarketAnalyzer:
    """시장 전체 상황 분석기"""

    def __init__(self, market_api):
        """
        초기화

        Args:
            market_api: 시장 데이터 API
        """
        self.market_api = market_api
        self.last_analysis = None
        self.analysis_cache_ttl = 60

        logger.info("시장 분석기 초기화 완료")

    def analyze_market(self) -> MarketCondition:
        """
        시장 전체 분석

        Returns:
            MarketCondition 객체
        """
        try:
            if self._is_cache_valid():
                return self.last_analysis

            kospi_trend = self._analyze_index_trend('001')
            kosdaq_trend = self._analyze_index_trend('101')

            fear_greed = self._calculate_fear_greed_index(kospi_trend, kosdaq_trend)

            sector_strength = self._analyze_sector_strength()

            momentum = self._calculate_market_momentum(
                kospi_trend,
                kosdaq_trend,
                sector_strength
            )

            signal = self._determine_signal(
                kospi_trend,
                kosdaq_trend,
                fear_greed,
                momentum
            )

            recommendation = self._generate_recommendation(signal, fear_greed, momentum)

            condition = MarketCondition(
                signal=signal,
                kospi_trend=kospi_trend['trend'],
                kosdaq_trend=kosdaq_trend['trend'],
                fear_greed_index=fear_greed,
                sector_strength=sector_strength,
                momentum_score=momentum,
                recommendation=recommendation,
                timestamp=datetime.now()
            )

            self.last_analysis = condition

            logger.info(
                f"시장 분석 완료: 신호={signal.value}, "
                f"공포/탐욕={fear_greed:.1f}, 모멘텀={momentum:.1f}"
            )

            return condition

        except Exception as e:
            logger.error(f"시장 분석 실패: {e}", exc_info=True)
            return self._get_default_condition()

    def _analyze_index_trend(self, index_code: str) -> Dict[str, Any]:
        """지수 추세 분석"""
        try:
            index_data = self.market_api.get_index_data(index_code)

            if not index_data:
                return {'trend': 'neutral', 'change': 0.0, 'volume_ratio': 1.0}

            change_rate = float(index_data.get('change_rate', 0))
            volume = int(index_data.get('volume', 0))
            avg_volume = int(index_data.get('avg_volume', volume))

            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0

            if change_rate > 1.5 and volume_ratio > 1.2:
                trend = 'strong_bullish'
            elif change_rate > 0.5:
                trend = 'bullish'
            elif change_rate < -1.5 and volume_ratio > 1.2:
                trend = 'strong_bearish'
            elif change_rate < -0.5:
                trend = 'bearish'
            else:
                trend = 'neutral'

            return {
                'trend': trend,
                'change': change_rate,
                'volume_ratio': volume_ratio
            }

        except Exception as e:
            logger.debug(f"지수 추세 분석 실패: {e}")
            return {'trend': 'neutral', 'change': 0.0, 'volume_ratio': 1.0}

    def _calculate_fear_greed_index(
        self,
        kospi_trend: Dict,
        kosdaq_trend: Dict
    ) -> float:
        """
        공포/탐욕 지수 계산 (0-100)
        0 = 극단적 공포, 50 = 중립, 100 = 극단적 탐욕
        """
        kospi_change = kospi_trend.get('change', 0)
        kosdaq_change = kosdaq_trend.get('change', 0)
        kospi_volume = kospi_trend.get('volume_ratio', 1.0)
        kosdaq_volume = kosdaq_trend.get('volume_ratio', 1.0)

        change_score = ((kospi_change + kosdaq_change) / 2) * 10
        volume_score = ((kospi_volume + kosdaq_volume) / 2 - 1) * 20

        base_score = 50
        final_score = base_score + change_score + volume_score

        return max(0, min(100, final_score))

    def _analyze_sector_strength(self) -> Dict[str, float]:
        """업종별 강도 분석"""
        sectors = {
            'technology': 0.0,
            'finance': 0.0,
            'bio': 0.0,
            'automobile': 0.0,
            'semiconductor': 0.0
        }

        try:
            sector_codes = {
                'technology': 'IT',
                'finance': 'FIN',
                'bio': 'BIO',
                'automobile': 'AUTO',
                'semiconductor': 'SEMI'
            }

            for sector_name, sector_code in sector_codes.items():
                try:
                    sector_data = self.market_api.get_sector_data(sector_code)
                    if sector_data:
                        change = float(sector_data.get('change_rate', 0))
                        volume_ratio = float(sector_data.get('volume_ratio', 1.0))
                        strength = (change * 0.7) + ((volume_ratio - 1) * 100 * 0.3)
                        sectors[sector_name] = strength
                except:
                    continue

        except Exception as e:
            logger.debug(f"업종 강도 분석 실패: {e}")

        return sectors

    def _calculate_market_momentum(
        self,
        kospi_trend: Dict,
        kosdaq_trend: Dict,
        sector_strength: Dict[str, float]
    ) -> float:
        """
        시장 모멘텀 점수 계산 (-100 ~ +100)
        """
        kospi_score = kospi_trend.get('change', 0) * 10
        kosdaq_score = kosdaq_trend.get('change', 0) * 10

        sector_avg = sum(sector_strength.values()) / len(sector_strength) if sector_strength else 0

        momentum = (kospi_score * 0.4) + (kosdaq_score * 0.4) + (sector_avg * 0.2)

        return max(-100, min(100, momentum))

    def _determine_signal(
        self,
        kospi_trend: Dict,
        kosdaq_trend: Dict,
        fear_greed: float,
        momentum: float
    ) -> MarketSignal:
        """신호등 결정"""

        if fear_greed > 70 and momentum > 30:
            return MarketSignal.GREEN
        elif fear_greed < 30 and momentum < -30:
            return MarketSignal.RED
        elif 40 <= fear_greed <= 60 and -20 <= momentum <= 20:
            return MarketSignal.YELLOW
        elif fear_greed > 50 and momentum > 0:
            return MarketSignal.GREEN
        elif fear_greed < 50 and momentum < 0:
            return MarketSignal.RED
        else:
            return MarketSignal.YELLOW

    def _generate_recommendation(
        self,
        signal: MarketSignal,
        fear_greed: float,
        momentum: float
    ) -> str:
        """매매 추천 생성"""

        if signal == MarketSignal.GREEN:
            if fear_greed > 80:
                return "강세장: 적극 매수 (과열 주의)"
            else:
                return "강세장: 적극 매수"

        elif signal == MarketSignal.RED:
            if fear_greed < 20:
                return "약세장: 관망 또는 손절 (반등 기회 주시)"
            else:
                return "약세장: 관망 또는 손절"

        else:
            if momentum > 0:
                return "중립: 선별 매수"
            elif momentum < 0:
                return "중립: 보수적 관망"
            else:
                return "중립: 관망"

    def _is_cache_valid(self) -> bool:
        """캐시 유효성 확인"""
        if not self.last_analysis:
            return False

        elapsed = (datetime.now() - self.last_analysis.timestamp).seconds
        return elapsed < self.analysis_cache_ttl

    def _get_default_condition(self) -> MarketCondition:
        """기본 시장 상태"""
        return MarketCondition(
            signal=MarketSignal.YELLOW,
            kospi_trend='neutral',
            kosdaq_trend='neutral',
            fear_greed_index=50.0,
            sector_strength={},
            momentum_score=0.0,
            recommendation="분석 불가: 관망",
            timestamp=datetime.now()
        )

    def compare_stock_momentum(
        self,
        stock_change_rate: float,
        market_condition: MarketCondition
    ) -> Dict[str, Any]:
        """개별 종목 모멘텀 vs 시장 모멘텀 비교"""

        market_avg_change = (
            market_condition.momentum_score / 10
        )

        relative_strength = stock_change_rate - market_avg_change

        if relative_strength > 3.0:
            category = 'very_strong'
        elif relative_strength > 1.0:
            category = 'strong'
        elif relative_strength > -1.0:
            category = 'normal'
        elif relative_strength > -3.0:
            category = 'weak'
        else:
            category = 'very_weak'

        return {
            'stock_change': stock_change_rate,
            'market_avg_change': market_avg_change,
            'relative_strength': relative_strength,
            'category': category
        }


__all__ = ['MarketAnalyzer', 'MarketCondition', 'MarketSignal']
