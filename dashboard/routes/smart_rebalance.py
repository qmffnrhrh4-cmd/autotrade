"""
Smart Rebalancing API - AI-powered portfolio rebalancing
Version: 6.1.2
"""
from flask import Blueprint, jsonify
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

smart_rebalance_bp = Blueprint('smart_rebalance', __name__)

# Module-level bot instance
_bot_instance = None

def set_bot_instance(bot):
    """Set the bot instance for this module"""
    global _bot_instance
    _bot_instance = bot


@smart_rebalance_bp.route('/api/portfolio/rebalance/smart')
def get_smart_rebalance():
    """
    AI-powered smart rebalancing recommendations

    Unlike simple equal-weight rebalancing, this:
    1. Analyzes each stock's chart and technical indicators
    2. Uses AI to evaluate current market conditions
    3. Provides specific buy/sell prices based on orderbook analysis
    4. Recommends optimal cash reserve ratio
    5. Considers risk/reward for each position
    """
    try:
        if not _bot_instance:
            return jsonify({'success': False, 'error': 'Bot not initialized'})

        if not hasattr(_bot_instance, 'account_api'):
            return jsonify({'success': False, 'error': 'Account API not available'})

        # Get current holdings and deposit
        holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT")
        deposit = _bot_instance.account_api.get_deposit()

        if not holdings:
            return jsonify({
                'success': True,
                'needs_rebalance': False,
                'message': '보유 종목이 없습니다.',
                'recommendations': [],
                'cash_recommendation': None
            })

        # Get cash
        cash = int(str(deposit.get('ord_alow_amt', 0)).replace(',', '')) if deposit else 0

        # Calculate total assets
        total_value = sum(
            int(str(h.get('eval_amt', 0)).replace(',', ''))
            for h in holdings
        )
        total_assets = total_value + cash
        current_cash_ratio = (cash / total_assets * 100) if total_assets > 0 else 0

        # Analyze each position
        recommendations = []

        for holding in holdings:
            try:
                stock_code = str(holding.get('stk_cd', '')).replace('A', '').replace('_NX', '')
                stock_name = holding.get('stk_nm', '')
                quantity = int(str(holding.get('rmnd_qty', 0)).replace(',', ''))
                current_price = int(str(holding.get('cur_prc', 0)).replace(',', ''))
                avg_price = int(str(holding.get('avg_prc', 0)).replace(',', ''))
                eval_amt = int(str(holding.get('eval_amt', 0)).replace(',', ''))

                if quantity == 0 or current_price == 0:
                    continue

                # Calculate current weight
                current_weight = (eval_amt / total_assets * 100) if total_assets > 0 else 0

                # Get AI analysis for this stock
                ai_analysis = _analyze_stock_with_ai(
                    _bot_instance,
                    stock_code,
                    stock_name,
                    current_price
                )

                # Get optimal prices from orderbook
                optimal_buy_price = _get_optimal_buy_price_safe(
                    _bot_instance,
                    stock_code,
                    current_price
                )
                optimal_sell_price = _get_optimal_sell_price_safe(
                    _bot_instance,
                    stock_code,
                    current_price
                )

                # Determine action based on AI analysis
                action, target_weight, reason = _determine_rebalance_action(
                    ai_analysis,
                    current_weight,
                    avg_price,
                    current_price
                )

                # Calculate quantity and amount
                if action == 'SELL':
                    # Sell some or all
                    target_value = total_assets * (target_weight / 100)
                    sell_value = eval_amt - target_value
                    sell_quantity = int(sell_value / optimal_sell_price) if optimal_sell_price > 0 else 0

                    if sell_quantity > 0:
                        recommendations.append({
                            'action': 'SELL',
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'current_quantity': quantity,
                            'sell_quantity': min(sell_quantity, quantity),
                            'current_price': current_price,
                            'recommended_price': optimal_sell_price,
                            'current_weight': round(current_weight, 2),
                            'target_weight': round(target_weight, 2),
                            'reason': reason,
                            'ai_score': ai_analysis.get('score', 0),
                            'ai_signal': ai_analysis.get('signal', 'hold'),
                            'expected_amount': sell_quantity * optimal_sell_price
                        })

                elif action == 'BUY':
                    # Buy more
                    target_value = total_assets * (target_weight / 100)
                    buy_value = target_value - eval_amt
                    buy_quantity = int(buy_value / optimal_buy_price) if optimal_buy_price > 0 else 0

                    if buy_quantity > 0:
                        recommendations.append({
                            'action': 'BUY',
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'current_quantity': quantity,
                            'buy_quantity': buy_quantity,
                            'current_price': current_price,
                            'recommended_price': optimal_buy_price,
                            'current_weight': round(current_weight, 2),
                            'target_weight': round(target_weight, 2),
                            'reason': reason,
                            'ai_score': ai_analysis.get('score', 0),
                            'ai_signal': ai_analysis.get('signal', 'hold'),
                            'expected_amount': buy_quantity * optimal_buy_price
                        })

                else:  # HOLD
                    recommendations.append({
                        'action': 'HOLD',
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'current_quantity': quantity,
                        'current_price': current_price,
                        'current_weight': round(current_weight, 2),
                        'target_weight': round(target_weight, 2),
                        'reason': reason,
                        'ai_score': ai_analysis.get('score', 0),
                        'ai_signal': ai_analysis.get('signal', 'hold')
                    })

            except Exception as e:
                logger.error(f"Error analyzing {stock_code}: {e}")
                continue

        # Determine optimal cash ratio
        cash_recommendation = _determine_cash_ratio(
            recommendations,
            current_cash_ratio
        )

        # Check if rebalancing is needed
        needs_rebalance = any(
            r['action'] in ['BUY', 'SELL']
            for r in recommendations
        )

        return jsonify({
            'success': True,
            'needs_rebalance': needs_rebalance,
            'total_assets': total_assets,
            'current_cash': cash,
            'current_cash_ratio': round(current_cash_ratio, 2),
            'recommendations': recommendations,
            'cash_recommendation': cash_recommendation,
            'analysis_time': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Smart rebalance error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        })


def _analyze_stock_with_ai(bot, stock_code: str, stock_name: str, current_price: int) -> Dict[str, Any]:
    """Analyze stock using AI and scoring system"""
    try:
        # Try to use AI analyzer if available
        if hasattr(bot, 'ai_analyzer') and bot.ai_analyzer:
            ai_result = bot.ai_analyzer.analyze_stock_simple(
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price
            )
            return {
                'signal': ai_result.get('signal', 'hold'),
                'score': ai_result.get('score', 50),
                'confidence': ai_result.get('confidence', 'low'),
                'reasons': ai_result.get('reasons', [])
            }

        # Fallback: basic analysis
        return {
            'signal': 'hold',
            'score': 50,
            'confidence': 'medium',
            'reasons': ['AI 분석 사용 불가 - 기본 분석 사용']
        }

    except Exception as e:
        logger.error(f"AI analysis error for {stock_code}: {e}")
        return {
            'signal': 'hold',
            'score': 50,
            'confidence': 'low',
            'reasons': [f'분석 오류: {str(e)}']
        }


def _get_optimal_buy_price_safe(bot, stock_code: str, current_price: int) -> int:
    """Get optimal buy price from orderbook (safe wrapper)"""
    try:
        if hasattr(bot, 'data_fetcher'):
            orderbook = bot.data_fetcher.get_orderbook(stock_code)
            if orderbook and 'bids' in orderbook:
                bids = orderbook['bids'][:3]
                if bids:
                    # Use best bid price (slightly lower than current)
                    return int(bids[0].get('price', current_price))

        return current_price

    except Exception as e:
        logger.debug(f"Orderbook error for {stock_code}: {e}")
        return current_price


def _get_optimal_sell_price_safe(bot, stock_code: str, current_price: int) -> int:
    """Get optimal sell price from orderbook (safe wrapper)"""
    try:
        if hasattr(bot, 'data_fetcher'):
            orderbook = bot.data_fetcher.get_orderbook(stock_code)
            if orderbook and 'asks' in orderbook:
                asks = orderbook['asks'][:3]
                if asks:
                    # Use best ask price (slightly higher than current)
                    return int(asks[0].get('price', current_price))

        return current_price

    except Exception as e:
        logger.debug(f"Orderbook error for {stock_code}: {e}")
        return current_price


def _determine_rebalance_action(
    ai_analysis: Dict[str, Any],
    current_weight: float,
    avg_price: int,
    current_price: int
) -> tuple[str, float, str]:
    """
    Determine rebalance action based on AI analysis

    Returns:
        (action, target_weight, reason)
    """
    signal = ai_analysis.get('signal', 'hold')
    score = ai_analysis.get('score', 50)
    reasons = ai_analysis.get('reasons', [])

    # Calculate profit/loss
    pnl_rate = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

    # Decision logic
    if signal == 'sell' or score < 40:
        # Weak signal - reduce position
        target_weight = max(0, current_weight * 0.5)
        reason = f"약세 신호 (점수: {score:.0f})"
        if reasons:
            reason += f" - {reasons[0]}"
        return 'SELL', target_weight, reason

    elif signal == 'buy' and score >= 70:
        # Strong buy signal - increase position (but cap at 30%)
        target_weight = min(30, current_weight * 1.5)
        reason = f"강세 신호 (점수: {score:.0f})"
        if reasons:
            reason += f" - {reasons[0]}"
        return 'BUY', target_weight, reason

    elif pnl_rate > 20:
        # Take profit - reduce position
        target_weight = current_weight * 0.7
        reason = f"익절 권장 (수익률: +{pnl_rate:.1f}%)"
        return 'SELL', target_weight, reason

    elif pnl_rate < -10 and score < 50:
        # Cut loss - reduce or exit
        target_weight = 0
        reason = f"손절 권장 (손실: {pnl_rate:.1f}%, 점수: {score:.0f})"
        return 'SELL', target_weight, reason

    else:
        # Hold - maintain current position
        reason = f"현재 포지션 유지 (점수: {score:.0f}, 수익률: {pnl_rate:+.1f}%)"
        return 'HOLD', current_weight, reason


def _determine_cash_ratio(
    recommendations: List[Dict[str, Any]],
    current_cash_ratio: float
) -> Dict[str, Any]:
    """Determine optimal cash reserve ratio"""
    # Count sell vs buy signals
    sell_count = sum(1 for r in recommendations if r['action'] == 'SELL')
    buy_count = sum(1 for r in recommendations if r['action'] == 'BUY')

    # Calculate average AI score
    scores = [r.get('ai_score', 50) for r in recommendations if 'ai_score' in r]
    avg_score = sum(scores) / len(scores) if scores else 50

    # Determine target cash ratio
    if sell_count > buy_count or avg_score < 45:
        # Defensive mode - hold more cash
        target_ratio = 25
        reason = "약세장 대응: 현금 비율 확대 권장"
    elif buy_count > sell_count and avg_score > 65:
        # Aggressive mode - lower cash
        target_ratio = 10
        reason = "강세장 활용: 현금 비율 축소 가능"
    else:
        # Neutral mode - moderate cash
        target_ratio = 15
        reason = "중립장: 적정 현금 비율 유지"

    return {
        'current_ratio': round(current_cash_ratio, 2),
        'target_ratio': target_ratio,
        'reason': reason,
        'adjustment_needed': abs(current_cash_ratio - target_ratio) > 5
    }
