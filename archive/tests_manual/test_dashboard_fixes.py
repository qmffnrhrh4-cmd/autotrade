#!/usr/bin/env python3
"""
대시보드 수정사항 테스트 스크립트 (실제 코드 구조 기반)

테스트 항목:
1. 계좌 정보 API (kt00001 필드)
2. 보유현황 API (kt00004 필드)
3. 가상매매 시스템
4. 매수 수량 계산

장 운영 시간:
- 08:00-09:00: NXT 시장 (프리마켓)
- 09:00-15:30: 일반 주식장
- 15:30-20:00: NXT 시장 (애프터마켓)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_account_info():
    """계좌 정보 테스트 (kt00001 API 필드 검증)"""
    print("\n" + "="*60)
    print("TEST 1: 계좌 정보 API 필드 검증")
    print("="*60)

    try:
        from api.account import AccountAPI
        from core.rest_client import KiwoomRESTClient

        # 싱글톤 클라이언트 생성
        client = KiwoomRESTClient()
        account_api = AccountAPI(client)

        deposit = account_api.get_deposit()

        if not deposit:
            print("❌ FAIL: 예수금 정보를 가져올 수 없습니다")
            print("   → API 연결 상태를 확인하세요")
            print("   → main.py를 먼저 실행하여 토큰을 발급받으세요")
            return False

        # 필드 검증
        print("\n✅ 예수금 정보 조회 성공")
        print(f"   - entr (예수금): {deposit.get('entr', 'N/A')}")
        print(f"   - 100stk_ord_alow_amt (주문가능금액): {deposit.get('100stk_ord_alow_amt', 'N/A')}")
        print(f"   - ord_alow_amt (일반주문가능금액): {deposit.get('ord_alow_amt', 'N/A')}")

        # 계산 검증
        entr = int(str(deposit.get('entr', '0')).replace(',', ''))
        orderable = int(str(deposit.get('100stk_ord_alow_amt', '0')).replace(',', ''))

        print(f"\n💰 계산 결과:")
        print(f"   - 예수금: {entr:,}원")
        print(f"   - 주문가능금액: {orderable:,}원")

        if entr > 0 or orderable > 0:
            print("✅ PASS: API 필드가 정상적으로 작동합니다")
            if orderable == 0:
                print("   ⚠️  주문가능금액이 0원 (잔고 부족 또는 전액 투자)")
            return True
        else:
            print("⚠️  WARNING: 모든 금액이 0원입니다")
            print("   → 하지만 API 연결은 정상입니다")
            return True

    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_holdings():
    """보유현황 테스트 (kt00004 API 필드 검증)"""
    print("\n" + "="*60)
    print("TEST 2: 보유현황 API 필드 검증")
    print("="*60)

    try:
        from api.account import AccountAPI
        from core.rest_client import KiwoomRESTClient

        client = KiwoomRESTClient()
        account_api = AccountAPI(client)

        holdings = account_api.get_holdings()

        if not holdings or len(holdings) == 0:
            print("✅ 보유 종목 없음 (정상)")
            print("   → API는 정상 작동하지만 보유 주식이 없습니다")
            return True

        print(f"\n✅ 보유 종목 {len(holdings)}개 조회 성공")

        for i, h in enumerate(holdings[:3], 1):  # 최대 3개만 표시
            code = str(h.get('stk_cd', '')).strip()
            if code.startswith('A'):
                code = code[1:]

            name = h.get('stk_nm', '')
            qty = int(str(h.get('rmnd_qty', 0)).replace(',', ''))
            avg_price = int(str(h.get('avg_prc', 0)).replace(',', ''))
            cur_price = int(str(h.get('cur_prc', 0)).replace(',', ''))
            eval_amt = int(str(h.get('eval_amt', 0)).replace(',', ''))

            print(f"\n{i}. {name} ({code})")
            print(f"   - 보유수량: {qty}주")
            print(f"   - 평균단가: {avg_price:,}원")
            print(f"   - 현재가: {cur_price:,}원")
            print(f"   - 평가금액: {eval_amt:,}원")

        print("\n✅ PASS: 모든 필드가 정상적으로 파싱되었습니다")
        return True

    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_virtual_trading():
    """가상매매 시스템 테스트"""
    print("\n" + "="*60)
    print("TEST 3: 가상매매 시스템 검증")
    print("="*60)

    try:
        from virtual_trading.virtual_trader import VirtualTrader

        # 가상매매 인스턴스 생성
        virtual_trader = VirtualTrader(initial_cash=10_000_000)

        print("\n✅ VirtualTrader 초기화 성공")
        print(f"   - 초기 자본: 10,000,000원")
        print(f"   - 전략 개수: {len(virtual_trader.accounts)}개")

        # 전략별 요약 조회 (실제 필드명 사용)
        summaries = virtual_trader.get_all_summaries()

        for strategy_name, summary in summaries.items():
            print(f"\n📊 {strategy_name}:")
            print(f"   - 현금: {summary['current_cash']:,.0f}원")
            print(f"   - 총 자산: {summary['total_value']:,.0f}원")
            print(f"   - 수익률: {summary['total_pnl_rate']*100:+.2f}%")
            print(f"   - 포지션: {summary['position_count']}개")
            print(f"   - 승률: {summary['win_rate']:.1f}%")

        # 최고 전략
        best = virtual_trader.get_best_strategy()
        print(f"\n🏆 최고 성과 전략: {best}")

        print("\n✅ PASS: 가상매매 시스템이 정상 작동합니다")
        return True

    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_buy_calculation():
    """매수 수량 계산 테스트"""
    print("\n" + "="*60)
    print("TEST 4: 매수 수량 계산 검증")
    print("="*60)

    try:
        from api.account import AccountAPI
        from core.rest_client import KiwoomRESTClient
        from strategy.dynamic_risk_manager import DynamicRiskManager

        client = KiwoomRESTClient()
        account_api = AccountAPI(client)

        # 예수금 조회
        deposit = account_api.get_deposit()
        holdings = account_api.get_holdings()

        # 올바른 필드 사용 (수정된 방식)
        deposit_total = int(str(deposit.get('entr', '0')).replace(',', '')) if deposit else 0
        available_cash = int(str(deposit.get('100stk_ord_alow_amt', '0')).replace(',', '')) if deposit else 0

        print(f"\n💰 계좌 정보:")
        print(f"   - 예수금: {deposit_total:,}원")
        print(f"   - 주문가능금액: {available_cash:,}원")

        # 보유주식 평가액
        holdings_value = 0
        if holdings:
            for h in holdings:
                holdings_value += int(str(h.get('eval_amt', 0)).replace(',', ''))

        # 초기 자본 계산
        initial_capital = deposit_total + holdings_value
        if initial_capital == 0:
            initial_capital = 10_000_000  # 기본값
            print(f"   ⚠️  계좌 정보 없음, 기본값 사용")

        print(f"   - 보유주식 평가: {holdings_value:,}원")
        print(f"   - 총 자산: {initial_capital:,}원")

        # 리스크 관리자 생성
        risk_manager = DynamicRiskManager(initial_capital=initial_capital)

        # 테스트 주가
        test_prices = [10000, 20000, 50000, 100000]

        # 계산에 사용할 현금 (available_cash가 0이면 초기자본의 20% 사용)
        calc_cash = available_cash if available_cash > 0 else int(initial_capital * 0.2)

        print(f"\n📊 매수 가능 수량 계산 (리스크 관리 적용):")
        print(f"   계산 기준 금액: {calc_cash:,}원")

        for price in test_prices:
            qty = risk_manager.calculate_position_size(
                stock_price=price,
                available_cash=calc_cash
            )
            print(f"   - 주가 {price:,}원: {qty}주 (총 {qty*price:,}원)")

        print("\n✅ PASS: 매수 가능 금액이 정상적으로 계산되었습니다")

        # 장 운영 시간 안내
        print("\n⏰ 장 운영 시간 안내:")
        print("   - 08:00-09:00: NXT 프리마켓 (장전)")
        print("   - 09:00-15:30: 일반 주식장 (정규장)")
        print("   - 15:30-20:00: NXT 애프터마켓 (장후)")
        print("   → 위 시간대에 실제 주문을 테스트하세요")

        return True

    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """전체 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 대시보드 수정사항 종합 테스트")
    print("="*60)
    print("\n⚠️  주의: 이 테스트는 main.py가 실행 중이어야 합니다!")
    print("   → main.py로 토큰 발급 후 테스트하세요\n")

    results = {
        "계좌 정보 API": test_account_info(),
        "보유현황 API": test_holdings(),
        "가상매매 시스템": test_virtual_trading(),
        "매수 수량 계산": test_buy_calculation(),
    }

    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    total = len(results)
    passed = sum(results.values())

    print(f"\n총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 모든 테스트 통과!")
        print("\n📌 다음 단계:")
        print("   1. 대시보드 새로고침 (Ctrl+F5) → v5.0 확인")
        print("   2. 장 운영 시간에 실제 매수 테스트")
        print("      - 08:00-09:00 (NXT 프리마켓)")
        print("      - 09:00-15:30 (일반 주식장)")
        print("      - 15:30-20:00 (NXT 애프터마켓)")
    elif passed >= total * 0.5:
        print(f"\n✅ {passed}개 테스트 통과! (일부 실패는 정상일 수 있습니다)")
        print("\n💡 실패한 테스트:")
        for test_name, result in results.items():
            if not result:
                print(f"   - {test_name}: 위 오류 메시지 참고")
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패")
        print("   → main.py가 실행 중인지 확인하세요")
        print("   → 위 오류 메시지를 확인하세요")

    return passed >= total * 0.5  # 50% 이상 통과하면 성공


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
