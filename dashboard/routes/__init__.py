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
from .system import system_bp
from .pages import pages_bp
from .alerts import alerts_bp
from .backtest import backtest_bp

__all__ = [
    'account_bp',
    'trading_bp',
    'ai_bp',
    'market_bp',
    'portfolio_bp',
    'system_bp',
    'pages_bp',
    'alerts_bp',
    'backtest_bp'
]


def register_routes(app):
    """Register all route blueprints with the Flask app"""
    app.register_blueprint(account_bp)
    app.register_blueprint(trading_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(pages_bp)
