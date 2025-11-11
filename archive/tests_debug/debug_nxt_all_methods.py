"""
NXT 현재가 조회 - 모든 방법 총망라 테스트
목표: 가능한 모든 조합을 시도해서 성공하는 방법 찾기
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
import json
from datetime import datetime, time
from typing import Dict, Optional, List
from collections import defaultdict

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'


class ComprehensiveNXTTest:
    """NXT 현재가 조회 모든 방법 테스트"""

    def __init__(self, bot):
        self.bot = bot
        self.client = bot.client
        self.ws_manager = bot.websocket_manager

        # 테스트 종목 (1개만 - 빠른 테스트)
        self.test_stock = ("249420", "일동제약")

        # 결과 저장
        self.results = []
        self.success_methods = []

        # WebSocket 실시간 데이터
        self.realtime_data = {}
        self.realtime_event = asyncio.Event()

    def is_nxt_hours(self) -> bool:
        """NXT 거래 시간 확인"""
        now = datetime.now().time()

        # 오전 NXT: 08:00 ~ 09:00
        morning = time(8, 0) <= now < time(9, 0)

        # 오후 NXT: 15:30 ~ 20:00
        afternoon = time(15, 30) <= now <= time(20, 0)

        return morning or afternoon

    # ================================================================
    # REST API 테스트
    # ================================================================

    def test_rest_api(self, api_id: str, stock_code: str, description: str, **extra_params):
        """REST API 호출 테스트"""
        try:
            body = {"stk_cd": stock_code, **extra_params}

            # API별 경로 결정
            path_map = {
                "ka10003": "stkinfo",
                "ka10004": "mrkcond",
                "ka10006": "invest",
                "ka10007": "exright",
                "ka10008": "frgnistt",
                "ka10009": "elw",
                "ka30001": "stockinfo",
                "ka30002": "chart"
            }
            path = path_map.get(api_id, "stkinfo")

            response = self.client.request(api_id=api_id, body=body, path=path)

            if response and response.get('return_code') == 0:
                # 현재가 추출 시도
                price = self._extract_price_from_response(response, api_id)

                if price:
                    print(f"{GREEN}✓{RESET} {description}: {price:,}원")
                    self.results.append({
                        'method': 'REST',
                        'api': api_id,
                        'description': description,
                        'success': True,
                        'price': price,
                        'code': stock_code
                    })
                    self.success_methods.append(f"{api_id} - {description}")
                    return price
                else:
                    print(f"{RED}✗{RESET} {description}: 가격 추출 실패")
                    self.results.append({
                        'method': 'REST',
                        'api': api_id,
                        'description': description,
                        'success': False,
                        'error': '가격 추출 실패'
                    })
            else:
                error_msg = response.get('return_msg', 'API 호출 실패') if response else 'No response'
                print(f"{RED}✗{RESET} {description}: {error_msg}")
                self.results.append({
                    'method': 'REST',
                    'api': api_id,
                    'description': description,
                    'success': False,
                    'error': error_msg
                })

            return None

        except Exception as e:
            print(f"{RED}✗{RESET} {description}: {str(e)[:50]}")
            self.results.append({
                'method': 'REST',
                'api': api_id,
                'description': description,
                'success': False,
                'error': str(e)[:100]
            })
            return None

    def _extract_price_from_response(self, response: dict, api_id: str) -> Optional[int]:
        """API 응답에서 현재가 추출"""
        try:
            # ka10003: 체결정보
            if api_id == "ka10003":
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr:
                    cur_prc = cntr_infr[0].get('cur_prc', '0')
                    return abs(int(str(cur_prc).replace('+', '').replace('-', '').replace(',', '')))

            # ka10004: 호가
            elif api_id == "ka10004":
                # cur_prc 필드
                cur_prc = response.get('cur_prc', '0')
                if cur_prc and cur_prc != '0':
                    return abs(int(str(cur_prc).replace('+', '').replace('-', '').replace(',', '')))

                # 호가 중간가
                sell = response.get('sel_fpr_bid', '0').replace('+', '').replace('-', '')
                buy = response.get('buy_fpr_bid', '0').replace('+', '').replace('-', '')
                sell_p = abs(int(sell)) if sell and sell != '0' else 0
                buy_p = abs(int(buy)) if buy and buy != '0' else 0
                if sell_p > 0 or buy_p > 0:
                    return (sell_p + buy_p) // 2 if (sell_p and buy_p) else (sell_p or buy_p)

            # ka30002: 차트
            elif api_id == "ka30002":
                chart_data = response.get('cntr_day_list', [])
                if chart_data:
                    cncl_prc = chart_data[-1].get('cncl_prc', '0')
                    return abs(int(str(cncl_prc).replace('+', '').replace('-', '').replace(',', '')))

            # 기타: cur_prc, 현재가 등의 필드 탐색
            for key in ['cur_prc', '현재가', 'price', '10']:
                if key in response:
                    val = str(response[key]).replace('+', '').replace('-', '').replace(',', '')
                    if val and val != '0':
                        return abs(int(val))

        except:
            pass

        return None

    def run_rest_tests(self):
        """REST API 모든 조합 테스트"""
        print(f"\n{MAGENTA}{'='*80}{RESET}")
        print(f"{MAGENTA}REST API 테스트 - 모든 조합{RESET}")
        print(f"{MAGENTA}{'='*80}{RESET}\n")

        code, name = self.test_stock

        # 1. ka10003 - 체결정보
        print(f"{CYAN}[ka10003 - 체결정보]{RESET}")
        self.test_rest_api("ka10003", code, f"ka10003 기본코드 ({code})")
        self.test_rest_api("ka10003", f"{code}_NX", f"ka10003 NX코드 ({code}_NX)")

        # 2. ka10004 - 호가
        print(f"\n{CYAN}[ka10004 - 호가]{RESET}")
        self.test_rest_api("ka10004", code, f"ka10004 기본코드 ({code})")
        self.test_rest_api("ka10004", f"{code}_NX", f"ka10004 NX코드 ({code}_NX)")

        # 3. ka30002 - 차트 (일봉)
        print(f"\n{CYAN}[ka30002 - 차트 일봉]{RESET}")
        today = datetime.now().strftime("%Y%m%d")
        self.test_rest_api("ka30002", code, f"ka30002 일봉 기본코드",
                          time_type="D", inq_strt_dt=today, inq_end_dt=today)
        self.test_rest_api("ka30002", f"{code}_NX", f"ka30002 일봉 NX코드",
                          time_type="D", inq_strt_dt=today, inq_end_dt=today)

        # 4. ka30002 - 차트 (분봉)
        print(f"\n{CYAN}[ka30002 - 차트 분봉]{RESET}")
        self.test_rest_api("ka30002", code, f"ka30002 1분봉 기본코드",
                          time_type="m", time_value="1", inq_strt_dt=today, inq_end_dt=today)
        self.test_rest_api("ka30002", f"{code}_NX", f"ka30002 1분봉 NX코드",
                          time_type="m", time_value="1", inq_strt_dt=today, inq_end_dt=today)

    # ================================================================
    # WebSocket 테스트
    # ================================================================

    async def websocket_callback(self, data: dict):
        """WebSocket 콜백"""
        try:
            ws_type = data.get('type', '')
            item = data.get('item', '')
            values = data.get('values', {})

            if item and values:
                # 현재가 추출 시도
                price = None
                for key in ['10', 'cur_prc', '현재가', 'price']:
                    if key in values:
                        val = str(values[key]).replace('+', '').replace('-', '').replace(',', '')
                        if val and val != '0':
                            try:
                                price = abs(int(val))
                                break
                            except:
                                pass

                if price:
                    key = f"{ws_type}:{item}"
                    self.realtime_data[key] = {
                        'type': ws_type,
                        'item': item,
                        'price': price
                    }
                    print(f"{GREEN}✓{RESET} WS {ws_type} - {item}: {price:,}원")
                    self.realtime_event.set()

        except Exception as e:
            pass

    async def test_websocket(self, ws_type: str, stock_code: str, description: str):
        """WebSocket 실시간 등록 테스트"""
        try:
            print(f"{CYAN}[{description}]{RESET}")

            # 콜백 등록
            self.ws_manager.register_callback(ws_type, self.websocket_callback)

            # REG 패킷
            reg_packet = {
                'trnm': 'REG',
                'grp_no': '1',
                'refresh': '0',  # 기존 등록 해지
                'data': [{
                    'item': [stock_code],
                    'type': [ws_type]
                }]
            }

            await self.ws_manager.websocket.send(json.dumps(reg_packet))
            await asyncio.sleep(1)

            # 데이터 수신 대기 (5초)
            self.realtime_event.clear()
            try:
                await asyncio.wait_for(self.realtime_event.wait(), timeout=5)

                key = f"{ws_type}:{stock_code}"
                if key in self.realtime_data:
                    price = self.realtime_data[key]['price']
                    self.results.append({
                        'method': 'WebSocket',
                        'type': ws_type,
                        'description': description,
                        'success': True,
                        'price': price,
                        'code': stock_code
                    })
                    self.success_methods.append(f"WS {ws_type} - {description}")
                    return price

            except asyncio.TimeoutError:
                print(f"{RED}✗{RESET} {description}: 타임아웃 (5초)")
                self.results.append({
                    'method': 'WebSocket',
                    'type': ws_type,
                    'description': description,
                    'success': False,
                    'error': '타임아웃'
                })

            return None

        except Exception as e:
            print(f"{RED}✗{RESET} {description}: {str(e)[:50]}")
            self.results.append({
                'method': 'WebSocket',
                'type': ws_type,
                'description': description,
                'success': False,
                'error': str(e)[:100]
            })
            return None

    async def run_websocket_tests(self):
        """WebSocket 모든 조합 테스트"""
        print(f"\n{MAGENTA}{'='*80}{RESET}")
        print(f"{MAGENTA}WebSocket 테스트 - 모든 타입{RESET}")
        print(f"{MAGENTA}{'='*80}{RESET}\n")

        code, name = self.test_stock

        # 다양한 WebSocket 타입 테스트
        ws_types = [
            ('0A', '주식기세'),
            ('0B', '주식체결'),
            ('0C', '주식우선호가'),
            ('0D', '주식호가잔량'),
            ('0E', '주식시간외호가'),
        ]

        for ws_type, type_name in ws_types:
            # 기본 코드
            await self.test_websocket(ws_type, code, f"{type_name} 기본코드 ({code})")

            # _NX 코드
            await self.test_websocket(ws_type, f"{code}_NX", f"{type_name} NX코드 ({code}_NX)")

    # ================================================================
    # 결과 출력
    # ================================================================

    def print_summary(self):
        """결과 요약"""
        print(f"\n{MAGENTA}{'='*80}{RESET}")
        print(f"{MAGENTA}테스트 결과 요약{RESET}")
        print(f"{MAGENTA}{'='*80}{RESET}\n")

        # 통계
        total = len(self.results)
        success = sum(1 for r in self.results if r['success'])
        fail = total - success

        print(f"{BLUE}[전체 통계]{RESET}")
        print(f"  총 시도: {total}개")
        print(f"  성공: {GREEN}{success}개{RESET}")
        print(f"  실패: {RED}{fail}개{RESET}")
        print(f"  성공률: {success/total*100:.1f}%")

        # 성공한 방법들
        if self.success_methods:
            print(f"\n{GREEN}[성공한 방법들]{RESET}")
            for i, method in enumerate(self.success_methods, 1):
                result = next((r for r in self.results if f"{r.get('api', r.get('type', ''))} - {r['description']}" == method), None)
                price = result.get('price', 0) if result else 0
                print(f"  {i}. {method}: {price:,}원")
        else:
            print(f"\n{RED}[성공한 방법 없음]{RESET}")
            print(f"  모든 방법이 실패했습니다.")

        # 실패 원인 분석
        print(f"\n{YELLOW}[실패 원인 분석]{RESET}")
        errors = defaultdict(int)
        for r in self.results:
            if not r['success']:
                error = r.get('error', 'Unknown')[:50]
                errors[error] += 1

        for error, count in sorted(errors.items(), key=lambda x: x[1], reverse=True):
            print(f"  {error}: {count}건")

        # NXT 시간대 확인
        is_nxt = self.is_nxt_hours()
        print(f"\n{YELLOW}[현재 상태]{RESET}")
        print(f"  시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  NXT 거래시간: {GREEN if is_nxt else RED}{'예' if is_nxt else '아니오'}{RESET}")
        if not is_nxt:
            print(f"  {YELLOW}⚠️  NXT 거래 시간이 아닙니다 (오전 08:00-09:00, 오후 15:30-20:00){RESET}")

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print(f"\n{BLUE}{'#'*80}{RESET}")
        print(f"{BLUE}#  NXT 현재가 조회 - 모든 방법 총망라 테스트{RESET}")
        print(f"{BLUE}#  종목: {self.test_stock[0]} ({self.test_stock[1]}){RESET}")
        print(f"{BLUE}{'#'*80}{RESET}\n")

        # REST API 테스트
        self.run_rest_tests()

        # WebSocket 테스트
        await self.run_websocket_tests()

        # 결과 출력
        self.print_summary()


async def main():
    """메인 실행"""
    try:
        from main import TradingBotV2
        bot = TradingBotV2()

        if not bot.client:
            print(f"{RED}❌ 클라이언트 초기화 실패{RESET}")
            return

        print(f"{GREEN}✅ 초기화 완료{RESET}")

        # 테스트 실행
        tester = ComprehensiveNXTTest(bot)
        await tester.run_all_tests()

    except Exception as e:
        print(f"\n{RED}❌ 오류: {e}{RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
