"""
Batch Price Fetcher - N+1 문제 해결을 위한 배치 가격 조회
ThreadPoolExecutor를 사용하여 여러 종목의 가격을 병렬로 조회
"""
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

from utils.logger_new import get_logger

logger = get_logger()


@dataclass
class PriceData:
    """가격 데이터"""
    stock_code: str
    current_price: int
    change_rate: float
    volume: int
    high_price: int = 0
    low_price: int = 0
    open_price: int = 0
    fetched_at: datetime = field(default_factory=datetime.now)

    @property
    def is_stale(self) -> bool:
        """데이터가 만료되었는지 확인 (5초 이상)"""
        return (datetime.now() - self.fetched_at).total_seconds() > 5


class BatchPriceFetcher:
    """배치 가격 조회기

    특징:
    - ThreadPoolExecutor로 병렬 조회
    - 인메모리 캐시로 중복 요청 방지
    - 자동 만료 및 갱신
    """

    def __init__(self, market_api=None, max_workers: int = 10, cache_ttl: float = 5.0):
        self.market_api = market_api
        self.max_workers = max_workers
        self.cache_ttl = cache_ttl  # 캐시 TTL (초)

        # 캐시: {stock_code: PriceData}
        self._cache: Dict[str, PriceData] = {}
        self._cache_lock = threading.RLock()

        # 성능 통계
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'batch_fetches': 0,
            'single_fetches': 0,
            'errors': 0,
            'avg_batch_time_ms': 0
        }
        self._stats_lock = threading.Lock()

        logger.info(f"BatchPriceFetcher 초기화 (workers={max_workers}, cache_ttl={cache_ttl}s)")

    def set_market_api(self, market_api):
        """Market API 설정"""
        self.market_api = market_api

    def get_prices(self, stock_codes: List[str]) -> Dict[str, PriceData]:
        """여러 종목의 가격을 배치로 조회

        Args:
            stock_codes: 종목 코드 리스트

        Returns:
            {stock_code: PriceData} 딕셔너리
        """
        if not stock_codes:
            return {}

        with self._stats_lock:
            self._stats['total_requests'] += len(stock_codes)

        # 캐시에서 유효한 데이터 확인
        results: Dict[str, PriceData] = {}
        codes_to_fetch: List[str] = []

        with self._cache_lock:
            for code in stock_codes:
                if code in self._cache and not self._cache[code].is_stale:
                    results[code] = self._cache[code]
                    with self._stats_lock:
                        self._stats['cache_hits'] += 1
                else:
                    codes_to_fetch.append(code)

        # 캐시에 없는 종목들 배치 조회
        if codes_to_fetch:
            fetched = self._batch_fetch(codes_to_fetch)
            results.update(fetched)

        return results

    def get_price(self, stock_code: str) -> Optional[PriceData]:
        """단일 종목 가격 조회"""
        result = self.get_prices([stock_code])
        return result.get(stock_code)

    def _batch_fetch(self, stock_codes: List[str]) -> Dict[str, PriceData]:
        """ThreadPoolExecutor로 병렬 조회"""
        if not self.market_api:
            logger.warning("Market API가 설정되지 않음")
            return {}

        start_time = time.time()
        results: Dict[str, PriceData] = {}

        with self._stats_lock:
            self._stats['batch_fetches'] += 1

        # 병렬 조회
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(stock_codes))) as executor:
            future_to_code = {
                executor.submit(self._fetch_single, code): code
                for code in stock_codes
            }

            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    price_data = future.result()
                    if price_data:
                        results[code] = price_data
                        # 캐시 업데이트
                        with self._cache_lock:
                            self._cache[code] = price_data
                except Exception as e:
                    logger.warning(f"가격 조회 실패 ({code}): {e}")
                    with self._stats_lock:
                        self._stats['errors'] += 1

        # 성능 통계 업데이트
        elapsed_ms = (time.time() - start_time) * 1000
        with self._stats_lock:
            prev_avg = self._stats['avg_batch_time_ms']
            batch_count = self._stats['batch_fetches']
            self._stats['avg_batch_time_ms'] = ((prev_avg * (batch_count - 1)) + elapsed_ms) / batch_count

        if len(stock_codes) > 5:
            logger.debug(f"배치 조회 완료: {len(stock_codes)}개 종목, {elapsed_ms:.1f}ms")

        return results

    def _fetch_single(self, stock_code: str) -> Optional[PriceData]:
        """단일 종목 API 조회"""
        try:
            with self._stats_lock:
                self._stats['single_fetches'] += 1

            price_info = self.market_api.get_stock_price(stock_code)

            if price_info:
                return PriceData(
                    stock_code=stock_code,
                    current_price=price_info.get('current_price', 0),
                    change_rate=price_info.get('change_rate', 0),
                    volume=price_info.get('volume', 0),
                    high_price=price_info.get('high_price', 0),
                    low_price=price_info.get('low_price', 0),
                    open_price=price_info.get('open_price', 0)
                )
        except Exception as e:
            logger.warning(f"API 조회 실패 ({stock_code}): {e}")

        return None

    def invalidate(self, stock_code: str = None):
        """캐시 무효화

        Args:
            stock_code: 특정 종목만 무효화 (None이면 전체)
        """
        with self._cache_lock:
            if stock_code:
                self._cache.pop(stock_code, None)
            else:
                self._cache.clear()

    def get_stats(self) -> Dict:
        """성능 통계 반환"""
        with self._stats_lock:
            stats = self._stats.copy()

        with self._cache_lock:
            stats['cache_size'] = len(self._cache)

        # 캐시 히트율 계산
        total = stats['total_requests']
        if total > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / total * 100
        else:
            stats['cache_hit_rate'] = 0

        return stats

    def cleanup_stale_cache(self):
        """만료된 캐시 정리"""
        with self._cache_lock:
            stale_codes = [
                code for code, data in self._cache.items()
                if data.is_stale
            ]
            for code in stale_codes:
                del self._cache[code]

            if stale_codes:
                logger.debug(f"만료된 캐시 정리: {len(stale_codes)}개")


# 싱글톤 인스턴스
_batch_price_fetcher: Optional[BatchPriceFetcher] = None
_instance_lock = threading.Lock()


def get_batch_price_fetcher(market_api=None) -> BatchPriceFetcher:
    """BatchPriceFetcher 싱글톤 인스턴스 반환"""
    global _batch_price_fetcher

    with _instance_lock:
        if _batch_price_fetcher is None:
            _batch_price_fetcher = BatchPriceFetcher(market_api=market_api)
        elif market_api and _batch_price_fetcher.market_api is None:
            _batch_price_fetcher.set_market_api(market_api)

    return _batch_price_fetcher
