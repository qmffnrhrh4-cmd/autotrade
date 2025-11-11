"""
NXT 현재가 조회 종합 테스트 - v5.15
다양한 조건과 접근법으로 성공 조합 찾기

테스트 목적:
1. NXT 시간대 감지 확인
2. 다양한 API 호출 방법 시도
3. 성공하는 조합 찾아내기
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import logging
from datetime import datetime, time
from typing import Dict, Any, Optional, List
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 색상 코드
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class NXTPriceDiscovery:
    """NXT 현재가 조회 다양한 접근법 테스트"""

    def __init__(self, client):
        self.client = client
        self.results = []

        # 테스트할 NXT 종목들
        self.test_stocks = [
            ("052020", "에프엔에스테크"),
            ("249420", "일동제약"),
            ("452450", "SG&G"),
            ("114450", "KPX생명과학"),
            ("098460", "고영")
        ]

    def check_time_status(self):
        """현재 시간 및 NXT 거래 시간 확인"""
        print(f"\n{'='*80}")
        print(f"{BLUE}[시간 상태 확인]{RESET}")
        print(f"{'='*80}")

        now = datetime.now()
        current_time = now.time()

        # NXT 거래 시간
        morning_start = time(8, 0)
        morning_end = time(9, 0)
        afternoon_start = time(15, 30)
        afternoon_end = time(20, 0)

        is_morning = morning_start <= current_time < morning_end
        is_afternoon = afternoon_start <= current_time <= afternoon_end
        is_nxt = is_morning or is_afternoon

        print(f"현재 시각: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"현재 시간: {current_time}")
        print(f"오전 NXT (08:00-09:00): {GREEN if is_morning else RED}{is_morning}{RESET}")
        print(f"오후 NXT (15:30-20:00): {GREEN if is_afternoon else RED}{is_afternoon}{RESET}")
        print(f"NXT 거래 시간 여부: {GREEN if is_nxt else RED}{is_nxt}{RESET}")

        return is_nxt

    def test_method_1_direct_api_base_code(self, stock_code: str, stock_name: str):
        """방법 1: 직접 API 호출 - 기본 코드"""
        method = "ka10003 직접 호출 (기본 코드)"
        print(f"\n{YELLOW}[방법 1] {method}{RESET}")

        try:
            body = {"stk_cd": stock_code}
            response = self.client.request(
                api_id="ka10003",
                body=body,
                path="stkinfo"
            )

            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr and len(cntr_infr) > 0:
                    latest = cntr_infr[0]
                    cur_prc_str = latest.get('cur_prc', '0')
                    current_price = abs(int(cur_prc_str.replace('+', '').replace('-', '')))

                    if current_price > 0:
                        print(f"{GREEN}✓ 성공{RESET}: {stock_code} {stock_name} = {current_price:,}원")
                        self.results.append({
                            'method': method,
                            'stock_code': stock_code,
                            'code_used': stock_code,
                            'success': True,
                            'price': current_price,
                            'data': latest
                        })
                        return current_price

            print(f"{RED}✗ 실패{RESET}: 체결정보 없음")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': stock_code,
                'success': False,
                'error': '체결정보 없음'
            })
            return None

        except Exception as e:
            print(f"{RED}✗ 오류{RESET}: {e}")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': stock_code,
                'success': False,
                'error': str(e)
            })
            return None

    def test_method_2_direct_api_nx_code(self, stock_code: str, stock_name: str):
        """방법 2: 직접 API 호출 - _NX 코드"""
        method = "ka10003 직접 호출 (_NX 코드)"
        nxt_code = f"{stock_code}_NX"
        print(f"\n{YELLOW}[방법 2] {method}{RESET}")

        try:
            body = {"stk_cd": nxt_code}
            response = self.client.request(
                api_id="ka10003",
                body=body,
                path="stkinfo"
            )

            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr and len(cntr_infr) > 0:
                    latest = cntr_infr[0]
                    cur_prc_str = latest.get('cur_prc', '0')
                    current_price = abs(int(cur_prc_str.replace('+', '').replace('-', '')))

                    if current_price > 0:
                        print(f"{GREEN}✓ 성공{RESET}: {nxt_code} {stock_name} = {current_price:,}원")
                        self.results.append({
                            'method': method,
                            'stock_code': stock_code,
                            'code_used': nxt_code,
                            'success': True,
                            'price': current_price,
                            'data': latest
                        })
                        return current_price

            print(f"{RED}✗ 실패{RESET}: 체결정보 없음")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': nxt_code,
                'success': False,
                'error': '체결정보 없음'
            })
            return None

        except Exception as e:
            print(f"{RED}✗ 오류{RESET}: {e}")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': nxt_code,
                'success': False,
                'error': str(e)
            })
            return None

    def test_method_3_orderbook_base_code(self, stock_code: str, stock_name: str):
        """방법 3: 호가 정보 - 기본 코드"""
        method = "ka10004 호가 조회 (기본 코드)"
        print(f"\n{YELLOW}[방법 3] {method}{RESET}")

        try:
            body = {"stk_cd": stock_code}
            response = self.client.request(
                api_id="ka10004",
                body=body,
                path="mrkcond"
            )

            if response and response.get('return_code') == 0:
                # 현재가 추출 시도
                cur_prc_str = response.get('cur_prc', '0')
                if cur_prc_str and cur_prc_str != '0':
                    current_price = abs(int(cur_prc_str.replace('+', '').replace('-', '')))
                    if current_price > 0:
                        print(f"{GREEN}✓ 성공 (cur_prc){RESET}: {stock_code} {stock_name} = {current_price:,}원")
                        self.results.append({
                            'method': method + " (cur_prc)",
                            'stock_code': stock_code,
                            'code_used': stock_code,
                            'success': True,
                            'price': current_price,
                            'source': 'cur_prc'
                        })
                        return current_price

                # 매도1호가/매수1호가 중간가 계산
                sel_fpr_bid = response.get('sel_fpr_bid', '0').replace('+', '').replace('-', '')
                buy_fpr_bid = response.get('buy_fpr_bid', '0').replace('+', '').replace('-', '')

                sell_price = abs(int(sel_fpr_bid)) if sel_fpr_bid and sel_fpr_bid != '0' else 0
                buy_price = abs(int(buy_fpr_bid)) if buy_fpr_bid and buy_fpr_bid != '0' else 0

                if sell_price > 0 or buy_price > 0:
                    if sell_price > 0 and buy_price > 0:
                        current_price = (sell_price + buy_price) // 2
                    elif sell_price > 0:
                        current_price = sell_price
                    else:
                        current_price = buy_price

                    print(f"{GREEN}✓ 성공 (호가 중간가){RESET}: {stock_code} {stock_name} = {current_price:,}원")
                    print(f"  매도1: {sell_price:,}원, 매수1: {buy_price:,}원")
                    self.results.append({
                        'method': method + " (호가 중간가)",
                        'stock_code': stock_code,
                        'code_used': stock_code,
                        'success': True,
                        'price': current_price,
                        'source': 'orderbook_mid',
                        'sell_price': sell_price,
                        'buy_price': buy_price
                    })
                    return current_price

            print(f"{RED}✗ 실패{RESET}: 호가 정보 없음")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': stock_code,
                'success': False,
                'error': '호가 정보 없음'
            })
            return None

        except Exception as e:
            print(f"{RED}✗ 오류{RESET}: {e}")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': stock_code,
                'success': False,
                'error': str(e)
            })
            return None

    def test_method_4_orderbook_nx_code(self, stock_code: str, stock_name: str):
        """방법 4: 호가 정보 - _NX 코드"""
        method = "ka10004 호가 조회 (_NX 코드)"
        nxt_code = f"{stock_code}_NX"
        print(f"\n{YELLOW}[방법 4] {method}{RESET}")

        try:
            body = {"stk_cd": nxt_code}
            response = self.client.request(
                api_id="ka10004",
                body=body,
                path="mrkcond"
            )

            if response and response.get('return_code') == 0:
                # 현재가 추출 시도
                cur_prc_str = response.get('cur_prc', '0')
                if cur_prc_str and cur_prc_str != '0':
                    current_price = abs(int(cur_prc_str.replace('+', '').replace('-', '')))
                    if current_price > 0:
                        print(f"{GREEN}✓ 성공 (cur_prc){RESET}: {nxt_code} {stock_name} = {current_price:,}원")
                        self.results.append({
                            'method': method + " (cur_prc)",
                            'stock_code': stock_code,
                            'code_used': nxt_code,
                            'success': True,
                            'price': current_price,
                            'source': 'cur_prc'
                        })
                        return current_price

                # 매도1호가/매수1호가 중간가 계산
                sel_fpr_bid = response.get('sel_fpr_bid', '0').replace('+', '').replace('-', '')
                buy_fpr_bid = response.get('buy_fpr_bid', '0').replace('+', '').replace('-', '')

                sell_price = abs(int(sel_fpr_bid)) if sel_fpr_bid and sel_fpr_bid != '0' else 0
                buy_price = abs(int(buy_fpr_bid)) if buy_fpr_bid and buy_fpr_bid != '0' else 0

                if sell_price > 0 or buy_price > 0:
                    if sell_price > 0 and buy_price > 0:
                        current_price = (sell_price + buy_price) // 2
                    elif sell_price > 0:
                        current_price = sell_price
                    else:
                        current_price = buy_price

                    print(f"{GREEN}✓ 성공 (호가 중간가){RESET}: {nxt_code} {stock_name} = {current_price:,}원")
                    print(f"  매도1: {sell_price:,}원, 매수1: {buy_price:,}원")
                    self.results.append({
                        'method': method + " (호가 중간가)",
                        'stock_code': stock_code,
                        'code_used': nxt_code,
                        'success': True,
                        'price': current_price,
                        'source': 'orderbook_mid',
                        'sell_price': sell_price,
                        'buy_price': buy_price
                    })
                    return current_price

            print(f"{RED}✗ 실패{RESET}: 호가 정보 없음")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': nxt_code,
                'success': False,
                'error': '호가 정보 없음'
            })
            return None

        except Exception as e:
            print(f"{RED}✗ 오류{RESET}: {e}")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': nxt_code,
                'success': False,
                'error': str(e)
            })
            return None

    def test_method_5_chart_daily(self, stock_code: str, stock_name: str):
        """방법 5: 일봉 차트 마지막 종가"""
        method = "차트 조회 (일봉 마지막 종가)"
        print(f"\n{YELLOW}[방법 5] {method}{RESET}")

        try:
            body = {
                "stk_cd": stock_code,
                "time_type": "D",  # Daily
                "inq_strt_dt": datetime.now().strftime("%Y%m%d"),
                "inq_end_dt": datetime.now().strftime("%Y%m%d")
            }
            response = self.client.request(
                api_id="ka30002",
                body=body,
                path="chart"
            )

            if response and response.get('return_code') == 0:
                chart_data = response.get('cntr_day_list', [])
                if chart_data and len(chart_data) > 0:
                    latest = chart_data[-1]  # 마지막 데이터
                    close_price_str = latest.get('cncl_prc', '0')
                    close_price = abs(int(close_price_str.replace('+', '').replace('-', '')))

                    if close_price > 0:
                        print(f"{GREEN}✓ 성공{RESET}: {stock_code} {stock_name} = {close_price:,}원 (종가)")
                        self.results.append({
                            'method': method,
                            'stock_code': stock_code,
                            'code_used': stock_code,
                            'success': True,
                            'price': close_price,
                            'source': 'chart_daily_close'
                        })
                        return close_price

            print(f"{RED}✗ 실패{RESET}: 차트 데이터 없음")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': stock_code,
                'success': False,
                'error': '차트 데이터 없음'
            })
            return None

        except Exception as e:
            print(f"{RED}✗ 오류{RESET}: {e}")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': stock_code,
                'success': False,
                'error': str(e)
            })
            return None

    def test_method_6_chart_minute(self, stock_code: str, stock_name: str):
        """방법 6: 분봉 차트 마지막 종가"""
        method = "차트 조회 (분봉 마지막 종가)"
        print(f"\n{YELLOW}[방법 6] {method}{RESET}")

        try:
            body = {
                "stk_cd": stock_code,
                "time_type": "m",  # Minute
                "time_value": "1",
                "inq_strt_dt": datetime.now().strftime("%Y%m%d"),
                "inq_end_dt": datetime.now().strftime("%Y%m%d")
            }
            response = self.client.request(
                api_id="ka30002",
                body=body,
                path="chart"
            )

            if response and response.get('return_code') == 0:
                chart_data = response.get('cntr_day_list', [])
                if chart_data and len(chart_data) > 0:
                    latest = chart_data[-1]  # 마지막 데이터
                    close_price_str = latest.get('cncl_prc', '0')
                    close_price = abs(int(close_price_str.replace('+', '').replace('-', '')))

                    if close_price > 0:
                        print(f"{GREEN}✓ 성공{RESET}: {stock_code} {stock_name} = {close_price:,}원 (1분봉 종가)")
                        self.results.append({
                            'method': method,
                            'stock_code': stock_code,
                            'code_used': stock_code,
                            'success': True,
                            'price': close_price,
                            'source': 'chart_minute_close'
                        })
                        return close_price

            print(f"{RED}✗ 실패{RESET}: 차트 데이터 없음")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': stock_code,
                'success': False,
                'error': '차트 데이터 없음'
            })
            return None

        except Exception as e:
            print(f"{RED}✗ 오류{RESET}: {e}")
            self.results.append({
                'method': method,
                'stock_code': stock_code,
                'code_used': stock_code,
                'success': False,
                'error': str(e)
            })
            return None

    def test_stock_all_methods(self, stock_code: str, stock_name: str):
        """한 종목에 대해 모든 방법 테스트"""
        print(f"\n{'='*80}")
        print(f"{BLUE}[종목 테스트] {stock_code} - {stock_name}{RESET}")
        print(f"{'='*80}")

        results = []

        # 방법 1: 기본 코드 직접 API
        price = self.test_method_1_direct_api_base_code(stock_code, stock_name)
        if price:
            results.append(('방법1_기본코드_API', price))

        # 방법 2: _NX 코드 직접 API
        price = self.test_method_2_direct_api_nx_code(stock_code, stock_name)
        if price:
            results.append(('방법2_NX코드_API', price))

        # 방법 3: 기본 코드 호가
        price = self.test_method_3_orderbook_base_code(stock_code, stock_name)
        if price:
            results.append(('방법3_기본코드_호가', price))

        # 방법 4: _NX 코드 호가
        price = self.test_method_4_orderbook_nx_code(stock_code, stock_name)
        if price:
            results.append(('방법4_NX코드_호가', price))

        # 방법 5: 일봉 차트
        price = self.test_method_5_chart_daily(stock_code, stock_name)
        if price:
            results.append(('방법5_일봉차트', price))

        # 방법 6: 분봉 차트
        price = self.test_method_6_chart_minute(stock_code, stock_name)
        if price:
            results.append(('방법6_분봉차트', price))

        # 결과 요약
        print(f"\n{BLUE}[{stock_code} 결과 요약]{RESET}")
        if results:
            print(f"{GREEN}성공한 방법: {len(results)}개{RESET}")
            for method, price in results:
                print(f"  - {method}: {price:,}원")
        else:
            print(f"{RED}모든 방법 실패{RESET}")

        return results

    def run_all_tests(self):
        """모든 종목, 모든 방법 테스트"""
        print(f"\n{'#'*80}")
        print(f"#{' '*78}#")
        print(f"#  NXT 현재가 조회 종합 테스트 - 성공 조합 찾기")
        print(f"#{' '*78}#")
        print(f"{'#'*80}")

        # 시간 상태 확인
        is_nxt = self.check_time_status()

        # 각 종목 테스트
        all_stock_results = {}
        for stock_code, stock_name in self.test_stocks:
            results = self.test_stock_all_methods(stock_code, stock_name)
            all_stock_results[stock_code] = results

        # 최종 통계
        self.print_final_summary(all_stock_results, is_nxt)

        # 결과를 JSON 파일로 저장
        self.save_results()

    def print_final_summary(self, all_stock_results: dict, is_nxt: bool):
        """최종 결과 요약"""
        print(f"\n{'='*80}")
        print(f"{BLUE}[최종 결과 요약]{RESET}")
        print(f"{'='*80}")

        # 방법별 성공률 통계
        method_stats = {}
        for result in self.results:
            method = result['method']
            if method not in method_stats:
                method_stats[method] = {'success': 0, 'fail': 0}

            if result['success']:
                method_stats[method]['success'] += 1
            else:
                method_stats[method]['fail'] += 1

        print(f"\n{YELLOW}[방법별 성공률]{RESET}")
        print(f"{'방법':<50} {'성공':>8} {'실패':>8} {'성공률':>10}")
        print(f"{'-'*80}")

        for method, stats in sorted(method_stats.items()):
            total = stats['success'] + stats['fail']
            success_rate = (stats['success'] / total * 100) if total > 0 else 0
            color = GREEN if success_rate > 0 else RED
            print(f"{method:<50} {color}{stats['success']:>8}{RESET} {stats['fail']:>8} {success_rate:>9.1f}%")

        # 추천 방법
        print(f"\n{YELLOW}[추천 방법]{RESET}")
        best_methods = sorted(method_stats.items(), key=lambda x: x[1]['success'], reverse=True)
        if best_methods and best_methods[0][1]['success'] > 0:
            for i, (method, stats) in enumerate(best_methods[:3], 1):
                if stats['success'] > 0:
                    print(f"{GREEN}{i}. {method}{RESET} - 성공 {stats['success']}/{stats['success'] + stats['fail']}회")
        else:
            print(f"{RED}성공한 방법이 없습니다.{RESET}")

        # NXT 시간대 여부에 따른 조언
        print(f"\n{YELLOW}[조언]{RESET}")
        if is_nxt:
            print(f"{GREEN}현재 NXT 거래 시간입니다.{RESET}")
            print(f"- _NX 접미사를 사용한 방법이 성공할 가능성이 높습니다.")
        else:
            print(f"{RED}현재 NXT 거래 시간이 아닙니다.{RESET}")
            print(f"- 기본 코드(접미사 없음)를 사용한 방법이 성공할 가능성이 높습니다.")
            print(f"- NXT 종목은 정규 시장 시간 외에는 조회가 어려울 수 있습니다.")

    def save_results(self):
        """결과를 JSON 파일로 저장"""
        output_file = Path(__file__).parent / "nxt_price_test_results.json"

        data = {
            'timestamp': datetime.now().isoformat(),
            'results': self.results
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n{GREEN}결과 저장됨:{RESET} {output_file}")


def main():
    """메인 실행"""
    print(f"\n{BLUE}TradingBot 초기화 중 (클라이언트 포함)...{RESET}")

    # main.py의 TradingBotV2를 import하여 초기화
    try:
        from main import TradingBotV2

        # 봇 초기화 (클라이언트 자동 초기화됨)
        bot = TradingBotV2()

        # 봇에서 클라이언트 가져오기
        if not bot.client:
            print(f"{RED}클라이언트 초기화 실패{RESET}")
            return

        client = bot.client
        print(f"{GREEN}클라이언트 초기화 완료 (from TradingBotV2){RESET}")

    except Exception as e:
        print(f"{RED}TradingBot 초기화 실패: {e}{RESET}")
        print(f"{YELLOW}Fallback: 직접 클라이언트 초기화 시도...{RESET}")

        try:
            from core.rest_client import KiwoomRESTClient
            client = KiwoomRESTClient()  # 인자 없이 초기화
            print(f"{GREEN}클라이언트 직접 초기화 완료{RESET}")
        except Exception as e2:
            print(f"{RED}클라이언트 직접 초기화도 실패: {e2}{RESET}")
            return

    # 테스트 실행
    discovery = NXTPriceDiscovery(client)
    discovery.run_all_tests()


if __name__ == "__main__":
    main()
