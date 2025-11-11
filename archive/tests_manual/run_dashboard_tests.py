#!/usr/bin/env python3
"""
대시보드 이슈 테스트 실행 스크립트

사용법:
    python tests/manual_tests/run_dashboard_tests.py

또는 main.py에서:
    from tests.manual_tests.run_dashboard_tests import quick_test
    quick_test(bot)
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def quick_test(bot_instance):
    """
    빠른 테스트 (main.py에서 호출용)

    Args:
        bot_instance: 실행 중인 봇 인스턴스
    """
    print("=" * 80)
    print("대시보드 이슈 빠른 테스트")
    print("=" * 80)
    print()

    market_api = bot_instance.market_api if hasattr(bot_instance, 'market_api') else None
    account_api = bot_instance.account_api if hasattr(bot_instance, 'account_api') else None

    # ========================================================================
    # 1. 계좌 잔고
    # ========================================================================
    print("📊 1. 계좌 잔고 계산 테스트")
    print("-" * 80)

    if account_api:
        try:
            from tests.manual_tests.patches.fix_account_balance import AccountBalanceFix

            deposit = account_api.get_deposit()
            holdings = account_api.get_holdings()

            if deposit and holdings is not None:
                # 접근법 1 (추천)
                result = AccountBalanceFix.approach_1_deposit_minus_purchase(deposit, holdings)

                print(f"✅ 계좌 잔고 계산 성공")
                print(f"   예수금: {result['_debug']['deposit_amount']:,}원")
                print(f"   구매원가: {result['_debug']['total_purchase_cost']:,}원")
                print(f"   실제 사용가능액: {result['cash']:,}원")
                print(f"   총 자산: {result['total_assets']:,}원")
                print(f"   보유주식: {result['stock_value']:,}원")
                print(f"   손익: {result['profit_loss']:,}원 ({result['profit_loss_percent']:.2f}%)")
            else:
                print("⚠️  deposit 또는 holdings 조회 실패")

        except Exception as e:
            print(f"❌ 계좌 잔고 테스트 실패: {e}")
    else:
        print("⚠️  account_api 없음")

    print()

    # ========================================================================
    # 2. NXT 가격 조회
    # ========================================================================
    print("💰 2. NXT 시장가격 조회 테스트")
    print("-" * 80)

    if market_api:
        try:
            from tests.manual_tests.patches.fix_nxt_price import MarketAPIExtended, NXTPriceFix

            # 현재 시간 정보
            print(f"정규시장 시간: {NXTPriceFix.is_regular_market_time()}")
            print(f"NXT 거래시간: {NXTPriceFix.is_nxt_time()}")
            print()

            # 테스트 종목
            test_stock = '005930'  # 삼성전자

            market_api_ext = MarketAPIExtended(market_api, account_api)
            price_info = market_api_ext.get_current_price_with_source(test_stock)

            if price_info['price'] > 0:
                print(f"✅ 가격 조회 성공: {test_stock}")
                print(f"   현재가: {price_info['price']:,}원")
                print(f"   가격 소스: {price_info['source']}")
                print(f"   시도한 소스: {price_info.get('sources_tried', [])}")
                print(f"   NXT 시간: {price_info['is_nxt_time']}")
            else:
                print(f"⚠️  가격 조회 실패: {test_stock}")
                print(f"   시도한 소스: {price_info.get('sources_tried', [])}")

        except Exception as e:
            print(f"❌ NXT 가격 조회 테스트 실패: {e}")
    else:
        print("⚠️  market_api 없음")

    print()

    # ========================================================================
    # 3. AI 스캐닝 연동
    # ========================================================================
    print("🤖 3. AI 스캐닝 종목 연동 테스트")
    print("-" * 80)

    try:
        from tests.manual_tests.patches.fix_ai_scanning import get_scanning_info

        # 접근법 3 (추천)
        scanning_info = get_scanning_info(bot_instance, method='combined')

        print(f"✅ AI 스캐닝 정보 조회 성공")
        print(f"   Fast Scan (스캐닝 종목): {scanning_info['fast_scan']['count']}개")
        print(f"     - 마지막 실행: {scanning_info['fast_scan']['last_run']}")
        print(f"     - 소스: {scanning_info['fast_scan'].get('source', 'N/A')}")

        print(f"   Deep Scan (AI 분석 완료): {scanning_info['deep_scan']['count']}개")
        print(f"     - 마지막 실행: {scanning_info['deep_scan']['last_run']}")
        print(f"     - 소스: {scanning_info['deep_scan'].get('source', 'N/A')}")

        print(f"   AI Scan (매수 대기): {scanning_info['ai_scan']['count']}개")
        print(f"     - 마지막 실행: {scanning_info['ai_scan']['last_run']}")
        print(f"     - 소스: {scanning_info['ai_scan'].get('source', 'N/A')}")

        # 상세 정보 (있는 경우)
        if scanning_info['fast_scan']['count'] > 0 and scanning_info['fast_scan'].get('results'):
            print("\n   Fast Scan 상위 종목:")
            for stock in scanning_info['fast_scan']['results'][:3]:
                print(f"     - {stock['name']} ({stock['code']}): {stock.get('score', 0):.1f}점")

    except Exception as e:
        print(f"❌ AI 스캐닝 연동 테스트 실패: {e}")

    print()
    print("=" * 80)
    print("빠른 테스트 완료")
    print("=" * 80)


def full_test(bot_instance):
    """
    전체 테스트 (모든 접근법)

    Args:
        bot_instance: 실행 중인 봇 인스턴스
    """
    from tests.manual_tests.test_dashboard_issues import run_all_tests

    market_api = bot_instance.market_api if hasattr(bot_instance, 'market_api') else None
    account_api = bot_instance.account_api if hasattr(bot_instance, 'account_api') else None

    results = run_all_tests(
        bot_instance=bot_instance,
        market_api=market_api,
        account_api=account_api
    )

    return results


def apply_fixes(bot_instance):
    """
    수정 사항 적용 (대시보드에 패치 적용)

    Args:
        bot_instance: 실행 중인 봇 인스턴스
    """
    print("=" * 80)
    print("대시보드 수정 사항 적용")
    print("=" * 80)
    print()

    try:
        # 1. 계좌 잔고 계산 수정
        from tests.manual_tests.patches.fix_account_balance import AccountBalanceFix
        print("✅ AccountBalanceFix 로드됨")

        # 2. NXT 가격 조회 수정
        from tests.manual_tests.patches.fix_nxt_price import MarketAPIExtended
        market_api_ext = MarketAPIExtended(
            bot_instance.market_api if hasattr(bot_instance, 'market_api') else None,
            bot_instance.account_api if hasattr(bot_instance, 'account_api') else None
        )
        print("✅ MarketAPIExtended 생성됨")

        # 3. AI 스캐닝 연동 수정
        from tests.manual_tests.patches.fix_ai_scanning import get_scanning_info
        print("✅ AIScanningFix 로드됨")

        print()
        print("수정 사항이 메모리에 로드되었습니다.")
        print("대시보드 코드에 직접 적용하려면 README_DASHBOARD_FIXES.md를 참고하세요.")
        print()

        # 헬퍼 함수 제공
        bot_instance._fix_account_balance = lambda: AccountBalanceFix.approach_1_deposit_minus_purchase(
            bot_instance.account_api.get_deposit(),
            bot_instance.account_api.get_holdings()
        )

        bot_instance._fix_get_price = lambda stock_code: market_api_ext.get_current_price_with_source(stock_code)

        bot_instance._fix_scanning_info = lambda: get_scanning_info(bot_instance, method='combined')

        print("✅ 봇 인스턴스에 헬퍼 함수 추가됨:")
        print("   - bot._fix_account_balance()")
        print("   - bot._fix_get_price(stock_code)")
        print("   - bot._fix_scanning_info()")
        print()

    except Exception as e:
        print(f"❌ 수정 사항 적용 실패: {e}")
        import traceback
        traceback.print_exc()


def interactive_test():
    """대화형 테스트 메뉴"""
    print("=" * 80)
    print("대시보드 이슈 테스트 - 대화형 모드")
    print("=" * 80)
    print()
    print("이 스크립트는 봇이 실행 중일 때 사용해야 합니다.")
    print()
    print("사용법:")
    print("1. main.py를 실행합니다")
    print("2. Python 콘솔에서 다음 명령을 실행:")
    print()
    print("   from tests.manual_tests.run_dashboard_tests import quick_test")
    print("   quick_test(bot)")
    print()
    print("또는 전체 테스트:")
    print()
    print("   from tests.manual_tests.run_dashboard_tests import full_test")
    print("   full_test(bot)")
    print()
    print("또는 수정 사항 적용:")
    print()
    print("   from tests.manual_tests.run_dashboard_tests import apply_fixes")
    print("   apply_fixes(bot)")
    print()


if __name__ == "__main__":
    interactive_test()
