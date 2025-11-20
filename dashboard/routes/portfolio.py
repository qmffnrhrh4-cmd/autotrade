"""
Portfolio Management Routes Module
Handles portfolio optimization, risk analysis, and performance tracking
"""
from datetime import datetime
from flask import Blueprint, jsonify, request
from utils.response_helper import error_response
from utils.logger_new import get_logger

logger = get_logger()

# Create Blueprint
portfolio_bp = Blueprint('portfolio', __name__)

# Module-level bot instance
_bot_instance = None

def set_bot_instance(bot):
    """Set the bot instance for this module"""
    global _bot_instance
    _bot_instance = bot


@portfolio_bp.route('/api/performance')
def get_performance():
    """Get performance history for chart from database"""
    data = []

    try:
        # 데이터베이스에서 포트폴리오 스냅샷 조회
        from database import get_db_session, PortfolioSnapshot
        from sqlalchemy import desc

        session = get_db_session()
        if session:
            # 최근 100개 스냅샷 조회 (최근 24시간 또는 그 이상)
            snapshots = session.query(PortfolioSnapshot)\
                .order_by(desc(PortfolioSnapshot.timestamp))\
                .limit(100)\
                .all()

            # 시간 순서로 정렬 (오래된 것부터)
            snapshots.reverse()

            for snapshot in snapshots:
                data.append({
                    'timestamp': int(snapshot.timestamp.timestamp() * 1000),
                    'value': snapshot.total_capital
                })

        # 데이터가 없으면 현재 계좌 정보로 단일 포인트 생성
        if not data:
            if _bot_instance and hasattr(_bot_instance, 'account_api'):
                try:
                    deposit = _bot_instance.account_api.get_deposit()
                    holdings = _bot_instance.account_api.get_holdings()

                    cash = int(deposit.get('ord_alow_amt', 0)) if deposit else 0
                    stock_value = sum(int(h.get('eval_amt', 0)) for h in holdings) if holdings else 0
                    total_assets = cash + stock_value

                    data.append({
                        'timestamp': int(datetime.now().timestamp() * 1000),
                        'value': total_assets
                    })
                except Exception as e:
                    print(f"Error getting current account for performance: {e}")

        # 여전히 데이터가 없으면 기본값
        if not data:
            data.append({
                'timestamp': int(datetime.now().timestamp() * 1000),
                'value': 0
            })

    except Exception as e:
        print(f"Error getting performance data: {e}")
        # 에러 발생시 현재 시간에 0 값
        data = [{
            'timestamp': int(datetime.now().timestamp() * 1000),
            'value': 0
        }]

    return jsonify(data)

@portfolio_bp.route('/api/portfolio/optimize')
def get_portfolio_optimization():
    """Get portfolio optimization analysis - v6.0.1 Fixed field names"""
    try:
        from features.portfolio_optimizer import PortfolioOptimizer

        if _bot_instance and hasattr(_bot_instance, 'account_api'):
            # v6.0.1: Use correct field names from kt00004 API
            holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT")

            if not holdings:
                return jsonify({
                    'success': True,
                    'status': '✅ 정상',
                    'risk': 'low',
                    'score': 100,
                    'message': '보유 종목이 없습니다.',
                    'suggestions': []
                })

            # Convert holdings to position format with CORRECT field names
            positions = []
            for h in holdings:
                code = str(h.get('stk_cd', '')).replace('A', '')  # stk_cd not pdno
                name = h.get('stk_nm', '')  # stk_nm not prdt_name
                quantity = int(str(h.get('rmnd_qty', 0)).replace(',', ''))  # rmnd_qty not hldg_qty
                avg_price = int(str(h.get('avg_prc', 0)).replace(',', ''))  # avg_prc not pchs_avg_pric
                current_price = int(str(h.get('cur_prc', 0)).replace(',', ''))  # cur_prc not prpr

                # Calculate value
                eval_amt = int(str(h.get('eval_amt', 0)).replace(',', ''))
                if eval_amt == 0:
                    eval_amt = quantity * current_price

                if quantity > 0 and current_price > 0:
                    positions.append({
                        'code': code,
                        'name': name,
                        'quantity': quantity,
                        'avg_price': avg_price,
                        'current_price': current_price,
                        'value': eval_amt
                    })

            if not positions:
                return jsonify({
                    'success': True,
                    'status': '✅ 정상',
                    'risk': 'low',
                    'score': 100,
                    'message': '보유 종목이 없습니다.',
                    'suggestions': []
                })

            optimizer = PortfolioOptimizer()
            result = optimizer.get_optimization_for_dashboard(positions)
            return jsonify(result)
        else:
            return error_response('Bot not initialized')
    except Exception as e:
        print(f"Portfolio optimization API error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e))

@portfolio_bp.route('/api/risk/analysis')
def get_risk_analysis():
    """Get portfolio risk analysis with correlation heatmap"""
    try:
        from strategy.advanced_risk_analytics import AdvancedRiskAnalytics as RiskAnalyzer

        if _bot_instance and hasattr(_bot_instance, 'account_api'):
            # v6.0.1: Fixed field names - use correct kt00004 API field names
            holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT")

            # Convert holdings to position format with sector info
            positions = []
            for h in holdings:
                # v6.0.1: Use correct field names from kt00004 API response
                code = str(h.get('stk_cd', '')).replace('A', '')  # stk_cd not pdno
                name = h.get('stk_nm', '')  # stk_nm not prdt_name
                quantity = int(str(h.get('rmnd_qty', 0)).replace(',', ''))

                if quantity <= 0:
                    continue

                # Calculate value
                eval_amt = int(str(h.get('eval_amt', 0)).replace(',', ''))
                current_price = int(str(h.get('cur_prc', 0)).replace(',', ''))
                if eval_amt == 0 and current_price > 0:
                    eval_amt = quantity * current_price

                positions.append({
                    'code': code,
                    'name': name,
                    'value': eval_amt,
                    'weight': 0,  # Will be calculated
                    'sector': '기타'  # Will be determined by analyzer
                })

            # Calculate weights
            total_value = sum(p['value'] for p in positions)
            for p in positions:
                p['weight'] = (p['value'] / total_value * 100) if total_value > 0 else 0

            analyzer = RiskAnalyzer()
            result = analyzer.get_risk_analysis_for_dashboard(positions)
            return jsonify(result)
        else:
            return error_response('Bot not initialized')
    except Exception as e:
        print(f"Risk analysis API error: {e}")
        return error_response(str(e))


@portfolio_bp.route('/api/portfolio/concentration')
def get_portfolio_concentration():
    """Get portfolio concentration analysis (diversification risk)"""
    try:
        if _bot_instance and hasattr(_bot_instance, 'account_api'):
            holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT")

            if not holdings:
                return jsonify({
                    'success': True,
                    'concentration_risk': 'low',
                    'hhi': 0,
                    'positions': [],
                    'max_position': None,
                    'recommendations': []
                })

            # Convert holdings to position format
            positions = []
            total_value = 0

            for h in holdings:
                code = str(h.get('stk_cd', '')).replace('A', '').replace('_NX', '')
                name = h.get('stk_nm', '')
                quantity = int(str(h.get('rmnd_qty', 0)).replace(',', ''))
                current_price = int(str(h.get('cur_prc', 0)).replace(',', ''))
                eval_amt = int(str(h.get('eval_amt', 0)).replace(',', ''))

                if eval_amt == 0:
                    eval_amt = quantity * current_price

                if quantity > 0:
                    positions.append({
                        'code': code,
                        'name': name,
                        'quantity': quantity,
                        'value': eval_amt
                    })
                    total_value += eval_amt

            # Calculate weights and HHI (Herfindahl-Hirschman Index)
            hhi = 0
            max_position = None
            max_weight = 0

            for pos in positions:
                weight = (pos['value'] / total_value * 100) if total_value > 0 else 0
                pos['weight'] = round(weight, 2)

                # HHI calculation (sum of squared weights)
                hhi += (weight / 100) ** 2

                if weight > max_weight:
                    max_weight = weight
                    max_position = {
                        'code': pos['code'],
                        'name': pos['name'],
                        'weight': weight,
                        'value': pos['value']
                    }

            # Determine concentration risk level
            # HHI ranges: 0-0.15 (low), 0.15-0.25 (medium), >0.25 (high)
            if hhi < 0.15:
                risk_level = 'low'
                risk_text = '낮음 (분산 양호)'
            elif hhi < 0.25:
                risk_level = 'medium'
                risk_text = '보통 (주의 필요)'
            else:
                risk_level = 'high'
                risk_text = '높음 (위험)'

            # Generate recommendations
            recommendations = []
            if max_weight > 30:
                recommendations.append(f"{max_position['name']} 비중이 {max_weight:.1f}%로 과도합니다. 30% 이하로 조정을 권장합니다.")

            if len(positions) < 5:
                recommendations.append(f"현재 {len(positions)}개 종목 보유 중입니다. 5개 이상으로 분산투자를 권장합니다.")

            if hhi > 0.25:
                recommendations.append("포트폴리오 집중도가 높습니다. 추가 분산투자를 고려하세요.")

            # Sort positions by weight
            positions.sort(key=lambda x: x['weight'], reverse=True)

            return jsonify({
                'success': True,
                'concentration_risk': risk_level,
                'concentration_text': risk_text,
                'hhi': round(hhi, 4),
                'hhi_percent': round(hhi * 100, 2),
                'position_count': len(positions),
                'max_position': max_position,
                'positions': positions,
                'recommendations': recommendations
            })
        else:
            return error_response('Bot not initialized')
    except Exception as e:
        print(f"Portfolio concentration API error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e))


@portfolio_bp.route('/api/portfolio/rebalance/recommendations')
def get_rebalance_recommendations():
    """Get portfolio rebalancing recommendations"""
    try:
        if _bot_instance and hasattr(_bot_instance, 'account_api'):
            holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT")
            deposit = _bot_instance.account_api.get_deposit()

            if not holdings:
                return jsonify({
                    'success': True,
                    'needs_rebalance': False,
                    'recommendations': [],
                    'message': '보유 종목이 없습니다.'
                })

            # Get total cash
            cash = int(str(deposit.get('ord_alow_amt', 0)).replace(',', '')) if deposit else 0

            # Convert holdings to position format
            positions = []
            total_value = 0

            for h in holdings:
                code = str(h.get('stk_cd', '')).replace('A', '').replace('_NX', '')
                name = h.get('stk_nm', '')
                quantity = int(str(h.get('rmnd_qty', 0)).replace(',', ''))
                current_price = int(str(h.get('cur_prc', 0)).replace(',', ''))
                eval_amt = int(str(h.get('eval_amt', 0)).replace(',', ''))

                if eval_amt == 0:
                    eval_amt = quantity * current_price

                if quantity > 0:
                    positions.append({
                        'code': code,
                        'name': name,
                        'quantity': quantity,
                        'current_price': current_price,
                        'value': eval_amt
                    })
                    total_value += eval_amt

            total_assets = total_value + cash

            # Calculate current weights
            for pos in positions:
                pos['weight'] = (pos['value'] / total_assets * 100) if total_assets > 0 else 0

            # Rebalancing logic
            recommendations = []
            needs_rebalance = False

            # Target: Equal weight distribution
            target_count = max(5, len(positions))  # At least 5 positions recommended
            target_weight = 100.0 / target_count
            threshold = 5.0  # 5% threshold

            for pos in positions:
                current_weight = pos['weight']
                weight_diff = current_weight - target_weight

                if abs(weight_diff) > threshold:
                    needs_rebalance = True

                    if weight_diff > 0:
                        # Overweight - suggest selling
                        sell_percent = weight_diff
                        sell_amount = int(total_assets * (sell_percent / 100))
                        sell_quantity = int(sell_amount / pos['current_price'])

                        recommendations.append({
                            'action': 'sell',
                            'code': pos['code'],
                            'name': pos['name'],
                            'current_weight': round(current_weight, 2),
                            'target_weight': round(target_weight, 2),
                            'quantity': sell_quantity,
                            'reason': f"{pos['name']} 비중이 {current_weight:.1f}%로 과도합니다. {sell_quantity}주 매도를 권장합니다."
                        })
                    else:
                        # Underweight - suggest buying
                        buy_percent = abs(weight_diff)
                        buy_amount = int(total_assets * (buy_percent / 100))
                        buy_quantity = int(buy_amount / pos['current_price'])

                        recommendations.append({
                            'action': 'buy',
                            'code': pos['code'],
                            'name': pos['name'],
                            'current_weight': round(current_weight, 2),
                            'target_weight': round(target_weight, 2),
                            'quantity': buy_quantity,
                            'reason': f"{pos['name']} 비중이 {current_weight:.1f}%로 낮습니다. {buy_quantity}주 추가 매수를 권장합니다."
                        })

            # Check if we need more positions
            if len(positions) < 5:
                needs_rebalance = True
                recommendations.append({
                    'action': 'diversify',
                    'reason': f"현재 {len(positions)}개 종목만 보유 중입니다. 5개 이상으로 분산투자를 권장합니다."
                })

            return jsonify({
                'success': True,
                'needs_rebalance': needs_rebalance,
                'target_weight': round(target_weight, 2),
                'position_count': len(positions),
                'recommendations': recommendations,
                'total_assets': total_assets
            })
        else:
            return error_response('Bot not initialized')
    except Exception as e:
        print(f"Rebalance recommendations API error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e))


@portfolio_bp.route('/api/performance/metrics')
def get_performance_metrics():
    """Get comprehensive performance metrics"""
    try:
        from database import get_db_session, Trade
        from sqlalchemy import func
        import statistics
        from flask import request

        session = get_db_session()
        if not session:
            return error_response('Database not available')

        # Get period from query parameter (default: 30 days)
        period_days = int(request.args.get('period', 30))
        from datetime import timedelta

        # Fix v6.1.5: Support different time periods
        if period_days > 0:
            period_start = datetime.now() - timedelta(days=period_days)
            period_label = f'최근 {period_days}일'
        else:
            period_start = datetime(2000, 1, 1)  # 전체 기간
            period_label = '전체 기간'

        # Fix v6.1.3: Try to filter by is_virtual, fallback if column doesn't exist
        try:
            trades = session.query(Trade).filter(
                Trade.action == 'sell',
                Trade.profit_loss.isnot(None),
                Trade.timestamp >= period_start,
                Trade.is_virtual == False  # Only real trades
            ).all()
            logger.info(f"성과지표 계산: {len(trades)}개 실제 거래 (is_virtual=False)")
        except Exception as e:
            # Fallback: is_virtual column doesn't exist yet
            logger.warning(f"is_virtual 컬럼 없음 - 모든 거래 포함: {e}")
            trades = session.query(Trade).filter(
                Trade.action == 'sell',
                Trade.profit_loss.isnot(None),
                Trade.timestamp >= period_start
            ).all()
            logger.info(f"성과지표 계산: {len(trades)}개 거래 (전체)")

        if not trades:
            # Return default metrics
            return jsonify({
                'success': True,
                'metrics': {
                    'avg_return': 0.0,
                    'win_rate': 0.0,
                    'max_drawdown': 0.0,
                    'sharpe_ratio': 0.0,
                    'daily_trades': 0.0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_profit': 0,
                    'total_loss': 0,
                    'avg_profit': 0.0,
                    'avg_loss': 0.0,
                    'profit_factor': 0.0
                },
                'period': period_label,
                'has_data': False
            })

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.profit_loss > 0]
        losing_trades = [t for t in trades if t.profit_loss <= 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        # Returns
        returns = [t.profit_loss_ratio for t in trades if t.profit_loss_ratio is not None]
        avg_return = statistics.mean(returns) if returns else 0.0

        # Profits and Losses
        total_profit = sum(t.profit_loss for t in winning_trades) if winning_trades else 0
        total_loss = abs(sum(t.profit_loss for t in losing_trades)) if losing_trades else 0
        avg_profit = total_profit / win_count if win_count > 0 else 0
        avg_loss = total_loss / loss_count if loss_count > 0 else 0

        # Profit Factor
        profit_factor = total_profit / total_loss if total_loss > 0 else 0.0

        # Maximum Drawdown
        cumulative_returns = []
        cumulative = 0
        for t in trades:
            cumulative += t.profit_loss_ratio if t.profit_loss_ratio else 0
            cumulative_returns.append(cumulative)

        max_drawdown = 0.0
        if cumulative_returns:
            peak = cumulative_returns[0]
            for value in cumulative_returns:
                if value > peak:
                    peak = value
                drawdown = (peak - value)
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        # Sharpe Ratio (simplified)
        sharpe_ratio = 0.0
        if returns and len(returns) > 1:
            mean_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            sharpe_ratio = (mean_return / std_return) * (252 ** 0.5) if std_return > 0 else 0.0

        # Daily trade frequency
        days_with_trades = len(set(t.timestamp.date() for t in trades))
        daily_trades = total_trades / days_with_trades if days_with_trades > 0 else 0

        return jsonify({
            'success': True,
            'metrics': {
                'avg_return': round(avg_return, 2),
                'win_rate': round(win_rate, 1),
                'max_drawdown': round(max_drawdown, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'daily_trades': round(daily_trades, 1),
                'total_trades': total_trades,
                'winning_trades': win_count,
                'losing_trades': loss_count,
                'total_profit': int(total_profit),
                'total_loss': int(total_loss),
                'avg_profit': int(avg_profit),
                'avg_loss': int(avg_loss),
                'profit_factor': round(profit_factor, 2)
            },
            'period': period_label,
            'has_data': True,
            'debug_info': {
                'total_sell_trades': total_trades,
                'date_range': f"{period_start.strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')}",
                'profit_loss_ratio_available': len(returns),
                'profit_loss_ratio_missing': total_trades - len(returns)
            }
        })

    except Exception as e:
        print(f"Performance metrics error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e))


@portfolio_bp.route('/api/portfolio/summary')
def get_portfolio_summary():
    """
    포트폴리오 요약 정보 조회

    Returns:
    {
        "success": true,
        "holdings": [
            {
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "quantity": 10,
                "avg_price": 70000,
                "current_price": 71000,
                "profit_loss": 10000,
                "profit_loss_rate": 1.43
            }
        ],
        "total_assets": 10000000,
        "cash": 5000000,
        "stock_value": 5000000
    }
    """
    try:
        logger.info("="*60)
        logger.info("📊 포트폴리오 요약 API 호출됨")
        logger.info("="*60)

        if not _bot_instance:
            logger.error("❌ Bot instance not available")
            return error_response('Bot instance not available')

        if not hasattr(_bot_instance, 'account_api'):
            logger.error("❌ account_api not available")
            return error_response('account_api not available')

        # 보유 종목 및 예수금 조회
        holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT")
        deposit = _bot_instance.account_api.get_deposit()

        # 보유 종목 포맷팅
        formatted_holdings = []
        stock_value = 0

        for h in holdings:
            stock_code = h.get('stk_cd', '').replace('A', '').replace('_NX', '')
            quantity = int(str(h.get('rmnd_qty', 0)).replace(',', ''))
            avg_price = int(float(str(h.get('avg_prc', 0)).replace(',', '')))
            current_price = int(float(str(h.get('prsnt_prc', 0)).replace(',', '')))
            eval_amt = int(float(str(h.get('eval_amt', 0)).replace(',', '')))

            profit_loss = eval_amt - (avg_price * quantity)
            profit_loss_rate = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

            stock_value += eval_amt

            formatted_holdings.append({
                'stock_code': stock_code,
                'stock_name': h.get('stk_nm', ''),
                'quantity': quantity,
                'avg_price': avg_price,
                'current_price': current_price,
                'profit_loss': profit_loss,
                'profit_loss_rate': round(profit_loss_rate, 2)
            })

        # 예수금
        cash = int(str(deposit.get('100stk_ord_alow_amt', '0')).replace(',', '')) if deposit else 0
        total_assets = cash + stock_value

        logger.info(f"✅ 보유 종목: {len(formatted_holdings)}개, 총 자산: {total_assets:,}원")

        return jsonify({
            'success': True,
            'holdings': formatted_holdings,
            'total_assets': total_assets,
            'cash': cash,
            'stock_value': stock_value
        })

    except Exception as e:
        logger.error(f"❌ 포트폴리오 요약 조회 실패: {e}", exc_info=True)
        return error_response(f'Failed to get portfolio summary: {str(e)}')


@portfolio_bp.route('/api/portfolio/sell', methods=['POST'])
def sell_position():
    """
    포트폴리오에서 종목 매도

    POST Body:
    {
        "stock_code": "005930",
        "quantity": 10,
        "price": 70000
    }
    """
    try:
        logger.info("="*60)
        logger.info("📤 포트폴리오 매도 API 호출됨")
        logger.info("="*60)

        if not _bot_instance:
            logger.error("❌ Bot instance not available")
            return error_response('Bot instance not available')

        data = request.get_json()
        logger.info(f"요청 데이터: {data}")

        stock_code = data.get('stock_code')
        quantity = data.get('quantity')
        price = data.get('price')

        if not stock_code:
            logger.error("❌ stock_code 누락")
            return error_response('stock_code is required')

        logger.info(f"매도 요청: {stock_code}, 수량={quantity}, 가격={price}")

        # Fix v6.1.3: 분할 매도 사용
        if hasattr(_bot_instance, 'split_order_executor') and _bot_instance.split_order_executor:
            logger.info(f"🔀 포트폴리오 분할 매도 시작: {stock_code} {quantity}주")

            # 종목명 및 평균 매수가 조회
            stock_name = stock_code
            entry_price = 0
            if hasattr(_bot_instance, 'account_api'):
                logger.info("보유 종목 조회 중...")
                holdings = _bot_instance.account_api.get_holdings()
                logger.info(f"보유 종목 수: {len(holdings) if holdings else 0}")
                for h in holdings:
                    # Fix v6.1.5: 종목 코드 매칭 개선 (_NX 접미사 제거)
                    holding_code = h.get('stk_cd', '').replace('A', '').replace('_NX', '')
                    if holding_code == stock_code:
                        stock_name = h.get('stk_nm', stock_code)
                        # quantity가 없으면 전량 매도
                        if not quantity:
                            quantity = int(str(h.get('rmnd_qty', 0)).replace(',', ''))
                        # Fix v6.1.5: 평균 매수가 필드명 수정 (avg_buy_price → avg_prc)
                        entry_price = float(str(h.get('avg_prc', 0)).replace(',', ''))
                        if entry_price == 0:
                            # 다른 필드도 확인
                            entry_price = float(str(h.get('pchs_avg_pric', 0)).replace(',', ''))
                        logger.info(f"매도 대상: {stock_name} (보유: {h.get('rmnd_qty', 0)}주, 평균단가: {entry_price:,}원)")
                        break

            if not quantity or quantity == 0:
                logger.error(f"❌ 보유 수량 없음 (stock_code={stock_code})")
                return error_response('보유 수량 없음')

            if entry_price == 0:
                logger.error(f"❌ 평균 매수가를 찾을 수 없음 (stock_code={stock_code})")
                return error_response('평균 매수가를 찾을 수 없음')

            # 분할 매도 실행
            logger.info(f"🚀 분할 매도 실행: {stock_name} {quantity}주 @ 평균단가 {entry_price}원")
            result = _bot_instance.split_order_executor.execute_split_sell(
                stock_code=stock_code,
                stock_name=stock_name,
                total_quantity=quantity,
                entry_price=entry_price
            )

            # Fix: result is a SplitOrderGroup object, not a dict
            if result:
                logger.info(f"✅ 분할 매도 성공: {stock_name} {quantity}주 (그룹 ID: {result.group_id})")
                # Convert entries to dict format for JSON response
                split_orders = [
                    {
                        'entry_id': entry.entry_id,
                        'quantity': entry.quantity,
                        'price': entry.price,
                        'status': entry.status.value if hasattr(entry.status, 'value') else str(entry.status),
                        'order_number': entry.order_number
                    }
                    for entry in result.entries
                ]
                return jsonify({
                    'success': True,
                    'message': f'{stock_name} {quantity}주 분할 매도 주문 완료',
                    'stock_code': stock_code,
                    'quantity': quantity,
                    'group_id': result.group_id,
                    'split_orders': split_orders
                })
            else:
                logger.error(f"❌ 분할 매도 실패: {stock_name} {quantity}주")
                return error_response('매도 주문 실패')

        elif hasattr(_bot_instance, 'order_api') and _bot_instance.order_api:
            # Fallback: 일반 매도
            logger.info(f"일반 매도 시작: {stock_code} {quantity}주")

            result = _bot_instance.order_api.sell(
                stock_code=stock_code,
                quantity=quantity,
                price=price if price else 0,
                order_type='0'
            )

            logger.info(f"매도 API 응답: {result}")

            if result:
                logger.info(f"✅ 일반 매도 성공: {stock_code} {quantity}주")
                return jsonify({
                    'success': True,
                    'message': f'{stock_code} {quantity}주 매도 주문 완료',
                    'order_no': result.get('order_no')
                })
            else:
                logger.error(f"❌ 일반 매도 실패: {stock_code} {quantity}주")
                return error_response('매도 주문 실패')
        else:
            logger.error("❌ Trading API not available")
            return error_response('Trading API not available')

    except Exception as e:
        logger.error(f"❌ Portfolio sell error: {e}", exc_info=True)
        return error_response(str(e))
