"""
virtual_trading 패키지
가상매매 시스템 (Paper Trading)
YOLO-style 연속 학습 및 진화 알고리즘 포함
"""
from .virtual_account import VirtualAccount
from .virtual_trader import VirtualTrader
from .performance_tracker import PerformanceTracker
from .trade_logger import TradeLogger
from .models import VirtualTradingDB
from .manager import VirtualTradingManager
from .scheduler import VirtualTradingScheduler
from .backtest_adapter import BacktestAdapter
from .ai_strategy_manager import AIStrategyManager
from .evolution_engine import StrategyEvolutionEngine, get_evolution_engine

__all__ = [
    'VirtualAccount',
    'VirtualTrader',
    'PerformanceTracker',
    'TradeLogger',
    'VirtualTradingDB',
    'VirtualTradingManager',
    'VirtualTradingScheduler',
    'BacktestAdapter',
    'AIStrategyManager',
    'StrategyEvolutionEngine',
    'get_evolution_engine',
]
