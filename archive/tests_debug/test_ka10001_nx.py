"""
ka10001 API 테스트 - NXT 종목코드 (_NX)
키움 API 어시스턴트가 추천한 방법 검증
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from datetime import datetime

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'


def test_ka10001(client, stock_code: str, description: str):
    """ka10001 API 테스트"""
    print(f"\n{CYAN}[{description}]{RESET}")
    print(f"  API: ka10001 (주식기본정보요청)")
    print(f"  종목코드: {stock_code}")

    try:
        response = client.request(
            api_id="ka10001",
            body={"stk_cd": stock_code},
            path="stkinfo"
        )

        if response and response.get('return_code') == 0:
            print(f"{GREEN}✓ API 호출 성공{RESET}")

            # 응답 구조 출력
            import json
            print(f"\n{BLUE}[응답 데이터]{RESET}")
            print(json.dumps(response, ensure_ascii=False, indent=2)[:500])

            # 현재가 추출 시도
            cur_prc = None

            # 다양한 필드명 시도
            for key in ['cur_prc', '현재가', 'stk_prc', 'price']:
                if key in response:
                    try:
                        val = str(response[key]).replace('+', '').replace('-', '').replace(',', '')
                        if val and val != '0':
                            cur_prc = abs(int(val))
                            print(f"\n{GREEN}💰 현재가 발견: {cur_prc:,}원 (필드: {key}){RESET}")
                            break
                    except:
                        pass

            if not cur_prc:
                print(f"\n{YELLOW}⚠️  현재가 필드를 찾을 수 없습니다.{RESET}")
                print(f"{YELLOW}응답의 모든 키: {list(response.keys())}{RESET}")

            return cur_prc

        else:
            error_msg = response.get('return_msg', 'No response') if response else 'No response'
            print(f"{RED}✗ API 호출 실패: {error_msg}{RESET}")
            return None

    except Exception as e:
        print(f"{RED}✗ 예외 발생: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """메인 테스트"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}ka10001 API 테스트 - NXT 종목코드 (_NX){RESET}")
    print(f"{BLUE}시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")

    from main import TradingBotV2
    bot = TradingBotV2()
    client = bot.client

    # 테스트 종목
    test_stocks = [
        ("249420", "일동제약"),
        ("052020", "에프엔에스테크"),
    ]

    results = {}

    for code, name in test_stocks:
        print(f"\n{MAGENTA}{'='*80}{RESET}")
        print(f"{MAGENTA}종목: {code} ({name}){RESET}")
        print(f"{MAGENTA}{'='*80}{RESET}")

        # 1. 기본 코드 테스트
        price_base = test_ka10001(client, code, f"기본 코드 ({code})")

        # 2. _NX 코드 테스트 (어시스턴트 추천)
        price_nx = test_ka10001(client, f"{code}_NX", f"NX 코드 ({code}_NX)")

        results[code] = {
            'name': name,
            'base': price_base,
            'nx': price_nx
        }

    # 결과 요약
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}테스트 결과 요약{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

    print(f"{'종목코드':<10} {'종목명':<15} {'기본 코드':<20} {'_NX 코드':<20}")
    print(f"{'-'*70}")

    for code, name in test_stocks:
        r = results[code]
        base_str = f"{r['base']:,}원" if r['base'] else f"{RED}실패{RESET}"
        nx_str = f"{r['nx']:,}원" if r['nx'] else f"{RED}실패{RESET}"

        print(f"{code:<10} {name:<15} {base_str:<29} {nx_str:<29}")

    # 결론
    print(f"\n{YELLOW}[결론]{RESET}")

    any_base_success = any(r['base'] for r in results.values())
    any_nx_success = any(r['nx'] for r in results.values())

    if any_nx_success:
        print(f"{GREEN}✅ _NX 코드로 조회 성공! (어시스턴트 추천 방법 확인){RESET}")
    elif any_base_success:
        print(f"{GREEN}✅ 기본 코드로 조회 성공{RESET}")
        print(f"{YELLOW}⚠️  _NX 코드는 작동하지 않음{RESET}")
    else:
        print(f"{RED}❌ 모든 방법 실패{RESET}")

    print(f"\n{BLUE}{'='*80}{RESET}\n")


MAGENTA = '\033[95m'

if __name__ == "__main__":
    main()
