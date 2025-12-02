"""
utils/unified_cache.py
통합 캐싱 시스템

기존 파일 통합:
- cache_manager.py (TTL 기반 캐시)
- data_cache.py (LRU 기반 캐시)

Features:
- TTL 기반 캐시 만료
- LRU (Least Recently Used) 제거
- 메모리 사용량 제한
- 캐시 히트율 모니터링
- 태그 기반 무효화
- 멀티레벨 캐시 (메모리 + 디스크)
- 데이터 타입별 최적화된 TTL
- 스레드 안전
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timedelta
from collections import OrderedDict
from threading import RLock
from functools import wraps
from pathlib import Path
import hashlib
import pickle
import json
import logging

logger = logging.getLogger(__name__)


class CacheTTL:
    """
    캐시 TTL 상수 (초)

    실시간 자동매매 시스템용으로 최적화:
    - 주문 결정에 사용되는 데이터: 2-5초 (호가, 현재가)
    - 분석용 데이터: 10-30초
    - 참조 데이터: 60초 이상
    """
    # 실시간 트레이딩 데이터 (주문 결정용)
    REALTIME = 2         # 호가창, 체결정보 - 2초 (기존 3초)
    STOCK_PRICE = 3      # 현재가 - 3초 (기존 5초)
    ORDERBOOK = 2        # 호가 깊이 - 2초 (신규)

    # 계좌/포트폴리오 데이터
    PORTFOLIO = 5        # 보유 종목 - 5초 (기존 10초)
    ACCOUNT_INFO = 15    # 계좌 정보 - 15초 (기존 30초)

    # 분석용 데이터
    MARKET_DATA = 10     # 시장 데이터 - 10초 (기존 60초)
    STRATEGY_LIST = 30   # 전략 목록 - 30초 (기존 60초)

    # 참조 데이터 (변경 빈도 낮음)
    STOCK_INFO = 300     # 종목 기본정보 - 5분
    HISTORICAL_DATA = 600  # 과거 데이터 - 10분
    STATIC_DATA = 3600   # 정적 데이터 - 1시간
    NEVER_EXPIRE = 0     # 만료 없음


@dataclass
class CacheEntry:
    """캐시 엔트리"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    hit_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """만료 여부 확인"""
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at

    def access(self) -> Any:
        """값 접근 (히트 카운트 증가)"""
        self.hit_count += 1
        self.last_accessed = datetime.now()
        return self.value


@dataclass
class CacheStats:
    """캐시 통계"""
    entries: int = 0
    max_size: int = 0
    memory_bytes: int = 0
    max_memory_bytes: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    uptime_seconds: float = 0

    @property
    def hit_rate(self) -> float:
        """히트율 계산"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0

    @property
    def usage_percent(self) -> float:
        """사용률 계산"""
        return (self.entries / self.max_size * 100) if self.max_size > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            'entries': self.entries,
            'max_size': self.max_size,
            'memory_mb': self.memory_bytes / 1024 / 1024,
            'max_memory_mb': self.max_memory_bytes / 1024 / 1024,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(self.hit_rate, 2),
            'usage_percent': round(self.usage_percent, 2),
            'evictions': self.evictions,
            'expirations': self.expirations,
            'uptime_seconds': round(self.uptime_seconds, 1)
        }


class UnifiedCache:
    """
    통합 캐시

    Features:
    - LRU 정책
    - TTL 기반 만료
    - 메모리 제한
    - 태그 기반 무효화
    - 스레드 안전
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl: int = 60,
        name: str = "UnifiedCache"
    ):
        """
        초기화

        Args:
            max_size: 최대 엔트리 수
            max_memory_mb: 최대 메모리 (MB)
            default_ttl: 기본 TTL (초)
            name: 캐시 이름
        """
        self.name = name
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()
        self._start_time = datetime.now()

        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0
        self._memory_bytes = 0

        logger.debug(f"{name} 초기화: max_size={max_size}, max_memory={max_memory_mb}MB, ttl={default_ttl}s")

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        캐시에서 값 조회

        Args:
            key: 캐시 키
            default: 기본값 (없을 때 반환)

        Returns:
            캐시된 값 또는 default
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default

            entry = self._cache[key]

            if entry.is_expired():
                self._delete_entry(key)
                self._expirations += 1
                self._misses += 1
                return default

            self._cache.move_to_end(key)

            self._hits += 1
            return entry.access()

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초), None이면 default TTL
            tags: 태그 목록

        Returns:
            저장 성공 여부
        """
        with self._lock:
            try:
                size_bytes = len(pickle.dumps(value))
            except Exception:
                size_bytes = 1024

            if size_bytes > self.max_memory_bytes:
                logger.warning(f"캐시 크기 초과: {key} ({size_bytes} bytes)")
                return False

            if key in self._cache:
                self._delete_entry(key)

            self._evict_if_needed(size_bytes)

            ttl_value = ttl if ttl is not None else self.default_ttl
            expires_at = None
            if ttl_value > 0:
                expires_at = datetime.now() + timedelta(seconds=ttl_value)

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at,
                size_bytes=size_bytes,
                tags=tags or []
            )

            self._cache[key] = entry
            self._memory_bytes += size_bytes

            return True

    def delete(self, key: str) -> bool:
        """
        캐시에서 삭제

        Args:
            key: 캐시 키

        Returns:
            삭제 성공 여부
        """
        with self._lock:
            if key in self._cache:
                self._delete_entry(key)
                return True
            return False

    def get_or_set(
        self,
        key: str,
        factory: Callable,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Any:
        """
        캐시에서 가져오거나 없으면 생성하여 저장

        Args:
            key: 캐시 키
            factory: 값 생성 함수
            ttl: TTL (초)
            tags: 태그 목록

        Returns:
            캐시된 값 또는 새로 생성된 값
        """
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        self.set(key, value, ttl, tags)
        return value

    def invalidate_by_tag(self, tag: str) -> int:
        """
        태그로 캐시 무효화

        Args:
            tag: 태그

        Returns:
            삭제된 엔트리 수
        """
        with self._lock:
            keys_to_delete = [
                key for key, entry in self._cache.items()
                if tag in entry.tags
            ]

            for key in keys_to_delete:
                self._delete_entry(key)

            if keys_to_delete:
                logger.debug(f"태그 '{tag}'로 {len(keys_to_delete)}개 엔트리 무효화")

            return len(keys_to_delete)

    def invalidate_by_prefix(self, prefix: str) -> int:
        """
        키 프리픽스로 캐시 무효화

        Args:
            prefix: 키 프리픽스

        Returns:
            삭제된 엔트리 수
        """
        with self._lock:
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(prefix)
            ]

            for key in keys_to_delete:
                self._delete_entry(key)

            return len(keys_to_delete)

    def clear(self):
        """전체 캐시 삭제"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._memory_bytes = 0
            logger.info(f"{self.name}: {count}개 엔트리 삭제")

    def cleanup_expired(self) -> int:
        """만료된 엔트리 정리"""
        with self._lock:
            keys_to_delete = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in keys_to_delete:
                self._delete_entry(key)
                self._expirations += 1

            return len(keys_to_delete)

    def get_stats(self) -> CacheStats:
        """캐시 통계 조회"""
        with self._lock:
            uptime = (datetime.now() - self._start_time).total_seconds()

            return CacheStats(
                entries=len(self._cache),
                max_size=self.max_size,
                memory_bytes=self._memory_bytes,
                max_memory_bytes=self.max_memory_bytes,
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
                expirations=self._expirations,
                uptime_seconds=uptime
            )

    def _delete_entry(self, key: str):
        """엔트리 삭제 (내부)"""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._memory_bytes = max(0, self._memory_bytes - entry.size_bytes)

    def _evict_if_needed(self, incoming_size: int):
        """필요시 LRU 제거"""
        while (self._memory_bytes + incoming_size > self.max_memory_bytes and
               len(self._cache) > 0):
            oldest_key = next(iter(self._cache))
            self._delete_entry(oldest_key)
            self._evictions += 1

        while len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            self._delete_entry(oldest_key)
            self._evictions += 1


class MultiLevelCache:
    """
    멀티레벨 캐시 (L1: 메모리, L2: 디스크)
    """

    def __init__(
        self,
        l1_max_size: int = 500,
        l1_max_memory_mb: int = 50,
        l2_enabled: bool = True,
        l2_cache_dir: str = "data/cache",
        default_ttl: int = 300
    ):
        """
        초기화

        Args:
            l1_max_size: L1 캐시 최대 크기
            l1_max_memory_mb: L1 캐시 최대 메모리
            l2_enabled: L2 캐시 활성화
            l2_cache_dir: L2 캐시 디렉토리
            default_ttl: 기본 TTL
        """
        self.l1_cache = UnifiedCache(
            max_size=l1_max_size,
            max_memory_mb=l1_max_memory_mb,
            default_ttl=default_ttl,
            name="L1Cache"
        )

        self.l2_enabled = l2_enabled
        self.l2_cache_dir = Path(l2_cache_dir)

        if self.l2_enabled:
            self.l2_cache_dir.mkdir(parents=True, exist_ok=True)

        self._lock = RLock()

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """L1 -> L2 순서로 조회"""
        value = self.l1_cache.get(key)
        if value is not None:
            return value

        if self.l2_enabled:
            value = self._get_from_l2(key)
            if value is not None:
                self.l1_cache.set(key, value)
                return value

        return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
        persist_l2: bool = True
    ) -> bool:
        """L1 + L2 저장"""
        success = self.l1_cache.set(key, value, ttl, tags)

        if self.l2_enabled and persist_l2:
            self._set_to_l2(key, value, ttl)

        return success

    def delete(self, key: str) -> bool:
        """L1 + L2 삭제"""
        l1_deleted = self.l1_cache.delete(key)

        if self.l2_enabled:
            l2_deleted = self._delete_from_l2(key)
            return l1_deleted or l2_deleted

        return l1_deleted

    def clear(self):
        """전체 삭제"""
        self.l1_cache.clear()

        if self.l2_enabled:
            for cache_file in self.l2_cache_dir.glob("*.cache"):
                try:
                    cache_file.unlink()
                except Exception:
                    pass

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        l1_stats = self.l1_cache.get_stats()

        stats = {
            'l1': l1_stats.to_dict()
        }

        if self.l2_enabled:
            l2_files = list(self.l2_cache_dir.glob("*.cache"))
            l2_size = sum(f.stat().st_size for f in l2_files if f.exists())
            stats['l2'] = {
                'entries': len(l2_files),
                'size_mb': round(l2_size / 1024 / 1024, 2)
            }

        return stats

    def _get_from_l2(self, key: str) -> Optional[Any]:
        """L2에서 조회"""
        cache_file = self._get_l2_path(key)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)

            if data.get('expires_at'):
                expires_at = datetime.fromisoformat(data['expires_at'])
                if datetime.now() >= expires_at:
                    cache_file.unlink()
                    return None

            return data.get('value')

        except Exception:
            return None

    def _set_to_l2(self, key: str, value: Any, ttl: Optional[int]) -> bool:
        """L2에 저장"""
        cache_file = self._get_l2_path(key)

        try:
            expires_at = None
            if ttl and ttl > 0:
                expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()

            data = {
                'value': value,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at
            }

            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)

            return True

        except Exception:
            return False

    def _delete_from_l2(self, key: str) -> bool:
        """L2에서 삭제"""
        cache_file = self._get_l2_path(key)

        if cache_file.exists():
            try:
                cache_file.unlink()
                return True
            except Exception:
                pass

        return False

    def _get_l2_path(self, key: str) -> Path:
        """L2 파일 경로"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.l2_cache_dir / f"{key_hash}.cache"


def cached(
    ttl: int = 300,
    key_prefix: str = "",
    cache_instance: Optional[UnifiedCache] = None
):
    """
    함수 결과 캐싱 데코레이터

    Args:
        ttl: TTL (초)
        key_prefix: 키 프리픽스
        cache_instance: 사용할 캐시 인스턴스

    Example:
        @cached(ttl=60, key_prefix="price")
        def get_stock_price(stock_code):
            return fetch_price_from_api(stock_code)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = cache_instance or get_cache()

            args_str = json.dumps([str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())], default=str)
            args_hash = hashlib.md5(args_str.encode()).hexdigest()[:12]

            if key_prefix:
                cache_key = f"{key_prefix}:{func.__name__}:{args_hash}"
            else:
                cache_key = f"{func.__module__}.{func.__name__}:{args_hash}"

            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


_global_cache: Optional[UnifiedCache] = None
_price_cache: Optional[MultiLevelCache] = None
_market_cache: Optional[MultiLevelCache] = None
_api_cache: Optional[UnifiedCache] = None


def get_cache() -> UnifiedCache:
    """전역 캐시 인스턴스"""
    global _global_cache
    if _global_cache is None:
        _global_cache = UnifiedCache(
            max_size=1000,
            max_memory_mb=100,
            default_ttl=CacheTTL.STRATEGY_LIST,
            name="GlobalCache"
        )
    return _global_cache


def get_price_cache() -> MultiLevelCache:
    """가격 데이터 캐시"""
    global _price_cache
    if _price_cache is None:
        _price_cache = MultiLevelCache(
            l1_max_size=500,
            l1_max_memory_mb=50,
            l2_enabled=True,
            l2_cache_dir="data/cache/prices",
            default_ttl=CacheTTL.STOCK_PRICE
        )
    return _price_cache


def get_market_cache() -> MultiLevelCache:
    """마켓 데이터 캐시"""
    global _market_cache
    if _market_cache is None:
        _market_cache = MultiLevelCache(
            l1_max_size=1000,
            l1_max_memory_mb=100,
            l2_enabled=True,
            l2_cache_dir="data/cache/market",
            default_ttl=CacheTTL.MARKET_DATA
        )
    return _market_cache


def get_api_cache() -> UnifiedCache:
    """API 응답 캐시"""
    global _api_cache
    if _api_cache is None:
        _api_cache = UnifiedCache(
            max_size=500,
            max_memory_mb=30,
            default_ttl=CacheTTL.MARKET_DATA,
            name="APICache"
        )
    return _api_cache


def get_cache_manager() -> UnifiedCache:
    """기존 API 호환: CacheManager 대신 UnifiedCache 반환"""
    return get_cache()


def print_cache_stats():
    """캐시 통계 출력"""
    cache = get_cache()
    stats = cache.get_stats()

    logger.info("📊 Cache Statistics:")
    logger.info(f"   Size: {stats.entries}/{stats.max_size} ({stats.usage_percent:.1f}%)")
    logger.info(f"   Hits: {stats.hits:,} | Misses: {stats.misses:,}")
    logger.info(f"   Hit Rate: {stats.hit_rate:.1f}%")
    logger.info(f"   Evictions: {stats.evictions} | Expirations: {stats.expirations}")


__all__ = [
    'CacheTTL',
    'CacheEntry',
    'CacheStats',
    'UnifiedCache',
    'MultiLevelCache',
    'cached',
    'get_cache',
    'get_price_cache',
    'get_market_cache',
    'get_api_cache',
    'get_cache_manager',
    'print_cache_stats',
]
