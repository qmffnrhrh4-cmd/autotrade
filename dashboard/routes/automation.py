"""
Automation Systems API Routes
자동화 시스템 API 엔드포인트

고급 자동화 기능들을 대시보드에서 제어할 수 있는 API
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from typing import Optional

# Import automation systems
from strategy.split_order_executor import SplitOrderExecutor
from strategy.split_order_manager import get_split_order_manager, OrderStatus
from strategy.smart_money_manager import get_smart_money_manager, RiskLevel
from strategy.emergency_manager import get_emergency_manager, EmergencyLevel
from strategy.liquidity_splitter import get_liquidity_splitter
from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

# Blueprint
automation_bp = Blueprint('automation', __name__, url_prefix='/api/automation')

# Global instances
_split_executor: Optional[SplitOrderExecutor] = None
_bot_instance = None


def init_automation_routes(bot):
    """
    자동화 라우트 초기화

    Args:
        bot: TradingBot 인스턴스
    """
    global _split_executor, _bot_instance

    _bot_instance = bot

    # Split order executor 초기화
    if hasattr(bot, 'order_api') and hasattr(bot, 'data_fetcher'):
        _split_executor = SplitOrderExecutor(
            order_api=bot.order_api,
            data_fetcher=bot.data_fetcher
        )
        logger.info("✅ Split order executor initialized")

    logger.info("✅ Automation routes initialized")


# ============================================================
# Split Order Endpoints
# ============================================================

@automation_bp.route('/split-order/buy', methods=['POST'])
def execute_split_buy():
    """
    분할 매수 실행

    POST Body:
    {
        "stock_code": "005930",
        "stock_name": "삼성전자",
        "total_quantity": 30,
        "entry_strategy": "gradual_down",  # gradual_down, immediate, support_levels
        "num_splits": 3,
        "price_gaps": [-0.005, -0.01, -0.015]  # Optional
    }
    """
    try:
        data = request.get_json()

        if not _split_executor:
            return jsonify({
                'success': False,
                'message': 'Split order executor not initialized'
            }), 500

        # Required fields
        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        total_quantity = data.get('total_quantity')

        if not all([stock_code, stock_name, total_quantity]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields: stock_code, stock_name, total_quantity'
            }), 400

        # Optional fields
        entry_strategy = data.get('entry_strategy', 'gradual_down')
        num_splits = data.get('num_splits', 3)
        price_gaps = data.get('price_gaps')

        # Execute split buy
        group = _split_executor.execute_split_buy(
            stock_code=stock_code,
            stock_name=stock_name,
            total_quantity=total_quantity,
            entry_strategy=entry_strategy,
            num_splits=num_splits,
            price_gaps=price_gaps
        )

        if not group:
            return jsonify({
                'success': False,
                'message': 'Failed to execute split buy'
            }), 500

        return jsonify({
            'success': True,
            'group_id': group.group_id,
            'stock_code': group.stock_code,
            'stock_name': group.stock_name,
            'total_quantity': group.total_quantity,
            'num_splits': len(group.entries),
            'entries': [
                {
                    'entry_id': entry.entry_id,
                    'order_number': entry.order_number or 0,
                    'quantity': entry.quantity,
                    'price': entry.price,
                    'status': entry.status.value
                }
                for entry in group.entries
            ]
        })

    except Exception as e:
        logger.error(f"Split buy error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/split-order/sell', methods=['POST'])
def execute_split_sell():
    """
    분할 매도 실행

    POST Body:
    {
        "stock_code": "005930",
        "stock_name": "삼성전자",
        "total_quantity": 30,
        "entry_price": 73000,
        "exit_strategy": "gradual_profit",  # gradual_profit, quick_exit, trailing
        "num_splits": 3,
        "profit_targets": [0.02, 0.04, 0.07]  # Optional
    }
    """
    try:
        data = request.get_json()

        if not _split_executor:
            return jsonify({
                'success': False,
                'message': 'Split order executor not initialized'
            }), 500

        # Required fields
        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        total_quantity = data.get('total_quantity')
        entry_price = data.get('entry_price')

        if not all([stock_code, stock_name, total_quantity, entry_price]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields: stock_code, stock_name, total_quantity, entry_price'
            }), 400

        # Optional fields
        exit_strategy = data.get('exit_strategy', 'gradual_profit')
        num_splits = data.get('num_splits', 3)
        profit_targets = data.get('profit_targets')

        # Execute split sell
        group = _split_executor.execute_split_sell(
            stock_code=stock_code,
            stock_name=stock_name,
            total_quantity=total_quantity,
            entry_price=float(entry_price),
            exit_strategy=exit_strategy,
            num_splits=num_splits,
            profit_targets=profit_targets
        )

        if not group:
            return jsonify({
                'success': False,
                'message': 'Failed to execute split sell'
            }), 500

        return jsonify({
            'success': True,
            'group_id': group.group_id,
            'stock_code': group.stock_code,
            'stock_name': group.stock_name,
            'total_quantity': group.total_quantity,
            'num_splits': len(group.entries),
            'entries': [
                {
                    'entry_id': entry.entry_id,
                    'order_number': entry.order_number or 0,
                    'quantity': entry.quantity,
                    'price': entry.price,
                    'status': entry.status.value
                }
                for entry in group.entries
            ]
        })

    except Exception as e:
        logger.error(f"Split sell error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/split-order/status/<group_id>', methods=['GET'])
def get_split_order_status(group_id):
    """분할 주문 상태 조회"""
    try:
        manager = get_split_order_manager()

        if group_id not in manager.active_groups:
            return jsonify({
                'success': False,
                'message': 'Group not found'
            }), 404

        group = manager.active_groups[group_id]

        return jsonify({
            'success': True,
            'group_id': group.group_id,
            'stock_code': group.stock_code,
            'stock_name': group.stock_name,
            'split_type': group.split_type.value,
            'total_quantity': group.total_quantity,
            'filled_quantity': group.get_filled_quantity(),
            'average_price': group.get_average_price(),
            'completion_ratio': group.get_completion_ratio(),
            'is_completed': group.is_completed(),
            'entries': [
                {
                    'entry_id': entry.entry_id,
                    'order_number': entry.order_number or 0,
                    'quantity': entry.quantity,
                    'price': entry.price,
                    'filled_quantity': entry.filled_quantity,
                    'filled_price': entry.filled_price,
                    'status': entry.status.value
                }
                for entry in group.entries
            ]
        })

    except Exception as e:
        logger.error(f"Get split order status error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/split-order/<group_id>', methods=['DELETE'])
def cancel_split_order(group_id):
    """분할 주문 그룹 취소"""
    try:
        if not _split_executor:
            return jsonify({
                'success': False,
                'message': 'Split order executor not initialized'
            }), 500

        success = _split_executor.cancel_group(group_id)

        if success:
            return jsonify({
                'success': True,
                'message': f'Group {group_id} cancelled'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to cancel group'
            }), 500

    except Exception as e:
        logger.error(f"Cancel split order error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/split-order/active', methods=['GET'])
def get_active_split_orders():
    """활성 분할 주문 목록 조회"""
    try:
        manager = get_split_order_manager()

        active_groups = []
        for group_id, group in manager.active_groups.items():
            active_groups.append({
                'group_id': group.group_id,
                'stock_code': group.stock_code,
                'stock_name': group.stock_name,
                'split_type': group.split_type.value,
                'total_quantity': group.total_quantity,
                'filled_quantity': group.get_filled_quantity(),
                'completion_ratio': group.get_completion_ratio(),
                'is_completed': group.is_completed(),
                'created_at': group.created_at.isoformat()
            })

        return jsonify({
            'success': True,
            'count': len(active_groups),
            'groups': active_groups
        })

    except Exception as e:
        logger.error(f"Get active split orders error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================================
# Smart Money Manager Endpoints
# ============================================================

@automation_bp.route('/money-manager/calculate-position', methods=['POST'])
def calculate_position_size():
    """
    포지션 사이즈 계산

    POST Body:
    {
        "stock_code": "005930",
        "current_price": 73000,
        "available_capital": 10000000,
        "strategy_confidence": 0.8,
        "win_rate": 0.6,
        "avg_win_loss_ratio": 1.5,
        "volatility": 0.025,
        "risk_level": "moderate"  # conservative, moderate, aggressive
    }
    """
    try:
        data = request.get_json()
        manager = get_smart_money_manager()

        # Required fields
        stock_code = data.get('stock_code')
        current_price = data.get('current_price')
        available_capital = data.get('available_capital')

        if not all([stock_code, current_price, available_capital]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields: stock_code, current_price, available_capital'
            }), 400

        # Optional fields with defaults
        strategy_confidence = data.get('strategy_confidence', 0.7)
        win_rate = data.get('win_rate', 0.5)
        avg_win_loss_ratio = data.get('avg_win_loss_ratio', 1.5)
        volatility = data.get('volatility', 0.02)
        risk_level_str = data.get('risk_level', 'moderate')

        # Convert risk level string to enum
        risk_level = RiskLevel.MODERATE
        if risk_level_str == 'conservative':
            risk_level = RiskLevel.CONSERVATIVE
        elif risk_level_str == 'aggressive':
            risk_level = RiskLevel.AGGRESSIVE

        # Calculate position size
        position = manager.calculate_position_size(
            stock_code=stock_code,
            current_price=float(current_price),
            available_capital=float(available_capital),
            strategy_confidence=float(strategy_confidence),
            win_rate=float(win_rate),
            avg_win_loss_ratio=float(avg_win_loss_ratio),
            volatility=float(volatility),
            risk_level=risk_level
        )

        return jsonify({
            'success': True,
            'stock_code': position.stock_code,
            'recommended_quantity': position.recommended_quantity,
            'recommended_amount': position.recommended_amount,
            'position_ratio': position.position_ratio,
            'risk_amount': position.risk_amount,
            'confidence_level': position.confidence_level,
            'reasoning': position.reasoning
        })

    except Exception as e:
        logger.error(f"Calculate position size error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/money-manager/allocate-multi', methods=['POST'])
def allocate_capital_multi_stock():
    """
    여러 종목에 자본 배분

    POST Body:
    {
        "available_capital": 10000000,
        "risk_level": "moderate",
        "stocks": [
            {
                "stock_code": "005930",
                "current_price": 73000,
                "confidence": 0.8,
                "win_rate": 0.6,
                "volatility": 0.025
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        manager = get_smart_money_manager()

        available_capital = data.get('available_capital')
        stock_list = data.get('stocks', [])

        if not available_capital or not stock_list:
            return jsonify({
                'success': False,
                'message': 'Missing required fields: available_capital, stocks'
            }), 400

        risk_level_str = data.get('risk_level', 'moderate')
        risk_level = RiskLevel.MODERATE
        if risk_level_str == 'conservative':
            risk_level = RiskLevel.CONSERVATIVE
        elif risk_level_str == 'aggressive':
            risk_level = RiskLevel.AGGRESSIVE

        # Allocate capital
        allocations = manager.allocate_capital_multi_stock(
            stock_list=stock_list,
            available_capital=float(available_capital),
            risk_level=risk_level
        )

        # Format response
        results = []
        for stock_code, position in allocations.items():
            results.append({
                'stock_code': position.stock_code,
                'recommended_quantity': position.recommended_quantity,
                'recommended_amount': position.recommended_amount,
                'position_ratio': position.position_ratio,
                'risk_amount': position.risk_amount,
                'confidence_level': position.confidence_level,
                'reasoning': position.reasoning
            })

        return jsonify({
            'success': True,
            'allocations': results
        })

    except Exception as e:
        logger.error(f"Allocate capital error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/money-manager/should-reduce', methods=['POST'])
def check_should_reduce_position():
    """
    포지션 축소 필요 여부 확인

    POST Body:
    {
        "current_loss_pct": 7.5,
        "max_drawdown_pct": 12.3,
        "consecutive_losses": 3
    }
    """
    try:
        data = request.get_json()
        manager = get_smart_money_manager()

        current_loss_pct = data.get('current_loss_pct', 0)
        max_drawdown_pct = data.get('max_drawdown_pct', 0)
        consecutive_losses = data.get('consecutive_losses', 0)

        should_reduce, reduction_ratio = manager.should_reduce_position(
            current_loss_pct=float(current_loss_pct),
            max_drawdown_pct=float(max_drawdown_pct),
            consecutive_losses=int(consecutive_losses)
        )

        return jsonify({
            'success': True,
            'should_reduce': should_reduce,
            'reduction_ratio': reduction_ratio,
            'reduction_pct': (1 - reduction_ratio) * 100
        })

    except Exception as e:
        logger.error(f"Should reduce position error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================================
# Emergency Manager Endpoints
# ============================================================

@automation_bp.route('/emergency/start-monitoring', methods=['POST'])
def start_emergency_monitoring():
    """비상 모니터링 시작"""
    try:
        if not _bot_instance:
            return jsonify({
                'success': False,
                'message': 'Bot instance not available'
            }), 500

        emergency_mgr = get_emergency_manager()
        emergency_mgr.start_monitoring(_bot_instance)

        return jsonify({
            'success': True,
            'message': 'Emergency monitoring started'
        })

    except Exception as e:
        logger.error(f"Start emergency monitoring error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/emergency/stop-monitoring', methods=['POST'])
def stop_emergency_monitoring():
    """비상 모니터링 중지"""
    try:
        emergency_mgr = get_emergency_manager()
        emergency_mgr.stop_monitoring()

        return jsonify({
            'success': True,
            'message': 'Emergency monitoring stopped'
        })

    except Exception as e:
        logger.error(f"Stop emergency monitoring error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/emergency/status', methods=['GET'])
def get_emergency_status():
    """비상 시스템 상태 조회"""
    try:
        emergency_mgr = get_emergency_manager()

        return jsonify({
            'success': True,
            'is_monitoring': emergency_mgr.is_monitoring,
            'circuit_breaker_active': emergency_mgr.circuit_breaker_active,
            'enabled': emergency_mgr.enabled,
            'circuit_breaker_enabled': emergency_mgr.circuit_breaker_enabled,
            'emergency_stop_loss_pct': emergency_mgr.emergency_stop_loss_pct
        })

    except Exception as e:
        logger.error(f"Get emergency status error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/emergency/events', methods=['GET'])
def get_emergency_events():
    """최근 비상 이벤트 조회"""
    try:
        hours = request.args.get('hours', default=24, type=int)
        emergency_mgr = get_emergency_manager()

        events = emergency_mgr.get_recent_events(hours=hours)

        return jsonify({
            'success': True,
            'count': len(events),
            'events': [
                {
                    'event_type': event.event_type.value,
                    'level': event.level.value,
                    'timestamp': event.timestamp.isoformat(),
                    'description': event.description,
                    'data': event.data,
                    'action_taken': event.action_taken
                }
                for event in events
            ]
        })

    except Exception as e:
        logger.error(f"Get emergency events error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/emergency/circuit-breaker', methods=['POST'])
def activate_circuit_breaker():
    """
    서킷 브레이커 수동 활성화

    POST Body:
    {
        "duration_minutes": 30
    }
    """
    try:
        data = request.get_json() or {}
        duration_minutes = data.get('duration_minutes', 30)

        emergency_mgr = get_emergency_manager()
        emergency_mgr.activate_circuit_breaker(duration_minutes=int(duration_minutes))

        return jsonify({
            'success': True,
            'message': f'Circuit breaker activated for {duration_minutes} minutes'
        })

    except Exception as e:
        logger.error(f"Activate circuit breaker error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================================
# Liquidity Splitter Endpoints
# ============================================================

@automation_bp.route('/liquidity/calculate-splits', methods=['POST'])
def calculate_liquidity_splits():
    """
    유동성 기반 주문 분할 계산

    POST Body:
    {
        "target_quantity": 1000,
        "current_price": 73000,
        "avg_daily_volume": 50000000,
        "avg_volume_per_minute": 138888,
        "strategy": "liquidity_adaptive"  # liquidity_adaptive, twap, vwap, iceberg
    }
    """
    try:
        data = request.get_json()
        splitter = get_liquidity_splitter()

        target_quantity = data.get('target_quantity')
        current_price = data.get('current_price')
        avg_daily_volume = data.get('avg_daily_volume')

        if not all([target_quantity, current_price, avg_daily_volume]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields: target_quantity, current_price, avg_daily_volume'
            }), 400

        avg_volume_per_minute = data.get('avg_volume_per_minute')
        strategy = data.get('strategy', 'liquidity_adaptive')

        # Calculate split orders
        split_orders = splitter.calculate_split_orders(
            target_quantity=int(target_quantity),
            current_price=float(current_price),
            avg_daily_volume=int(avg_daily_volume),
            avg_volume_per_minute=int(avg_volume_per_minute) if avg_volume_per_minute else None,
            strategy=strategy
        )

        return jsonify({
            'success': True,
            'num_splits': len(split_orders),
            'splits': [
                {
                    'order_number': order.order_number,
                    'quantity': order.quantity,
                    'estimated_price': order.estimated_price,
                    'delay_seconds': order.delay_seconds
                }
                for order in split_orders
            ]
        })

    except Exception as e:
        logger.error(f"Calculate liquidity splits error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/liquidity/estimate-impact', methods=['POST'])
def estimate_market_impact():
    """
    시장 충격 추정

    POST Body:
    {
        "order_quantity": 1000,
        "current_price": 73000,
        "avg_daily_volume": 50000000
    }
    """
    try:
        data = request.get_json()
        splitter = get_liquidity_splitter()

        order_quantity = data.get('order_quantity')
        current_price = data.get('current_price')
        avg_daily_volume = data.get('avg_daily_volume')

        if not all([order_quantity, current_price, avg_daily_volume]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields: order_quantity, current_price, avg_daily_volume'
            }), 400

        # Estimate impact
        impact = splitter.estimate_market_impact(
            order_quantity=int(order_quantity),
            current_price=float(current_price),
            avg_daily_volume=int(avg_daily_volume)
        )

        return jsonify({
            'success': True,
            **impact
        })

    except Exception as e:
        logger.error(f"Estimate market impact error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================================
# Cache Manager Endpoints
# ============================================================

@automation_bp.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    """캐시 통계 조회"""
    try:
        cache_mgr = get_cache_manager()
        stats = cache_mgr.get_stats()

        return jsonify({
            'success': True,
            **stats
        })

    except Exception as e:
        logger.error(f"Get cache stats error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """전체 캐시 삭제"""
    try:
        cache_mgr = get_cache_manager()
        cache_mgr.clear()

        return jsonify({
            'success': True,
            'message': 'Cache cleared'
        })

    except Exception as e:
        logger.error(f"Clear cache error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@automation_bp.route('/cache/<key>', methods=['DELETE'])
def delete_cache_key(key):
    """특정 캐시 키 삭제"""
    try:
        cache_mgr = get_cache_manager()
        success = cache_mgr.delete(key)

        if success:
            return jsonify({
                'success': True,
                'message': f'Cache key {key} deleted'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Cache key {key} not found'
            }), 404

    except Exception as e:
        logger.error(f"Delete cache key error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


__all__ = ['automation_bp', 'init_automation_routes']
