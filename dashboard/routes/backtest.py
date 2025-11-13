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

        # 기본 백테스트 종목: 코스피 대형주 15개
        default_stocks = [
            '005930',  # 삼성전자
            '000660',  # SK하이닉스
            '373220',  # LG에너지솔루션
            '207940',  # 삼성바이오로직스
            '005380',  # 현대차
            '051910',  # LG화학
            '006400',  # 삼성SDI
            '035420',  # NAVER
            '000270',  # 기아
            '105560',  # KB금융
            '055550',  # 신한지주
            '035720',  # 카카오
            '068270',  # 셀트리온
            '012330',  # 현대모비스
            '028260',  # 삼성물산
        ]

        # 포트폴리오 종목 동적으로 가져오기
        portfolio_stocks = []
        if _bot_instance and hasattr(_bot_instance, 'account_manager'):
            try:
                # 계좌 보유 종목 조회
                positions = _bot_instance.account_manager.get_positions()
                if positions:
                    for stock_code, position in positions.items():
                        # 종목 코드에서 'A' 제거 (A005930 → 005930)
                        clean_code = stock_code.replace('A', '')
                        if clean_code not in default_stocks:  # 중복 방지
                            portfolio_stocks.append(clean_code)
                    logger.info(f"포트폴리오 종목 추가: {len(portfolio_stocks)}개")
            except Exception as e:
                logger.warning(f"포트폴리오 종목 조회 실패: {e}")

        # 대형주 + 포트폴리오 종목 합치기
        default_stocks_with_portfolio = default_stocks + portfolio_stocks

        # stock_codes 처리: 빈 배열이면 기본값 사용
        stock_codes_from_request = data.get('stock_codes')
        if stock_codes_from_request is None or (isinstance(stock_codes_from_request, list) and len(stock_codes_from_request) == 0):
            stock_codes = default_stocks_with_portfolio
            logger.info(f"📊 종목 코드 없음 → 기본값 사용: 대형주 {len(default_stocks)}개 + 포트폴리오 {len(portfolio_stocks)}개 = 총 {len(stock_codes)}개")
        else:
            stock_codes = stock_codes_from_request
            logger.info(f"📊 사용자 지정 종목: {len(stock_codes)}개")

        start_date = data.get('start_date')
        end_date = data.get('end_date')
        interval = data.get('interval', '5')
        parallel = data.get('parallel', True)

        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')  # 90일로 확대
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')

        logger.info(f"🎯 백테스트 실행: {len(stock_codes)}개 종목, {start_date} ~ {end_date}")
        logger.info(f"   종목 목록: {stock_codes[:5]}{'...' if len(stock_codes) > 5 else ''}")

        results = _backtester.run_backtest(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            parallel=parallel
        )

        response_data = {}
        for strategy_name, result in results.items():
            # 전략 조건 정보 가져오기
            strategy_info = None
            if _backtester and hasattr(_backtester, 'strategies'):
                for strat in _backtester.strategies:
                    if strat.name == strategy_name:
                        strategy_info = {
                            'name': strat.name,
                            'description': getattr(strat, 'description', '전략 설명 없음'),
                            'buy_conditions': getattr(strat, 'buy_conditions', '매수 조건 정보 없음'),
                            'sell_conditions': getattr(strat, 'sell_conditions', '매도 조건 정보 없음'),
                            'parameters': getattr(strat, 'parameters', {})
                        }
                        break

            # 거래 내역에 더 상세한 정보 추가
            detailed_trades = []
            for trade in result.trades[:100]:  # 최대 100개
                # Fix: datetime 사용 시 안전하게 처리
                buy_price = trade.get('buy_price', 0)
                sell_price = trade.get('sell_price', 0)
                profit_pct = ((sell_price - buy_price) / buy_price * 100) if buy_price > 0 else 0

                # Fix: 날짜 계산 안전하게 처리
                holding_days = 0
                try:
                    sell_date = trade.get('sell_date')
                    buy_date = trade.get('buy_date')
                    if sell_date and buy_date:
                        from datetime import datetime as dt
                        sell_dt = dt.strptime(str(sell_date), '%Y%m%d')
                        buy_dt = dt.strptime(str(buy_date), '%Y%m%d')
                        holding_days = (sell_dt - buy_dt).days
                except:
                    holding_days = 0

                detailed_trades.append({
                    **trade,  # 기존 정보 유지
                    'profit_pct': profit_pct,
                    'holding_days': holding_days,
                })

            response_data[strategy_name] = {
                'strategy_name': result.strategy_name,
                'strategy_info': strategy_info,  # 전략 조건 정보 추가
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

                # 거래 통계 추가
                'avg_holding_days': sum(t['holding_days'] for t in detailed_trades) / len(detailed_trades) if detailed_trades else 0,
                'best_trade': max(detailed_trades, key=lambda t: t.get('profit', 0)) if detailed_trades else None,
                'worst_trade': min(detailed_trades, key=lambda t: t.get('profit', 0)) if detailed_trades else None,

                'daily_returns': result.daily_returns,
                'daily_cash': result.daily_cash,
                'daily_dates': result.daily_dates,

                'trades': detailed_trades,  # 상세 거래 내역
            }

        ranking = _backtester.get_ranking(results)
        best_strategy = _backtester.get_best_strategy(results)

        # 백테스트 요약 정보 생성
        total_trades_all = sum(result.total_trades for result in results.values())
        avg_return = sum(result.total_return_pct for result in results.values()) / len(results) if results else 0
        avg_win_rate = sum(result.win_rate for result in results.values()) / len(results) if results else 0

        # 기간 계산
        from datetime import datetime
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        period_days = (end_dt - start_dt).days

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
                'interval': interval,
                'period_days': period_days,
                'stock_count': len(stock_codes)
            },
            'summary': {
                'total_strategies_tested': len(results),
                'total_trades_all_strategies': total_trades_all,
                'average_return': avg_return,
                'average_win_rate': avg_win_rate,
                'test_period': f"{start_date} ~ {end_date} ({period_days}일)",
                'tested_stocks': ', '.join(stock_codes),
                'description': f"{len(results)}개 전략으로 {len(stock_codes)}개 종목을 {period_days}일 동안 테스트 (총 {total_trades_all}회 거래)"
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
