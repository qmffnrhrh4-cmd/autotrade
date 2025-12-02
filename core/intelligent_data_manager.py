"""
Intelligent Data Manager - 지능형 데이터 관리자
5단계 캐싱 + 배치 조회 + 선제적 로딩
"""
import time
import threading
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

from utils.logger_new import get_logger

logger = get_logger()


@dataclass
class CacheTier:
    """캐시 티어 설정"""
    name: str
    ttl_seconds: float
    max_size: int = 1000


class TieredCache:
    """5단계 티어드 캐시

    Tier 1: Hot (2초) - 현재가, 호가
    Tier 2: Warm (30초) - 보유 종목, 예수금
    Tier 3: Cool (5분) - 기술 지표, 점수
    Tier 4: Cold (30분) - 일봉 데이터, 평균 거래량
    Tier 5: Frozen (24시간) - 종목 정보, 재무 데이터
    """

    TIERS = {
        'hot': CacheTier('hot', 2.0, 500),        # 현재가
        'warm': CacheTier('warm', 30.0, 200),     # 보유 종목
        'cool': CacheTier('cool', 300.0, 500),   # 기술 지표
        'cold': CacheTier('cold', 1800.0, 1000), # 일봉 데이터
        'frozen': CacheTier('frozen', 86400.0, 2000)  # 종목 정보
    }

    def __init__(self):
        self._caches: Dict[str, Dict[str, Any]] = {tier: {} for tier in self.TIERS}
        self._timestamps: Dict[str, Dict[str, datetime]] = {tier: {} for tier in self.TIERS}
        self._locks: Dict[str, threading.RLock] = {tier: threading.RLock() for tier in self.TIERS}
        self._stats = defaultdict(lambda: {'hits': 0, 'misses': 0, 'evictions': 0})

    def get(self, tier: str, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        if tier not in self.TIERS:
            return None

        with self._locks[tier]:
            if key not in self._caches[tier]:
                self._stats[tier]['misses'] += 1
                return None

            # TTL 체크
            cached_time = self._timestamps[tier].get(key)
            if cached_time:
                age = (datetime.now() - cached_time).total_seconds()
                if age > self.TIERS[tier].ttl_seconds:
                    # 만료됨
                    del self._caches[tier][key]
                    del self._timestamps[tier][key]
                    self._stats[tier]['misses'] += 1
                    return None

            self._stats[tier]['hits'] += 1
            return self._caches[tier][key]

    def set(self, tier: str, key: str, value: Any):
        """캐시에 값 저장"""
        if tier not in self.TIERS:
            return

        with self._locks[tier]:
            # 용량 체크
            if len(self._caches[tier]) >= self.TIERS[tier].max_size:
                self._evict_oldest(tier)

            self._caches[tier][key] = value
            self._timestamps[tier][key] = datetime.now()

    def _evict_oldest(self, tier: str):
        """가장 오래된 항목 제거 (10% 제거)"""
        remove_count = max(1, len(self._caches[tier]) // 10)

        sorted_items = sorted(
            self._timestamps[tier].items(),
            key=lambda x: x[1]
        )

        for key, _ in sorted_items[:remove_count]:
            del self._caches[tier][key]
            del self._timestamps[tier][key]
            self._stats[tier]['evictions'] += 1

    def invalidate(self, tier: str = None, key: str = None):
        """캐시 무효화"""
        if tier and key:
            with self._locks[tier]:
                self._caches[tier].pop(key, None)
                self._timestamps[tier].pop(key, None)
        elif tier:
            with self._locks[tier]:
                self._caches[tier].clear()
                self._timestamps[tier].clear()
        else:
            for t in self.TIERS:
                with self._locks[t]:
                    self._caches[t].clear()
                    self._timestamps[t].clear()

    def get_stats(self) -> Dict:
        """통계 반환"""
        stats = {}
        for tier in self.TIERS:
            with self._locks[tier]:
                tier_stats = self._stats[tier].copy()
                tier_stats['size'] = len(self._caches[tier])
                tier_stats['max_size'] = self.TIERS[tier].max_size
                tier_stats['ttl'] = self.TIERS[tier].ttl_seconds
                total = tier_stats['hits'] + tier_stats['misses']
                tier_stats['hit_rate'] = (tier_stats['hits'] / total * 100) if total > 0 else 0
                stats[tier] = tier_stats
        return stats


class IntelligentDataManager:
    """지능형 데이터 관리자

    특징:
    - 5단계 티어드 캐싱
    - 배치 데이터 조회
    - 선제적 데이터 로딩
    - 데이터 버전 관리
    - 자동 무효화
    """

    def __init__(self, market_api=None, account_api=None, max_workers: int = 10):
        self.market_api = market_api
        self.account_api = account_api
        self.max_workers = max_workers

        self._cache = TieredCache()
        self._prefetch_queue: Set[str] = set()
        self._prefetch_lock = threading.Lock()

        # 데이터 버전 (무효화 트리거)
        self._versions: Dict[str, int] = defaultdict(int)
        self._version_lock = threading.Lock()

        # 배치 조회 대기열
        self._batch_queue: Dict[str, Set[str]] = defaultdict(set)
        self._batch_lock = threading.Lock()
        self._batch_event = threading.Event()

        # 통계
        self._stats = {
            'batch_fetches': 0,
            'single_fetches': 0,
            'prefetch_count': 0,
            'invalidations': 0
        }

        # 배치 처리 스레드 시작
        self._running = True
        self._batch_thread = threading.Thread(target=self._batch_processor, daemon=True)
        self._batch_thread.start()

        logger.info(f"IntelligentDataManager 초기화 (workers={max_workers})")

    def set_apis(self, market_api=None, account_api=None):
        """API 설정"""
        if market_api:
            self.market_api = market_api
        if account_api:
            self.account_api = account_api

    # === 현재가 조회 (Hot Tier) ===

    def get_price(self, stock_code: str) -> Optional[Dict]:
        """단일 종목 현재가 조회"""
        cached = self._cache.get('hot', f'price:{stock_code}')
        if cached:
            return cached

        if not self.market_api:
            return None

        try:
            price_data = self.market_api.get_stock_price(stock_code)
            if price_data:
                self._cache.set('hot', f'price:{stock_code}', price_data)
                self._stats['single_fetches'] += 1
            return price_data
        except Exception as e:
            logger.warning(f"가격 조회 실패 ({stock_code}): {e}")
            return None

    def get_prices_batch(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """여러 종목 현재가 배치 조회"""
        results = {}
        codes_to_fetch = []

        # 캐시 확인
        for code in stock_codes:
            cached = self._cache.get('hot', f'price:{code}')
            if cached:
                results[code] = cached
            else:
                codes_to_fetch.append(code)

        # 미캐시 종목 병렬 조회
        if codes_to_fetch and self.market_api:
            self._stats['batch_fetches'] += 1

            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(codes_to_fetch))) as executor:
                future_to_code = {
                    executor.submit(self.market_api.get_stock_price, code): code
                    for code in codes_to_fetch
                }

                for future in as_completed(future_to_code):
                    code = future_to_code[future]
                    try:
                        price_data = future.result()
                        if price_data:
                            self._cache.set('hot', f'price:{code}', price_data)
                            results[code] = price_data
                    except Exception as e:
                        logger.warning(f"가격 조회 실패 ({code}): {e}")

        return results

    # === 보유 종목 조회 (Warm Tier) ===

    def get_holdings(self, force_refresh: bool = False) -> List[Dict]:
        """보유 종목 조회"""
        if not force_refresh:
            cached = self._cache.get('warm', 'holdings')
            if cached:
                return cached

        if not self.account_api:
            return []

        try:
            holdings = self.account_api.get_holdings()
            if holdings is not None:
                self._cache.set('warm', 'holdings', holdings)
            return holdings or []
        except Exception as e:
            logger.warning(f"보유 종목 조회 실패: {e}")
            return []

    def get_deposit(self, force_refresh: bool = False) -> Optional[Dict]:
        """예수금 조회"""
        if not force_refresh:
            cached = self._cache.get('warm', 'deposit')
            if cached:
                return cached

        if not self.account_api:
            return None

        try:
            deposit = self.account_api.get_deposit()
            if deposit:
                self._cache.set('warm', 'deposit', deposit)
            return deposit
        except Exception as e:
            logger.warning(f"예수금 조회 실패: {e}")
            return None

    # === 기술 지표 (Cool Tier) ===

    def get_score(self, stock_code: str, stock_data: Dict, scoring_func: Callable) -> Optional[Dict]:
        """점수 조회 (캐시 + 계산)"""
        # 데이터 해시로 캐시 키 생성
        data_hash = self._compute_data_hash(stock_data)
        cache_key = f'score:{stock_code}:{data_hash}'

        cached = self._cache.get('cool', cache_key)
        if cached:
            return cached

        try:
            score = scoring_func(stock_data)
            if score:
                self._cache.set('cool', cache_key, score)
            return score
        except Exception as e:
            logger.warning(f"점수 계산 실패 ({stock_code}): {e}")
            return None

    def _compute_data_hash(self, data: Dict) -> str:
        """데이터 해시 계산"""
        # 가격, 거래량 등 변동성 높은 필드만 해시
        key_fields = ['current_price', 'volume', 'change_rate']
        hash_data = {k: data.get(k) for k in key_fields if k in data}
        return hashlib.md5(str(hash_data).encode()).hexdigest()[:8]

    # === 일봉 데이터 (Cold Tier) ===

    def get_daily_data(self, stock_code: str, days: int = 20) -> Optional[List[Dict]]:
        """일봉 데이터 조회"""
        cache_key = f'daily:{stock_code}:{days}'
        cached = self._cache.get('cold', cache_key)
        if cached:
            return cached

        if not self.market_api:
            return None

        try:
            # data_fetcher가 있으면 사용
            if hasattr(self.market_api, 'client') and hasattr(self.market_api.client, 'data_fetcher'):
                daily_data = self.market_api.client.data_fetcher.get_daily_ohlcv(stock_code, days)
            else:
                daily_data = None

            if daily_data:
                self._cache.set('cold', cache_key, daily_data)
            return daily_data
        except Exception as e:
            logger.warning(f"일봉 데이터 조회 실패 ({stock_code}): {e}")
            return None

    # === 종목 정보 (Frozen Tier) ===

    def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """종목 기본 정보 조회"""
        cached = self._cache.get('frozen', f'info:{stock_code}')
        if cached:
            return cached

        if not self.market_api:
            return None

        try:
            info = self.market_api.get_stock_info(stock_code)
            if info:
                self._cache.set('frozen', f'info:{stock_code}', info)
            return info
        except Exception as e:
            logger.warning(f"종목 정보 조회 실패 ({stock_code}): {e}")
            return None

    # === 선제적 로딩 ===

    def prefetch(self, stock_codes: List[str]):
        """선제적 데이터 로딩 예약"""
        with self._prefetch_lock:
            self._prefetch_queue.update(stock_codes)
            self._stats['prefetch_count'] += len(stock_codes)

    def _batch_processor(self):
        """배치 처리 스레드"""
        while self._running:
            try:
                # 선제적 로딩 처리
                codes_to_prefetch = []
                with self._prefetch_lock:
                    if self._prefetch_queue:
                        codes_to_prefetch = list(self._prefetch_queue)[:50]  # 최대 50개
                        self._prefetch_queue -= set(codes_to_prefetch)

                if codes_to_prefetch:
                    self.get_prices_batch(codes_to_prefetch)

                self._batch_event.wait(timeout=1.0)  # 1초 대기
                self._batch_event.clear()

            except Exception as e:
                logger.error(f"배치 처리 오류: {e}")
                time.sleep(1)

    # === 무효화 ===

    def invalidate_on_trade(self, stock_code: str = None):
        """거래 발생 시 관련 캐시 무효화"""
        # 보유 종목, 예수금 무효화
        self._cache.invalidate('warm')

        # 특정 종목 가격 무효화
        if stock_code:
            self._cache.invalidate('hot', f'price:{stock_code}')

        self._stats['invalidations'] += 1
        self._bump_version('trade')

    def invalidate_prices(self):
        """모든 가격 캐시 무효화"""
        self._cache.invalidate('hot')
        self._stats['invalidations'] += 1

    def _bump_version(self, category: str):
        """데이터 버전 증가"""
        with self._version_lock:
            self._versions[category] += 1

    def get_version(self, category: str) -> int:
        """데이터 버전 조회"""
        with self._version_lock:
            return self._versions[category]

    # === 통계 ===

    def get_stats(self) -> Dict:
        """통계 반환"""
        stats = self._stats.copy()
        stats['cache'] = self._cache.get_stats()
        stats['prefetch_queue_size'] = len(self._prefetch_queue)
        return stats

    def stop(self):
        """종료"""
        self._running = False
        self._batch_event.set()


# 싱글톤 인스턴스
_data_manager: Optional[IntelligentDataManager] = None
_instance_lock = threading.Lock()


def get_data_manager(market_api=None, account_api=None) -> IntelligentDataManager:
    """IntelligentDataManager 싱글톤 인스턴스 반환"""
    global _data_manager

    with _instance_lock:
        if _data_manager is None:
            _data_manager = IntelligentDataManager(market_api=market_api, account_api=account_api)
        elif market_api or account_api:
            _data_manager.set_apis(market_api, account_api)

    return _data_manager
