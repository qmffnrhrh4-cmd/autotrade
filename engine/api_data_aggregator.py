"""
engine/api_data_aggregator.py
전체 REST API 데이터 종합 수집기

모든 133개 Kiwoom REST API를 활용하여 시장 데이터를 수집하고 분석

Author: AutoTrade Pro
Version: 1.0
"""
import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class APIDataCategory:
    """API 데이터 카테고리"""
    INVESTOR = "investor"           # 투자자 동향
    PROGRAM = "program"             # 프로그램 매매
    FOREIGN = "foreign"             # 외국인 매매
    INSTITUTION = "institution"     # 기관 매매
    VOLUME = "volume"               # 거래량
    PRICE_CHANGE = "price_change"   # 등락률
    ORDERBOOK = "orderbook"         # 호가
    CHART = "chart"                 # 차트
    SECTOR = "sector"               # 업종
    THEME = "theme"                 # 테마
    SHORT_SELL = "short_sell"       # 공매도
    CREDIT = "credit"               # 신용


@dataclass
class MarketSignal:
    """시장 신호"""
    signal_type: str  # bullish, bearish, neutral
    strength: float  # 0-100
    source: str  # API ID
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class MarketSnapshot:
    """시장 스냅샷"""
    timestamp: datetime
    kospi: Dict[str, Any] = field(default_factory=dict)
    kosdaq: Dict[str, Any] = field(default_factory=dict)
    foreign_flow: float = 0.0
    institution_flow: float = 0.0
    program_flow: float = 0.0
    market_sentiment: str = "neutral"  # bullish, bearish, neutral
    active_signals: List[MarketSignal] = field(default_factory=list)


class APIDataAggregator:
    """
    전체 API 데이터 종합 수집기

    133개 Kiwoom REST API에서 데이터를 수집하고
    자동매매에 필요한 통합 시장 뷰를 제공
    """

    # API 정의: (api_id, interval_seconds, category, description)
    API_SCHEDULE = [
        # === 투자자 동향 (핵심) ===
        ('ka10059', 30, 'investor', '종목별 투자자기관별'),
        ('ka10063', 30, 'investor', '장중 투자자별 매매'),
        ('ka10065', 30, 'investor', '장중 투자자별 매매 상위'),
        ('ka10066', 60, 'investor', '장마감후 투자자별 매매'),
        ('ka10078', 60, 'investor', '증권사별 종목 매매 동향'),

        # === 외국인 매매 ===
        ('ka10034', 30, 'foreign', '외인 기간별 매매 상위'),
        ('ka10035', 60, 'foreign', '외인 연속 순매매 상위'),
        ('ka10036', 120, 'foreign', '외인 한도소진율 증가 상위'),
        ('ka10037', 60, 'foreign', '외국계 창구 매매 상위'),
        ('ka10131', 120, 'foreign', '기관외국인 연속매매 현황'),
        ('ka90009', 60, 'foreign', '외국인기관 매매 상위'),

        # === 기관 매매 ===
        ('ka10045', 60, 'institution', '종목별 기관 매매 추이'),
        ('ka10058', 120, 'institution', '투자자별 일별 매매 종목'),

        # === 프로그램 매매 ===
        ('ka90004', 60, 'program', '종목별 프로그램 매매 현황'),
        ('ka90005', 30, 'program', '프로그램 매매 추이 시간별'),
        ('ka90007', 60, 'program', '프로그램 매매 누적 추이'),
        ('ka90008', 120, 'program', '종목 시간별 프로그램 매매'),
        ('ka90013', 300, 'program', '종목 일별 프로그램 매매'),
        ('ka10010', 60, 'program', '업종 프로그램'),

        # === 거래량/거래대금 ===
        ('ka10031', 60, 'volume', '전일 거래량 상위'),
        ('ka10032', 60, 'volume', '거래대금 상위'),
        ('ka10023', 30, 'volume', '거래량 급증'),
        ('ka10055', 60, 'volume', '당일전일 체결량'),
        ('ka10052', 30, 'volume', '거래원 순간 거래량'),

        # === 등락률 ===
        ('ka10027', 30, 'price_change', '전일대비 등락률 상위'),
        ('ka10028', 60, 'price_change', '시가대비 등락률'),
        ('ka10029', 30, 'price_change', '예상 체결 등락률 상위'),
        ('ka10019', 60, 'price_change', '가격 급등락'),
        ('ka10098', 120, 'price_change', '시간외 단일가 등락률'),

        # === 호가/잔량 ===
        ('ka10020', 30, 'orderbook', '호가 잔량 상위'),
        ('ka10021', 30, 'orderbook', '호가 잔량 급증'),
        ('ka10022', 60, 'orderbook', '잔량율 급증'),
        ('ka10025', 120, 'orderbook', '매물대 집중'),

        # === 업종 ===
        ('ka20001', 60, 'sector', '업종 현재가'),
        ('ka20002', 120, 'sector', '업종별 주가'),
        ('ka20003', 300, 'sector', '전업종 지수'),
        ('ka20009', 300, 'sector', '업종 현재가 일별'),
        ('ka10051', 120, 'sector', '업종별 투자자 순매수'),

        # === 테마 ===
        ('ka90001', 300, 'theme', '테마 그룹별'),
        ('ka90002', 300, 'theme', '테마 구성 종목'),

        # === 공매도/대차 ===
        ('ka10014', 300, 'short_sell', '공매도 추이'),
        ('ka10068', 300, 'short_sell', '대차거래 추이'),
        ('ka10069', 300, 'short_sell', '대차거래 상위 10종목'),
        ('ka90012', 300, 'short_sell', '대차거래 내역'),
        ('ka20068', 600, 'short_sell', '대차거래 추이'),

        # === 신용 ===
        ('ka10013', 300, 'credit', '신용매매 동향'),
        ('ka10033', 120, 'credit', '신용비율 상위'),

        # === 거래원/증권사 ===
        ('ka10038', 120, 'broker', '종목별 증권사 순위'),
        ('ka10039', 120, 'broker', '증권사별 매매 상위'),
        ('ka10040', 60, 'broker', '당일 주요 거래원'),
        ('ka10042', 120, 'broker', '순매수 거래원 순위'),
        ('ka10043', 300, 'broker', '거래원 매물대 분석'),

        # === 기타 시장 정보 ===
        ('ka10016', 600, 'market', '신고저가'),
        ('ka10017', 60, 'market', '상하한가'),
        ('ka10018', 120, 'market', '고저가 근접'),
        ('ka10026', 300, 'market', '고저 PER'),
        ('ka10054', 30, 'market', '변동성 완화장치 (VI)'),

        # === 체결 정보 ===
        ('ka10003', 10, 'execution', '체결 정보'),
        ('ka10046', 60, 'execution', '체결강도 시간별'),
        ('ka10047', 60, 'execution', '체결강도 일별'),
    ]

    def __init__(
        self,
        client,
        max_workers: int = 10,
        enable_all_apis: bool = True
    ):
        """
        Args:
            client: KiwoomRESTClient
            max_workers: 병렬 처리 스레드 수
            enable_all_apis: 모든 API 활성화 여부
        """
        self.client = client
        self.max_workers = max_workers
        self.enable_all_apis = enable_all_apis

        # 스레드 풀
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 데이터 저장소
        self.data_store: Dict[str, Dict] = defaultdict(dict)
        self.last_fetch_time: Dict[str, datetime] = {}

        # 시장 신호
        self.market_signals: List[MarketSignal] = []
        self.signal_history: List[MarketSnapshot] = []

        # 상태
        self.is_running = False
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

        # 콜백
        self.on_signal_detected: Optional[Callable] = None
        self.on_market_change: Optional[Callable] = None

        logger.info(f"📊 API 데이터 수집기 초기화: {len(self.API_SCHEDULE)}개 API")

    def start(self):
        """데이터 수집 시작"""
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()

        # 수집 스레드 시작
        thread = threading.Thread(
            target=self._collection_loop,
            name="APIDataAggregator",
            daemon=True
        )
        thread.start()

        logger.info("✅ API 데이터 수집 시작")

    def stop(self):
        """데이터 수집 중지"""
        self.is_running = False
        self._stop_event.set()
        logger.info("🛑 API 데이터 수집 중지")

    def _collection_loop(self):
        """데이터 수집 루프"""
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                tasks = []

                for api_id, interval, category, description in self.API_SCHEDULE:
                    last_time = self.last_fetch_time.get(api_id, datetime.min)
                    elapsed = (now - last_time).total_seconds()

                    if elapsed >= interval:
                        tasks.append((api_id, category, description))

                if tasks:
                    self._fetch_batch(tasks)

                time.sleep(1)

            except Exception as e:
                logger.error(f"데이터 수집 루프 오류: {e}")
                time.sleep(5)

    def _fetch_batch(self, tasks: List[tuple]):
        """배치 데이터 수집"""
        futures = {}

        for api_id, category, description in tasks:
            future = self.executor.submit(
                self._fetch_single_api,
                api_id, category, description
            )
            futures[future] = (api_id, category)

        try:
            for future in as_completed(futures, timeout=30):
                try:
                    api_id, category = futures[future]
                    result = future.result()

                    if result:
                        self._process_result(api_id, category, result)
                        self.last_fetch_time[api_id] = datetime.now()

                except Exception as e:
                    api_id, _ = futures[future]
                    logger.debug(f"API {api_id} 수집 실패: {e}")
        except TimeoutError:
            # 타임아웃 시 미완료 futures 취소
            for future in futures:
                if not future.done():
                    future.cancel()
            logger.debug("일부 API 수집 타임아웃 - 다음 주기에 재시도")

    def _fetch_single_api(self, api_id: str, category: str, description: str) -> Optional[Dict]:
        """단일 API 호출 (RankingAPI 우선 사용)"""
        try:
            # RankingAPI로 직접 호출 시도 (더 안정적)
            result = self._call_ranking_api(api_id)

            if result:
                return {
                    'data': {'items': result, 'return_code': 0},
                    'timestamp': datetime.now(),
                    'category': category,
                    'description': description
                }

            # fallback: call_verified_api 사용
            result = self.client.call_verified_api(
                api_id=api_id,
                variant_idx=1
            )

            if result and result.get('return_code') == 0:
                return {
                    'data': result,
                    'timestamp': datetime.now(),
                    'category': category,
                    'description': description
                }

        except Exception as e:
            logger.debug(f"API {api_id} 호출 실패: {e}")

        return None

    def _call_ranking_api(self, api_id: str) -> Optional[List]:
        """RankingAPI로 직접 호출"""
        try:
            from api.market.ranking import RankingAPI
            ranking = RankingAPI(self.client)

            if api_id == 'ka10031':  # 거래량 상위
                return ranking.get_volume_rank(market='ALL', limit=50)
            elif api_id == 'ka10032':  # 거래대금 상위
                return ranking.get_trading_value_rank(market='ALL', limit=50)
            elif api_id == 'ka10027':  # 등락률 상위
                return ranking.get_price_change_rank(market='ALL', sort='rise', limit=50)
            elif api_id == 'ka10034':  # 외인 기간별 매매
                return ranking.get_foreign_period_trading_rank(market='KOSPI', trade_type='buy', limit=30)
            elif api_id == 'ka90009':  # 외국인기관 매매 상위
                return ranking.get_foreign_institution_trading_rank(market='KOSPI', limit=30)
            elif api_id == 'ka10020':  # 호가 잔량 상위
                return ranking.get_orderbook_rank(market='ALL', limit=30)
            elif api_id == 'ka20001':  # 업종 현재가
                return ranking.get_sector_price(market='KOSPI')

        except Exception as e:
            logger.debug(f"RankingAPI {api_id} 실패: {e}")

        return None

    def _process_result(self, api_id: str, category: str, result: Dict):
        """결과 처리 및 신호 감지"""
        with self._lock:
            self.data_store[api_id] = result

        # 카테고리별 신호 감지
        signals = self._detect_signals(api_id, category, result.get('data', {}))

        for signal in signals:
            self.market_signals.append(signal)

            if self.on_signal_detected:
                self.on_signal_detected(signal)

    def _detect_signals(self, api_id: str, category: str, data: Dict) -> List[MarketSignal]:
        """시장 신호 감지"""
        signals = []

        try:
            if category == 'foreign':
                signal = self._analyze_foreign_data(api_id, data)
                if signal:
                    signals.append(signal)

            elif category == 'institution':
                signal = self._analyze_institution_data(api_id, data)
                if signal:
                    signals.append(signal)

            elif category == 'program':
                signal = self._analyze_program_data(api_id, data)
                if signal:
                    signals.append(signal)

            elif category == 'volume':
                signal = self._analyze_volume_data(api_id, data)
                if signal:
                    signals.append(signal)

            elif category == 'market':
                signal = self._analyze_market_data(api_id, data)
                if signal:
                    signals.append(signal)

        except Exception as e:
            logger.debug(f"신호 감지 오류 ({api_id}): {e}")

        return signals

    def _analyze_foreign_data(self, api_id: str, data: Dict) -> Optional[MarketSignal]:
        """외국인 데이터 분석"""
        # 외국인 순매수 상위 종목에서 신호 추출
        if api_id == 'ka10034':
            items = data.get('frgn_list', [])
            if items:
                total_buy = sum(int(item.get('net_buy', 0)) for item in items[:10])

                if total_buy > 100000000000:  # 1000억 이상 순매수
                    return MarketSignal(
                        signal_type='bullish',
                        strength=min(100, total_buy / 10000000000),  # 100억당 10점
                        source=api_id,
                        description=f"외국인 대량 순매수: {total_buy/100000000:.0f}억원",
                        metadata={'total_buy': total_buy, 'top_stocks': items[:5]}
                    )
                elif total_buy < -100000000000:  # 1000억 이상 순매도
                    return MarketSignal(
                        signal_type='bearish',
                        strength=min(100, abs(total_buy) / 10000000000),
                        source=api_id,
                        description=f"외국인 대량 순매도: {abs(total_buy)/100000000:.0f}억원",
                        metadata={'total_sell': abs(total_buy), 'top_stocks': items[:5]}
                    )

        return None

    def _analyze_institution_data(self, api_id: str, data: Dict) -> Optional[MarketSignal]:
        """기관 데이터 분석"""
        if api_id == 'ka10045':
            items = data.get('inst_list', [])
            if items:
                total_buy = sum(int(item.get('net_buy', 0)) for item in items[:10])

                if total_buy > 50000000000:  # 500억 이상
                    return MarketSignal(
                        signal_type='bullish',
                        strength=min(80, total_buy / 5000000000),
                        source=api_id,
                        description=f"기관 대량 순매수: {total_buy/100000000:.0f}억원",
                        metadata={'total_buy': total_buy}
                    )

        return None

    def _analyze_program_data(self, api_id: str, data: Dict) -> Optional[MarketSignal]:
        """프로그램 매매 분석"""
        if api_id == 'ka90005':
            program_buy = int(data.get('program_buy', 0))
            program_sell = int(data.get('program_sell', 0))
            net = program_buy - program_sell

            if abs(net) > 30000000000:  # 300억 이상
                signal_type = 'bullish' if net > 0 else 'bearish'
                return MarketSignal(
                    signal_type=signal_type,
                    strength=min(70, abs(net) / 5000000000),
                    source=api_id,
                    description=f"프로그램 {'순매수' if net > 0 else '순매도'}: {abs(net)/100000000:.0f}억원",
                    metadata={'net': net, 'buy': program_buy, 'sell': program_sell}
                )

        return None

    def _analyze_volume_data(self, api_id: str, data: Dict) -> Optional[MarketSignal]:
        """거래량 분석"""
        if api_id == 'ka10023':  # 거래량 급증
            items = data.get('vol_surge_list', [])
            if len(items) > 20:  # 급증 종목 20개 이상
                return MarketSignal(
                    signal_type='bullish',
                    strength=min(60, len(items) * 2),
                    source=api_id,
                    description=f"거래량 급증 종목 다수: {len(items)}개",
                    metadata={'count': len(items), 'stocks': items[:10]}
                )

        return None

    def _analyze_market_data(self, api_id: str, data: Dict) -> Optional[MarketSignal]:
        """시장 데이터 분석"""
        if api_id == 'ka10054':  # VI (변동성 완화장치)
            vi_count = len(data.get('vi_list', []))
            if vi_count >= 5:
                return MarketSignal(
                    signal_type='neutral',
                    strength=vi_count * 10,
                    source=api_id,
                    description=f"VI 발동 종목 다수: {vi_count}개 (변동성 주의)",
                    metadata={'vi_count': vi_count}
                )

        return None

    # ========== 데이터 조회 메서드 ==========

    def get_market_snapshot(self) -> MarketSnapshot:
        """현재 시장 스냅샷 조회"""
        with self._lock:
            # 최근 신호들
            recent_signals = [
                s for s in self.market_signals
                if (datetime.now() - s.timestamp).seconds < 300
            ]

            # 시장 심리 판단
            bullish_count = sum(1 for s in recent_signals if s.signal_type == 'bullish')
            bearish_count = sum(1 for s in recent_signals if s.signal_type == 'bearish')

            if bullish_count > bearish_count + 2:
                sentiment = 'bullish'
            elif bearish_count > bullish_count + 2:
                sentiment = 'bearish'
            else:
                sentiment = 'neutral'

            # 외국인/기관/프로그램 흐름
            foreign_flow = self._get_latest_flow('foreign')
            institution_flow = self._get_latest_flow('institution')
            program_flow = self._get_latest_flow('program')

            return MarketSnapshot(
                timestamp=datetime.now(),
                foreign_flow=foreign_flow,
                institution_flow=institution_flow,
                program_flow=program_flow,
                market_sentiment=sentiment,
                active_signals=recent_signals[-10:]  # 최근 10개
            )

    def _get_latest_flow(self, category: str) -> float:
        """카테고리별 최근 자금 흐름"""
        total = 0
        count = 0

        for api_id, result in self.data_store.items():
            if result.get('category') == category:
                data = result.get('data', {})
                net = data.get('net_buy', 0) or data.get('net', 0)
                if net:
                    total += int(net)
                    count += 1

        return total / max(count, 1)

    def get_foreign_top_stocks(self, limit: int = 20) -> List[Dict]:
        """외국인 순매수 상위 종목"""
        result = self.data_store.get('ka10034', {})
        items = result.get('data', {}).get('frgn_list', [])
        return items[:limit]

    def get_institution_top_stocks(self, limit: int = 20) -> List[Dict]:
        """기관 순매수 상위 종목"""
        result = self.data_store.get('ka10045', {})
        items = result.get('data', {}).get('inst_list', [])
        return items[:limit]

    def get_volume_surge_stocks(self, limit: int = 20) -> List[Dict]:
        """거래량 급증 종목"""
        result = self.data_store.get('ka10023', {})
        items = result.get('data', {}).get('vol_surge_list', [])
        return items[:limit]

    def get_price_top_stocks(self, limit: int = 20) -> List[Dict]:
        """등락률 상위 종목"""
        result = self.data_store.get('ka10027', {})
        items = result.get('data', {}).get('rate_list', [])
        return items[:limit]

    def get_program_trading_trend(self) -> Dict:
        """프로그램 매매 추이"""
        return self.data_store.get('ka90005', {}).get('data', {})

    def get_sector_data(self) -> List[Dict]:
        """업종별 데이터"""
        result = self.data_store.get('ka20003', {})
        return result.get('data', {}).get('sector_list', [])

    def get_signals_by_type(self, signal_type: str) -> List[MarketSignal]:
        """신호 유형별 조회"""
        return [s for s in self.market_signals if s.signal_type == signal_type]

    def get_recent_signals(self, minutes: int = 5) -> List[MarketSignal]:
        """최근 신호 조회"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [s for s in self.market_signals if s.timestamp > cutoff]

    def get_combined_buy_signals(self) -> List[str]:
        """
        외국인 + 기관 동시 순매수 종목

        자동매매에서 가장 중요한 신호 중 하나
        """
        foreign_stocks = set()
        inst_stocks = set()

        # 외국인 순매수
        for item in self.get_foreign_top_stocks(50):
            if int(item.get('net_buy', 0)) > 0:
                foreign_stocks.add(item.get('stk_cd', ''))

        # 기관 순매수
        for item in self.get_institution_top_stocks(50):
            if int(item.get('net_buy', 0)) > 0:
                inst_stocks.add(item.get('stk_cd', ''))

        # 교집합
        combined = foreign_stocks & inst_stocks
        combined.discard('')

        return list(combined)

    def get_api_coverage_stats(self) -> Dict:
        """API 수집 커버리지 통계"""
        total = len(self.API_SCHEDULE)
        collected = len(self.data_store)

        categories = defaultdict(int)
        for api_id, interval, category, _ in self.API_SCHEDULE:
            if api_id in self.data_store:
                categories[category] += 1

        return {
            'total_apis': total,
            'collected_apis': collected,
            'coverage_rate': collected / total * 100,
            'by_category': dict(categories),
            'last_update': max(self.last_fetch_time.values()) if self.last_fetch_time else None
        }


__all__ = ['APIDataAggregator', 'MarketSignal', 'MarketSnapshot']
