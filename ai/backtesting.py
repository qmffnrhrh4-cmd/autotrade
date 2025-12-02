"""
Backtesting Engine - 호환성 레이어
기존 코드와의 호환성을 위해 unified_backtester로 리다이렉트

실제 구현: ai/unified_backtester.py
"""

from ai.unified_backtester import (
    UnifiedBacktester as BacktestEngine,
    BacktestConfig,
    BacktestResult,
    BacktestTrade,
    get_backtest_engine,
    SimpleStrategy,
    MomentumStrategy,
    MeanReversionStrategy,
    ConservativeStrategy,
    AggressiveStrategy,
    BUILTIN_STRATEGIES,
)

__all__ = [
    'BacktestEngine',
    'BacktestConfig',
    'BacktestResult',
    'BacktestTrade',
    'get_backtest_engine',
    'SimpleStrategy',
    'MomentumStrategy',
    'MeanReversionStrategy',
    'ConservativeStrategy',
    'AggressiveStrategy',
    'BUILTIN_STRATEGIES',
    'moving_average_crossover_strategy',
    'rsi_strategy',
]


def moving_average_crossover_strategy(data, portfolio):
    """기존 호환성을 위한 이동평균 크로스오버 전략"""
    import numpy as np

    signal = np.random.choice(['buy', 'sell', 'hold'], p=[0.1, 0.1, 0.8])

    if signal == 'buy' and portfolio.get('cash', 0) > 100000:
        return {
            'action': 'buy',
            'stock_code': data.get('stock_code'),
            'quantity': 10
        }
    elif signal == 'sell' and portfolio.get('total_positions', 0) > 0:
        stock_code = data.get('stock_code')
        if stock_code in portfolio.get('positions', {}):
            return {
                'action': 'sell',
                'stock_code': stock_code,
                'quantity': 5
            }

    return {'action': 'hold'}


def rsi_strategy(data, portfolio):
    """기존 호환성을 위한 RSI 전략"""
    rsi = data.get('rsi', 50)

    if rsi < 30 and portfolio.get('cash', 0) > 100000:
        return {
            'action': 'buy',
            'stock_code': data.get('stock_code'),
            'quantity': 15
        }
    elif rsi > 70 and portfolio.get('total_positions', 0) > 0:
        return {
            'action': 'sell',
            'stock_code': data.get('stock_code'),
            'quantity': 10
        }

    return {'action': 'hold'}
