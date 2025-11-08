"""
Deep Learning v4.1 Routes
Handles LSTM, Transformer, CNN, Advanced RL, AutoML, and Backtesting endpoints
"""
from flask import Blueprint, jsonify, request
from dataclasses import asdict
import numpy as np
from datetime import datetime, timedelta
from .common import get_bot_instance

# Create blueprint
deep_learning_bp = Blueprint('deep_learning', __name__)


# ============================================================================
# Deep Learning v4.1 - LSTM, Transformer, CNN, Advanced RL, AutoML, Backtesting
# ============================================================================

@deep_learning_bp.route('/api/v4.1/deep_learning/predict/<stock_code>')
def get_deep_learning_prediction(stock_code: str):
    """Get deep learning prediction (LSTM + Transformer + CNN) - Currently disabled"""
    return jsonify({
        'success': False,
        'message': 'Deep Learning 기능은 현재 비활성화되었습니다. PyTorch 환경 구축 후 사용 가능합니다.',
        'prediction': None
    })


@deep_learning_bp.route('/api/v4.1/advanced_rl/action')
def get_advanced_rl_action():
    """Get action from advanced RL algorithms (A3C, PPO, SAC)"""
    try:
        from ai.advanced_rl import get_advanced_rl_manager
        import numpy as np
        from dataclasses import asdict

        manager = get_advanced_rl_manager()

        # Mock state
        state = np.random.randn(15)

        # Get algorithm from query params
        algorithm = request.args.get('algorithm', None)

        action = manager.get_action(state, algorithm)

        return jsonify({
            'success': True,
            'action': asdict(action)
        })
    except Exception as e:
        print(f"Advanced RL action error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@deep_learning_bp.route('/api/v4.1/advanced_rl/performance')
def get_advanced_rl_performance():
    """Get performance metrics for all RL algorithms"""
    try:
        from ai.advanced_rl import get_advanced_rl_manager

        manager = get_advanced_rl_manager()
        performance = manager.get_all_performances()

        return jsonify({
            'success': True,
            'performance': performance
        })
    except Exception as e:
        print(f"Advanced RL performance error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@deep_learning_bp.route('/api/v4.1/automl/optimize', methods=['POST'])
def run_automl_optimization():
    """Run AutoML optimization"""
    try:
        from ai.automl import get_automl_manager
        from dataclasses import asdict
        import numpy as np

        # Get parameters from request
        data = request.get_json() or {}
        model_types = data.get('model_types', ['random_forest', 'xgboost'])
        optimization_method = data.get('method', 'bayesian')
        n_trials = data.get('n_trials', 30)

        manager = get_automl_manager()

        # Mock data for demo
        X = np.random.randn(100, 5)
        y = np.random.randn(100)

        result = manager.auto_optimize(
            X=X,
            y=y,
            model_types=model_types,
            optimization_method=optimization_method,
            n_trials=n_trials
        )

        # Convert dataclasses to dict
        result_dict = asdict(result)

        return jsonify({
            'success': True,
            'result': result_dict
        })
    except Exception as e:
        print(f"AutoML optimization error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@deep_learning_bp.route('/api/v4.1/automl/history')
def get_automl_history():
    """Get AutoML optimization history"""
    try:
        from ai.automl import get_automl_manager
        from dataclasses import asdict

        manager = get_automl_manager()
        history = manager.get_optimization_history()

        history_dicts = [asdict(h) for h in history]

        return jsonify({
            'success': True,
            'history': history_dicts
        })
    except Exception as e:
        print(f"AutoML history error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@deep_learning_bp.route('/api/v4.1/backtest/run', methods=['POST'])
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
        return jsonify({'success': False, 'message': str(e)})


@deep_learning_bp.route('/api/v4.1/all/status')
def get_all_ai_status():
    """Get comprehensive status of all v4.1 AI systems - Currently disabled"""
    return jsonify({
        'success': False,
        'message': 'Advanced AI 기능들은 현재 비활성화되었습니다. Gemini AI 분석기를 사용하세요.',
        'deep_learning': None,
        'advanced_rl': None,
        'automl': None,
        'version': '4.1 (disabled)'
    })
