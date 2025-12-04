"""
research/scanner_pipeline.py
3단계 스캐닝 파이프라인 (Fast → Deep → AI)
Enhanced  Virtual trading learning integration, adaptive scanning
Q8. AI 분석 병렬화 적용
"""
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from pathlib import Path
from collections import deque
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.logger_new import get_logger
from utils.time_utils import is_market_hours, get_trading_session

from config.manager import get_config


logger = get_logger()

# Q8. AI 분석 병렬화: 최대 워커 수
AI_ANALYSIS_MAX_WORKERS = 5  # AI API 동시 호출 제한 (rate limit 고려)


_deep_scan_cache = {}
# Q3. 캐시 최적화: 2초로 단축 (초고속 실시간 매매)
CACHE_TTL_SECONDS = 2


@dataclass
class StockCandidate:
    """종목 후보 데이터 클래스 (v2 - 46+ API 통합)"""

    code: str
    name: str
    price: int
    volume: int
    rate: float  # 등락률 (%)

    # Fast Scan 데이터
    fast_scan_score: float = 0.0
    fast_scan_time: Optional[datetime] = None
    fast_scan_breakdown: Dict[str, float] = field(default_factory=dict)  # 점수 상세

    # =========================================================================
    # Deep Scan 데이터 - 기본 (7가지 API)
    # =========================================================================
    institutional_net_buy: int = 0          # ka10059: 기관 순매수
    foreign_net_buy: int = 0                # ka10059: 외국인 순매수
    individual_net_buy: int = 0             # ka10059: 개인 순매수
    bid_ask_ratio: float = 0.0              # ka10004: 호가비율 (매수/매도)
    bid_total: int = 0                      # ka10004: 매수 총잔량
    ask_total: int = 0                      # ka10004: 매도 총잔량
    institutional_trend: Optional[Dict[str, Any]] = None  # ka10045: 기관매매추이 데이터
    avg_volume: Optional[float] = None      # ka10006: 평균 거래량 (20일)
    volatility: Optional[float] = None      # ka10006: 변동성 (20일 표준편차)
    top_broker_buy_count: int = 0           # ka10078: 주요 증권사 순매수 카운트
    top_broker_net_buy: int = 0             # ka10078: 주요 증권사 순매수 총액
    execution_intensity: Optional[float] = None  # ka10047: 체결강도
    program_net_buy: Optional[int] = None   # ka90013: 프로그램순매수금액

    # =========================================================================
    # Deep Scan 데이터 - 기술적 지표 (일봉 기반)
    # =========================================================================
    rsi: Optional[float] = None             # RSI (14일)
    macd: Optional[Dict[str, float]] = None  # MACD {macd, ema12, ema26}
    bollinger_bands: Optional[Dict[str, float]] = None  # {upper, middle, lower, position}
    ma5: Optional[float] = None             # 5일 이동평균
    ma20: Optional[float] = None            # 20일 이동평균
    ma60: Optional[float] = None            # 60일 이동평균
    price_position: Optional[str] = None    # 이평선 대비 위치 (above_all, between, below_all)

    # =========================================================================
    # Deep Scan 데이터 - 확장 API (46+ API)
    # =========================================================================
    # 외국인 심화
    foreign_continuous_days: int = 0        # ka10035: 외국인 연속 순매수 일수
    foreign_holding_ratio: Optional[float] = None  # 외국인 보유비율
    foreign_limit_ratio: Optional[float] = None    # ka10036: 외국인 한도소진율

    # 기관 심화
    institution_continuous_days: int = 0    # ka10131: 기관 연속 순매수 일수
    financial_net_buy: int = 0              # 금융투자 순매수
    insurance_net_buy: int = 0              # 보험 순매수
    pension_net_buy: int = 0                # 연기금 순매수

    # 프로그램매매 심화
    program_buy: int = 0                    # ka90004: 프로그램 매수금액
    program_sell: int = 0                   # ka90004: 프로그램 매도금액
    program_ratio: Optional[float] = None   # 프로그램 비중

    # 거래량/거래대금
    volume_ratio: Optional[float] = None    # ka10023: 거래량 급증 비율 (vs 평균)
    trading_value: int = 0                  # 거래대금
    volume_surge_rank: Optional[int] = None # 거래량 급증 순위

    # 공매도/대차
    short_sell_volume: int = 0              # ka10014: 공매도량
    short_sell_ratio: Optional[float] = None  # 공매도 비율
    lending_volume: int = 0                 # ka10068: 대차거래량

    # 신용
    credit_ratio: Optional[float] = None    # ka10033: 신용비율
    credit_balance: int = 0                 # 신용잔고

    # 시장 정보
    market_cap: int = 0                     # 시가총액
    per: Optional[float] = None             # PER
    pbr: Optional[float] = None             # PBR
    eps: Optional[float] = None             # EPS

    # 업종/테마
    sector_code: str = ''                   # 업종코드
    sector_name: str = ''                   # 업종명
    sector_rank: Optional[int] = None       # 업종 내 순위
    themes: List[str] = field(default_factory=list)  # 소속 테마

    # =========================================================================
    # OpenAPI Comprehensive Data (20가지)
    # =========================================================================
    openapi_data: Optional[Dict[str, Any]] = None  # 전체 OpenAPI 종합 데이터
    daily_trend: Optional[str] = None       # 일봉 추세 (up/down)
    minute_trend: Optional[str] = None      # 분봉 추세 (strong_up/weak_up/neutral/weak_down/strong_down)
    minute_data_count: int = 0              # 수집된 분봉 데이터 수

    # =========================================================================
    # 시장 흐름 신호 (API Aggregator)
    # =========================================================================
    market_signals: List[str] = field(default_factory=list)  # 감지된 시장 신호
    foreign_flow_signal: Optional[str] = None    # 외국인 자금 흐름 신호
    institution_flow_signal: Optional[str] = None  # 기관 자금 흐름 신호
    program_flow_signal: Optional[str] = None    # 프로그램 자금 흐름 신호
    combined_buy_signal: bool = False       # 외국인+기관 동시 순매수 여부

    # =========================================================================
    # 점수 및 메타
    # =========================================================================
    deep_scan_score: float = 0.0
    deep_scan_time: Optional[datetime] = None
    deep_scan_breakdown: Dict[str, float] = field(default_factory=dict)  # 점수 상세
    data_quality_score: float = 0.0         # 데이터 수집 품질 점수 (0-100)
    api_success_count: int = 0              # 성공한 API 호출 수
    api_total_count: int = 0                # 시도한 API 호출 수

    # AI Scan 데이터
    ai_score: float = 0.0
    ai_signal: str = ''
    ai_confidence: str = ''
    ai_reasons: List[str] = field(default_factory=list)
    ai_risks: List[str] = field(default_factory=list)
    ai_scan_time: Optional[datetime] = None

    # 최종 점수
    final_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (전체 필드)"""
        return {
            # 기본 정보
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'volume': self.volume,
            'rate': self.rate,

            # Fast Scan
            'fast_scan_score': self.fast_scan_score,

            # Deep Scan 기본
            'institutional_net_buy': self.institutional_net_buy,
            'foreign_net_buy': self.foreign_net_buy,
            'individual_net_buy': self.individual_net_buy,
            'bid_ask_ratio': self.bid_ask_ratio,
            'avg_volume': self.avg_volume,
            'volatility': self.volatility,
            'execution_intensity': self.execution_intensity,
            'program_net_buy': self.program_net_buy,

            # 기술적 지표
            'rsi': self.rsi,
            'macd': self.macd,
            'bollinger_bands': self.bollinger_bands,
            'ma5': self.ma5,
            'ma20': self.ma20,
            'price_position': self.price_position,

            # 확장 API
            'foreign_continuous_days': self.foreign_continuous_days,
            'institution_continuous_days': self.institution_continuous_days,
            'volume_ratio': self.volume_ratio,
            'short_sell_ratio': self.short_sell_ratio,
            'credit_ratio': self.credit_ratio,

            # 시장 정보
            'market_cap': self.market_cap,
            'per': self.per,
            'sector_name': self.sector_name,
            'themes': self.themes,

            # 시장 신호
            'combined_buy_signal': self.combined_buy_signal,
            'market_signals': self.market_signals,

            # 점수
            'deep_scan_score': self.deep_scan_score,
            'data_quality_score': self.data_quality_score,
            'api_success_count': self.api_success_count,
            'api_total_count': self.api_total_count,

            # AI
            'ai_score': self.ai_score,
            'ai_signal': self.ai_signal,
            'ai_confidence': self.ai_confidence,
            'ai_reasons': self.ai_reasons,
            'ai_risks': self.ai_risks,

            # 최종
            'final_score': self.final_score,
        }

    def get_summary(self) -> str:
        """간략한 요약 문자열"""
        signals = []
        if self.combined_buy_signal:
            signals.append("외+기")
        if self.rsi and self.rsi < 30:
            signals.append("RSI과매도")
        if self.rsi and self.rsi > 70:
            signals.append("RSI과매수")
        if self.volume_ratio and self.volume_ratio > 3:
            signals.append("거래량급증")
        if self.foreign_continuous_days >= 3:
            signals.append(f"외인{self.foreign_continuous_days}연속")

        signal_str = ", ".join(signals) if signals else "없음"
        return (
            f"{self.name}({self.code}): "
            f"점수={self.deep_scan_score:.1f}, "
            f"품질={self.data_quality_score:.0f}%, "
            f"API={self.api_success_count}/{self.api_total_count}, "
            f"신호=[{signal_str}]"
        )


class ScannerPipeline:
    """3단계 스캐닝 파이프라인 (v2 - 46+ API 통합)"""

    def __init__(
        self,
        market_api,
        screener,
        ai_analyzer,
        scoring_system=None,
        performance_tracker=None,
        api_aggregator=None,
        enable_comprehensive_scan: bool = True
    ):
        """
        초기화

        Args:
            market_api: 시장 데이터 API
            screener: 종목 스크리너
            ai_analyzer: AI 분석기
            scoring_system: 스코어링 시스템 (선택)
            performance_tracker: 가상매매 성과 추적기 (선택)
            api_aggregator: APIDataAggregator 인스턴스 (선택, 46개 API 연동)
            enable_comprehensive_scan: 46+ API 통합 스캔 활성화 (기본: True)
        """
        self.market_api = market_api
        self.screener = screener
        self.ai_analyzer = ai_analyzer
        self.scoring_system = scoring_system
        self.performance_tracker = performance_tracker
        self.api_aggregator = api_aggregator
        self.enable_comprehensive_scan = enable_comprehensive_scan

        self.config = get_config()
        self.scan_config = self.config.scanning

        # Pydantic 모델과 dictionary 모두 지원하는 헬퍼 함수
        def get_scan_value(scan_type, key, default):
            try:
                if isinstance(self.scan_config, dict):
                    scan_settings = self.scan_config.get(scan_type, {})
                    return scan_settings.get(key, default) if isinstance(scan_settings, dict) else getattr(scan_settings, key, default)
                else:
                    scan_settings = getattr(self.scan_config, scan_type, None)
                    if scan_settings is None:
                        return default
                    return getattr(scan_settings, key, default)
            except:
                return default

        # 스캔 간격
        self.fast_scan_interval = get_scan_value('fast_scan', 'interval', 10)
        self.deep_scan_interval = get_scan_value('deep_scan', 'interval', 60)
        self.ai_scan_interval = get_scan_value('ai_scan', 'interval', 300)

        # Q1. 동시 분석 종목 수 극대화: 200/100/30으로 확대
        self.fast_max_candidates = get_scan_value('fast_scan', 'max_candidates', 200)
        self.deep_max_candidates = get_scan_value('deep_scan', 'max_candidates', 100)
        self.ai_max_candidates = get_scan_value('ai_scan', 'max_candidates', 30)

        # 스캔 상태
        self.last_fast_scan = 0
        self.last_deep_scan = 0
        self.last_ai_scan = 0

        # Q1. 후보 캐시 확대: 더 많은 종목 추적
        self.fast_scan_results = deque(maxlen=2000)
        self.deep_scan_results = deque(maxlen=1000)
        self.ai_scan_results = deque(maxlen=500)

        self.best_strategy_cache = {}
        self.market_condition_cache = None
        self.duplicate_filter_cache = set()

        self._load_learning_data()

        # API Aggregator 자동 초기화 (제공되지 않은 경우)
        if self.api_aggregator is None and self.enable_comprehensive_scan:
            self._init_api_aggregator()

        logger.info("🔍 3단계 스캐닝 파이프라인 초기화 완료 (v2 - 46+ API)")
        if self.api_aggregator:
            logger.info("   📊 API Aggregator: 활성화 (46개 API 실시간 수집)")

    def _init_api_aggregator(self):
        """API Aggregator 자동 초기화"""
        try:
            from engine.api_data_aggregator import APIDataAggregator

            # market_api에서 client 추출
            if hasattr(self.market_api, 'client'):
                client = self.market_api.client
                self.api_aggregator = APIDataAggregator(
                    client=client,
                    max_workers=5,
                    enable_all_apis=True
                )
                # 백그라운드 수집 시작
                self.api_aggregator.start()
                logger.info("   ✅ API Aggregator 자동 초기화 및 시작")
            else:
                logger.warning("   ⚠️ market_api에 client 없음 - API Aggregator 비활성화")
        except Exception as e:
            logger.warning(f"   ⚠️ API Aggregator 초기화 실패: {e}")
            self.api_aggregator = None

    def set_api_aggregator(self, aggregator):
        """API Aggregator 설정 (외부에서 주입)"""
        self.api_aggregator = aggregator
        if aggregator:
            logger.info("📊 API Aggregator 연결됨")

    def get_api_coverage_stats(self) -> Dict[str, Any]:
        """API 수집 커버리지 통계 조회"""
        if self.api_aggregator:
            return self.api_aggregator.get_api_coverage_stats()
        return {'total_apis': 0, 'collected_apis': 0, 'coverage_rate': 0}

    def should_run_fast_scan(self) -> bool:
        """Fast Scan 실행 여부 확인"""
        return time.time() - self.last_fast_scan >= self.fast_scan_interval

    def should_run_deep_scan(self) -> bool:
        """Deep Scan 실행 여부 확인"""
        return time.time() - self.last_deep_scan >= self.deep_scan_interval

    def should_run_ai_scan(self) -> bool:
        """AI Scan 실행 여부 확인"""
        return time.time() - self.last_ai_scan >= self.ai_scan_interval

    def run_fast_scan(self) -> List[StockCandidate]:
        """
        Fast Scan (10초 주기)
        - 거래량, 가격, 등락률 기본 필터링
        - 목표: 50종목 선정

        Returns:
            선정된 종목 리스트
        """
        print("⚡ Fast Scan 시작...")
        logger.info("⚡ Fast Scan 시작...")
        start_time = time.time()

        try:
            # 설정 로드
            fast_config = self.scan_config.get('fast_scan', {})
            filters = fast_config.get('filters', {})

            # 장 시간 확인
            market_open = is_market_hours()
            session = get_trading_session()

            # Fix: 등락률 필터 대폭 완화 - 이전 min_rate=1.0이 너무 엄격해서 후보가 0개였음
            # 장중/장외 모두 -10% ~ +30% 범위로 확대
            min_rate = filters.get('min_rate', -10.0)  # 1.0 → -10.0 (하락 종목도 포함)
            max_rate = filters.get('max_rate', 30.0)   # 15.0 → 30.0 (더 넓은 범위)

            if not market_open:
                logger.info(f"⏰ 장외 시간({session}): 등락률 필터 ({min_rate}% ~ {max_rate}%)")

            filter_params = {
                'min_price': filters.get('min_price', 1000),
                'max_price': filters.get('max_price', 1000000),
                'min_volume': filters.get('min_volume', 100000),
                'min_rate': min_rate,
                'max_rate': max_rate,
                'min_market_cap': filters.get('min_market_cap', 0),
            }
            print(f"📍 Fast Scan 필터: {filter_params} (장중: {market_open})")

            # 기본 필터로 종목 스크리닝
            print("📍 screener.screen_stocks() 호출 중...")
            candidates = self.screener.screen_stocks(**filter_params)
            print(f"📍 screener.screen_stocks() 결과: {len(candidates) if candidates else 0}개 종목")

            # ETF/레버리지/인버스/SPAC 제외 필터
            print("📍 ETF/레버리지/SPAC 필터링 중...")
            candidates = self.screener.filter_exclude_etf_and_derivatives(candidates)
            print(f"📍 ETF 필터 후: {len(candidates) if candidates else 0}개 종목")

            # 🔍 DEBUG: 첫 번째 후보 데이터 타입 확인
            if candidates and len(candidates) > 0:
                first = candidates[0]
                print(f"🔍 DEBUG: 첫 번째 종목 키: {list(first.keys())}")
                print(f"🔍 DEBUG: volume 타입={type(first.get('volume'))}, 값={first.get('volume')}")
                print(f"🔍 DEBUG: price 타입={type(first.get('price'))}, 값={first.get('price')}")
                print(f"🔍 DEBUG: rate 타입={type(first.get('rate'))}, 값={first.get('rate')}")

            # 거래량 기준 정렬
            print("📍 거래량 정렬 시작...")
            candidates = sorted(
                candidates,
                key=lambda x: float(x.get('volume', 0)) * float(x.get('price', 0)),  # 거래대금
                reverse=True
            )
            print("📍 거래량 정렬 완료")

            # 최대 개수 제한
            candidates = candidates[:self.fast_max_candidates]

            scan_time = datetime.now()
            stock_candidates = []

            print(f"📍 StockCandidate 생성 시작 ({len(candidates)}개)...")
            for idx, stock in enumerate(candidates):
                try:
                    print(f"  [{idx+1}] {stock.get('name')} - volume={stock.get('volume')} (type={type(stock.get('volume'))})")
                    candidate = StockCandidate(
                        code=stock['code'],
                        name=stock['name'],
                        price=int(float(stock['price'])),
                        volume=int(float(stock['volume'])),
                        rate=float(stock['rate']),
                        fast_scan_time=scan_time,
                    )

                    candidate.fast_scan_score = self._calculate_fast_score(candidate)
                    stock_candidates.append(candidate)
                except Exception as e:
                    print(f"  ❌ 에러 발생: {stock.get('name')} - {e}")
                    import traceback
                    traceback.print_exc()
                    raise  # 원래 에러를 다시 발생시켜 상위 except에서 잡히도록

            print(f"📍 헬퍼 함수 실행 시작 ({len(stock_candidates)}개)...")

            try:
                print("  🔹 _apply_learned_preferences 실행 중...")
                stock_candidates = self._apply_learned_preferences(stock_candidates)
                print(f"  ✅ _apply_learned_preferences 완료: {len(stock_candidates)}개")
            except Exception as e:
                print(f"  ❌ _apply_learned_preferences 에러: {e}")
                import traceback
                traceback.print_exc()
                raise

            try:
                print("  🔹 _adjust_for_market_condition 실행 중...")
                stock_candidates = self._adjust_for_market_condition(stock_candidates)
                print(f"  ✅ _adjust_for_market_condition 완료: {len(stock_candidates)}개")
            except Exception as e:
                print(f"  ❌ _adjust_for_market_condition 에러: {e}")
                import traceback
                traceback.print_exc()
                raise

            try:
                print("  🔹 _filter_duplicates 실행 중...")
                stock_candidates = self._filter_duplicates(stock_candidates)
                print(f"  ✅ _filter_duplicates 완료: {len(stock_candidates)}개")
            except Exception as e:
                print(f"  ❌ _filter_duplicates 에러: {e}")
                import traceback
                traceback.print_exc()
                raise

            self.fast_scan_results = stock_candidates
            self.last_fast_scan = time.time()

            elapsed = time.time() - start_time
            logger.info(
                f"⚡ Fast Scan 완료: {len(stock_candidates)}종목 선정 "
                f"(소요시간: {elapsed:.2f}초)"
            )

            return stock_candidates

        except Exception as e:
            logger.error(f"Fast Scan 실패: {e}", exc_info=True)
            return []

    def _calculate_fast_score(self, candidate: StockCandidate) -> float:
        """
        Fast Scan 점수 계산

        Args:
            candidate: 종목 후보

        Returns:
            점수 (0~100)
        """
        score = 0.0

        # 거래대금 점수 (40점)
        trading_value = candidate.price * candidate.volume
        if trading_value > 1_000_000_000:  # 10억 이상
            score += 40
        elif trading_value > 500_000_000:  # 5억 이상
            score += 30
        elif trading_value > 100_000_000:  # 1억 이상
            score += 20

        # 등락률 점수 (30점)
        if 2.0 <= candidate.rate <= 10.0:
            score += 30
        elif 1.0 <= candidate.rate <= 15.0:
            score += 20

        # 거래량 점수 (30점)
        if candidate.volume > 1_000_000:
            score += 30
        elif candidate.volume > 500_000:
            score += 20
        elif candidate.volume > 100_000:
            score += 10

        return score

    def run_deep_scan(self, candidates: Optional[List[StockCandidate]] = None) -> List[StockCandidate]:
        """
        Deep Scan v2 - 46+ API 통합 수집 (1분 주기)

        수집 데이터:
        - 기본 7가지 API (투자자, 호가, 기관추이, 일봉, 증권사, 체결강도, 프로그램)
        - 기술적 지표 (RSI, MACD, 볼린저밴드, 이동평균)
        - 확장 API (외인연속, 신용비율, 거래량급증)
        - OpenAPI 종합 데이터 (20가지) - 선택
        - API Aggregator 시장 신호 (46개) - 선택

        Args:
            candidates: 분석할 종목 리스트 (None이면 Fast Scan 결과 사용)

        Returns:
            선정된 종목 리스트 (enrichment 완료)
        """
        logger.info("🔬 Comprehensive Deep Scan v2 시작 (46+ API)...")
        start_time = time.time()

        try:
            if candidates is None:
                candidates = self.fast_scan_results

            if not candidates:
                logger.warning("Deep Scan 대상 종목 없음")
                return []

            # 통합 Deep Scanner 사용
            from research.comprehensive_deep_scan import ComprehensiveDeepScanner

            # OpenAPI 클라이언트 가져오기 (선택)
            openapi_client = None
            try:
                from core.openapi_client import get_openapi_client
                openapi_client = get_openapi_client(auto_connect=False)
                if openapi_client and openapi_client.is_connected:
                    logger.info("   📡 OpenAPI 클라이언트 연결됨")
                else:
                    openapi_client = None
            except Exception as e:
                logger.debug(f"OpenAPI 클라이언트 사용 불가: {e}")

            # API Aggregator 가져오기 (선택)
            api_aggregator = None
            try:
                if hasattr(self, 'api_aggregator') and self.api_aggregator:
                    api_aggregator = self.api_aggregator
                    logger.info("   📊 API Aggregator 연결됨")
            except Exception as e:
                logger.debug(f"API Aggregator 사용 불가: {e}")

            # ComprehensiveDeepScanner 인스턴스 생성
            scanner = ComprehensiveDeepScanner(
                market_api=self.market_api,
                openapi_client=openapi_client,
                api_aggregator=api_aggregator,
                max_workers=10
            )

            # 46+ API 데이터 수집 실행
            enriched_candidates = scanner.scan_candidates(
                candidates=list(candidates),
                max_candidates=self.deep_max_candidates,
                verbose=True
            )

            # 점수 기준 정렬
            enriched_candidates = sorted(
                enriched_candidates,
                key=lambda x: x.deep_scan_score,
                reverse=True
            )

            # 최대 개수 제한
            enriched_candidates = enriched_candidates[:self.deep_max_candidates]

            # 결과 저장
            self.deep_scan_results = enriched_candidates
            self.last_deep_scan = time.time()

            elapsed = time.time() - start_time

            # 통계 로그
            total_api_success = sum(c.api_success_count for c in enriched_candidates)
            total_api_calls = sum(c.api_total_count for c in enriched_candidates)
            avg_quality = sum(c.data_quality_score for c in enriched_candidates) / len(enriched_candidates) if enriched_candidates else 0
            combined_signals = sum(1 for c in enriched_candidates if c.combined_buy_signal)

            logger.info(
                f"🔬 Comprehensive Deep Scan 완료: {len(enriched_candidates)}종목 선정 "
                f"(소요시간: {elapsed:.2f}초)"
            )
            logger.info(
                f"   📊 API 통계: {total_api_success}/{total_api_calls} 성공, "
                f"평균 품질: {avg_quality:.0f}%"
            )
            if combined_signals > 0:
                logger.info(f"   🚨 외국인+기관 동시 순매수: {combined_signals}종목")

            # 상위 5종목 요약 출력
            print("\n" + "="*60)
            print("📊 Deep Scan 상위 5종목 요약")
            print("="*60)
            for idx, c in enumerate(enriched_candidates[:5], 1):
                print(f"  [{idx}] {c.get_summary()}")
            print("="*60 + "\n")

            return enriched_candidates

        except ImportError as e:
            logger.error(f"comprehensive_deep_scan 모듈 임포트 실패: {e}")
            logger.info("기존 Deep Scan 로직으로 폴백...")
            return self._run_legacy_deep_scan(candidates)

        except Exception as e:
            logger.error(f"Deep Scan 실패: {e}", exc_info=True)
            return []

    def _run_legacy_deep_scan(self, candidates: Optional[List[StockCandidate]] = None) -> List[StockCandidate]:
        """기존 Deep Scan 로직 (폴백용)"""
        if candidates is None:
            candidates = self.fast_scan_results

        if not candidates:
            return []

        scan_time = datetime.now()

        for candidate in candidates:
            try:
                # 기관/외국인 매매 데이터
                investor_data = self.market_api.get_investor_data(candidate.code)
                if investor_data:
                    candidate.institutional_net_buy = investor_data.get('기관_순매수', 0)
                    candidate.foreign_net_buy = investor_data.get('외국인_순매수', 0)

                # 호가 데이터
                bid_ask = self.market_api.get_bid_ask(candidate.code)
                if bid_ask:
                    bid_total = bid_ask.get('매수_총잔량', 1)
                    ask_total = bid_ask.get('매도_총잔량', 1)
                    candidate.bid_ask_ratio = bid_total / ask_total if ask_total > 0 else 0

                # 점수 계산
                candidate.deep_scan_score = self._calculate_deep_score(candidate)
                candidate.deep_scan_time = scan_time

                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Legacy Deep Scan 오류 ({candidate.code}): {e}")
                continue

        candidates = sorted(candidates, key=lambda x: x.deep_scan_score, reverse=True)
        candidates = candidates[:self.deep_max_candidates]

        self.deep_scan_results = candidates
        self.last_deep_scan = time.time()

        return candidates

    def _calculate_deep_score(self, candidate: StockCandidate) -> float:
        """
        Deep Scan 점수 계산

        Args:
            candidate: 종목 후보

        Returns:
            점수 (0~100)
        """
        score = candidate.fast_scan_score  # Fast Scan 점수 승계

        # 기관 순매수 점수 (30점)
        if candidate.institutional_net_buy > 50_000_000:  # 5천만원 이상
            score += 30
        elif candidate.institutional_net_buy > 20_000_000:  # 2천만원 이상
            score += 20
        elif candidate.institutional_net_buy > 10_000_000:  # 1천만원 이상
            score += 10

        # 외국인 순매수 점수 (20점)
        if candidate.foreign_net_buy > 20_000_000:
            score += 20
        elif candidate.foreign_net_buy > 10_000_000:
            score += 15
        elif candidate.foreign_net_buy > 5_000_000:
            score += 10

        # 호가 강도 점수 (20점)
        if candidate.bid_ask_ratio > 1.5:
            score += 20
        elif candidate.bid_ask_ratio > 1.2:
            score += 15
        elif candidate.bid_ask_ratio > 1.0:
            score += 10

        return score

    def _analyze_single_stock(self, candidate: StockCandidate, min_score: float, min_confidence: str, scan_time: datetime) -> Optional[StockCandidate]:
        """Q8. 단일 종목 AI 분석 (병렬 처리용)"""
        try:
            # 종목 데이터 준비
            stock_data = {
                'stock_code': candidate.code,
                'stock_name': candidate.name,
                'current_price': candidate.price,
                'volume': candidate.volume,
                'change_rate': candidate.rate,
                'institutional_net_buy': candidate.institutional_net_buy,
                'foreign_net_buy': candidate.foreign_net_buy,
                'bid_ask_ratio': candidate.bid_ask_ratio,
            }

            # AI 분석 실행
            analysis = self.ai_analyzer.analyze_stock(stock_data)

            # 결과 저장
            candidate.ai_score = analysis.get('score', 0)
            candidate.ai_signal = analysis.get('signal', 'hold')
            candidate.ai_confidence = analysis.get('confidence', 'Low')
            candidate.ai_reasons = analysis.get('reasons', [])
            candidate.ai_risks = analysis.get('risks', [])
            candidate.ai_scan_time = scan_time

            # 최종 점수 계산 (Deep Scan 70% + AI 30%)
            candidate.final_score = (
                candidate.deep_scan_score * 0.7 +
                candidate.ai_score * 10 * 0.3
            )

            # AI 승인 조건 확인
            confidence_level = {'Low': 1, 'Medium': 2, 'High': 3}
            min_conf_level = confidence_level.get(min_confidence, 2)
            ai_conf_level = confidence_level.get(candidate.ai_confidence, 1)

            if (
                candidate.ai_signal == 'buy' and
                candidate.ai_score >= min_score and
                ai_conf_level >= min_conf_level
            ):
                logger.info(
                    f"✅ AI 승인: {candidate.name} "
                    f"(점수: {candidate.ai_score:.1f}, 신뢰도: {candidate.ai_confidence})"
                )
                return candidate

            logger.debug(
                f"❌ AI 거부: {candidate.name} "
                f"(점수: {candidate.ai_score:.1f}, 신뢰도: {candidate.ai_confidence})"
            )
            return None

        except Exception as e:
            logger.error(f"종목 {candidate.code} AI 분석 실패: {e}")
            return None

    def run_ai_scan(self, candidates: Optional[List[StockCandidate]] = None) -> List[StockCandidate]:
        """
        AI Scan (5분 주기) - Q8. 병렬 처리 적용
        - AI 분석을 통한 최종 매수 추천
        - 목표: 30종목 선정 (5 → 30 확대)

        Args:
            candidates: 분석할 종목 리스트 (None이면 Deep Scan 결과 사용)

        Returns:
            선정된 종목 리스트
        """
        print("📍 run_ai_scan() 메서드 진입 (병렬 처리)")
        logger.info("🤖 AI Scan 시작 (병렬 처리)...")
        start_time = time.time()

        try:
            if candidates is None:
                candidates = self.deep_scan_results

            print(f"📍 AI Scan candidates: {len(candidates)}개")

            if not candidates:
                print("⚠️  candidates 비어있음 - 종료")
                logger.warning("AI Scan 대상 종목 없음")
                return []

            ai_config = self.scan_config.get('ai_scan', {})
            scan_time = datetime.now()
            min_score = ai_config.get('min_analysis_score', 5.0)
            min_confidence = ai_config.get('min_confidence', 'Low')

            print(f"📍 AI 분석기 타입: {type(self.ai_analyzer).__name__}")
            print(f"📍 AI 분석 시작 - {len(candidates)}개 종목 병렬 처리")

            # Q8. 병렬 AI 분석
            ai_approved = []

            with ThreadPoolExecutor(max_workers=AI_ANALYSIS_MAX_WORKERS) as executor:
                # 모든 종목에 대해 병렬로 AI 분석 제출
                future_to_candidate = {
                    executor.submit(
                        self._analyze_single_stock,
                        candidate, min_score, min_confidence, scan_time
                    ): candidate
                    for candidate in candidates
                }

                # 완료된 작업 수집
                completed = 0
                for future in as_completed(future_to_candidate):
                    completed += 1
                    candidate = future_to_candidate[future]
                    try:
                        result = future.result()
                        if result:
                            ai_approved.append(result)
                        if completed % 10 == 0:
                            logger.info(f"🤖 AI 분석 진행: {completed}/{len(candidates)}")
                    except Exception as e:
                        logger.error(f"AI 분석 Future 오류 ({candidate.name}): {e}")

            # 최종 점수 기준 정렬
            ai_approved = sorted(
                ai_approved,
                key=lambda x: x.final_score,
                reverse=True
            )

            # 최대 개수 제한
            ai_approved = ai_approved[:self.ai_max_candidates]

            # 결과 저장
            self.ai_scan_results = ai_approved
            self.last_ai_scan = time.time()

            elapsed = time.time() - start_time
            logger.info(
                f"🤖 AI Scan 완료: {len(ai_approved)}종목 선정 "
                f"(소요시간: {elapsed:.2f}초, 병렬처리)"
            )

            return ai_approved

        except Exception as e:
            logger.error(f"AI Scan 실패: {e}", exc_info=True)
            return []

    def scan_market(self) -> List[StockCandidate]:
        """
        시장 스캔 실행 (main.py에서 호출)
        run_full_pipeline()의 wrapper 메서드

        Returns:
            최종 후보 종목 리스트
        """
        return self.run_full_pipeline()

    def run_full_pipeline(self) -> List[StockCandidate]:
        """
        전체 파이프라인 실행 (필요한 단계만 실행)

        Returns:
            최종 AI 승인 종목 리스트
        """
        print("🚀 스캐닝 파이프라인 실행 시작")
        logger.info("🚀 스캐닝 파이프라인 실행 시작")

        # Fast Scan
        should_fast = self.should_run_fast_scan()
        print(f"📍 Fast Scan 조건: should_run={should_fast}, interval={self.fast_scan_interval}초, last_scan={self.last_fast_scan}")

        if should_fast:
            print("✅ Fast Scan 실행 중...")
            self.run_fast_scan()
            print(f"📊 Fast Scan 결과: {len(self.fast_scan_results)}개 종목")
        else:
            print(f"⏭️ Fast Scan 스킵 (간격 미충족, 캐시: {len(self.fast_scan_results)}개)")

        # Deep Scan
        should_deep = self.should_run_deep_scan()
        has_fast_results = len(self.fast_scan_results) > 0
        print(f"📍 Deep Scan 조건: should_run={should_deep}, has_fast_results={has_fast_results} ({len(self.fast_scan_results)}개)")

        if should_deep and has_fast_results:
            print("✅ Deep Scan 실행 중...")
            self.run_deep_scan()
            print(f"📊 Deep Scan 결과: {len(self.deep_scan_results)}개 종목")
        else:
            if not should_deep:
                print(f"⏭️ Deep Scan 스킵 (간격 미충족, 캐시: {len(self.deep_scan_results)}개)")
            else:
                print(f"⏭️ Deep Scan 스킵 (Fast Scan 결과 없음)")

        # AI는 매수 결정 시점에만 사용 (별도 스캔 단계 없음)
        print(f"ℹ️  AI 분석: 매수 시점에서 최종 후보에 대해서만 실행")

        summary = (
            f"✅ 스캐닝 파이프라인 완료: "
            f"Fast={len(self.fast_scan_results)}, "
            f"Deep={len(self.deep_scan_results)} (최종 후보)"
        )
        print(summary)
        logger.info(summary)

        # Deep Scan 결과를 최종 후보로 반환
        return self.deep_scan_results

    def get_scan_summary(self) -> Dict[str, Any]:
        """스캔 결과 요약"""
        return {
            'fast_scan': {
                'count': len(self.fast_scan_results),
                'last_run': datetime.fromtimestamp(self.last_fast_scan).isoformat() if self.last_fast_scan else None,
            },
            'deep_scan': {
                'count': len(self.deep_scan_results),
                'last_run': datetime.fromtimestamp(self.last_deep_scan).isoformat() if self.last_deep_scan else None,
            },
            'ai_scan': {
                'count': len(self.ai_scan_results),
                'last_run': datetime.fromtimestamp(self.last_ai_scan).isoformat() if self.last_ai_scan else None,
            },
        }

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """캐시에서 데이터 조회"""
        global _deep_scan_cache

        if cache_key not in _deep_scan_cache:
            return None

        entry = _deep_scan_cache[cache_key]
        timestamp = entry['timestamp']

        # TTL 체크
        if (datetime.now() - timestamp).total_seconds() > CACHE_TTL_SECONDS:
            # 만료됨 - 삭제
            del _deep_scan_cache[cache_key]
            return None

        return entry['data']

    def _save_to_cache(self, cache_key: str, data: Dict):
        """캐시에 데이터 저장"""
        global _deep_scan_cache

        _deep_scan_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }

    def _load_learning_data(self):
        """가상매매 학습 데이터 로드"""
        try:
            perf_file = Path('data/virtual_trading/performance.json')
            if not perf_file.exists():
                logger.debug("가상매매 성과 데이터 없음")
                return

            with open(perf_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            strategy_records = data.get('strategy_records', {})

            for strategy_name, records in strategy_records.items():
                trades = records.get('trades', [])
                if not trades:
                    continue

                completed_trades = [t for t in trades if t.get('profit_loss') is not None]
                if not completed_trades:
                    continue

                winning_trades = [t for t in completed_trades if t['profit_loss'] > 0]
                win_rate = len(winning_trades) / len(completed_trades) * 100 if completed_trades else 0
                avg_pnl = sum(t['profit_loss'] for t in completed_trades) / len(completed_trades)

                self.best_strategy_cache[strategy_name] = {
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'total_trades': len(completed_trades),
                    'winning_stocks': [t.get('stock_code') for t in winning_trades],
                    'losing_stocks': [t.get('stock_code') for t in completed_trades if t['profit_loss'] <= 0]
                }

            if self.best_strategy_cache:
                best = max(self.best_strategy_cache.items(), key=lambda x: x[1]['avg_pnl'])
                logger.info(f"📚 학습 데이터 로드: 최고 전략 = {best[0]} (평균 손익: {best[1]['avg_pnl']:,.0f}원)")

        except Exception as e:
            logger.warning(f"학습 데이터 로드 실패: {e}")

    def _detect_market_condition(self) -> str:
        """실시간 시장 조건 감지"""
        try:
            if self.market_condition_cache:
                cache_time = self.market_condition_cache.get('timestamp')
                # Fix: .seconds → total_seconds()
                if cache_time and (datetime.now() - cache_time).total_seconds() < 60:
                    return self.market_condition_cache.get('condition', 'normal')

            kospi_data = self.market_api.get_index_data('001')
            kosdaq_data = self.market_api.get_index_data('101')

            if kospi_data and kosdaq_data:
                kospi_change = float(kospi_data.get('change_rate', 0))
                kosdaq_change = float(kosdaq_data.get('change_rate', 0))

                if kospi_change > 1.5 and kosdaq_change > 1.5:
                    condition = 'bullish'
                elif kospi_change < -1.5 and kosdaq_change < -1.5:
                    condition = 'bearish'
                elif abs(kospi_change) < 0.5 and abs(kosdaq_change) < 0.5:
                    condition = 'sideways'
                else:
                    condition = 'normal'

                self.market_condition_cache = {
                    'condition': condition,
                    'timestamp': datetime.now(),
                    'kospi_change': kospi_change,
                    'kosdaq_change': kosdaq_change
                }

                return condition

        except Exception as e:
            logger.debug(f"시장 조건 감지 실패: {e}")

        return 'normal'

    def _filter_duplicates(self, candidates: List[StockCandidate]) -> List[StockCandidate]:
        """중복 종목 필터링 강화"""
        current_time = time.time()
        filtered = []

        for candidate in candidates:
            cache_key = f"{candidate.code}_{current_time // 300}"

            if cache_key not in self.duplicate_filter_cache:
                self.duplicate_filter_cache.add(cache_key)
                filtered.append(candidate)

        old_keys = {k for k in self.duplicate_filter_cache if int(float(k.split('_')[1])) < (current_time // 300) - 5}
        self.duplicate_filter_cache -= old_keys

        if len(candidates) != len(filtered):
            logger.info(f"중복 필터링: {len(candidates)}개 → {len(filtered)}개")

        return filtered

    def _apply_learned_preferences(self, candidates: List[StockCandidate]) -> List[StockCandidate]:
        """학습된 선호도 적용"""
        if not self.best_strategy_cache:
            return candidates

        for candidate in candidates:
            bonus_score = 0

            for strategy_data in self.best_strategy_cache.values():
                if candidate.code in strategy_data.get('winning_stocks', []):
                    bonus_score += 10
                    logger.debug(f"{candidate.name}: 과거 성공 종목 +10점")

                if candidate.code in strategy_data.get('losing_stocks', []):
                    bonus_score -= 5
                    logger.debug(f"{candidate.name}: 과거 실패 종목 -5점")

            candidate.fast_scan_score += bonus_score

        return candidates

    def _adjust_for_market_condition(self, candidates: List[StockCandidate]) -> List[StockCandidate]:
        """시장 조건에 따른 스캔 조정"""
        condition = self._detect_market_condition()

        logger.info(f"시장 조건: {condition}")

        if condition == 'bearish':
            candidates = [c for c in candidates if c.rate < 5.0]
            logger.info(f"약세장: 급등주 제외 ({len(candidates)}개 남음)")

        elif condition == 'bullish':
            candidates = [c for c in candidates if c.rate > 1.0]
            logger.info(f"강세장: 상승주 우선 ({len(candidates)}개 남음)")

        return candidates


__all__ = ['ScannerPipeline', 'StockCandidate']
