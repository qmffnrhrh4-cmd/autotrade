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
