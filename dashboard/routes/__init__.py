"""
Dashboard routes package
"""
from flask import Blueprint

# Import all route blueprints
from .account import account_bp
from .trading import trading_bp
from .ai import ai_bp
from .market import market_bp
from .portfolio import portfolio_bp
from .smart_rebalance import smart_rebalance_bp  # v6.1.2: AI-powered smart rebalancing
from .system import system_bp
from .pages import pages_bp
from .alerts import alerts_bp
from .backtest import backtest_bp
from .virtual_trading import virtual_trading_bp
from .automation import automation_bp
from .program_manager import program_manager_bp
from .strategy_evolution import evolution_bp  # Fix: 전략 진화 API 추가
from .backtest_analysis import backtest_analysis_bp  # 백테스팅 결과 분석
from .live_trading import live_trading_bp  # 실전 투자 전환

__all__ = [
    'account_bp',
    'trading_bp',
    'ai_bp',
    'market_bp',
    'portfolio_bp',
    'smart_rebalance_bp',  # v6.1.2: AI-powered smart rebalancing
    'system_bp',
    'pages_bp',
    'alerts_bp',
    'backtest_bp',
    'virtual_trading_bp',
    'automation_bp',
    'program_manager_bp',
    'evolution_bp',  # Fix: 전략 진화 API 추가
    'backtest_analysis_bp',  # 백테스팅 결과 분석
    'live_trading_bp'  # 실전 투자 전환
]


def register_routes(app):
    """Register all route blueprints with the Flask app"""
    app.register_blueprint(account_bp)
    app.register_blueprint(trading_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(smart_rebalance_bp)  # v6.1.2: AI-powered smart rebalancing
    app.register_blueprint(system_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(backtest_bp)
    app.register_blueprint(virtual_trading_bp)
    app.register_blueprint(automation_bp)
    app.register_blueprint(program_manager_bp)
    app.register_blueprint(evolution_bp)  # v6.1.3: 전략 진화 API
    app.register_blueprint(backtest_analysis_bp)  # 백테스팅 결과 분석
    app.register_blueprint(live_trading_bp)  # 실전 투자 전환
