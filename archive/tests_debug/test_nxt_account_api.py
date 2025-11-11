"""
NXT 계좌 API 테스트

발견: get_holdings(market_type="NXT")로 조회하면
NXT 보유 종목의 실시간 현재가를 가져올 수 있을 것!

테스트:
1. market_type="KRX" vs "NXT" 비교
2. cur_prc 필드 확인
3. 10회 조회로 가격 변동 확인
"""
import sys
from pathlib import Path
from datetime import datetime
import time

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 색상 코드
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
WHITE = '\033[97m'
RESET = '\033[0m'


def is_nxt_hours():
    """NXT 거래 시간 여부 확인"""
    now = datetime.now()
    current_time = now.time()

    # 오전: 08:00-09:00
    morning_start = datetime.strptime("08:00", "%H:%M").time()
    morning_end = datetime.strptime("09:00", "%H:%M").time()

    # 오후: 15:30-20:00
    afternoon_start = datetime.strptime("15:30", "%H:%M").time()
    afternoon_end = datetime.strptime("20:00", "%H:%M").time()

    is_morning = morning_start <= current_time < morning_end
    is_afternoon = afternoon_start <= current_time < afternoon_end

    return is_morning or is_afternoon


def test_nxt_holdings_monitoring(account_api, rounds=10, interval=5):
    """
    NXT 보유 종목 실시간 가격 모니터링

    Args:
        account_api: AccountAPI 인스턴스
        rounds: 조회 회차
        interval: 조회 간격 (초)
    """
    print(f"\n{BLUE}{'='*100}{RESET}")
    print(f"{BLUE}🔍 NXT 계좌 API 실시간 가격 모니터링{RESET}")
    print(f"{BLUE}{'='*100}{RESET}")
    print(f"{CYAN}조회 횟수: {rounds}회{RESET}")
    print(f"{CYAN}조회 간격: {interval}초{RESET}")

    # 가격 기록
    price_history = {}

    for round_num in range(1, rounds + 1):
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"\n{MAGENTA}{'='*100}{RESET}")
        print(f"{MAGENTA}[{round_num}/{rounds}회차] {current_time}{RESET}")
        print(f"{MAGENTA}{'='*100}{RESET}")

        # NXT 보유 종목 조회
        holdings = account_api.get_holdings(market_type="NXT")

        if holdings:
            print(f"{GREEN}✅ NXT 보유 종목: {len(holdings)}개{RESET}\n")

            for holding in holdings:
                # 종목 정보
                stk_cd = holding.get('stk_cd', '')
                stk_nm = holding.get('stk_nm', '')

                # 현재가 (여러 필드 시도)
                cur_prc = None
                price_field = None

                # 가능한 현재가 필드들
                for field in ['cur_prc', 'crnt_pric', 'now_pric', 'current_price']:
                    if field in holding:
                        try:
                            cur_prc = int(str(holding[field]).replace('+', '').replace('-', '').replace(',', ''))
                            price_field = field
                            break
                        except:
                            pass

                # 평가금액 (역산용)
                evlt_amt = holding.get('evlt_amt', 0)
                rmnd_qty = holding.get('rmnd_qty', 0)  # 보유수량

                # 가격 기록 초기화
                if stk_cd not in price_history:
                    price_history[stk_cd] = {
                        'name': stk_nm,
                        'prices': [],
                        'eval_amounts': [],
                        'quantities': []
                    }

                # 기록 추가
                if cur_prc:
                    price_history[stk_cd]['prices'].append(cur_prc)
                if evlt_amt:
                    price_history[stk_cd]['eval_amounts'].append(int(evlt_amt))
                if rmnd_qty:
                    price_history[stk_cd]['quantities'].append(int(rmnd_qty))

                # 변동 계산
                change_symbol = ""
                if len(price_history[stk_cd]['prices']) > 1:
                    prev_price = price_history[stk_cd]['prices'][-2]
                    if cur_prc:
                        diff = cur_prc - prev_price
                        if diff > 0:
                            change_symbol = f" 📈 +{diff:,}원"
                        elif diff < 0:
                            change_symbol = f" 📉 {diff:,}원"
                        else:
                            change_symbol = " ➡️  변동없음"

                # 출력
                if cur_prc:
                    print(f"  🟢 {stk_nm:15} ({stk_cd}) | 현재가: {cur_prc:7,}원 (필드: {price_field}){change_symbol}")
                else:
                    print(f"  ⚪ {stk_nm:15} ({stk_cd}) | 현재가: 조회 실패")

                # 추가 정보
                if evlt_amt and rmnd_qty:
                    try:
                        evlt_amt_int = int(str(evlt_amt).replace(',', ''))
                        rmnd_qty_int = int(str(rmnd_qty).replace(',', ''))
                        calculated_price = evlt_amt_int // rmnd_qty_int
                        print(f"      평가금액: {evlt_amt_int:,}원, 보유수량: {rmnd_qty_int:,}주 → 역산 현재가: {calculated_price:,}원")
                    except:
                        pass

        else:
            print(f"{YELLOW}⚠️  NXT 보유 종목 없음{RESET}")

        # 다음 회차 전 대기
        if round_num < rounds:
            print(f"\n  {CYAN}⏳ {interval}초 대기 중...{RESET}")
            time.sleep(interval)

    # 최종 결과 분석
    print(f"\n{BLUE}{'='*100}{RESET}")
    print(f"{BLUE}📊 최종 결과 분석{RESET}")
    print(f"{BLUE}{'='*100}{RESET}")

    if not price_history:
        print(f"\n{RED}❌ NXT 보유 종목이 없어서 테스트 불가{RESET}")
        print(f"{YELLOW}💡 NXT 종목을 먼저 매수한 후 테스트하세요{RESET}")
        return

    stocks_with_change = 0
    total_stocks = len(price_history)

    for stk_cd, data in price_history.items():
        prices = data['prices']
        name = data['name']

        if not prices:
            continue

        # 가격 변동 분석
        unique_prices = set(prices)
        has_change = len(unique_prices) > 1

        if has_change:
            stocks_with_change += 1

        # 개별 종목 요약
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price

        change_icon = "✅" if has_change else "❌"

        print(f"\n{WHITE}{name} ({stk_cd}){RESET}")
        print(f"  {change_icon} 가격 변동: {'있음' if has_change else '없음'} (최소: {min_price:,}원, 최대: {max_price:,}원, 범위: {price_range:,}원)")
        print(f"  📊 조회 횟수: {len(prices)}회")

    # 전체 통계
    print(f"\n{MAGENTA}{'='*100}{RESET}")
    print(f"{MAGENTA}🎯 최종 결론{RESET}")
    print(f"{MAGENTA}{'='*100}{RESET}")

    print(f"\n{CYAN}종목 통계:{RESET}")
    print(f"  • 총 NXT 보유 종목: {total_stocks}개")
    print(f"  • 가격 변동 있음: {stocks_with_change}개 ({stocks_with_change/total_stocks*100:.1f}%)")
    print(f"  • 가격 변동 없음: {total_stocks - stocks_with_change}개 ({(total_stocks - stocks_with_change)/total_stocks*100:.1f}%)")

    if stocks_with_change > 0:
        print(f"\n{GREEN}✅ NXT 계좌 API로 실시간 가격 조회 성공!{RESET}")
        print(f"{GREEN}   → get_holdings(market_type='NXT')로 실시간 현재가 조회 가능{RESET}")
        print(f"{GREEN}   → 이 방법을 사용하여 보유 NXT 종목의 현재가를 가져올 수 있습니다!{RESET}")
    else:
        print(f"\n{YELLOW}⚠️  가격 변동 없음{RESET}")
        print(f"{YELLOW}   → 실시간 가격이 아니거나, 테스트 기간 동안 가격 변동이 없었을 수 있음{RESET}")


def main():
    """메인 테스트"""
    print(f"\n{BLUE}{'='*100}{RESET}")
    print(f"{BLUE}🚀 NXT 계좌 API 실시간 가격 테스트{RESET}")
    print(f"{BLUE}{'='*100}{RESET}")

    # 현재 시간 확인
    now = datetime.now()
    in_nxt_hours = is_nxt_hours()

    print(f"\n{CYAN}📅 현재 시간 정보{RESET}")
    print(f"  시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  NXT 거래 시간: {'✅ 예' if in_nxt_hours else '❌ 아니오'}")

    if not in_nxt_hours:
        print(f"\n{YELLOW}⚠️  경고: 현재 NXT 거래 시간이 아닙니다!{RESET}")
        print(f"  NXT 거래 시간: 08:00-09:00, 15:30-20:00")
        response = input("\n  계속 진행하시겠습니까? (y/n): ")
        if response.lower() != 'y':
            return

    print(f"\n{GREEN}✅ 테스트를 시작합니다.{RESET}")

    try:
        # Account API 초기화
        from core.rest_client import KiwoomRESTClient
        from api.account import AccountAPI

        client = KiwoomRESTClient()
        account_api = AccountAPI(client)

        if not client.token:
            print(f"{RED}❌ API 연결 실패{RESET}")
            return

        print(f"{GREEN}✅ API 연결 성공{RESET}")

        # NXT 보유 종목 실시간 모니터링
        test_nxt_holdings_monitoring(
            account_api=account_api,
            rounds=10,
            interval=5
        )

    except Exception as e:
        print(f"{RED}❌ 오류 발생: {e}{RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
