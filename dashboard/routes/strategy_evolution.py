"""
전략 진화 현황 API
"""
from flask import Blueprint, jsonify
import sqlite3
import json
from datetime import datetime
from utils.logger_new import get_logger

logger = get_logger(__name__)

evolution_bp = Blueprint('evolution', __name__, url_prefix='/api/evolution')

DB_PATH = "data/strategy_evolution.db"


@evolution_bp.route('/status', methods=['GET'])
def get_status():
    """현재 진화 상태 조회"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 최신 세대 정보
        cursor.execute("""
            SELECT generation, best_fitness, avg_fitness, worst_fitness, created_at
            FROM generation_stats
            ORDER BY generation DESC
            LIMIT 1
        """)
        latest = cursor.fetchone()

        if not latest:
            return jsonify({
                'success': True,
                'running': False,
                'message': '아직 진화가 시작되지 않았습니다'
            })

        # 전체 세대 수
        cursor.execute("SELECT COUNT(*) as count FROM generation_stats")
        total_generations = cursor.fetchone()['count']

        conn.close()

        return jsonify({
            'success': True,
            'running': True,
            'current_generation': latest['generation'],
            'total_generations': total_generations,
            'best_fitness': round(latest['best_fitness'], 2),
            'avg_fitness': round(latest['avg_fitness'], 2),
            'worst_fitness': round(latest['worst_fitness'], 2),
            'last_update': latest['created_at']
        })

    except Exception as e:
        logger.error(f"진화 상태 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@evolution_bp.route('/history', methods=['GET'])
def get_history():
    """세대별 진화 히스토리"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT generation, best_fitness, avg_fitness, worst_fitness, created_at
            FROM generation_stats
            ORDER BY generation ASC
        """)

        history = []
        for row in cursor.fetchall():
            history.append({
                'generation': row['generation'],
                'best_fitness': round(row['best_fitness'], 2),
                'avg_fitness': round(row['avg_fitness'], 2),
                'worst_fitness': round(row['worst_fitness'], 2),
                'created_at': row['created_at']
            })

        conn.close()

        return jsonify({
            'success': True,
            'history': history,
            'total_generations': len(history)
        })

    except Exception as e:
        logger.error(f"진화 히스토리 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@evolution_bp.route('/best-strategy', methods=['GET'])
def get_best_strategy():
    """현재 최우수 전략 조회"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 최신 세대의 최고 점수 전략
        cursor.execute("""
            SELECT es.id, es.generation, es.genes, fr.fitness_score,
                   fr.total_return_pct, fr.sharpe_ratio, fr.win_rate,
                   fr.max_drawdown_pct, fr.profit_factor, fr.total_trades
            FROM evolved_strategies es
            JOIN fitness_results fr ON es.id = fr.strategy_id
            ORDER BY fr.fitness_score DESC
            LIMIT 1
        """)

        best = cursor.fetchone()
        conn.close()

        if not best:
            return jsonify({
                'success': False,
                'message': '최우수 전략을 찾을 수 없습니다'
            })

        genes = json.loads(best['genes'])

        return jsonify({
            'success': True,
            'strategy': {
                'id': best['id'],
                'generation': best['generation'],
                'fitness_score': round(best['fitness_score'], 2),
                'performance': {
                    'total_return_pct': round(best['total_return_pct'] or 0, 2),
                    'sharpe_ratio': round(best['sharpe_ratio'] or 0, 2),
                    'win_rate': round(best['win_rate'] or 0, 2),
                    'max_drawdown_pct': round(best['max_drawdown_pct'] or 0, 2),
                    'profit_factor': round(best['profit_factor'] or 0, 2),
                    'total_trades': best['total_trades'] or 0
                },
                'genes': genes
            }
        })

    except Exception as e:
        logger.error(f"최우수 전략 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@evolution_bp.route('/generation/<int:generation>', methods=['GET'])
def get_generation_detail(generation: int):
    """특정 세대의 전략들 조회"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT es.id, es.genes, fr.fitness_score
            FROM evolved_strategies es
            JOIN fitness_results fr ON es.id = fr.strategy_id
            WHERE es.generation = ?
            ORDER BY fr.fitness_score DESC
        """, (generation,))

        strategies = []
        for row in cursor.fetchall():
            strategies.append({
                'id': row['id'],
                'fitness_score': round(row['fitness_score'], 2),
                'genes': json.loads(row['genes'])
            })

        conn.close()

        return jsonify({
            'success': True,
            'generation': generation,
            'strategies': strategies,
            'count': len(strategies)
        })

    except Exception as e:
        logger.error(f"세대 상세 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


__all__ = ['evolution_bp']
