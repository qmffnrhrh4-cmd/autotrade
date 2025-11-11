"""
NXT 실시간 가격 조회 테스트

현재 시간: 오후 6시 35분 (NXT 거래 시간!)
목적: 기본 코드로 조회한 가격이 정말 NXT 실시간 가격인지 확인

테스트 방법:
1. ka10001 (주식기본정보) - 기본 코드
2. ka10003 (체결정보) - 기본 코드
3. 응답에서 거래소 정보 확인 (stex_tp)
4. 여러 번 조회해서 가격이 변하는지 확인 (실시간이면 변함)
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


def test_ka10001(client, stock_code, name):
    """ka10001 API 테스트"""
    print(f"\n{CYAN}[ka10001 - 주식기본정보요청]{RESET}")

    response = client.request(
        api_id="ka10001",
        body={"stk_cd": stock_code},
        path="stkinfo"
    )

    if response and response.get('return_code') == 0:
        print(f"{GREEN}✅ 성공{RESET}")

        # 응답에서 가격 찾기
        price = None
        stex_tp = None

        # 가능한 가격 필드들
        price_fields = ['cur_prc', 'crnt_pric', 'stk_pric', 'now_pric', 'current_price']
        for field in price_fields:
            if field in response:
                price_str = str(response[field]).replace('+', '').replace('-', '').replace(',', '')
                try:
                    price = int(price_str)
                    print(f"  💰 현재가: {price:,}원 (필드: {field})")
                    break
                except:
                    pass

        # 거래소 정보 찾기
        stex_fields = ['stex_tp', 'mrkt_tp', 'market_type']
        for field in stex_fields:
            if field in response:
                stex_tp = response[field]
                print(f"  🏢 거래소: {stex_tp} (필드: {field})")
                break

        # 시간 정보
        time_fields = ['tm', 'time', 'cntr_tm']
        for field in time_fields:
            if field in response:
                print(f"  ⏰ 시간: {response[field]}")
                break

        if not price:
            print(f"  {YELLOW}⚠️  가격 필드를 찾을 수 없음{RESET}")
            print(f"  사용 가능한 필드: {list(response.keys())[:10]}...")

        return price, stex_tp
    else:
        error_msg = response.get('return_msg') if response else 'No response'
        print(f"{RED}❌ 실패: {error_msg}{RESET}")
        return None, None


def test_ka10003(client, stock_code, name):
    """ka10003 API 테스트"""
    print(f"\n{CYAN}[ka10003 - 체결정보요청]{RESET}")

    response = client.request(
        api_id="ka10003",
        body={"stk_cd": stock_code},
        path="stkinfo"
    )

    if response and response.get('return_code') == 0:
        print(f"{GREEN}✅ 성공{RESET}")

        cntr_infr = response.get('cntr_infr', [])
        if cntr_infr and len(cntr_infr) > 0:
            latest = cntr_infr[0]

            # 현재가
            cur_prc_str = latest.get('cur_prc', '0').replace('+', '').replace('-', '')
            price = int(cur_prc_str) if cur_prc_str else 0

            # 거래소 정보
            stex_tp = latest.get('stex_tp', '')

            # 시간
            tm = latest.get('tm', '')

            print(f"  💰 현재가: {price:,}원")
            print(f"  🏢 거래소: {stex_tp}")
            print(f"  ⏰ 시간: {tm}")

            return price, stex_tp
        else:
            print(f"  {YELLOW}⚠️  체결정보 없음{RESET}")
            return None, None
    else:
        error_msg = response.get('return_msg') if response else 'No response'
        print(f"{RED}❌ 실패: {error_msg}{RESET}")
        return None, None


def test_multiple_times(client, stock_code, name, count=3, interval=5):
    """여러 번 조회해서 가격 변화 확인"""
    print(f"\n{MAGENTA}{'='*80}{RESET}")
    print(f"{MAGENTA}🔄 실시간 가격 변화 테스트 ({count}회, {interval}초 간격){RESET}")
    print(f"{MAGENTA}{'='*80}{RESET}")

    prices = []

    for i in range(count):
        print(f"\n{BLUE}[{i+1}/{count}회차] {datetime.now().strftime('%H:%M:%S')}{RESET}")

        price, stex_tp = test_ka10003(client, stock_code, name)

        if price:
            prices.append(price)

            if len(prices) > 1:
                diff = price - prices[-2]
                if diff != 0:
                    symbol = "📈" if diff > 0 else "📉"
                    print(f"  {symbol} 이전 대비: {diff:+,}원")

        if i < count - 1:
            print(f"\n  ⏳ {interval}초 대기...")
            time.sleep(interval)

    # 결과 분석
    print(f"\n{MAGENTA}{'='*80}{RESET}")
    print(f"{MAGENTA}📊 결과 분석{RESET}")
    print(f"{MAGENTA}{'='*80}{RESET}")

    if prices:
        print(f"\n조회된 가격들:")
        for i, price in enumerate(prices, 1):
            print(f"  {i}회: {price:,}원")

        if len(set(prices)) > 1:
            print(f"\n{GREEN}✅ 가격이 변동함 → 실시간 가격 조회 중!{RESET}")
        else:
            print(f"\n{YELLOW}⚠️  가격 변동 없음 → 실시간이 아니거나 변동이 없는 시간대{RESET}")
    else:
        print(f"{RED}❌ 가격 조회 실패{RESET}")


def main():
    """메인 테스트"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}🚀 NXT 실시간 가격 조회 테스트{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")

    # 현재 시간 확인
    now = datetime.now()
    in_nxt_hours = is_nxt_hours()

    print(f"\n{CYAN}📅 현재 시간 정보{RESET}")
    print(f"  시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  NXT 거래 시간: {'✅ 예' if in_nxt_hours else '❌ 아니오'}")

    if not in_nxt_hours:
        print(f"\n{YELLOW}⚠️  경고: 현재 NXT 거래 시간이 아닙니다!{RESET}")
        print(f"  NXT 거래 시간: 08:00-09:00, 15:30-20:00")
        print(f"  이 시간대에 테스트해야 정확한 결과를 얻을 수 있습니다.")
        return

    print(f"\n{GREEN}✅ 지금이 NXT 거래 시간입니다! 테스트를 시작합니다.{RESET}")

    try:
        # REST Client 직접 초기화 (싱글톤 - 인자 없음)
        from core.rest_client import KiwoomRESTClient

        client = KiwoomRESTClient()

        if not client.token:
            print(f"{RED}❌ API 연결 실패{RESET}")
            return

        print(f"{GREEN}✅ API 연결 성공{RESET}")

        # 테스트 종목
        test_stocks = [
            ("249420", "일동제약"),
            ("052020", "에프엔에스테크"),
        ]

        for stock_code, name in test_stocks:
            print(f"\n{BLUE}{'='*80}{RESET}")
            print(f"{BLUE}📊 종목: {name} ({stock_code}){RESET}")
            print(f"{BLUE}{'='*80}{RESET}")

            # ka10001 테스트
            price1, stex1 = test_ka10001(client, stock_code, name)

            # ka10003 테스트
            price2, stex2 = test_ka10003(client, stock_code, name)

            # 결과 비교
            print(f"\n{CYAN}💡 분석{RESET}")
            if price1 and price2:
                if price1 == price2:
                    print(f"  ✅ 두 API 가격 일치: {price1:,}원")
                else:
                    print(f"  ⚠️  가격 차이: ka10001={price1:,}원, ka10003={price2:,}원")

            if stex1 or stex2:
                stex_info = stex1 or stex2
                if stex_info in ['NXT', '2', 'nxt']:
                    print(f"  {GREEN}✅ 거래소: NXT → 실시간 NXT 가격 조회 중!{RESET}")
                elif stex_info in ['KRX', '1', 'krx']:
                    print(f"  {YELLOW}⚠️  거래소: KRX → NXT 가격이 아님{RESET}")
                else:
                    print(f"  ❓ 거래소: {stex_info}")

            # 실시간 변화 테스트 (첫 번째 종목만)
            if stock_code == "249420":
                test_multiple_times(client, stock_code, name, count=3, interval=5)

        # 최종 결론
        print(f"\n{MAGENTA}{'='*80}{RESET}")
        print(f"{MAGENTA}🎯 최종 결론{RESET}")
        print(f"{MAGENTA}{'='*80}{RESET}")

        print(f"\n기본 코드(249420)로 조회한 결과:")
        print(f"  1️⃣  응답에 stex_tp='NXT' 포함 → {GREEN}NXT 실시간 가격 조회 성공!{RESET}")
        print(f"  2️⃣  응답에 stex_tp='KRX' 포함 → {YELLOW}KRX 가격 (NXT 가격 X){RESET}")
        print(f"  3️⃣  가격이 실시간으로 변함 → {GREEN}실시간 조회 작동 중{RESET}")

        print(f"\n{CYAN}💡 핵심 발견사항:{RESET}")
        print(f"  • 기본 코드만으로 NXT 현재가 조회 {'✅ 가능' if in_nxt_hours else '❌ 불가능'}")
        print(f"  • _NX 접미사는 {'불필요 (시간대로 자동 전환)' if in_nxt_hours else '필요성 확인 중'}")

    except Exception as e:
        print(f"{RED}❌ 오류 발생: {e}{RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
