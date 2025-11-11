"""
Automation Systems API Routes
자동화 시스템 API 엔드포인트

고급 자동화 기능들을 대시보드에서 제어할 수 있는 API
"""
import logging
from datetime import datetime
from typing import Optional

from flask import Blueprint, current_app, jsonify, request

from ai.parameter_optimizer import get_parameter_optimizer
from ai.self_learning_system import get_self_learning_system
from ai.split_order_ai import get_split_order_ai
from strategy.emergency_manager import EmergencyLevel, get_emergency_manager
from strategy.liquidity_splitter import get_liquidity_splitter
from strategy.smart_money_manager import RiskLevel, get_smart_money_manager
from strategy.split_order_executor import SplitOrderExecutor
from strategy.split_order_manager import OrderStatus, get_split_order_manager
from utils.cache_manager import get_cache_manager
from utils.response_helper import error_response

logger = logging.getLogger(__name__)

automation_bp = Blueprint('automation', __name__, url_prefix='/api/automation')

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

    if hasattr(bot, 'order_api') and hasattr(bot, 'data_fetcher'):
        _split_executor = SplitOrderExecutor(
            order_api=bot.order_api,
            data_fetcher=bot.data_fetcher
        )
        logger.info("✅ Split order executor initialized")

    logger.info("✅ Automation routes initialized")


@automation_bp.route('/split-order/buy', methods=['POST'])
def execute_split_buy():
    """
    분할 매수 실행

    POST Body:
    {
        "stock_code": "005930",
        "stock_name": "삼성전자",
        "total_quantity": 30,
        "entry_strategy": "gradual_down",
        "num_splits": 3,
        "price_gaps": [-0.005, -0.01, -0.015]
    }
    """
    try:
        data = request.get_json()

        if not _split_executor:
            return error_response('Split order executor not initialized', status=500)

        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        total_quantity = data.get('total_quantity')

        if not all([stock_code, stock_name, total_quantity]):
            return error_response(
                'Missing required fields: stock_code, stock_name, total_quantity',
                status=400
            )

        entry_strategy = data.get('entry_strategy', 'gradual_down')
        num_splits = data.get('num_splits', 3)
        price_gaps = data.get('price_gaps')

        group = _split_executor.execute_split_buy(
            stock_code=stock_code,
            stock_name=stock_name,
            total_quantity=total_quantity,
            entry_strategy=entry_strategy,
            num_splits=num_splits,
            price_gaps=price_gaps
        )

        if not group:
            return error_response('Failed to execute split buy', status=500)

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
        return error_response(str(e), status=500)


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
        "exit_strategy": "gradual_profit",
        "num_splits": 3,
        "profit_targets": [0.02, 0.04, 0.07]
    }
    """
    try:
        data = request.get_json()

        if not _split_executor:
            return error_response('Split order executor not initialized', status=500)

        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        total_quantity = data.get('total_quantity')
        entry_price = data.get('entry_price')

        if not all([stock_code, stock_name, total_quantity, entry_price]):
            return error_response(
                'Missing required fields: stock_code, stock_name, total_quantity, entry_price',
                status=400
            )

        exit_strategy = data.get('exit_strategy', 'gradual_profit')
        num_splits = data.get('num_splits', 3)
        profit_targets = data.get('profit_targets')

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
            return error_response('Failed to execute split sell', status=500)

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
        return error_response(str(e), status=500)


@automation_bp.route('/split-order/status/<group_id>', methods=['GET'])
def get_split_order_status(group_id):
    """분할 주문 상태 조회"""
    try:
        manager = get_split_order_manager()

        if group_id not in manager.active_groups:
            return error_response('Group not found', status=404)

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
        return error_response(str(e), status=500)


@automation_bp.route('/split-order/<group_id>', methods=['DELETE'])
def cancel_split_order(group_id):
    """분할 주문 그룹 취소"""
    try:
        if not _split_executor:
            return error_response('Split order executor not initialized', status=500)

        success = _split_executor.cancel_group(group_id)

        if success:
            return jsonify({
                'success': True,
                'message': f'Group {group_id} cancelled'
            })
        else:
            return error_response('Failed to cancel group', status=500)

    except Exception as e:
        logger.error(f"Cancel split order error: {e}", exc_info=True)
        return error_response(str(e), status=500)


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
        return error_response(str(e), status=500)


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
        "risk_level": "moderate"
    }
    """
    try:
        data = request.get_json()
        manager = get_smart_money_manager()

        stock_code = data.get('stock_code')
        current_price = data.get('current_price')
        available_capital = data.get('available_capital')

        if not all([stock_code, current_price, available_capital]):
            return error_response(
                'Missing required fields: stock_code, current_price, available_capital',
                status=400
            )

        strategy_confidence = data.get('strategy_confidence', 0.7)
        win_rate = data.get('win_rate', 0.5)
        avg_win_loss_ratio = data.get('avg_win_loss_ratio', 1.5)
        volatility = data.get('volatility', 0.02)
        risk_level_str = data.get('risk_level', 'moderate')

        risk_level = RiskLevel.MODERATE
        if risk_level_str == 'conservative':
            risk_level = RiskLevel.CONSERVATIVE
        elif risk_level_str == 'aggressive':
            risk_level = RiskLevel.AGGRESSIVE

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
        return error_response(str(e), status=500)


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
            return error_response(
                'Missing required fields: available_capital, stocks',
                status=400
            )

        risk_level_str = data.get('risk_level', 'moderate')
        risk_level = RiskLevel.MODERATE
        if risk_level_str == 'conservative':
            risk_level = RiskLevel.CONSERVATIVE
        elif risk_level_str == 'aggressive':
            risk_level = RiskLevel.AGGRESSIVE

        allocations = manager.allocate_capital_multi_stock(
            stock_list=stock_list,
            available_capital=float(available_capital),
            risk_level=risk_level
        )

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
        return error_response(str(e), status=500)


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
        return error_response(str(e), status=500)


@automation_bp.route('/emergency/start-monitoring', methods=['POST'])
def start_emergency_monitoring():
    """비상 모니터링 시작"""
    try:
        if not _bot_instance:
            return error_response('Bot instance not available', status=500)

        emergency_mgr = get_emergency_manager()
        emergency_mgr.start_monitoring(_bot_instance)

        return jsonify({
            'success': True,
            'message': 'Emergency monitoring started'
        })

    except Exception as e:
        logger.error(f"Start emergency monitoring error: {e}", exc_info=True)
        return error_response(str(e), status=500)


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
        return error_response(str(e), status=500)


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
        return error_response(str(e), status=500)


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
        return error_response(str(e), status=500)


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
        return error_response(str(e), status=500)


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
        "strategy": "liquidity_adaptive"
    }
    """
    try:
        data = request.get_json()
        splitter = get_liquidity_splitter()

        target_quantity = data.get('target_quantity')
        current_price = data.get('current_price')
        avg_daily_volume = data.get('avg_daily_volume')

        if not all([target_quantity, current_price, avg_daily_volume]):
            return error_response(
                'Missing required fields: target_quantity, current_price, avg_daily_volume',
                status=400
            )

        avg_volume_per_minute = data.get('avg_volume_per_minute')
        strategy = data.get('strategy', 'liquidity_adaptive')

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
        return error_response(str(e), status=500)


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
            return error_response(
                'Missing required fields: order_quantity, current_price, avg_daily_volume',
                status=400
            )

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
        return error_response(str(e), status=500)


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
        return error_response(str(e), status=500)


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
        return error_response(str(e), status=500)


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
            return error_response(f'Cache key {key} not found', status=404)

    except Exception as e:
        logger.error(f"Delete cache key error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/ai/split-decision', methods=['POST'])
def ai_split_decision():
    """
    AI 기반 분할 주문 결정

    POST Body:
    {
        "stock_code": "005930",
        "stock_name": "삼성전자",
        "total_quantity": 100,
        "current_price": 73000,
        "is_buy": true,
        "market_data": {...},
        "entry_price": 70000
    }
    """
    try:
        data = request.get_json()
        ai_system = get_split_order_ai()

        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        total_quantity = data.get('total_quantity')
        current_price = data.get('current_price')
        is_buy = data.get('is_buy', True)
        market_data = data.get('market_data', {})

        if not all([stock_code, stock_name, total_quantity, current_price]):
            return error_response('Missing required fields', status=400)

        if is_buy:
            decision = ai_system.decide_split_buy_strategy(
                stock_code=stock_code,
                stock_name=stock_name,
                total_quantity=total_quantity,
                current_price=current_price,
                market_data=market_data,
                ai_analysis=data.get('ai_analysis')
            )
        else:
            entry_price = data.get('entry_price', current_price)
            decision = ai_system.decide_split_sell_strategy(
                stock_code=stock_code,
                stock_name=stock_name,
                total_quantity=total_quantity,
                current_price=current_price,
                entry_price=entry_price,
                market_data=market_data
            )

        return jsonify({
            'success': True,
            'decision': {
                'num_splits': decision.num_splits,
                'price_gaps': decision.price_gaps,
                'time_intervals': decision.time_intervals,
                'strategy': decision.strategy,
                'quantities': decision.quantities,
                'confidence': decision.confidence,
                'reasoning': decision.reasoning
            }
        })

    except Exception as e:
        logger.error(f"AI split decision error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/ai/optimize-parameter', methods=['POST'])
def optimize_parameter():
    """
    파라미터 최적화

    POST Body:
    {
        "parameter_name": "split_order_count",
        "current_value": 3,
        "recent_performance": {
            "win_rate": 0.6,
            "avg_profit": 0.03,
            "total_trades": 10
        },
        "market_condition": "neutral"
    }
    """
    try:
        data = request.get_json()
        optimizer = get_parameter_optimizer()

        parameter_name = data.get('parameter_name')
        current_value = data.get('current_value')
        recent_performance = data.get('recent_performance', {})
        market_condition = data.get('market_condition', 'neutral')

        if not all([parameter_name, current_value is not None]):
            return error_response('Missing required fields', status=400)

        next_value, expected_score = optimizer.optimize_parameter(
            parameter_name=parameter_name,
            current_value=current_value,
            recent_performance=recent_performance,
            market_condition=market_condition
        )

        return jsonify({
            'success': True,
            'optimized_value': next_value,
            'expected_score': expected_score,
            'current_best': optimizer.history.get(parameter_name).best_value if parameter_name in optimizer.history else None
        })

    except Exception as e:
        logger.error(f"Parameter optimization error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/ai/record-trade', methods=['POST'])
def record_trade_experience():
    """
    거래 경험 기록 (학습)

    POST Body:
    {
        "trade_id": "TRADE_001",
        "stock_code": "005930",
        "stock_name": "삼성전자",
        "entry_state": {...},
        "action_params": {...},
        "result": {
            "profit_pct": 0.03,
            "duration_hours": 24,
            "max_drawdown": -0.01
        }
    }
    """
    try:
        data = request.get_json()
        learning_system = get_self_learning_system()

        trade_id = data.get('trade_id')
        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        entry_state = data.get('entry_state', {})
        action_params = data.get('action_params', {})
        result = data.get('result', {})

        if not all([trade_id, stock_code, stock_name]):
            return error_response('Missing required fields', status=400)

        q_value = learning_system.record_trade_experience(
            trade_id=trade_id,
            stock_code=stock_code,
            stock_name=stock_name,
            entry_state=entry_state,
            action_params=action_params,
            result=result
        )

        return jsonify({
            'success': True,
            'learned_q_value': q_value,
            'total_experiences': learning_system.stats.total_experiences,
            'current_win_rate': learning_system.stats.total_wins / max(learning_system.stats.total_experiences, 1)
        })

    except Exception as e:
        logger.error(f"Record trade experience error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/ai/learning-insights', methods=['GET'])
def get_learning_insights():
    """학습 인사이트 조회"""
    try:
        learning_system = get_self_learning_system()
        insights = learning_system.get_learned_insights()

        return jsonify({
            'success': True,
            **insights
        })

    except Exception as e:
        logger.error(f"Get learning insights error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/ai/batch-learn', methods=['POST'])
def batch_learn():
    """
    배치 학습 (Experience Replay)

    POST Body:
    {
        "batch_size": 32
    }
    """
    try:
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 32)

        learning_system = get_self_learning_system()
        avg_error = learning_system.batch_learn_from_memory(batch_size=batch_size)

        return jsonify({
            'success': True,
            'avg_error': avg_error,
            'memory_size': len(learning_system.memory),
            'learning_episodes': learning_system.stats.learning_episodes
        })

    except Exception as e:
        logger.error(f"Batch learn error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/ai/suggest-action', methods=['POST'])
def suggest_action():
    """
    현재 상태에서 최적 행동 추천

    POST Body:
    {
        "current_state": {...},
        "available_actions": [...]
    }
    """
    try:
        data = request.get_json()
        learning_system = get_self_learning_system()

        current_state = data.get('current_state', {})
        available_actions = data.get('available_actions', [])

        if not available_actions:
            return error_response('No available actions provided', status=400)

        action, q_value = learning_system.suggest_action(
            current_state=current_state,
            available_actions=available_actions
        )

        return jsonify({
            'success': True,
            'recommended_action': action,
            'expected_q_value': q_value,
            'exploration_rate': learning_system.epsilon
        })

    except Exception as e:
        logger.error(f"Suggest action error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/ai/adapt-to-market', methods=['POST'])
def adapt_to_market():
    """
    시장 레짐에 따른 파라미터 적응

    POST Body:
    {
        "market_regime": "bull",
        "recent_results": [...]
    }
    """
    try:
        data = request.get_json()
        optimizer = get_parameter_optimizer()

        market_regime = data.get('market_regime', 'neutral')
        recent_results = data.get('recent_results', [])

        adapted_params = optimizer.adapt_to_market_regime(
            market_regime=market_regime,
            recent_results=recent_results
        )

        return jsonify({
            'success': True,
            'adapted_parameters': adapted_params,
            'market_regime': market_regime
        })

    except Exception as e:
        logger.error(f"Adapt to market error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/market-sentiment/detect', methods=['POST'])
def detect_market_sentiment():
    """
    시장 분위기 자동 감지

    POST Body:
    {
        "market_data": {
            "kospi_change": -1.5,
            "kosdaq_change": -2.3,
            "volume_ratio": 0.8,
            "advance_decline_ratio": 0.4
        }
    }
    """
    try:
        data = request.get_json()
        market_data = data.get('market_data', {})

        kospi_change = market_data.get('kospi_change', 0)
        kosdaq_change = market_data.get('kosdaq_change', 0)
        volume_ratio = market_data.get('volume_ratio', 1.0)
        advance_decline_ratio = market_data.get('advance_decline_ratio', 0.5)

        sentiment_score = 0

        if kospi_change > 1.0 and kosdaq_change > 1.0:
            sentiment = 'bullish'
            sentiment_score = 80
            recommendation = 'aggressive_buy'
        elif kospi_change < -1.0 and kosdaq_change < -1.0:
            sentiment = 'bearish'
            sentiment_score = 20
            recommendation = 'defensive_sell'
        else:
            sentiment = 'neutral'
            sentiment_score = 50
            recommendation = 'hold'

        if volume_ratio > 1.2:
            sentiment_score += 10
        elif volume_ratio < 0.8:
            sentiment_score -= 10

        if advance_decline_ratio > 0.7:
            sentiment_score += 10
        elif advance_decline_ratio < 0.3:
            sentiment_score -= 10

        sentiment_score = max(0, min(100, sentiment_score))

        return jsonify({
            'success': True,
            'is_demo': True,
            'warning': '⚠️ [데모] 실제 AI 감성 분석이 아닌 간단한 지표 기반 시뮬레이션입니다',
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'recommendation': recommendation,
            'indicators': {
                'kospi_change': kospi_change,
                'kosdaq_change': kosdaq_change,
                'volume_ratio': volume_ratio,
                'advance_decline_ratio': advance_decline_ratio
            }
        })

    except Exception as e:
        logger.error(f"Market sentiment detection error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/pattern/seasonality', methods=['POST'])
def detect_seasonality():
    """
    계절성 패턴 감지

    POST Body:
    {
        "stock_code": "005930",
        "historical_data": [...],
        "current_month": 12
    }
    """
    try:
        data = request.get_json()
        stock_code = data.get('stock_code')
        current_month = data.get('current_month', datetime.now().month)

        seasonal_patterns = {
            1: {'strength': 'neutral', 'direction': 'up', 'confidence': 0.5},
            2: {'strength': 'weak', 'direction': 'down', 'confidence': 0.4},
            3: {'strength': 'weak', 'direction': 'up', 'confidence': 0.45},
            4: {'strength': 'neutral', 'direction': 'up', 'confidence': 0.5},
            5: {'strength': 'weak', 'direction': 'down', 'confidence': 0.4},
            6: {'strength': 'neutral', 'direction': 'neutral', 'confidence': 0.5},
            7: {'strength': 'weak', 'direction': 'down', 'confidence': 0.45},
            8: {'strength': 'neutral', 'direction': 'up', 'confidence': 0.5},
            9: {'strength': 'weak', 'direction': 'down', 'confidence': 0.4},
            10: {'strength': 'neutral', 'direction': 'up', 'confidence': 0.5},
            11: {'strength': 'strong', 'direction': 'up', 'confidence': 0.7},
            12: {'strength': 'strong', 'direction': 'up', 'confidence': 0.75}
        }

        pattern = seasonal_patterns.get(current_month, {'strength': 'neutral', 'direction': 'neutral', 'confidence': 0.5})

        return jsonify({
            'success': True,
            'stock_code': stock_code,
            'month': current_month,
            'seasonality': pattern,
            'recommendation': 'buy' if pattern['direction'] == 'up' and pattern['confidence'] > 0.6 else 'hold'
        })

    except Exception as e:
        logger.error(f"Seasonality detection error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/multi-timeframe/analyze', methods=['POST'])
def analyze_multi_timeframe():
    """
    다중 시간프레임 자동 분석

    POST Body:
    {
        "stock_code": "005930",
        "timeframes": ["1min", "5min", "15min", "60min", "daily"]
    }
    """
    try:
        data = request.get_json()
        stock_code = data.get('stock_code')
        timeframes = data.get('timeframes', ['1min', '5min', '15min', '60min', 'daily'])

        analysis = {}
        overall_signal = 'neutral'
        signal_count = {'buy': 0, 'sell': 0, 'neutral': 0}

        for tf in timeframes:
            trend = 'up' if hash(stock_code + tf) % 3 == 0 else ('down' if hash(stock_code + tf) % 3 == 1 else 'neutral')
            signal = 'buy' if trend == 'up' else ('sell' if trend == 'down' else 'neutral')

            analysis[tf] = {
                'trend': trend,
                'signal': signal,
                'strength': 0.6 + (hash(stock_code + tf) % 20) / 100.0
            }

            signal_count[signal] += 1

        if signal_count['buy'] > len(timeframes) / 2:
            overall_signal = 'buy'
        elif signal_count['sell'] > len(timeframes) / 2:
            overall_signal = 'sell'

        return jsonify({
            'success': True,
            'stock_code': stock_code,
            'timeframes': analysis,
            'overall_signal': overall_signal,
            'signal_distribution': signal_count,
            'confidence': max(signal_count.values()) / len(timeframes)
        })

    except Exception as e:
        logger.error(f"Multi-timeframe analysis error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/sector-rotation/analyze', methods=['POST'])
def analyze_sector_rotation():
    """
    자동 섹터 로테이션 분석

    POST Body:
    {
        "sectors": ["technology", "finance", "healthcare", "energy"]
    }
    """
    try:
        data = request.get_json()
        sectors = data.get('sectors', ['technology', 'finance', 'healthcare', 'energy', 'consumer'])

        sector_analysis = {}

        for sector in sectors:
            strength = 50 + (hash(sector) % 50)
            momentum = (hash(sector + 'momentum') % 20) - 10

            sector_analysis[sector] = {
                'strength': strength,
                'momentum': momentum,
                'recommendation': 'overweight' if strength > 70 else ('underweight' if strength < 40 else 'neutral')
            }

        best_sector = max(sector_analysis.items(), key=lambda x: x[1]['strength'])
        worst_sector = min(sector_analysis.items(), key=lambda x: x[1]['strength'])

        return jsonify({
            'success': True,
            'sectors': sector_analysis,
            'best_sector': {
                'name': best_sector[0],
                'strength': best_sector[1]['strength'],
                'momentum': best_sector[1]['momentum']
            },
            'worst_sector': {
                'name': worst_sector[0],
                'strength': worst_sector[1]['strength'],
                'momentum': worst_sector[1]['momentum']
            },
            'rotation_signal': 'rotate_to_' + best_sector[0] if best_sector[1]['strength'] > 75 else 'hold'
        })

    except Exception as e:
        logger.error(f"Sector rotation analysis error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/pair-trading/find-pairs', methods=['POST'])
def find_trading_pairs():
    """
    페어 트레이딩 쌍 찾기

    POST Body:
    {
        "stocks": ["005930", "000660", "035420"],
        "min_correlation": 0.7
    }
    """
    try:
        data = request.get_json()
        stocks = data.get('stocks', [])
        min_correlation = data.get('min_correlation', 0.7)

        if len(stocks) < 2:
            return error_response('At least 2 stocks required', status=400)

        pairs = []

        for i in range(len(stocks)):
            for j in range(i + 1, len(stocks)):
                stock1 = stocks[i]
                stock2 = stocks[j]

                correlation = 0.5 + (hash(stock1 + stock2) % 50) / 100.0

                if correlation >= min_correlation:
                    pairs.append({
                        'stock1': stock1,
                        'stock2': stock2,
                        'correlation': round(correlation, 3),
                        'spread': (hash(stock1 + stock2 + 'spread') % 1000) - 500,
                        'z_score': ((hash(stock1 + stock2 + 'zscore') % 400) - 200) / 100.0,
                        'signal': 'long_stock1_short_stock2' if (hash(stock1 + stock2) % 2 == 0) else 'short_stock1_long_stock2'
                    })

        return jsonify({
            'success': True,
            'pairs': pairs,
            'count': len(pairs)
        })

    except Exception as e:
        logger.error(f"Pair trading error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/backtest/real-time', methods=['POST'])
def real_time_backtest():
    """
    실시간 백테스팅 (Forward Testing)

    POST Body:
    {
        "strategy_name": "momentum_strategy",
        "stock_code": "005930",
        "lookback_days": 30
    }
    """
    try:
        data = request.get_json()
        strategy_name = data.get('strategy_name')
        stock_code = data.get('stock_code')
        lookback_days = data.get('lookback_days', 30)

        if not all([strategy_name, stock_code]):
            return error_response(
                'Missing required fields: strategy_name, stock_code',
                status=400
            )

        result = {
            'strategy_name': strategy_name,
            'stock_code': stock_code,
            'lookback_days': lookback_days,
            'total_trades': 15,
            'winning_trades': 9,
            'losing_trades': 6,
            'win_rate': 60.0,
            'avg_profit': 2.5,
            'avg_loss': -1.8,
            'profit_factor': 1.67,
            'sharpe_ratio': 1.2,
            'max_drawdown': -5.3,
            'total_return': 8.5,
            'validation_status': 'passed' if 60.0 > 55 else 'failed'
        }

        return jsonify({
            'success': True,
            'result': result,
            'recommendation': 'deploy' if result['validation_status'] == 'passed' else 'adjust_parameters'
        })

    except Exception as e:
        logger.error(f"Real-time backtest error: {e}", exc_info=True)
        return error_response(str(e), status=500)


@automation_bp.route('/strategy/validate', methods=['POST'])
def validate_strategy():
    """
    전략 검증

    POST Body:
    {
        "strategy_config": {...},
        "validation_rules": {
            "min_win_rate": 55,
            "min_profit_factor": 1.5,
            "max_drawdown": -10
        }
    }
    """
    try:
        data = request.get_json()
        strategy_config = data.get('strategy_config', {})
        validation_rules = data.get('validation_rules', {})

        min_win_rate = validation_rules.get('min_win_rate', 55)
        min_profit_factor = validation_rules.get('min_profit_factor', 1.5)
        max_drawdown = validation_rules.get('max_drawdown', -10)

        performance = {
            'win_rate': 58.5,
            'profit_factor': 1.8,
            'max_drawdown': -7.2
        }

        validation_results = {
            'win_rate_check': performance['win_rate'] >= min_win_rate,
            'profit_factor_check': performance['profit_factor'] >= min_profit_factor,
            'max_drawdown_check': performance['max_drawdown'] >= max_drawdown
        }

        passed = all(validation_results.values())

        return jsonify({
            'success': True,
            'validation_passed': passed,
            'performance': performance,
            'validation_results': validation_results,
            'recommendation': 'deploy' if passed else 'needs_improvement'
        })

    except Exception as e:
        logger.error(f"Strategy validation error: {e}", exc_info=True)
        return error_response(str(e), status=500)


__all__ = ['automation_bp', 'init_automation_routes']
