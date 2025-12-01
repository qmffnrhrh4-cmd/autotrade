"""
Strategy Backtester - 호환성 레이어
기존 코드와의 호환성을 위해 unified_backtester로 리다이렉트

실제 구현: ai/unified_backtester.py
"""

from ai.unified_backtester import (
    UnifiedBacktester as StrategyBacktester,
    BacktestConfig,
    BacktestResult,
    BacktestTrade,
    get_backtest_engine,
)

from virtual_trading.diverse_strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    BreakoutStrategy,
    ValueInvestingStrategy,
    SwingTradingStrategy,
    MACDStrategy,
    ContrarianStrategy,
    SectorRotationStrategy,
    HotStockStrategy,
    DividendGrowthStrategy,
    InstitutionalFollowingStrategy,
    VolumeRSIStrategy
)

__all__ = [
    'StrategyBacktester',
    'BacktestConfig',
    'BacktestResult',
    'BacktestTrade',
    'get_backtest_engine',
    'MomentumStrategy',
    'MeanReversionStrategy',
    'BreakoutStrategy',
    'ValueInvestingStrategy',
    'SwingTradingStrategy',
    'MACDStrategy',
    'ContrarianStrategy',
    'SectorRotationStrategy',
    'HotStockStrategy',
    'DividendGrowthStrategy',
    'InstitutionalFollowingStrategy',
    'VolumeRSIStrategy',
    'STRATEGY_CLASSES',
]


STRATEGY_CLASSES = {
    'momentum': MomentumStrategy,
    'mean_reversion': MeanReversionStrategy,
    'breakout': BreakoutStrategy,
    'value_investing': ValueInvestingStrategy,
    'swing_trading': SwingTradingStrategy,
    'macd': MACDStrategy,
    'contrarian': ContrarianStrategy,
    'sector_rotation': SectorRotationStrategy,
    'hot_stock': HotStockStrategy,
    'dividend_growth': DividendGrowthStrategy,
    'institutional_following': InstitutionalFollowingStrategy,
    'volume_rsi': VolumeRSIStrategy,
}
