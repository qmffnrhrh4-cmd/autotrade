"""
Intelligent Cache Manager
지능형 캐싱 시스템

데이터베이스, API 호출 결과를 캐싱하여 성능 향상

기능:
- TTL 기반 캐시 만료 (기본: 60초)
- LRU (Least Recently Used) 제거
- 캐시 크기 제한 (최대 1000개)
- 캐시 히트율 모니터링
- 데이터 타입별 최적화된 TTL 설정
"""
import logging
from typing import Any, Optional, Callable, Dict
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json
import threading

from utils.base_manager import BaseManager

logger = logging.getLogger(__name__)


# 데이터 타입별 권장 TTL (초)
class CacheTTL:
    """캐시 TTL 상수"""
    STOCK_PRICE = 5          # 종목 현재가 - 5초 (실시간성 중요)
    PORTFOLIO = 10           # 포트폴리오 정보 - 10초
    ACCOUNT_INFO = 30        # 계좌 정보 - 30초
    STRATEGY_LIST = 60       # 전략 목록 - 60초 (기본값)
    MARKET_DATA = 60         # 시장 데이터 - 60초
    STOCK_INFO = 300         # 종목 기본 정보 - 5분
    HISTORICAL_DATA = 600    # 과거 데이터 - 10분
    NEVER_EXPIRE = 0         # 만료 없음


class CacheEntry:
    """캐시 엔트리"""

    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.created_at = datetime.now()
        self.ttl_seconds = ttl_seconds
        self.hit_count = 0
        self.last_access = datetime.now()

    def is_expired(self) -> bool:
        """만료 여부"""
        if self.ttl_seconds <= 0:
            return False  # 무제한
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)

    def access(self) -> Any:
        """값 접근"""
        self.hit_count += 1
        self.last_access = datetime.now()
        return self.value


class CacheManager(BaseManager):
    """
    지능형 캐시 관리자

    기능:
    - TTL 기반 캐싱
    - LRU (Least Recently Used) 제거
    - 히트율 모니터링
    - 자동 정리
    - 데이터 타입별 최적화된 TTL
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        """
        Args:
            max_size: 최대 캐시 크기 (기본: 1000)
            default_ttl: 기본 TTL 초 (기본: 60초)
        """
        super().__init__(name="CacheManager")
        self.max_size = max_size
        self.default_ttl = default_ttl

        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

        # 통계
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expirations = 0

        self.initialized = True
        self.logger.info(f"🚀 CacheManager 초기화 완료 - Max Size: {max_size}, Default TTL: {default_ttl}s")

        # 자동 정리 스레드 시작
        self._start_cleanup_thread()

    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회

        Args:
            key: 키

        Returns:
            값 (없으면 None)
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self.misses += 1
                logger.debug(f"❌ Cache miss: {key}")
                return None

            # 만료 체크
            if entry.is_expired():
                del self._cache[key]
                self.misses += 1
                self.expirations += 1
                logger.debug(f"⏰ Cache expired: {key}")
                return None

            # 히트
            self.hits += 1
            logger.debug(f"✅ Cache hit: {key} (hits: {entry.hit_count + 1})")
            return entry.access()

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        캐시에 값 저장

        Args:
            key: 키
            value: 값
            ttl: TTL (초), None이면 기본값 사용
        """
        with self._lock:
            # 크기 체크
            if len(self._cache) >= self.max_size:
                self._evict_lru()

            ttl = ttl if ttl is not None else self.default_ttl
            self._cache[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> bool:
        """
        캐시에서 삭제

        Args:
            key: 키

        Returns:
            삭제 성공 여부
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """전체 캐시 삭제"""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def get_or_set(self, key: str, factory: Callable, ttl: Optional[int] = None) -> Any:
        """
        캐시에서 값을 가져오거나, 없으면 factory로 생성하여 저장

        Args:
            key: 키
            factory: 값 생성 함수
            ttl: TTL (초)

        Returns:
            값
        """
        value = self.get(key)

        if value is not None:
            return value

        # 캐시 미스 - 새로 생성
        value = factory()
        self.set(key, value, ttl)
        return value

    def get_stats(self) -> dict:
        """
        캐시 통계 조회

        Returns:
            dict: 캐시 통계 정보
                - size: 현재 캐시 항목 수
                - max_size: 최대 캐시 크기
                - usage_percent: 사용률 (%)
                - hits: 캐시 히트 횟수
                - misses: 캐시 미스 횟수
                - hit_rate: 캐시 히트율 (%)
                - total_requests: 총 요청 수
                - evictions: LRU 제거 횟수
                - expirations: 만료 삭제 횟수
        """
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            usage_percent = (len(self._cache) / self.max_size * 100) if self.max_size > 0 else 0

            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'usage_percent': round(usage_percent, 2),
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': round(hit_rate, 2),
                'total_requests': total_requests,
                'evictions': self.evictions,
                'expirations': self.expirations
            }

    def _evict_lru(self):
        """LRU 제거 (가장 오래 사용 안 된 항목)"""
        if not self._cache:
            return

        # 가장 오래 사용 안 된 항목 찾기
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_access
        )

        del self._cache[lru_key]
        self.evictions += 1
        logger.debug(f"🗑️  LRU evicted: {lru_key} (total evictions: {self.evictions})")

    def _cleanup_expired(self):
        """만료된 항목 정리"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]
                self.expirations += 1

            if expired_keys:
                logger.debug(f"🧹 Cleaned up {len(expired_keys)} expired entries (total expirations: {self.expirations})")

    def _start_cleanup_thread(self):
        """정리 스레드 시작"""
        def cleanup_loop():
            while True:
                try:
                    self._cleanup_expired()
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")

                # 60초마다 정리
                threading.Event().wait(60)

        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()

    def initialize(self) -> bool:
        """초기화"""
        self.initialized = True
        self.logger.info("캐시 관리자 초기화 완료")
        return True

    def get_status(self) -> Dict[str, Any]:
        """상태 정보"""
        stats = self.get_stats()
        return {
            **super().get_stats(),
            'cache_stats': stats
        }


# 데코레이터: 함수 결과 캐싱
def cached(ttl: int = 300, key_prefix: str = ""):
    """
    함수 결과를 캐싱하는 데코레이터

    Args:
        ttl: TTL (초)
        key_prefix: 키 프리픽스

    Example:
        @cached(ttl=60, key_prefix="price")
        def get_price(stock_code):
            return fetch_price_from_api(stock_code)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix)

            # 캐시에서 조회
            cache_mgr = get_cache_manager()
            cached_value = cache_mgr.get(cache_key)

            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # 캐시 미스 - 실제 함수 실행
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)

            # 결과 캐싱
            cache_mgr.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


def _generate_cache_key(func: Callable, args: tuple, kwargs: dict, prefix: str) -> str:
    """캐시 키 생성"""
    # 함수명 + 인자들을 조합하여 해시
    func_name = f"{func.__module__}.{func.__name__}"

    # 인자들을 JSON으로 직렬화
    try:
        args_str = json.dumps([args, kwargs], sort_keys=True, default=str)
    except:
        # 직렬화 실패 시 str() 사용
        args_str = str([args, kwargs])

    # 해시 생성
    hash_obj = hashlib.md5(args_str.encode())
    hash_str = hash_obj.hexdigest()[:16]

    # 키 생성
    if prefix:
        return f"{prefix}:{func_name}:{hash_str}"
    else:
        return f"{func_name}:{hash_str}"


# Singleton instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """
    Get cache manager singleton

    Returns:
        CacheManager: 싱글톤 캐시 관리자 인스턴스
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(
            max_size=1000,
            default_ttl=60  # 기본 60초 (CacheTTL.STRATEGY_LIST)
        )
    return _cache_manager


def print_cache_stats():
    """
    캐시 통계 출력 (디버깅/모니터링용)

    Example:
        >>> from utils.cache_manager import print_cache_stats
        >>> print_cache_stats()
        📊 Cache Statistics:
           Size: 125/1000 (12.5%)
           Hits: 1,245 | Misses: 156
           Hit Rate: 88.87%
           Evictions: 3 | Expirations: 42
    """
    cache_mgr = get_cache_manager()
    stats = cache_mgr.get_stats()

    logger.info("📊 Cache Statistics:")
    logger.info(f"   Size: {stats['size']}/{stats['max_size']} ({stats['usage_percent']}%)")
    logger.info(f"   Hits: {stats['hits']:,} | Misses: {stats['misses']:,}")
    logger.info(f"   Hit Rate: {stats['hit_rate']}%")
    logger.info(f"   Evictions: {stats['evictions']} | Expirations: {stats['expirations']}")


__all__ = [
    'CacheTTL',
    'CacheManager',
    'get_cache_manager',
    'cached',
    'print_cache_stats'
]
