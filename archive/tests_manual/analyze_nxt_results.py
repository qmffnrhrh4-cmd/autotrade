"""
NXT 테스트 결과 분석 스크립트

사용법:
    python analyze_nxt_results.py test_results_nxt_YYYYMMDD_HHMMSS.json
"""

import json
import sys
from pathlib import Path


def analyze_results(filename: str):
    """테스트 결과 분석 및 권장사항 출력"""

    if not Path(filename).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {filename}")
        return

    with open(filename, 'r', encoding='utf-8') as f:
        results = json.load(f)

    print("\n" + "="*80)
    print("📊 NXT 테스트 결과 분석")
    print("="*80)

    # 기본 정보
    print(f"\n⏰ 테스트 시간: {results['timestamp']}")
    print(f"   NXT 시간대: {'✅ Yes' if results['is_nxt_time'] else '❌ No'}")
    print(f"   정규장 시간: {'✅ Yes' if results['is_market_time'] else '❌ No'}")

    # 현재가 조회 결과
    print("\n" + "-"*80)
    print("🔍 현재가 조회 결과")
    print("-"*80)

    price_tests = results.get('price_tests', [])
    price_success = [t for t in price_tests if t.get('success')]

    print(f"\n총 {len(price_tests)}개 테스트 중 {len(price_success)}개 성공 ({len(price_success)/len(price_tests)*100:.1f}%)")

    if price_success:
        print("\n✅ 성공한 접근법:")
        # 접근법별로 그룹화
        success_by_approach = {}
        for test in price_success:
            approach = test['approach']
            if approach not in success_by_approach:
                success_by_approach[approach] = []
            success_by_approach[approach].append(test)

        for approach, tests in success_by_approach.items():
            print(f"\n   📌 {approach} ({len(tests)}개 종목 성공)")
            for test in tests:
                print(f"      - {test['stock_code']}: {test['price']:,}원 (출처: {test['source']})")

        # 권장 방법
        print("\n" + "🎯 권장 현재가 조회 방법 ".ljust(80, "="))
        best = price_success[0]
        print(f"\n   접근법: {best['approach']}")
        print(f"   출처: {best['source']}")

        # 코드 예시
        if 'nxt' in best['approach'].lower() or best.get('source') == 'raw_api_nxt':
            print("\n   💡 코드 적용 예시:")
            print("   ```python")
            print("   body = {")
            print('       "stk_cd": stock_code,')
            print('       "dmst_stex_tp": "NXT"  # ← NXT 시간대용')
            print("   }")
            print("   response = self.client.request(api_id='ka10003', body=body, path='stkinfo')")
            print("   ```")
    else:
        print("\n❌ 성공한 접근법 없음")
        print("\n💡 확인사항:")
        print("   - API 키가 유효한가?")
        print("   - 네트워크 연결이 정상인가?")
        print("   - 장 운영 시간인가?")

    # 주문 결과
    print("\n" + "-"*80)
    print("📋 주문 테스트 결과")
    print("-"*80)

    order_tests = results.get('order_tests', [])
    order_success = [t for t in order_tests if t.get('success')]

    print(f"\n총 {len(order_tests)}개 조합 중 {len(order_success)}개 성공 ({len(order_success)/len(order_tests)*100:.1f}%)")

    if order_success:
        print("\n✅ 성공한 파라미터 조합:")
        for test in order_success:
            print(f"\n   📌 {test['combination']}")
            print(f"      주문번호: {test.get('ord_no', 'N/A')}")
            print(f"      응답: {test.get('return_msg', 'N/A')}")

        # 권장 조합
        print("\n" + "🎯 권장 주문 파라미터 ".ljust(80, "="))
        best_order = order_success[0]
        combination = best_order['combination']

        # 파라미터 추출
        import re
        dmst_match = re.search(r'dmst_stex_tp=(\w+)', combination)
        trde_match = re.search(r'trde_tp=(\w+)', combination)

        dmst = dmst_match.group(1) if dmst_match else 'Unknown'
        trde = trde_match.group(1) if trde_match else 'Unknown'

        print(f"\n   dmst_stex_tp: {dmst}")
        print(f"   trde_tp: {trde}")

        # trde_tp 설명
        trde_tp_desc = {
            '0': '지정가',
            '3': '시장가',
            '5': '조건부지정가',
            '6': '최유리지정가',
            '7': '최우선지정가',
            '10': '장전시간외',
            '13': '장후시간외',
            '16': '시간외단일가',
            '20': '장전시간외우선',
            '23': '장후시간외우선',
            '26': '시간외단일가우선'
        }
        desc = trde_tp_desc.get(trde, '알 수 없음')
        print(f"   거래유형: {desc}")

        # 코드 예시
        print("\n   💡 코드 적용 예시:")
        print("   ```python")
        print("   body = {")
        print(f'       "dmst_stex_tp": "{dmst}",')
        print('       "stk_cd": stock_code,')
        print('       "ord_qty": str(quantity),')
        print('       "ord_uv": str(price),')
        print(f'       "trde_tp": "{trde}"')
        print("   }")
        print("   response = self.client.request(api_id='kt10000', body=body, path='ordr')")
        print("   ```")

    else:
        print("\n❌ 성공한 조합 없음")
        print("\n💡 확인사항:")
        print("   - 매수가능금액이 충분한가?")
        print("   - 종목이 거래정지 상태가 아닌가?")
        print("   - 주문 시간이 적절한가?")

    # Summary
    summary = results.get('summary', {})
    if summary:
        print("\n" + "="*80)
        print("📈 전체 요약")
        print("="*80)

        price_summary = summary.get('price_tests', {})
        print(f"\n현재가 조회: {price_summary.get('success_rate', 'N/A')}")
        if price_summary.get('successful_approaches'):
            print(f"   성공 접근법: {', '.join(price_summary['successful_approaches'][:3])}")

        order_summary = summary.get('order_tests', {})
        print(f"\n주문 테스트: {order_summary.get('success_rate', 'N/A')}")
        if order_summary.get('successful_combinations'):
            print(f"   성공 조합: {', '.join(order_summary['successful_combinations'][:3])}")

    print("\n" + "="*80)
    print("✅ 분석 완료")
    print("="*80)
    print(f"\n상세 결과: {filename}\n")


def main():
    if len(sys.argv) < 2:
        # 가장 최근 결과 파일 찾기
        result_files = sorted(Path('.').glob('test_results_nxt_*.json'), reverse=True)
        if result_files:
            filename = str(result_files[0])
            print(f"📁 가장 최근 결과 파일 사용: {filename}\n")
        else:
            print("사용법: python analyze_nxt_results.py test_results_nxt_YYYYMMDD_HHMMSS.json")
            print("\n또는 최근 결과 파일이 있을 경우 자동으로 분석합니다.")
            return
    else:
        filename = sys.argv[1]

    analyze_results(filename)


if __name__ == "__main__":
    main()
