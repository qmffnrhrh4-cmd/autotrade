from flask import Blueprint, jsonify, request
from datetime import datetime
from .common import get_bot_instance

auto_analysis_bp = Blueprint('auto_analysis', __name__)


@auto_analysis_bp.route('/api/ai/portfolio-optimization')
def get_portfolio_optimization():
    try:
        optimization = {
            'status': 'optimal',
            'risk_level': 'low',
            'concentration_warning': False,
            'rebalance_needed': False,
            'suggestions': [],
            'sharpe_ratio': 0,
            'value_at_risk': 0,
            'max_drawdown': 0,
            'efficiency_score': 0,
            'portfolio_beta': 1.0,
        }

        bot_instance = get_bot_instance()
        if bot_instance and hasattr(bot_instance, 'account_api'):
            try:
                holdings = bot_instance.account_api.get_holdings()

                if holdings and len(holdings) > 0:
                    total_value = sum(int(h.get('eval_amt', 0)) for h in holdings)
                    if total_value == 0:
                        total_value = sum(int(h.get('rmnd_qty', 0)) * int(h.get('cur_prc', 0)) for h in holdings)

                    total_profit = 0
                    total_invested = 0
                    stock_returns = []

                    weights = []
                    for h in holdings:
                        value = int(h.get('eval_amt', 0))
                        if value == 0:
                            value = int(h.get('rmnd_qty', 0)) * int(h.get('cur_prc', 0))

                        quantity = int(h.get('rmnd_qty', 0))
                        buy_price = int(h.get('pchs_avg_pric', 0))
                        current_price = int(h.get('cur_prc', 0))

                        weight = (value / total_value * 100) if total_value > 0 else 0
                        weights.append({
                            'name': h.get('stk_nm', ''),
                            'weight': round(weight, 2),
                            'value': value
                        })

                        if buy_price > 0 and quantity > 0:
                            invested = buy_price * quantity
                            profit = (current_price - buy_price) * quantity
                            stock_return = (profit / invested) * 100 if invested > 0 else 0

                            total_profit += profit
                            total_invested += invested
                            stock_returns.append(stock_return)

                    weights.sort(key=lambda x: x['weight'], reverse=True)

                    portfolio_return = (total_profit / total_invested * 100) if total_invested > 0 else 0

                    risk_free_rate = 2.0
                    if len(stock_returns) > 1:
                        import statistics
                        volatility = statistics.stdev(stock_returns)
                        sharpe_ratio = (portfolio_return - risk_free_rate) / volatility if volatility > 0 else 0
                        optimization['sharpe_ratio'] = round(sharpe_ratio, 2)

                    if len(stock_returns) > 1:
                        import statistics
                        daily_volatility = statistics.stdev(stock_returns) / 100
                        var_95 = total_value * 1.65 * daily_volatility
                        optimization['value_at_risk'] = int(var_95)
                    else:
                        optimization['value_at_risk'] = int(total_value * 0.05)

                    if len(stock_returns) > 1:
                        import statistics
                        portfolio_vol = statistics.stdev(stock_returns)
                        market_vol = 20.0
                        beta = portfolio_vol / market_vol if market_vol > 0 else 1.0
                        optimization['portfolio_beta'] = round(beta, 2)

                    efficiency_score = 50

                    num_stocks = len(holdings)
                    if num_stocks >= 5 and num_stocks <= 8:
                        efficiency_score += 20
                    elif num_stocks >= 3:
                        efficiency_score += 10

                    if optimization['sharpe_ratio'] > 2.0:
                        efficiency_score += 20
                    elif optimization['sharpe_ratio'] > 1.0:
                        efficiency_score += 15
                    elif optimization['sharpe_ratio'] > 0.5:
                        efficiency_score += 10

                    max_weight = weights[0]['weight'] if weights else 0
                    if max_weight > 40:
                        efficiency_score -= 20
                    elif max_weight > 30:
                        efficiency_score -= 10

                    if portfolio_return > 10:
                        efficiency_score += 10
                    elif portfolio_return > 5:
                        efficiency_score += 5

                    optimization['efficiency_score'] = max(0, min(100, efficiency_score))

                    if optimization['efficiency_score'] >= 80:
                        optimization['suggestions'].insert(0, {
                            'type': 'success',
                            'title': '우수한 포트폴리오',
                            'message': f'포트폴리오 효율성: {optimization["efficiency_score"]}점. 잘 구성된 포트폴리오입니다.',
                            'action': '현 상태 유지'
                        })
                    elif optimization['efficiency_score'] < 50:
                        optimization['suggestions'].insert(0, {
                            'type': 'warning',
                            'title': '포트폴리오 개선 필요',
                            'message': f'포트폴리오 효율성: {optimization["efficiency_score"]}점. 구조 개선이 필요합니다.',
                            'action': '리밸런싱 권장'
                        })

                    max_weight = weights[0]['weight'] if weights else 0
                    top3_weight = sum(w['weight'] for w in weights[:3]) if len(weights) >= 3 else 0

                    if max_weight > 40:
                        optimization['concentration_warning'] = True
                        optimization['risk_level'] = 'high'
                        optimization['status'] = 'needs_attention'
                        optimization['suggestions'].append({
                            'type': 'warning',
                            'title': '과도한 집중도',
                            'message': f'{weights[0]["name"]} 비중이 {max_weight:.1f}%로 과도합니다. 30% 이하로 조정 권장.',
                            'action': f'{weights[0]["name"]} 일부 매도'
                        })
                    elif max_weight > 30:
                        optimization['risk_level'] = 'medium'
                        optimization['suggestions'].append({
                            'type': 'info',
                            'title': '집중도 주의',
                            'message': f'{weights[0]["name"]} 비중이 {max_weight:.1f}%입니다. 모니터링 필요.',
                            'action': '신규 종목 추가 고려'
                        })

                    if len(holdings) < 3:
                        optimization['suggestions'].append({
                            'type': 'warning',
                            'title': '분산 투자 부족',
                            'message': f'현재 {len(holdings)}개 종목만 보유 중입니다. 최소 5개 이상 권장.',
                            'action': '추가 종목 투자로 분산'
                        })
                    elif len(holdings) < 5:
                        optimization['suggestions'].append({
                            'type': 'info',
                            'title': '분산 투자 개선',
                            'message': f'현재 {len(holdings)}개 종목 보유. 5-8개가 적정.',
                            'action': '2-3개 종목 추가 고려'
                        })

                    if top3_weight > 70:
                        optimization['suggestions'].append({
                            'type': 'warning',
                            'title': '상위 3종목 집중도 높음',
                            'message': f'상위 3종목이 {top3_weight:.1f}% 차지. 60% 이하 권장.',
                            'action': '나머지 종목 비중 확대'
                        })

                    if max_weight > 35 or (len(holdings) >= 3 and top3_weight > 65):
                        optimization['rebalance_needed'] = True
                        optimization['suggestions'].append({
                            'type': 'action',
                            'title': '리밸런싱 필요',
                            'message': '포트폴리오 리밸런싱을 통해 리스크를 줄이세요.',
                            'action': '과비중 종목 일부 매도 후 저비중 종목 매수'
                        })

                    optimization['weights'] = weights[:5]
                    optimization['total_stocks'] = len(holdings)
                    optimization['max_weight'] = round(max_weight, 2)
                    optimization['top3_weight'] = round(top3_weight, 2)

            except Exception as e:
                print(f"Portfolio optimization error: {e}")
                import traceback
                traceback.print_exc()

        return jsonify({
            'success': True,
            'optimization': optimization
        })

    except Exception as e:
        print(f"Portfolio optimization API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@auto_analysis_bp.route('/api/ai/auto-stop-loss', methods=['POST'])
def execute_auto_stop_loss():
    try:
        bot_instance = get_bot_instance()
        if not bot_instance or not hasattr(bot_instance, 'account_api') or not hasattr(bot_instance, 'trading_api'):
            return jsonify({
                'success': False,
                'error': '봇 인스턴스가 초기화되지 않았습니다.'
            })

        data = request.get_json()
        enable = data.get('enable', False)
        threshold = data.get('threshold', -5)

        if not enable:
            return jsonify({
                'success': True,
                'message': '자동 손절이 비활성화되었습니다.',
                'executed': []
            })

        executed_orders = []
        holdings = bot_instance.account_api.get_holdings()

        for h in holdings:
            stock_code = h.get('stk_cd', '').replace('A', '')
            stock_name = h.get('stk_nm', '')
            quantity = int(h.get('rmnd_qty', 0))
            buy_price = int(h.get('pchs_avg_pric', 0))
            current_price = int(h.get('cur_prc', 0))

            if quantity == 0 or buy_price == 0:
                continue

            profit_pct = ((current_price - buy_price) / buy_price * 100)

            if profit_pct <= threshold:
                try:
                    order_result = bot_instance.trading_api.sell_market_order(
                        stock_code=stock_code,
                        quantity=quantity
                    )

                    executed_orders.append({
                        'stock': stock_name,
                        'code': stock_code,
                        'quantity': quantity,
                        'price': current_price,
                        'loss_pct': round(profit_pct, 2),
                        'order_result': order_result,
                        'timestamp': datetime.now().isoformat()
                    })

                    print(f"자동 손절 실행: {stock_name} {quantity}주 @ {current_price}원 ({profit_pct:.2f}%)")

                except Exception as e:
                    print(f"자동 손절 실패 ({stock_name}): {e}")

        return jsonify({
            'success': True,
            'message': f'{len(executed_orders)}건 자동 손절 실행',
            'executed': executed_orders
        })

    except Exception as e:
        print(f"Auto stop-loss error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'executed': []
        })


@auto_analysis_bp.route('/api/ai/auto-take-profit', methods=['POST'])
def execute_auto_take_profit():
    try:
        bot_instance = get_bot_instance()
        if not bot_instance or not hasattr(bot_instance, 'account_api') or not hasattr(bot_instance, 'trading_api'):
            return jsonify({
                'success': False,
                'error': '봇 인스턴스가 초기화되지 않았습니다.'
            })

        data = request.get_json()
        enable = data.get('enable', False)
        threshold = data.get('threshold', 15)
        sell_ratio = data.get('sell_ratio', 0.5)

        if not enable:
            return jsonify({
                'success': True,
                'message': '자동 익절이 비활성화되었습니다.',
                'executed': []
            })

        executed_orders = []
        holdings = bot_instance.account_api.get_holdings()

        for h in holdings:
            stock_code = h.get('stk_cd', '').replace('A', '')
            stock_name = h.get('stk_nm', '')
            quantity = int(h.get('rmnd_qty', 0))
            buy_price = int(h.get('pchs_avg_pric', 0))
            current_price = int(h.get('cur_prc', 0))

            if quantity == 0 or buy_price == 0:
                continue

            profit_pct = ((current_price - buy_price) / buy_price * 100)

            if profit_pct >= threshold:
                sell_quantity = int(quantity * sell_ratio)

                if sell_quantity > 0:
                    try:
                        order_result = bot_instance.trading_api.sell_market_order(
                            stock_code=stock_code,
                            quantity=sell_quantity
                        )

                        executed_orders.append({
                            'stock': stock_name,
                            'code': stock_code,
                            'quantity': sell_quantity,
                            'remaining': quantity - sell_quantity,
                            'price': current_price,
                            'profit_pct': round(profit_pct, 2),
                            'order_result': order_result,
                            'timestamp': datetime.now().isoformat()
                        })

                        print(f"자동 익절 실행: {stock_name} {sell_quantity}주 @ {current_price}원 ({profit_pct:.2f}%)")

                    except Exception as e:
                        print(f"자동 익절 실패 ({stock_name}): {e}")

        return jsonify({
            'success': True,
            'message': f'{len(executed_orders)}건 자동 익절 실행',
            'executed': executed_orders
        })

    except Exception as e:
        print(f"Auto take-profit error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'executed': []
        })


@auto_analysis_bp.route('/api/ai/alerts')
def get_ai_alerts():
    try:
        alerts = []

        bot_instance = get_bot_instance()
        if bot_instance and hasattr(bot_instance, 'account_api'):
            try:
                holdings = bot_instance.account_api.get_holdings()

                for h in holdings:
                    stock_name = h.get('stk_nm', '')
                    quantity = int(h.get('rmnd_qty', 0))
                    buy_price = int(h.get('pchs_avg_pric', 0))
                    current_price = int(h.get('cur_prc', 0))

                    if quantity == 0 or buy_price == 0:
                        continue

                    profit_pct = ((current_price - buy_price) / buy_price * 100)

                    if profit_pct <= -5:
                        alerts.append({
                            'type': 'stop_loss',
                            'severity': 'critical',
                            'stock': stock_name,
                            'message': f'{stock_name} {profit_pct:.1f}% 손실 - 즉시 손절 검토',
                            'action': '매도',
                            'color': '#ef4444'
                        })

                    elif profit_pct >= 15:
                        alerts.append({
                            'type': 'take_profit',
                            'severity': 'info',
                            'stock': stock_name,
                            'message': f'{stock_name} {profit_pct:.1f}% 수익 - 익절 고려',
                            'action': '일부 매도',
                            'color': '#10b981'
                        })

                    elif profit_pct <= -3:
                        alerts.append({
                            'type': 'warning',
                            'severity': 'warning',
                            'stock': stock_name,
                            'message': f'{stock_name} {profit_pct:.1f}% 손실 - 주의 관찰',
                            'action': '모니터링',
                            'color': '#f59e0b'
                        })

            except Exception as e:
                print(f"Alerts error: {e}")

        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        alerts.sort(key=lambda x: severity_order.get(x['severity'], 99))

        return jsonify({
            'success': True,
            'alerts': alerts[:10]
        })

    except Exception as e:
        print(f"AI alerts API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'alerts': []
        })


@auto_analysis_bp.route('/api/ai/auto-analysis')
def get_ai_auto_analysis():
    try:
        result = {
            'success': True,
            'portfolio': None,
            'sentiment': None,
            'risk': None,
            'consensus': None
        }

        bot_instance = get_bot_instance()
        if bot_instance and hasattr(bot_instance, 'account_api'):
            try:
                holdings = bot_instance.account_api.get_holdings()

                if holdings and len(holdings) > 0:
                    total_value = sum(int(h.get('eval_amt', 0)) for h in holdings)
                    if total_value == 0:
                        total_value = sum(int(h.get('rmnd_qty', 0)) * int(h.get('cur_prc', 0)) for h in holdings)

                    total_profit = 0
                    total_buy_value = 0

                    for h in holdings:
                        quantity = int(h.get('rmnd_qty', 0))
                        buy_price = int(h.get('pchs_avg_pric', 0))
                        current_price = int(h.get('cur_prc', 0))

                        if quantity > 0 and buy_price > 0:
                            profit = (current_price - buy_price) * quantity
                            total_profit += profit
                            total_buy_value += buy_price * quantity

                    profit_pct = (total_profit / total_buy_value * 100) if total_buy_value > 0 else 0

                    if profit_pct >= 15:
                        score = 9.0
                        health = '우수'
                    elif profit_pct >= 10:
                        score = 8.0
                        health = '양호'
                    elif profit_pct >= 5:
                        score = 7.0
                        health = '양호'
                    elif profit_pct >= 0:
                        score = 6.0
                        health = '보통'
                    elif profit_pct >= -5:
                        score = 5.0
                        health = '주의'
                    elif profit_pct >= -10:
                        score = 4.0
                        health = '경고'
                    else:
                        score = 3.0
                        health = '위험'

                    recommendations = []
                    if profit_pct < -5:
                        recommendations.append('손실 종목 점검 필요')
                    if len(holdings) < 3:
                        recommendations.append('분산 투자 확대 권장')
                    elif len(holdings) > 10:
                        recommendations.append('과도한 분산 - 집중 투자 고려')

                    if profit_pct > 10:
                        recommendations.append('수익 실현 타이밍 검토')

                    result['portfolio'] = {
                        'score': score,
                        'health': health,
                        'recommendations': recommendations if recommendations else ['현재 상태 유지']
                    }
                else:
                    result['portfolio'] = {
                        'score': 5.0,
                        'health': '보유 종목 없음',
                        'recommendations': ['종목 매수 필요']
                    }

            except Exception as e:
                print(f"Portfolio analysis error: {e}")
                import traceback
                traceback.print_exc()
                result['portfolio'] = {
                    'score': 5.0,
                    'health': '분석 오류',
                    'recommendations': ['데이터 확인 필요']
                }

            try:
                holdings = bot_instance.account_api.get_holdings()

                if holdings and len(holdings) > 0:
                    sentiment_scores = []
                    analyzed_stocks = []

                    for h in holdings[:5]:
                        stock_name = h.get('stk_nm', '')
                        stock_code = h.get('stk_cd', '').replace('A', '')

                        quantity = int(h.get('rmnd_qty', 0))
                        buy_price = int(h.get('pchs_avg_pric', 0))
                        current_price = int(h.get('cur_prc', 0))

                        if quantity > 0 and buy_price > 0:
                            profit_pct = ((current_price - buy_price) / buy_price * 100)

                            if profit_pct >= 10:
                                score = 0.8
                            elif profit_pct >= 5:
                                score = 0.7
                            elif profit_pct >= 0:
                                score = 0.6
                            elif profit_pct >= -5:
                                score = 0.4
                            else:
                                score = 0.3

                            sentiment_scores.append(score)
                            analyzed_stocks.append(stock_name)

                    if sentiment_scores:
                        avg_score = sum(sentiment_scores) / len(sentiment_scores)
                        overall_sentiment = avg_score * 10

                        if avg_score >= 0.6:
                            sentiment_status = '긍정적'
                        elif avg_score <= 0.4:
                            sentiment_status = '부정적'
                        else:
                            sentiment_status = '중립'

                        result['sentiment'] = {
                            'overall_sentiment': round(overall_sentiment, 2),
                            'sentiment': sentiment_status,
                            'overall_score': avg_score,
                            'count': len(sentiment_scores),
                            'status': sentiment_status,
                            'analyzed_stocks': analyzed_stocks,
                            'details': {
                                'positive_ratio': sum(1 for s in sentiment_scores if s > 0.5) / len(sentiment_scores),
                                'average': avg_score
                            }
                        }
                    else:
                        result['sentiment'] = {
                            'overall_sentiment': 5.0,
                            'sentiment': '중립',
                            'overall_score': 0.5,
                            'count': 0,
                            'status': '데이터 부족',
                            'analyzed_stocks': [],
                            'details': None
                        }
                else:
                    result['sentiment'] = {
                        'overall_sentiment': 5.0,
                        'sentiment': '중립',
                        'overall_score': 0.5,
                        'count': 0,
                        'status': '보유 종목 없음',
                        'analyzed_stocks': [],
                        'details': None
                    }
            except Exception as e:
                print(f"Sentiment analysis error: {e}")
                import traceback
                traceback.print_exc()
                result['sentiment'] = {
                    'overall_sentiment': 5.0,
                    'sentiment': '분석 오류',
                    'overall_score': 0.5,
                    'count': 0,
                    'status': '분석 오류',
                    'analyzed_stocks': [],
                    'error': str(e)
                }

            try:
                holdings = bot_instance.account_api.get_holdings()

                if holdings and len(holdings) > 0:
                    positions = []
                    total_value = sum(int(h.get('eval_amt', 0)) for h in holdings)

                    if total_value == 0:
                        for h in holdings:
                            qty = int(h.get('rmnd_qty', 0))
                            price = int(h.get('cur_prc', 0))
                            total_value += qty * price

                    for h in holdings:
                        code = h.get('stk_cd', '').replace('A', '')
                        value = int(h.get('eval_amt', 0))
                        if value == 0:
                            qty = int(h.get('rmnd_qty', 0))
                            price = int(h.get('cur_prc', 0))
                            value = qty * price

                        positions.append({
                            'code': code,
                            'name': h.get('stk_nm', ''),
                            'value': value,
                            'weight': (value / total_value * 100) if total_value > 0 else 0,
                            'sector': '기타'
                        })

                    max_weight = max([p['weight'] for p in positions]) if positions else 0

                    if max_weight > 50:
                        risk_level = '높음'
                        risk_score = 8
                        volatility = 25.0
                    elif max_weight > 30:
                        risk_level = '중간'
                        risk_score = 5
                        volatility = 18.0
                    else:
                        risk_level = '낮음'
                        risk_score = 3
                        volatility = 12.0

                    var = int(total_value * volatility / 100 * 1.65)
                    cvar = int(var * 1.3)

                    expected_return = 0.08
                    risk_free_rate = 0.03
                    sharpe_ratio = (expected_return - risk_free_rate) / (volatility / 100)

                    result['risk'] = {
                        'risk_level': risk_level,
                        'risk_score': risk_score,
                        'max_weight': max_weight,
                        'diversification': len(positions),
                        'total_value': total_value,
                        'positions': positions[:5],
                        'recommendation': f'{len(positions)}개 종목 보유 중, 최대 비중 {max_weight:.1f}%',
                        'var': var,
                        'cvar': cvar,
                        'volatility': volatility,
                        'sharpe_ratio': round(sharpe_ratio, 2),
                        'max_loss_pct': round(volatility * 0.6, 1)
                    }
                else:
                    result['risk'] = {
                        'risk_level': '없음',
                        'risk_score': 0,
                        'max_weight': 0,
                        'diversification': 0,
                        'total_value': 0,
                        'positions': [],
                        'recommendation': '보유 종목 없음',
                        'var': 0,
                        'cvar': 0,
                        'volatility': 0,
                        'sharpe_ratio': 0,
                        'max_loss_pct': 0
                    }
            except Exception as e:
                print(f"Risk analysis error: {e}")
                import traceback
                traceback.print_exc()
                result['risk'] = {
                    'risk_level': '분석 오류',
                    'risk_score': 0,
                    'max_weight': 0,
                    'diversification': 0,
                    'total_value': 0,
                    'positions': [],
                    'error': str(e),
                    'var': 0,
                    'cvar': 0,
                    'volatility': 0,
                    'sharpe_ratio': 0,
                    'max_loss_pct': 0
                }

            try:
                if result['portfolio'] and result['risk']:
                    portfolio_health = result['portfolio'].get('health', '보통')
                    risk_level = result['risk'].get('risk_level', '보통')
                    portfolio_score = result['portfolio'].get('score', 5)
                    risk_score = result['risk'].get('risk_score', 5)

                    if portfolio_score >= 7 and risk_level in ['낮음', '중간']:
                        final_action = 'BUY'
                        consensus_level = 0.85
                        confidence = 0.90
                        votes = {'buy': 4, 'sell': 0, 'hold': 1}
                    elif portfolio_score <= 3 or risk_level == '높음':
                        final_action = 'SELL'
                        consensus_level = 0.75
                        confidence = 0.80
                        votes = {'buy': 0, 'sell': 4, 'hold': 1}
                    else:
                        final_action = 'HOLD'
                        consensus_level = 0.70
                        confidence = 0.75
                        votes = {'buy': 1, 'sell': 1, 'hold': 3}

                    result['consensus'] = {
                        'final_action': final_action,
                        'consensus_level': consensus_level,
                        'confidence': confidence,
                        'votes': votes,
                        'status': f'{final_action} 추천',
                        'recommendation': f'포트폴리오 상태: {portfolio_health}, 리스크: {risk_level}'
                    }
                else:
                    result['consensus'] = {
                        'final_action': 'HOLD',
                        'consensus_level': 0.5,
                        'confidence': 0.5,
                        'votes': {'buy': 0, 'sell': 0, 'hold': 5},
                        'status': '데이터 부족',
                        'recommendation': '분석 데이터 부족으로 보류'
                    }
            except Exception as e:
                print(f"Consensus analysis error: {e}")
                result['consensus'] = {
                    'final_action': 'HOLD',
                    'consensus_level': 0.5,
                    'confidence': 0.5,
                    'votes': {'buy': 0, 'sell': 0, 'hold': 5},
                    'status': '분석 오류',
                    'recommendation': f'오류: {str(e)}'
                }

        return jsonify(result)

    except Exception as e:
        print(f"AI auto-analysis error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })
