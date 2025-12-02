"""
Rate-Limited Logger - 호환성 레이어
기존 코드와의 호환성을 위해 logger_new.py로 리다이렉트

실제 구현: utils/logger_new.py
"""

from utils.logger_new import (
    RateLimitedLogger,
    get_rate_limited_logger,
    get_logger,
    LoggerMixin,
)

__all__ = [
    'RateLimitedLogger',
    'get_rate_limited_logger',
    'get_logger',
    'LoggerMixin',
]


def rate_limit_log(rate_limit_seconds: float = 1.0):
    """함수 데코레이터: 함수 내부 로깅을 rate limit"""
    import time
    from functools import wraps

    def decorator(func):
        last_log = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            func_name = func.__name__

            if now - last_log.get(func_name, 0) >= rate_limit_seconds:
                last_log[func_name] = now
                return func(*args, **kwargs)

        return wrapper
    return decorator
