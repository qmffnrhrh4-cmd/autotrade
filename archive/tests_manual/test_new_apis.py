"""
신규 API 테스트 스크립트
- ka10047: 체결강도
- ka90013: 프로그램매매
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.rest_client import KiwoomRESTClient
from api.market import MarketAPI

def test_execution_intensity():
    """체결강도 API 테스트"""
    print("\n" + "="*80)
    print("📊 체결강도 API 테스트 (ka10047)")
    print("="*80)

    try:
        client = KiwoomRESTClient()
        market_api = MarketAPI(client)

        # 삼성전자 테스트
        test_stock = "005930"
        print(f"\n테스트 종목: {test_stock} (삼성전자)")

        result = market_api.get_execution_intensity(test_stock)

        if result:
            print(f"\n✅ 성공!")
            print(f"   체결강도: {result.get('execution_intensity')}")
            print(f"   날짜: {result.get('date')}")
            print(f"   현재가: {result.get('current_price')}")
            print(f"   등락률: {result.get('change_rate')}")
            print(f"   거래량: {result.get('volume')}")
            return True
        else:
            print("\n❌ 실패: 데이터를 받아오지 못했습니다")
            return False

    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_program_trading():
    """프로그램매매 API 테스트"""
    print("\n" + "="*80)
    print("📊 프로그램매매 API 테스트 (ka90013)")
    print("="*80)

    try:
        client = KiwoomRESTClient()
        market_api = MarketAPI(client)

        # 삼성전자 테스트
        test_stock = "005930"
        print(f"\n테스트 종목: {test_stock} (삼성전자)")

        result = market_api.get_program_trading(test_stock)

        if result:
            print(f"\n✅ 성공!")
            print(f"   프로그램순매수: {result.get('program_net_buy'):,}원")
            print(f"   프로그램매수: {result.get('program_buy')}")
            print(f"   프로그램매도: {result.get('program_sell')}")
            print(f"   날짜: {result.get('date')}")
            print(f"   현재가: {result.get('current_price')}")
            return True
        else:
            print("\n❌ 실패: 데이터를 받아오지 못했습니다")
            return False

    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 함수"""
    print("\n" + "="*80)
    print("🧪 신규 API 테스트 시작")
    print("="*80)

    results = []

    # 체결강도 테스트
    result1 = test_execution_intensity()
    results.append(("체결강도 (ka10047)", result1))

    # 프로그램매매 테스트
    result2 = test_program_trading()
    results.append(("프로그램매매 (ka90013)", result2))

    # 결과 요약
    print("\n" + "="*80)
    print("📊 테스트 결과 요약")
    print("="*80)

    for name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"   {name}: {status}")

    print("\n" + "="*80)

    all_success = all(r[1] for r in results)
    if all_success:
        print("🎉 모든 테스트 성공!")
    else:
        print("⚠️  일부 테스트 실패")

    print("="*80 + "\n")

    return all_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
