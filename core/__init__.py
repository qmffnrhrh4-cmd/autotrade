"""
core 패키지
핵심 API 클라이언트 + 표준 타입 시스템

v4.2 CRITICAL #2: 표준 타입 시스템 추가
- Position 클래스 통합 (4 → 1)
- Trade, MarketSnapshot 표준화

v6.0: OpenAPI 클라이언트 추가
- KiwoomOpenAPIClient (koapy 기반 자동매매)
"""
from .rest_client import KiwoomRESTClient
from .openapi_client import KiwoomOpenAPIClient, get_openapi_client
from .exceptions import (
    KiwoomAPIError,
    AuthenticationError,
    TokenExpiredError,
    RateLimitError,
    NetworkError,
    InvalidResponseError,
    WebSocketError,
    WebSocketConnectionError,
    WebSocketMessageError,
    ConfigurationError,
    ValidationError,
    StrategyError,
    OrderError,
)

# v4.2 Standard Types (CRITICAL #2)
from .trading_types import (
    OrderAction,
    OrderType,
    PositionStatus,
    Position,
    Trade,
    MarketSnapshot,
)

__all__ = [
    # REST Client
    'KiwoomRESTClient',

    # OpenAPI Client (v6.0)
    'KiwoomOpenAPIClient',
    'get_openapi_client',

    # Exceptions
    'KiwoomAPIError',
    'AuthenticationError',
    'TokenExpiredError',
    'RateLimitError',
    'NetworkError',
    'InvalidResponseError',
    'WebSocketError',
    'WebSocketConnectionError',
    'WebSocketMessageError',
    'ConfigurationError',
    'ValidationError',
    'StrategyError',
    'OrderError',

    # v4.2 Standard Types
    'OrderAction',
    'OrderType',
    'PositionStatus',
    'Position',
    'Trade',
    'MarketSnapshot',
]