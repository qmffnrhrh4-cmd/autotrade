"""
Smart Cache System - 스마트 캐시 시스템
거래 이벤트 기반 자동 무효화, 스레드 안전, TTL 관리
"""
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from utils.logger_new import get_logger

logger = get_logger()


class CacheType(Enum):
    """캐시 타입"""
    HOLDINGS = "holdings"       # 보유 종목
    DEPOSIT = "deposit"         # 예수금
    PRICES = "prices"           # 가격 데이터
    ORDERBOOK = "orderbook"     # 호가
    PENDING_ORDERS = "pending"  # 미체결 주문


@dataclass
class CacheEntry:
    """캐시 엔트리"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: float = 60.0
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

    @property
    def is_expired(self) -> bool:
        """만료 여부"""
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """캐시 경과 시간"""
        return (datetime.now() - self.created_at).total_seconds()


class SmartCache:
    """스마트 캐시

    특징:
    - 거래 이벤트 시 자동 무효화
    - 타입별 TTL 설정
    - 스레드 안전
    - LRU 스타일 정리
    """

    # 타입별 기본 TTL (초)
    DEFAULT_TTL = {
        CacheType.HOLDINGS: 30.0,      # 보유 종목: 30초
        CacheType.DEPOSIT: 30.0,       # 예수금: 30초
        CacheType.PRICES: 5.0,         # 가격: 5초 (빠른 갱신)
        CacheType.ORDERBOOK: 3.0,      # 호가: 3초
        CacheType.PENDING_ORDERS: 10.0 # 미체결: 10초
    }

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

        # 무효화 콜백
        self._invalidation_callbacks: List[Callable] = []

        # 통계
        self._stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'evictions': 0
        }

        logger.info(f"SmartCache 초기화 (max_size={max_size})")

    def _make_key(self, cache_type: CacheType, identifier: str = "") -> str:
        """캐시 키 생성"""
        return f"{cache_type.value}:{identifier}"

    def get(self, cache_type: CacheType, identifier: str = "") -> Optional[Any]:
        """캐시 조회

        Args:
            cache_type: 캐시 타입
            identifier: 식별자 (예: 종목코드)

        Returns:
            캐시된 값 또는 None
        """
        key = self._make_key(cache_type, identifier)

        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats['misses'] += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._stats['misses'] += 1
                return None

            # 접근 통계 업데이트
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self._stats['hits'] += 1

            return entry.value

    def set(self, cache_type: CacheType, value: Any, identifier: str = "",
            ttl: float = None) -> None:
        """캐시 저장

        Args:
            cache_type: 캐시 타입
            value: 저장할 값
            identifier: 식별자
            ttl: TTL (초), None이면 기본값 사용
        """
        key = self._make_key(cache_type, identifier)
        ttl = ttl or self.DEFAULT_TTL.get(cache_type, 60.0)

        with self._lock:
            # 용량 초과 시 LRU 정리
            if len(self._cache) >= self.max_size:
                self._evict_lru()

            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                ttl_seconds=ttl
            )

    def invalidate(self, cache_type: CacheType = None, identifier: str = None) -> int:
        """캐시 무효화

        Args:
            cache_type: 무효화할 타입 (None이면 전체)
            identifier: 무효화할 식별자 (None이면 해당 타입 전체)

        Returns:
            무효화된 엔트리 수
        """
        count = 0

        with self._lock:
            if cache_type is None:
                # 전체 무효화
                count = len(self._cache)
                self._cache.clear()
            elif identifier is None:
                # 타입 전체 무효화
                prefix = f"{cache_type.value}:"
                keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
                for key in keys_to_remove:
                    del self._cache[key]
                    count += 1
            else:
                # 특정 엔트리 무효화
                key = self._make_key(cache_type, identifier)
                if key in self._cache:
                    del self._cache[key]
                    count = 1

            self._stats['invalidations'] += count

        if count > 0:
            logger.debug(f"캐시 무효화: {count}개 (type={cache_type}, id={identifier})")

        return count

    def invalidate_on_trade(self, stock_code: str = None):
        """거래 발생 시 관련 캐시 무효화

        Args:
            stock_code: 거래 종목 코드
        """
        # 보유 종목과 예수금은 항상 무효화
        self.invalidate(CacheType.HOLDINGS)
        self.invalidate(CacheType.DEPOSIT)
        self.invalidate(CacheType.PENDING_ORDERS)

        # 특정 종목 가격 무효화
        if stock_code:
            self.invalidate(CacheType.PRICES, stock_code)
            self.invalidate(CacheType.ORDERBOOK, stock_code)

        # 콜백 호출
        for callback in self._invalidation_callbacks:
            try:
                callback(stock_code)
            except Exception as e:
                logger.warning(f"무효화 콜백 오류: {e}")

    def register_invalidation_callback(self, callback: Callable):
        """무효화 콜백 등록"""
        self._invalidation_callbacks.append(callback)

    def _evict_lru(self):
        """LRU 방식으로 캐시 정리 (가장 오래 접근하지 않은 항목 제거)"""
        if not self._cache:
            return

        # 마지막 접근 시간 기준 정렬
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )

        # 10% 제거
        remove_count = max(1, len(self._cache) // 10)
        for key, _ in sorted_entries[:remove_count]:
            del self._cache[key]
            self._stats['evictions'] += 1

        logger.debug(f"LRU 캐시 정리: {remove_count}개 제거")

    def cleanup_expired(self) -> int:
        """만료된 캐시 정리"""
        count = 0
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
                count += 1

        if count > 0:
            logger.debug(f"만료된 캐시 정리: {count}개")

        return count

    def get_stats(self) -> Dict:
        """캐시 통계 반환"""
        with self._lock:
            stats = self._stats.copy()
            stats['size'] = len(self._cache)
            stats['max_size'] = self.max_size

            # 히트율 계산
            total = stats['hits'] + stats['misses']
            stats['hit_rate'] = (stats['hits'] / total * 100) if total > 0 else 0

            # 타입별 통계
            type_counts = {}
            for cache_type in CacheType:
                prefix = f"{cache_type.value}:"
                type_counts[cache_type.value] = sum(
                    1 for k in self._cache.keys() if k.startswith(prefix)
                )
            stats['by_type'] = type_counts

        return stats

    def get_or_fetch(self, cache_type: CacheType, identifier: str,
                     fetch_func: Callable, ttl: float = None) -> Any:
        """캐시에서 가져오거나, 없으면 fetch_func로 조회 후 캐싱

        Args:
            cache_type: 캐시 타입
            identifier: 식별자
            fetch_func: 데이터 조회 함수
            ttl: TTL (초)

        Returns:
            캐시된 값 또는 새로 조회한 값
        """
        # 캐시 확인
        cached = self.get(cache_type, identifier)
        if cached is not None:
            return cached

        # 새로 조회
        try:
            value = fetch_func()
            if value is not None:
                self.set(cache_type, value, identifier, ttl)
            return value
        except Exception as e:
            logger.warning(f"fetch 실패 ({cache_type.value}:{identifier}): {e}")
            return None


# 싱글톤 인스턴스
_smart_cache: Optional[SmartCache] = None
_instance_lock = threading.Lock()


def get_smart_cache() -> SmartCache:
    """SmartCache 싱글톤 인스턴스 반환"""
    global _smart_cache

    with _instance_lock:
        if _smart_cache is None:
            _smart_cache = SmartCache()

    return _smart_cache
