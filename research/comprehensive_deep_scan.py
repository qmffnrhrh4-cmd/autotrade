"""
research/comprehensive_deep_scan.py
통합 Deep Scan 모듈 - 46+ API 데이터 수집

모든 가용 API를 통합하여 종목 데이터를 수집합니다:
1. 기본 7가지 API (기존 deep_scan_utils.py)
2. API Aggregator 46개 API
3. OpenAPI Comprehensive Data 20가지

Author: AutoTrade Pro v8.2
"""
import time
import statistics
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import threading

from utils.logger_new import get_logger

if TYPE_CHECKING:
    from research.scanner_pipeline import StockCandidate

logger = get_logger()

# =========================================================================
# 캐시 설정
# =========================================================================
_comprehensive_cache = {}
CACHE_TTL_SECONDS = 30  # 30초


def _get_from_cache(cache_key: str) -> Optional[Dict]:
    """캐시에서 데이터 조회"""
    global _comprehensive_cache
    if cache_key not in _comprehensive_cache:
        return None
    entry = _comprehensive_cache[cache_key]
    if (datetime.now() - entry['timestamp']).total_seconds() > CACHE_TTL_SECONDS:
        del _comprehensive_cache[cache_key]
        return None
    return entry['data']


def _save_to_cache(cache_key: str, data: Dict):
    """캐시에 데이터 저장"""
    global _comprehensive_cache
    _comprehensive_cache[cache_key] = {
        'data': data,
        'timestamp': datetime.now()
    }


# =========================================================================
# 기술적 지표 계산
# =========================================================================
def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """RSI (Relative Strength Index) 계산"""
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_macd(prices: List[float]) -> Optional[Dict[str, float]]:
    """MACD 계산"""
    if len(prices) < 26:
        return None

    def ema(data: List[float], period: int) -> float:
        multiplier = 2 / (period + 1)
        ema_value = sum(data[:period]) / period
        for price in data[period:]:
            ema_value = (price - ema_value) * multiplier + ema_value
        return ema_value

    ema12 = ema(prices, 12)
    ema26 = ema(prices, 26)
    macd_line = ema12 - ema26
    return {'macd': macd_line, 'ema12': ema12, 'ema26': ema26}


def calculate_bollinger_bands(prices: List[float], period: int = 20) -> Optional[Dict[str, float]]:
    """볼린저 밴드 계산"""
    if len(prices) < period:
        return None
    recent_prices = prices[-period:]
    ma = sum(recent_prices) / period
    std_dev = statistics.stdev(recent_prices) if len(recent_prices) > 1 else 0
    upper_band = ma + (2 * std_dev)
    lower_band = ma - (2 * std_dev)
    current_price = prices[-1]
    bb_position = (current_price - lower_band) / (upper_band - lower_band) if upper_band != lower_band else 0.5
    return {
        'upper': upper_band,
        'middle': ma,
        'lower': lower_band,
        'position': bb_position
    }


def calculate_moving_averages(prices: List[float]) -> Dict[str, Optional[float]]:
    """이동평균 계산"""
    result = {'ma5': None, 'ma20': None, 'ma60': None}
    if len(prices) >= 5:
        result['ma5'] = sum(prices[-5:]) / 5
    if len(prices) >= 20:
        result['ma20'] = sum(prices[-20:]) / 20
    if len(prices) >= 60:
        result['ma60'] = sum(prices[-60:]) / 60
    return result


# =========================================================================
# 통합 Deep Scan 클래스
# =========================================================================
class ComprehensiveDeepScanner:
    """
    통합 Deep Scan 엔진

    46+ API를 병렬로 수집하여 종목 데이터를 enrichment합니다.
    """

    # 주요 증권사 코드
    MAJOR_BROKERS = [
        ('001', '한국투자'),
        ('003', '미래에셋'),
        ('030', 'NH투자'),
        ('005', '삼성'),
        ('038', 'KB증권'),
    ]

    def __init__(
        self,
        market_api,
        openapi_client=None,
        api_aggregator=None,
        max_workers: int = 10
    ):
        """
        초기화

        Args:
            market_api: MarketAPI 인스턴스
            openapi_client: KiwoomOpenAPIClient 인스턴스 (선택)
            api_aggregator: APIDataAggregator 인스턴스 (선택)
            max_workers: 병렬 처리 워커 수
        """
        self.market_api = market_api
        self.openapi_client = openapi_client
        self.api_aggregator = api_aggregator
        self.max_workers = max_workers
        self._lock = threading.Lock()

        logger.info(
            f"📊 ComprehensiveDeepScanner 초기화: "
            f"market_api={'O' if market_api else 'X'}, "
            f"openapi={'O' if openapi_client else 'X'}, "
            f"aggregator={'O' if api_aggregator else 'X'}"
        )

    def scan_candidates(
        self,
        candidates: List['StockCandidate'],
        max_candidates: int = 50,
        verbose: bool = True
    ) -> List['StockCandidate']:
        """
        후보 종목들에 대해 46+ API 데이터 수집

        Args:
            candidates: 후보 종목 리스트
            max_candidates: 최대 처리 종목 수
            verbose: 상세 로그 출력

        Returns:
            enrichment된 종목 리스트
        """
        if not candidates:
            return candidates

        top_candidates = candidates[:max_candidates]
        total = len(top_candidates)

        if verbose:
            print(f"\n{'='*60}")
            print(f"🔬 Comprehensive Deep Scan 시작 ({total}개 종목)")
            print(f"{'='*60}")

        start_time = time.time()
        success_count = 0
        total_api_calls = 0
        total_api_success = 0

        for idx, candidate in enumerate(top_candidates, 1):
            try:
                if verbose:
                    print(f"\n[{idx}/{total}] {candidate.name} ({candidate.code})")
                    print("-" * 40)

                # 종목별 데이터 수집
                api_stats = self._enrich_single_candidate(candidate, verbose)

                total_api_calls += api_stats['total']
                total_api_success += api_stats['success']

                # Deep Scan 점수 계산
                candidate.deep_scan_score = self._calculate_comprehensive_score(candidate)
                candidate.deep_scan_time = datetime.now()

                # 데이터 품질 점수
                if api_stats['total'] > 0:
                    candidate.data_quality_score = (api_stats['success'] / api_stats['total']) * 100
                    candidate.api_success_count = api_stats['success']
                    candidate.api_total_count = api_stats['total']

                success_count += 1

                if verbose:
                    print(f"   📊 점수: {candidate.deep_scan_score:.1f}")
                    print(f"   📈 품질: {candidate.data_quality_score:.0f}% ({api_stats['success']}/{api_stats['total']} API)")
                    if candidate.combined_buy_signal:
                        print(f"   🚨 신호: 외국인+기관 동시 순매수!")

            except Exception as e:
                logger.error(f"종목 {candidate.code} 처리 중 오류: {e}")
                if verbose:
                    print(f"   ❌ 오류: {e}")
                continue

        elapsed = time.time() - start_time

        if verbose:
            print(f"\n{'='*60}")
            print(f"✅ Comprehensive Deep Scan 완료")
            print(f"   처리: {success_count}/{total} 종목")
            print(f"   API: {total_api_success}/{total_api_calls} 성공")
            print(f"   소요: {elapsed:.1f}초")
            print(f"{'='*60}\n")

        return top_candidates

    def _enrich_single_candidate(
        self,
        candidate: 'StockCandidate',
        verbose: bool = True
    ) -> Dict[str, int]:
        """
        단일 종목 데이터 수집 (46+ API)

        Returns:
            {'total': API 호출 수, 'success': 성공 수}
        """
        stats = {'total': 0, 'success': 0}

        # =====================================================================
        # 1. 기본 API (7가지) - 순차 처리
        # =====================================================================
        self._fetch_basic_apis(candidate, stats, verbose)

        # =====================================================================
        # 2. 확장 API (병렬 처리)
        # =====================================================================
        self._fetch_extended_apis(candidate, stats, verbose)

        # =====================================================================
        # 3. OpenAPI Comprehensive Data (선택)
        # =====================================================================
        if self.openapi_client:
            self._fetch_openapi_data(candidate, stats, verbose)

        # =====================================================================
        # 4. API Aggregator 데이터 (선택)
        # =====================================================================
        if self.api_aggregator:
            self._fetch_aggregator_data(candidate, stats, verbose)

        return stats

    def _fetch_basic_apis(
        self,
        candidate: 'StockCandidate',
        stats: Dict[str, int],
        verbose: bool
    ):
        """기본 7가지 API 수집"""

        # 1. 투자자별 매매 (ka10059)
        stats['total'] += 1
        if verbose:
            print(f"   📊 [1/7] 투자자별 매매 (ka10059)...", end=" ")
        try:
            investor_data = self.market_api.get_investor_data(candidate.code)
            if investor_data:
                candidate.institutional_net_buy = investor_data.get('기관_순매수', 0)
                candidate.foreign_net_buy = investor_data.get('외국인_순매수', 0)
                candidate.individual_net_buy = investor_data.get('개인_순매수', 0)
                stats['success'] += 1
                if verbose:
                    print(f"✓ 기관={candidate.institutional_net_buy:,}, 외인={candidate.foreign_net_buy:,}")
            else:
                if verbose:
                    print("⚠ 데이터 없음")
        except Exception as e:
            if verbose:
                print(f"✗ {e}")

        time.sleep(0.05)

        # 2. 호가 데이터 (ka10004)
        stats['total'] += 1
        if verbose:
            print(f"   📊 [2/7] 호가 데이터 (ka10004)...", end=" ")
        try:
            bid_ask = self.market_api.get_bid_ask(candidate.code)
            if bid_ask:
                candidate.bid_total = bid_ask.get('매수_총잔량', 0)
                candidate.ask_total = bid_ask.get('매도_총잔량', 1)
                candidate.bid_ask_ratio = candidate.bid_total / candidate.ask_total if candidate.ask_total > 0 else 0
                stats['success'] += 1
                if verbose:
                    print(f"✓ 비율={candidate.bid_ask_ratio:.2f}")
            else:
                if verbose:
                    print("⚠ 데이터 없음")
        except Exception as e:
            if verbose:
                print(f"✗ {e}")

        time.sleep(0.05)

        # 3. 기관매매추이 (ka10045)
        stats['total'] += 1
        if verbose:
            print(f"   📊 [3/7] 기관매매추이 (ka10045)...", end=" ")
        try:
            trend_data = self.market_api.get_institutional_trading_trend(
                candidate.code, days=5, price_type='buy'
            )
            if trend_data:
                candidate.institutional_trend = trend_data
                stats['success'] += 1
                if verbose:
                    print(f"✓ 5일 데이터")
            else:
                if verbose:
                    print("⚠ 데이터 없음")
        except Exception as e:
            if verbose:
                print(f"✗ {e}")

        time.sleep(0.05)

        # 4. 일봉 데이터 (ka10006) + 기술적 지표
        stats['total'] += 1
        if verbose:
            print(f"   📊 [4/7] 일봉 + 기술지표 (ka10006)...", end=" ")
        try:
            daily_data = self.market_api.get_daily_chart(candidate.code, period=60)
            if daily_data and len(daily_data) > 1:
                # 평균 거래량
                volumes = [d.get('volume', 0) for d in daily_data if d.get('volume')]
                if volumes:
                    candidate.avg_volume = sum(volumes) / len(volumes)
                    if candidate.avg_volume > 0:
                        candidate.volume_ratio = candidate.volume / candidate.avg_volume

                # 변동성
                rates = []
                for d in daily_data:
                    close = d.get('close', 0)
                    open_price = d.get('open', 0)
                    if open_price and open_price > 0:
                        rates.append((close - open_price) / open_price)
                if len(rates) > 1:
                    candidate.volatility = statistics.stdev(rates)

                # 기술적 지표
                closes = [d.get('close', 0) for d in daily_data if d.get('close')]
                if closes:
                    # RSI
                    candidate.rsi = calculate_rsi(closes)
                    # MACD
                    candidate.macd = calculate_macd(closes)
                    # 볼린저 밴드
                    candidate.bollinger_bands = calculate_bollinger_bands(closes)
                    # 이동평균
                    mas = calculate_moving_averages(closes)
                    candidate.ma5 = mas.get('ma5')
                    candidate.ma20 = mas.get('ma20')
                    candidate.ma60 = mas.get('ma60')

                    # 가격 위치 판단
                    current = closes[-1] if closes else 0
                    if candidate.ma5 and candidate.ma20:
                        if current > candidate.ma5 > candidate.ma20:
                            candidate.price_position = 'above_all'
                        elif current < candidate.ma5 < candidate.ma20:
                            candidate.price_position = 'below_all'
                        else:
                            candidate.price_position = 'between'

                stats['success'] += 1
                indicators = []
                if candidate.rsi:
                    indicators.append(f"RSI={candidate.rsi:.1f}")
                if candidate.macd:
                    indicators.append(f"MACD={candidate.macd['macd']:.2f}")
                if candidate.bollinger_bands:
                    indicators.append(f"BB={candidate.bollinger_bands['position']*100:.0f}%")
                if verbose:
                    print(f"✓ {', '.join(indicators) if indicators else '지표 계산됨'}")
            else:
                if verbose:
                    print("⚠ 데이터 없음")
        except Exception as e:
            if verbose:
                print(f"✗ {e}")

        time.sleep(0.05)

        # 5. 증권사별 매매 (ka10078)
        stats['total'] += 1
        if verbose:
            print(f"   📊 [5/7] 증권사별 매매 (ka10078)...", end=" ")
        try:
            buy_count = 0
            total_net = 0
            for firm_code, firm_name in self.MAJOR_BROKERS[:3]:  # 상위 3개만
                firm_data = self.market_api.get_securities_firm_trading(
                    firm_code=firm_code,
                    stock_code=candidate.code,
                    days=1
                )
                if firm_data and len(firm_data) > 0:
                    net_qty = firm_data[0].get('net_qty', 0)
                    if net_qty > 0:
                        buy_count += 1
                        total_net += net_qty
                time.sleep(0.03)

            candidate.top_broker_buy_count = buy_count
            candidate.top_broker_net_buy = total_net
            stats['success'] += 1
            if verbose:
                print(f"✓ {buy_count}/3 증권사 순매수")
        except Exception as e:
            if verbose:
                print(f"✗ {e}")

        # 6. 체결강도 (ka10047)
        stats['total'] += 1
        cache_key = f"exec_{candidate.code}"
        cached = _get_from_cache(cache_key)
        if verbose:
            print(f"   📊 [6/7] 체결강도 (ka10047)...", end=" ")
        try:
            if cached:
                candidate.execution_intensity = cached.get('execution_intensity')
                stats['success'] += 1
                if verbose:
                    val = candidate.execution_intensity or 0
                    print(f"✓ {val:.1f} [캐시]")
            else:
                exec_data = self.market_api.get_execution_intensity(candidate.code)
                if exec_data:
                    candidate.execution_intensity = exec_data.get('execution_intensity')
                    _save_to_cache(cache_key, exec_data)
                    stats['success'] += 1
                    if verbose:
                        val = candidate.execution_intensity or 0
                        print(f"✓ {val:.1f}")
                else:
                    if verbose:
                        print("⚠ 데이터 없음")
        except Exception as e:
            if verbose:
                print(f"✗ {e}")

        time.sleep(0.05)

        # 7. 프로그램매매 (ka90013)
        stats['total'] += 1
        cache_key = f"prog_{candidate.code}"
        cached = _get_from_cache(cache_key)
        if verbose:
            print(f"   📊 [7/7] 프로그램매매 (ka90013)...", end=" ")
        try:
            if cached:
                candidate.program_net_buy = cached.get('program_net_buy')
                candidate.program_buy = cached.get('program_buy', 0)
                candidate.program_sell = cached.get('program_sell', 0)
                stats['success'] += 1
                if verbose:
                    val = candidate.program_net_buy or 0
                    print(f"✓ {val:,}원 [캐시]")
            else:
                prog_data = self.market_api.get_program_trading(candidate.code)
                if prog_data:
                    candidate.program_net_buy = prog_data.get('program_net_buy')
                    candidate.program_buy = prog_data.get('program_buy', 0)
                    candidate.program_sell = prog_data.get('program_sell', 0)
                    _save_to_cache(cache_key, prog_data)
                    stats['success'] += 1
                    if verbose:
                        val = candidate.program_net_buy or 0
                        print(f"✓ {val:,}원")
                else:
                    if verbose:
                        print("⚠ 데이터 없음")
        except Exception as e:
            if verbose:
                print(f"✗ {e}")

    def _fetch_extended_apis(
        self,
        candidate: 'StockCandidate',
        stats: Dict[str, int],
        verbose: bool
    ):
        """확장 API 수집 (병렬)"""

        if verbose:
            print(f"   📊 확장 API 수집 중...")

        # 외국인 연속 매매 조회
        stats['total'] += 1
        try:
            foreign_cont = self.market_api.get_foreign_continuous_trading_rank(
                market='KOSPI', trade_type='buy', limit=100
            )
            if foreign_cont:
                for item in foreign_cont:
                    if item.get('code') == candidate.code:
                        candidate.foreign_continuous_days = item.get('continuous_days', 0)
                        break
                stats['success'] += 1
        except Exception:
            pass

        # 신용비율 조회
        stats['total'] += 1
        try:
            credit_rank = self.market_api.get_credit_ratio_rank(market='KOSPI', limit=100)
            if credit_rank:
                for item in credit_rank:
                    if item.get('code') == candidate.code:
                        candidate.credit_ratio = item.get('credit_ratio')
                        break
                stats['success'] += 1
        except Exception:
            pass

        # 거래량 급증 조회
        stats['total'] += 1
        try:
            vol_surge = self.market_api.get_volume_surge_rank(market='ALL', limit=100)
            if vol_surge:
                for idx, item in enumerate(vol_surge):
                    if item.get('code') == candidate.code:
                        candidate.volume_surge_rank = idx + 1
                        break
                stats['success'] += 1
        except Exception:
            pass

        # 거래대금 계산
        candidate.trading_value = candidate.price * candidate.volume

    def _fetch_openapi_data(
        self,
        candidate: 'StockCandidate',
        stats: Dict[str, int],
        verbose: bool
    ):
        """OpenAPI Comprehensive Data 수집 (20가지)"""

        if verbose:
            print(f"   📊 OpenAPI 종합 데이터 (20가지)...", end=" ")

        stats['total'] += 1
        try:
            comp_data = self.openapi_client.get_comprehensive_data(candidate.code)

            if comp_data and 'data' in comp_data:
                candidate.openapi_data = comp_data

                # 특징 추출
                features = self.openapi_client.extract_openapi_features(comp_data)

                if features:
                    # 시가총액
                    if 'market_cap' in features:
                        candidate.market_cap = features['market_cap']

                    # 일봉 추세
                    if 'daily_trend' in features:
                        candidate.daily_trend = features['daily_trend']

                    # 분봉 데이터
                    if 'minute_data_count' in features:
                        candidate.minute_data_count = features['minute_data_count']
                    if 'recent_price_action' in features:
                        candidate.minute_trend = features['recent_price_action']

                    # OpenAPI에서 가져온 투자자 데이터로 보강
                    if 'institutional_net_buy_openapi' in features and features['institutional_net_buy_openapi']:
                        if candidate.institutional_net_buy == 0:
                            candidate.institutional_net_buy = features['institutional_net_buy_openapi']
                    if 'foreign_net_buy_openapi' in features and features['foreign_net_buy_openapi']:
                        if candidate.foreign_net_buy == 0:
                            candidate.foreign_net_buy = features['foreign_net_buy_openapi']
                    if 'program_net_buy' in features and features['program_net_buy']:
                        if candidate.program_net_buy is None:
                            candidate.program_net_buy = features['program_net_buy']

                success_count = comp_data.get('success_count', 0)
                total_count = comp_data.get('total_count', 1)
                stats['success'] += 1
                if verbose:
                    print(f"✓ {success_count}/{total_count}")
            else:
                if verbose:
                    print("⚠ 응답 없음")

        except Exception as e:
            if verbose:
                print(f"✗ {e}")

    def _fetch_aggregator_data(
        self,
        candidate: 'StockCandidate',
        stats: Dict[str, int],
        verbose: bool
    ):
        """API Aggregator 데이터 연동"""

        if verbose:
            print(f"   📊 시장 흐름 신호 분석...", end=" ")

        stats['total'] += 1
        try:
            # 외국인+기관 동시 순매수 종목 확인
            combined_stocks = self.api_aggregator.get_combined_buy_signals()
            if candidate.code in combined_stocks:
                candidate.combined_buy_signal = True
                candidate.market_signals.append("외국인+기관 동시 순매수")

            # 최근 시장 신호 확인
            recent_signals = self.api_aggregator.get_recent_signals(minutes=5)
            for signal in recent_signals:
                if signal.signal_type == 'bullish':
                    candidate.market_signals.append(f"강세: {signal.description}")
                elif signal.signal_type == 'bearish':
                    candidate.market_signals.append(f"약세: {signal.description}")

            # 시장 스냅샷
            snapshot = self.api_aggregator.get_market_snapshot()
            if snapshot.foreign_flow > 0:
                candidate.foreign_flow_signal = 'bullish'
            elif snapshot.foreign_flow < 0:
                candidate.foreign_flow_signal = 'bearish'

            if snapshot.institution_flow > 0:
                candidate.institution_flow_signal = 'bullish'
            elif snapshot.institution_flow < 0:
                candidate.institution_flow_signal = 'bearish'

            if snapshot.program_flow > 0:
                candidate.program_flow_signal = 'bullish'
            elif snapshot.program_flow < 0:
                candidate.program_flow_signal = 'bearish'

            stats['success'] += 1
            if verbose:
                signal_count = len(candidate.market_signals)
                combined = "✓ 외+기" if candidate.combined_buy_signal else ""
                print(f"✓ {signal_count}개 신호 {combined}")

        except Exception as e:
            if verbose:
                print(f"✗ {e}")

    def _calculate_comprehensive_score(self, candidate: 'StockCandidate') -> float:
        """
        종합 점수 계산 (0-100)

        가중치:
        - 기관/외국인 매매: 30%
        - 기술적 지표: 25%
        - 거래량/체결강도: 20%
        - 시장 신호: 15%
        - 추세: 10%
        """
        score = 0.0
        breakdown = {}

        # 1. 기관/외국인 매매 점수 (30점)
        investor_score = 0.0
        if candidate.institutional_net_buy > 50_000_000:
            investor_score += 15
        elif candidate.institutional_net_buy > 20_000_000:
            investor_score += 10
        elif candidate.institutional_net_buy > 10_000_000:
            investor_score += 5

        if candidate.foreign_net_buy > 50_000_000:
            investor_score += 15
        elif candidate.foreign_net_buy > 20_000_000:
            investor_score += 10
        elif candidate.foreign_net_buy > 10_000_000:
            investor_score += 5

        # 외국인+기관 동시 순매수 보너스
        if candidate.combined_buy_signal:
            investor_score += 10

        breakdown['investor'] = min(investor_score, 30)
        score += breakdown['investor']

        # 2. 기술적 지표 점수 (25점)
        tech_score = 0.0

        # RSI
        if candidate.rsi:
            if 30 <= candidate.rsi <= 50:  # 과매도 구간에서 반등
                tech_score += 10
            elif 50 <= candidate.rsi <= 70:  # 상승 추세
                tech_score += 7
            elif candidate.rsi < 30:  # 과매도
                tech_score += 5

        # 볼린저 밴드
        if candidate.bollinger_bands:
            bb_pos = candidate.bollinger_bands['position']
            if 0.2 <= bb_pos <= 0.5:  # 하단에서 중간
                tech_score += 8
            elif 0.5 <= bb_pos <= 0.8:  # 중간에서 상단
                tech_score += 5

        # 이동평균 위치
        if candidate.price_position == 'above_all':
            tech_score += 7
        elif candidate.price_position == 'between':
            tech_score += 3

        breakdown['technical'] = min(tech_score, 25)
        score += breakdown['technical']

        # 3. 거래량/체결강도 점수 (20점)
        volume_score = 0.0

        if candidate.volume_ratio:
            if candidate.volume_ratio > 5:
                volume_score += 10
            elif candidate.volume_ratio > 3:
                volume_score += 7
            elif candidate.volume_ratio > 2:
                volume_score += 5

        if candidate.execution_intensity:
            if candidate.execution_intensity > 150:
                volume_score += 10
            elif candidate.execution_intensity > 120:
                volume_score += 7
            elif candidate.execution_intensity > 100:
                volume_score += 5

        breakdown['volume'] = min(volume_score, 20)
        score += breakdown['volume']

        # 4. 시장 신호 점수 (15점)
        signal_score = 0.0

        if candidate.foreign_flow_signal == 'bullish':
            signal_score += 5
        if candidate.institution_flow_signal == 'bullish':
            signal_score += 5
        if candidate.program_flow_signal == 'bullish':
            signal_score += 3

        signal_score += len(candidate.market_signals) * 2

        breakdown['signals'] = min(signal_score, 15)
        score += breakdown['signals']

        # 5. 추세 점수 (10점)
        trend_score = 0.0

        if candidate.daily_trend == 'up':
            trend_score += 5
        if candidate.minute_trend in ['strong_up', 'weak_up']:
            trend_score += 5

        if candidate.foreign_continuous_days >= 5:
            trend_score += 5
        elif candidate.foreign_continuous_days >= 3:
            trend_score += 3

        breakdown['trend'] = min(trend_score, 10)
        score += breakdown['trend']

        # breakdown 저장
        candidate.deep_scan_breakdown = breakdown

        return min(score, 100)


# =========================================================================
# 모듈 함수 (기존 호환)
# =========================================================================
def comprehensive_deep_scan(
    candidates: List['StockCandidate'],
    market_api,
    openapi_client=None,
    api_aggregator=None,
    max_candidates: int = 50,
    verbose: bool = True
) -> List['StockCandidate']:
    """
    통합 Deep Scan 실행 (기존 호환 함수)

    Args:
        candidates: 후보 종목 리스트
        market_api: MarketAPI 인스턴스
        openapi_client: KiwoomOpenAPIClient (선택)
        api_aggregator: APIDataAggregator (선택)
        max_candidates: 최대 처리 종목 수
        verbose: 상세 로그 출력

    Returns:
        enrichment된 종목 리스트
    """
    scanner = ComprehensiveDeepScanner(
        market_api=market_api,
        openapi_client=openapi_client,
        api_aggregator=api_aggregator
    )

    return scanner.scan_candidates(candidates, max_candidates, verbose)


__all__ = [
    'ComprehensiveDeepScanner',
    'comprehensive_deep_scan',
    'calculate_rsi',
    'calculate_macd',
    'calculate_bollinger_bands',
    'calculate_moving_averages',
]
