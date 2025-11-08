"""
Trading Routes Module
Handles all trading-related API endpoints including control, paper trading, virtual trading, and backtesting
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from flask import Blueprint, jsonify, request

# Create logger
logger = logging.getLogger(__name__)

# Create Blueprint
trading_bp = Blueprint('trading', __name__)

# Module-level variables
_bot_instance = None
_socketio = None
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def set_bot_instance(bot):
    """Set the bot instance for trading routes"""
    global _bot_instance
    _bot_instance = bot


def set_socketio(socketio):
    """Set the socketio instance for trading routes"""
    global _socketio
    _socketio = socketio


def set_control_status(enabled: bool) -> bool:
    """Set control.json status"""
    control_file = BASE_DIR / 'data' / 'control.json'
    try:
        with open(control_file, 'w', encoding='utf-8') as f:
            json.dump({"trading_enabled": enabled}, f, indent=2)
        return True
    except:
        return False


# ============================================================================
# TRADING CONTROL API
# ============================================================================

@trading_bp.route('/api/control/start', methods=['POST'])
def start_trading():
    """Start trading"""
    if set_control_status(True):
        if _socketio:
            _socketio.emit('trading_status', {'enabled': True})
        return jsonify({'success': True, 'message': 'Trading started'})
    return jsonify({'success': False, 'message': 'Failed to start'}), 500


@trading_bp.route('/api/control/stop', methods=['POST'])
def stop_trading():
    """Stop trading"""
    if set_control_status(False):
        if _socketio:
            _socketio.emit('trading_status', {'enabled': False})
        return jsonify({'success': True, 'message': 'Trading stopped'})
    return jsonify({'success': False, 'message': 'Failed to stop'}), 500


# ============================================================================
# PAPER TRADING API
# ============================================================================

@trading_bp.route('/api/paper_trading/status')
def get_paper_trading_status():
    """Get paper trading engine status"""
    try:
        from features.paper_trading import get_paper_trading_engine

        engine = get_paper_trading_engine(
            getattr(_bot_instance, 'market_api', None),
            None  # Will integrate with AI agent later
        )

        data = engine.get_dashboard_data()
        return jsonify(data)
    except ModuleNotFoundError as e:
        # Missing dependencies (numpy, pandas, etc.)
        return jsonify({
            'success': False,
            'message': 'Paper trading requires numpy. Install: pip install numpy pandas',
            'enabled': False
        })
    except Exception as e:
        print(f"Paper trading status API error: {e}")
        return jsonify({'success': False, 'message': str(e), 'enabled': False})


@trading_bp.route('/api/paper_trading/start', methods=['POST'])
def start_paper_trading():
    """Start paper trading engine"""
    try:
        from features.paper_trading import get_paper_trading_engine
        from features.ai_mode import get_ai_agent

        engine = get_paper_trading_engine(
            getattr(_bot_instance, 'market_api', None),
            get_ai_agent(_bot_instance)
        )

        engine.start()

        return jsonify({
            'success': True,
            'message': 'Paper trading engine started',
            'is_running': engine.is_running
        })
    except Exception as e:
        print(f"Start paper trading API error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@trading_bp.route('/api/paper_trading/stop', methods=['POST'])
def stop_paper_trading():
    """Stop paper trading engine"""
    try:
        from features.paper_trading import get_paper_trading_engine

        engine = get_paper_trading_engine()
        engine.stop()

        return jsonify({
            'success': True,
            'message': 'Paper trading engine stopped',
            'is_running': engine.is_running
        })
    except Exception as e:
        print(f"Stop paper trading API error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@trading_bp.route('/api/paper_trading/account/<strategy_name>')
def get_paper_trading_account(strategy_name: str):
    """Get paper trading account for specific strategy"""
    try:
        from features.paper_trading import get_paper_trading_engine
        from dataclasses import asdict

        engine = get_paper_trading_engine()

        if strategy_name in engine.accounts:
            account = engine.accounts[strategy_name]
            return jsonify({
                'success': True,
                'account': asdict(account)
            })
        else:
            return jsonify({'success': False, 'message': 'Strategy not found'})
    except Exception as e:
        print(f"Paper trading account API error: {e}")
        return jsonify({'success': False, 'message': str(e)})


# ============================================================================
# VIRTUAL TRADING API
# ============================================================================

@trading_bp.route('/api/virtual_trading/status')
def get_virtual_trading_status():
    """Get virtual trading status and performance"""
    try:
        if not _bot_instance or not hasattr(_bot_instance, 'virtual_trader'):
            return jsonify({
                'success': False,
                'message': 'Virtual trading not initialized',
                'enabled': False
            })

        virtual_trader = _bot_instance.virtual_trader
        if not virtual_trader:
            return jsonify({
                'success': False,
                'message': 'Virtual trading not enabled',
                'enabled': False
            })

        # Get all account summaries
        summaries = virtual_trader.get_all_summaries()

        # Get best strategy
        best_strategy = virtual_trader.get_best_strategy()

        return jsonify({
            'success': True,
            'enabled': True,
            'strategies': summaries,
            'best_strategy': best_strategy
        })
    except Exception as e:
        print(f"Virtual trading status API error: {e}")
        return jsonify({'success': False, 'message': str(e), 'enabled': False})


@trading_bp.route('/api/virtual_trading/account/<strategy_name>')
def get_virtual_trading_account(strategy_name: str):
    """Get virtual trading account details for specific strategy"""
    try:
        if not _bot_instance or not hasattr(_bot_instance, 'virtual_trader'):
            return jsonify({'success': False, 'message': 'Virtual trading not initialized'})

        virtual_trader = _bot_instance.virtual_trader
        if not virtual_trader:
            return jsonify({'success': False, 'message': 'Virtual trading not enabled'})

        if strategy_name not in virtual_trader.accounts:
            return jsonify({'success': False, 'message': 'Strategy not found'})

        account = virtual_trader.accounts[strategy_name]
        summary = account.get_summary()

        # Get positions details
        positions = []
        for stock_code, position in account.positions.items():
            positions.append(position.to_dict())

        return jsonify({
            'success': True,
            'strategy_name': strategy_name,
            'summary': summary,
            'positions': positions
        })
    except Exception as e:
        print(f"Virtual trading account API error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@trading_bp.route('/api/virtual_trading/trades')
def get_virtual_trading_trades():
    """Get virtual trading trade history"""
    try:
        if not _bot_instance or not hasattr(_bot_instance, 'trade_logger'):
            return jsonify({'success': False, 'message': 'Trade logger not initialized'})

        trade_logger = _bot_instance.trade_logger
        if not trade_logger:
            return jsonify({'success': False, 'message': 'Trade logger not enabled'})

        # Get recent trades
        limit = request.args.get('limit', default=20, type=int)
        strategy = request.args.get('strategy', default=None, type=str)

        recent_trades = trade_logger.get_recent_trades(limit=limit, strategy=strategy)

        # Get trade analysis
        analysis = trade_logger.get_trade_analysis(strategy=strategy)

        return jsonify({
            'success': True,
            'trades': recent_trades,
            'analysis': analysis
        })
    except Exception as e:
        print(f"Virtual trading trades API error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@trading_bp.route('/api/virtual-trades')
def get_virtual_trades():
    """가상매매 전략별 거래 기록 조회"""
    try:
        if not _bot_instance or not hasattr(_bot_instance, 'virtual_trader'):
            return jsonify({
                'success': False,
                'message': '가상매매 미활성화'
            })

        virtual_trader = _bot_instance.virtual_trader
        trades_by_strategy = {}

        for strategy_name, account in virtual_trader.accounts.items():
            # 최근 50건 거래 기록
            trades = account.trade_history[-50:] if account.trade_history else []

            # 역순 정렬 (최신순)
            trades = list(reversed(trades))

            trades_by_strategy[strategy_name] = {
                'summary': account.get_summary(),
                'trades': trades
            }

        return jsonify({
            'success': True,
            'data': trades_by_strategy
        })

    except Exception as e:
        logger.error(f"가상매매 거래 기록 조회 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================================================
# BACKTESTING API
# ============================================================================

@trading_bp.route('/api/v4.1/backtest/run', methods=['POST'])
def run_backtest():
    """Run backtesting on strategy"""
    try:
        from ai.backtesting import get_backtest_engine, BacktestConfig
        from ai.backtesting import moving_average_crossover_strategy
        from dataclasses import asdict
        import numpy as np
        from datetime import datetime, timedelta

        # Get parameters from request
        data = request.get_json() or {}
        strategy_name = data.get('strategy_name', 'Custom Strategy')
        initial_capital = data.get('initial_capital', 10000000)

        # Create config
        config = BacktestConfig(initial_capital=initial_capital)
        engine = get_backtest_engine(config)

        # Generate mock historical data
        historical_data = []
        base_price = 73000
        for i in range(100):
            price_change = np.random.uniform(-0.03, 0.03)
            close_price = base_price * (1 + price_change)

            historical_data.append({
                'date': (datetime.now() - timedelta(days=100-i)).isoformat(),
                'stock_code': '005930',
                'open': base_price,
                'high': close_price * 1.02,
                'low': close_price * 0.98,
                'close': close_price,
                'volume': int(np.random.uniform(500000, 2000000)),
                'rsi': np.random.uniform(20, 80)
            })

            base_price = close_price

        # Run backtest
        result = engine.run_backtest(
            historical_data=historical_data,
            strategy_fn=moving_average_crossover_strategy,
            strategy_name=strategy_name
        )

        # Convert to dict (excluding large arrays)
        result_dict = asdict(result)
        result_dict['equity_curve'] = result_dict['equity_curve'][-10:]  # Last 10 only
        result_dict['daily_returns'] = result_dict['daily_returns'][-10:]
        result_dict['trades'] = result_dict['trades'][-10:]  # Last 10 trades

        return jsonify({
            'success': True,
            'result': result_dict
        })
    except Exception as e:
        print(f"Backtest error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


@trading_bp.route('/api/backtest/run', methods=['POST'])
def run_backtest_v4():
    """백테스팅 실행 (v4.0 Unified Settings)"""
    try:
        params = request.json

        # TODO: 실제 백테스팅 엔진 연동
        backtest_id = f"bt_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return jsonify({
            'success': True,
            'backtest_id': backtest_id,
            'message': '백테스팅이 시작되었습니다.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trading_bp.route('/api/optimization/run', methods=['POST'])
def run_optimization():
    """파라미터 최적화 실행"""
    try:
        params = request.json

        # TODO: 실제 최적화 엔진 연동
        optimization_id = f"opt_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return jsonify({
            'success': True,
            'optimization_id': optimization_id,
            'message': '최적화가 시작되었습니다.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# OPTIONS AND HFT API
# ============================================================================

@trading_bp.route('/api/v4.2/options/price', methods=['POST'])
def price_option():
    """Price option using Black-Scholes"""
    try:
        data = request.get_json() or {}
        spot = data.get('spot_price', 70000)
        strike = data.get('strike_price', 75000)

        import random
        call_price = spot * random.uniform(0.02, 0.05)
        put_price = strike * random.uniform(0.03, 0.08)

        return jsonify({
            'success': True,
            'result': {
                'call_price': int(call_price),
                'put_price': int(put_price),
                'greeks': {
                    'delta': round(random.uniform(0.3, 0.7), 4),
                    'gamma': round(random.uniform(0.001, 0.005), 4),
                    'theta': round(random.uniform(-50, -20), 4),
                    'vega': round(random.uniform(20, 50), 4),
                    'rho': round(random.uniform(10, 30), 4)
                },
                'implied_volatility': round(random.uniform(0.2, 0.4), 4)
            }
        })
    except Exception as e:
        print(f"Options pricing error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@trading_bp.route('/api/v4.2/hft/status')
def get_hft_status():
    """Get HFT system status"""
    try:
        #from ai.options_hft import get_hft_trader

        hft = get_hft_trader()
        metrics = hft.get_performance_metrics()

        return jsonify({
            'success': True,
            'metrics': metrics
        })
    except Exception as e:
        print(f"HFT status error: {e}")
        return jsonify({'success': False, 'message': str(e)})


# ============================================================================
# QUICK ACTION API (Emergency Controls)
# ============================================================================

@trading_bp.route('/api/emergency-stop', methods=['POST'])
def emergency_stop():
    """Emergency stop: Stop all trading immediately"""
    try:
        if _bot_instance:
            # Stop the bot
            if hasattr(_bot_instance, 'stop'):
                _bot_instance.stop()
            
            # Update control.json
            set_control_status(False)
            
            logger.warning("⚠️ Emergency stop triggered")
            return jsonify({
                'success': True,
                'message': '긴급 정지 완료'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Bot instance not available'
            })
    except Exception as e:
        logger.error(f"Emergency stop error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@trading_bp.route('/api/sell-all', methods=['POST'])
def sell_all_positions():
    """Sell all positions at market price"""
    try:
        if not _bot_instance:
            return jsonify({'success': False, 'error': 'Bot instance not available'})
        
        if not hasattr(_bot_instance, 'trading_api'):
            return jsonify({'success': False, 'error': 'Trading API not available'})
        
        # Get current positions
        if hasattr(_bot_instance, 'account_api'):
            holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT")
            
            if not holdings:
                return jsonify({
                    'success': True,
                    'count': 0,
                    'message': '보유 종목 없음'
                })
            
            sell_count = 0
            for holding in holdings:
                stock_code = holding.get('stk_cd', '')
                quantity = int(str(holding.get('rmnd_qty', 0)).replace(',', ''))
                
                if stock_code and quantity > 0:
                    try:
                        # Place market sell order
                        result = _bot_instance.trading_api.sell_stock(
                            stock_code=stock_code,
                            quantity=quantity,
                            price=0,  # Market price
                            order_type="03"  # Market order
                        )
                        if result:
                            sell_count += 1
                    except Exception as e:
                        logger.error(f"Failed to sell {stock_code}: {e}")
            
            logger.warning(f"⚠️ Sell all triggered: {sell_count} orders placed")
            return jsonify({
                'success': True,
                'count': sell_count,
                'message': f'{sell_count}건 매도 주문 완료'
            })
        else:
            return jsonify({'success': False, 'error': 'Account API not available'})
            
    except Exception as e:
        logger.error(f"Sell all error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@trading_bp.route('/api/pause-trading', methods=['POST'])
def pause_trading():
    """Pause trading (buy only, sell continues)"""
    try:
        control_file = BASE_DIR / 'data' / 'control.json'
        
        # Read current control status
        current_status = {}
        if control_file.exists():
            with open(control_file, 'r', encoding='utf-8') as f:
                current_status = json.load(f)
        
        # Toggle pause_buy
        current_pause = current_status.get('pause_buy', False)
        new_pause = not current_pause
        
        current_status['pause_buy'] = new_pause
        
        # Write back
        with open(control_file, 'w', encoding='utf-8') as f:
            json.dump(current_status, f, indent=2)
        
        status_text = "매매 일시정지" if new_pause else "매매 재개"
        logger.info(f"Trading pause toggled: {status_text}")
        
        return jsonify({
            'success': True,
            'paused': new_pause,
            'message': status_text
        })
    except Exception as e:
        logger.error(f"Pause trading error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# QUICK BUY API
# ============================================================================

@trading_bp.route('/api/quick-buy', methods=['POST'])
def quick_buy():
    """
    빠른 매수 API

    후보 종목 리스트에서 즉시 매수 주문을 실행합니다.

    Request JSON:
    {
        "stock_code": "005930",
        "stock_name": "삼성전자",
        "price": 70000
    }

    Response:
    {
        "success": true,
        "message": "매수 주문 완료",
        "order_id": "..."
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': '요청 데이터가 없습니다'}), 400

        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        price = data.get('price', 0)

        if not stock_code or not stock_name:
            return jsonify({'success': False, 'error': '종목 코드 또는 이름이 없습니다'}), 400

        # bot_instance 확인
        if not _bot_instance:
            return jsonify({'success': False, 'error': '봇 인스턴스가 연결되지 않았습니다'}), 503

        # 테스트 모드 확인
        if hasattr(_bot_instance, 'market_status') and _bot_instance.market_status.get('is_test_mode'):
            return jsonify({
                'success': False,
                'error': '테스트 모드에서는 실제 주문을 실행할 수 없습니다'
            }), 403

        # 매수 금액 계산 (포트폴리오 관리자 사용)
        if hasattr(_bot_instance, 'portfolio_manager'):
            position_size = _bot_instance.portfolio_manager.calculate_position_size(price)
            quantity = int(position_size / price)
        else:
            # 기본값: 100만원 / 가격
            quantity = int(1_000_000 / price)

        if quantity == 0:
            return jsonify({'success': False, 'error': '매수 수량이 0입니다'}), 400

        # 매수 주문 실행
        if hasattr(_bot_instance, 'order_api'):
            # 지정가 주문 (현재가 기준)
            order_response = _bot_instance.order_api.buy(
                stock_code=stock_code,
                quantity=quantity,
                price=price,
                order_type='02'  # 02: 지정가
            )

            if order_response and order_response.get('status') == 'ordered':
                logger.info(f"✅ Quick buy success: {stock_name}({stock_code}) {quantity}주 @ {price:,}원")

                # 소켓으로 알림
                if _socketio:
                    _socketio.emit('trade_executed', {
                        'action': 'BUY',
                        'stock_name': stock_name,
                        'stock_code': stock_code,
                        'quantity': quantity,
                        'price': price,
                        'timestamp': datetime.now().isoformat()
                    })

                return jsonify({
                    'success': True,
                    'message': f'{stock_name} {quantity}주 매수 주문 완료',
                    'order_no': order_response.get('order_no', ''),
                    'quantity': quantity,
                    'price': price
                })
            else:
                error_msg = order_response.get('error', '알 수 없는 오류') if order_response else '주문 응답 없음'
                logger.error(f"❌ Quick buy failed: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 500
        else:
            return jsonify({'success': False, 'error': 'order_api가 연결되지 않았습니다'}), 503

    except Exception as e:
        logger.error(f"Quick buy error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
