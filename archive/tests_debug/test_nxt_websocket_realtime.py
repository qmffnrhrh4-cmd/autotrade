"""
WebSocket 실시간 현재가 조회 테스트 - KRX + NXT 혼합

핵심 발견:
- WebSocket 실시간 구독에서는 _NX 접미사 사용 필수!
- type: 0B (주식체결)
- 필드 10: 현재가
- 필드 9081: 거래소구분

테스트:
- 5개 고거래량 KRX 종목 + 5개 NXT 종목 구독
- 5초마다 현재가 체크 (10회)
- 가격 변동 추적
- KRX 고거래량 종목으로 WebSocket 작동 여부 확인
"""
import sys
from pathlib import Path
from datetime import datetime
import time
import asyncio
import json

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


async def test_websocket_realtime():
    """WebSocket 실시간 가격 테스트"""
    print(f"\n{BLUE}{'='*100}{RESET}")
    print(f"{BLUE}🔍 WebSocket 실시간 가격 모니터링 (KRX + NXT 혼합){RESET}")
    print(f"{BLUE}{'='*100}{RESET}")

    # 테스트 종목 10개: NXT 시간에는 NXT 종목만 거래됨!
    # (code, name, market_type)

    # 현재 NXT 시간 확인
    in_nxt = is_nxt_hours()
    now = datetime.now().time()

    # 정규 거래시간 (09:00-15:30)인지 확인
    is_regular_hours = (
        datetime.strptime("09:00", "%H:%M").time() <= now < datetime.strptime("15:30", "%H:%M").time()
    )

    if is_regular_hours:
        # 정규시간: KRX + NXT 혼합
        test_stocks = [
            ("005930", "삼성전자", "KRX"),
            ("000660", "SK하이닉스", "KRX"),
            ("035720", "카카오", "KRX"),
            ("005380", "현대차", "KRX"),
            ("051910", "LG화학", "KRX"),
            ("249420", "일동제약", "NXT"),
            ("052020", "에프엔에스테크", "NXT"),
            ("900290", "GRT", "NXT"),
            ("900250", "크리스탈신소재", "NXT"),
            ("217270", "넵튠", "NXT"),
        ]
    else:
        # NXT 시간: 실제 NXT 거래 종목만 테스트
        test_stocks = [
            ("249420", "일동제약", "NXT"),
            ("052020", "에프엔에스테크", "NXT"),
            ("900290", "GRT", "NXT"),
            ("900340", "윙입푸드", "NXT"),
            ("900250", "크리스탈신소재", "NXT"),
            ("900270", "헝셩그룹", "NXT"),
            ("217270", "넵튠", "NXT"),
            ("900300", "오가닉티코스메틱", "NXT"),
            ("900110", "이스트아시아홀딩스", "NXT"),
            ("900260", "로스웰", "NXT"),
        ]
        print(f"\n{YELLOW}⚠️  현재 시각 {now.strftime('%H:%M')} - 정규장 종료{RESET}")
        print(f"{YELLOW}   실제 NXT 거래 가능 종목 10개로 테스트합니다.{RESET}")
        print(f"{YELLOW}   참고: 삼성전자 등 대형주는 NXT에 상장되지 않음!{RESET}")

    print(f"\n{CYAN}테스트 종목 ({len(test_stocks)}개):{RESET}")

    krx_stocks = [s for s in test_stocks if s[2] == "KRX"]
    nxt_stocks = [s for s in test_stocks if s[2] == "NXT"]

    if krx_stocks:
        print(f"\n{GREEN}[KRX 고거래량 종목 - {len(krx_stocks)}개]{RESET}")
        for i, (code, name, market) in enumerate(krx_stocks, 1):
            print(f"  {i}. {name:20} ({code})")

    if nxt_stocks:
        print(f"\n{YELLOW}[NXT 종목 - {len(nxt_stocks)}개]{RESET}")
        for i, (code, name, market) in enumerate(nxt_stocks, 1):
            print(f"  {i}. {name:20} ({code}_NX)")

    try:
        # WebSocketManager 초기화
        from core.websocket_manager import WebSocketManager
        from core.rest_client import KiwoomRESTClient

        # REST Client로 토큰 발급
        rest_client = KiwoomRESTClient()
        if not rest_client.token:
            print(f"{RED}❌ REST API 연결 실패{RESET}")
            return

        print(f"{GREEN}✅ REST API 연결 성공{RESET}")

        # WebSocket 연결
        ws_manager = WebSocketManager(rest_client.token)

        print(f"{CYAN}WebSocket 연결 시도...{RESET}")
        await ws_manager.connect()

        if not ws_manager.is_connected:
            print(f"{RED}❌ WebSocket 연결 실패{RESET}")
            return

        print(f"{GREEN}✅ WebSocket 연결 성공{RESET}")

        # 가격 기록 저장소
        price_history = {code: {'name': name, 'market': market, 'prices': [], 'timestamps': []}
                        for code, name, market in test_stocks}

        # 실시간 데이터 수신 콜백
        received_count = [0]  # 수신된 데이터 카운터

        def on_realtime_data(data):
            """실시간 데이터 수신 시 호출"""
            try:
                if not isinstance(data, dict):
                    return

                # 디버깅: 전체 메시지 출력
                trnm = data.get('trnm', '')
                if trnm == 'REAL':
                    print(f"\n{CYAN}🔍 REAL 메시지 전체:{RESET}")
                    print(f"  {json.dumps(data, ensure_ascii=False)[:500]}")

                data_list = data.get('data', [])
                for idx, item in enumerate(data_list):
                    # 디버깅: 각 item 구조 출력
                    print(f"\n{CYAN}  Item #{idx+1}:{RESET}")
                    print(f"    Keys: {list(item.keys())}")

                    item_code = item.get('item', '')
                    values = item.get('values', {})

                    print(f"    item_code: '{item_code}'")
                    print(f"    현재가(10): {values.get('10', 'N/A')}")
                    print(f"    체결시간(20): {values.get('20', 'N/A')}")

                    # _NX 제거하여 기본 코드 추출
                    base_code = item_code.replace('_NX', '')

                    if base_code in price_history:
                        # 필드 10: 현재가
                        cur_prc_str = values.get('10', '0')

                        try:
                            cur_prc = abs(int(cur_prc_str.replace('+', '').replace('-', '').replace(',', '')))

                            # 기록 저장
                            price_history[base_code]['prices'].append(cur_prc)
                            price_history[base_code]['timestamps'].append(datetime.now().strftime('%H:%M:%S'))

                            received_count[0] += 1
                            print(f"    {GREEN}✅ 저장 성공: {price_history[base_code]['name']} = {cur_prc:,}원{RESET}")

                        except Exception as e:
                            print(f"    {RED}❌ 파싱 실패: {e}{RESET}")
                    else:
                        print(f"    {YELLOW}⚠️  종목코드 '{base_code}' 매칭 실패{RESET}")

            except Exception as e:
                print(f"{RED}콜백 오류: {e}{RESET}")
                import traceback
                traceback.print_exc()

        # 콜백 등록
        ws_manager.register_callback('test', on_realtime_data)

        # 종목 구독 (0B: 주식체결)
        # KRX: 기본 코드, NXT: _NX 접미사
        items_for_subscription = []
        for code, name, market in test_stocks:
            if market == "NXT":
                items_for_subscription.append(f"{code}_NX")
            else:
                items_for_subscription.append(code)

        print(f"\n{CYAN}종목 구독 중...{RESET}")
        print(f"  Type: 0B (주식체결)")
        print(f"  Items: {len(items_for_subscription)}개 (KRX: 기본코드, NXT: _NX 접미사)")
        print(f"  구독 코드: {', '.join(items_for_subscription[:3])}...")

        success = await ws_manager.subscribe(
            stock_codes=items_for_subscription,
            types=["0B"]  # 주식체결 - 19:48에 REAL 받았을 때 사용한 타입
        )

        if not success:
            print(f"{RED}❌ 구독 실패{RESET}")
            return

        print(f"{GREEN}✅ 구독 성공!{RESET}")

        # ⭐ 구독 완료 후 receive_loop 시작!
        print(f"{CYAN}실시간 데이터 수신 루프 시작...{RESET}")
        receive_task = asyncio.create_task(ws_manager.receive_loop())

        # 루프가 시작될 시간 대기
        await asyncio.sleep(0.5)

        # 10회 체크 (5초 간격)
        print(f"\n{MAGENTA}{'='*100}{RESET}")
        print(f"{MAGENTA}📊 실시간 데이터 수신 모니터링 (10회, 5초 간격){RESET}")
        print(f"{MAGENTA}{'='*100}{RESET}")

        for round_num in range(1, 11):
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"\n{BLUE}[{round_num}/10회차] {current_time}{RESET}")
            print(f"  수신된 데이터: {received_count[0]}건")

            # 현재까지 수신된 가격 출력
            stocks_with_data = 0
            for code, data in price_history.items():
                if data['prices']:
                    stocks_with_data += 1
                    latest_price = data['prices'][-1]
                    latest_time = data['timestamps'][-1]
                    market = data['market']

                    # 변동 계산
                    change_symbol = ""
                    if len(data['prices']) > 1:
                        prev_price = data['prices'][-2]
                        diff = latest_price - prev_price
                        if diff > 0:
                            change_symbol = f" 📈 +{diff:,}원"
                        elif diff < 0:
                            change_symbol = f" 📉 {diff:,}원"
                        else:
                            change_symbol = " ➡️  변동없음"

                    # 시장별 아이콘 및 코드 표시
                    if market == "KRX":
                        icon = "🔵"
                        code_display = code
                    else:
                        icon = "🟢"
                        code_display = f"{code}_NX"

                    print(f"  {icon} {data['name']:15} ({code_display:10}) | {latest_price:7,}원 @ {latest_time}{change_symbol}")

            if stocks_with_data == 0:
                print(f"  {YELLOW}⚠️  아직 데이터 수신 없음...{RESET}")

            # 마지막 회차가 아니면 대기
            if round_num < 10:
                await asyncio.sleep(5)

        # 최종 결과 분석
        print(f"\n{BLUE}{'='*100}{RESET}")
        print(f"{BLUE}📊 최종 결과 분석{RESET}")
        print(f"{BLUE}{'='*100}{RESET}")

        total_stocks = len(test_stocks)
        stocks_with_change = 0
        stocks_with_data = 0

        krx_with_data = 0
        nxt_with_data = 0
        krx_with_change = 0
        nxt_with_change = 0

        for code, data in price_history.items():
            prices = data['prices']
            name = data['name']
            market = data['market']

            # 코드 표시
            code_display = f"{code}_NX" if market == "NXT" else code
            market_icon = "🟢" if market == "NXT" else "🔵"

            if not prices:
                print(f"\n{YELLOW}{market_icon} {name} ({code_display}){RESET}")
                print(f"  ❌ 데이터 수신 없음")
                continue

            stocks_with_data += 1
            if market == "KRX":
                krx_with_data += 1
            else:
                nxt_with_data += 1

            # 가격 변동 분석
            unique_prices = set(prices)
            has_change = len(unique_prices) > 1

            if has_change:
                stocks_with_change += 1
                if market == "KRX":
                    krx_with_change += 1
                else:
                    nxt_with_change += 1

            # 개별 종목 요약
            min_price = min(prices)
            max_price = max(prices)
            price_range = max_price - min_price

            change_icon = "✅" if has_change else "❌"

            print(f"\n{WHITE}{market_icon} {name} ({code_display}) [{market}]{RESET}")
            print(f"  {change_icon} 가격 변동: {'있음' if has_change else '없음'} (최소: {min_price:,}원, 최대: {max_price:,}원, 범위: {price_range:,}원)")
            print(f"  📊 수신 횟수: {len(prices)}회")

        # 전체 통계
        print(f"\n{MAGENTA}{'='*100}{RESET}")
        print(f"{MAGENTA}🎯 최종 결론{RESET}")
        print(f"{MAGENTA}{'='*100}{RESET}")

        print(f"\n{CYAN}수신 통계:{RESET}")
        print(f"  • 총 종목 수: {total_stocks}개 (KRX: 5개, NXT: 5개)")
        print(f"  • 데이터 수신: {stocks_with_data}개 ({stocks_with_data/total_stocks*100:.1f}%)")
        print(f"    - 🔵 KRX: {krx_with_data}/5개")
        print(f"    - 🟢 NXT: {nxt_with_data}/5개")
        print(f"  • 수신 없음: {total_stocks - stocks_with_data}개")
        print(f"  • 총 수신 건수: {received_count[0]}건")

        print(f"\n{CYAN}가격 변동 분석:{RESET}")
        if stocks_with_data > 0:
            print(f"  • 가격 변동 있음: {stocks_with_change}개 ({stocks_with_change/stocks_with_data*100:.1f}%)")
            print(f"    - 🔵 KRX: {krx_with_change}/{krx_with_data}개" + (f" ({krx_with_change/krx_with_data*100:.1f}%)" if krx_with_data > 0 else ""))
            print(f"    - 🟢 NXT: {nxt_with_change}/{nxt_with_data}개" + (f" ({nxt_with_change/nxt_with_data*100:.1f}%)" if nxt_with_data > 0 else ""))
            print(f"  • 가격 변동 없음: {stocks_with_data - stocks_with_change}개")
        else:
            print(f"  • 데이터 없음")

        # 최종 판정
        print(f"\n{MAGENTA}{'='*100}{RESET}")
        print(f"{MAGENTA}📋 판정 결과{RESET}")
        print(f"{MAGENTA}{'='*100}{RESET}")

        if stocks_with_data == 0:
            print(f"\n{RED}❌ WebSocket 실시간 데이터 수신 완전 실패{RESET}")
            print(f"{YELLOW}가능한 원인:{RESET}")
            print(f"  1. WebSocket 연결 문제")
            print(f"  2. 구독 타입(0B) 문제")
            print(f"  3. 토큰 권한 문제")
        elif krx_with_data == 0 and nxt_with_data == 0:
            print(f"\n{RED}❌ KRX/NXT 모두 데이터 수신 실패{RESET}")
        elif krx_with_data > 0 and nxt_with_data == 0:
            print(f"\n{YELLOW}⚠️  KRX만 데이터 수신, NXT 데이터 수신 실패{RESET}")
            print(f"{YELLOW}   → KRX: {krx_with_data}개 수신 ({krx_with_change}개 변동){RESET}")
            print(f"{YELLOW}   → NXT: 0개 수신{RESET}")
            print(f"{YELLOW}   → _NX 접미사 문제이거나 NXT 거래량 부족{RESET}")
        elif krx_with_data == 0 and nxt_with_data > 0:
            print(f"\n{YELLOW}⚠️  NXT만 데이터 수신, KRX 데이터 수신 실패{RESET}")
            print(f"{YELLOW}   → NXT: {nxt_with_data}개 수신 ({nxt_with_change}개 변동){RESET}")
            print(f"{YELLOW}   → KRX: 0개 수신 (예상 외){RESET}")
        else:
            # 둘 다 수신됨
            print(f"\n{GREEN}✅ WebSocket 데이터 수신 성공!{RESET}")
            print(f"{GREEN}   → KRX: {krx_with_data}/5개 수신, {krx_with_change}개 가격 변동{RESET}")
            print(f"{GREEN}   → NXT: {nxt_with_data}/5개 수신, {nxt_with_change}개 가격 변동{RESET}")

            if krx_with_change > 0 and nxt_with_change > 0:
                print(f"\n{GREEN}🎉 완벽! KRX와 NXT 모두 실시간 가격 변동 확인!{RESET}")
                print(f"{GREEN}   → WebSocket으로 NXT 실시간 현재가 조회 가능{RESET}")
                print(f"{GREEN}   → _NX 접미사 + type=0B 방식 작동 확인{RESET}")
            elif krx_with_change > 0 and nxt_with_change == 0:
                print(f"\n{YELLOW}⚠️  KRX는 변동 있으나 NXT는 변동 없음{RESET}")
                print(f"{YELLOW}   → WebSocket은 작동하지만 NXT 거래량 부족일 가능성{RESET}")
            elif krx_with_change == 0 and nxt_with_change > 0:
                print(f"\n{YELLOW}⚠️  NXT는 변동 있으나 KRX는 변동 없음 (예상 외){RESET}")
            else:
                print(f"\n{YELLOW}⚠️  데이터 수신은 됐으나 가격 변동 없음{RESET}")
                print(f"{YELLOW}   → 테스트 기간 동안 체결이 없었을 가능성{RESET}")

        # WebSocket 해제
        print(f"\n{CYAN}WebSocket 연결 해제 중...{RESET}")
        receive_task.cancel()  # 백그라운드 태스크 취소
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        await ws_manager.disconnect()

    except Exception as e:
        print(f"{RED}❌ 오류 발생: {e}{RESET}")
        import traceback
        traceback.print_exc()


def main():
    """메인 함수"""
    print(f"\n{BLUE}{'='*100}{RESET}")
    print(f"{BLUE}🚀 WebSocket 실시간 가격 테스트 (KRX 5개 + NXT 5개){RESET}")
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
        print(f"\n  💡 이 테스트는 KRX 종목(5개)도 포함하므로")
        print(f"     정규 거래시간(09:00-15:30)에도 실행 가능합니다.")
        print(f"     다만 NXT 종목은 NXT 시간대가 아니면 데이터 수신이 안 될 수 있습니다.")
        print(f"\n  {GREEN}→ KRX 종목 테스트를 위해 자동으로 진행합니다.{RESET}")

    print(f"\n{GREEN}✅ 테스트를 시작합니다.{RESET}")

    # asyncio 실행
    try:
        asyncio.run(test_websocket_realtime())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}테스트 중단됨{RESET}")
    except Exception as e:
        print(f"\n{RED}오류: {e}{RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
