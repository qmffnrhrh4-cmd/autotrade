"""
dashboard/routes/autonomous.py
자율 진화 모드 대시보드 API

단일 화면에서 모든 자동매매 활동을 모니터링
"""
from flask import Blueprint, render_template, jsonify, current_app
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

autonomous_bp = Blueprint('autonomous', __name__)


@autonomous_bp.route('/')
def monitor():
    """자율 진화 모니터 대시보드"""
    return render_template('autonomous_monitor.html')


@autonomous_bp.route('/api/autonomous/status')
def get_status():
    """시스템 상태 조회"""
    try:
        bot = current_app.config.get('BOT')

        # 엔진 상태 확인
        engine_running = False
        evolution_running = False
        data_collector_running = False
        api_connected = False
        signal_count = 0
        api_stats = {}

        if bot:
            # 자율 엔진 상태
            if hasattr(bot, '_autonomous_engine') and bot._autonomous_engine:
                engine = bot._autonomous_engine
                engine_running = engine.is_running
                signal_count = engine.signal_queue.qsize() if hasattr(engine, 'signal_queue') else 0

            # 진화 엔진 상태
            if hasattr(bot, '_evolution_engine') and bot._evolution_engine:
                evolution_running = bot._evolution_engine.is_running

            # 데이터 수집기 상태
            if hasattr(bot, '_api_aggregator') and bot._api_aggregator:
                agg = bot._api_aggregator
                data_collector_running = agg.is_running
                api_stats = agg.get_api_coverage_stats() if hasattr(agg, 'get_api_coverage_stats') else {}

            # API 연결 상태
            if hasattr(bot, 'client') and bot.client:
                api_connected = True

        # 시장 상태
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        weekday = now.weekday()

        # 평일 9:00-15:30
        market_open = (
            weekday < 5 and
            ((hour == 9 and minute >= 0) or (9 < hour < 15) or (hour == 15 and minute <= 30))
        )

        return jsonify({
            'success': True,
            'engine_running': engine_running,
            'evolution_running': evolution_running,
            'data_collector_running': data_collector_running,
            'api_connected': api_connected,
            'market_open': market_open,
            'signal_count': signal_count,
            'api_stats': {
                'total': api_stats.get('collected_apis', 0),
                'foreign': api_stats.get('by_category', {}).get('foreign', 0),
                'institution': api_stats.get('by_category', {}).get('institution', 0),
                'program': api_stats.get('by_category', {}).get('program', 0),
                'volume': api_stats.get('by_category', {}).get('volume', 0),
                'orderbook': api_stats.get('by_category', {}).get('orderbook', 0),
                'sector': api_stats.get('by_category', {}).get('sector', 0),
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"상태 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'engine_running': False,
            'evolution_running': False,
            'data_collector_running': False,
            'api_connected': False,
            'market_open': False
        })


@autonomous_bp.route('/api/autonomous/evolution')
def get_evolution():
    """진화 상태 조회"""
    try:
        bot = current_app.config.get('BOT')

        evolution_data = {
            'generation': 0,
            'best_fitness': 0,
            'avg_fitness': 0,
            'population_size': 0,
            'deployed_count': 0,
            'is_evolving': False
        }

        if bot and hasattr(bot, '_evolution_engine') and bot._evolution_engine:
            engine = bot._evolution_engine
            stats = engine.get_evolution_stats() if hasattr(engine, 'get_evolution_stats') else {}

            evolution_data.update({
                'generation': stats.get('generation', 0),
                'best_fitness': engine.best_fitness if hasattr(engine, 'best_fitness') else 0,
                'avg_fitness': 0,  # 계산 필요
                'population_size': stats.get('population_size', 0),
                'deployed_count': stats.get('deployed_strategies', 0),
                'is_evolving': stats.get('is_running', False)
            })

            # 평균 적합도 계산
            if hasattr(engine, 'fitness_scores') and engine.fitness_scores:
                fitness_values = list(engine.fitness_scores.values())
                evolution_data['avg_fitness'] = sum(fitness_values) / len(fitness_values)

        return jsonify({
            'success': True,
            **evolution_data
        })

    except Exception as e:
        logger.error(f"진화 상태 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'generation': 0,
            'best_fitness': 0
        })


@autonomous_bp.route('/api/autonomous/signals')
def get_signals():
    """시장 신호 조회"""
    try:
        bot = current_app.config.get('BOT')
        signals = []

        if bot and hasattr(bot, '_api_aggregator') and bot._api_aggregator:
            agg = bot._api_aggregator
            recent = agg.get_recent_signals(5) if hasattr(agg, 'get_recent_signals') else []

            for s in recent:
                signals.append({
                    'type': s.signal_type if hasattr(s, 'signal_type') else 'neutral',
                    'strength': int(s.strength) if hasattr(s, 'strength') else 0,
                    'source': s.source if hasattr(s, 'source') else '',
                    'description': s.description if hasattr(s, 'description') else ''
                })

        return jsonify({
            'success': True,
            'signals': signals
        })

    except Exception as e:
        logger.error(f"신호 조회 오류: {e}")
        return jsonify({
            'success': False,
            'signals': []
        })


@autonomous_bp.route('/api/autonomous/logs')
def get_logs():
    """활동 로그 조회"""
    try:
        bot = current_app.config.get('BOT')
        logs = []

        if bot and hasattr(bot, '_autonomous_engine') and bot._autonomous_engine:
            engine = bot._autonomous_engine

            # 최근 거래
            for trade in engine.daily_trades[-20:]:
                logs.append({
                    'type': trade.get('action', 'trade'),
                    'title': trade.get('stock_name', trade.get('stock_code', '')),
                    'detail': f"{trade.get('quantity', 0)}주",
                    'time': trade.get('time', datetime.now()).isoformat()
                })

        return jsonify({
            'success': True,
            'logs': logs
        })

    except Exception as e:
        logger.error(f"로그 조회 오류: {e}")
        return jsonify({
            'success': False,
            'logs': []
        })
