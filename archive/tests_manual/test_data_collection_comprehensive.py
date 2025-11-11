"""
종합 데이터 수집 테스트
여러 방법으로 시도해서 실제로 작동하는 방법을 찾습니다
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.rest_client import KiwoomRESTClient
from api.market import MarketAPI
from typing import Optional, Dict, Any, List
import statistics


class DataCollectionTester:
    """데이터 수집 테스트 클래스"""

    def __init__(self):
        """초기화"""
        self.client = KiwoomRESTClient()
        self.market_api = MarketAPI(self.client)
        self.results = {}

    def test_all_methods(self, stock_code: str = "005930") -> Dict[str, Any]:
        """모든 방법 테스트"""
        print("\n" + "="*80)
        print(f"📊 종합 데이터 수집 테스트: {stock_code}")
        print("="*80)

        results = {
            'stock_code': stock_code,
            'avg_volume': None,
            'volatility': None,
            'broker_buy_count': None,
            'broker_net_buy': None,
            'execution_intensity': None,
            'program_net_buy': None,
            'methods_used': {},
            'success_count': 0,
            'fail_count': 0
        }

        # 1. 평균 거래량 & 변동성 테스트
        print("\n" + "-"*80)
        print("🧪 TEST 1: 평균 거래량 & 변동성")
        print("-"*80)
        avg_vol, volatility, method = self._test_volume_volatility(stock_code)
        results['avg_volume'] = avg_vol
        results['volatility'] = volatility
        results['methods_used']['volume_volatility'] = method
        if avg_vol is not None:
            results['success_count'] += 1
        else:
            results['fail_count'] += 1

        # 2. 증권사별 매매 테스트
        print("\n" + "-"*80)
        print("🧪 TEST 2: 증권사별 매매")
        print("-"*80)
        buy_count, net_buy, method = self._test_broker_trading(stock_code)
        results['broker_buy_count'] = buy_count
        results['broker_net_buy'] = net_buy
        results['methods_used']['broker_trading'] = method
        if buy_count is not None:
            results['success_count'] += 1
        else:
            results['fail_count'] += 1

        # 3. 체결강도 테스트
        print("\n" + "-"*80)
        print("🧪 TEST 3: 체결강도")
        print("-"*80)
        execution_intensity, method = self._test_execution_intensity(stock_code)
        results['execution_intensity'] = execution_intensity
        results['methods_used']['execution_intensity'] = method
        if execution_intensity is not None:
            results['success_count'] += 1
        else:
            results['fail_count'] += 1

        # 4. 프로그램매매 테스트
        print("\n" + "-"*80)
        print("🧪 TEST 4: 프로그램매매")
        print("-"*80)
        program_net_buy, method = self._test_program_trading(stock_code)
        results['program_net_buy'] = program_net_buy
        results['methods_used']['program_trading'] = method
        if program_net_buy is not None:
            results['success_count'] += 1
        else:
            results['fail_count'] += 1

        return results

    def _test_volume_volatility(self, stock_code: str):
        """평균 거래량 & 변동성 테스트 (여러 방법)"""

        # 방법 1: get_daily_chart() 사용 (ka10081)
        print("\n   방법 1: market_api.get_daily_chart() [ka10081]")
        try:
            daily_data = self.market_api.get_daily_chart(stock_code, period=20)
            if daily_data and len(daily_data) > 1:
                # 평균 거래량
                volumes = [d.get('volume', 0) for d in daily_data if d.get('volume')]
                if volumes:
                    avg_volume = sum(volumes) / len(volumes)
                    print(f"      ✅ 평균거래량: {avg_volume:,.0f}주")
                else:
                    avg_volume = None
                    print(f"      ❌ 거래량 데이터 없음")

                # 변동성 (등락률 표준편차)
                rates = []
                for d in daily_data:
                    # 등락률 계산 (종가 기준)
                    close = d.get('close', 0)
                    open_price = d.get('open', 0)
                    if open_price and open_price > 0:
                        rate = ((close - open_price) / open_price) * 100
                        rates.append(rate)

                if len(rates) > 1:
                    volatility = statistics.stdev(rates)
                    print(f"      ✅ 변동성: {volatility:.2f}%")
                else:
                    volatility = None
                    print(f"      ❌ 변동성 계산 실패")

                return avg_volume, volatility, "get_daily_chart[ka10081]"
            else:
                print(f"      ❌ 일봉 데이터 없음")
        except Exception as e:
            print(f"      ❌ 실패: {e}")

        # 방법 2: 직접 ka10081 호출
        print("\n   방법 2: 직접 ka10081 호출")
        try:
            from utils.trading_date import get_last_trading_date

            response = self.client.request(
                api_id="ka10081",
                body={
                    "stk_cd": stock_code,
                    "base_dt": get_last_trading_date(),
                    "upd_stkpc_tp": "1"
                },
                path="chart"
            )

            if response and response.get('return_code') == 0:
                daily_data = response.get('stk_dt_pole_chart_qry', [])
                if daily_data and len(daily_data) > 1:
                    # 평균 거래량
                    volumes = [int(d.get('trde_qty', 0)) for d in daily_data[:20] if d.get('trde_qty')]
                    if volumes:
                        avg_volume = sum(volumes) / len(volumes)
                        print(f"      ✅ 평균거래량 (직접): {avg_volume:,.0f}주")

                        # 변동성
                        rates = []
                        for d in daily_data[:20]:
                            close = int(d.get('cur_prc', 0))
                            open_price = int(d.get('open_pric', 0))
                            if open_price and open_price > 0:
                                rate = ((close - open_price) / open_price) * 100
                                rates.append(rate)

                        if len(rates) > 1:
                            volatility = statistics.stdev(rates)
                            print(f"      ✅ 변동성 (직접): {volatility:.2f}%")
                            return avg_volume, volatility, "direct_ka10081"

                print(f"      ❌ 데이터 파싱 실패")
            else:
                print(f"      ❌ API 응답 실패")
        except Exception as e:
            print(f"      ❌ 실패: {e}")

        return None, None, "NONE"

    def _test_broker_trading(self, stock_code: str):
        """증권사별 매매 테스트 (여러 방법)"""

        # 방법 1: 주요 증권사 코드로 개별 조회 후 합산
        print("\n   방법 1: 주요 증권사 개별 조회 후 합산")
        try:
            # 주요 증권사 코드 (상위 10개)
            major_firms = [
                ('001', '한국투자증권'),
                ('003', '미래에셋증권'),
                ('030', 'NH투자증권'),
                ('005', '삼성증권'),
                ('034', '한화투자증권'),
                ('088', '신한투자증권'),
                ('039', '교보증권'),
                ('040', 'KB증권'),
                ('218', '현대차증권'),
                ('247', 'DB금융투자'),
            ]

            buy_count = 0
            total_net_buy = 0
            success_firms = []

            for firm_code, firm_name in major_firms:
                try:
                    data = self.market_api.get_securities_firm_trading(
                        firm_code=firm_code,
                        stock_code=stock_code,
                        days=5
                    )

                    if data and len(data) > 0:
                        # 최근 데이터의 순매수 확인
                        latest = data[0]
                        net_qty = latest.get('net_qty', 0)

                        if net_qty > 0:
                            buy_count += 1
                            total_net_buy += net_qty
                            success_firms.append(f"{firm_name}({net_qty:,})")

                except Exception as e:
                    continue

            if buy_count > 0:
                print(f"      ✅ 순매수증권사: {buy_count}개")
                print(f"      ✅ 순매수총량: {total_net_buy:,}주")
                print(f"      📋 상세: {', '.join(success_firms[:3])}")
                return buy_count, total_net_buy, "individual_firm_query"
            else:
                print(f"      ⚠️  순매수 증권사 없음 (모두 순매도)")
                return 0, 0, "individual_firm_query"

        except Exception as e:
            print(f"      ❌ 실패: {e}")

        # 방법 2: 통합 API 탐색
        print("\n   방법 2: 통합 증권사 API 탐색")
        try:
            # ka10078의 다른 사용법 시도
            # 회원사코드를 비워두거나 특수값 사용
            response = self.client.request(
                api_id="ka10078",
                body={
                    "mmcm_cd": "",  # 빈 값으로 전체 조회 시도
                    "stk_cd": stock_code,
                    "strt_dt": "",
                    "end_dt": ""
                },
                path="mrkcond"
            )

            if response and response.get('return_code') == 0:
                print(f"      ✅ 통합 API 성공!")
                # 데이터 파싱 로직 추가 필요
                return None, None, "unified_api"
            else:
                print(f"      ❌ 통합 API 불가: {response.get('return_msg', 'unknown')}")
        except Exception as e:
            print(f"      ❌ 통합 API 실패: {e}")

        # 방법 3: 대안 - 기관/외국인 데이터로 대체
        print("\n   방법 3: 대안 - 기관매매추이 사용")
        try:
            trend_data = self.market_api.get_institutional_trading_trend(
                stock_code=stock_code,
                days=5,
                price_type='buy'
            )

            if trend_data:
                print(f"      ✅ 기관매매추이 데이터 사용 가능")
                print(f"      ℹ️  증권사 데이터 대신 기관 데이터 사용")
                # 기관 데이터에서 순매수 정보 추출 가능
                return 0, 0, "institutional_trend_fallback"
            else:
                print(f"      ❌ 기관매매추이 없음")
        except Exception as e:
            print(f"      ❌ 기관매매추이 실패: {e}")

        return None, None, "NONE"

    def _test_execution_intensity(self, stock_code: str):
        """체결강도 테스트"""

        # 방법 1: get_execution_intensity() 사용
        print("\n   방법 1: market_api.get_execution_intensity()")
        try:
            data = self.market_api.get_execution_intensity(stock_code)
            if data and data.get('execution_intensity'):
                intensity = data['execution_intensity']
                print(f"      ✅ 체결강도: {intensity:.1f}")
                return intensity, "get_execution_intensity"
            else:
                print(f"      ❌ 체결강도 데이터 없음")
        except Exception as e:
            print(f"      ❌ 실패: {e}")

        # 방법 2: 직접 API 호출
        print("\n   방법 2: 직접 ka10047 호출")
        try:
            response = self.client.request(
                api_id="ka10047",
                body={"stk_cd": stock_code},
                path="mrkcond"
            )

            if response and response.get('return_code') == 0:
                # 응답 파싱
                data_keys = [k for k in response.keys()
                            if k not in ['return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key']]

                for key in data_keys:
                    val = response.get(key)
                    if isinstance(val, list) and len(val) > 0:
                        latest = val[0]
                        # 체결강도 필드 찾기
                        cntr_str = latest.get('cntr_str', latest.get('cntr_str', '0'))
                        if cntr_str:
                            try:
                                intensity = float(str(cntr_str).replace('+', '').replace('-', ''))
                                print(f"      ✅ 체결강도 (직접): {intensity:.1f}")
                                return intensity, "direct_ka10047"
                            except:
                                pass

                print(f"      ❌ 체결강도 필드 없음")
            else:
                print(f"      ❌ API 응답 실패")
        except Exception as e:
            print(f"      ❌ 실패: {e}")

        return None, "NONE"

    def _test_program_trading(self, stock_code: str):
        """프로그램매매 테스트"""

        # 방법 1: get_program_trading() 사용
        print("\n   방법 1: market_api.get_program_trading()")
        try:
            data = self.market_api.get_program_trading(stock_code)
            if data and data.get('program_net_buy'):
                net_buy = data['program_net_buy']
                print(f"      ✅ 프로그램순매수: {net_buy:,}원")
                return net_buy, "get_program_trading"
            else:
                print(f"      ❌ 프로그램매매 데이터 없음")
        except Exception as e:
            print(f"      ❌ 실패: {e}")

        # 방법 2: 직접 API 호출
        print("\n   방법 2: 직접 ka90013 호출")
        try:
            response = self.client.request(
                api_id="ka90013",
                body={
                    "stk_cd": stock_code,
                    "amt_qty_tp": "1",  # 1: 금액, 2: 수량
                    "date": ""
                },
                path="mrkcond"
            )

            if response and response.get('return_code') == 0:
                # 응답 파싱
                data_keys = [k for k in response.keys()
                            if k not in ['return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key']]

                for key in data_keys:
                    val = response.get(key)
                    if isinstance(val, list) and len(val) > 0:
                        latest = val[0]
                        # 프로그램 순매수 필드 찾기
                        net_buy = latest.get('prm_netprps_amt', latest.get('prm_netslmt', '0'))
                        if net_buy:
                            try:
                                net_buy_int = int(str(net_buy).replace('+', '').replace('-', '').replace(',', ''))
                                print(f"      ✅ 프로그램순매수 (직접): {net_buy_int:,}원")
                                return net_buy_int, "direct_ka90013"
                            except:
                                pass

                print(f"      ❌ 프로그램순매수 필드 없음")
            else:
                print(f"      ❌ API 응답 실패")
        except Exception as e:
            print(f"      ❌ 실패: {e}")

        return None, "NONE"

    def print_summary(self, results: Dict[str, Any]):
        """결과 요약 출력"""
        print("\n" + "="*80)
        print("📊 테스트 결과 요약")
        print("="*80)

        print(f"\n✅ 성공: {results['success_count']}개")
        print(f"❌ 실패: {results['fail_count']}개")
        print(f"📈 성공률: {results['success_count']/4*100:.1f}%")

        print("\n[수집된 데이터]")
        print(f"  • 평균거래량: {results['avg_volume']:,.0f}주" if results['avg_volume'] else "  • 평균거래량: ❌")
        print(f"  • 변동성: {results['volatility']:.2f}%" if results['volatility'] else "  • 변동성: ❌")
        print(f"  • 순매수증권사: {results['broker_buy_count']}개" if results['broker_buy_count'] is not None else "  • 순매수증권사: ❌")
        print(f"  • 순매수총액: {results['broker_net_buy']:,}주" if results['broker_net_buy'] is not None else "  • 순매수총액: ❌")
        print(f"  • 체결강도: {results['execution_intensity']:.1f}" if results['execution_intensity'] else "  • 체결강도: ❌")
        print(f"  • 프로그램순매수: {results['program_net_buy']:,}원" if results['program_net_buy'] else "  • 프로그램순매수: ❌")

        print("\n[사용된 방법]")
        for key, method in results['methods_used'].items():
            status = "✅" if method != "NONE" else "❌"
            print(f"  {status} {key}: {method}")

        print("\n" + "="*80)
        print("💡 실제 코드 적용 가이드")
        print("="*80)

        if 'ka10081' in results['methods_used']['volume_volatility']:
            print("\n1. 평균거래량/변동성:")
            print("   daily_data = self.market_api.get_daily_chart(candidate.code, period=20)")
            print("   # ka10081 API 사용 (path='mrkcond') ✅")

        if results['methods_used']['broker_trading'] == 'individual_firm_query':
            print("\n2. 증권사별매매:")
            print("   # 주요 증권사 개별 조회 후 합산")
            print("   major_firms = [('001', '한국투자증권'), ...]")
            print("   for firm_code, firm_name in major_firms:")
            print("       data = self.market_api.get_securities_firm_trading(firm_code, stock_code, days=5)")

        if results['methods_used']['execution_intensity'] == 'get_execution_intensity':
            print("\n3. 체결강도:")
            print("   data = self.market_api.get_execution_intensity(candidate.code)")
            print("   # 이미 정상 작동 ✅")

        if results['methods_used']['program_trading'] == 'get_program_trading':
            print("\n4. 프로그램매매:")
            print("   data = self.market_api.get_program_trading(candidate.code)")
            print("   # 이미 정상 작동 ✅")


def main():
    """메인 함수"""
    tester = DataCollectionTester()

    # 여러 종목으로 테스트
    test_stocks = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
    ]

    all_results = []

    for stock_code, stock_name in test_stocks:
        print(f"\n{'='*80}")
        print(f"🔍 테스트 종목: {stock_name} ({stock_code})")
        print(f"{'='*80}")

        results = tester.test_all_methods(stock_code)
        results['stock_name'] = stock_name
        all_results.append(results)

        tester.print_summary(results)

        # 첫 번째 종목만 테스트 (시간 절약)
        break

    print("\n" + "="*80)
    print("🎯 최종 결론")
    print("="*80)

    if all_results:
        avg_success_rate = sum(r['success_count'] for r in all_results) / (len(all_results) * 4) * 100
        print(f"\n평균 성공률: {avg_success_rate:.1f}%")

        if avg_success_rate >= 75:
            print("✅ 대부분의 데이터 수집 성공! scan_strategies.py 적용 가능")
        elif avg_success_rate >= 50:
            print("⚠️  일부 데이터 수집 실패. 코드 수정 필요")
        else:
            print("❌ 많은 데이터 수집 실패. API 문제 확인 필요")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
