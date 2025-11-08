"""
AutoTrade Pro - 공통 상수 정의
모든 하드코딩된 값들을 중앙에서 관리
"""

RISK_FREE_RATE = 0.03
TRADING_DAYS_PER_YEAR = 252
DEFAULT_CACHE_TTL = 300

AI_MODELS = {
    'primary': 'gemini-2.5-flash',
    'secondary': 'gemini-2.0-flash-exp',
    'fallback': 'gemini-pro'
}

RISK_MODES = {
    'very_conservative': {
        'max_open_positions': 3,
        'risk_per_trade_ratio': 0.05,
        'take_profit_ratio': 0.08,
        'stop_loss_ratio': -0.03,
        'ai_min_score': 8.0
    },
    'conservative': {
        'max_open_positions': 5,
        'risk_per_trade_ratio': 0.10,
        'take_profit_ratio': 0.10,
        'stop_loss_ratio': -0.05,
        'ai_min_score': 7.5
    },
    'normal': {
        'max_open_positions': 8,
        'risk_per_trade_ratio': 0.15,
        'take_profit_ratio': 0.12,
        'stop_loss_ratio': -0.06,
        'ai_min_score': 7.0
    },
    'aggressive': {
        'max_open_positions': 12,
        'risk_per_trade_ratio': 0.25,
        'take_profit_ratio': 0.15,
        'stop_loss_ratio': -0.07,
        'ai_min_score': 6.5
    }
}

PORTFOLIO_OPTIMIZATION = {
    'learning_rate': 0.01,
    'num_iterations': 1000,
    'efficient_frontier_points': 100,
    'rebalance_threshold_pct': 0.05,
    'min_trade_amount': 100000
}

API_TIMEOUTS = {
    'default': 10,
    'long': 30,
    'short': 5
}

MARKET_HOURS = {
    'regular': {'start': '09:00', 'end': '15:30'},
    'nxt_premarket': {'start': '08:00', 'end': '09:00'},
    'nxt_aftermarket': {'start': '15:40', 'end': '20:00'}
}

DEFAULT_INITIAL_CAPITAL = 10_000_000
DEFAULT_VIRTUAL_CAPITAL = 10_000_000

DELAYS = {
    'api_retry': 1.0,
    'api_retry_error': 2.0,
    'paper_trading_check': 30.0,
    'paper_trading_error': 60.0,
    'order_check': 30.0,
    'websocket_reconnect': 5.0,
    'rate_limit': 0.2,
    'server_init': 1.0,
    'batch_delay': 0.1
}

URLS = {
    'openapi_server': 'http://127.0.0.1:5001',
    'kiwoom_api_base': 'https://api.kiwoom.com',
    'openapi_health': 'http://127.0.0.1:5001/health'
}

PROFIT_LOSS_RATIOS = {
    'default': {
        'stop_loss': 0.05,
        'take_profit': 0.10
    },
    'aggressive': {
        'stop_loss': 0.07,
        'take_profit': 0.15
    },
    'conservative': {
        'stop_loss': 0.03,
        'take_profit': 0.08
    },
    'moderate': {
        'stop_loss': 0.05,
        'take_profit': 0.12
    },
    'day_trading': {
        'stop_loss': 0.02,
        'take_profit': 0.05
    }
}

RISK_LIMITS = {
    'max_position_size': 0.30,
    'max_daily_loss': 0.03,
    'max_total_loss': 0.10,
    'max_consecutive_losses': 3,
    'position_limit': 5,
    'emergency_stop_loss': 0.15
}

THRESHOLDS = {
    'min_ai_score': 7.0,
    'min_trading_volume': 100000,
    'max_spread_pct': 0.02,
    'min_market_cap': 100_000_000_000
}

RETRY_CONFIG = {
    'max_retries': 3,
    'backoff_factor': 2.0,
    'max_backoff': 60.0
}
