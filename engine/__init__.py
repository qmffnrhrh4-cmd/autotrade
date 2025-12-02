"""
engine/
자율 진화형 자동매매 엔진 모듈

주요 구성:
- autonomous_trading_engine.py: 핵심 자동매매 엔진
- api_data_aggregator.py: 전체 API 데이터 수집기
- continuous_evolution.py: 24시간 연속 진화 시스템
"""

from engine.autonomous_trading_engine import (
    AutonomousTradingEngine,
    TradingSignal,
    create_autonomous_engine
)

from engine.api_data_aggregator import (
    APIDataAggregator,
    MarketSignal,
    MarketSnapshot
)

from engine.continuous_evolution import (
    ContinuousEvolution,
    StrategyGene,
    EvolutionResult,
    MARKET_PRESETS
)

__all__ = [
    # 자동매매 엔진
    'AutonomousTradingEngine',
    'TradingSignal',
    'create_autonomous_engine',

    # API 수집기
    'APIDataAggregator',
    'MarketSignal',
    'MarketSnapshot',

    # 연속 진화
    'ContinuousEvolution',
    'StrategyGene',
    'EvolutionResult',
    'MARKET_PRESETS',
]

