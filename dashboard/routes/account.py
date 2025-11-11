"""
Account-related API routes
Handles account balance, positions, and detailed holdings
"""
from flask import Blueprint, jsonify
from typing import Dict, Any
from datetime import datetime
from research.data_fetcher import is_nxt_hours

account_bp = Blueprint('account', __name__)

# Global bot instance (will be set by main app)
_bot_instance = None


def set_bot_instance(bot):
    """Set the bot instance for this module"""
    global _bot_instance
    _bot_instance = bot


@account_bp.route('/api/account')
def get_account():
    """Get account information from real API"""
    # 테스트 모드 정보
    test_mode_active = False
    test_date = None
    if _bot_instance:
        test_mode_active = getattr(_bot_instance, 'test_mode_active', False)
        test_date = getattr(_bot_instance, 'test_date', None)

    try:
        if _bot_instance and hasattr(_bot_instance, 'account_api'):
            # 실제 API에서 데이터 가져오기 (테스트 모드에서도 가장 최근 데이터 사용)
            deposit = _bot_instance.account_api.get_deposit()

            # v5.5.0: KRX+NXT 통합 조회로 중복 제거
            # 이전에는 KRX와 NXT를 각각 조회하여 같은 종목이 2번 카운트되는 버그 발생
            # API가 "KRX+NXT" 옵션을 지원하므로 한 번에 조회
            holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT") or []

            # 디버깅 로그
            if holdings:
                print(f"[ACCOUNT] 보유 종목: {len(holdings)}개")
                for h in holdings:
                    print(f"  - {h.get('stk_cd', 'N/A')} {h.get('stk_nm', 'N/A')}: {h.get('rmnd_qty', 0)}주")
            else:
                print(f"[ACCOUNT] 보유 종목: 없음")

            # 계좌 정보 계산 (kt00001 API 응답 구조)
            #
            # 정확한 공식:
            # - 총자산 = 예수금 + 주식평가액
            # - 가용금액 = 주문가능금액 (100stk_ord_alow_amt)
            # - 예수금 = entr (총 현금)
            #
            # kt00001 API 주요 필드:
            # - entr: 예수금 (총 현금)
            # - 100stk_ord_alow_amt: 100% 주문가능금액 (실제 사용 가능한 금액)
            # - ord_psbl_amt: 주문가능금액
            # - wdrw_psbl_amt: 출금가능금액

            # 디버깅: deposit 원본 데이터 출력
            logger.debug(f"deposit 원본 데이터: {deposit}")

            deposit_amount = int(float(str(deposit.get('entr', '0')).replace(',', ''))) if deposit else 0
            available_cash = int(float(str(deposit.get('100stk_ord_alow_amt', '0')).replace(',', ''))) if deposit else 0
            order_possible = int(float(str(deposit.get('ord_psbl_amt', '0')).replace(',', ''))) if deposit else 0
            withdraw_possible = int(float(str(deposit.get('wdrw_psbl_amt', '0')).replace(',', ''))) if deposit else 0

            logger.debug(f"entr (예수금?): {deposit_amount:,}원")
            logger.debug(f"100stk_ord_alow_amt: {available_cash:,}원")
            logger.debug(f"ord_psbl_amt: {order_possible:,}원")

            # v5.4.2: 주식 현재가치 계산 (장외 시간 대응)
            # eval_amt이 0인 경우 (장외 시간) 수량 × 현재가로 직접 계산
            # v5.17: NXT 시간대에는 실시간 현재가 조회
            in_nxt = is_nxt_hours()
            stock_value = 0
            logger.debug(f"보유 종목 수: {len(holdings) if holdings else 0}")
            if holdings:
                for idx, h in enumerate(holdings, 1):
                    logger.debug(f"종목 {idx}: {h}")
                    quantity = int(float(str(h.get('rmnd_qty', 0)).replace(',', '')))
                    cur_price = int(float(str(h.get('cur_prc', 0)).replace(',', '')))

                    # NXT 시간대일 때는 실시간 현재가 조회
                    if in_nxt and _bot_instance and hasattr(_bot_instance, 'data_fetcher'):
                        try:
                            code = str(h.get('stk_cd', '')).strip().replace('_NX', '').replace('A', '')
                            price_info = _bot_instance.data_fetcher.get_current_price(code)
                            if price_info and price_info.get('current_price'):
                                cur_price = price_info['current_price']
                        except Exception as e:
                            print(f"[NXT] 현재가 조회 실패: {e}")

                    eval_amt = int(float(str(h.get('eval_amt', 0)).replace(',', '')))
                    if eval_amt > 0 and not in_nxt:
                        # API에서 평가금액이 정상적으로 오는 경우 (장중)
                        logger.debug(f"  -> eval_amt 사용: {eval_amt:,}원")
                        stock_value += eval_amt
                    else:
                        # 장외 시간 또는 NXT 시간대는 직접 계산
                        calculated_value = quantity * cur_price
                        logger.debug(f"  -> 직접 계산: {quantity} × {cur_price:,} = {calculated_value:,}원")
                        stock_value += calculated_value

            # 정확한 공식 적용:
            # 총자산 = 예수금 + 주식평가액
            total_assets = deposit_amount + stock_value

            # 가용금액 = 주문가능금액 (available_cash 또는 order_possible)
            # 일반적으로 100stk_ord_alow_amt를 사용
            cash = available_cash

            logger.info(f"===== 계좌 정보 요약 =====")
            logger.info(f"  예수금 (entr): {deposit_amount:,}원")
            logger.info(f"  주식평가액: {stock_value:,}원")
            logger.info(f"  --------------------------------")
            logger.info(f"  총자산: {total_assets:,}원")
            logger.info(f"  계산식: {deposit_amount:,} + {stock_value:,} = {total_assets:,}원")
            logger.info(f"  ================================")
            logger.info(f"  가용금액: {cash:,}원")

            # 92만원 vs 105만원 문제 디버깅
            if deposit_amount > 900000 and total_assets > 1000000:
                logger.warning(f"총 자산 차이 감지!")
                logger.warning(f"  예수금(entr): {deposit_amount:,}원")
                logger.warning(f"  총자산: {total_assets:,}원")
                logger.warning(f"  차이: {total_assets - deposit_amount:,}원")
                logger.warning(f"  의심: entr 필드가 이미 주식평가액을 포함하는지 확인 필요")
            logger.info(f"  주문가능금액: {order_possible:,}원")
            logger.info(f"  출금가능금액: {withdraw_possible:,}원")

            # 손익 계산 (kt00004 API 필드 사용: avg_prc, rmnd_qty)
            # 계산 방식: get_positions()와 동일하게 통일
            total_buy_amount = 0
            profit_loss_detailed = []

            if holdings:
                for h in holdings:
                    stock_code = h.get('stk_cd', '')
                    stock_name = h.get('stk_nm', '')

                    # kt00004 API 필드 사용 (main.py:841-851과 동일)
                    quantity = int(float(str(h.get('rmnd_qty', 0)).replace(',', '')))  # 보유수량
                    avg_price = int(float(str(h.get('avg_prc', 0)).replace(',', '')))  # 평균단가
                    cur_price = int(float(str(h.get('cur_prc', 0)).replace(',', '')))  # 현재가

                    # 매입금액 계산 (평균단가 × 수량)
                    buy_amt = avg_price * quantity

                    # 평가금액 계산
                    eval_amt = int(float(str(h.get('eval_amt', 0)).replace(',', '')))
                    if eval_amt == 0:
                        # 장외 시간 등으로 eval_amt이 0인 경우, 직접 계산
                        eval_amt = quantity * cur_price

                    # 손익 = 평가금액 - 매입금액
                    stock_pl = eval_amt - buy_amt
                    total_buy_amount += buy_amt

                    profit_loss_detailed.append({
                        'code': stock_code,
                        'name': stock_name,
                        'buy_amount': buy_amt,
                        'eval_amount': eval_amt,
                        'profit_loss': stock_pl
                    })

                    print(f"[ACCOUNT] {stock_code} ({stock_name}) 손익: {stock_pl:,}원 (매입: {buy_amt:,}원 = {quantity}주 × {avg_price:,}원, 평가: {eval_amt:,}원)")

            profit_loss = stock_value - total_buy_amount
            profit_loss_percent = (profit_loss / total_buy_amount * 100) if total_buy_amount > 0 else 0

            print(f"[ACCOUNT] 총 손익: {profit_loss:,}원 ({profit_loss_percent:+.2f}%)")
            print(f"[ACCOUNT] 총 매입금액: {total_buy_amount:,}원 (정확한 계산: avg_prc × rmnd_qty)")
            print(f"[ACCOUNT] 총 평가금액: {stock_value:,}원")

            return jsonify({
                'total_assets': total_assets,
                'cash': cash,
                'stock_value': stock_value,
                'profit_loss': profit_loss,
                'profit_loss_percent': profit_loss_percent,
                'open_positions': len(holdings) if holdings else 0,
                'test_mode': test_mode_active,
                'test_date': test_date
            })
        else:
            # Bot이 없으면 mock data
            return jsonify({
                'total_assets': 0,
                'cash': 0,
                'stock_value': 0,
                'profit_loss': 0,
                'profit_loss_percent': 0,
                'open_positions': 0,
                'test_mode': test_mode_active,
                'test_date': test_date
            })
    except Exception as e:
        print(f"Error getting account info: {e}")
        return jsonify({
            'total_assets': 0,
            'cash': 0,
            'stock_value': 0,
            'profit_loss': 0,
            'profit_loss_percent': 0,
            'open_positions': 0,
            'test_mode': test_mode_active,
            'test_date': test_date
        })


@account_bp.route('/api/account/portfolio')
def get_account_portfolio():
    """Get portfolio holdings in dashboard-compatible format"""
    try:
        # Get positions using the same logic as get_positions()
        if not _bot_instance or not hasattr(_bot_instance, 'account_api'):
            return jsonify({
                'success': False,
                'holdings': [],
                'message': 'Bot not initialized'
            })

        holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT")

        if not holdings:
            return jsonify({
                'success': True,
                'holdings': []
            })

        # NXT 시간대 확인
        in_nxt = is_nxt_hours()

        portfolio = []
        for h in holdings:
            try:
                code = str(h.get('stk_cd', '')).strip()
                # _NX 접미사 제거
                code = code.replace('_NX', '')
                # A 접두사 제거
                if code.startswith('A'):
                    code = code[1:]

                name = h.get('stk_nm', '')
                quantity = int(float(str(h.get('rmnd_qty', 0)).replace(',', '')))

                if quantity <= 0:
                    continue

                avg_price = int(float(str(h.get('avg_prc', 0)).replace(',', '')))
                current_price = int(float(str(h.get('cur_prc', 0)).replace(',', '')))

                # NXT 시간대일 때는 실시간 현재가 조회
                if in_nxt and _bot_instance and hasattr(_bot_instance, 'data_fetcher'):
                    try:
                        price_info = _bot_instance.data_fetcher.get_current_price(code)
                        if price_info and price_info.get('current_price'):
                            current_price = price_info['current_price']
                            print(f"[NXT] {code} 실시간 현재가: {current_price:,}원")
                    except Exception as e:
                        print(f"[NXT] {code} 현재가 조회 실패: {e}")
                        # 조회 실패 시 기존 가격 사용

                value = int(float(str(h.get('eval_amt', 0)).replace(',', '')))
                if value == 0 and current_price > 0:
                    value = quantity * current_price
                elif in_nxt and current_price > 0:
                    # NXT 시간대에는 실시간 현재가로 재계산
                    value = quantity * current_price

                profit_loss = value - (avg_price * quantity)
                profit_loss_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

                portfolio.append({
                    'stock_code': code,
                    'stock_name': name,
                    'quantity': quantity,
                    'avg_price': avg_price,
                    'current_price': current_price,
                    'value': value,
                    'profit_loss': profit_loss,
                    'profit_loss_percent': profit_loss_percent
                })
            except Exception as e:
                print(f"Error processing holding {h}: {e}")
                continue

        return jsonify({
            'success': True,
            'holdings': portfolio
        })

    except Exception as e:
        print(f"Error getting portfolio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'holdings': [],
            'message': str(e)
        })


@account_bp.route('/api/positions')
def get_positions():
    """Get current positions from real API (kt00004 API 응답 필드 사용)"""
    try:
        # v5.3.2: bot_instance 체크 강화
        if not _bot_instance:
            print("Error: bot_instance is None")
            return jsonify([])

        if not hasattr(_bot_instance, 'account_api'):
            print("Error: bot_instance has no account_api")
            return jsonify([])

        # v5.5.0: KRX+NXT 통합 조회
        holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT")

        if not holdings:
            print("[POSITIONS] 보유 종목 없음")
            return jsonify([])

        positions = []
        for h in holdings:
            try:
                # kt00004 API 응답 필드 사용 (동일한 필드: main.py:856-864)
                code = str(h.get('stk_cd', '')).strip()  # 종목코드
                # A 접두사 제거 (키움증권 API에서 A005930 형식으로 올 수 있음)
                if code.startswith('A'):
                    code = code[1:]

                name = h.get('stk_nm', '')  # 종목명
                quantity = int(float(str(h.get('rmnd_qty', 0)).replace(',', '')))  # 보유수량

                # v5.3.2: 수량 0인 종목 스킵
                if quantity <= 0:
                    continue

                avg_price = int(float(str(h.get('avg_prc', 0)).replace(',', '')))  # 평균단가
                current_price = int(float(str(h.get('cur_prc', 0)).replace(',', '')))  # 현재가

                # v5.4.2: 평가금액 계산 (장외 시간 대응)
                value = int(float(str(h.get('eval_amt', 0)).replace(',', '')))
                if value == 0 and current_price > 0:
                    # 장외 시간 등으로 eval_amt이 0인 경우, 직접 계산
                    value = quantity * current_price

                profit_loss = value - (avg_price * quantity)
                profit_loss_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

                # v5.7.2: 수익 최적화 분석 추가
                optimization_info = {}
                try:
                    from features.profit_optimizer import get_profit_optimizer

                    optimizer = get_profit_optimizer()

                    # 최고가 추정 (현재가와 평균단가 중 높은 값)
                    highest_price = max(current_price, avg_price)
                    if profit_loss_percent > 0:
                        # 수익 중이면 현재가가 최고가일 가능성
                        highest_price = current_price

                    # 보유 일수 계산 (실제로는 entry_time 필요, 여기서는 추정)
                    days_held = 5  # 기본값

                    # 포지션 분석
                    analysis = optimizer.analyze_position(
                        entry_price=avg_price,
                        current_price=current_price,
                        highest_price=highest_price,
                        quantity=quantity,
                        days_held=days_held,
                        rule_name='balanced'
                    )

                    # ATR 기반 최적 레벨 계산 (ATR 추정)
                    estimated_atr = current_price * 0.02  # 주가의 2%로 추정
                    exit_levels = optimizer.optimize_exit_levels(
                        entry_price=avg_price,
                        atr=estimated_atr,
                        rule_name='balanced'
                    )

                    optimization_info = {
                        'action': analysis.action,
                        'reason': analysis.reason,
                        'sell_ratio': analysis.sell_ratio,
                        'optimized_stop_loss': exit_levels['stop_loss'],
                        'optimized_take_profit': exit_levels['take_profit'],
                        'risk_reward_ratio': exit_levels['risk_reward_ratio'],
                        'trailing_stop': analysis.new_stop_loss if analysis.new_stop_loss else None
                    }

                except Exception as e:
                    print(f"Error in profit optimization for {code}: {e}")
                    optimization_info = {
                        'action': 'hold',
                        'reason': '분석 불가',
                        'sell_ratio': 0.0
                    }

                # 기존 손절가 (dynamic_risk_manager)
                stop_loss_price = avg_price
                if _bot_instance and hasattr(_bot_instance, 'dynamic_risk_manager'):
                    try:
                        thresholds = _bot_instance.dynamic_risk_manager.get_exit_thresholds(avg_price)
                        stop_loss_price = thresholds.get('stop_loss', avg_price)
                    except Exception as e:
                        print(f"Error getting exit thresholds for {code}: {e}")

                positions.append({
                    'stock_code': code,  # v6.0.1: 일관성을 위해 'code' → 'stock_code'
                    'stock_name': name,  # v6.0.1: 일관성을 위해 'name' → 'stock_name'
                    'quantity': quantity,
                    'avg_price': avg_price,
                    'current_price': current_price,
                    'profit_loss': profit_loss,
                    'profit_loss_percent': profit_loss_percent,
                    'value': value,
                    'stop_loss_price': stop_loss_price,
                    'optimization': optimization_info  # v5.7.2: 최적화 정보 추가
                })
            except Exception as e:
                print(f"Error processing holding {h}: {e}")
                continue

        return jsonify(positions)

    except Exception as e:
        print(f"Error getting positions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@account_bp.route('/api/portfolio/real-holdings')
def get_real_holdings():
    """실제 보유 종목 상세 정보 (수익률, ATR 기반 손절/익절)"""
    try:
        # v5.3.2: bot_instance 체크 강화
        if not _bot_instance:
            print("Error: bot_instance is None")
            return jsonify({
                'success': False,
                'message': 'Bot not initialized'
            })

        holdings = []

        # 실제 보유 종목 조회
        if not hasattr(_bot_instance, 'account_api'):
            print("Error: bot_instance has no account_api")
            return jsonify({
                'success': False,
                'message': 'Account API not available'
            })

        # v5.5.0: KRX+NXT 통합 조회
        raw_holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT")

        if not raw_holdings:
            print("[HOLDINGS] 보유 종목 없음")
            return jsonify({
                'success': True,
                'data': []
            })

        print(f"[HOLDINGS] {len(raw_holdings)}개 종목 분석 중...")

        # v5.3.2: 각 종목 처리를 try-except로 감싸서 하나가 실패해도 다른 종목은 계속 처리
        for idx, holding in enumerate(raw_holdings):
            try:
                stock_code = str(holding.get('stk_cd', '')).strip()
                # A 접두사 제거
                if stock_code.startswith('A'):
                    stock_code = stock_code[1:]

                stock_name = holding.get('stk_nm', stock_code)
                quantity = int(float(str(holding.get('rmnd_qty', 0)).replace(',', '')))

                if quantity <= 0:
                    continue

                avg_price = int(float(str(holding.get('avg_prc', 0)).replace(',', '')))
                current_price = int(float(str(holding.get('cur_prc', 0)).replace(',', '')))

                # v5.4.2: 평가금액 계산 (장외 시간 대응)
                eval_amount = int(float(str(holding.get('eval_amt', 0)).replace(',', '')))
                if eval_amount == 0 and current_price > 0:
                    # 장외 시간 등으로 eval_amt이 0인 경우, 직접 계산
                    eval_amount = quantity * current_price

                # 수익률 계산
                pnl = (current_price - avg_price) * quantity
                pnl_rate = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

                # v5.3.2: 기본값 설정 (ATR 계산 실패 시 사용)
                stop_loss_price = int(avg_price * 0.95)  # -5%
                take_profit_price = int(avg_price * 1.10)  # +10%
                kelly_fraction = 0.10
                sharpe_ratio = 0
                max_dd = 0
                rsi = 50
                bb_position = 0.5
                risk_reward_ratio = 2.0

                # ATR 기반 동적 손절/익절 계산 (선택적)
                try:
                    # ATR 조회 (14일 기준)
                    if hasattr(_bot_instance, 'market_api'):
                        print(f"  [{idx+1}/{len(raw_holdings)}] Fetching daily data for {stock_code}...")
                        # 일봉 데이터로 ATR 계산
                        daily_data = _bot_instance.market_api.get_daily_chart(stock_code, period=20)

                        if daily_data and len(daily_data) >= 14:
                            # ATR 계산 (True Range 평균)
                            atr_values = []
                            for i in range(1, min(15, len(daily_data))):
                                high = daily_data[i].get('high', 0)
                                low = daily_data[i].get('low', 0)
                                prev_close = daily_data[i-1].get('close', 0)

                                tr = max(
                                    high - low,
                                    abs(high - prev_close),
                                    abs(low - prev_close)
                                )
                                atr_values.append(tr)

                            if atr_values:
                                atr = sum(atr_values) / len(atr_values)

                                # ATR 기반 손절/익절 (2 ATR)
                                stop_loss_price = int(avg_price - (atr * 2))
                                take_profit_price = int(avg_price + (atr * 3))

                                # Kelly Criterion 계산 (승률 60%, Risk/Reward 1.5배 가정)
                                win_rate = 0.60
                                avg_win_loss_ratio = 1.5
                                kelly_fraction = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
                                kelly_fraction = max(0, min(kelly_fraction, 0.25))  # 최대 25%로 제한

                                # Sharpe Ratio 추정 (최근 20일 수익률 기반)
                                returns = []
                                for j in range(1, len(daily_data)):
                                    close_today = daily_data[j-1].get('close', 0)
                                    close_yesterday = daily_data[j].get('close', 0)
                                    if close_yesterday > 0:
                                        ret = (close_today - close_yesterday) / close_yesterday
                                        returns.append(ret)

                                if returns:
                                    avg_return = sum(returns) / len(returns)
                                    variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                                    std_return = variance ** 0.5
                                    sharpe_ratio = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
                                else:
                                    sharpe_ratio = 0

                                # Maximum Drawdown 계산
                                peak = daily_data[0].get('close', current_price)
                                max_dd = 0
                                for data in daily_data:
                                    price = data.get('close', 0)
                                    if price > peak:
                                        peak = price
                                    dd = (peak - price) / peak if peak > 0 else 0
                                    if dd > max_dd:
                                        max_dd = dd

                                # RSI 계산 (14일)
                                gains = []
                                losses = []
                                for k in range(1, min(15, len(daily_data))):
                                    change = daily_data[k-1].get('close', 0) - daily_data[k].get('close', 0)
                                    if change > 0:
                                        gains.append(change)
                                        losses.append(0)
                                    else:
                                        gains.append(0)
                                        losses.append(abs(change))

                                avg_gain = sum(gains) / len(gains) if gains else 0
                                avg_loss = sum(losses) / len(losses) if losses else 0.01
                                rs = avg_gain / avg_loss if avg_loss > 0 else 0
                                rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50

                                # Bollinger Bands 위치 (20일 SMA, 2 표준편차)
                                closes = [d.get('close', 0) for d in daily_data[:20]]
                                sma_20 = sum(closes) / len(closes) if closes else current_price
                                variance_bb = sum((c - sma_20) ** 2 for c in closes) / len(closes) if closes else 0
                                std_20 = variance_bb ** 0.5
                                bb_upper = sma_20 + (std_20 * 2)
                                bb_lower = sma_20 - (std_20 * 2)
                                bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) if (bb_upper - bb_lower) > 0 else 0.5

                                # Risk/Reward Ratio
                                potential_loss = current_price - stop_loss_price
                                potential_gain = take_profit_price - current_price
                                risk_reward_ratio = potential_gain / potential_loss if potential_loss > 0 else 0

                                print(f"    ✓ ATR-based metrics calculated for {stock_code}")

                except Exception as e:
                    print(f"⚠️ Advanced metrics calculation failed ({stock_code}): {e}")
                    # 기본값은 이미 설정됨

                # 손절/익절까지 거리 계산
                distance_to_stop = ((stop_loss_price - current_price) / current_price * 100) if current_price > 0 else 0
                distance_to_target = ((take_profit_price - current_price) / current_price * 100) if current_price > 0 else 0

                holdings.append({
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'quantity': quantity,
                    'avg_price': avg_price,
                    'current_price': current_price,
                    'eval_amount': eval_amount,
                    'pnl': pnl,
                    'pnl_rate': round(pnl_rate, 2),
                    'stop_loss_price': stop_loss_price,
                    'take_profit_price': take_profit_price,
                    'distance_to_stop': round(distance_to_stop, 2),
                    'distance_to_target': round(distance_to_target, 2),
                    'atr_based': True,  # ATR 기반 여부
                    # 진보된 지표들
                    'kelly_fraction': round(kelly_fraction, 3),
                    'sharpe_ratio': round(sharpe_ratio, 2),
                    'max_drawdown': round(max_dd * 100, 2),
                    'rsi': round(rsi, 1),
                    'bb_position': round(bb_position, 2),
                    'risk_reward_ratio': round(risk_reward_ratio, 2)
                })

                print(f"  [{idx+1}/{len(raw_holdings)}] ✓ {stock_code} processed")

            except Exception as e:
                print(f"  [{idx+1}/{len(raw_holdings)}] ❌ Error processing holding: {e}")
                continue

        print(f"Successfully processed {len(holdings)} holdings")

        return jsonify({
            'success': True,
            'data': holdings
        })

    except Exception as e:
        print(f"❌ 실제 보유 종목 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# v5.7.2: 수익 최적화 API

@account_bp.route('/api/profit-optimization/rules')
def get_optimization_rules():
    """수익 최적화 규칙 조회"""
    try:
        from features.profit_optimizer import get_profit_optimizer

        optimizer = get_profit_optimizer()

        rules_info = []
        for name, rule in optimizer.rules.items():
            rules_info.append({
                'name': name,
                'display_name': rule.name,
                'stop_loss_rate': rule.stop_loss_rate * 100,
                'take_profit_rate': rule.take_profit_rate * 100,
                'trailing_stop_enabled': rule.trailing_stop_enabled,
                'trailing_stop_trigger': rule.trailing_stop_trigger * 100,
                'trailing_stop_distance': rule.trailing_stop_distance * 100,
                'max_holding_days': rule.max_holding_days,
                'partial_profit_enabled': rule.partial_profit_enabled,
                'partial_profit_rate': rule.partial_profit_rate * 100,
                'partial_profit_sell_ratio': rule.partial_profit_sell_ratio * 100
            })

        return jsonify({
            'success': True,
            'rules': rules_info
        })

    except Exception as e:
        print(f"Error getting optimization rules: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@account_bp.route('/api/profit-optimization/summary')
def get_optimization_summary():
    """현재 보유 종목의 수익 최적화 요약"""
    try:
        from features.profit_optimizer import get_profit_optimizer

        if not _bot_instance or not hasattr(_bot_instance, 'account_api'):
            return jsonify({
                'success': False,
                'message': 'Bot not initialized'
            })

        optimizer = get_profit_optimizer()
        holdings = _bot_instance.account_api.get_holdings(market_type="KRX+NXT")

        if not holdings:
            return jsonify({
                'success': True,
                'summary': {
                    'total_positions': 0,
                    'sell_recommended': 0,
                    'hold_recommended': 0,
                    'partial_sell_recommended': 0,
                    'actions': []
                }
            })

        actions = []
        sell_count = 0
        hold_count = 0
        partial_sell_count = 0

        for h in holdings:
            code = str(h.get('stk_cd', '')).replace('A', '')
            name = h.get('stk_nm', '')
            quantity = int(float(str(h.get('rmnd_qty', 0)).replace(',', '')))

            if quantity <= 0:
                continue

            avg_price = int(float(str(h.get('avg_prc', 0)).replace(',', '')))
            current_price = int(float(str(h.get('cur_prc', 0)).replace(',', '')))

            # 최고가 추정
            highest_price = max(current_price, avg_price)
            pnl_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

            if pnl_percent > 0:
                highest_price = current_price

            # 분석
            analysis = optimizer.analyze_position(
                entry_price=avg_price,
                current_price=current_price,
                highest_price=highest_price,
                quantity=quantity,
                days_held=5,
                rule_name='balanced'
            )

            if analysis.action == 'full_sell':
                sell_count += 1
            elif analysis.action == 'partial_sell':
                partial_sell_count += 1
            else:
                hold_count += 1

            actions.append({
                'stock_code': code,  # v6.0.1: 일관성을 위해 'code' → 'stock_code'
                'stock_name': name,  # v6.0.1: 일관성을 위해 'name' → 'stock_name'
                'action': analysis.action,
                'reason': analysis.reason,
                'pnl_percent': pnl_percent
            })

        return jsonify({
            'success': True,
            'summary': {
                'total_positions': len(actions),
                'sell_recommended': sell_count,
                'hold_recommended': hold_count,
                'partial_sell_recommended': partial_sell_count,
                'actions': actions
            }
        })

    except Exception as e:
        print(f"Error getting optimization summary: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        })
