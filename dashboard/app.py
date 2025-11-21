"""AutoTrade Pro v5.4 - Modular Dashboard"""
import os
import sys
import time
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

REALTIME_UPDATE_INTERVAL = 3

# Import config constants
try:
    from config.constants import HOST, PORTS
except ImportError:
    # Fallback to hardcoded values if config not available
    HOST = '0.0.0.0'
    PORTS = {'dashboard': 5000}

# Import unified settings manager
try:
    from config.unified_settings import get_unified_settings
    unified_settings = get_unified_settings()
except ImportError:
    unified_settings = None

# Import real-time minute chart manager
try:
    from core.realtime_minute_chart import RealtimeMinuteChartManager
except ImportError:
    RealtimeMinuteChartManager = None

# Create Flask app
app = Flask(__name__,
           template_folder='templates',
           static_folder='static')
app.config['SECRET_KEY'] = 'autotrade-pro-v5-modular'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Suppress Flask/werkzeug logs (only show warnings and errors)
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)
app.logger.setLevel(logging.WARNING)

# Global state
bot_instance = None
config_manager = None
realtime_chart_manager = None


# ============================================================================
# ROUTE REGISTRATION
# ============================================================================

# Import all route blueprints
from .routes import (
    account_bp, trading_bp, market_bp,
    portfolio_bp, smart_rebalance_bp, system_bp, pages_bp, alerts_bp, backtest_bp, virtual_trading_bp, program_manager_bp,
    evolution_bp,  # Fix: 전략 진화 API 추가
    backtest_analysis_bp,  # 백테스팅 결과 분석
    live_trading_bp  # 실전 투자 전환
)

# Import automation routes (v5.5: 고급 자동화 시스템)
from .routes.automation import automation_bp, init_automation_routes

# Import AI routes registration function (v5.7.5: modularized AI routes)
from .routes.ai import register_ai_routes, set_bot_instance as ai_set_bot

# Import route setter functions
from .routes.account import set_bot_instance as account_set_bot
from .routes.trading import set_bot_instance as trading_set_bot, set_socketio as trading_set_socketio
from .routes.market import set_bot_instance as market_set_bot, set_realtime_chart_manager as market_set_chart_manager
from .routes.portfolio import set_bot_instance as portfolio_set_bot
from .routes.smart_rebalance import set_bot_instance as smart_rebalance_set_bot  # v6.1.2
from .routes.system import (
    set_bot_instance as system_set_bot,
    set_config_manager as system_set_config_manager,
    set_unified_settings as system_set_unified_settings
)
from .routes.backtest import set_bot_instance as backtest_set_bot
from .routes.virtual_trading import init_virtual_trading_manager
from .routes.program_manager import set_bot_instance as program_manager_set_bot
from .routes.backtest_analysis import set_bot_instance as backtest_analysis_set_bot
from .routes.live_trading import set_bot_instance as live_trading_set_bot, set_live_trading_bridge

# Register all blueprints
app.register_blueprint(account_bp)
app.register_blueprint(trading_bp)
register_ai_routes(app)  # v5.7.5: Register modularized AI routes (6 sub-blueprints, 34 endpoints)
app.register_blueprint(market_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(smart_rebalance_bp)  # v6.1.2: AI-powered smart rebalancing
app.register_blueprint(system_bp)
app.register_blueprint(pages_bp)
app.register_blueprint(alerts_bp)  # v5.7.5: 알림 시스템
app.register_blueprint(backtest_bp)  # 백테스팅 시스템
app.register_blueprint(virtual_trading_bp)  # 가상매매 시스템
app.register_blueprint(automation_bp)  # v5.5: 고급 자동화 시스템
app.register_blueprint(program_manager_bp)  # 프로그램 매니저
app.register_blueprint(evolution_bp)  # Fix: 전략 진화 시스템
app.register_blueprint(backtest_analysis_bp)  # 백테스팅 결과 분석
app.register_blueprint(live_trading_bp)  # 실전 투자 전환

# Register WebSocket handlers
from .websocket import register_websocket_handlers
register_websocket_handlers(socketio)


# ============================================================================
# HELPER FUNCTIONS (Preserved from original app_apple.py)
# ============================================================================

def get_control_status() -> Dict[str, Any]:
    """Get control.json status"""
    control_file = BASE_DIR / 'data' / 'control.json'
    try:
        with open(control_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"trading_enabled": False}


# ============================================================================
# REAL-TIME UPDATE THREAD
# ============================================================================

def realtime_update_thread():
    """Background thread for pushing real-time updates"""
    while True:
        time.sleep(3)  # Update every 3 seconds

        try:
            # Push status update
            control = get_control_status()
            socketio.emit('status_update', {
                'timestamp': datetime.now().isoformat(),
                'trading_enabled': control.get('trading_enabled', False)
            })
        except Exception as e:
            print(f"Error in realtime update: {e}")


# Start real-time update thread
update_thread = threading.Thread(target=realtime_update_thread, daemon=True)
update_thread.start()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def run_dashboard(bot=None, host: str = None, port: int = None, debug: bool = False):
    """Run the modular dashboard

    Args:
        bot: Trading bot instance
        host: Host to bind to (default: from config.constants.HOST)
        port: Port to bind to (default: from config.constants.PORTS['dashboard'])
        debug: Enable debug mode (default: False)
    """
    # Use config defaults if not specified
    if host is None:
        host = HOST
    if port is None:
        port = PORTS['dashboard']
    global bot_instance, realtime_chart_manager
    bot_instance = bot

    # Initialize all route modules with bot instance
    if bot_instance:
        account_set_bot(bot_instance)
        trading_set_bot(bot_instance)
        trading_set_socketio(socketio)
        ai_set_bot(bot_instance)
        market_set_bot(bot_instance)
        portfolio_set_bot(bot_instance)
        smart_rebalance_set_bot(bot_instance)  # v6.1.2
        system_set_bot(bot_instance)
        backtest_set_bot(bot_instance)
        program_manager_set_bot(bot_instance)
        backtest_analysis_set_bot(bot_instance)
        live_trading_set_bot(bot_instance)

        # Set config manager and unified settings for system routes
        if config_manager:
            system_set_config_manager(config_manager)
        if unified_settings:
            system_set_unified_settings(unified_settings)

    # Initialize virtual trading manager
    try:
        init_virtual_trading_manager(bot=bot_instance)
        print("✅ Virtual trading manager initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize virtual trading manager: {e}")

    # Initialize automation routes (v5.5: 고급 자동화 시스템)
    try:
        init_automation_routes(bot=bot_instance)
        print("✅ Automation routes initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize automation routes: {e}")

    # Initialize live trading bridge
    try:
        if bot_instance and hasattr(bot_instance, 'virtual_trader'):
            from virtual_trading import VirtualTradingManager, get_live_trading_bridge, LiveTradingConfig

            # 가상 매매 매니저 가져오기
            virtual_manager = bot_instance.virtual_trader if hasattr(bot_instance, 'virtual_trader') else None

            # 실전 거래 API 가져오기
            trading_api = bot_instance.trading_api if hasattr(bot_instance, 'trading_api') else None

            if virtual_manager and trading_api:
                live_bridge = get_live_trading_bridge(
                    virtual_manager=virtual_manager,
                    trading_api=trading_api,
                    config=LiveTradingConfig()
                )
                set_live_trading_bridge(live_bridge)
                print("✅ Live trading bridge initialized")
            else:
                print("⚠️ Virtual manager or trading API not available")
    except Exception as e:
        print(f"⚠️ Failed to initialize live trading bridge: {e}")

    # Initialize real-time minute chart manager if WebSocket is available
    if bot_instance and hasattr(bot_instance, 'websocket_manager') and bot_instance.websocket_manager:
        if RealtimeMinuteChartManager:
            try:
                realtime_chart_manager = RealtimeMinuteChartManager(bot_instance.websocket_manager)
                market_set_chart_manager(realtime_chart_manager)
                print("✅ Real-time minute chart manager initialized")
            except Exception as e:
                print(f"⚠️ Failed to initialize real-time minute chart manager: {e}")
                realtime_chart_manager = None
        else:
            print("⚠️ RealtimeMinuteChartManager not available")
    else:
        print("⚠️ WebSocket manager not available, real-time minute charts disabled")

    print("=" * 80)
    print("🚀 AutoTrade Pro v5.4 - Modular AI-Powered Trading Dashboard")
    print("=" * 80)
    print(f"📱 Dashboard URL: http://localhost:{port}")
    print(f"🤖 AI Systems: 18 integrated (v4.0 + v4.1 + v4.2)")
    print(f"📊 API Endpoints: 84 total")
    print(f"🎨 Design: Apple-inspired minimalist UI")
    print(f"⚡ New in v5.4: Modular architecture, better maintainability")
    print(f"📁 Code Organization: routes/ + websocket/ + utils/")
    print("=" * 80)

    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


def create_app():
    """Create Flask app (for testing)"""
    return app


# Export for backward compatibility
__all__ = ['run_dashboard', 'create_app', 'app', 'socketio']
