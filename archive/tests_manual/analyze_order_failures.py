"""
주문 실패 원인 상세 분석 스크립트

사용법:
    python analyze_order_failures.py test_results_nxt_YYYYMMDD_HHMMSS.json
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def analyze_order_failures(filename: str):
    """주문 실패 원인 상세 분석"""

    if not Path(filename).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {filename}")
        return

    with open(filename, 'r', encoding='utf-8') as f:
        results = json.load(f)

    print("\n" + "="*80)
    print("📋 주문 실패 상세 분석")
    print("="*80)

    order_tests = results.get('order_tests', [])

    if not order_tests:
        print("\n❌ 주문 테스트 결과가 없습니다.")
        return

    print(f"\n총 {len(order_tests)}개 조합 테스트")

    # 오류 코드별 그룹화
    error_groups = defaultdict(list)
    for test in order_tests:
        return_code = test.get('return_code')
        return_msg = test.get('return_msg', test.get('error', 'Unknown'))

        key = f"{return_code}: {return_msg}"
        error_groups[key].append(test)

    print(f"오류 유형: {len(error_groups)}가지\n")

    # 오류 유형별 상세 출력
    for error_key, tests in sorted(error_groups.items(), key=lambda x: len(x[1]), reverse=True):
        print("="*80)
        print(f"❌ {error_key}")
        print(f"   발생 횟수: {len(tests)}회")
        print("-"*80)

        # dmst_stex_tp별 그룹화
        by_dmst = defaultdict(list)
        for test in tests:
            combo = test['combination']
            # dmst_stex_tp 추출
            import re
            dmst_match = re.search(r'dmst_stex_tp=(\w+)', combo)
            dmst = dmst_match.group(1) if dmst_match else 'Unknown'
            by_dmst[dmst].append(test)

        for dmst, dmst_tests in sorted(by_dmst.items()):
            print(f"\n   📌 dmst_stex_tp={dmst} ({len(dmst_tests)}개)")

            # trde_tp 목록
            trde_tps = []
            for test in dmst_tests:
                combo = test['combination']
                import re
                trde_match = re.search(r'trde_tp=(\w+)', combo)
                trde = trde_match.group(1) if trde_match else '?'
                trde_tps.append(trde)

            print(f"      trde_tp: {', '.join(sorted(trde_tps))}")

        print()

    # NXT 시간에 시도해볼 조합 제안
    print("="*80)
    print("💡 NXT 시간대 권장 시도 조합")
    print("="*80)

    # 에러 메시지 분석 기반 제안
    장종료_errors = [k for k in error_groups.keys() if '장종료' in k or '505217' in k]
    주문불가_errors = [k for k in error_groups.keys() if '주문불가' in k or '주문거부' in k]

    if 장종료_errors:
        print("\n❌ '장종료' 오류가 발생한 조합들:")
        print("   → 정규장 전용 거래유형입니다.")
        print("   → NXT 시간에는 시간외 거래유형 사용 필요\n")

    print("🎯 NXT 시간대 추천 조합 (시도해볼 것):")
    print()

    # 키움증권 API 문서 기반 추천
    nxt_recommendations = [
        {
            'dmst_stex_tp': 'NXT',
            'trde_tp': '16',
            'desc': '시간외단일가',
            'time': 'NXT 시간대 (08:00-09:00, 15:30-20:00)'
        },
        {
            'dmst_stex_tp': 'NXT',
            'trde_tp': '13',
            'desc': '장후시간외',
            'time': '장 종료 후 (15:30-20:00)'
        },
        {
            'dmst_stex_tp': 'NXT',
            'trde_tp': '10',
            'desc': '장전시간외',
            'time': '장 시작 전 (08:00-09:00)'
        },
        {
            'dmst_stex_tp': 'KRX',
            'trde_tp': '16',
            'desc': '시간외단일가 (KRX)',
            'time': 'NXT 시간대'
        },
    ]

    for i, rec in enumerate(nxt_recommendations, 1):
        print(f"{i}. dmst_stex_tp={rec['dmst_stex_tp']}, trde_tp={rec['trde_tp']}")
        print(f"   거래유형: {rec['desc']}")
        print(f"   사용 시간: {rec['time']}")

        # 이 조합이 테스트되었는지 확인
        combo_str = f"dmst_stex_tp={rec['dmst_stex_tp']}, trde_tp={rec['trde_tp']}"
        tested = [t for t in order_tests if t['combination'] == combo_str]

        if tested:
            test = tested[0]
            if test.get('success'):
                print(f"   ✅ 테스트 성공!")
            else:
                error_msg = test.get('return_msg', test.get('error', 'Unknown'))
                print(f"   ❌ 테스트 실패: {error_msg}")
        else:
            print(f"   ⚠️  미테스트")
        print()

    # 실시간 주문 가능 시간 안내
    print("="*80)
    print("⏰ NXT 거래 시간")
    print("="*80)
    print("""
프리마켓 (장전시간외):
    시간: 08:00 - 09:00
    거래유형: trde_tp=10 (장전시간외)

애프터마켓 (장후시간외):
    시간: 15:30 - 20:00
    거래유형: trde_tp=13 (장후시간외) 또는 trde_tp=16 (시간외단일가)

※ 현재 시간이 어느 구간인지 확인하고 적절한 거래유형 사용
    """)

    # 수동 테스트 스크립트 생성
    print("="*80)
    print("🔧 수동 테스트 스크립트")
    print("="*80)
    print("""
다음 코드로 개별 조합을 직접 테스트할 수 있습니다:

```python
from core.rest_client import KiwoomRESTClient

client = KiwoomRESTClient()

# 테스트할 조합
test_combinations = [
    {'dmst_stex_tp': 'NXT', 'trde_tp': '16'},  # 시간외단일가
    {'dmst_stex_tp': 'NXT', 'trde_tp': '13'},  # 장후시간외
    {'dmst_stex_tp': 'NXT', 'trde_tp': '10'},  # 장전시간외
]

for combo in test_combinations:
    body = {
        'dmst_stex_tp': combo['dmst_stex_tp'],
        'stk_cd': '005930',  # 삼성전자
        'ord_qty': '1',
        'ord_uv': '50000',
        'trde_tp': combo['trde_tp']
    }

    print(f"\\nTesting: {combo}")
    response = client.request(api_id='kt10000', body=body, path='ordr')
    print(f"Result: {response}")
```
    """)


def main():
    if len(sys.argv) < 2:
        # 가장 최근 결과 파일 찾기
        result_files = sorted(Path('.').glob('test_results_nxt_*.json'), reverse=True)
        if result_files:
            filename = str(result_files[0])
            print(f"📁 가장 최근 결과 파일 사용: {filename}\n")
        else:
            print("사용법: python analyze_order_failures.py test_results_nxt_YYYYMMDD_HHMMSS.json")
            return
    else:
        filename = sys.argv[1]

    analyze_order_failures(filename)


if __name__ == "__main__":
    main()
