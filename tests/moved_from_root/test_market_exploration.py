"""
Market Exploration Diversification Test - v5.9
외국인/기관 매매 기반 스크리닝 테스트
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from research.screener import Screener
from research.data_fetcher import DataFetcher
from api.kiwoom_rest_client import KiwoomRESTClient


def test_data_fetcher_methods():
    """Test DataFetcher new methods"""
    print("=" * 60)
    print("Testing DataFetcher - Foreign/Institution Ranking Methods")
    print("=" * 60)

    try:
        client = KiwoomRESTClient()
        fetcher = DataFetcher(client)

        # Test 1: 외국인 순매수 순위
        print("\n[Test 1] 외국인 순매수 순위 조회")
        foreign_buy = fetcher.get_foreign_buying_rank(market='KOSPI', limit=5)
        print(f"✓ 결과: {len(foreign_buy)}개 종목")
        if foreign_buy:
            print(f"  예시: {foreign_buy[0]}")

        # Test 2: 기관 순매수 순위
        print("\n[Test 2] 기관 순매수 순위 조회")
        inst_buy = fetcher.get_institution_buying_rank(market='KOSPI', limit=5)
        print(f"✓ 결과: {len(inst_buy)}개 종목")
        if inst_buy:
            print(f"  예시: {inst_buy[0]}")

        # Test 3: 외국인 순매도 순위
        print("\n[Test 3] 외국인 순매도 순위 조회")
        foreign_sell = fetcher.get_foreign_selling_rank(market='KOSPI', limit=5)
        print(f"✓ 결과: {len(foreign_sell)}개 종목")
        if foreign_sell:
            print(f"  예시: {foreign_sell[0]}")

        # Test 4: 기관 순매도 순위
        print("\n[Test 4] 기관 순매도 순위 조회")
        inst_sell = fetcher.get_institution_selling_rank(market='KOSPI', limit=5)
        print(f"✓ 결과: {len(inst_sell)}개 종목")
        if inst_sell:
            print(f"  예시: {inst_sell[0]}")

        print("\n✅ DataFetcher 테스트 완료!")
        return True

    except Exception as e:
        print(f"\n❌ DataFetcher 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_screener_methods():
    """Test Screener new methods"""
    print("\n" + "=" * 60)
    print("Testing Screener - Investor-based Screening Methods")
    print("=" * 60)

    try:
        client = KiwoomRESTClient()
        screener = Screener(client)

        # Test 1: 외국인 순매수 스크리닝
        print("\n[Test 1] 외국인 순매수 스크리닝")
        foreign_buy = screener.screen_by_foreign_buying(market='KOSPI', limit=5)
        print(f"✓ 결과: {len(foreign_buy)}개 종목")
        if foreign_buy:
            print(f"  예시: {foreign_buy[0]}")

        # Test 2: 기관 순매수 스크리닝
        print("\n[Test 2] 기관 순매수 스크리닝")
        inst_buy = screener.screen_by_institution_buying(market='KOSPI', limit=5)
        print(f"✓ 결과: {len(inst_buy)}개 종목")
        if inst_buy:
            print(f"  예시: {inst_buy[0]}")

        # Test 3: 스마트머니 스크리닝
        print("\n[Test 3] 스마트머니 (외국인+기관 동시 순매수) 스크리닝")
        smart_money = screener.screen_by_smart_money(market='KOSPI', limit=10)
        print(f"✓ 결과: {len(smart_money)}개 종목")
        if smart_money:
            print(f"  예시: {smart_money[0]}")

        # Test 4: 외국인 순매도 스크리닝
        print("\n[Test 4] 외국인 순매도 스크리닝")
        foreign_sell = screener.screen_by_foreign_selling(market='KOSPI', limit=5)
        print(f"✓ 결과: {len(foreign_sell)}개 종목")
        if foreign_sell:
            print(f"  예시: {foreign_sell[0]}")

        # Test 5: 기관 순매도 스크리닝
        print("\n[Test 5] 기관 순매도 스크리닝")
        inst_sell = screener.screen_by_institution_selling(market='KOSPI', limit=5)
        print(f"✓ 결과: {len(inst_sell)}개 종목")
        if inst_sell:
            print(f"  예시: {inst_sell[0]}")

        print("\n✅ Screener 테스트 완료!")
        return True

    except Exception as e:
        print(f"\n❌ Screener 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Market Exploration Diversification Test - v5.9")
    print("=" * 60)

    results = []

    # Test DataFetcher
    results.append(("DataFetcher", test_data_fetcher_methods()))

    # Test Screener
    results.append(("Screener", test_screener_methods()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패")

    return all_passed


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 테스트 중단됨")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
