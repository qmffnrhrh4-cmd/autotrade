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

# Q5. 다중 종목 동시 매매: 포지션 수 대폭 확대
# Q7. 위험 관리 자동화: 시장 상황에 따라 유기적 조절
RISK_MODES = {
    'very_conservative': {
        'max_open_positions': 10,      # 3 → 10
        'risk_per_trade_ratio': 0.03,  # 포지션당 3%
        'take_profit_ratio': 0.06,
        'stop_loss_ratio': -0.02,
        'ai_min_score': 6.0,           # 8.0 → 6.0 (더 많은 기회)
        'volatility_multiplier': 0.5   # Q4. 변동성 기반 조절
    },
    'conservative': {
        'max_open_positions': 20,      # 5 → 20
        'risk_per_trade_ratio': 0.05,
        'take_profit_ratio': 0.08,
        'stop_loss_ratio': -0.03,
        'ai_min_score': 5.5,
        'volatility_multiplier': 0.7
    },
    'normal': {
        'max_open_positions': 30,      # 8 → 30
        'risk_per_trade_ratio': 0.08,
        'take_profit_ratio': 0.10,
        'stop_loss_ratio': -0.05,
        'ai_min_score': 5.0,           # 7.0 → 5.0
        'volatility_multiplier': 1.0
    },
    'aggressive': {
        'max_open_positions': 50,      # 12 → 50
        'risk_per_trade_ratio': 0.10,
        'take_profit_ratio': 0.15,
        'stop_loss_ratio': -0.07,
        'ai_min_score': 4.0,           # 6.5 → 4.0
        'volatility_multiplier': 1.5
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

HOST = '0.0.0.0'
OPENAPI_HOST = '127.0.0.1'
REDIS_HOST = 'localhost'

PORTS = {
    'openapi': 5001,
    'dashboard': 5000,
    'redis': 6379
}

URLS = {
    'openapi_server': f'http://{OPENAPI_HOST}:{PORTS["openapi"]}',
    'kiwoom_api_base': 'https://api.kiwoom.com',
    'openapi_health': f'http://{OPENAPI_HOST}:{PORTS["openapi"]}/health',
    'dashboard': f'http://localhost:{PORTS["dashboard"]}'
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

# Q5. 다중 종목 동시 매매 지원
RISK_LIMITS = {
    'max_position_size': 0.10,         # 0.30 → 0.10 (분산 투자)
    'max_daily_loss': 0.05,            # 0.03 → 0.05
    'max_total_loss': 0.15,            # 0.10 → 0.15
    'max_consecutive_losses': 5,       # 3 → 5
    'position_limit': 50,              # 5 → 50 (다중 종목)
    'emergency_stop_loss': 0.20
}

# Q4. 동적 파라미터: 더 많은 종목 포착
THRESHOLDS = {
    'min_ai_score': 4.0,               # 7.0 → 4.0 (더 많은 기회)
    'min_trading_volume': 50000,       # 100000 → 50000
    'max_spread_pct': 0.05,            # 0.02 → 0.05
    'min_market_cap': 10_000_000_000   # 100B → 10B (소형주 포함)
}

# Q5. 다중 종목 동시 매매: 스캔당 매수 수 확대
BUY_SCORE_THRESHOLDS = {
    'ai_buy': 100,                     # 150 → 100 (더 많은 기회)
    'ai_hold': 180,                    # 220 → 180
    'max_score': 440,
    'max_buys_per_scan': 15            # 3 → 15 (동시 매수)
}

RETRY_CONFIG = {
    'max_retries': 3,
    'backoff_factor': 2.0,
    'max_backoff': 60.0
}
