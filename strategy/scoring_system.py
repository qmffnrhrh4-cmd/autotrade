"""
strategy/scoring_system.py
10가지 기준 스코어링 시스템 (440점 만점)

Enhanced Features:
- Time-based dynamic weight adjustment
- Risk score integration
- Virtual trading performance feedback
- Historical performance tracking
- Market condition adaptation
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time as dt_time
from pathlib import Path
import hashlib
import json
import yaml

from utils.logger_new import get_logger
from utils.data_cache import get_api_cache
from config.manager import get_config


logger = get_logger()


@dataclass
class ScoringResult:
    """스코어링 결과"""

    total_score: float = 0.0
    max_score: float = 440.0
    percentage: float = 0.0

    volume_surge_score: float = 0.0
    price_momentum_score: float = 0.0
    institutional_buying_score: float = 0.0
    bid_strength_score: float = 0.0
    execution_intensity_score: float = 0.0
    broker_activity_score: float = 0.0
    program_trading_score: float = 0.0
    technical_indicators_score: float = 0.0
    theme_news_score: float = 0.0
    volatility_pattern_score: float = 0.0

    risk_score: float = 0.0
    time_adjusted_score: float = 0.0
    historical_performance_score: float = 0.0

    details: Dict[str, Any] = field(default_factory=dict)

    def calculate_percentage(self):
        """퍼센티지 계산"""
        self.percentage = (self.total_score / self.max_score) * 100 if self.max_score > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'total_score': self.total_score,
            'max_score': self.max_score,
            'percentage': self.percentage,
            'breakdown': {
                'volume_surge': self.volume_surge_score,
                'price_momentum': self.price_momentum_score,
                'institutional_buying': self.institutional_buying_score,
                'bid_strength': self.bid_strength_score,
                'execution_intensity': self.execution_intensity_score,
                'broker_activity': self.broker_activity_score,
                'program_trading': self.program_trading_score,
                'technical_indicators': self.technical_indicators_score,
                'theme_news': self.theme_news_score,
                'volatility_pattern': self.volatility_pattern_score,
            },
            'details': self.details,
        }


class ScoringSystem:
    """10가지 기준 스코어링 시스템"""

    def __init__(
        self,
        market_api=None,
        enable_cache: bool = True,
        risk_manager=None,
        performance_tracker=None
    ):
        """
        초기화

        Args:
            market_api: 시장 데이터 API (선택)
            enable_cache: 캐싱 활성화 여부 (기본 True)
            risk_manager: 리스크 관리자 (선택)
            performance_tracker: 가상매매 성과 추적기 (선택)
        """
        self.market_api = market_api
        self.risk_manager = risk_manager
        self.performance_tracker = performance_tracker

        self.config = get_config()
        self.scoring_config = self.config.scoring
        self.criteria_config = self.scoring_config.get('criteria', {})

        self.enable_cache = enable_cache
        self.cache_manager = get_api_cache() if enable_cache else None
        self.cache_ttl = 30

        self.stock_history = {}
        self._load_historical_data()

        logger.info("📊 10가지 기준 스코어링 시스템 초기화 완료")

        # YAML 설정 파일에서 가중치 로드
        self._load_scoring_weights_from_yaml()

    def _load_scoring_weights_from_yaml(self) -> None:
        """
        YAML 설정 파일에서 가중치 로드
        파일이 없을 경우 기본값 사용
        """
        yaml_path = Path('config/scoring_weights.yaml')

        # 기본 가중치 (fallback)
        default_time_based_weights = {
            'early': {
                'volume_surge': 1.5,
                'execution_intensity': 1.3,
                'program_trading': 1.2,
                'price_momentum': 0.9,
            },
            'mid': {
                'price_momentum': 1.2,
                'institutional_buying': 1.3,
                'technical_indicators': 1.1,
                'volatility_pattern': 0.9,
            },
            'late': {
                'price_momentum': 1.4,
                'technical_indicators': 1.2,
                'volatility_pattern': 1.3,
                'volume_surge': 0.8,
            }
        }

        default_scan_type_weights = {
            'volume_based': {
                'volume_surge': 1.5,
                'price_momentum': 0.8,
                'institutional_buying': 1.0,
                'bid_strength': 1.3,
                'execution_intensity': 1.5,
                'broker_activity': 1.1,
                'program_trading': 1.0,
                'technical_indicators': 0.7,
                'theme_news': 0.9,
                'volatility_pattern': 1.0,
            },
            'price_change': {
                'volume_surge': 0.9,
                'price_momentum': 1.5,
                'institutional_buying': 1.0,
                'bid_strength': 0.8,
                'execution_intensity': 0.9,
                'broker_activity': 1.0,
                'program_trading': 1.0,
                'technical_indicators': 1.4,
                'theme_news': 1.2,
                'volatility_pattern': 1.3,
            },
            'ai_driven': {
                'volume_surge': 1.0,
                'price_momentum': 1.0,
                'institutional_buying': 1.5,
                'bid_strength': 1.1,
                'execution_intensity': 1.2,
                'broker_activity': 1.5,
                'program_trading': 1.5,
                'technical_indicators': 1.1,
                'theme_news': 1.3,
                'volatility_pattern': 0.9,
            },
            'default': {
                'volume_surge': 1.0,
                'price_momentum': 1.0,
                'institutional_buying': 1.0,
                'bid_strength': 1.0,
                'execution_intensity': 1.0,
                'broker_activity': 1.0,
                'program_trading': 1.0,
                'technical_indicators': 1.0,
                'theme_news': 1.0,
                'volatility_pattern': 1.0,
            },
        }

        try:
            if yaml_path.exists():
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f)

                # YAML에서 가중치 로드
                self.time_based_weights = yaml_config.get('time_based_weights', default_time_based_weights)
                self.scan_type_weights = yaml_config.get('scan_type_weights', default_scan_type_weights)

                logger.info(f"✅ YAML 설정 파일 로드 성공: {yaml_path}")
            else:
                # YAML 파일이 없으면 기본값 사용
                self.time_based_weights = default_time_based_weights
                self.scan_type_weights = default_scan_type_weights

                logger.warning(f"⚠️ YAML 설정 파일 없음, 기본값 사용: {yaml_path}")

        except Exception as e:
            # YAML 로드 실패 시 기본값 사용
            self.time_based_weights = default_time_based_weights
            self.scan_type_weights = default_scan_type_weights

            logger.error(f"❌ YAML 파일 로드 실패, 기본값 사용: {e}")

    def _generate_cache_key(self, stock_data: Dict[str, Any], scan_type: str) -> str:
        """
        캐시 키 생성

        Args:
            stock_data: 종목 데이터
            scan_type: 스캔 타입

        Returns:
            캐시 키
        """
        # 종목코드 + 가격 + 거래량 + 스캔타입으로 키 생성
        key_data = {
            'code': stock_data.get('stock_code', ''),
            'price': stock_data.get('current_price', 0),
            'volume': stock_data.get('volume', 0),
            'scan_type': scan_type
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"score:{hashlib.md5(key_str.encode()).hexdigest()}"

    def calculate_score(self, stock_data: Dict[str, Any], scan_type: str = 'default') -> ScoringResult:
        """
        종목 종합 점수 계산

        Args:
            stock_data: 종목 데이터
            scan_type: 스캔 타입 ('volume_based', 'price_change', 'ai_driven', 'default')

        Returns:
            ScoringResult 객체
        """
        if self.enable_cache and self.cache_manager:
            cache_key = self._generate_cache_key(stock_data, scan_type)
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"캐시 히트: {stock_data.get('stock_code', 'unknown')}")
                return cached_result

        result = ScoringResult()

        weights = self.scan_type_weights.get(scan_type, self.scan_type_weights['default'])

        time_weights = self._get_time_based_weights()
        for key in time_weights:
            if key in weights:
                weights[key] *= time_weights[key]

        # 1. 거래량 급증 (60점)
        result.volume_surge_score = self._score_volume_surge(stock_data) * weights['volume_surge']

        # 2. 가격 모멘텀 (60점)
        result.price_momentum_score = self._score_price_momentum(stock_data) * weights['price_momentum']

        # 3. 기관 매수세 (60점)
        result.institutional_buying_score = self._score_institutional_buying(stock_data) * weights['institutional_buying']

        # 4. 매수 호가 강도 (40점)
        result.bid_strength_score = self._score_bid_strength(stock_data) * weights['bid_strength']

        # 5. 체결 강도 (40점)
        result.execution_intensity_score = self._score_execution_intensity(stock_data) * weights['execution_intensity']

        # 6. 주요 증권사 활동 (40점)
        result.broker_activity_score = self._score_broker_activity(stock_data) * weights['broker_activity']

        # 7. 프로그램 매매 (40점)
        result.program_trading_score = self._score_program_trading(stock_data) * weights['program_trading']

        # 8. 기술적 지표 (40점)
        result.technical_indicators_score = self._score_technical_indicators(stock_data) * weights['technical_indicators']

        # 9. 시장 모멘텀 (40점)
        result.theme_news_score = self._score_market_momentum(stock_data) * weights['theme_news']

        # 10. 변동성 패턴 (20점)
        result.volatility_pattern_score = self._score_volatility_pattern(stock_data) * weights['volatility_pattern']

        base_score = (
            result.volume_surge_score +
            result.price_momentum_score +
            result.institutional_buying_score +
            result.bid_strength_score +
            result.execution_intensity_score +
            result.broker_activity_score +
            result.program_trading_score +
            result.technical_indicators_score +
            result.theme_news_score +
            result.volatility_pattern_score
        )

        result.risk_score = self._calculate_risk_score(stock_data)
        result.historical_performance_score = self._get_historical_performance_score(
            stock_data.get('stock_code', '')
        )

        result.total_score = base_score + result.risk_score + result.historical_performance_score
        result.time_adjusted_score = result.total_score

        result.calculate_percentage()

        if self.enable_cache and self.cache_manager:
            cache_key = self._generate_cache_key(stock_data, scan_type)
            self.cache_manager.set(cache_key, result, ttl_seconds=self.cache_ttl)
        scan_type_display = {
            'volume_based': '거래량 기반',
            'price_change': '상승률 기반',
            'ai_driven': 'AI 기반',
            'default': '기본'
        }.get(scan_type, scan_type)

        logger.info(
            f"📊 스코어링 완료 [{scan_type_display}]: {stock_data.get('name', stock_data.get('code', 'Unknown'))} "
            f"총점 {result.total_score:.1f}/{result.max_score} ({result.percentage:.1f}%)"
        )

        return result

    def calculate_scores_parallel(
        self,
        stocks_data: List[Dict[str, Any]],
        scan_type: str = 'default',
        max_workers: int = 4
    ) -> List[Dict[str, Any]]:
        """
        다중 종목 병렬 스코어링

        Args:
            stocks_data: 종목 데이터 리스트
            scan_type: 스캔 타입
            max_workers: 최대 워커 수 (기본 4)

        Returns:
            스코어링 결과 리스트 (원본 데이터 + 점수)
        """
        if not stocks_data:
            return []

        results = []

        # 단일 종목이면 병렬 처리 불필요
        if len(stocks_data) == 1:
            stock = stocks_data[0]
            score = self.calculate_score(stock, scan_type)
            stock['scoring_result'] = score
            return stocks_data

        logger.info(f"🚀 병렬 스코어링 시작: {len(stocks_data)}개 종목 (워커 {max_workers}개)")

        # 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 작업 제출
            future_to_stock = {
                executor.submit(self.calculate_score, stock, scan_type): stock
                for stock in stocks_data
            }

            # 결과 수집
            for future in as_completed(future_to_stock):
                stock = future_to_stock[future]
                try:
                    score = future.result()
                    stock['scoring_result'] = score
                    results.append(stock)
                except Exception as e:
                    logger.error(f"스코어링 실패: {stock.get('name', 'Unknown')} - {e}")
                    # 실패한 종목도 포함 (점수 0)
                    stock['scoring_result'] = ScoringResult()
                    results.append(stock)

        # 원래 순서 유지를 위해 정렬
        results.sort(key=lambda x: stocks_data.index(x) if x in stocks_data else 999)

        logger.info(f"✅ 병렬 스코어링 완료: {len(results)}개 종목")

        return results

    def _score_volume_surge(self, stock_data: Dict[str, Any]) -> float:
        """
        1. 거래량 급증 점수 (60점)

        Args:
            stock_data: 종목 데이터

        Returns:
            점수 (0~60)
        """
        config = self.criteria_config.get('volume_surge', {})
        max_score = config.get('weight', 60)

        volume = stock_data.get('volume', 0)
        avg_volume = stock_data.get('avg_volume', None)

        stock_code = stock_data.get('stock_code', 'Unknown')

        # avg_volume이 있으면 비율 계산
        if avg_volume and avg_volume > 0:
            volume_ratio = volume / avg_volume

            if volume_ratio >= 5.0:
                return max_score
            elif volume_ratio >= 3.0:
                score = max_score * 0.75
                return score
            elif volume_ratio >= 2.0:
                score = max_score * 0.5
                return score
            elif volume_ratio >= 1.0:
                score = max_score * 0.25
                return score
            else:
                return 0.0

        # avg_volume이 없으면 절대값 기준

        if volume >= 5_000_000:
            score = max_score * 0.8
            return score
        elif volume >= 2_000_000:
            score = max_score * 0.6
            return score
        elif volume >= 1_000_000:
            score = max_score * 0.4
            return score
        elif volume >= 500_000:
            score = max_score * 0.2
            return score

        return 0.0

    def _score_price_momentum(self, stock_data: Dict[str, Any]) -> float:
        """
        2. 가격 모멘텀 점수 (60점)

        Args:
            stock_data: 종목 데이터

        Returns:
            점수 (0~60)
        """
        config = self.criteria_config.get('price_momentum', {})
        max_score = config.get('weight', 60)

        # change_rate를 % 단위로 받음 (예: 3.5는 3.5%)
        change_rate = stock_data.get('change_rate', stock_data.get('rate', 0.0))

        # 상승률 기준 점수 (강화)
        if change_rate >= 10.0:  # 10% 이상
            return max_score
        elif change_rate >= 7.0:  # 7% 이상
            return max_score * 0.85
        elif change_rate >= 5.0:  # 5% 이상
            return max_score * 0.7
        elif change_rate >= 3.0:  # 3% 이상
            return max_score * 0.55
        elif change_rate >= 2.0:  # 2% 이상
            return max_score * 0.4
        elif change_rate >= 1.0:  # 1% 이상
            return max_score * 0.25
        else:
            return 0.0

    def _score_institutional_buying(self, stock_data: Dict[str, Any]) -> float:
        """
        3. 기관 매수세 점수 (60점)

        - institutional_net_buy (일별, ka10008): 40점
        - foreign_net_buy (일별, ka10008): 10점
        - institutional_trend (5일 추이, ka10045): 10점 ⭐ NEW

        Args:
            stock_data: 종목 데이터

        Returns:
            점수 (0~60)
        """
        config = self.criteria_config.get('institutional_buying', {})
        max_score = config.get('weight', 60)

        institutional_net_buy = stock_data.get('institutional_net_buy', 0)
        foreign_net_buy = stock_data.get('foreign_net_buy', 0)
        institutional_trend = stock_data.get('institutional_trend', None)

        min_net_buy = config.get('min_net_buy', 10_000_000)

        stock_code = stock_data.get('stock_code', 'Unknown')

        score = 0.0
        score_details = []

        # 1) 기관 순매수 - 일별 (40점)
        if institutional_net_buy >= min_net_buy * 5:
            score += 40.0
            score_details.append("기관+40")
        elif institutional_net_buy >= min_net_buy * 3:
            score += 30.0
            score_details.append("기관+30")
        elif institutional_net_buy >= min_net_buy:
            score += 20.0
            score_details.append("기관+20")

        # 2) 외국인 순매수 - 일별 (10점)
        if foreign_net_buy >= min_net_buy:
            score += 10.0
            score_details.append("외국인+10")
        elif foreign_net_buy >= min_net_buy * 0.5:
            score += 5.0
            score_details.append("외국인+5")

        # 3) 기관/외국인 매매 추이 - 5일 (10점)
        if institutional_trend:
            trend_score = 0.0
            try:
                for key, values in institutional_trend.items():
                    if isinstance(values, list) and len(values) > 0:
                        recent = values[0]

                        orgn_net = recent.get('orgn_netslmt', '0')
                        if orgn_net and not str(orgn_net).startswith('-'):
                            trend_score += 5.0

                        for_net = recent.get('for_netslmt', '0')
                        if for_net and not str(for_net).startswith('-'):
                            trend_score += 5.0

                        break

                if trend_score > 0:
                    score += trend_score
                    score_details.append(f"추이+{trend_score:.0f}")
            except Exception as e:
                logger.debug(f"institutional_trend 파싱 실패: {e}")

        final_score = min(score, max_score)
        if score_details:
        else:

        return final_score

    def _score_bid_strength(self, stock_data: Dict[str, Any]) -> float:
        """
        4. 매수 호가 강도 점수 (40점)

        Args:
            stock_data: 종목 데이터

        Returns:
            점수 (0~40)
        """
        config = self.criteria_config.get('bid_strength', {})
        max_score = config.get('weight', 40)

        bid_ask_ratio = stock_data.get('bid_ask_ratio', 0.0)

        # 호가비율 기준 (매수호가/매도호가)
        # 1.0 이상 = 매수 우위, 1.0 미만 = 매도 우위
        if bid_ask_ratio >= 1.5:  # 강한 매수 우위
            return max_score
        elif bid_ask_ratio >= 1.2:  # 매수 우위
            return max_score * 0.75
        elif bid_ask_ratio >= 0.8:  # 균형 (약간 매도 우위)
            return max_score * 0.5
        elif bid_ask_ratio >= 0.5:  # 매도 우위
            return max_score * 0.25
        else:  # 강한 매도 우위
            return 0.0

    def _score_execution_intensity(self, stock_data: Dict[str, Any]) -> float:
        """
        5. 체결 강도 점수 (40점)

        ka10047 API로 수집한 실제 체결강도 값 사용

        Args:
            stock_data: 종목 데이터

        Returns:
            점수 (0~40)
        """
        config = self.criteria_config.get('execution_intensity', {})
        max_score = config.get('weight', 40)

        execution_intensity = stock_data.get('execution_intensity')

        # 디버그: 체결강도 값 확인
        stock_code = stock_data.get('stock_code', 'Unknown')

        # execution_intensity 데이터가 없으면 0점
        if execution_intensity is None or execution_intensity == 0:
            return 0.0

        # 체결강도 기준 점수 계산
        config = self.criteria_config.get('execution_intensity', {})
        min_value = config.get('min_value', 50)

        if execution_intensity >= min_value * 3.0:  # 150 이상
            score = max_score
        elif execution_intensity >= min_value * 2.0:  # 100 이상
            score = max_score * 0.75
        elif execution_intensity >= min_value * 1.4:  # 70 이상
            score = max_score * 0.5
        elif execution_intensity >= min_value:  # 50 이상
            score = max_score * 0.25
        else:
            score = 0.0

        return score

    def _score_broker_activity(self, stock_data: Dict[str, Any]) -> float:
        """
        6. 주요 증권사 활동 점수 (40점)

        Args:
            stock_data: 종목 데이터

        Returns:
            점수 (0~40)
        """
        config = self.criteria_config.get('broker_activity', {})
        max_score = config.get('weight', 40)

        broker_buy_count = stock_data.get('top_broker_buy_count', 0)
        top_brokers = config.get('top_brokers', 5)

        if broker_buy_count >= top_brokers:  # 5개
            return max_score
        elif broker_buy_count >= top_brokers * 0.6:  # 3개
            return max_score * 0.67
        elif broker_buy_count >= top_brokers * 0.4:  # 2개
            return max_score * 0.33
        elif broker_buy_count >= 1:  # 1개라도 있으면
            return max_score * 0.17
        else:
            return 0.0

    def _score_program_trading(self, stock_data: Dict[str, Any]) -> float:
        """
        7. 프로그램 매매 점수 (40점)

        ka90013 API로 수집한 실제 프로그램순매수금액 사용

        Args:
            stock_data: 종목 데이터

        Returns:
            점수 (0~40)
        """
        config = self.criteria_config.get('program_trading', {})
        max_score = config.get('weight', 40)

        program_net_buy = stock_data.get('program_net_buy')

        # 디버그: 프로그램매매 값 확인
        stock_code = stock_data.get('stock_code', 'Unknown')

        # 데이터가 없으면 0점
        if program_net_buy is None:
            return 0.0

        # 양수(순매수)만 점수, 음수(순매도)는 0점
        if program_net_buy <= 0:
            return 0.0

        # 프로그램 순매수 금액 기준 (원 단위)
        if program_net_buy >= 5_000_000:  # 500만원 이상
            score = max_score
        elif program_net_buy >= 3_000_000:  # 300만원 이상
            score = max_score * 0.75
        elif program_net_buy >= 1_000_000:  # 100만원 이상
            score = max_score * 0.5
        elif program_net_buy >= 100_000:  # 10만원 이상
            score = max_score * 0.25
        else:
            score = 0.0

        return score

    def _score_technical_indicators(self, stock_data: Dict[str, Any]) -> float:
        """
        8. 기술적 지표 점수 (40점)
        RSI, MACD, BB, MA 등 기술지표 반영

        Args:
            stock_data: 종목 데이터

        Returns:
            점수 (0~40)
        """
        config = self.criteria_config.get('technical_indicators', {})
        max_score = config.get('weight', 40)
        rsi_weight = config.get('rsi_weight', 0.375)
        macd_weight = config.get('macd_weight', 0.375)
        bb_weight = config.get('bb_weight', 0.125)
        ma_weight = config.get('ma_weight', 0.125)

        score = 0.0

        stock_code = stock_data.get('stock_code', 'Unknown')
        score_parts = []

        # RSI
        rsi = stock_data.get('rsi', None)
        if rsi is not None:
            if 30 <= rsi <= 70:  # 과매도/과매수 아님
                rsi_score = max_score * rsi_weight
                score += rsi_score
                score_parts.append(f"RSI({rsi:.0f})+{rsi_score:.0f}")
        else:
            # RSI 없으면 상승률로 추정
            change_rate = stock_data.get('change_rate', 0)
            if 0.5 <= change_rate <= 20.0:
                score_ratio = min(change_rate / 10.0, 1.0)
                rsi_score = max_score * rsi_weight * score_ratio
                score += rsi_score
                score_parts.append(f"RSI추정+{rsi_score:.0f}")
            elif change_rate > 0:
                rsi_score = max_score * 0.25
                score += rsi_score
                score_parts.append(f"RSI추정+{rsi_score:.0f}")

        # MACD
        macd_bullish = stock_data.get('macd_bullish_crossover', False)
        macd = stock_data.get('macd', None)
        macd_positive = False
        if macd is not None:
            if isinstance(macd, dict):
                macd_positive = macd.get('macd', 0) > 0
            elif isinstance(macd, (int, float)):
                macd_positive = macd > 0

        if macd_bullish or macd_positive:
            macd_score = max_score * macd_weight
            score += macd_score
            score_parts.append(f"MACD+{macd_score:.0f}")
        else:
            # MACD 없으면 거래량+상승률로 추정
            change_rate = stock_data.get('change_rate', 0)
            volume = stock_data.get('volume', 0)
            if change_rate > 0 and volume > 500_000:
                macd_score = max_score * 0.3
                score += macd_score
                score_parts.append(f"MACD추정+{macd_score:.0f}")
            elif change_rate > 0:
                macd_score = max_score * 0.2
                score += macd_score
                score_parts.append(f"MACD추정+{macd_score:.0f}")

        # 볼린저밴드 (BB)
        bollinger_bands = stock_data.get('bollinger_bands', None)
        bb_position = bollinger_bands.get('position') if isinstance(bollinger_bands, dict) else stock_data.get('bb_position', None)

        if bb_position is not None and 0.2 <= bb_position <= 0.8:
            bb_score = max_score * bb_weight
            score += bb_score
            score_parts.append(f"BB+{bb_score:.0f}")
        else:
            change_rate = stock_data.get('change_rate', 0)
            if abs(change_rate) < 15:
                bb_score = max_score * 0.1
                score += bb_score
                score_parts.append(f"BB추정+{bb_score:.0f}")

        # 이동평균 (MA)
        ma5 = stock_data.get('ma5', None)
        ma20 = stock_data.get('ma20', None)
        current_price = stock_data.get('current_price', 0)

        if ma5 and ma20 and ma5 > ma20:
            ma_score = max_score * ma_weight
            score += ma_score
            score_parts.append(f"MA+{ma_score:.0f}")
        elif current_price > 0:
            if current_price >= 1000:
                ma_score = max_score * 0.1
                score += ma_score
                score_parts.append(f"MA추정+{ma_score:.0f}")

        if score_parts:
        else:

        return score

    def _score_market_momentum(self, stock_data: Dict[str, Any]) -> float:
        """
        9. 시장 모멘텀 점수 (40점)

        거래량 급등과 가격 상승률 기반으로 시장 모멘텀 추정
        (원래 테마/뉴스 점수였으나 실제 데이터 없어 모멘텀으로 추정)

        Args:
            stock_data: 종목 데이터

        Returns:
            점수 (0~40)
        """
        config = self.criteria_config.get('theme_news', {})
        max_score = config.get('weight', 40)

        score = 0.0

        # 거래량 모멘텀 (20점)
        is_trending_theme = stock_data.get('is_trending_theme', False)
        if is_trending_theme:
            score += max_score * 0.5
        else:
            # 거래량+상승률 기반 시장 모멘텀 추정
            volume = stock_data.get('volume', 0)
            avg_volume = stock_data.get('avg_volume')
            change_rate = stock_data.get('change_rate', 0)

            # avg_volume이 있고 0보다 큰 경우에만 비율 계산
            if avg_volume and avg_volume > 0:
                volume_ratio = volume / avg_volume

                # 거래량 2배 이상 + 상승률 3% 이상 = 강한 모멘텀
                if volume_ratio >= 2.0 and change_rate >= 3.0:
                    score += max_score * 0.4  # 16점
                elif volume_ratio >= 1.5 and change_rate >= 1.5:
                    score += max_score * 0.25  # 10점
                elif volume_ratio >= 1.2 or change_rate >= 0.5:
                    score += max_score * 0.125  # 5점

        # 가격 모멘텀 (20점)
        has_positive_news = stock_data.get('has_positive_news', False)
        if has_positive_news:
            score += max_score * 0.5
        else:
            # 가격 모멘텀+기관 매수 기반 가격 강도 추정
            change_rate = stock_data.get('change_rate', 0)
            institutional_net = stock_data.get('institutional_net_buy')

            # None 체크
            if institutional_net is None:
                institutional_net = 0

            # 상승률 5% 이상 + 기관 순매수 100만원 이상 = 강한 가격 강도
            if change_rate >= 5.0 and institutional_net >= 1_000_000:
                score += max_score * 0.4  # 16점
            elif change_rate >= 2.0 and institutional_net >= 500_000:
                score += max_score * 0.25  # 10점
            elif change_rate >= 0.5 or institutional_net >= 100_000:
                score += max_score * 0.125  # 5점

        return score

    def _score_volatility_pattern(self, stock_data: Dict[str, Any]) -> float:
        """
        10. 변동성 패턴 점수 (20점)

        실제 volatility 데이터만 사용 (일봉 20일 표준편차)

        Args:
            stock_data: 종목 데이터

        Returns:
            점수 (0~20)
        """
        config = self.criteria_config.get('volatility_pattern', {})
        max_score = config.get('weight', 20)

        volatility = stock_data.get('volatility')
        min_volatility = config.get('min_volatility', 0.02)
        max_volatility = config.get('max_volatility', 0.15)

        # volatility 데이터가 없으면 0점
        if volatility is None:
            return 0.0

        # volatility가 있으면 적정 변동성 범위 체크
        if min_volatility <= volatility <= max_volatility:
            # 중간값에 가까울수록 높은 점수
            mid_volatility = (min_volatility + max_volatility) / 2
            distance_from_mid = abs(volatility - mid_volatility)
            max_distance = (max_volatility - min_volatility) / 2

            score_ratio = 1 - (distance_from_mid / max_distance)
            return max_score * score_ratio
        else:
            return 0.0

    def get_grade(self, total_score: float) -> str:
        """
        점수에 따른 등급 반환

        Args:
            total_score: 총점

        Returns:
            등급 (S, A, B, C, D, F)
        """
        max_score = self.scoring_config.get('max_score', 440)
        percentage = (total_score / max_score) * 100

        if percentage >= 90:
            return 'S'
        elif percentage >= 80:
            return 'A'
        elif percentage >= 70:
            return 'B'
        elif percentage >= 60:
            return 'C'
        elif percentage >= 50:
            return 'D'
        else:
            return 'F'

    def should_buy(self, scoring_result: ScoringResult, threshold: float = 300) -> bool:
        """
        매수 여부 판단

        Args:
            scoring_result: 스코어링 결과
            threshold: 매수 임계값 (기본 300점)

        Returns:
            매수 여부
        """
        return scoring_result.total_score >= threshold

    def _get_time_based_weights(self) -> Dict[str, float]:
        """시간대별 가중치 반환"""
        now = datetime.now().time()

        if dt_time(9, 0) <= now < dt_time(11, 0):
            period = 'early'
        elif dt_time(11, 0) <= now < dt_time(14, 0):
            period = 'mid'
        elif dt_time(14, 0) <= now < dt_time(15, 30):
            period = 'late'
        else:
            return {}

        return self.time_based_weights.get(period, {})

    def _calculate_risk_score(self, stock_data: Dict[str, Any]) -> float:
        """리스크 점수 계산 (DynamicRiskManager 연동)"""
        if not self.risk_manager:
            return 0.0

        try:
            risk_level = self.risk_manager.evaluate_stock_risk(stock_data)

            risk_score_map = {
                'low': 20.0,
                'medium': 10.0,
                'high': -10.0,
                'very_high': -20.0
            }

            return risk_score_map.get(risk_level, 0.0)

        except Exception as e:
            logger.debug(f"리스크 점수 계산 실패: {e}")
            return 0.0

    def _get_historical_performance_score(self, stock_code: str) -> float:
        """종목별 과거 성과 히스토리 반영"""
        if stock_code not in self.stock_history:
            return 0.0

        history = self.stock_history[stock_code]

        total_trades = history.get('total_trades', 0)
        if total_trades == 0:
            return 0.0

        win_rate = history.get('win_rate', 0)
        avg_pnl = history.get('avg_pnl', 0)

        if win_rate > 70 and avg_pnl > 50000:
            return 15.0
        elif win_rate > 50 and avg_pnl > 0:
            return 10.0
        elif win_rate < 30 or avg_pnl < -50000:
            return -15.0
        elif avg_pnl < 0:
            return -10.0

        return 0.0

    def _load_historical_data(self):
        """과거 거래 데이터 로드"""
        try:
            perf_file = Path('data/virtual_trading/performance.json')
            if not perf_file.exists():
                return

            with open(perf_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            strategy_records = data.get('strategy_records', {})

            for records in strategy_records.values():
                trades = records.get('trades', [])

                for trade in trades:
                    stock_code = trade.get('stock_code')
                    if not stock_code:
                        continue

                    if stock_code not in self.stock_history:
                        self.stock_history[stock_code] = {
                            'total_trades': 0,
                            'wins': 0,
                            'losses': 0,
                            'total_pnl': 0,
                            'win_rate': 0,
                            'avg_pnl': 0
                        }

                    hist = self.stock_history[stock_code]
                    pnl = trade.get('profit_loss')

                    if pnl is not None:
                        hist['total_trades'] += 1
                        hist['total_pnl'] += pnl

                        if pnl > 0:
                            hist['wins'] += 1
                        else:
                            hist['losses'] += 1

            for stock_code, hist in self.stock_history.items():
                if hist['total_trades'] > 0:
                    hist['win_rate'] = (hist['wins'] / hist['total_trades']) * 100
                    hist['avg_pnl'] = hist['total_pnl'] / hist['total_trades']

            if self.stock_history:
                logger.info(f"과거 성과 데이터 로드: {len(self.stock_history)}개 종목")

        except Exception as e:
            logger.warning(f"과거 성과 데이터 로드 실패: {e}")


__all__ = ['ScoringSystem', 'ScoringResult']
