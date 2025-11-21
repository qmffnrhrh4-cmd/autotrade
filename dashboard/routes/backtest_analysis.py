"""
백테스팅 결과 분석 대시보드
Backtest Analysis & Visualization Routes

진화 알고리즘 백테스팅 결과를 분석하고 시각화합니다.
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Blueprint 생성
backtest_analysis_bp = Blueprint('backtest_analysis', __name__)

# 모듈 레벨 변수
_bot_instance = None


def set_bot_instance(bot):
    """Set the bot instance"""
    global _bot_instance
    _bot_instance = bot


@backtest_analysis_bp.route('/api/backtest/analysis/summary')
def get_backtest_summary():
    """
    백테스팅 결과 요약 조회

    Returns:
        전략별 백테스팅 성과 요약
    """
    try:
        from virtual_trading import VirtualTradingDB

        db = VirtualTradingDB()
        strategies = db.get_all_strategies()

        summary_data = []

        for strategy in strategies:
            # Fix: Use 'id' instead of 'strategy_id'
            strategy_id = strategy.get('id') or strategy.get('strategy_id')
            if not strategy_id:
                continue

            # Use data from get_all_strategies() which already includes metrics
            summary_data.append({
                'strategy_id': strategy_id,
                'strategy_name': strategy.get('name', f'전략{strategy_id}'),
                'initial_capital': strategy.get('initial_capital', 0),
                'current_capital': strategy.get('current_capital', 0),
                'total_return': strategy.get('return_rate', 0),
                'win_rate': strategy.get('win_rate', 0),
                'total_trades': strategy.get('trade_count', 0),
                'created_at': strategy.get('created_at', '')
            })

        # 수익률 순으로 정렬
        summary_data.sort(key=lambda x: x['total_return'], reverse=True)

        return jsonify({
            'success': True,
            'strategies': summary_data,
            'total_strategies': len(summary_data)
        })

    except Exception as e:
        logger.error(f"백테스팅 요약 조회 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backtest_analysis_bp.route('/api/backtest/analysis/strategy/<int:strategy_id>')
def get_strategy_analysis(strategy_id: int):
    """
    특정 전략 상세 분석

    Args:
        strategy_id: 전략 ID

    Returns:
        상세 분석 데이터 (거래 내역, 수익 곡선, 주요 지표)
    """
    try:
        from virtual_trading import VirtualTradingDB

        db = VirtualTradingDB()

        # 전략 정보 조회
        strategies = db.get_all_strategies()
        strategy = next((s for s in strategies if s['strategy_id'] == strategy_id), None)

        if not strategy:
            return jsonify({
                'success': False,
                'error': '전략을 찾을 수 없습니다'
            }), 404

        # 성과 지표 조회
        metrics = db.get_strategy_summary(strategy_id=strategy_id)

        # 포지션 내역 조회 (최근 100개)
        positions = db.get_closed_positions(strategy_id=strategy_id, limit=100)

        # 수익 곡선 생성
        equity_curve = _calculate_equity_curve(positions, strategy['initial_capital'])

        # 월별 수익 분석
        monthly_returns = _calculate_monthly_returns(positions)

        # 거래 분석
        trade_analysis = _analyze_trades(positions)

        return jsonify({
            'success': True,
            'strategy': {
                'strategy_id': strategy_id,
                'strategy_name': strategy['strategy_name'],
                'description': strategy['description'],
                'initial_capital': strategy['initial_capital'],
                'created_at': strategy['created_at']
            },
            'metrics': metrics[0] if metrics else {},
            'equity_curve': equity_curve,
            'monthly_returns': monthly_returns,
            'trade_analysis': trade_analysis,
            'recent_trades': positions[:20]  # 최근 20개 거래
        })

    except Exception as e:
        logger.error(f"전략 분석 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backtest_analysis_bp.route('/api/backtest/analysis/compare')
def compare_strategies():
    """
    전략 비교 분석

    Query params:
        strategy_ids: 비교할 전략 ID 리스트 (쉼표 구분)

    Returns:
        전략 간 성과 비교 데이터
    """
    try:
        strategy_ids_str = request.args.get('strategy_ids', '')

        if not strategy_ids_str:
            return jsonify({
                'success': False,
                'error': 'strategy_ids 파라미터가 필요합니다'
            }), 400

        strategy_ids = [int(sid) for sid in strategy_ids_str.split(',')]

        from virtual_trading import VirtualTradingDB
        db = VirtualTradingDB()

        comparison_data = []

        for strategy_id in strategy_ids:
            strategies = db.get_all_strategies()
            strategy = next((s for s in strategies if s['strategy_id'] == strategy_id), None)

            if not strategy:
                continue

            metrics = db.get_strategy_summary(strategy_id=strategy_id)
            positions = db.get_closed_positions(strategy_id=strategy_id, limit=1000)

            comparison_data.append({
                'strategy_id': strategy_id,
                'strategy_name': strategy['strategy_name'],
                'total_return': metrics[0]['total_return'] if metrics else 0,
                'win_rate': metrics[0]['win_rate'] if metrics else 0,
                'total_trades': metrics[0]['total_trades'] if metrics else 0,
                'avg_profit': metrics[0]['avg_profit'] if metrics else 0,
                'max_drawdown': _calculate_max_drawdown(positions, strategy['initial_capital']),
                'sharpe_ratio': _calculate_sharpe_ratio(positions)
            })

        return jsonify({
            'success': True,
            'strategies': comparison_data
        })

    except Exception as e:
        logger.error(f"전략 비교 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backtest_analysis_bp.route('/api/backtest/analysis/evolution-progress')
def get_evolution_progress():
    """
    진화 알고리즘 진행 상황 조회

    Returns:
        세대별 성과 개선 현황
    """
    try:
        from virtual_trading import get_evolution_engine

        engine = get_evolution_engine()

        if not engine:
            return jsonify({
                'success': False,
                'error': '진화 엔진을 찾을 수 없습니다'
            }), 404

        # 세대별 최고 전략 성과
        generation_data = []

        for generation in range(engine.generation + 1):
            # 해당 세대의 전략들 조회
            # (실제로는 DB에서 generation 필드로 필터링)
            # 여기서는 간단히 현재 세대 정보만 반환
            pass

        return jsonify({
            'success': True,
            'current_generation': engine.generation,
            'population_size': engine.population_size,
            'best_fitness': getattr(engine, 'best_fitness', None),
            'evolution_history': generation_data
        })

    except Exception as e:
        logger.error(f"진화 진행 상황 조회 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _calculate_equity_curve(positions: List[Dict], initial_capital: float) -> List[Dict]:
    """수익 곡선 계산"""
    if not positions:
        return [{'date': datetime.now().isoformat(), 'equity': initial_capital}]

    equity_curve = [{'date': None, 'equity': initial_capital}]
    current_equity = initial_capital

    for pos in sorted(positions, key=lambda x: x.get('close_time', '')):
        if pos.get('profit_loss'):
            current_equity += pos['profit_loss']
            equity_curve.append({
                'date': pos.get('close_time'),
                'equity': current_equity
            })

    return equity_curve


def _calculate_monthly_returns(positions: List[Dict]) -> List[Dict]:
    """월별 수익률 계산"""
    if not positions:
        return []

    monthly_data = {}

    for pos in positions:
        if not pos.get('close_time'):
            continue

        try:
            close_date = datetime.fromisoformat(pos['close_time'].replace('Z', '+00:00'))
            month_key = close_date.strftime('%Y-%m')

            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'month': month_key,
                    'total_profit': 0,
                    'trade_count': 0
                }

            monthly_data[month_key]['total_profit'] += pos.get('profit_loss', 0)
            monthly_data[month_key]['trade_count'] += 1
        except:
            continue

    return sorted(monthly_data.values(), key=lambda x: x['month'])


def _analyze_trades(positions: List[Dict]) -> Dict[str, Any]:
    """거래 분석"""
    if not positions:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0
        }

    winning_trades = [p for p in positions if p.get('profit_loss', 0) > 0]
    losing_trades = [p for p in positions if p.get('profit_loss', 0) < 0]

    total_wins = sum(p['profit_loss'] for p in winning_trades)
    total_losses = abs(sum(p['profit_loss'] for p in losing_trades))

    return {
        'total_trades': len(positions),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': len(winning_trades) / len(positions) * 100 if positions else 0,
        'avg_win': total_wins / len(winning_trades) if winning_trades else 0,
        'avg_loss': total_losses / len(losing_trades) if losing_trades else 0,
        'profit_factor': total_wins / total_losses if total_losses > 0 else 0
    }


def _calculate_max_drawdown(positions: List[Dict], initial_capital: float) -> float:
    """최대 낙폭(MDD) 계산"""
    if not positions:
        return 0

    equity_curve = _calculate_equity_curve(positions, initial_capital)

    max_equity = initial_capital
    max_drawdown = 0

    for point in equity_curve:
        equity = point['equity']
        if equity > max_equity:
            max_equity = equity

        drawdown = (max_equity - equity) / max_equity * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return max_drawdown


def _calculate_sharpe_ratio(positions: List[Dict]) -> float:
    """샤프 비율 계산 (간단 버전)"""
    if not positions:
        return 0

    returns = [p.get('profit_loss', 0) for p in positions if p.get('profit_loss') is not None]

    if not returns:
        return 0

    avg_return = sum(returns) / len(returns)

    # 표준편차 계산
    variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
    std_dev = variance ** 0.5

    if std_dev == 0:
        return 0

    # 샤프 비율 (무위험 수익률 0으로 가정)
    return (avg_return / std_dev) * (252 ** 0.5)  # 연율화
