"""
dashboard/routes/virtual_trading.py
가상매매 API 엔드포인트
"""
import logging
from flask import Blueprint, jsonify, request
from utils.response_helper import error_response
from virtual_trading import VirtualTradingManager

logger = logging.getLogger(__name__)

# Blueprint 생성
virtual_trading_bp = Blueprint('virtual_trading', __name__)

# 가상매매 매니저 인스턴스 (전역 변수)
virtual_manager: VirtualTradingManager = None
_bot_instance = None


def init_virtual_trading_manager(bot=None, db_path: str = "data/virtual_trading.db"):
    """
    가상매매 매니저 초기화

    Args:
        bot: Bot instance with data_fetcher
        db_path: SQLite 데이터베이스 파일 경로
    """
    global virtual_manager, _bot_instance
    virtual_manager = VirtualTradingManager(db_path)
    _bot_instance = bot

    if bot and hasattr(bot, 'data_fetcher'):
        logger.info("✅ 가상매매 매니저 초기화 완료 (DataFetcher 사용 가능)")
    else:
        logger.warning("⚠️ 가상매매 매니저 초기화 완료 (DataFetcher 없음 - 일부 기능 제한)")


def _get_data_fetcher():
    """
    DataFetcher 가져오기 (없으면 생성)

    Returns:
        DataFetcher instance or None
    """
    # 1차: bot_instance에서 가져오기
    if _bot_instance and hasattr(_bot_instance, 'data_fetcher'):
        logger.info("✅ DataFetcher: bot_instance에서 가져옴")
        return _bot_instance.data_fetcher

    # 2차: 새로 생성 시도 (config 파일에서 API 정보 읽기)
    try:
        import yaml
        import os
        from pathlib import Path
        from research import DataFetcher
        from core import KiwoomRESTClient

        logger.info("DataFetcher 없음 - 새로 생성 시도 중...")

        # config.yaml 파일에서 설정 읽기
        config_path = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'

        if not config_path.exists():
            logger.warning(f"⚠️ config.yaml 파일이 없음: {config_path}")
            logger.info("Fallback: 환경 변수에서 API 정보 읽기 시도...")

            # 환경 변수에서 읽기
            api_url = os.getenv('KIWOOM_REST_URL')
            api_key = os.getenv('KIWOOM_API_KEY')
            api_secret = os.getenv('KIWOOM_API_SECRET')

            if not all([api_url, api_key, api_secret]):
                logger.error("❌ 환경 변수에도 API 정보가 없습니다")
                return None

            client = KiwoomRESTClient(
                base_url=api_url,
                api_key=api_key,
                api_secret=api_secret
            )
        else:
            # config 파일에서 읽기
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # secrets.json에서 API 정보 읽기
            secrets_path = Path(__file__).parent.parent.parent / '_immutable' / 'credentials' / 'secrets.json'

            if not secrets_path.exists():
                logger.error(f"❌ secrets.json 파일이 없음: {secrets_path}")
                return None

            import json
            with open(secrets_path, 'r', encoding='utf-8') as f:
                secrets = json.load(f)

            kiwoom_config = secrets.get('kiwoom', {})
            api_url = kiwoom_config.get('rest_url')
            api_key = kiwoom_config.get('api_key')
            api_secret = kiwoom_config.get('api_secret')

            if not all([api_url, api_key, api_secret]):
                logger.error("❌ secrets.json에 Kiwoom API 정보가 없습니다")
                return None

            logger.info(f"✅ API 정보 로드 완료: {api_url}")
            client = KiwoomRESTClient(
                base_url=api_url,
                api_key=api_key,
                api_secret=api_secret
            )

        # DataFetcher 생성
        data_fetcher = DataFetcher(client)
        logger.info("✅ DataFetcher 생성 완료")
        return data_fetcher

    except Exception as e:
        logger.error(f"❌ DataFetcher 생성 실패: {e}", exc_info=True)
        logger.info("💡 Tip: config/config.yaml과 _immutable/credentials/secrets.json을 확인하세요")
        return None


@virtual_trading_bp.route('/api/virtual-trading/strategies', methods=['GET'])
def get_strategies():
    """모든 가상매매 전략 조회"""
    try:
        if not virtual_manager:
            return jsonify({'error': '가상매매 매니저가 초기화되지 않았습니다'}), 500

        strategies_list = virtual_manager.get_strategy_summary()

        # JavaScript가 기대하는 형식으로 변환 (리스트 -> 딕셔너리)
        strategies_dict = {}
        for strategy in strategies_list:
            name = strategy.get('name', f"전략{strategy.get('id', '?')}")
            strategies_dict[name] = {
                'id': strategy.get('id'),
                'return': round((strategy.get('current_capital', 0) - strategy.get('initial_capital', 0)) / strategy.get('initial_capital', 1) * 100, 2) if strategy.get('initial_capital') else 0,
                'capital': strategy.get('current_capital', 0),
                'trades': 0,  # TODO: 실제 거래 수 계산
                'status': 'active' if strategy.get('is_active') else 'inactive'
            }

        return jsonify({
            'success': True,
            'strategies': strategies_dict
        })

    except Exception as e:
        logger.error(f"전략 조회 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/strategies', methods=['POST'])
def create_strategy():
    """새로운 가상매매 전략 생성"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        data = request.json
        name = data.get('name')
        description = data.get('description', '')
        initial_capital = data.get('initial_capital', 10000000)

        if not name:
            return error_response('전략 이름이 필요합니다', status=400)

        strategy_id = virtual_manager.create_strategy(
            name=name,
            description=description,
            initial_capital=initial_capital
        )

        return jsonify({
            'success': True,
            'strategy_id': strategy_id,
            'message': f'전략 "{name}" 생성 완료'
        })

    except Exception as e:
        logger.error(f"전략 생성 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/strategies/<int:strategy_id>', methods=['GET'])
def get_strategy_detail(strategy_id: int):
    """특정 전략의 상세 정보 조회"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        # 전략 기본 정보
        strategies = virtual_manager.get_strategy_summary(strategy_id)
        if not strategies:
            return error_response('전략을 찾을 수 없습니다', status=404)

        strategy = strategies[0]

        # 성과 지표
        metrics = virtual_manager.get_performance_metrics(strategy_id)

        # 포지션 정보
        positions = virtual_manager.get_positions(strategy_id)

        # 거래 내역
        trades = virtual_manager.get_trade_history(strategy_id, limit=20)

        return jsonify({
            'success': True,
            'strategy': strategy,
            'metrics': metrics,
            'positions': positions,
            'recent_trades': trades
        })

    except Exception as e:
        logger.error(f"전략 상세 조회 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/strategies/<int:strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id: int):
    """가상매매 전략 삭제"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        success = virtual_manager.delete_strategy(strategy_id)

        if success:
            return jsonify({
                'success': True,
                'message': f'전략 #{strategy_id} 삭제 완료'
            })
        else:
            return jsonify({
                'success': False,
                'error': '전략 삭제 실패 (활성 포지션이 있거나 오류 발생)'
            }), 400

    except Exception as e:
        logger.error(f"전략 삭제 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/positions', methods=['GET'])
def get_positions():
    """활성 포지션 조회"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        strategy_id = request.args.get('strategy_id', type=int)
        positions = virtual_manager.get_positions(strategy_id)

        return jsonify({
            'success': True,
            'positions': positions
        })

    except Exception as e:
        logger.error(f"포지션 조회 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/trades', methods=['GET'])
def get_trades():
    """거래 내역 조회"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        strategy_id = request.args.get('strategy_id', type=int)
        limit = request.args.get('limit', type=int, default=50)

        trades = virtual_manager.get_trade_history(strategy_id, limit)

        return jsonify({
            'success': True,
            'trades': trades
        })

    except Exception as e:
        logger.error(f"거래 내역 조회 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/buy', methods=['POST'])
def execute_buy():
    """가상매매 매수 주문 실행"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        data = request.json
        strategy_id = data.get('strategy_id')
        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        quantity = data.get('quantity')
        price = data.get('price')
        stop_loss_percent = data.get('stop_loss_percent')
        take_profit_percent = data.get('take_profit_percent')

        # 필수 파라미터 검증
        if not all([strategy_id, stock_code, stock_name, quantity, price]):
            return error_response('필수 파라미터가 누락되었습니다', status=400)

        position_id = virtual_manager.execute_buy(
            strategy_id=strategy_id,
            stock_code=stock_code,
            stock_name=stock_name,
            quantity=quantity,
            price=price,
            stop_loss_percent=stop_loss_percent,
            take_profit_percent=take_profit_percent
        )

        if position_id:
            return jsonify({
                'success': True,
                'position_id': position_id,
                'message': f'{stock_name} {quantity}주 매수 완료'
            })
        else:
            return error_response('매수 주문 실행 실패', status=500)

    except Exception as e:
        logger.error(f"매수 주문 실행 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/sell', methods=['POST'])
def execute_sell():
    """가상매매 매도 주문 실행"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        data = request.json
        position_id = data.get('position_id')
        sell_price = data.get('sell_price')
        reason = data.get('reason', 'manual')

        # 필수 파라미터 검증
        if not all([position_id, sell_price]):
            return error_response('필수 파라미터가 누락되었습니다', status=400)

        profit = virtual_manager.execute_sell(
            position_id=position_id,
            sell_price=sell_price,
            reason=reason
        )

        if profit is not None:
            return jsonify({
                'success': True,
                'profit': profit,
                'message': f'매도 완료 (수익: {profit:+,.0f}원)'
            })
        else:
            return error_response('매도 주문 실행 실패', status=500)

    except Exception as e:
        logger.error(f"매도 주문 실행 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/prices', methods=['POST'])
def update_prices():
    """종목 현재가 업데이트"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        data = request.json
        price_updates = data.get('prices', {})

        if not price_updates:
            return error_response('가격 정보가 누락되었습니다', status=400)

        virtual_manager.update_prices(price_updates)

        return jsonify({
            'success': True,
            'message': f'{len(price_updates)}개 종목 가격 업데이트 완료'
        })

    except Exception as e:
        logger.error(f"가격 업데이트 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/check-conditions', methods=['POST'])
def check_conditions():
    """손절/익절 조건 체크 및 자동 매도 실행"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        executed_orders = virtual_manager.check_stop_loss_take_profit()

        return jsonify({
            'success': True,
            'executed_orders': executed_orders,
            'count': len(executed_orders)
        })

    except Exception as e:
        logger.error(f"조건 체크 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/performance/<int:strategy_id>', methods=['GET'])
def get_performance(strategy_id: int):
    """전략 성과 지표 조회"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        metrics = virtual_manager.get_performance_metrics(strategy_id)

        if not metrics:
            return error_response('전략을 찾을 수 없습니다', status=404)

        return jsonify({
            'success': True,
            'metrics': metrics
        })

    except Exception as e:
        logger.error(f"성과 지표 조회 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/backtest', methods=['POST'])
def run_backtest():
    """백테스팅 실행 (과거 데이터로 전략 검증)"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        data = request.json
        strategy_id = data.get('strategy_id')
        stock_code = data.get('stock_code')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        stop_loss_percents = data.get('stop_loss_percents', [3.0, 5.0, 7.0])
        take_profit_percents = data.get('take_profit_percents', [5.0, 10.0, 15.0])

        # 필수 파라미터 검증
        if not all([strategy_id, stock_code, start_date, end_date]):
            return error_response('필수 파라미터가 누락되었습니다', status=400)

        # BacktestAdapter 임포트 및 실행
        from virtual_trading import BacktestAdapter

        # data_fetcher 가져오기 (없으면 생성)
        data_fetcher = _get_data_fetcher()
        if not data_fetcher:
            return error_response('DataFetcher를 사용할 수 없습니다. API 연결을 확인하세요.', status=500)

        adapter = BacktestAdapter(
            virtual_manager=virtual_manager,
            data_fetcher=data_fetcher
        )

        result = adapter.run_backtest(
            strategy_id=strategy_id,
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            stop_loss_percents=stop_loss_percents,
            take_profit_percents=take_profit_percents
        )

        if 'error' in result:
            return error_response(result['error'], status=500)

        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        logger.error(f"백테스팅 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/backtest/apply', methods=['POST'])
def apply_backtest_result():
    """백테스팅 최적 조건을 전략에 적용"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        data = request.json
        strategy_id = data.get('strategy_id')
        backtest_result = data.get('backtest_result')

        if not all([strategy_id, backtest_result]):
            return error_response('필수 파라미터가 누락되었습니다', status=400)

        from virtual_trading import BacktestAdapter

        data_fetcher = _get_data_fetcher()
        if not data_fetcher:
            return error_response('DataFetcher를 사용할 수 없습니다. API 연결을 확인하세요.', status=500)

        adapter = BacktestAdapter(
            virtual_manager=virtual_manager,
            data_fetcher=data_fetcher
        )

        success = adapter.apply_best_conditions(strategy_id, backtest_result)

        if success:
            return jsonify({
                'success': True,
                'message': '최적 조건이 적용되었습니다',
                'recommendation': backtest_result.get('recommendation', {})
            })
        else:
            return error_response('최적 조건 적용 실패', status=500)

    except Exception as e:
        logger.error(f"백테스팅 조건 적용 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


# AI 자동 전략 관리 API

@virtual_trading_bp.route('/api/virtual-trading/ai/initialize', methods=['POST'])
def ai_initialize_strategies():
    """AI가 5가지 전략을 자동 생성"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        data_fetcher = _get_data_fetcher()
        if not data_fetcher:
            return error_response('DataFetcher를 사용할 수 없습니다. API 연결을 확인하세요.', status=500)

        from virtual_trading import AIStrategyManager

        ai_manager = AIStrategyManager(virtual_manager, data_fetcher)

        data = request.json or {}
        initial_capital = data.get('initial_capital', 10000000)

        strategy_ids = ai_manager.initialize_strategies(initial_capital)

        return jsonify({
            'success': True,
            'strategy_ids': strategy_ids,
            'message': f'AI가 5가지 전략을 자동 생성했습니다'
        })

    except Exception as e:
        logger.error(f"AI 전략 초기화 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/ai/review', methods=['POST'])
def ai_review_strategies():
    """AI가 전략 성과를 자동 검토"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        data_fetcher = _get_data_fetcher()
        if not data_fetcher:
            return error_response('DataFetcher를 사용할 수 없습니다. API 연결을 확인하세요.', status=500)

        from virtual_trading import AIStrategyManager

        ai_manager = AIStrategyManager(virtual_manager, data_fetcher)

        # 모든 전략 가져오기
        strategies = virtual_manager.get_strategy_summary()
        ai_manager.active_strategy_ids = [s['strategy_id'] for s in strategies]

        review_result = ai_manager.review_strategies()

        return jsonify({
            'success': True,
            'result': review_result
        })

    except Exception as e:
        logger.error(f"AI 전략 검토 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/ai/improve', methods=['POST'])
def ai_improve_strategies():
    """AI가 전략을 자동 개선"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        data_fetcher = _get_data_fetcher()
        if not data_fetcher:
            return error_response('DataFetcher를 사용할 수 없습니다. API 연결을 확인하세요.', status=500)

        from virtual_trading import AIStrategyManager

        ai_manager = AIStrategyManager(virtual_manager, data_fetcher)

        # 모든 전략 가져오기
        strategies = virtual_manager.get_strategy_summary()
        ai_manager.active_strategy_ids = [s['strategy_id'] for s in strategies]

        data = request.json or {}
        backtest_period_days = data.get('backtest_period_days', 90)

        improvement_result = ai_manager.improve_strategies(backtest_period_days)

        return jsonify({
            'success': True,
            'result': improvement_result
        })

    except Exception as e:
        logger.error(f"AI 전략 개선 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)


@virtual_trading_bp.route('/api/virtual-trading/ai/auto-manage', methods=['POST'])
def ai_auto_manage():
    """AI가 전략을 자동 관리 (검토 → 개선 → 추천)"""
    try:
        if not virtual_manager:
            return error_response('가상매매 매니저가 초기화되지 않았습니다', status=500)

        data_fetcher = _get_data_fetcher()
        if not data_fetcher:
            return error_response('DataFetcher를 사용할 수 없습니다. API 연결을 확인하세요.', status=500)

        from virtual_trading import AIStrategyManager

        ai_manager = AIStrategyManager(virtual_manager, data_fetcher)

        # 모든 전략 가져오기
        strategies = virtual_manager.get_strategy_summary()
        ai_manager.active_strategy_ids = [s['strategy_id'] for s in strategies]

        manage_result = ai_manager.auto_manage_strategies()

        return jsonify({
            'success': True,
            'result': manage_result
        })

    except Exception as e:
        logger.error(f"AI 자동 관리 실패: {e}", exc_info=True)
        return error_response(str(e), status=500)
