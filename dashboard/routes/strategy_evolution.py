"""
전략 진화 현황 API
"""
from flask import Blueprint, jsonify
import sqlite3
import json
import threading
import subprocess
import signal
import os
import sys
from datetime import datetime
from utils.logger_new import get_logger

logger = get_logger()  # Fix: get_logger()는 인자를 받지 않음

evolution_bp = Blueprint('evolution', __name__, url_prefix='/api/evolution')

DB_PATH = "data/strategy_evolution.db"

# Global state management
_evolution_process = None
_evolution_thread = None
_evolution_running = False


@evolution_bp.route('/status', methods=['GET'])
def get_status():
    """현재 진화 상태 조회"""
    global _evolution_process, _evolution_running

    try:
        # Check if process is running
        process_running = False
        if _evolution_process:
            if _evolution_process.poll() is None:
                process_running = True
            else:
                # Process has terminated
                _evolution_running = False

        # Fix: 데이터베이스 파일 존재 여부 확인
        if not os.path.exists(DB_PATH):
            logger.warning(f"진화 데이터베이스 없음: {DB_PATH}")
            return jsonify({
                'success': True,
                'running': process_running,
                'message': '전략 진화 엔진이 아직 실행되지 않았거나 데이터가 없습니다',
                'note': '대시보드의 "진화 시작" 버튼을 클릭하세요'
            })

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
            'running': process_running,
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
        # Fix: 데이터베이스 파일 존재 여부 확인
        import os
        if not os.path.exists(DB_PATH):
            logger.warning(f"진화 데이터베이스 없음: {DB_PATH}")
            return jsonify({
                'success': False,
                'history': [],
                'total_generations': 0,
                'message': '진화 데이터가 없습니다'
            })

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
        # Fix: 데이터베이스 파일 존재 여부 확인
        import os
        if not os.path.exists(DB_PATH):
            logger.warning(f"진화 데이터베이스 없음: {DB_PATH}")
            return jsonify({
                'success': False,
                'message': '전략 진화 엔진이 실행되지 않았습니다'
            })

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


@evolution_bp.route('/top-strategies', methods=['GET'])
def get_top_strategies():
    """현재 최고 성과 전략 Top 10 조회"""
    try:
        # Fix: 데이터베이스 파일 존재 여부 확인
        import os
        if not os.path.exists(DB_PATH):
            logger.warning(f"진화 데이터베이스 없음: {DB_PATH}")
            return jsonify({
                'success': True,
                'strategies': [],
                'total': 0,
                'message': '전략 진화 엔진이 실행되지 않았습니다'
            })

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 최고 성과 전략 Top 10
        cursor.execute("""
            SELECT es.id, es.generation, es.genes,
                   fr.fitness_score, fr.total_return_pct, fr.win_rate,
                   fr.sharpe_ratio, fr.max_drawdown_pct, fr.total_trades,
                   es.created_at
            FROM evolved_strategies es
            JOIN fitness_results fr ON es.id = fr.strategy_id
            ORDER BY fr.fitness_score DESC
            LIMIT 10
        """)

        strategies = []
        for row in cursor.fetchall():
            genes = json.loads(row['genes'])
            strategies.append({
                'id': row['id'],
                'name': f"전략 G{row['generation']}-{row['id']}",
                'generation': row['generation'],
                'fitness_score': round(row['fitness_score'], 2),
                'return_rate': round(row['total_return_pct'] or 0, 2),
                'win_rate': round(row['win_rate'] or 0, 2),
                'sharpe_ratio': round(row['sharpe_ratio'] or 0, 2),
                'max_drawdown': round(row['max_drawdown_pct'] or 0, 2),
                'total_trades': row['total_trades'] or 0,
                'created_at': row['created_at']
            })

        conn.close()

        return jsonify({
            'success': True,
            'strategies': strategies,
            'total': len(strategies)
        })

    except Exception as e:
        logger.error(f"Top 전략 조회 실패: {e}")
        return jsonify({'success': False, 'strategies': [], 'total': 0, 'error': str(e)})


@evolution_bp.route('/deployment-status', methods=['GET'])
def get_deployment_status():
    """배포된 전략 현황 조회"""
    try:
        # Fix: 데이터베이스 파일 존재 여부 확인
        import os
        if not os.path.exists(DB_PATH):
            logger.warning(f"진화 데이터베이스 없음: {DB_PATH}")
            return jsonify({
                'success': False,
                'deployable_strategies': [],
                'total': 0,
                'message': '전략 진화 엔진이 실행되지 않았습니다'
            })

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 최근 배포 가능한 최우수 전략들
        cursor.execute("""
            SELECT
                gs.generation,
                gs.best_fitness,
                gs.best_strategy_id,
                es.genes,
                fr.total_return_pct,
                fr.win_rate,
                fr.sharpe_ratio,
                gs.created_at
            FROM generation_stats gs
            JOIN evolved_strategies es ON gs.best_strategy_id = es.id
            JOIN fitness_results fr ON es.id = fr.strategy_id
            ORDER BY gs.generation DESC
            LIMIT 10
        """)

        deployable_strategies = []
        for row in cursor.fetchall():
            genes = json.loads(row['genes'])
            deployable_strategies.append({
                'generation': row['generation'],
                'fitness': round(row['best_fitness'], 2),
                'strategy_id': row['best_strategy_id'],
                'backtest_return': round(row['total_return_pct'] or 0, 2),
                'win_rate': round(row['win_rate'] or 0, 2),
                'sharpe_ratio': round(row['sharpe_ratio'] or 0, 2),
                'created_at': row['created_at'],
                'genes_summary': {
                    'buy_rsi': f"{genes.get('buy_rsi_min', 0):.1f}-{genes.get('buy_rsi_max', 0):.1f}",
                    'sell_profit': f"+{genes.get('sell_take_profit', 0)*100:.1f}%",
                    'sell_loss': f"{genes.get('sell_stop_loss', 0)*100:.1f}%"
                }
            })

        conn.close()

        return jsonify({
            'success': True,
            'deployable_strategies': deployable_strategies,
            'total': len(deployable_strategies),
            'note': '자동 배포 활성화 시 --auto-deploy 플래그 사용'
        })

    except Exception as e:
        logger.error(f"배포 현황 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@evolution_bp.route('/start', methods=['POST'])
def start_evolution():
    """진화 알고리즘 시작"""
    global _evolution_process, _evolution_running

    try:
        # Check if already running
        if _evolution_running and _evolution_process:
            if _evolution_process.poll() is None:  # Process is still running
                logger.warning("진화 알고리즘이 이미 실행 중입니다")
                return jsonify({
                    'success': False,
                    'message': '진화 알고리즘이 이미 실행 중입니다',
                    'running': True,
                    'pid': _evolution_process.pid
                })

        logger.info("🚀 진화 알고리즘 시작 중...")

        # Get the project root directory
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        script_path = os.path.join(project_root, 'run_strategy_optimizer.py')

        # Create logs directory
        logs_dir = os.path.join(project_root, 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Log files for stdout and stderr
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        stdout_log = os.path.join(logs_dir, f'evolution_stdout_{timestamp}.log')
        stderr_log = os.path.join(logs_dir, f'evolution_stderr_{timestamp}.log')

        stdout_f = open(stdout_log, 'w', encoding='utf-8')
        stderr_f = open(stderr_log, 'w', encoding='utf-8')

        # Start the evolution process in background
        _evolution_process = subprocess.Popen(
            [sys.executable, script_path, '--auto-deploy', '--interval', '300', '--population-size', '20'],
            cwd=project_root,
            stdout=stdout_f,
            stderr=stderr_f,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )

        # Wait a moment to check if process starts successfully
        import time
        time.sleep(1)

        if _evolution_process.poll() is not None:
            # Process already terminated
            stdout_f.close()
            stderr_f.close()

            # Read error logs
            with open(stderr_log, 'r', encoding='utf-8') as f:
                error_msg = f.read()

            logger.error(f"진화 프로세스가 즉시 종료됨: {error_msg}")
            return jsonify({
                'success': False,
                'message': '진화 알고리즘 시작 실패 - 프로세스가 즉시 종료되었습니다',
                'error': error_msg[:500],  # First 500 chars
                'stderr_log': stderr_log
            }), 500

        _evolution_running = True

        logger.info(f"✅ 진화 알고리즘 프로세스 시작됨 (PID: {_evolution_process.pid})")
        logger.info(f"   stdout 로그: {stdout_log}")
        logger.info(f"   stderr 로그: {stderr_log}")

        return jsonify({
            'success': True,
            'message': '진화 알고리즘이 백그라운드에서 시작되었습니다',
            'pid': _evolution_process.pid,
            'running': True,
            'stdout_log': stdout_log,
            'stderr_log': stderr_log,
            'note': f'로그 파일: {stdout_log}'
        })

    except Exception as e:
        logger.error(f"진화 알고리즘 시작 실패: {e}", exc_info=True)
        _evolution_running = False
        return jsonify({'success': False, 'error': str(e)}), 500


@evolution_bp.route('/stop', methods=['POST'])
def stop_evolution():
    """진화 알고리즘 중지"""
    global _evolution_process, _evolution_running

    try:
        if not _evolution_running or not _evolution_process:
            logger.warning("진화 알고리즘이 실행 중이지 않습니다")
            return jsonify({
                'success': False,
                'message': '진화 알고리즘이 실행 중이지 않습니다',
                'running': False
            })

        # Check if process is still running
        if _evolution_process.poll() is not None:
            logger.warning("진화 프로세스가 이미 종료되었습니다")
            _evolution_running = False
            return jsonify({
                'success': False,
                'message': '진화 프로세스가 이미 종료되었습니다',
                'running': False
            })

        logger.info(f"⏹️  진화 알고리즘 중지 중... (PID: {_evolution_process.pid})")

        # Terminate the process gracefully
        try:
            if sys.platform == 'win32':
                # On Windows, use CTRL_BREAK_EVENT
                _evolution_process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                # On Unix, use SIGTERM
                _evolution_process.terminate()

            # Wait for process to terminate (with timeout)
            try:
                _evolution_process.wait(timeout=10)
                logger.info("✅ 진화 프로세스 정상 종료됨")
            except subprocess.TimeoutExpired:
                logger.warning("진화 프로세스가 응답하지 않음, 강제 종료 중...")
                _evolution_process.kill()
                _evolution_process.wait()
                logger.info("✅ 진화 프로세스 강제 종료됨")
        except Exception as e:
            logger.error(f"프로세스 종료 중 오류: {e}")
            # Try to kill anyway
            _evolution_process.kill()

        _evolution_running = False
        _evolution_process = None

        return jsonify({
            'success': True,
            'message': '진화 알고리즘이 중지되었습니다',
            'running': False
        })

    except Exception as e:
        logger.error(f"진화 알고리즘 중지 실패: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


__all__ = ['evolution_bp']
