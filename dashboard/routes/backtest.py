"""
Backtest Routes - 12가지 전략 백테스팅 API
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from typing import Optional
import traceback

from utils.logger_new import get_logger

logger = get_logger()

backtest_bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')

_bot_instance = None
_backtester = None


def set_bot_instance(bot):
    global _bot_instance, _backtester
    _bot_instance = bot

    if bot and hasattr(bot, 'market_api'):
        try:
            from ai.strategy_backtester import StrategyBacktester
            _backtester = StrategyBacktester(bot.market_api)
            logger.info("Backtester initialized")
        except Exception as e:
            logger.error(f"Failed to initialize backtester: {e}")


@backtest_bp.route('/strategies', methods=['GET'])
def get_strategies():
    """
    사용 가능한 전략 목록 조회
    """
    try:
        if not _backtester:
            return jsonify({
                'success': False,
                'error': 'Backtester not initialized'
            }), 500

        strategies = []
        for strategy in _backtester.strategies:
            strategies.append({
                'name': strategy.name,
                'description': getattr(strategy, 'description', ''),
                'risk_level': getattr(strategy, 'risk_level', 'Medium'),
            })

        return jsonify({
            'success': True,
            'strategies': strategies,
            'total': len(strategies)
        })

    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backtest_bp.route('/run', methods=['POST'])
def run_backtest():
    """
    백테스트 실행

    Request Body:
    {
        "stock_codes": ["005930", "000660"],
        "start_date": "20250101",
        "end_date": "20250108",
        "interval": "5",
        "parallel": true
    }
    """
    try:
        if not _backtester:
            return jsonify({
                'success': False,
                'error': 'Backtester not initialized'
            }), 500

        data = request.get_json()

        stock_codes = data.get('stock_codes', ['005930'])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        interval = data.get('interval', '5')
        parallel = data.get('parallel', True)

        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')

        logger.info(f"Running backtest: {stock_codes}, {start_date} ~ {end_date}")

        results = _backtester.run_backtest(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            parallel=parallel
        )

        response_data = {}
        for strategy_name, result in results.items():
            response_data[strategy_name] = {
                'strategy_name': result.strategy_name,
                'initial_cash': result.initial_cash,
                'final_cash': result.final_cash,
                'total_return': result.total_return,
                'total_return_pct': result.total_return_pct,

                'total_trades': result.total_trades,
                'winning_trades': result.winning_trades,
                'losing_trades': result.losing_trades,
                'win_rate': result.win_rate,

                'max_drawdown': result.max_drawdown,
                'max_drawdown_pct': result.max_drawdown_pct,
                'sharpe_ratio': result.sharpe_ratio,
                'sortino_ratio': result.sortino_ratio,

                'avg_profit_per_trade': result.avg_profit_per_trade,
                'avg_loss_per_trade': result.avg_loss_per_trade,
                'profit_factor': result.profit_factor,

                'daily_returns': result.daily_returns,
                'daily_cash': result.daily_cash,
                'daily_dates': result.daily_dates,

                'trades': result.trades[:100],
            }

        ranking = _backtester.get_ranking(results)
        best_strategy = _backtester.get_best_strategy(results)

        return jsonify({
            'success': True,
            'results': response_data,
            'ranking': [
                {
                    'rank': idx + 1,
                    'name': name,
                    'return_pct': result.total_return_pct,
                    'win_rate': result.win_rate,
                    'sharpe_ratio': result.sharpe_ratio,
                    'total_trades': result.total_trades
                }
                for idx, (name, result) in enumerate(ranking)
            ],
            'best_strategy': {
                'name': best_strategy[0],
                'return_pct': best_strategy[1].total_return_pct,
                'win_rate': best_strategy[1].win_rate,
                'sharpe_ratio': best_strategy[1].sharpe_ratio
            } if best_strategy else None,
            'config': {
                'stock_codes': stock_codes,
                'start_date': start_date,
                'end_date': end_date,
                'interval': interval
            }
        })

    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@backtest_bp.route('/status', methods=['GET'])
def get_status():
    """
    백테스터 상태 확인
    """
    try:
        return jsonify({
            'success': True,
            'initialized': _backtester is not None,
            'strategies_count': len(_backtester.strategies) if _backtester else 0
        })

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


__all__ = ['backtest_bp', 'set_bot_instance']
