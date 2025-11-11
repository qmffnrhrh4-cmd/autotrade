"""
NXT 종가 조회 테스트

WebSocket 실시간 대신 REST API로 NXT 종가를 조회
_NX 접미사 사용 여부 테스트
"""
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.rest_client import KiwoomRESTClient

# 색상 코드
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
WHITE = '\033[97m'
RESET = '\033[0m'


def test_nxt_closing_price():
    """NXT 종가 조회 테스트"""
    print(f"\n{BLUE}{'='*100}{RESET}")
    print(f"{BLUE}🔍 NXT 종가 조회 테스트{RESET}")
    print(f"{BLUE}{'='*100}{RESET}")

    # 테스트 종목
    test_stocks = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("035720", "카카오"),
        ("249420", "일동제약"),
        ("052020", "에프엔에스테크"),
        ("900290", "GRT"),
    ]

    print(f"\n{CYAN}테스트 종목 ({len(test_stocks)}개):{RESET}")
    for i, (code, name) in enumerate(test_stocks, 1):
        print(f"  {i}. {name:20} ({code})")

    # REST Client 초기화
    client = KiwoomRESTClient()
    if not client.token:
        print(f"{RED}❌ REST API 연결 실패{RESET}")
        return

    print(f"\n{GREEN}✅ REST API 연결 성공{RESET}")

    print(f"\n{MAGENTA}{'='*100}{RESET}")
    print(f"{MAGENTA}📊 종가 조회 테스트{RESET}")
    print(f"{MAGENTA}{'='*100}{RESET}")

    results = {
        'base_code_success': [],
        'nx_suffix_success': [],
        'both_failed': []
    }

    for code, name in test_stocks:
        print(f"\n{WHITE}{'='*100}{RESET}")
        print(f"{WHITE}📈 {name} ({code}){RESET}")
        print(f"{WHITE}{'='*100}{RESET}")

        # 1. 기본 코드로 조회
        print(f"\n{CYAN}1️⃣ 기본 코드 조회: {code}{RESET}")
        try:
            response = client.request(
                api_id="ka10003",
                body={"stk_cd": code},
                path="stkinfo"
            )

            # 디버깅: 전체 응답 출력
            print(f"  {YELLOW}[DEBUG] 응답:{RESET}")
            if response:
                import json
                print(f"  {json.dumps(response, ensure_ascii=False, indent=2)[:500]}")
            else:
                print(f"  {RED}None{RESET}")

            if response and 'cntr_infr' in response and len(response['cntr_infr']) > 0:
                # 첫 번째 체결 정보 사용
                cntr_info = response['cntr_infr'][0]
                cur_prc = cntr_info.get('cur_prc', 'N/A')
                stex_tp = cntr_info.get('stex_tp', 'N/A')
                tm = cntr_info.get('tm', 'N/A')
                pred_pre = cntr_info.get('pred_pre', 'N/A')

                print(f"  현재가: {cur_prc}")
                print(f"  거래소: {stex_tp}")
                print(f"  시간: {tm}")
                print(f"  전일대비: {pred_pre}")

                if cur_prc != 'N/A' and cur_prc != '0':
                    print(f"  {GREEN}✅ 조회 성공{RESET}")
                    results['base_code_success'].append((code, name, cur_prc, stex_tp))
                else:
                    print(f"  {RED}❌ 가격 없음{RESET}")
            else:
                print(f"  {RED}❌ 응답 데이터 없음 (cntr_infr 필드 없거나 비어있음){RESET}")
        except Exception as e:
            print(f"  {RED}❌ 오류: {e}{RESET}")
            import traceback
            traceback.print_exc()

        # 2. _NX 접미사로 조회
        print(f"\n{CYAN}2️⃣ _NX 접미사 조회: {code}_NX{RESET}")
        try:
            response = client.request(
                api_id="ka10003",
                body={"stk_cd": f"{code}_NX"},
                path="stkinfo"
            )

            # 디버깅: 전체 응답 출력
            print(f"  {YELLOW}[DEBUG] 응답:{RESET}")
            if response:
                import json
                print(f"  {json.dumps(response, ensure_ascii=False, indent=2)[:500]}")
            else:
                print(f"  {RED}None{RESET}")

            if response and 'cntr_infr' in response and len(response['cntr_infr']) > 0:
                # 첫 번째 체결 정보 사용
                cntr_info = response['cntr_infr'][0]
                cur_prc = cntr_info.get('cur_prc', 'N/A')
                stex_tp = cntr_info.get('stex_tp', 'N/A')
                tm = cntr_info.get('tm', 'N/A')
                pred_pre = cntr_info.get('pred_pre', 'N/A')

                print(f"  현재가: {cur_prc}")
                print(f"  거래소: {stex_tp}")
                print(f"  시간: {tm}")
                print(f"  전일대비: {pred_pre}")

                if cur_prc != 'N/A' and cur_prc != '0':
                    print(f"  {GREEN}✅ 조회 성공{RESET}")
                    results['nx_suffix_success'].append((code, name, cur_prc, stex_tp))
                else:
                    print(f"  {RED}❌ 가격 없음{RESET}")
            else:
                print(f"  {RED}❌ 응답 데이터 없음 (cntr_infr 필드 없거나 비어있음){RESET}")
        except Exception as e:
            print(f"  {RED}❌ 오류: {e}{RESET}")
            import traceback
            traceback.print_exc()

        # 결과 판정
        base_success = any(item[0] == code for item in results['base_code_success'])
        nx_success = any(item[0] == code for item in results['nx_suffix_success'])

        if not base_success and not nx_success:
            results['both_failed'].append((code, name))

    # 최종 결과
    print(f"\n{BLUE}{'='*100}{RESET}")
    print(f"{BLUE}🎯 최종 결과{RESET}")
    print(f"{BLUE}{'='*100}{RESET}")

    print(f"\n{GREEN}✅ 기본 코드로 조회 성공 ({len(results['base_code_success'])}개):{RESET}")
    for code, name, price, stex_tp in results['base_code_success']:
        print(f"  • {name:20} ({code:6}) | {price:>12} | 거래소: {stex_tp}")

    print(f"\n{GREEN}✅ _NX 접미사로 조회 성공 ({len(results['nx_suffix_success'])}개):{RESET}")
    for code, name, price, stex_tp in results['nx_suffix_success']:
        print(f"  • {name:20} ({code:6}_NX) | {price:>12} | 거래소: {stex_tp}")

    if results['both_failed']:
        print(f"\n{RED}❌ 둘 다 실패 ({len(results['both_failed'])}개):{RESET}")
        for code, name in results['both_failed']:
            print(f"  • {name:20} ({code})")

    # 결론
    print(f"\n{MAGENTA}{'='*100}{RESET}")
    print(f"{MAGENTA}💡 결론{RESET}")
    print(f"{MAGENTA}{'='*100}{RESET}")

    if len(results['nx_suffix_success']) > 0:
        print(f"\n{GREEN}🎉 SUCCESS! _NX 접미사로 NXT 종가 조회 가능!{RESET}")
        print(f"\n{CYAN}사용법:{RESET}")
        print(f"  • API: ka10003 (체결정보)")
        print(f"  • 파라미터: stk_cd = '<code>_NX'")
        print(f"  • 응답 필드: cntr_infr[0].cur_prc")
        print(f"  • 거래소 구분: cntr_infr[0].stex_tp = 'NXT'")
        print(f"\n{YELLOW}주의사항:{RESET}")
        print(f"  • NXT 거래가 없던 종목은 cntr_infr = [] (빈 배열)")
        print(f"  • 기본 코드는 KRX 종가, _NX는 NXT 종가 반환")
    elif len(results['base_code_success']) > 0:
        print(f"\n{YELLOW}⚠️  기본 코드로만 조회 가능{RESET}")
        print(f"{YELLOW}   _NX 접미사는 REST API에서 작동하지 않음{RESET}")
        print(f"{YELLOW}   거래소 구분(stex_tp)으로 NXT 여부 확인 필요{RESET}")
    else:
        print(f"\n{RED}❌ NXT 종가 조회 실패{RESET}")
        print(f"{RED}   다른 API나 방법 필요{RESET}")


if __name__ == "__main__":
    test_nxt_closing_price()
