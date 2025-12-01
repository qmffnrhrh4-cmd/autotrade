"""
Data Cache - 호환성 레이어
기존 코드와의 호환성을 위해 unified_cache로 리다이렉트

실제 구현: utils/unified_cache.py
"""

from utils.unified_cache import (
    CacheTTL,
    CacheEntry,
    CacheStats,
    UnifiedCache as LRUCache,
    MultiLevelCache,
    cached,
    get_cache,
    get_price_cache,
    get_market_cache,
    get_api_cache,
)

__all__ = [
    'CacheTTL',
    'CacheEntry',
    'CacheStats',
    'LRUCache',
    'MultiLevelCache',
    'cached',
    'get_cache',
    'get_price_cache',
    'get_market_cache',
    'get_api_cache',
]
