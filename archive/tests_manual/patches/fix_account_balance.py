"""
계좌 잔고 계산 수정 패치
문제: 인출가능액(ord_alow_amt)이 아닌 실제 사용가능액을 표시해야 함
해결: 예수금 - 보유주식 구매원가

다양한 접근법:
1. approach_1: 예수금(dps_amt) - 총 구매원가(pchs_amt)
2. approach_2: 예수금에서 보유주식 평균단가*수량 차감
3. approach_3: 계좌평가현황 API의 계산된 값 사용
"""

from typing import Dict, Any, List


class AccountBalanceFix:
    """계좌 잔고 계산 수정"""

    @staticmethod
    def approach_1_deposit_minus_purchase(deposit: Dict, holdings: List[Dict]) -> Dict[str, Any]:
        """
        접근법 1: 키움증권 API의 실제 사용가능액 필드 사용

        kt00001 API 응답에서:
        - entr: 예수금
        - 100stk_ord_alow_amt: 100% 주문가능금액 (실제 사용가능액)
        - ord_alow_amt: 일반 주문가능금액 (보수적)
        """
        # 예수금 (entr 필드)
        deposit_amount = int(deposit.get('entr', '0').replace(',', ''))

        # 실제 사용가능액 (100% 주문가능금액)
        available_cash = int(deposit.get('100stk_ord_alow_amt', '0').replace(',', ''))

        # 보유주식 총 구매원가 (추가 정보용)
        total_purchase_cost = sum(int(str(h.get('pchs_amt', 0)).replace(',', '')) for h in holdings)

        # 보유주식 현재가치
        stock_value = sum(int(str(h.get('eval_amt', 0)).replace(',', '')) for h in holdings)

        # 총 자산 = 예수금 + 보유주식 평가액
        total_assets = deposit_amount + stock_value

        # 손익
        profit_loss = stock_value - total_purchase_cost
        profit_loss_percent = (profit_loss / total_purchase_cost * 100) if total_purchase_cost > 0 else 0

        return {
            'total_assets': total_assets,
            'cash': available_cash,  # 실제 사용가능액 (100stk_ord_alow_amt)
            'stock_value': stock_value,
            'profit_loss': profit_loss,
            'profit_loss_percent': profit_loss_percent,
            'open_positions': len(holdings),

            # 디버깅 정보
            '_debug': {
                'deposit_amount': deposit_amount,  # entr
                'available_cash': available_cash,  # 100stk_ord_alow_amt
                'total_purchase_cost': total_purchase_cost,
                'ord_alow_amt': int(deposit.get('ord_alow_amt', '0').replace(',', '')),  # 참고용
                'field': '100stk_ord_alow_amt'
            }
        }

    @staticmethod
    def approach_2_manual_calculation(deposit: Dict, holdings: List[Dict]) -> Dict[str, Any]:
        """
        접근법 2: 수동 계산

        평균단가 * 수량으로 직접 계산
        """
        # 예수금
        deposit_amount = int(deposit.get('dps_amt', 0))

        # 보유주식별 계산
        total_purchase_cost = 0
        stock_value = 0

        for h in holdings:
            quantity = int(h.get('hldg_qty', h.get('rmnd_qty', 0)))
            avg_price = int(h.get('pchs_avg_pric', h.get('avg_prc', 0)))
            current_price = int(h.get('prpr', h.get('cur_prc', 0)))

            # 구매원가 = 평균단가 * 수량
            purchase_cost = avg_price * quantity
            # 현재가치 = 현재가 * 수량
            current_value = current_price * quantity

            total_purchase_cost += purchase_cost
            stock_value += current_value

        # 실제 사용가능액
        available_cash = deposit_amount - total_purchase_cost

        # 총 자산
        total_assets = deposit_amount + stock_value

        # 손익
        profit_loss = stock_value - total_purchase_cost
        profit_loss_percent = (profit_loss / total_purchase_cost * 100) if total_purchase_cost > 0 else 0

        return {
            'total_assets': total_assets,
            'cash': available_cash,
            'stock_value': stock_value,
            'profit_loss': profit_loss,
            'profit_loss_percent': profit_loss_percent,
            'open_positions': len(holdings),

            '_debug': {
                'deposit_amount': deposit_amount,
                'total_purchase_cost': total_purchase_cost,
                'calculation': 'manual avg_price * quantity'
            }
        }

    @staticmethod
    def approach_3_account_evaluation(account_api, market_type: str = "KRX") -> Dict[str, Any]:
        """
        접근법 3: 계좌평가현황 API 사용

        kt00004 API가 제공하는 계산된 값 활용
        """
        account_eval = account_api.get_account_evaluation(market_type=market_type)

        if not account_eval or account_eval.get('return_code') != 0:
            raise ValueError("계좌평가현황 조회 실패")

        # 예수금
        deposit_amount = int(account_eval.get('dps_amt', 0))

        # 총 매입금액
        total_purchase = int(account_eval.get('tot_pchs_amt', 0))

        # 총 평가금액
        total_eval = int(account_eval.get('tot_eval_amt', 0))

        # 실제 사용가능액
        available_cash = deposit_amount - total_purchase

        # 보유종목 수
        holdings = account_eval.get('stk_acnt_evlt_prst', [])

        # 손익
        profit_loss = total_eval - total_purchase
        profit_loss_percent = (profit_loss / total_purchase * 100) if total_purchase > 0 else 0

        return {
            'total_assets': deposit_amount + total_eval,
            'cash': available_cash,
            'stock_value': total_eval,
            'profit_loss': profit_loss,
            'profit_loss_percent': profit_loss_percent,
            'open_positions': len(holdings),

            '_debug': {
                'deposit_amount': deposit_amount,
                'total_purchase': total_purchase,
                'total_eval': total_eval,
                'source': 'kt00004 API'
            }
        }


# ============================================================================
# 대시보드 적용 예시
# ============================================================================

def get_account_fixed_approach_1(bot_instance, test_mode_active=False, test_date=None):
    """
    수정된 get_account() 함수 - 접근법 1

    dashboard/app_apple.py의 get_account() 대체용
    """
    try:
        if bot_instance and hasattr(bot_instance, 'account_api'):
            # 실제 API에서 데이터 가져오기
            deposit = bot_instance.account_api.get_deposit()
            holdings = bot_instance.account_api.get_holdings()

            if deposit and holdings is not None:
                # 수정된 계산 로직 사용
                result = AccountBalanceFix.approach_1_deposit_minus_purchase(deposit, holdings)
                result['test_mode'] = test_mode_active
                result['test_date'] = test_date
                return result

        # 실패 시 기본값
        return {
            'total_assets': 0,
            'cash': 0,
            'stock_value': 0,
            'profit_loss': 0,
            'profit_loss_percent': 0,
            'open_positions': 0,
            'test_mode': test_mode_active,
            'test_date': test_date
        }

    except Exception as e:
        print(f"Error getting account info: {e}")
        return {
            'total_assets': 0,
            'cash': 0,
            'stock_value': 0,
            'profit_loss': 0,
            'profit_loss_percent': 0,
            'open_positions': 0,
            'test_mode': test_mode_active,
            'test_date': test_date
        }


def get_account_fixed_approach_2(bot_instance, test_mode_active=False, test_date=None):
    """
    수정된 get_account() 함수 - 접근법 2

    수동 계산 방식
    """
    try:
        if bot_instance and hasattr(bot_instance, 'account_api'):
            deposit = bot_instance.account_api.get_deposit()
            holdings = bot_instance.account_api.get_holdings()

            if deposit and holdings is not None:
                result = AccountBalanceFix.approach_2_manual_calculation(deposit, holdings)
                result['test_mode'] = test_mode_active
                result['test_date'] = test_date
                return result

        return {
            'total_assets': 0,
            'cash': 0,
            'stock_value': 0,
            'profit_loss': 0,
            'profit_loss_percent': 0,
            'open_positions': 0,
            'test_mode': test_mode_active,
            'test_date': test_date
        }

    except Exception as e:
        print(f"Error getting account info: {e}")
        return {
            'total_assets': 0,
            'cash': 0,
            'stock_value': 0,
            'profit_loss': 0,
            'profit_loss_percent': 0,
            'open_positions': 0,
            'test_mode': test_mode_active,
            'test_date': test_date
        }


def get_account_fixed_approach_3(bot_instance, test_mode_active=False, test_date=None):
    """
    수정된 get_account() 함수 - 접근법 3

    계좌평가현황 API 기반
    """
    try:
        if bot_instance and hasattr(bot_instance, 'account_api'):
            result = AccountBalanceFix.approach_3_account_evaluation(
                bot_instance.account_api,
                market_type="KRX"
            )
            result['test_mode'] = test_mode_active
            result['test_date'] = test_date
            return result

        return {
            'total_assets': 0,
            'cash': 0,
            'stock_value': 0,
            'profit_loss': 0,
            'profit_loss_percent': 0,
            'open_positions': 0,
            'test_mode': test_mode_active,
            'test_date': test_date
        }

    except Exception as e:
        print(f"Error getting account info: {e}")
        return {
            'total_assets': 0,
            'cash': 0,
            'stock_value': 0,
            'profit_loss': 0,
            'profit_loss_percent': 0,
            'open_positions': 0,
            'test_mode': test_mode_active,
            'test_date': test_date
        }


# ============================================================================
# 테스트
# ============================================================================

if __name__ == "__main__":
    print("계좌 잔고 계산 수정 패치")
    print()
    print("사용법:")
    print("1. 접근법 1 (추천): deposit - purchase_cost")
    print("   result = AccountBalanceFix.approach_1_deposit_minus_purchase(deposit, holdings)")
    print()
    print("2. 접근법 2: 수동 계산")
    print("   result = AccountBalanceFix.approach_2_manual_calculation(deposit, holdings)")
    print()
    print("3. 접근법 3: 계좌평가현황 API")
    print("   result = AccountBalanceFix.approach_3_account_evaluation(account_api)")
    print()
    print("대시보드 적용:")
    print("  dashboard/app_apple.py의 get_account() 함수를")
    print("  get_account_fixed_approach_1()로 교체")
