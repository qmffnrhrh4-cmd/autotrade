"""
Advanced Backtester - 호환성 레이어
기존 코드와의 호환성을 위해 unified_backtester로 리다이렉트

실제 구현: ai/unified_backtester.py
"""

from ai.unified_backtester import (
    UnifiedBacktester as AdvancedBacktester,
    BacktestConfig,
    BacktestResult,
    BacktestTrade,
    get_backtest_engine,
    OrderSide,
)

__all__ = [
    'AdvancedBacktester',
    'BacktestConfig',
    'BacktestResult',
    'BacktestTrade',
    'get_backtest_engine',
    'OrderSide',
]
