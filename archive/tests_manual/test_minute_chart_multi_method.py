"""
분봉 데이터 조회 테스트 (다방법 탐색)

목적:
1. 여러 API 메서드로 분봉 데이터 조회 시도
2. 1분, 3분, 5분, 15분, 30분, 60분봉 조회 테스트
3. 5초 간격 10번 반복 테스트로 데이터 변동 확인

테스트 방법:
- Method 1: ka10080 API (tic_scope 파라미터 변경)
- Method 2: ka10080 API (다른 파라미터 조합)
- Method 3: ChartDataAPI.get_minute_chart() (공식 래퍼)
- Method 4: 다중 시간프레임 일괄 조회
- Method 5: 실시간 분봉 차트 생성기 (WebSocket 기반)
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


def method1_ka10080_direct(client, stock_code: str, interval: int) -> Optional[Dict[str, Any]]:
    """Method 1: ka10080 API 직접 호출 (기본)"""
    try:
        response = client.request(
            api_id="ka10080",
            body={
                "stk_cd": stock_code,
                "tic_scope": str(interval),
                "upd_stkpc_tp": "1"  # 수정주가 반영
            },
            path="chart"
        )

        if response and response.get('return_code') == 0:
            minute_data = response.get('stk_tic_pole_chart_qry', [])

            if minute_data:
                # 최근 3개 캔들만 파싱
                parsed_data = []
                for item in minute_data[:3]:
                    try:
                        parsed_data.append({
                            'date': item.get('dt', ''),
                            'time': item.get('tm', ''),
                            'open': int(item.get('open_pric', 0)),
                            'high': int(item.get('high_pric', 0)),
                            'low': int(item.get('low_pric', 0)),
                            'close': int(item.get('cur_prc', 0)),
                            'volume': int(item.get('trde_qty', 0))
                        })
                    except:
                        continue

                return {
                    'success': True,
                    'data_count': len(minute_data),
                    'sample_data': parsed_data,
                    'source': 'ka10080_direct',
                    'interval': interval
                }

        return {'success': False, 'error': response.get('return_msg') if response else 'No response'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def method2_ka10080_alt_params(client, stock_code: str, interval: int) -> Optional[Dict[str, Any]]:
    """Method 2: ka10080 API 대체 파라미터 조합"""
    try:
        # 대체 파라미터 시도
        response = client.request(
            api_id="ka10080",
            body={
                "stk_cd": stock_code,
                "tic_scope": str(interval),
                "upd_stkpc_tp": "0"  # 수정주가 미반영
            },
            path="chart"
        )

        if response and response.get('return_code') == 0:
            minute_data = response.get('stk_tic_pole_chart_qry', [])

            if minute_data:
                parsed_data = []
                for item in minute_data[:3]:
                    try:
                        parsed_data.append({
                            'date': item.get('dt', ''),
                            'time': item.get('tm', ''),
                            'open': int(item.get('open_pric', 0)),
                            'high': int(item.get('high_pric', 0)),
                            'low': int(item.get('low_pric', 0)),
                            'close': int(item.get('cur_prc', 0)),
                            'volume': int(item.get('trde_qty', 0))
                        })
                    except:
                        continue

                return {
                    'success': True,
                    'data_count': len(minute_data),
                    'sample_data': parsed_data,
                    'source': 'ka10080_alt_params',
                    'interval': interval
                }

        return {'success': False, 'error': response.get('return_msg') if response else 'No response'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def method3_chart_api_wrapper(chart_api, stock_code: str, interval: int) -> Optional[Dict[str, Any]]:
    """Method 3: ChartDataAPI 공식 래퍼 사용"""
    try:
        minute_data = chart_api.get_minute_chart(
            stock_code=stock_code,
            interval=interval,
            count=100,
            adjusted=True
        )

        if minute_data:
            return {
                'success': True,
                'data_count': len(minute_data),
                'sample_data': minute_data[:3],  # 최근 3개
                'source': 'ChartDataAPI_wrapper',
                'interval': interval
            }

        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def method4_multi_timeframe(chart_api, stock_code: str) -> Optional[Dict[str, Any]]:
    """Method 4: 다중 시간프레임 일괄 조회"""
    try:
        result = chart_api.get_multi_timeframe_data(
            stock_code=stock_code,
            timeframes=[1, 5, 15, 30, 60]
        )

        # 각 시간프레임별 데이터 개수 확인
        summary = {}
        for tf, data in result.items():
            summary[tf] = {
                'count': len(data),
                'has_data': len(data) > 0,
                'sample': data[:1] if data else []  # 최근 1개만
            }

        return {
            'success': True,
            'source': 'multi_timeframe',
            'summary': summary
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def method5_alternative_intervals(client, stock_code: str) -> Optional[Dict[str, Any]]:
    """Method 5: 다양한 interval 값 시도 (3분, 10분 등)"""
    try:
        # 3분봉 시도 (공식 문서에 없지만 시도)
        test_intervals = [3, 10, 20]
        results = {}

        for interval in test_intervals:
            response = client.request(
                api_id="ka10080",
                body={
                    "stk_cd": stock_code,
                    "tic_scope": str(interval),
                    "upd_stkpc_tp": "1"
                },
                path="chart"
            )

            if response and response.get('return_code') == 0:
                minute_data = response.get('stk_tic_pole_chart_qry', [])
                results[f'{interval}min'] = {
                    'success': True,
                    'count': len(minute_data)
                }
            else:
                results[f'{interval}min'] = {
                    'success': False,
                    'error': response.get('return_msg') if response else 'No response'
                }

        return {
            'success': True,
            'source': 'alternative_intervals',
            'results': results
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def test_single_stock_minute_data(client, chart_api, stock_code: str, stock_name: str, iteration: int):
    """단일 종목의 분봉 데이터 테스트"""
    print(f"\n{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{WHITE}{BOLD}[#{iteration}] {stock_name} ({stock_code}) - {datetime.now().strftime('%H:%M:%S')}{RESET}")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")

    results = {}

    # 테스트할 분봉 간격들
    test_intervals = [1, 3, 5, 15, 30, 60]

    for interval in test_intervals:
        print(f"\n{MAGENTA}━━━ {interval}분봉 테스트 ━━━{RESET}")

        # Method 1: Direct ka10080
        print(f"\n{YELLOW}Method 1: ka10080 직접 호출 (수정주가 반영){RESET}")
        result = method1_ka10080_direct(client, stock_code, interval)
        key = f'{interval}min_method1'
        results[key] = result

        if result['success']:
            print(f"{GREEN}✅ 성공: {result['data_count']}개 조회{RESET}")
            if result['sample_data']:
                latest = result['sample_data'][0]
                print(f"  최근 캔들: {latest['date']} {latest['time']} | "
                      f"O:{latest['open']:,} H:{latest['high']:,} L:{latest['low']:,} C:{latest['close']:,}")
        else:
            print(f"{RED}❌ 실패: {result.get('error', 'Unknown error')}{RESET}")

        # Method 2: Alternative params
        print(f"\n{YELLOW}Method 2: ka10080 대체 파라미터 (수정주가 미반영){RESET}")
        result = method2_ka10080_alt_params(client, stock_code, interval)
        key = f'{interval}min_method2'
        results[key] = result

        if result['success']:
            print(f"{GREEN}✅ 성공: {result['data_count']}개 조회{RESET}")
        else:
            print(f"{RED}❌ 실패: {result.get('error', 'Unknown error')}{RESET}")

        # Method 3: ChartDataAPI wrapper (유효한 간격만)
        if interval in [1, 5, 15, 30, 60]:
            print(f"\n{YELLOW}Method 3: ChartDataAPI 래퍼{RESET}")
            result = method3_chart_api_wrapper(chart_api, stock_code, interval)
            key = f'{interval}min_method3'
            results[key] = result

            if result['success']:
                print(f"{GREEN}✅ 성공: {result['data_count']}개 조회{RESET}")
            else:
                print(f"{RED}❌ 실패: {result.get('error', 'Unknown error')}{RESET}")

    # Method 4: Multi timeframe
    print(f"\n{MAGENTA}━━━ 다중 시간프레임 일괄 조회 ━━━{RESET}")
    print(f"\n{YELLOW}Method 4: 다중 시간프레임 일괄 조회{RESET}")
    result = method4_multi_timeframe(chart_api, stock_code)
    results['multi_timeframe'] = result

    if result['success']:
        print(f"{GREEN}✅ 성공{RESET}")
        for tf, info in result['summary'].items():
            status = f"{GREEN}✓{RESET}" if info['has_data'] else f"{RED}✗{RESET}"
            print(f"  {status} {tf}: {info['count']}개")
    else:
        print(f"{RED}❌ 실패: {result.get('error', 'Unknown error')}{RESET}")

    # Method 5: Alternative intervals
    print(f"\n{MAGENTA}━━━ 비표준 간격 시도 (3분, 10분, 20분) ━━━{RESET}")
    print(f"\n{YELLOW}Method 5: 비표준 분봉 간격 시도{RESET}")
    result = method5_alternative_intervals(client, stock_code)
    results['alternative_intervals'] = result

    if result['success']:
        print(f"{GREEN}✅ 테스트 완료{RESET}")
        for interval_name, info in result['results'].items():
            if info['success']:
                print(f"  {GREEN}✓{RESET} {interval_name}: {info['count']}개")
            else:
                print(f"  {RED}✗{RESET} {interval_name}: {info.get('error', 'Failed')}")
    else:
        print(f"{RED}❌ 실패: {result.get('error', 'Unknown error')}{RESET}")

    return results


def main():
    """메인 테스트"""
    print(f"\n{BLUE}{BOLD}{'='*80}{RESET}")
    print(f"{BLUE}{BOLD}분봉 데이터 조회 테스트 (다방법 탐색){RESET}")
    print(f"{BLUE}{BOLD}{'='*80}{RESET}")

    now = datetime.now()
    print(f"\n{CYAN}📅 테스트 시작 시간{RESET}")
    print(f"  시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        from main import TradingBotV2
        from api.market.chart_data import ChartDataAPI

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
        chart_api = ChartDataAPI(client)

        # 테스트 종목 10개
        test_stocks = [
            ("005930", "삼성전자"),
            ("000660", "SK하이닉스"),
            ("035420", "NAVER"),
            ("051910", "LG화학"),
            ("005490", "POSCO홀딩스"),
            ("035720", "카카오"),
            ("006400", "삼성SDI"),
            ("028260", "삼성물산"),
            ("068270", "셀트리온"),
            ("105560", "KB금융"),
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
                results = test_single_stock_minute_data(client, chart_api, stock_code, stock_name, i)
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

        # 전체 성공률 통계
        method_success_count = {}
        method_total_count = {}

        for stock_code, stock_name in test_stocks:
            print(f"\n{WHITE}{BOLD}{stock_name} ({stock_code}){RESET}")

            # 각 메서드별 성공률 계산
            for iteration_data in all_results[stock_code]:
                for method_name, result in iteration_data['results'].items():
                    if method_name not in method_success_count:
                        method_success_count[method_name] = 0
                        method_total_count[method_name] = 0

                    method_total_count[method_name] += 1
                    if result.get('success', False):
                        method_success_count[method_name] += 1

            # 종목별 요약
            method_stats = {}
            for iteration_data in all_results[stock_code]:
                for method_name, result in iteration_data['results'].items():
                    if method_name not in method_stats:
                        method_stats[method_name] = {'success': 0, 'total': 0}

                    method_stats[method_name]['total'] += 1
                    if result.get('success', False):
                        method_stats[method_name]['success'] += 1

            # 분봉 간격별 최고 성공률 메서드
            for interval in [1, 3, 5, 15, 30, 60]:
                interval_methods = {k: v for k, v in method_stats.items() if k.startswith(f'{interval}min')}
                if interval_methods:
                    best_method = max(interval_methods.items(), key=lambda x: x[1]['success'] / x[1]['total'])
                    success_rate = (best_method[1]['success'] / best_method[1]['total']) * 100
                    color = GREEN if success_rate >= 80 else YELLOW if success_rate >= 50 else RED
                    print(f"  {color}{interval}분봉 최고: {best_method[0]} ({success_rate:.1f}%){RESET}")

        # 전체 통계
        print(f"\n{MAGENTA}{BOLD}{'='*80}{RESET}")
        print(f"{MAGENTA}{BOLD}🎯 전체 메서드 성공률{RESET}")
        print(f"{MAGENTA}{BOLD}{'='*80}{RESET}")

        sorted_methods = sorted(method_success_count.items(),
                              key=lambda x: x[1] / method_total_count[x[0]] if method_total_count[x[0]] > 0 else 0,
                              reverse=True)

        for method_name, success_count in sorted_methods:
            total_count = method_total_count[method_name]
            success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
            color = GREEN if success_rate >= 80 else YELLOW if success_rate >= 50 else RED
            print(f"{color}{method_name}: {success_rate:.1f}% ({success_count}/{total_count}){RESET}")

        # 최종 권장사항
        print(f"\n{MAGENTA}{BOLD}{'='*80}{RESET}")
        print(f"{MAGENTA}{BOLD}💡 권장 사항{RESET}")
        print(f"{MAGENTA}{BOLD}{'='*80}{RESET}")

        print(f"\n{WHITE}1. 높은 성공률을 보이는 메서드를 우선 사용하세요.{RESET}")
        print(f"{WHITE}2. 표준 간격 (1, 5, 15, 30, 60분)은 ChartDataAPI 래퍼를 사용하세요.{RESET}")
        print(f"{WHITE}3. 비표준 간격 (3, 10, 20분)은 직접 ka10080 API를 호출하세요.{RESET}")
        print(f"{WHITE}4. 여러 메서드를 fallback으로 구성하여 안정성을 높이세요.{RESET}")
        print(f"{WHITE}5. 수정주가 반영 여부(upd_stkpc_tp)를 용도에 맞게 선택하세요.{RESET}")

        # 성공한 메서드 예제 코드 출력
        print(f"\n{CYAN}{BOLD}{'='*80}{RESET}")
        print(f"{CYAN}{BOLD}📝 성공한 메서드 사용 예제{RESET}")
        print(f"{CYAN}{BOLD}{'='*80}{RESET}")

        if sorted_methods:
            best_method = sorted_methods[0][0]
            print(f"\n{GREEN}가장 성공률이 높은 메서드: {best_method}{RESET}")

            if 'method1' in best_method or 'method2' in best_method:
                print(f"\n{WHITE}# ka10080 API 직접 호출{RESET}")
                print(f"""
response = client.request(
    api_id="ka10080",
    body={{
        "stk_cd": stock_code,
        "tic_scope": "5",  # 1, 5, 15, 30, 60
        "upd_stkpc_tp": "1"  # 1=수정주가 반영, 0=미반영
    }},
    path="chart"
)
minute_data = response.get('stk_tic_pole_chart_qry', [])
""")
            elif 'method3' in best_method:
                print(f"\n{WHITE}# ChartDataAPI 래퍼 사용{RESET}")
                print(f"""
from api.market.chart_data import ChartDataAPI

chart_api = ChartDataAPI(client)
minute_data = chart_api.get_minute_chart(
    stock_code=stock_code,
    interval=5,  # 1, 5, 15, 30, 60
    count=100,
    adjusted=True  # 수정주가 반영
)
""")

        # 결과를 JSON 파일로 저장
        output_file = project_root / 'tests' / 'manual' / f'minute_chart_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n{GREEN}✅ 테스트 결과가 저장되었습니다: {output_file}{RESET}")

    except Exception as e:
        print(f"{RED}❌ 오류 발생: {e}{RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
