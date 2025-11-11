"""
NXT 시간대 현재가 조회 및 매수 주문 종합 테스트
모든 가능한 접근법을 시도해서 성공하는 방법을 찾아냅니다.

사용법:
    python test_nxt_comprehensive.py

결과:
    - test_results_nxt_YYYYMMDD_HHMMSS.json 파일 생성
    - 성공한 조합이 표시됨
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class NXTComprehensiveTest:
    """NXT 시간대 종합 테스트"""

    def __init__(self):
        from core.rest_client import KiwoomRESTClient
        from api.market import MarketAPI
        from api.order import OrderAPI
        from api.account import AccountAPI
        from utils.trading_date import is_nxt_hours, is_market_hours

        self.client = KiwoomRESTClient()
        self.market_api = MarketAPI(self.client)
        self.order_api = OrderAPI(self.client)
        self.account_api = AccountAPI(self.client)
        self.is_nxt_hours = is_nxt_hours
        self.is_market_hours = is_market_hours

        # 테스트 종목 (삼성전자, SK하이닉스, NAVER)
        self.test_stocks = ['005930', '000660', '035420']

        # 테스트 결과 저장
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'is_nxt_time': is_nxt_hours(),
            'is_market_time': is_market_hours(),
            'price_tests': [],
            'order_tests': [],
            'summary': {}
        }

    # ========================================================================
    # 현재가 조회 테스트 (10가지 접근법)
    # ========================================================================

    def test_price_approach_1_ka10003_basic(self, stock_code: str) -> Dict[str, Any]:
        """접근법 1: ka10003 기본 체결정보"""
        logger.info(f"\n[접근법 1] ka10003 기본 체결정보 - {stock_code}")
        try:
            result = self.market_api.get_stock_price(stock_code, use_fallback=False)
            return {
                'approach': '1_ka10003_basic',
                'stock_code': stock_code,
                'success': result is not None and result.get('current_price', 0) > 0,
                'price': result.get('current_price', 0) if result else 0,
                'source': result.get('source', 'unknown') if result else 'failed',
                'data': result
            }
        except Exception as e:
            logger.error(f"접근법 1 실패: {e}")
            return {
                'approach': '1_ka10003_basic',
                'stock_code': stock_code,
                'success': False,
                'error': str(e)
            }

    def test_price_approach_2_ka10003_with_fallback(self, stock_code: str) -> Dict[str, Any]:
        """접근법 2: ka10003 + 호가 fallback"""
        logger.info(f"\n[접근법 2] ka10003 + 호가 fallback - {stock_code}")
        try:
            result = self.market_api.get_stock_price(stock_code, use_fallback=True)
            return {
                'approach': '2_ka10003_fallback',
                'stock_code': stock_code,
                'success': result is not None and result.get('current_price', 0) > 0,
                'price': result.get('current_price', 0) if result else 0,
                'source': result.get('source', 'unknown') if result else 'failed',
                'data': result
            }
        except Exception as e:
            logger.error(f"접근법 2 실패: {e}")
            return {
                'approach': '2_ka10003_fallback',
                'stock_code': stock_code,
                'success': False,
                'error': str(e)
            }

    def test_price_approach_3_ka10004_orderbook(self, stock_code: str) -> Dict[str, Any]:
        """접근법 3: ka10004 호가정보"""
        logger.info(f"\n[접근법 3] ka10004 호가정보 - {stock_code}")
        try:
            result = self.market_api.get_orderbook(stock_code)
            current_price = int(result.get('현재가', 0)) if result else 0
            return {
                'approach': '3_ka10004_orderbook',
                'stock_code': stock_code,
                'success': current_price > 0,
                'price': current_price,
                'source': 'orderbook',
                'data': result
            }
        except Exception as e:
            logger.error(f"접근법 3 실패: {e}")
            return {
                'approach': '3_ka10004_orderbook',
                'stock_code': stock_code,
                'success': False,
                'error': str(e)
            }

    def test_price_approach_4_ka10087_nxt_single_price(self, stock_code: str) -> Dict[str, Any]:
        """접근법 4: ka10087 시간외단일가"""
        logger.info(f"\n[접근법 4] ka10087 시간외단일가 - {stock_code}")
        try:
            body = {"stk_cd": stock_code}
            response = self.client.request(
                api_id="ka10087",
                body=body,
                path="mrkcond"
            )

            if response and response.get('return_code') == 0:
                # 응답 구조 파악
                logger.info(f"ka10087 응답: {json.dumps(response, ensure_ascii=False, indent=2)}")

                # 현재가 필드 찾기
                price = 0
                for key in ['cur_prc', 'current_price', 'price', 'sgpr', 'dnpr']:
                    if key in response:
                        price = int(str(response[key]).replace('+', '').replace('-', '').replace(',', ''))
                        if price > 0:
                            break

                return {
                    'approach': '4_ka10087_nxt_single',
                    'stock_code': stock_code,
                    'success': price > 0,
                    'price': price,
                    'source': 'nxt_single_price_api',
                    'data': response
                }

            return {
                'approach': '4_ka10087_nxt_single',
                'stock_code': stock_code,
                'success': False,
                'error': response.get('return_msg', 'Unknown error') if response else 'No response'
            }
        except Exception as e:
            logger.error(f"접근법 4 실패: {e}")
            return {
                'approach': '4_ka10087_nxt_single',
                'stock_code': stock_code,
                'success': False,
                'error': str(e)
            }

    def test_price_approach_5_holdings(self, stock_code: str) -> Dict[str, Any]:
        """접근법 5: 보유종목 현재가"""
        logger.info(f"\n[접근법 5] 보유종목 현재가 - {stock_code}")
        try:
            holdings = self.account_api.get_holdings()
            for h in holdings:
                code = str(h.get('stk_cd', '')).strip()
                if code.startswith('A'):
                    code = code[1:]

                if code == stock_code:
                    current_price = int(str(h.get('cur_prc', 0)).replace(',', ''))
                    return {
                        'approach': '5_holdings',
                        'stock_code': stock_code,
                        'success': current_price > 0,
                        'price': current_price,
                        'source': 'holdings',
                        'data': h
                    }

            return {
                'approach': '5_holdings',
                'stock_code': stock_code,
                'success': False,
                'error': 'Stock not in holdings'
            }
        except Exception as e:
            logger.error(f"접근법 5 실패: {e}")
            return {
                'approach': '5_holdings',
                'stock_code': stock_code,
                'success': False,
                'error': str(e)
            }

    def test_price_approach_6_daily_chart(self, stock_code: str) -> Dict[str, Any]:
        """접근법 6: 일봉 차트 최신 데이터"""
        logger.info(f"\n[접근법 6] 일봉 차트 - {stock_code}")
        try:
            result = self.market_api.get_daily_chart(stock_code, period=1)
            if result and len(result) > 0:
                latest = result[0]
                price = int(latest.get('close', 0))
                return {
                    'approach': '6_daily_chart',
                    'stock_code': stock_code,
                    'success': price > 0,
                    'price': price,
                    'source': 'daily_chart',
                    'data': latest,
                    'note': 'This is previous close price, not real-time'
                }

            return {
                'approach': '6_daily_chart',
                'stock_code': stock_code,
                'success': False,
                'error': 'No chart data'
            }
        except Exception as e:
            logger.error(f"접근법 6 실패: {e}")
            return {
                'approach': '6_daily_chart',
                'stock_code': stock_code,
                'success': False,
                'error': str(e)
            }

    def test_price_approach_7_minute_chart(self, stock_code: str) -> Dict[str, Any]:
        """접근법 7: 분봉 차트 최신 데이터"""
        logger.info(f"\n[접근법 7] 분봉 차트 - {stock_code}")
        try:
            result = self.market_api.get_minute_chart(stock_code, tick=1, count=1)
            if result and len(result) > 0:
                latest = result[0]
                price = int(latest.get('close', 0))
                return {
                    'approach': '7_minute_chart',
                    'stock_code': stock_code,
                    'success': price > 0,
                    'price': price,
                    'source': 'minute_chart',
                    'data': latest
                }

            return {
                'approach': '7_minute_chart',
                'stock_code': stock_code,
                'success': False,
                'error': 'No chart data'
            }
        except Exception as e:
            logger.error(f"접근법 7 실패: {e}")
            return {
                'approach': '7_minute_chart',
                'stock_code': stock_code,
                'success': False,
                'error': str(e)
            }

    def test_price_approach_8_raw_api_krx(self, stock_code: str) -> Dict[str, Any]:
        """접근법 8: 직접 API 호출 (dmst_stex_tp=KRX)"""
        logger.info(f"\n[접근법 8] 직접 API (KRX) - {stock_code}")
        try:
            body = {
                "stk_cd": stock_code,
                "dmst_stex_tp": "KRX"
            }
            response = self.client.request(
                api_id="ka10003",
                body=body,
                path="stkinfo"
            )

            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr and len(cntr_infr) > 0:
                    cur_prc = cntr_infr[0].get('cur_prc', '0')
                    price = abs(int(cur_prc.replace('+', '').replace('-', '')))
                    return {
                        'approach': '8_raw_api_krx',
                        'stock_code': stock_code,
                        'success': price > 0,
                        'price': price,
                        'source': 'raw_api_krx',
                        'data': cntr_infr[0]
                    }

            return {
                'approach': '8_raw_api_krx',
                'stock_code': stock_code,
                'success': False,
                'error': response.get('return_msg', 'Unknown') if response else 'No response'
            }
        except Exception as e:
            logger.error(f"접근법 8 실패: {e}")
            return {
                'approach': '8_raw_api_krx',
                'stock_code': stock_code,
                'success': False,
                'error': str(e)
            }

    def test_price_approach_9_raw_api_nxt(self, stock_code: str) -> Dict[str, Any]:
        """접근법 9: 직접 API 호출 (dmst_stex_tp=NXT)"""
        logger.info(f"\n[접근법 9] 직접 API (NXT) - {stock_code}")
        try:
            body = {
                "stk_cd": stock_code,
                "dmst_stex_tp": "NXT"
            }
            response = self.client.request(
                api_id="ka10003",
                body=body,
                path="stkinfo"
            )

            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr and len(cntr_infr) > 0:
                    cur_prc = cntr_infr[0].get('cur_prc', '0')
                    price = abs(int(cur_prc.replace('+', '').replace('-', '')))
                    return {
                        'approach': '9_raw_api_nxt',
                        'stock_code': stock_code,
                        'success': price > 0,
                        'price': price,
                        'source': 'raw_api_nxt',
                        'data': cntr_infr[0]
                    }

            return {
                'approach': '9_raw_api_nxt',
                'stock_code': stock_code,
                'success': False,
                'error': response.get('return_msg', 'Unknown') if response else 'No response'
            }
        except Exception as e:
            logger.error(f"접근법 9 실패: {e}")
            return {
                'approach': '9_raw_api_nxt',
                'stock_code': stock_code,
                'success': False,
                'error': str(e)
            }

    def test_price_approach_10_raw_api_sor(self, stock_code: str) -> Dict[str, Any]:
        """접근법 10: 직접 API 호출 (dmst_stex_tp=SOR)"""
        logger.info(f"\n[접근법 10] 직접 API (SOR) - {stock_code}")
        try:
            body = {
                "stk_cd": stock_code,
                "dmst_stex_tp": "SOR"
            }
            response = self.client.request(
                api_id="ka10003",
                body=body,
                path="stkinfo"
            )

            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr and len(cntr_infr) > 0:
                    cur_prc = cntr_infr[0].get('cur_prc', '0')
                    price = abs(int(cur_prc.replace('+', '').replace('-', '')))
                    return {
                        'approach': '10_raw_api_sor',
                        'stock_code': stock_code,
                        'success': price > 0,
                        'price': price,
                        'source': 'raw_api_sor',
                        'data': cntr_infr[0]
                    }

            return {
                'approach': '10_raw_api_sor',
                'stock_code': stock_code,
                'success': False,
                'error': response.get('return_msg', 'Unknown') if response else 'No response'
            }
        except Exception as e:
            logger.error(f"접근법 10 실패: {e}")
            return {
                'approach': '10_raw_api_sor',
                'stock_code': stock_code,
                'success': False,
                'error': str(e)
            }

    # ========================================================================
    # 매수 주문 테스트 (여러 파라미터 조합)
    # ========================================================================

    def test_order_combination(self, dmst_stex_tp: str, trde_tp: str, stock_code: str = '005930') -> Dict[str, Any]:
        """주문 파라미터 조합 테스트"""
        logger.info(f"\n[주문 테스트] dmst_stex_tp={dmst_stex_tp}, trde_tp={trde_tp}")

        try:
            # 최소 수량으로 테스트 (1주)
            body = {
                "dmst_stex_tp": dmst_stex_tp,
                "stk_cd": stock_code,
                "ord_qty": "1",
                "ord_uv": "50000",  # 임의 가격
                "trde_tp": trde_tp
            }

            response = self.client.request(
                api_id='kt10000',
                body=body,
                path='ordr'
            )

            success = response and response.get('return_code') == 0

            return {
                'combination': f"dmst_stex_tp={dmst_stex_tp}, trde_tp={trde_tp}",
                'stock_code': stock_code,
                'success': success,
                'return_code': response.get('return_code') if response else None,
                'return_msg': response.get('return_msg') if response else 'No response',
                'ord_no': response.get('ord_no') if response else None,
                'full_response': response
            }

        except Exception as e:
            logger.error(f"주문 테스트 실패: {e}")
            return {
                'combination': f"dmst_stex_tp={dmst_stex_tp}, trde_tp={trde_tp}",
                'stock_code': stock_code,
                'success': False,
                'error': str(e)
            }

    # ========================================================================
    # 통합 테스트 실행
    # ========================================================================

    def run_all_price_tests(self):
        """모든 현재가 조회 테스트 실행"""
        logger.info("\n" + "="*80)
        logger.info("🔍 현재가 조회 테스트 시작 (10가지 접근법)")
        logger.info("="*80)

        price_test_methods = [
            self.test_price_approach_1_ka10003_basic,
            self.test_price_approach_2_ka10003_with_fallback,
            self.test_price_approach_3_ka10004_orderbook,
            self.test_price_approach_4_ka10087_nxt_single_price,
            self.test_price_approach_5_holdings,
            self.test_price_approach_6_daily_chart,
            self.test_price_approach_7_minute_chart,
            self.test_price_approach_8_raw_api_krx,
            self.test_price_approach_9_raw_api_nxt,
            self.test_price_approach_10_raw_api_sor,
        ]

        for stock_code in self.test_stocks:
            logger.info(f"\n{'='*60}")
            logger.info(f"종목: {stock_code}")
            logger.info('='*60)

            for test_method in price_test_methods:
                result = test_method(stock_code)
                self.results['price_tests'].append(result)

                if result.get('success'):
                    logger.info(f"✅ {result['approach']}: {result['price']:,}원 (출처: {result['source']})")
                else:
                    logger.warning(f"❌ {result['approach']}: {result.get('error', 'Failed')}")

    def run_all_order_tests(self):
        """모든 주문 파라미터 조합 테스트"""
        logger.info("\n" + "="*80)
        logger.info("📋 주문 파라미터 조합 테스트 시작")
        logger.info("="*80)

        # dmst_stex_tp 조합
        dmst_stex_tp_values = ['KRX', 'NXT', 'SOR']

        # trde_tp 조합 (API 스펙에서 가능한 값들)
        trde_tp_values = ['0', '3', '5', '6', '7', '10', '13', '16', '20', '23', '26']

        # 테스트할 종목 (삼성전자)
        test_stock = '005930'

        for dmst in dmst_stex_tp_values:
            for trde in trde_tp_values:
                result = self.test_order_combination(dmst, trde, test_stock)
                self.results['order_tests'].append(result)

                if result.get('success'):
                    logger.info(f"✅ {result['combination']}: 주문번호 {result['ord_no']}")
                else:
                    logger.warning(f"❌ {result['combination']}: {result.get('return_msg', result.get('error', 'Failed'))}")

    def generate_summary(self):
        """테스트 결과 요약"""
        logger.info("\n" + "="*80)
        logger.info("📊 테스트 결과 요약")
        logger.info("="*80)

        # 현재가 조회 성공률
        price_success = [r for r in self.results['price_tests'] if r.get('success')]
        price_total = len(self.results['price_tests'])

        logger.info(f"\n🔍 현재가 조회: {len(price_success)}/{price_total} 성공")

        if price_success:
            logger.info("\n✅ 성공한 접근법:")
            for r in price_success:
                logger.info(f"   - {r['approach']} ({r['stock_code']}): {r['price']:,}원 via {r['source']}")

        # 주문 성공률
        order_success = [r for r in self.results['order_tests'] if r.get('success')]
        order_total = len(self.results['order_tests'])

        logger.info(f"\n📋 주문 테스트: {len(order_success)}/{order_total} 성공")

        if order_success:
            logger.info("\n✅ 성공한 주문 조합:")
            for r in order_success:
                logger.info(f"   - {r['combination']}: 주문번호 {r['ord_no']}")

        # Summary 저장
        self.results['summary'] = {
            'price_tests': {
                'total': price_total,
                'success': len(price_success),
                'success_rate': f"{len(price_success)/price_total*100:.1f}%" if price_total > 0 else "0%",
                'successful_approaches': [r['approach'] for r in price_success]
            },
            'order_tests': {
                'total': order_total,
                'success': len(order_success),
                'success_rate': f"{len(order_success)/order_total*100:.1f}%" if order_total > 0 else "0%",
                'successful_combinations': [r['combination'] for r in order_success]
            }
        }

    def save_results(self):
        """결과를 JSON 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_nxt_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        logger.info(f"\n💾 결과 저장: {filename}")
        return filename

    def run(self):
        """전체 테스트 실행"""
        logger.info("\n" + "="*80)
        logger.info("🚀 NXT 종합 테스트 시작")
        logger.info("="*80)
        logger.info(f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"NXT 시간: {self.is_nxt_hours()}")
        logger.info(f"정규장 시간: {self.is_market_hours()}")

        # 1. 현재가 조회 테스트
        self.run_all_price_tests()

        # 2. 주문 테스트
        logger.info("\n⚠️  주문 테스트를 실행하시겠습니까?")
        logger.info("   (실제 주문이 발생할 수 있습니다. 최소 금액으로 테스트합니다)")
        user_input = input("   계속하려면 'yes' 입력: ")

        if user_input.lower() == 'yes':
            self.run_all_order_tests()
        else:
            logger.info("주문 테스트를 건너뜁니다.")

        # 3. 요약 생성
        self.generate_summary()

        # 4. 결과 저장
        filename = self.save_results()

        logger.info("\n" + "="*80)
        logger.info("✅ 테스트 완료!")
        logger.info("="*80)
        logger.info(f"결과 파일: {filename}")

        # 성공한 조합 출력
        price_success = [r for r in self.results['price_tests'] if r.get('success')]
        order_success = [r for r in self.results['order_tests'] if r.get('success')]

        if price_success:
            logger.info("\n🎯 권장 현재가 조회 방법:")
            best = price_success[0]
            logger.info(f"   접근법: {best['approach']}")
            logger.info(f"   출처: {best['source']}")

        if order_success:
            logger.info("\n🎯 권장 주문 파라미터:")
            best = order_success[0]
            logger.info(f"   조합: {best['combination']}")


def main():
    """메인 실행"""
    tester = NXTComprehensiveTest()
    tester.run()


if __name__ == "__main__":
    main()
