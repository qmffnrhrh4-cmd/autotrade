"""
strategy 패키지
매매 전략 모듈

v5.0 Changes:
- Consolidated RiskManager into DynamicRiskManager
- Position now imported from core (standardized)
- PositionManager still available for backward compatibility
"""
from .base_strategy import BaseStrategy
from .momentum_strategy import MomentumStrategy
from .portfolio_manager import PortfolioManager
from .dynamic_risk_manager import DynamicRiskManager, RiskMode, RiskModeConfig

# v4.0 Advanced Strategies
try:
    from .trailing_stop_manager import TrailingStopManager, TrailingStopState
    from .volatility_breakout_strategy import VolatilityBreakoutStrategy, BreakoutState
    from .pairs_trading_strategy import PairsTradingStrategy, PairState
    from .kelly_criterion import KellyCriterion, KellyParameters
    from .institutional_following_strategy import InstitutionalFollowingStrategy, InstitutionalData
except ImportError:
    # numpy 등 의존성 없을 때
    TrailingStopManager = TrailingStopState = None
    VolatilityBreakoutStrategy = BreakoutState = None
    PairsTradingStrategy = PairState = None
    KellyCriterion = KellyParameters = None
    InstitutionalFollowingStrategy = InstitutionalData = None

# v4.2: Position from core (standardized), PositionManager from local
from core import Position  # v4.2: Use standard Position
from .position_manager import PositionManager, get_position_manager
from .signal_checker import SignalChecker, SignalType, TradingSignalValidator

__all__ = [
    'BaseStrategy',
    'MomentumStrategy',
    'PortfolioManager',
    'DynamicRiskManager',
    'RiskMode',
    'RiskModeConfig',
    # v4.0 Advanced Strategies
    'TrailingStopManager',
    'TrailingStopState',
    'VolatilityBreakoutStrategy',
    'BreakoutState',
    'PairsTradingStrategy',
    'PairState',
    'KellyCriterion',
    'KellyParameters',
    'InstitutionalFollowingStrategy',
    'InstitutionalData',
    # v4.0 Utilities
    'PositionManager',
    'Position',
    'get_position_manager',
    'SignalChecker',
    'SignalType',
    'TradingSignalValidator',
]