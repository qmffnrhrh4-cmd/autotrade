"""
NXT 실시간 현재가 조회 테스트 - WebSocket 활용
목적: 종가 vs NXT 실시간 현재가 비교
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


class NXTRealtimePriceTest:
    """NXT 실시간 현재가 테스트"""

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
        self.results = {}
        self.realtime_prices = {}
        self.realtime_received = asyncio.Event()

    def get_close_price(self, stock_code: str) -> Optional[int]:
        """종가 조회 (ka10003 - 체결정보)"""
        try:
            response = self.client.request(
                api_id="ka10003",
                body={"stk_cd": stock_code},
                path="stkinfo"
            )

            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr and len(cntr_infr) > 0:
                    latest = cntr_infr[0]
                    cur_prc_str = latest.get('cur_prc', '0')
                    price = abs(int(cur_prc_str.replace('+', '').replace('-', '')))
                    return price if price > 0 else None
            return None
        except Exception as e:
            print(f"  {RED}종가 조회 오류: {e}{RESET}")
            return None

    async def subscribe_realtime(self, stock_codes: list):
        """실시간 시세 등록 (WebSocket)"""
        try:
            # REG 패킷 구성
            reg_packet = {
                'trnm': 'REG',
                'grp_no': '1',
                'refresh': '1',
                'data': [{
                    'item': stock_codes,
                    'type': ['0B']  # 주식체결 실시간 항목
                }]
            }

            print(f"{CYAN}실시간 등록 요청: {stock_codes}{RESET}")
            print(f"{YELLOW}REG 패킷: {json.dumps(reg_packet, ensure_ascii=False)}{RESET}")

            await self.ws_manager.websocket.send(json.dumps(reg_packet))
            print(f"{GREEN}실시간 등록 전송 완료{RESET}")

            # 등록 응답 대기 (1초)
            await asyncio.sleep(1)

        except Exception as e:
            print(f"{RED}실시간 등록 실패: {e}{RESET}")
            import traceback
            traceback.print_exc()

    async def wait_for_realtime_data(self, timeout: int = 10):
        """실시간 데이터 수신 대기"""
        try:
            print(f"{YELLOW}실시간 데이터 수신 대기 중... (최대 {timeout}초){RESET}")
            print(f"{YELLOW}디버깅: 모든 WebSocket 메시지 출력{RESET}")

            # 기존 수신 핸들러를 일시적으로 수정
            original_handler = self.ws_manager._handle_real_data

            async def custom_handler(message):
                """커스텀 실시간 메시지 핸들러"""
                try:
                    # 📋 디버깅: 모든 메시지 출력
                    trnm = message.get('trnm', 'UNKNOWN')
                    print(f"\n{BLUE}[WebSocket 메시지] trnm={trnm}{RESET}")
                    print(f"{BLUE}{json.dumps(message, ensure_ascii=False, indent=2)[:500]}...{RESET}")

                    # 원래 핸들러도 호출
                    await original_handler(message)

                    # REAL 데이터 파싱
                    # 구조: {"trnm": "REAL", "data": [{"type": "0B", "item": "005930", "values": {...}}]}
                    if message.get('trnm') == 'REAL':
                        print(f"{CYAN}[REAL 데이터 감지]{RESET}")
                        data_list = message.get('data', [])
                        print(f"{CYAN}data_list 개수: {len(data_list)}{RESET}")

                        for idx, data in enumerate(data_list):
                            stock_code = data.get('item', '')  # item 필드가 종목코드
                            data_type = data.get('type', '')
                            values = data.get('values', {})

                            print(f"{CYAN}  [{idx}] type={data_type}, item={stock_code}, values 키: {list(values.keys())[:10]}{RESET}")

                            if stock_code and values:
                                # 현재가 추출 (키움 WebSocket 필드: '10')
                                cur_prc_str = values.get('10', '0')  # 필드 '10' = 현재가
                                print(f"{CYAN}    필드 '10' (현재가): {cur_prc_str}{RESET}")

                                try:
                                    if cur_prc_str and cur_prc_str != '0':
                                        price = abs(int(str(cur_prc_str).replace('+', '').replace('-', '').replace(',', '')))
                                        if price > 0:
                                            self.realtime_prices[stock_code] = price
                                            print(f"  {GREEN}✓ 실시간 수신: {stock_code} = {price:,}원{RESET}")
                                except Exception as e:
                                    print(f"  {RED}가격 파싱 오류: {e}{RESET}")

                        # 모든 종목 수신 확인
                        if len(self.realtime_prices) >= len(self.test_stocks):
                            self.realtime_received.set()

                except Exception as e:
                    print(f"  {RED}실시간 데이터 파싱 오류: {e}{RESET}")
                    import traceback
                    traceback.print_exc()

            # 핸들러 교체
            self.ws_manager._handle_real_data = custom_handler

            # 데이터 수신 대기
            try:
                await asyncio.wait_for(self.realtime_received.wait(), timeout=timeout)
                print(f"\n{GREEN}모든 종목 실시간 데이터 수신 완료{RESET}")
            except asyncio.TimeoutError:
                print(f"\n{YELLOW}타임아웃: {len(self.realtime_prices)}/{len(self.test_stocks)}개 종목 수신{RESET}")

            # 핸들러 복원
            self.ws_manager._handle_real_data = original_handler

        except Exception as e:
            print(f"{RED}실시간 데이터 대기 오류: {e}{RESET}")
            import traceback
            traceback.print_exc()

    async def run_test(self):
        """테스트 실행"""
        print(f"\n{'='*80}")
        print(f"{BLUE}NXT 실시간 현재가 조회 테스트{RESET}")
        print(f"{BLUE}시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
        print(f"{'='*80}\n")

        # 1단계: 종가 조회 (REST API)
        print(f"{YELLOW}[1단계] 종가 조회 (REST API - ka10003){RESET}")
        for stock_code, stock_name in self.test_stocks:
            close_price = self.get_close_price(stock_code)
            self.results[stock_code] = {
                'name': stock_name,
                'close': close_price
            }
            if close_price:
                print(f"  {GREEN}✓{RESET} {stock_code} {stock_name}: {close_price:,}원")
            else:
                print(f"  {RED}✗{RESET} {stock_code} {stock_name}: 조회 실패")

        # 2단계: 실시간 현재가 등록 및 수신 (WebSocket)
        print(f"\n{YELLOW}[2단계] 실시간 현재가 조회 (WebSocket - 0B 타입){RESET}")

        stock_codes = [code for code, _ in self.test_stocks]
        await self.subscribe_realtime(stock_codes)
        await self.wait_for_realtime_data(timeout=15)

        # 실시간 가격을 결과에 병합
        for stock_code in stock_codes:
            if stock_code in self.realtime_prices:
                self.results[stock_code]['realtime'] = self.realtime_prices[stock_code]
            else:
                self.results[stock_code]['realtime'] = None

        # 3단계: 결과 비교표 출력
        self.print_comparison_table()

    def print_comparison_table(self):
        """결과 비교표 출력"""
        print(f"\n{'='*80}")
        print(f"{BLUE}[최종 결과] 종가 vs NXT 실시간 현재가{RESET}")
        print(f"{'='*80}")

        # 테이블 헤더
        print(f"\n{'종목코드':<10} {'종목명':<15} {'종가(REST)':<15} {'실시간(WS)':<15} {'차이':<15}")
        print(f"{'-'*80}")

        success_count = 0
        total_count = len(self.test_stocks)

        for stock_code, stock_name in self.test_stocks:
            result = self.results.get(stock_code, {})
            close = result.get('close')
            realtime = result.get('realtime')

            # 종가 포맷
            if close:
                close_str = f"{close:,}원"
            else:
                close_str = f"{RED}실패{RESET}"

            # 실시간 포맷
            if realtime:
                realtime_str = f"{GREEN}{realtime:,}원{RESET}"
                success_count += 1
            else:
                realtime_str = f"{RED}실패{RESET}"

            # 차이 계산
            if close and realtime:
                diff = realtime - close
                diff_pct = (diff / close * 100) if close > 0 else 0
                if diff > 0:
                    diff_str = f"{GREEN}+{diff:,}원 (+{diff_pct:.2f}%){RESET}"
                elif diff < 0:
                    diff_str = f"{RED}{diff:,}원 ({diff_pct:.2f}%){RESET}"
                else:
                    diff_str = "동일"
            else:
                diff_str = "-"

            print(f"{stock_code:<10} {stock_name:<15} {close_str:<24} {realtime_str:<24} {diff_str}")

        # 요약
        print(f"\n{'='*80}")
        print(f"{BLUE}[요약]{RESET}")
        print(f"  총 종목 수: {total_count}개")
        print(f"  실시간 성공: {GREEN}{success_count}개{RESET}")
        print(f"  실시간 실패: {RED}{total_count - success_count}개{RESET}")
        print(f"  성공률: {success_count / total_count * 100:.1f}%")
        print(f"{'='*80}\n")


async def main():
    """메인 실행"""
    print(f"\n{BLUE}TradingBot 초기화 중 (WebSocket 포함)...{RESET}")

    try:
        from main import TradingBotV2

        # 봇 초기화 (WebSocket 자동 연결)
        bot = TradingBotV2()

        if not bot.client:
            print(f"{RED}클라이언트 초기화 실패{RESET}")
            return

        if not bot.websocket_manager or not bot.websocket_manager.is_connected:
            print(f"{RED}WebSocket 연결 실패{RESET}")
            return

        print(f"{GREEN}✅ 초기화 완료 (WebSocket 연결됨){RESET}")

        # 테스트 실행
        tester = NXTRealtimePriceTest(bot)
        await tester.run_test()

    except Exception as e:
        print(f"{RED}오류 발생: {e}{RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
