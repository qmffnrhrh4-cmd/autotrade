"""AI Mode API Routes"""
from flask import Blueprint, jsonify, request
from dataclasses import asdict
from .common import get_bot_instance

ai_mode_bp = Blueprint('ai_mode', __name__)


@ai_mode_bp.route('/api/ai/status')
def get_ai_status():
    try:
        from features.ai_mode import get_ai_agent

        bot = get_bot_instance()
        agent = get_ai_agent(bot)
        data = agent.get_dashboard_data()
        return jsonify(data)
    except Exception as e:
        print(f"AI status API error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@ai_mode_bp.route('/api/ai/toggle', methods=['POST'])
def toggle_ai_mode():
    try:
        from features.ai_mode import get_ai_agent

        data = request.json
        enable = data.get('enable', False)

        bot = get_bot_instance()
        agent = get_ai_agent(bot)

        if enable:
            agent.enable_ai_mode()
            message = 'AI 모드 활성화됨 - 자율 트레이딩 시작'
        else:
            agent.disable_ai_mode()
            message = 'AI 모드 비활성화됨 - 수동 제어로 전환'

        return jsonify({
            'success': True,
            'enabled': agent.is_enabled(),
            'message': message
        })
    except Exception as e:
        print(f"AI toggle API error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@ai_mode_bp.route('/api/ai/decision/<stock_code>')
def get_ai_decision(stock_code: str):
    try:
        from features.ai_mode import get_ai_agent

        bot = get_bot_instance()
        stock_name = stock_code
        stock_data = {
            'current_price': 0,
            'rsi': 50,
            'volume_ratio': 1.0,
            'total_score': 0
        }

        if bot and hasattr(bot, 'market_api'):
            try:
                price_info = bot.market_api.get_current_price(stock_code)
                if price_info:
                    stock_data['current_price'] = int(price_info.get('prpr', 0))
                    stock_name = price_info.get('prdt_name', stock_code)
            except:
                pass

        agent = get_ai_agent(bot)
        decision = agent.make_trading_decision(stock_code, stock_name, stock_data)

        return jsonify({
            'success': True,
            'decision': asdict(decision)
        })
    except Exception as e:
        print(f"AI decision API error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@ai_mode_bp.route('/api/ai/learning/summary')
def get_ai_learning_summary():
    try:
        from features.ai_learning import AILearningEngine

        engine = AILearningEngine()
        summary = engine.get_learning_summary()

        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        print(f"AI learning API error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@ai_mode_bp.route('/api/ai/optimize', methods=['POST'])
def trigger_ai_optimization():
    try:
        from features.ai_mode import get_ai_agent

        bot = get_bot_instance()
        agent = get_ai_agent(bot)
        agent.optimize_parameters()

        return jsonify({
            'success': True,
            'message': 'AI 자기 최적화 완료',
            'performance': asdict(agent.performance)
        })
    except Exception as e:
        print(f"AI optimization API error: {e}")
        return jsonify({'success': False, 'message': str(e)})
