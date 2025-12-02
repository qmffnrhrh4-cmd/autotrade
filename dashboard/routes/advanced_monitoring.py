"""
dashboard/routes/advanced_monitoring.py
고급 모니터링 및 분석 API

새로 추가된 기능들의 대시보드 API 엔드포인트:
- 리스크 관리
- 성능 분석
- 긴급 정지 제어
- A/B 테스트 현황
- 실시간 이벤트
"""
from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('advanced_monitoring', __name__, url_prefix='/api/advanced')


# === 리스크 관리 API ===

@bp.route('/risk/status', methods=['GET'])
def get_risk_status():
    """리스크 상태 조회"""
    try:
        from core.risk_validation_pipeline import get_risk_pipeline

        pipeline = get_risk_pipeline()
        summary = pipeline.get_validation_summary()
        daily_stats = pipeline.get_daily_stats()

        return jsonify({
            'success': True,
            'data': {
                'validation_summary': summary,
                'daily_stats': daily_stats,
                'emergency_stop': pipeline.emergency_stop,
                'emergency_reason': pipeline.emergency_reason
            }
        })
    except Exception as e:
        logger.error(f"리스크 상태 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/risk/limits', methods=['GET'])
def get_risk_limits():
    """리스크 한도 조회"""
    try:
        from core.risk_validation_pipeline import get_risk_pipeline

        pipeline = get_risk_pipeline()
        return jsonify({
            'success': True,
            'data': pipeline.limits
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/risk/limits', methods=['POST'])
def update_risk_limits():
    """리스크 한도 업데이트"""
    try:
        from core.risk_validation_pipeline import get_risk_pipeline

        data = request.get_json()
        pipeline = get_risk_pipeline()

        for key, value in data.items():
            if key in pipeline.limits:
                pipeline.limits[key] = value

        return jsonify({
            'success': True,
            'message': '리스크 한도가 업데이트되었습니다',
            'data': pipeline.limits
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/risk/validation-history', methods=['GET'])
def get_validation_history():
    """검증 히스토리 조회"""
    try:
        from core.risk_validation_pipeline import get_risk_pipeline
        from dataclasses import asdict

        pipeline = get_risk_pipeline()
        limit = request.args.get('limit', 50, type=int)

        history = []
        for report in pipeline.validation_history[-limit:]:
            report_dict = {
                'order_id': report.order_id,
                'timestamp': report.timestamp,
                'stock_code': report.stock_code,
                'stock_name': report.stock_name,
                'order_type': report.order_type,
                'requested_quantity': report.requested_quantity,
                'final_quantity': report.final_quantity,
                'result': report.final_result.value,
                'risk_level': report.overall_risk_level.value,
                'rejection_reasons': report.rejection_reasons,
                'warnings': report.warnings
            }
            history.append(report_dict)

        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 포트폴리오 리스크 API ===

@bp.route('/portfolio-risk/report', methods=['GET'])
def get_portfolio_risk_report():
    """포트폴리오 리스크 보고서 조회"""
    try:
        from core.portfolio_risk_manager import get_portfolio_risk_manager
        from dataclasses import asdict

        manager = get_portfolio_risk_manager()

        # 최근 보고서
        if manager.report_history:
            report = manager.report_history[-1]
            return jsonify({
                'success': True,
                'data': {
                    'timestamp': report.timestamp,
                    'total_value': report.total_value,
                    'cash': report.cash,
                    'invested': report.invested,
                    'portfolio_var_95': report.portfolio_var_95,
                    'portfolio_var_99': report.portfolio_var_99,
                    'portfolio_volatility': report.portfolio_volatility,
                    'sharpe_ratio': report.sharpe_ratio,
                    'sector_exposure': report.sector_exposure,
                    'max_sector_weight': report.max_sector_weight,
                    'warnings': report.warnings,
                    'recommendations': report.recommendations
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': None,
                'message': '보고서 없음'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 성능 분석 API ===

@bp.route('/performance/summary', methods=['GET'])
def get_performance_summary():
    """성능 요약 조회"""
    try:
        from core.performance_analyzer import get_performance_analyzer

        analyzer = get_performance_analyzer()
        summary = analyzer.get_summary()

        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/performance/strategy-comparison', methods=['GET'])
def get_strategy_comparison():
    """전략별 성과 비교"""
    try:
        from core.performance_analyzer import get_performance_analyzer

        analyzer = get_performance_analyzer()
        comparison = analyzer.get_strategy_comparison()

        return jsonify({
            'success': True,
            'data': comparison
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/performance/stock-ranking', methods=['GET'])
def get_stock_ranking():
    """종목별 순위"""
    try:
        from core.performance_analyzer import get_performance_analyzer

        analyzer = get_performance_analyzer()
        top_n = request.args.get('top', 10, type=int)
        top, worst = analyzer.get_stock_ranking(top_n)

        return jsonify({
            'success': True,
            'data': {
                'top_performers': top,
                'worst_performers': worst
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/performance/attribution', methods=['GET'])
def get_attribution_analysis():
    """귀인 분석"""
    try:
        from core.performance_analyzer import get_performance_analyzer

        analyzer = get_performance_analyzer()
        analysis = analyzer.get_attribution_analysis()

        return jsonify({
            'success': True,
            'data': analysis
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/performance/monthly-report', methods=['GET'])
def get_monthly_report():
    """월간 보고서"""
    try:
        from core.performance_analyzer import get_performance_analyzer
        from dataclasses import asdict
        from datetime import datetime

        analyzer = get_performance_analyzer()

        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', datetime.now().month, type=int)

        report = analyzer.generate_monthly_report(year, month)

        if report:
            return jsonify({
                'success': True,
                'data': asdict(report)
            })
        else:
            return jsonify({
                'success': True,
                'data': None,
                'message': f'{year}년 {month}월 데이터 없음'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 긴급 정지 API ===

@bp.route('/emergency/status', methods=['GET'])
def get_emergency_status():
    """긴급 상태 조회"""
    try:
        from core.emergency_controller import get_emergency_controller

        controller = get_emergency_controller()
        status = controller.get_status()

        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/emergency/stop', methods=['POST'])
def trigger_emergency_stop():
    """긴급 정지 활성화"""
    try:
        from core.emergency_controller import get_emergency_controller

        data = request.get_json() or {}
        reason = data.get('reason', '수동 긴급 정지')

        controller = get_emergency_controller()
        controller.trigger_emergency_stop(reason, triggered_by='dashboard')

        return jsonify({
            'success': True,
            'message': f'긴급 정지 활성화됨: {reason}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/emergency/release', methods=['POST'])
def release_emergency_stop():
    """긴급 정지 해제"""
    try:
        from core.emergency_controller import get_emergency_controller

        controller = get_emergency_controller()
        controller.release_emergency_stop(released_by='dashboard')

        return jsonify({
            'success': True,
            'message': '긴급 정지 해제됨'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === A/B 테스트 API ===

@bp.route('/ab-test/status', methods=['GET'])
def get_ab_test_status():
    """A/B 테스트 현황"""
    try:
        from core.strategy_ab_test import get_ab_test_manager

        manager = get_ab_test_manager()
        status = manager.get_test_status()

        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/ab-test/summary', methods=['GET'])
def get_ab_test_summary():
    """A/B 테스트 요약"""
    try:
        from core.strategy_ab_test import get_ab_test_manager

        manager = get_ab_test_manager()
        summary = manager.get_summary()

        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/ab-test/start', methods=['POST'])
def start_ab_test():
    """A/B 테스트 시작"""
    try:
        from core.strategy_ab_test import get_ab_test_manager
        from dataclasses import asdict

        data = request.get_json()
        control = data.get('control_version')
        treatment = data.get('treatment_version')
        weight = data.get('treatment_weight', 0.10)

        if not control or not treatment:
            return jsonify({
                'success': False,
                'error': 'control_version과 treatment_version이 필요합니다'
            }), 400

        manager = get_ab_test_manager()
        test = manager.start_ab_test(control, treatment, weight)

        return jsonify({
            'success': True,
            'data': asdict(test)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 실시간 이벤트 API ===

@bp.route('/events/recent', methods=['GET'])
def get_recent_events():
    """최근 이벤트 조회"""
    try:
        from core.event_bus import get_event_bus

        bus = get_event_bus()
        limit = request.args.get('limit', 50, type=int)
        event_type = request.args.get('type')

        if event_type:
            from core.event_bus import EventType
            try:
                et = EventType(event_type)
                events = bus.get_recent_events(limit, et)
            except ValueError:
                events = bus.get_recent_events(limit)
        else:
            events = bus.get_recent_events(limit)

        return jsonify({
            'success': True,
            'data': events
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/events/stats', methods=['GET'])
def get_event_stats():
    """이벤트 통계"""
    try:
        from core.event_bus import get_event_bus

        bus = get_event_bus()
        stats = bus.get_stats()

        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 진단 API ===

@bp.route('/diagnostics/report', methods=['GET'])
def get_diagnostic_report():
    """진단 보고서 조회"""
    try:
        from utils.diagnostic_logger import get_diagnostic_logger

        diag = get_diagnostic_logger()
        report = diag.generate_diagnostic_report()

        return jsonify({
            'success': True,
            'data': report
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/diagnostics/api-summary', methods=['GET'])
def get_api_summary():
    """API 호출 요약"""
    try:
        from utils.diagnostic_logger import get_diagnostic_logger

        diag = get_diagnostic_logger()
        summary = diag.get_api_summary()

        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 거래 로그 API ===

@bp.route('/trades/recent', methods=['GET'])
def get_recent_trades_log():
    """최근 거래 로그"""
    try:
        from utils.trade_logger import get_trade_logger

        trade_logger = get_trade_logger()
        limit = request.args.get('limit', 50, type=int)
        trades = trade_logger.get_recent_trades(limit)

        return jsonify({
            'success': True,
            'data': trades
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/trades/pending', methods=['GET'])
def get_pending_trades():
    """대기 중 거래"""
    try:
        from utils.trade_logger import get_trade_logger

        trade_logger = get_trade_logger()
        pending = trade_logger.get_pending_trades()

        return jsonify({
            'success': True,
            'data': pending
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/trades/stats', methods=['GET'])
def get_trade_stats():
    """거래 통계"""
    try:
        from utils.trade_logger import get_trade_logger

        trade_logger = get_trade_logger()
        stats = trade_logger.get_trade_stats()

        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 통합 대시보드 API ===

@bp.route('/dashboard/overview', methods=['GET'])
def get_dashboard_overview():
    """대시보드 전체 개요"""
    try:
        result = {}

        # 긴급 상태
        try:
            from core.emergency_controller import get_emergency_controller
            controller = get_emergency_controller()
            result['emergency'] = controller.get_status()
        except:
            result['emergency'] = {'level': 'unknown'}

        # 리스크 상태
        try:
            from core.risk_validation_pipeline import get_risk_pipeline
            pipeline = get_risk_pipeline()
            result['risk'] = pipeline.get_validation_summary()
        except:
            result['risk'] = {}

        # 성능 요약
        try:
            from core.performance_analyzer import get_performance_analyzer
            analyzer = get_performance_analyzer()
            result['performance'] = analyzer.get_summary()
        except:
            result['performance'] = {}

        # A/B 테스트
        try:
            from core.strategy_ab_test import get_ab_test_manager
            manager = get_ab_test_manager()
            result['ab_test'] = manager.get_summary()
        except:
            result['ab_test'] = {}

        # 이벤트 통계
        try:
            from core.event_bus import get_event_bus
            bus = get_event_bus()
            result['events'] = bus.get_stats()
        except:
            result['events'] = {}

        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 성능 최적화 API (v8.1) ===

@bp.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    """스마트 캐시 통계"""
    try:
        from core.smart_cache import get_smart_cache
        cache = get_smart_cache()
        return jsonify({
            'success': True,
            'data': cache.get_stats()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """캐시 전체 무효화"""
    try:
        from core.smart_cache import get_smart_cache, CacheType
        cache = get_smart_cache()

        data = request.get_json() or {}
        cache_type = data.get('type')

        if cache_type:
            try:
                ct = CacheType(cache_type)
                count = cache.invalidate(ct)
            except ValueError:
                return jsonify({'success': False, 'error': f'Invalid cache type: {cache_type}'}), 400
        else:
            count = cache.invalidate()

        return jsonify({
            'success': True,
            'message': f'{count}개 캐시 무효화됨'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/batch-price/stats', methods=['GET'])
def get_batch_price_stats():
    """배치 가격 조회 통계"""
    try:
        from core.batch_price_fetcher import get_batch_price_fetcher
        fetcher = get_batch_price_fetcher()
        return jsonify({
            'success': True,
            'data': fetcher.get_stats()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/order-idempotency/stats', methods=['GET'])
def get_order_idempotency_stats():
    """주문 멱등성 통계"""
    try:
        from core.order_idempotency import get_order_idempotency
        manager = get_order_idempotency()
        return jsonify({
            'success': True,
            'data': manager.get_stats()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/db-transaction/stats', methods=['GET'])
def get_db_transaction_stats():
    """DB 트랜잭션 통계"""
    try:
        from core.db_transaction import get_transaction_manager
        manager = get_transaction_manager()
        return jsonify({
            'success': True,
            'data': manager.get_stats()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/scheduler/stats', methods=['GET'])
def get_scheduler_stats():
    """비동기 스케줄러 통계"""
    try:
        from core.async_scheduler import get_async_scheduler
        scheduler = get_async_scheduler()
        return jsonify({
            'success': True,
            'data': scheduler.get_stats()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/scheduler/tasks', methods=['GET'])
def get_scheduler_tasks():
    """스케줄러 태스크 목록"""
    try:
        from core.async_scheduler import get_async_scheduler
        scheduler = get_async_scheduler()
        return jsonify({
            'success': True,
            'data': scheduler.get_all_tasks()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/scheduler/trigger/<task_id>', methods=['POST'])
def trigger_scheduler_task(task_id):
    """스케줄러 태스크 즉시 실행"""
    try:
        from core.async_scheduler import get_async_scheduler
        scheduler = get_async_scheduler()

        if scheduler.trigger_task(task_id):
            return jsonify({
                'success': True,
                'message': f'태스크 {task_id} 트리거됨'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'태스크 {task_id} 찾을 수 없음'
            }), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/system/optimization-stats', methods=['GET'])
def get_optimization_stats():
    """전체 최적화 시스템 통계"""
    try:
        result = {}

        # 스마트 캐시
        try:
            from core.smart_cache import get_smart_cache
            result['smart_cache'] = get_smart_cache().get_stats()
        except:
            result['smart_cache'] = {}

        # 배치 가격 조회
        try:
            from core.batch_price_fetcher import get_batch_price_fetcher
            result['batch_price_fetcher'] = get_batch_price_fetcher().get_stats()
        except:
            result['batch_price_fetcher'] = {}

        # 주문 멱등성
        try:
            from core.order_idempotency import get_order_idempotency
            result['order_idempotency'] = get_order_idempotency().get_stats()
        except:
            result['order_idempotency'] = {}

        # DB 트랜잭션
        try:
            from core.db_transaction import get_transaction_manager
            result['db_transaction'] = get_transaction_manager().get_stats()
        except:
            result['db_transaction'] = {}

        # 스케줄러
        try:
            from core.async_scheduler import get_async_scheduler
            result['scheduler'] = get_async_scheduler().get_stats()
        except:
            result['scheduler'] = {}

        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 서킷 브레이커 API (v8.2) ===

@bp.route('/circuit-breaker/stats', methods=['GET'])
def get_circuit_breaker_stats():
    """서킷 브레이커 전체 통계"""
    try:
        from core.circuit_breaker import get_all_circuit_stats
        return jsonify({
            'success': True,
            'data': get_all_circuit_stats()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/circuit-breaker/<name>/reset', methods=['POST'])
def reset_circuit_breaker(name):
    """특정 서킷 브레이커 리셋"""
    try:
        from core.circuit_breaker import get_circuit_breaker
        cb = get_circuit_breaker(name)
        cb.reset()
        return jsonify({
            'success': True,
            'message': f'서킷 브레이커 "{name}" 리셋됨'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 자가 치유 엔진 API ===

@bp.route('/health/status', methods=['GET'])
def get_health_status():
    """시스템 건강 상태"""
    try:
        from core.self_healing_engine import get_healing_engine
        engine = get_healing_engine()
        return jsonify({
            'success': True,
            'data': engine.get_status()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/health/integrity', methods=['GET'])
def check_data_integrity():
    """데이터 무결성 검증"""
    try:
        from core.self_healing_engine import get_healing_engine
        from virtual_trading.database import get_db_session

        engine = get_healing_engine()
        session = get_db_session()

        result = engine.verify_data_integrity(session)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/health/repair', methods=['POST'])
def auto_repair():
    """자동 복구 실행"""
    try:
        from core.self_healing_engine import get_healing_engine
        from virtual_trading.database import get_db_session

        data = request.get_json() or {}
        issue_type = data.get('issue_type')

        if not issue_type:
            return jsonify({'success': False, 'error': 'issue_type 필요'}), 400

        engine = get_healing_engine()
        session = get_db_session()

        success = engine.auto_repair(session, issue_type)
        return jsonify({
            'success': success,
            'message': '복구 완료' if success else '복구 실패'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 자율 최적화 API ===

@bp.route('/optimizer/status', methods=['GET'])
def get_optimizer_status():
    """자율 최적화 상태"""
    try:
        from core.autonomous_optimizer import get_autonomous_optimizer
        optimizer = get_autonomous_optimizer()
        return jsonify({
            'success': True,
            'data': optimizer.get_status()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/optimizer/tune', methods=['POST'])
def trigger_auto_tune():
    """자동 튜닝 트리거"""
    try:
        from core.autonomous_optimizer import get_autonomous_optimizer
        optimizer = get_autonomous_optimizer()
        result = optimizer.auto_tune()
        return jsonify({
            'success': result.get('success', False),
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/optimizer/market-condition', methods=['POST'])
def update_market_condition():
    """시장 상황 업데이트"""
    try:
        from core.autonomous_optimizer import get_autonomous_optimizer

        data = request.get_json() or {}
        optimizer = get_autonomous_optimizer()
        condition = optimizer.detect_market_condition(data)

        return jsonify({
            'success': True,
            'data': {
                'market_condition': condition.value,
                'mode': optimizer._mode.value
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 거래 코디네이터 API ===

@bp.route('/coordinator/stats', methods=['GET'])
def get_coordinator_stats():
    """거래 코디네이터 통계"""
    try:
        from core.trade_coordinator import get_trade_coordinator
        coordinator = get_trade_coordinator()
        return jsonify({
            'success': True,
            'data': coordinator.get_stats()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/coordinator/positions', methods=['GET'])
def get_coordinator_positions():
    """거래 코디네이터 포지션 목록"""
    try:
        from core.trade_coordinator import get_trade_coordinator
        coordinator = get_trade_coordinator()
        return jsonify({
            'success': True,
            'data': coordinator.get_all_positions()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/coordinator/partial-close', methods=['POST'])
def create_partial_close():
    """부분 청산 주문 생성"""
    try:
        from core.trade_coordinator import get_trade_coordinator

        data = request.get_json() or {}
        position_id = data.get('position_id')
        close_ratio = data.get('close_ratio', 0.5)
        price = data.get('price')
        reason = data.get('reason', '')

        if not position_id or not price:
            return jsonify({'success': False, 'error': 'position_id와 price 필요'}), 400

        coordinator = get_trade_coordinator()
        order_id = coordinator.create_partial_close(
            position_id=position_id,
            close_ratio=close_ratio,
            price=price,
            reason=reason
        )

        if order_id:
            return jsonify({
                'success': True,
                'data': {'order_id': order_id}
            })
        else:
            return jsonify({'success': False, 'error': '부분 청산 주문 생성 실패'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 지능형 데이터 매니저 API ===

@bp.route('/data-manager/stats', methods=['GET'])
def get_data_manager_stats():
    """지능형 데이터 매니저 통계"""
    try:
        from core.intelligent_data_manager import get_data_manager
        manager = get_data_manager()
        return jsonify({
            'success': True,
            'data': manager.get_stats()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/data-manager/invalidate', methods=['POST'])
def invalidate_data():
    """데이터 캐시 무효화"""
    try:
        from core.intelligent_data_manager import get_data_manager

        data = request.get_json() or {}
        stock_code = data.get('stock_code')

        manager = get_data_manager()
        manager.invalidate_on_trade(stock_code)

        return jsonify({
            'success': True,
            'message': '캐시 무효화 완료'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# === 통합 시스템 API (v8.2) ===

@bp.route('/system/full-status', methods=['GET'])
def get_full_system_status():
    """전체 시스템 상태 (v8.2 통합)"""
    try:
        result = {
            'timestamp': datetime.now().isoformat(),
            'version': '8.2'
        }

        # 서킷 브레이커
        try:
            from core.circuit_breaker import get_all_circuit_stats
            result['circuit_breakers'] = get_all_circuit_stats()
        except:
            result['circuit_breakers'] = {}

        # 자가 치유 엔진
        try:
            from core.self_healing_engine import get_healing_engine
            result['health'] = get_healing_engine().get_status()
        except:
            result['health'] = {}

        # 자율 최적화
        try:
            from core.autonomous_optimizer import get_autonomous_optimizer
            result['optimizer'] = get_autonomous_optimizer().get_status()
        except:
            result['optimizer'] = {}

        # 거래 코디네이터
        try:
            from core.trade_coordinator import get_trade_coordinator
            result['coordinator'] = get_trade_coordinator().get_stats()
        except:
            result['coordinator'] = {}

        # 데이터 매니저
        try:
            from core.intelligent_data_manager import get_data_manager
            result['data_manager'] = get_data_manager().get_stats()
        except:
            result['data_manager'] = {}

        # 리스크 파이프라인
        try:
            from core.risk_validation_pipeline import get_risk_pipeline
            pipeline = get_risk_pipeline()
            result['risk_pipeline'] = pipeline.get_stats()
        except:
            result['risk_pipeline'] = {}

        # 긴급 정지
        try:
            from core.emergency_controller import get_emergency_controller
            controller = get_emergency_controller()
            result['emergency'] = {
                'level': controller.current_level.value,
                'trading_allowed': controller.is_trading_allowed(),
                'new_buy_allowed': controller.is_new_buy_allowed()
            }
        except:
            result['emergency'] = {}

        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
