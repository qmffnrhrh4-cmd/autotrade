"""
실전 투자 전환 API
Live Trading Routes

가상매매에서 검증된 전략을 실전 투자로 전환합니다.
"""
import logging
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# Blueprint 생성
live_trading_bp = Blueprint('live_trading', __name__)

# 모듈 레벨 변수
_bot_instance = None
_live_trading_bridge = None


def set_bot_instance(bot):
    """Set the bot instance"""
    global _bot_instance
    _bot_instance = bot


def set_live_trading_bridge(bridge):
    """Set the live trading bridge"""
    global _live_trading_bridge
    _live_trading_bridge = bridge


@live_trading_bp.route('/api/live-trading/validate/<int:strategy_id>')
def validate_strategy(strategy_id: int):
    """
    전략 검증 (실전 투자 가능 여부 확인)

    Args:
        strategy_id: 가상매매 전략 ID

    Returns:
        검증 결과
    """
    try:
        if not _live_trading_bridge:
            return jsonify({
                'success': False,
                'error': '실전 투자 브릿지가 초기화되지 않았습니다'
            }), 503

        result = _live_trading_bridge.validate_strategy(strategy_id)

        return jsonify({
            'success': True,
            'validation': result
        })

    except Exception as e:
        logger.error(f"전략 검증 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@live_trading_bp.route('/api/live-trading/enable', methods=['POST'])
def enable_live_trading():
    """
    실전 투자 활성화

    Request JSON:
    {
        "strategy_id": 1
    }

    Returns:
        활성화 결과
    """
    try:
        if not _live_trading_bridge:
            return jsonify({
                'success': False,
                'error': '실전 투자 브릿지가 초기화되지 않았습니다'
            }), 503

        data = request.get_json()

        if not data or 'strategy_id' not in data:
            return jsonify({
                'success': False,
                'error': 'strategy_id가 필요합니다'
            }), 400

        strategy_id = int(data['strategy_id'])

        result = _live_trading_bridge.enable_live_trading(strategy_id)

        return jsonify(result)

    except Exception as e:
        logger.error(f"실전 투자 활성화 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@live_trading_bp.route('/api/live-trading/disable', methods=['POST'])
def disable_live_trading():
    """
    실전 투자 비활성화

    Returns:
        비활성화 결과
    """
    try:
        if not _live_trading_bridge:
            return jsonify({
                'success': False,
                'error': '실전 투자 브릿지가 초기화되지 않았습니다'
            }), 503

        result = _live_trading_bridge.disable_live_trading()

        return jsonify(result)

    except Exception as e:
        logger.error(f"실전 투자 비활성화 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@live_trading_bp.route('/api/live-trading/status')
def get_live_trading_status():
    """
    실전 투자 현황 조회

    Returns:
        현재 실전 투자 상태 및 성과
    """
    try:
        if not _live_trading_bridge:
            return jsonify({
                'success': False,
                'error': '실전 투자 브릿지가 초기화되지 않았습니다',
                'live_mode_enabled': False
            }), 503

        status = _live_trading_bridge.get_live_status()

        return jsonify({
            'success': True,
            'status': status
        })

    except Exception as e:
        logger.error(f"실전 투자 현황 조회 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'live_mode_enabled': False
        }), 500


@live_trading_bp.route('/api/live-trading/execute', methods=['POST'])
def execute_live_trade():
    """
    실전 주문 실행

    Request JSON:
    {
        "action": "buy" or "sell",
        "stock_code": "005930",
        "stock_name": "삼성전자",
        "quantity": 10,
        "price": 70000,
        "strategy_id": 1
    }

    Returns:
        주문 결과
    """
    try:
        if not _live_trading_bridge:
            return jsonify({
                'success': False,
                'error': '실전 투자 브릿지가 초기화되지 않았습니다'
            }), 503

        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': '요청 데이터가 없습니다'
            }), 400

        # 필수 파라미터 확인
        required_fields = ['action', 'stock_code', 'stock_name', 'quantity', 'price', 'strategy_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} 파라미터가 필요합니다'
                }), 400

        result = _live_trading_bridge.execute_live_trade(
            action=data['action'],
            stock_code=data['stock_code'],
            stock_name=data['stock_name'],
            quantity=int(data['quantity']),
            price=float(data['price']),
            strategy_id=int(data['strategy_id'])
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"실전 주문 실행 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@live_trading_bp.route('/api/live-trading/config', methods=['GET', 'POST'])
def manage_live_trading_config():
    """
    실전 투자 설정 조회/변경

    GET: 현재 설정 조회
    POST: 설정 변경

    Request JSON (POST):
    {
        "max_daily_loss_pct": 5.0,
        "max_position_size_pct": 20.0,
        "initial_live_capital": 10000000
    }

    Returns:
        설정 정보
    """
    try:
        if not _live_trading_bridge:
            return jsonify({
                'success': False,
                'error': '실전 투자 브릿지가 초기화되지 않았습니다'
            }), 503

        if request.method == 'GET':
            # 현재 설정 조회
            config = _live_trading_bridge.config

            return jsonify({
                'success': True,
                'config': {
                    'min_win_rate': config.min_win_rate,
                    'min_trades': config.min_trades,
                    'min_return_rate': config.min_return_rate,
                    'max_drawdown': config.max_drawdown,
                    'max_daily_loss_pct': config.max_daily_loss_pct,
                    'max_position_size_pct': config.max_position_size_pct,
                    'max_total_investment_pct': config.max_total_investment_pct,
                    'initial_live_capital': config.initial_live_capital,
                    'position_sizing_method': config.position_sizing_method
                }
            })

        else:  # POST
            # 설정 변경
            data = request.get_json()

            if not data:
                return jsonify({
                    'success': False,
                    'error': '요청 데이터가 없습니다'
                }), 400

            config = _live_trading_bridge.config

            # 설정 업데이트
            if 'max_daily_loss_pct' in data:
                config.max_daily_loss_pct = float(data['max_daily_loss_pct'])
            if 'max_position_size_pct' in data:
                config.max_position_size_pct = float(data['max_position_size_pct'])
            if 'initial_live_capital' in data:
                config.initial_live_capital = float(data['initial_live_capital'])

            logger.info("실전 투자 설정 업데이트 완료")

            return jsonify({
                'success': True,
                'message': '설정이 업데이트되었습니다',
                'config': {
                    'max_daily_loss_pct': config.max_daily_loss_pct,
                    'max_position_size_pct': config.max_position_size_pct,
                    'initial_live_capital': config.initial_live_capital
                }
            })

    except Exception as e:
        logger.error(f"실전 투자 설정 관리 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
