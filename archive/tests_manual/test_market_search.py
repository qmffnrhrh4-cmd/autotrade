#!/usr/bin/env python3
"""
시장탐색 기능 직접 테스트
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core import KiwoomRESTClient
from research import DataFetcher


def test_volume_rank():
    """거래량 순위 조회 테스트"""
    print("=" * 80)
    print("시장탐색 기능 테스트 - 거래량 순위")
    print("=" * 80)

    try:
        # 1. REST 클라이언트 초기화
        print("\n1. REST 클라이언트 초기화 중...")
        client = KiwoomRESTClient()
        print("✅ REST 클라이언트 초기화 완료")

        # 2. DataFetcher 생성
        print("\n2. DataFetcher 생성 중...")
        fetcher = DataFetcher(client)
        print("✅ DataFetcher 생성 완료")

        # 3. 거래량 순위 조회
        print("\n3. 거래량 순위 조회 중...")
        print("   - 시장: KOSPI")
        print("   - 개수: 20개")

        result = fetcher.get_volume_rank(market='KOSPI', limit=20)

        print(f"\n✅ 조회 완료! {len(result)}개 종목")

        # 4. 결과 출력
        if result:
            print("\n" + "=" * 80)
            print("거래량 순위 결과")
            print("=" * 80)
            print(f"{'순위':<5} {'종목명':<15} {'종목코드':<10} {'현재가':>12} {'등락률':>10} {'거래량':>15}")
            print("-" * 80)

            for i, item in enumerate(result[:10], 1):  # 상위 10개만 출력
                name = item.get('name', item.get('stock_name', '-'))
                code = item.get('code', item.get('stock_code', '-'))
                price = item.get('price', item.get('current_price', 0))
                rate = item.get('change_rate', item.get('rate', 0))
                volume = item.get('volume', item.get('trading_volume', 0))

                print(f"{i:<5} {name:<15} {code:<10} {price:>12,}원 {rate:>9.2f}% {volume:>15,}")

            print("\n✅ 시장탐색 기능 정상 작동!")
            return True
        else:
            print("\n❌ 결과가 비어있습니다.")
            print("   가능한 원인:")
            print("   1. API 키 설정 오류")
            print("   2. 네트워크 오류")
            print("   3. 시장 휴장")
            return False

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_price_change_rank():
    """등락률 순위 조회 테스트"""
    print("\n" + "=" * 80)
    print("시장탐색 기능 테스트 - 상승률 순위")
    print("=" * 80)

    try:
        client = KiwoomRESTClient()
        fetcher = DataFetcher(client)

        print("\n상승률 순위 조회 중...")
        print("   - 시장: KOSDAQ")
        print("   - 정렬: 상승")
        print("   - 개수: 10개")

        result = fetcher.get_price_change_rank(market='KOSDAQ', sort='rise', limit=10)

        print(f"\n✅ 조회 완료! {len(result)}개 종목")

        if result:
            print("\n상위 3개 종목:")
            for i, item in enumerate(result[:3], 1):
                name = item.get('name', '-')
                rate = item.get('change_rate', 0)
                print(f"   {i}. {name}: {rate:+.2f}%")

            return True
        else:
            print("\n❌ 결과가 비어있습니다.")
            return False

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        return False


def main():
    """메인 함수"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║         시장탐색 기능 직접 테스트                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

이 스크립트는 DataFetcher를 직접 호출하여
시장탐색 기능이 정상 작동하는지 확인합니다.

대시보드를 실행하지 않아도 테스트할 수 있습니다.
    """)

    # Test 1: 거래량 순위
    success1 = test_volume_rank()

    # Test 2: 등락률 순위
    success2 = test_price_change_rank()

    # 결과 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    print(f"거래량 순위: {'✅ 통과' if success1 else '❌ 실패'}")
    print(f"등락률 순위: {'✅ 통과' if success2 else '❌ 실패'}")

    if success1 and success2:
        print("\n🎉 모든 테스트 통과!")
        print("\n시장탐색 기능은 정상입니다.")
        print("대시보드에서도 정상 작동해야 합니다.")
    else:
        print("\n⚠️  일부 테스트 실패")
        print("\n가능한 원인:")
        print("1. config.yaml의 키움증권 API 키 확인")
        print("2. 네트워크 연결 확인")
        print("3. 시장 운영 시간 확인")
        print("\n에러 메시지를 확인하여 문제를 해결하세요.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n테스트 중단됨.")
