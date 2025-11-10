"""
Portfolio Management Routes Module
Handles portfolio optimization, risk analysis, and performance tracking
"""
from datetime import datetime
from flask import Blueprint, jsonify, request

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
            return jsonify({'success': False, 'message': 'Bot not initialized'})
    except Exception as e:
        print(f"Portfolio optimization API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

@portfolio_bp.route('/api/risk/analysis')
def get_risk_analysis():
    """Get portfolio risk analysis with correlation heatmap"""
    try:
        from strategy.advanced_risk_analytics import AdvancedRiskAnalytics as RiskAnalyzer

        if _bot_instance and hasattr(_bot_instance, 'account_api'):
            holdings = _bot_instance.account_api.get_holdings()

            # Convert holdings to position format with sector info
            positions = []
            for h in holdings:
                code = h.get('pdno', '')
                positions.append({
                    'code': code,
                    'name': h.get('prdt_name', ''),
                    'value': int(h.get('eval_amt', 0)),
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
            return jsonify({'success': False, 'message': 'Bot not initialized'})
    except Exception as e:
        print(f"Risk analysis API error: {e}")
        return jsonify({'success': False, 'message': str(e)})
