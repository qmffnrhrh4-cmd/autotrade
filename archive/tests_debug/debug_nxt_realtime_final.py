"""
NXT 실시간 현재가 조회 최종 테스트
키움 문서 기반 정확한 구현
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
import json
from datetime import datetime
from typing import Dict, Optional

# 색상
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'


class NXTRealtimeTest:
    """NXT 실시간 현재가 조회 테스트"""

    def __init__(self, bot):
        self.bot = bot
        self.client = bot.client
        self.ws_manager = bot.websocket_manager

        # 테스트할 NXT 종목 5개
        self.test_stocks = [
            ("052020", "에프엔에스테크"),
            ("249420", "일동제약"),
            ("452450", "SG&G"),
            ("114450", "KPX생명과학"),
            ("098460", "고영")
        ]

        # 결과 저장
        self.close_prices = {}  # 종가
        self.realtime_prices = {}  # 실시간 현재가

        # 이벤트
        self.reg_completed = asyncio.Event()
        self.data_received = asyncio.Event()

    def get_close_price(self, stock_code: str) -> Optional[int]:
        """종가 조회"""
        try:
            response = self.client.request(
                api_id="ka10003",
                body={"stk_cd": stock_code},
                path="stkinfo"
            )

            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr:
                    cur_prc_str = cntr_infr[0].get('cur_prc', '0')
                    price = abs(int(cur_prc_str.replace('+', '').replace('-', '')))
                    return price if price > 0 else None
            return None
        except:
            return None

    async def realtime_callback(self, data: dict):
        """실시간 데이터 콜백 (0B - 주식체결)"""
        try:
            stock_code = data.get('item', '')
            values = data.get('values', {})

            if stock_code and values:
                # 필드 '10' = 현재가
                cur_prc_str = values.get('10', '0')
                if cur_prc_str and cur_prc_str != '0':
                    price = abs(int(str(cur_prc_str).replace('+', '').replace('-', '').replace(',', '')))
                    if price > 0:
                        self.realtime_prices[stock_code] = price
                        print(f"  {GREEN}✓ {stock_code}: {price:,}원{RESET}")

                        # 모든 종목 수신 확인
                        if len(self.realtime_prices) >= len(self.test_stocks):
                            self.data_received.set()
        except Exception as e:
            print(f"  {RED}콜백 오류: {e}{RESET}")

    async def run_test(self):
        """테스트 실행"""
        print(f"\n{'='*80}")
        print(f"{BLUE}NXT 실시간 현재가 조회 테스트 (최종){RESET}")
        print(f"{BLUE}시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
        print(f"{'='*80}\n")

        # ============================================================
        # 1단계: 종가 조회
        # ============================================================
        print(f"{YELLOW}[1단계] 종가 조회 (REST API){RESET}")
        for code, name in self.test_stocks:
            price = self.get_close_price(code)
            self.close_prices[code] = price
            if price:
                print(f"  ✓ {code} {name}: {price:,}원")
            else:
                print(f"  ✗ {code} {name}: 실패")

        # ============================================================
        # 2단계: 실시간 등록 및 수신
        # ============================================================
        print(f"\n{YELLOW}[2단계] 실시간 등록 (WebSocket){RESET}")

        # 콜백 등록 (0B = 주식체결)
        self.ws_manager.register_callback('0B', self.realtime_callback)
        print(f"{CYAN}콜백 등록 완료 (0B - 주식체결){RESET}")

        # REG 패킷 전송
        stock_codes = [code for code, _ in self.test_stocks]
        reg_packet = {
            'trnm': 'REG',
            'grp_no': '1',
            'refresh': '1',
            'data': [{
                'item': stock_codes,
                'type': ['0B']
            }]
        }

        print(f"{CYAN}실시간 등록 전송: {stock_codes}{RESET}")
        await self.ws_manager.websocket.send(json.dumps(reg_packet))

        # 등록 응답 대기
        await asyncio.sleep(2)
        print(f"{GREEN}등록 완료{RESET}")

        # ============================================================
        # 3단계: 실시간 데이터 수신 대기
        # ============================================================
        print(f"\n{YELLOW}[3단계] 실시간 데이터 수신{RESET}")
        print(f"{CYAN}데이터 수신 대기 중... (최대 20초){RESET}")

        try:
            await asyncio.wait_for(self.data_received.wait(), timeout=20)
            print(f"\n{GREEN}✅ 모든 종목 수신 완료{RESET}")
        except asyncio.TimeoutError:
            print(f"\n{YELLOW}⏱️  타임아웃 ({len(self.realtime_prices)}/{len(self.test_stocks)}개 수신){RESET}")

        # ============================================================
        # 4단계: 결과 출력
        # ============================================================
        self.print_results()

    def print_results(self):
        """결과 출력"""
        print(f"\n{'='*80}")
        print(f"{BLUE}[최종 결과] 종가 vs 실시간 현재가{RESET}")
        print(f"{'='*80}\n")

        # 테이블 헤더
        print(f"{'코드':<10} {'종목명':<15} {'종가':<15} {'실시간':<15} {'차이':<20}")
        print(f"{'-'*80}")

        success = 0
        for code, name in self.test_stocks:
            close = self.close_prices.get(code)
            realtime = self.realtime_prices.get(code)

            # 종가
            close_str = f"{close:,}원" if close else f"{RED}실패{RESET}"

            # 실시간
            if realtime:
                realtime_str = f"{GREEN}{realtime:,}원{RESET}"
                success += 1
            else:
                realtime_str = f"{RED}미수신{RESET}"

            # 차이
            if close and realtime:
                diff = realtime - close
                pct = (diff / close * 100) if close > 0 else 0
                if diff > 0:
                    diff_str = f"{GREEN}+{diff:,}원 (+{pct:.2f}%){RESET}"
                elif diff < 0:
                    diff_str = f"{RED}{diff:,}원 ({pct:.2f}%){RESET}"
                else:
                    diff_str = "동일"
            else:
                diff_str = "-"

            print(f"{code:<10} {name:<15} {close_str:<24} {realtime_str:<24} {diff_str}")

        # 요약
        total = len(self.test_stocks)
        print(f"\n{'='*80}")
        print(f"{BLUE}[요약]{RESET}")
        print(f"  총 종목: {total}개")
        print(f"  종가 조회: {sum(1 for p in self.close_prices.values() if p)}개")
        print(f"  실시간 수신: {GREEN}{success}개{RESET}")
        print(f"  성공률: {success/total*100:.1f}%")
        print(f"{'='*80}\n")


async def main():
    """메인 실행"""
    print(f"\n{BLUE}TradingBot 초기화 중...{RESET}")

    try:
        from main import TradingBotV2
        bot = TradingBotV2()

        if not bot.client:
            print(f"{RED}❌ 클라이언트 초기화 실패{RESET}")
            return

        if not bot.websocket_manager or not bot.websocket_manager.is_connected:
            print(f"{RED}❌ WebSocket 연결 실패{RESET}")
            return

        print(f"{GREEN}✅ 초기화 완료{RESET}")

        # 테스트 실행
        tester = NXTRealtimeTest(bot)
        await tester.run_test()

        # 정리
        print(f"\n{YELLOW}정리 중...{RESET}")

    except KeyboardInterrupt:
        print(f"\n{YELLOW}사용자 중단{RESET}")
    except Exception as e:
        print(f"\n{RED}❌ 오류: {e}{RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}종료{RESET}")
