"""
NXT 거래가능 종목 - 종가 vs 현재가 비교 테스트 (다방법 탐색)

목적:
1. 일반시장 종가와 NXT 현재가의 차이 확인
2. 여러 API 메서드로 NXT 현재가 조회 시도
3. 5초 간격 10번 반복 테스트로 실시간 가격 변동 감지

테스트 방법:
- Method 1: ka10003 API (기본 코드)
- Method 2: ka10003 API (_NX 접미사)
- Method 3: ka10004 호가 API (기본 코드)
- Method 4: ka10004 호가 API (_NX 접미사)
- Method 5: ka10081 차트 종가
- Method 6: NXTRealtimePriceManager
"""
import sys
from pathlib import Path
from datetime import datetime
import json
import time
from typing import Dict, Any, Optional, List

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
BOLD = '\033[1m'
RESET = '\033[0m'


def is_nxt_hours():
    """NXT 거래 시간 여부 확인"""
    from utils.trading_date import is_nxt_hours
    return is_nxt_hours()


def method1_ka10003_basic(client, stock_code: str) -> Optional[Dict[str, Any]]:
    """Method 1: ka10003 API - 기본 코드"""
    try:
        response = client.request(
            api_id="ka10003",
            body={"stk_cd": stock_code},
            path="stkinfo"
        )

        if response and response.get('return_code') == 0:
            cntr_infr = response.get('cntr_infr', [])
            if cntr_infr and len(cntr_infr) > 0:
                latest = cntr_infr[0]
                cur_prc = latest.get('cur_prc', '0')
                price = abs(int(str(cur_prc).replace('+', '').replace('-', '').replace(',', '')))

                return {
                    'success': True,
                    'price': price,
                    'source': 'ka10003_basic',
                    'stex_tp': latest.get('stex_tp', ''),
                    'time': latest.get('tm', ''),
                    'raw_response': latest
                }

        return {'success': False, 'error': response.get('return_msg') if response else 'No response'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def method2_ka10003_nx(client, stock_code: str) -> Optional[Dict[str, Any]]:
    """Method 2: ka10003 API - _NX 접미사"""
    try:
        nx_code = stock_code if stock_code.endswith('_NX') else f"{stock_code}_NX"
        response = client.request(
            api_id="ka10003",
            body={"stk_cd": nx_code},
            path="stkinfo"
        )

        if response and response.get('return_code') == 0:
            cntr_infr = response.get('cntr_infr', [])
            if cntr_infr and len(cntr_infr) > 0:
                latest = cntr_infr[0]
                cur_prc = latest.get('cur_prc', '0')
                price = abs(int(str(cur_prc).replace('+', '').replace('-', '').replace(',', '')))

                return {
                    'success': True,
                    'price': price,
                    'source': 'ka10003_nx',
                    'stex_tp': latest.get('stex_tp', ''),
                    'time': latest.get('tm', ''),
                    'raw_response': latest
                }

        return {'success': False, 'error': response.get('return_msg') if response else 'No response'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def method3_ka10004_basic(client, stock_code: str) -> Optional[Dict[str, Any]]:
    """Method 3: ka10004 호가 API - 기본 코드"""
    try:
        response = client.request(
            api_id="ka10004",
            body={"stk_cd": stock_code},
            path="mrkcond"
        )

        if response and response.get('return_code') == 0:
            sel_fpr_bid = response.get('sel_fpr_bid', '0').replace('+', '').replace('-', '')
            buy_fpr_bid = response.get('buy_fpr_bid', '0').replace('+', '').replace('-', '')

            sell_price = abs(int(sel_fpr_bid)) if sel_fpr_bid != '0' else 0
            buy_price = abs(int(buy_fpr_bid)) if buy_fpr_bid != '0' else 0

            if sell_price > 0 and buy_price > 0:
                mid_price = (sell_price + buy_price) // 2
            elif sell_price > 0:
                mid_price = sell_price
            elif buy_price > 0:
                mid_price = buy_price
            else:
                return {'success': False, 'error': 'No valid price'}

            return {
                'success': True,
                'price': mid_price,
                'source': 'ka10004_basic_orderbook',
                'sell_price': sell_price,
                'buy_price': buy_price,
                'raw_response': response
            }

        return {'success': False, 'error': response.get('return_msg') if response else 'No response'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def method4_ka10004_nx(client, stock_code: str) -> Optional[Dict[str, Any]]:
    """Method 4: ka10004 호가 API - _NX 접미사"""
    try:
        nx_code = stock_code if stock_code.endswith('_NX') else f"{stock_code}_NX"
        response = client.request(
            api_id="ka10004",
            body={"stk_cd": nx_code},
            path="mrkcond"
        )

        if response and response.get('return_code') == 0:
            sel_fpr_bid = response.get('sel_fpr_bid', '0').replace('+', '').replace('-', '')
            buy_fpr_bid = response.get('buy_fpr_bid', '0').replace('+', '').replace('-', '')

            sell_price = abs(int(sel_fpr_bid)) if sel_fpr_bid != '0' else 0
            buy_price = abs(int(buy_fpr_bid)) if buy_fpr_bid != '0' else 0

            if sell_price > 0 and buy_price > 0:
                mid_price = (sell_price + buy_price) // 2
            elif sell_price > 0:
                mid_price = sell_price
            elif buy_price > 0:
                mid_price = buy_price
            else:
                return {'success': False, 'error': 'No valid price'}

            return {
                'success': True,
                'price': mid_price,
                'source': 'ka10004_nx_orderbook',
                'sell_price': sell_price,
                'buy_price': buy_price,
                'raw_response': response
            }

        return {'success': False, 'error': response.get('return_msg') if response else 'No response'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def method5_ka10081_chart_close(client, stock_code: str) -> Optional[Dict[str, Any]]:
    """Method 5: ka10081 차트 API - 종가"""
    try:
        from utils.trading_date import get_last_trading_date

        date = get_last_trading_date()
        response = client.request(
            api_id="ka10081",
            body={"stk_cd": stock_code, "base_dt": date, "upd_stkpc_tp": "1"},
            path="chart"
        )

        if response and response.get('return_code') == 0:
            daily_data = response.get('stk_dt_pole_chart_qry', [])
            if daily_data and len(daily_data) > 0:
                latest = daily_data[0]
                close_price = int(latest.get('cur_prc', 0))

                return {
                    'success': True,
                    'price': close_price,
                    'source': 'ka10081_chart_close',
                    'date': latest.get('dt', ''),
                    'raw_response': latest
                }

        return {'success': False, 'error': response.get('return_msg') if response else 'No response'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def method6_nxt_manager(market_api, stock_code: str) -> Optional[Dict[str, Any]]:
    """Method 6: NXTRealtimePriceManager"""
    try:
        from utils.nxt_realtime_price import NXTRealtimePriceManager

        manager = NXTRealtimePriceManager(market_api)
        price_data = manager.get_realtime_price(stock_code, force_refresh=True)

        if price_data:
            return {
                'success': True,
                'price': price_data['current_price'],
                'source': price_data['source'],
                'is_nxt_hours': price_data.get('is_nxt_hours', False),
                'raw_response': price_data
            }

        return {'success': False, 'error': 'Manager returned None'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def test_single_stock_all_methods(client, market_api, stock_code: str, stock_name: str, iteration: int):
    """단일 종목을 모든 방법으로 테스트"""
    print(f"\n{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{WHITE}{BOLD}[#{iteration}] {stock_name} ({stock_code}) - {datetime.now().strftime('%H:%M:%S')}{RESET}")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")

    results = {}

    # Method 1
    print(f"\n{YELLOW}Method 1: ka10003 (기본 코드){RESET}")
    result = method1_ka10003_basic(client, stock_code)
    results['method1'] = result
    if result['success']:
        print(f"{GREEN}✅ 성공: {result['price']:,}원{RESET} | 거래소: {result.get('stex_tp', 'N/A')} | 시간: {result.get('time', 'N/A')}")
    else:
        print(f"{RED}❌ 실패: {result.get('error', 'Unknown error')}{RESET}")

    # Method 2
    print(f"\n{YELLOW}Method 2: ka10003 (_NX 접미사){RESET}")
    result = method2_ka10003_nx(client, stock_code)
    results['method2'] = result
    if result['success']:
        print(f"{GREEN}✅ 성공: {result['price']:,}원{RESET} | 거래소: {result.get('stex_tp', 'N/A')} | 시간: {result.get('time', 'N/A')}")
    else:
        print(f"{RED}❌ 실패: {result.get('error', 'Unknown error')}{RESET}")

    # Method 3
    print(f"\n{YELLOW}Method 3: ka10004 호가 (기본 코드){RESET}")
    result = method3_ka10004_basic(client, stock_code)
    results['method3'] = result
    if result['success']:
        print(f"{GREEN}✅ 성공: {result['price']:,}원{RESET} | 매도: {result.get('sell_price', 0):,} | 매수: {result.get('buy_price', 0):,}")
    else:
        print(f"{RED}❌ 실패: {result.get('error', 'Unknown error')}{RESET}")

    # Method 4
    print(f"\n{YELLOW}Method 4: ka10004 호가 (_NX 접미사){RESET}")
    result = method4_ka10004_nx(client, stock_code)
    results['method4'] = result
    if result['success']:
        print(f"{GREEN}✅ 성공: {result['price']:,}원{RESET} | 매도: {result.get('sell_price', 0):,} | 매수: {result.get('buy_price', 0):,}")
    else:
        print(f"{RED}❌ 실패: {result.get('error', 'Unknown error')}{RESET}")

    # Method 5
    print(f"\n{YELLOW}Method 5: ka10081 차트 종가{RESET}")
    result = method5_ka10081_chart_close(client, stock_code)
    results['method5'] = result
    if result['success']:
        print(f"{GREEN}✅ 성공: {result['price']:,}원{RESET} | 날짜: {result.get('date', 'N/A')}")
    else:
        print(f"{RED}❌ 실패: {result.get('error', 'Unknown error')}{RESET}")

    # Method 6
    print(f"\n{YELLOW}Method 6: NXTRealtimePriceManager{RESET}")
    result = method6_nxt_manager(market_api, stock_code)
    results['method6'] = result
    if result['success']:
        print(f"{GREEN}✅ 성공: {result['price']:,}원{RESET} | 출처: {result.get('source', 'N/A')} | NXT시간: {result.get('is_nxt_hours', False)}")
    else:
        print(f"{RED}❌ 실패: {result.get('error', 'Unknown error')}{RESET}")

    # 가격 비교 분석
    print(f"\n{MAGENTA}━━━ 가격 비교 분석 ━━━{RESET}")
    prices = []
    for method_name, result in results.items():
        if result['success']:
            prices.append((method_name, result['price']))

    if len(prices) > 1:
        prices_sorted = sorted(prices, key=lambda x: x[1])
        min_price = prices_sorted[0][1]
        max_price = prices_sorted[-1][1]

        if min_price != max_price:
            diff = max_price - min_price
            diff_pct = (diff / min_price) * 100
            print(f"{YELLOW}⚠️  가격 차이 발견!{RESET}")
            print(f"  최저가: {min_price:,}원 ({prices_sorted[0][0]})")
            print(f"  최고가: {max_price:,}원 ({prices_sorted[-1][0]})")
            print(f"  차이: {diff:,}원 ({diff_pct:.2f}%)")
            print(f"\n{GREEN}✅ 차트 종가와 다른 메서드의 가격이 다르다면, 해당 메서드가 실시간 현재가를 불러오는 것!{RESET}")
        else:
            print(f"{BLUE}모든 메서드의 가격이 동일: {min_price:,}원{RESET}")

    return results


def main():
    """메인 테스트"""
    print(f"\n{BLUE}{BOLD}{'='*80}{RESET}")
    print(f"{BLUE}{BOLD}NXT 거래가능 종목 - 종가 vs 현재가 비교 테스트 (다방법 탐색){RESET}")
    print(f"{BLUE}{BOLD}{'='*80}{RESET}")

    # 현재 시간 정보
    now = datetime.now()
    in_nxt_hours = is_nxt_hours()

    print(f"\n{CYAN}📅 테스트 시작 시간{RESET}")
    print(f"  시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  NXT 거래 시간: {'✅ 예' if in_nxt_hours else '❌ 아니오'} (08:00-09:00, 15:30-20:00)")

    if not in_nxt_hours:
        print(f"\n{YELLOW}⚠️  경고: 현재 NXT 거래 시간이 아닙니다!{RESET}")
        print(f"{YELLOW}   테스트는 진행되지만, NXT 현재가와 차트 종가의 차이를 확인하기 어려울 수 있습니다.{RESET}")

    try:
        from main import TradingBotV2
        from api.market import MarketAPI

        bot = TradingBotV2()

        if not bot.client:
            print(f"{RED}❌ API 클라이언트 초기화 실패{RESET}")
            return

        # Check if client has a valid token
        if not hasattr(bot.client, 'token') or not bot.client.token:
            print(f"{RED}❌ API 인증 실패{RESET}")
            return

        print(f"{GREEN}✅ API 연결 성공{RESET}")

        client = bot.client
        market_api = MarketAPI(client)

        # 테스트 종목 10개 (NXT 거래 가능 종목)
        test_stocks = [
            ("249420", "일동제약"),
            ("052020", "에프엔에스테크"),
            ("001340", "백광소재"),
            ("058470", "리노공업"),
            ("039030", "이오테크닉스"),
            ("086900", "메디톡스"),
            ("234080", "JW생명과학"),
            ("064760", "티씨케이"),
            ("108860", "셀바스AI"),
            ("241560", "두산밥캣"),
        ]

        print(f"\n{CYAN}📋 테스트 종목: {len(test_stocks)}개{RESET}")
        for code, name in test_stocks:
            print(f"  • {name} ({code})")

        print(f"\n{CYAN}⏱️  테스트 설정: 5초 간격, 10회 반복{RESET}")

        # 각 종목별 전체 결과 저장
        all_results = {code: [] for code, _ in test_stocks}

        # 10회 반복 테스트
        for i in range(1, 11):
            print(f"\n{BLUE}{BOLD}{'='*80}{RESET}")
            print(f"{BLUE}{BOLD}테스트 회차: {i}/10{RESET}")
            print(f"{BLUE}{BOLD}{'='*80}{RESET}")

            for stock_code, stock_name in test_stocks:
                results = test_single_stock_all_methods(client, market_api, stock_code, stock_name, i)
                all_results[stock_code].append({
                    'iteration': i,
                    'timestamp': datetime.now().isoformat(),
                    'results': results
                })

                # 마지막 종목이 아니면 약간의 딜레이
                if stock_code != test_stocks[-1][0]:
                    time.sleep(0.5)

            # 다음 회차 전 대기
            if i < 10:
                print(f"\n{YELLOW}⏳ 다음 회차까지 5초 대기...{RESET}")
                time.sleep(5)

        # 최종 분석
        print(f"\n{MAGENTA}{BOLD}{'='*80}{RESET}")
        print(f"{MAGENTA}{BOLD}📊 최종 분석 결과{RESET}")
        print(f"{MAGENTA}{BOLD}{'='*80}{RESET}")

        for stock_code, stock_name in test_stocks:
            print(f"\n{WHITE}{BOLD}{stock_name} ({stock_code}){RESET}")

            # 각 메서드별 성공률 계산
            method_stats = {}
            for iteration_data in all_results[stock_code]:
                for method_name, result in iteration_data['results'].items():
                    if method_name not in method_stats:
                        method_stats[method_name] = {'success': 0, 'total': 0, 'prices': []}

                    method_stats[method_name]['total'] += 1
                    if result['success']:
                        method_stats[method_name]['success'] += 1
                        method_stats[method_name]['prices'].append(result['price'])

            # 통계 출력
            for method_name, stats in method_stats.items():
                success_rate = (stats['success'] / stats['total']) * 100
                avg_price = sum(stats['prices']) / len(stats['prices']) if stats['prices'] else 0

                color = GREEN if success_rate >= 80 else YELLOW if success_rate >= 50 else RED
                print(f"  {color}{method_name}: {success_rate:.1f}% 성공률{RESET}", end='')

                if stats['prices']:
                    print(f" | 평균가: {avg_price:,.0f}원 | 최저: {min(stats['prices']):,}원 | 최고: {max(stats['prices']):,}원")
                else:
                    print()

        # 최종 권장사항
        print(f"\n{MAGENTA}{BOLD}{'='*80}{RESET}")
        print(f"{MAGENTA}{BOLD}💡 권장 사항{RESET}")
        print(f"{MAGENTA}{BOLD}{'='*80}{RESET}")

        print(f"\n{WHITE}1. 높은 성공률을 보이는 메서드를 우선 사용하세요.{RESET}")
        print(f"{WHITE}2. 차트 종가(Method 5)와 다른 가격을 반환하는 메서드가 실시간 현재가를 제공합니다.{RESET}")
        print(f"{WHITE}3. NXT 시간대에는 stex_tp='NXT' 또는 is_nxt_hours=True인 메서드를 사용하세요.{RESET}")
        print(f"{WHITE}4. 여러 메서드를 fallback으로 구성하여 안정성을 높이세요.{RESET}")

        # 결과를 JSON 파일로 저장
        output_file = project_root / 'tests' / 'manual' / f'nxt_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n{GREEN}✅ 테스트 결과가 저장되었습니다: {output_file}{RESET}")

    except Exception as e:
        print(f"{RED}❌ 오류 발생: {e}{RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
