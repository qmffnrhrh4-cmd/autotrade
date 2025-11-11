"""
NXT 주문 최종 테스트 (가격 없이)

발견 사항:
- trde_tp=81 (장마감후시간외)가 정답!
- 하지만 ord_uv="" (빈 문자열) 필요
- "시간외종가 주문시에는 단가를 입력하지 않습니다" 오류 해결

사용법:
    python test_nxt_orders_final.py
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class NXTOrderFinalTest:
    """NXT 주문 최종 테스트 (가격 파라미터 수정)"""

    def __init__(self):
        from core.rest_client import KiwoomRESTClient
        from utils.trading_date import is_nxt_hours, is_market_hours

        self.client = KiwoomRESTClient()
        self.is_nxt = is_nxt_hours()
        self.is_market = is_market_hours()

        now = datetime.now()
        self.hour = now.hour
        self.minute = now.minute

        self.results = {
            'timestamp': datetime.now().isoformat(),
            'is_nxt_time': self.is_nxt,
            'is_market_time': self.is_market,
            'tests': [],
            'successful_combinations': []
        }

    def get_trading_period(self) -> str:
        """현재 거래 시간대"""
        if self.hour == 8:
            return '프리마켓'
        elif 9 <= self.hour < 15 or (self.hour == 15 and self.minute <= 30):
            return '정규장'
        elif (self.hour == 15 and self.minute >= 30) or (16 <= self.hour < 20):
            return '애프터마켓'
        else:
            return '장외시간'

    def test_order(self, dmst_stex_tp: str, trde_tp: str, ord_uv: str, desc: str,
                   stock_code: str = '005930') -> Dict[str, Any]:
        """주문 테스트"""

        logger.info(f"\n{'='*70}")
        logger.info(f"🧪 {desc}")
        logger.info(f"   dmst_stex_tp={dmst_stex_tp}, trde_tp={trde_tp}")
        logger.info(f"   종목: {stock_code}, 가격: {ord_uv if ord_uv else '시간외종가(가격 미지정)'}")
        logger.info('='*70)

        try:
            body = {
                "dmst_stex_tp": dmst_stex_tp,
                "stk_cd": stock_code,
                "ord_qty": "1",
                "ord_uv": ord_uv,  # 시간외종가는 빈 문자열
                "trde_tp": trde_tp
            }

            logger.info(f"   📋 요청: {json.dumps(body, ensure_ascii=False)}")

            response = self.client.request(
                api_id='kt10000',
                body=body,
                path='ordr'
            )

            success = response and response.get('return_code') == 0
            return_code = response.get('return_code') if response else None
            return_msg = response.get('return_msg') if response else 'No response'
            ord_no = response.get('ord_no') if response else None

            result = {
                'description': desc,
                'dmst_stex_tp': dmst_stex_tp,
                'trde_tp': trde_tp,
                'ord_uv': ord_uv,
                'stock_code': stock_code,
                'success': success,
                'return_code': return_code,
                'return_msg': return_msg,
                'ord_no': ord_no
            }

            if success:
                logger.info(f"✅ 성공! 주문번호: {ord_no}")
                logger.info(f"   응답: {return_msg}")
                self.results['successful_combinations'].append(result)
            else:
                logger.warning(f"❌ 실패: [{return_code}] {return_msg}")

            return result

        except Exception as e:
            logger.error(f"❌ 오류: {e}")
            return {
                'description': desc,
                'success': False,
                'error': str(e)
            }

    def run_all_tests(self):
        """모든 테스트 실행"""

        period = self.get_trading_period()

        logger.info("\n" + "="*80)
        logger.info("🎯 NXT 주문 최종 테스트 (가격 파라미터 수정)")
        logger.info("="*80)
        logger.info(f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"거래 시간대: {period}")
        logger.info(f"NXT 시간: {self.is_nxt}")

        # 테스트 케이스 정의
        test_cases = []

        if period == '프리마켓':
            logger.info("\n📌 프리마켓 테스트 (08:00-09:00)")
            test_cases = [
                ('KRX', '61', '', '✅ KRX + 장시작전시간외(61) + 가격없음'),
                ('NXT', '61', '', '✅ NXT + 장시작전시간외(61) + 가격없음'),
                ('KRX', '61', '50000', '🧪 KRX + 장시작전시간외(61) + 가격있음'),
            ]

        elif period == '애프터마켓':
            logger.info("\n📌 애프터마켓 테스트 (15:30-20:00)")
            test_cases = [
                # 시간외종가 (가격 없이)
                ('KRX', '81', '', '✅ KRX + 장마감후시간외(81) + 가격없음'),
                ('NXT', '81', '', '✅ NXT + 장마감후시간외(81) + 가격없음'),

                # 실험: 가격 지정
                ('KRX', '81', '50000', '🧪 KRX + 장마감후시간외(81) + 가격있음 (실패 예상)'),
                ('NXT', '81', '50000', '🧪 NXT + 장마감후시간외(81) + 가격있음 (실패 예상)'),
            ]

        else:
            logger.warning("⚠️  장외 시간입니다.")
            test_cases = [
                ('KRX', '81', '', '✅ KRX + 장마감후시간외(81) + 가격없음'),
                ('NXT', '81', '', '✅ NXT + 장마감후시간외(81) + 가격없음'),
            ]

        # 확인
        logger.info("\n" + "="*80)
        logger.info("⚠️  실제 주문이 발생합니다!")
        logger.info("="*80)
        logger.info(f"테스트 수: {len(test_cases)}개")
        logger.info(f"종목: 삼성전자 (005930)")
        logger.info("주의: 시간외종가 주문은 장 마감 후 종가로 체결됩니다\n")

        user_input = input("계속하시겠습니까? (yes/no): ")
        if user_input.lower() != 'yes':
            logger.info("테스트를 취소합니다.")
            return

        # 테스트 실행
        for dmst, trde, price, desc in test_cases:
            result = self.test_order(dmst, trde, price, desc)
            self.results['tests'].append(result)

        # 결과 요약
        self.print_summary()
        self.save_results()

    def print_summary(self):
        """결과 요약"""
        logger.info("\n" + "="*80)
        logger.info("📊 최종 테스트 결과")
        logger.info("="*80)

        tests = self.results['tests']
        success_tests = [t for t in tests if t.get('success')]

        logger.info(f"\n총 {len(tests)}개 테스트 중 {len(success_tests)}개 성공")

        if success_tests:
            logger.info("\n" + "🎉"*20)
            logger.info("✅ 성공한 조합 발견!")
            logger.info("🎉"*20)

            for test in success_tests:
                logger.info(f"\n   🎯 {test['description']}")
                logger.info(f"      dmst_stex_tp = '{test['dmst_stex_tp']}'")
                logger.info(f"      trde_tp = '{test['trde_tp']}'")
                logger.info(f"      ord_uv = '{test['ord_uv']}'")
                logger.info(f"      주문번호: {test['ord_no']}")

            # 권장 코드
            best = success_tests[0]
            logger.info("\n" + "="*80)
            logger.info("💡 즉시 적용 가능한 코드 (api/order.py)")
            logger.info("="*80)

            period = self.get_trading_period()

            logger.info(f"""
def buy_stock_nxt(self, stock_code: str, quantity: int) -> Optional[str]:
    \"\"\"NXT {period} 매수 주문\"\"\"
    body = {{
        "dmst_stex_tp": "{best['dmst_stex_tp']}",
        "stk_cd": stock_code,
        "ord_qty": str(quantity),
        "ord_uv": "{best['ord_uv']}",  # 시간외종가는 빈 문자열!
        "trde_tp": "{best['trde_tp']}"
    }}

    response = self.client.request(
        api_id='kt10000',
        body=body,
        path='ordr'
    )

    return response.get('ord_no') if response.get('return_code') == 0 else None
            """)

        else:
            logger.warning("\n❌ 성공한 조합이 없습니다.")

    def save_results(self):
        """결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_nxt_FINAL_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        logger.info(f"\n💾 결과 저장: {filename}")


def main():
    """메인"""
    print("\n" + "="*80)
    print("🎯 NXT 주문 최종 테스트")
    print("="*80)
    print("\n발견 사항:")
    print("   ✅ trde_tp=81 (장마감후시간외) 코드가 정답!")
    print("   ✅ 하지만 ord_uv=\"\" (가격 입력 안 함)")
    print("   ✅ 시간외종가 주문 = 장 마감 후 종가로 주문")
    print("\n이전 오류:")
    print("   ❌ '시간외종가 주문시에는 단가를 입력하지 않습니다'")
    print("   → ord_uv에 가격을 입력해서 실패")
    print("\n해결:")
    print("   ✅ ord_uv=\"\" (빈 문자열)")
    print("="*80 + "\n")

    tester = NXTOrderFinalTest()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
