"""
Trading Routes Module
Handles all trading-related API endpoints including control, paper trading, virtual trading, and backtesting
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from flask import Blueprint, jsonify, request
from utils.response_helper import error_response

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
        # Note: error_response doesn't support 'enabled' key, so keep jsonify for special format
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
        return error_response(str(e))


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
        return error_response(str(e))


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
            return error_response('Strategy not found', status=404)
    except Exception as e:
        print(f"Paper trading account API error: {e}")
        return error_response(str(e))


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
        # Note: error_response doesn't support 'enabled' key, so keep jsonify for special format
        return jsonify({'success': False, 'message': str(e), 'enabled': False})


@trading_bp.route('/api/virtual_trading/account/<strategy_name>')
def get_virtual_trading_account(strategy_name: str):
    """Get virtual trading account details for specific strategy"""
    try:
        if not _bot_instance or not hasattr(_bot_instance, 'virtual_trader'):
            return error_response('Virtual trading not initialized')

        virtual_trader = _bot_instance.virtual_trader
        if not virtual_trader:
            return error_response('Virtual trading not enabled')

        if strategy_name not in virtual_trader.accounts:
            return error_response('Strategy not found', status=404)

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
        return error_response(str(e))


@trading_bp.route('/api/virtual_trading/trades')
def get_virtual_trading_trades():
    """Get virtual trading trade history"""
    try:
        if not _bot_instance or not hasattr(_bot_instance, 'trade_logger'):
            return error_response('Trade logger not initialized')

        trade_logger = _bot_instance.trade_logger
        if not trade_logger:
            return error_response('Trade logger not enabled')

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
        return error_response(str(e))


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
        if not virtual_trader:
            return jsonify({
                'success': False,
                'message': '가상매매 미활성화'
            })

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
        return error_response(str(e))


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
        return error_response(str(e))


@trading_bp.route('/api/sell-all', methods=['POST'])
def sell_all_positions():
    """Sell all positions at market price"""
    try:
        if not _bot_instance:
            return error_response('Bot instance not available')

        if not hasattr(_bot_instance, 'trading_api'):
            return error_response('Trading API not available')
        
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
            return error_response('Account API not available')

    except Exception as e:
        logger.error(f"Sell all error: {e}")
        return error_response(str(e))


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
        return error_response(str(e), status=500)


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
            return error_response('요청 데이터가 없습니다', status=400)

        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        price = data.get('price', 0)

        if not stock_code or not stock_name:
            return error_response('종목 코드 또는 이름이 없습니다', status=400)

        # bot_instance 확인
        if not _bot_instance:
            return error_response('봇 인스턴스가 연결되지 않았습니다', status=503)

        # 테스트 모드 확인
        if hasattr(_bot_instance, 'market_status') and _bot_instance.market_status.get('is_test_mode'):
            return error_response('테스트 모드에서는 실제 주문을 실행할 수 없습니다', status=403)

        # 매수 금액 계산 (포트폴리오 관리자 사용)
        if hasattr(_bot_instance, 'portfolio_manager'):
            position_size = _bot_instance.portfolio_manager.calculate_position_size(price)
            quantity = int(position_size / price)
        else:
            # 기본값: 100만원 / 가격
            quantity = int(1_000_000 / price)

        if quantity == 0:
            return error_response('매수 수량이 0입니다', status=400)

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
                return error_response(error_msg, status=500)
        else:
            return error_response('order_api가 연결되지 않았습니다', status=503)

    except Exception as e:
        logger.error(f"Quick buy error: {e}", exc_info=True)
        return error_response(str(e), status=500)


# ============================================================================
# Split Order Management Routes
# ============================================================================

@trading_bp.route('/api/split_orders/active', methods=['GET'])
def get_active_split_orders():
    """
    활성 분할 주문 목록 조회 (미체결 포함)

    Returns:
        JSON: {
            'success': bool,
            'active_groups': [
                {
                    'group_id': str,
                    'stock_code': str,
                    'stock_name': str,
                    'split_type': 'buy' | 'sell',
                    'total_quantity': int,
                    'filled_quantity': int,
                    'average_price': float,
                    'completion_ratio': float,
                    'is_completed': bool,
                    'created_at': str,
                    'entries': [
                        {
                            'entry_id': str,
                            'order_number': str,
                            'quantity': int,
                            'price': float,
                            'filled_quantity': int,
                            'filled_price': float,
                            'status': 'pending' | 'partial' | 'filled' | 'cancelled',
                            'fill_ratio': float
                        }
                    ]
                }
            ]
        }
    """
    try:
        from strategy.split_order_manager import get_split_order_manager

        manager = get_split_order_manager()

        # 모든 활성 그룹 조회
        active_groups = []
        for group_id in list(manager.active_groups.keys()):
            group_status = manager.get_group_status(group_id)
            if group_status:
                # created_at을 ISO format string으로 변환
                group_status['created_at'] = manager.active_groups[group_id].created_at.isoformat()
                active_groups.append(group_status)

        # 생성 시간 기준 내림차순 정렬 (최신순)
        active_groups.sort(key=lambda x: x['created_at'], reverse=True)

        return jsonify({
            'success': True,
            'active_groups': active_groups,
            'total_count': len(active_groups)
        })

    except Exception as e:
        logger.error(f"Failed to get active split orders: {e}", exc_info=True)
        return error_response(str(e), status=500)


@trading_bp.route('/api/split_orders/<group_id>', methods=['GET'])
def get_split_order_detail(group_id: str):
    """
    특정 분할 주문 그룹의 상세 정보 조회

    Args:
        group_id: 그룹 ID (예: BUY_005930_20250124100530)

    Returns:
        JSON: 그룹 상세 정보
    """
    try:
        from strategy.split_order_manager import get_split_order_manager

        manager = get_split_order_manager()
        group_status = manager.get_group_status(group_id)

        if not group_status:
            return error_response(f'그룹 ID {group_id}를 찾을 수 없습니다', status=404)

        # created_at 변환
        if group_id in manager.active_groups:
            group_status['created_at'] = manager.active_groups[group_id].created_at.isoformat()

        return jsonify({
            'success': True,
            'group': group_status
        })

    except Exception as e:
        logger.error(f"Failed to get split order detail: {e}", exc_info=True)
        return error_response(str(e), status=500)


@trading_bp.route('/api/split_orders/<group_id>/cancel', methods=['POST'])
def cancel_split_order_group(group_id: str):
    """
    특정 분할 주문 그룹의 미체결 주문 취소

    Args:
        group_id: 그룹 ID

    Returns:
        JSON: {
            'success': bool,
            'message': str,
            'cancelled_count': int
        }
    """
    try:
        from strategy.split_order_manager import get_split_order_manager

        manager = get_split_order_manager()

        # 그룹 확인
        if group_id not in manager.active_groups:
            return error_response(f'그룹 ID {group_id}를 찾을 수 없습니다', status=404)

        group = manager.active_groups[group_id]

        # 미체결 주문 개수 확인
        pending_entries = group.get_pending_entries()
        pending_count = len(pending_entries)

        if pending_count == 0:
            return jsonify({
                'success': True,
                'message': '취소할 미체결 주문이 없습니다',
                'cancelled_count': 0
            })

        # bot_instance에서 split_order_executor 가져오기
        if not _bot_instance:
            return error_response('Trading bot이 연결되지 않았습니다', status=503)

        # SplitOrderExecutor 인스턴스 가져오기
        # bot_instance에서 직접 접근하거나, 새로 생성
        from strategy.split_order_executor import SplitOrderExecutor

        order_api = getattr(_bot_instance, 'order_api', None)
        data_fetcher = getattr(_bot_instance, 'data_fetcher', None)

        if not order_api:
            return error_response('OrderAPI가 연결되지 않았습니다', status=503)

        executor = SplitOrderExecutor(order_api=order_api, data_fetcher=data_fetcher)

        # 그룹 취소 실행
        success = executor.cancel_group(group_id)

        if success:
            return jsonify({
                'success': True,
                'message': f'{pending_count}개의 미체결 주문을 취소했습니다',
                'cancelled_count': pending_count,
                'group_id': group_id
            })
        else:
            return error_response('주문 취소에 실패했습니다', status=500)

    except Exception as e:
        logger.error(f"Failed to cancel split order group: {e}", exc_info=True)
        return error_response(str(e), status=500)


@trading_bp.route('/api/split_orders/completed', methods=['GET'])
def get_completed_split_orders():
    """
    완료된 분할 주문 목록 조회

    Query Params:
        limit: 조회할 최대 개수 (기본값: 50)

    Returns:
        JSON: 완료된 그룹 목록
    """
    try:
        from strategy.split_order_manager import get_split_order_manager

        limit = int(request.args.get('limit', 50))
        manager = get_split_order_manager()

        # 완료된 그룹 조회 (최근순)
        completed_groups = []
        for group in reversed(manager.completed_groups[-limit:]):
            completed_groups.append({
                'group_id': group.group_id,
                'stock_code': group.stock_code,
                'stock_name': group.stock_name,
                'split_type': group.split_type.value,
                'total_quantity': group.total_quantity,
                'filled_quantity': group.get_filled_quantity(),
                'average_price': group.get_average_price(),
                'created_at': group.created_at.isoformat(),
                'completed_at': group.completed_at.isoformat() if group.completed_at else None,
                'entries_count': len(group.entries)
            })

        return jsonify({
            'success': True,
            'completed_groups': completed_groups,
            'total_count': len(completed_groups)
        })

    except Exception as e:
        logger.error(f"Failed to get completed split orders: {e}", exc_info=True)
        return error_response(str(e), status=500)
