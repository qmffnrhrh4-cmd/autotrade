"""
Redis Cache Manager v6.0
Redis 기반 고성능 캐싱
"""

import json
import pickle
from typing import Any, Optional, Callable
from datetime import timedelta
from functools import wraps
import hashlib
import logging

logger = logging.getLogger(__name__)

# Import config constants
try:
    from config.constants import REDIS_HOST, PORTS
    _REDIS_HOST = REDIS_HOST
    _REDIS_PORT = PORTS['redis']
except ImportError:
    # Fallback to hardcoded values if config not available
    _REDIS_HOST = 'localhost'
    _REDIS_PORT = 6379

# Redis 사용 가능 여부 확인
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed - caching disabled")


class RedisCacheManager:
    """
    Redis 캐시 관리자

    Features:
    - TTL 기반 자동 만료
    - JSON/Pickle 직렬화
    - 데코레이터 기반 캐싱
    - 캐시 통계
    - Fallback (Redis 없으면 메모리 캐시)
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = 0,
        password: Optional[str] = None,
        use_fallback: bool = True
    ):
        """
        초기화

        Args:
            host: Redis 호스트 (default: from config.constants.REDIS_HOST)
            port: Redis 포트 (default: from config.constants.PORTS['redis'])
            db: Redis 데이터베이스 번호
            password: Redis 비밀번호
            use_fallback: Redis 없을 때 메모리 캐시 사용
        """
        # Use config defaults if not specified
        if host is None:
            host = _REDIS_HOST
        if port is None:
            port = _REDIS_PORT

        self.redis_client = None
        self.fallback_cache = {} if use_fallback else None
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }

        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=False,  # Pickle을 위해 False
                    socket_connect_timeout=5,
                    socket_timeout=5
                )

                # 연결 테스트
                self.redis_client.ping()
                logger.info(f"✓ Redis 연결 성공: {host}:{port}")

            except Exception as e:
                logger.warning(f"Redis 연결 실패: {e}")
                self.redis_client = None

                if use_fallback:
                    logger.info("→ 메모리 캐시로 폴백")

    def get(self, key: str, default: Any = None) -> Any:
        """
        캐시에서 값 조회

        Args:
            key: 캐시 키
            default: 기본값

        Returns:
            캐시된 값 또는 기본값
        """

        try:
            if self.redis_client:
                # Redis 조회
                value = self.redis_client.get(key)

                if value:
                    self.stats['hits'] += 1
                    return pickle.loads(value)
                else:
                    self.stats['misses'] += 1
                    return default

            elif self.fallback_cache is not None:
                # 메모리 캐시 조회
                if key in self.fallback_cache:
                    data, expiry = self.fallback_cache[key]

                    # 만료 확인
                    if expiry is None or expiry > self._current_timestamp():
                        self.stats['hits'] += 1
                        return data
                    else:
                        # 만료됨 - 삭제
                        del self.fallback_cache[key]

                self.stats['misses'] += 1
                return default

            else:
                return default

        except Exception as e:
            logger.error(f"캐시 조회 오류: {e}")
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초 단위)

        Returns:
            성공 여부
        """

        try:
            if self.redis_client:
                # Redis 저장
                serialized = pickle.dumps(value)

                if ttl:
                    self.redis_client.setex(key, ttl, serialized)
                else:
                    self.redis_client.set(key, serialized)

                self.stats['sets'] += 1
                return True

            elif self.fallback_cache is not None:
                # 메모리 캐시 저장
                expiry = None
                if ttl:
                    expiry = self._current_timestamp() + ttl

                self.fallback_cache[key] = (value, expiry)
                self.stats['sets'] += 1
                return True

            return False

        except Exception as e:
            logger.error(f"캐시 저장 오류: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        캐시 삭제

        Args:
            key: 캐시 키

        Returns:
            성공 여부
        """

        try:
            if self.redis_client:
                result = self.redis_client.delete(key)
                self.stats['deletes'] += 1
                return result > 0

            elif self.fallback_cache is not None:
                if key in self.fallback_cache:
                    del self.fallback_cache[key]
                    self.stats['deletes'] += 1
                    return True

            return False

        except Exception as e:
            logger.error(f"캐시 삭제 오류: {e}")
            return False

    def clear(self, pattern: Optional[str] = None) -> int:
        """
        캐시 일괄 삭제

        Args:
            pattern: 패턴 (예: "stock:*")

        Returns:
            삭제된 키 개수
        """

        try:
            if self.redis_client:
                if pattern:
                    # 패턴 매칭
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        return self.redis_client.delete(*keys)
                    return 0
                else:
                    # 전체 삭제
                    self.redis_client.flushdb()
                    return -1  # 알 수 없음

            elif self.fallback_cache is not None:
                if pattern:
                    # 패턴 매칭 (간단한 구현)
                    pattern_prefix = pattern.replace('*', '')
                    keys_to_delete = [
                        k for k in self.fallback_cache.keys()
                        if k.startswith(pattern_prefix)
                    ]
                    for key in keys_to_delete:
                        del self.fallback_cache[key]
                    return len(keys_to_delete)
                else:
                    count = len(self.fallback_cache)
                    self.fallback_cache.clear()
                    return count

            return 0

        except Exception as e:
            logger.error(f"캐시 일괄 삭제 오류: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """캐시 키 존재 여부"""

        try:
            if self.redis_client:
                return self.redis_client.exists(key) > 0

            elif self.fallback_cache is not None:
                if key in self.fallback_cache:
                    _, expiry = self.fallback_cache[key]
                    if expiry is None or expiry > self._current_timestamp():
                        return True
                    else:
                        del self.fallback_cache[key]

            return False

        except Exception as e:
            logger.error(f"캐시 존재 확인 오류: {e}")
            return False

    def get_stats(self) -> dict:
        """캐시 통계"""

        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'hit_rate': f"{hit_rate:.1f}%",
            'backend': 'redis' if self.redis_client else 'memory'
        }

    def _current_timestamp(self) -> int:
        """현재 타임스탬프 (초)"""
        import time
        return int(time.time())

    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """캐시 키 생성"""

        # 함수명 + 인자로 키 생성
        key_parts = [func_name]

        for arg in args:
            key_parts.append(str(arg))

        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")

        key_string = ":".join(key_parts)

        # MD5 해시
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        return f"cache:{func_name}:{key_hash}"


def cache_with_ttl(ttl: int = 300, key_prefix: str = ""):
    """
    캐싱 데코레이터

    Args:
        ttl: TTL (초)
        key_prefix: 키 접두사

    Usage:
        @cache_with_ttl(300)
        def get_stock_price(stock_code):
            return api.get_price(stock_code)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()

            # 캐시 키 생성
            func_name = f"{key_prefix}{func.__name__}" if key_prefix else func.__name__
            cache_key = cache_manager._generate_cache_key(func_name, args, kwargs)

            # 캐시 조회
            cached_value = cache_manager.get(cache_key)

            if cached_value is not None:
                logger.debug(f"캐시 히트: {func_name}")
                return cached_value

            # 캐시 미스 - 함수 실행
            logger.debug(f"캐시 미스: {func_name}")
            result = func(*args, **kwargs)

            # 캐시 저장
            if result is not None:
                cache_manager.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


# 싱글톤 인스턴스
_cache_manager_instance = None


def get_cache_manager() -> RedisCacheManager:
    """RedisCacheManager 싱글톤 인스턴스 반환"""
    global _cache_manager_instance

    if _cache_manager_instance is None:
        _cache_manager_instance = RedisCacheManager()

    return _cache_manager_instance
