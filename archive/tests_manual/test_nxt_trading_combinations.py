"""
NXT 시간외 거래 매수/매도 조합 테스트
다양한 파라미터 조합을 시도해서 정답을 찾습니다.

⚠️ 주의: 실제 주문이 체결됩니다!
- 소액(1주)으로 테스트합니다
- 테스트 후 즉시 정리합니다
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import time
from datetime import datetime
from core.rest_client import KiwoomRESTClient
from api.market import MarketAPI
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TradingCombinationTester:
    """다양한 거래 파라미터 조합을 테스트하는 클래스"""

    def __init__(self):
        self.client = KiwoomRESTClient()
        self.market_api = MarketAPI(self.client)
        self.results = []

        # 테스트 종목 (삼성전자)
        self.test_stock = "005930"
        self.test_name = "삼성전자"

        logger.info(f"🔧 초기화 완료")
        logger.info(f"   서버: {self.client.base_url}")
        logger.info(f"   테스트 종목: {self.test_name} ({self.test_stock})")

    def get_current_price(self):
        """현재가 조회"""
        try:
            quote = self.market_api.get_stock_price(self.test_stock)
            if quote and quote.get('current_price'):
                return int(quote['current_price'])
        except Exception as e:
            logger.error(f"현재가 조회 실패: {e}")
        return None

    def test_order(self, test_case: dict):
        """
        주문 테스트

        Args:
            test_case: {
                'name': '테스트 케이스 이름',
                'dmst_stex_tp': 'KRX' or 'NXT' or 'SOR',
                'trde_tp': '0' or '3' or '61' or '62' or '81',
                'ord_uv': '' or 가격,
                'description': '설명'
            }
        """
        case_name = test_case['name']
        dmst_stex_tp = test_case['dmst_stex_tp']
        trde_tp = test_case['trde_tp']
        ord_uv = test_case['ord_uv']
        description = test_case.get('description', '')

        logger.info(f"\n{'='*80}")
        logger.info(f"🧪 테스트: {case_name}")
        logger.info(f"   설명: {description}")
        logger.info(f"   파라미터: dmst_stex_tp={dmst_stex_tp}, trde_tp={trde_tp}, ord_uv={ord_uv}")
        logger.info(f"{'='*80}")

        # 매수 주문 시도
        body_params = {
            "dmst_stex_tp": dmst_stex_tp,
            "stk_cd": self.test_stock,
            "ord_qty": "1",
            "ord_uv": str(ord_uv),
            "trde_tp": trde_tp
        }

        try:
            result = self.client.request(
                api_id='kt10000',
                body=body_params,
                path='/api/dostk/ordr'
            )

            success = result and result.get('return_code') == 0

            test_result = {
                'case': case_name,
                'dmst_stex_tp': dmst_stex_tp,
                'trde_tp': trde_tp,
                'ord_uv': ord_uv,
                'success': success,
                'order_no': result.get('ord_no') if success else None,
                'error': result.get('return_msg') if not success else None,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }

            if success:
                logger.info(f"✅ 성공! 주문번호: {result.get('ord_no')}")

                # 성공한 경우 즉시 취소 (청소)
                time.sleep(0.5)
                self.cancel_order(result.get('ord_no'), dmst_stex_tp)
            else:
                logger.error(f"❌ 실패: {result.get('return_msg')}")

            self.results.append(test_result)
            return success

        except Exception as e:
            logger.error(f"❌ 예외 발생: {e}")
            self.results.append({
                'case': case_name,
                'dmst_stex_tp': dmst_stex_tp,
                'trde_tp': trde_tp,
                'ord_uv': ord_uv,
                'success': False,
                'order_no': None,
                'error': str(e),
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            return False

    def cancel_order(self, order_no: str, dmst_stex_tp: str):
        """주문 취소"""
        if not order_no:
            return

        try:
            logger.info(f"🗑️  주문 취소 중: {order_no}")
            cancel_params = {
                "dmst_stex_tp": dmst_stex_tp,
                "orig_ord_no": order_no,
                "stk_cd": self.test_stock,
                "cncl_qty": "0"  # 전량 취소
            }

            result = self.client.request(
                api_id='kt10003',
                body=cancel_params,
                path='/api/dostk/ordr'
            )

            if result and result.get('return_code') == 0:
                logger.info(f"✅ 취소 성공")
            else:
                logger.warning(f"⚠️ 취소 실패: {result.get('return_msg') if result else '응답 없음'}")

        except Exception as e:
            logger.error(f"취소 중 오류: {e}")

    def print_summary(self):
        """테스트 결과 요약 출력"""
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 테스트 결과 요약")
        logger.info(f"{'='*80}")

        success_count = sum(1 for r in self.results if r['success'])
        total_count = len(self.results)

        logger.info(f"\n총 {total_count}개 케이스 테스트")
        logger.info(f"성공: {success_count}개 ✅")
        logger.info(f"실패: {total_count - success_count}개 ❌")

        # 성공한 케이스들
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ 성공한 조합:")
        logger.info(f"{'='*80}")
        success_cases = [r for r in self.results if r['success']]
        if success_cases:
            for r in success_cases:
                logger.info(f"  🎯 {r['case']}")
                logger.info(f"     dmst_stex_tp={r['dmst_stex_tp']}, trde_tp={r['trde_tp']}, ord_uv={r['ord_uv']}")
                logger.info(f"     주문번호: {r['order_no']}")
        else:
            logger.info(f"  없음")

        # 실패한 케이스들
        logger.info(f"\n{'='*80}")
        logger.info(f"❌ 실패한 조합:")
        logger.info(f"{'='*80}")
        failed_cases = [r for r in self.results if not r['success']]
        for r in failed_cases:
            logger.info(f"  ❌ {r['case']}")
            logger.info(f"     dmst_stex_tp={r['dmst_stex_tp']}, trde_tp={r['trde_tp']}, ord_uv={r['ord_uv']}")
            logger.info(f"     오류: {r['error']}")

        # 결론
        logger.info(f"\n{'='*80}")
        logger.info(f"💡 결론")
        logger.info(f"{'='*80}")
        if success_cases:
            logger.info(f"✅ 성공한 조합을 사용하세요!")
            logger.info(f"   권장 설정: dmst_stex_tp={success_cases[0]['dmst_stex_tp']}, "
                       f"trde_tp={success_cases[0]['trde_tp']}, "
                       f"ord_uv={success_cases[0]['ord_uv']}")
        else:
            logger.info(f"❌ 모든 조합이 실패했습니다.")
            logger.info(f"   서버 확인: {self.client.base_url}")
            logger.info(f"   시간 확인: 시간외 거래 시간대인지 확인하세요")


def main():
    """메인 테스트 실행"""
    logger.info(f"\n{'='*80}")
    logger.info(f"🚀 NXT 시간외 거래 조합 테스트 시작")
    logger.info(f"{'='*80}")
    logger.info(f"⚠️  주의: 실제 주문이 체결됩니다!")
    logger.info(f"⚠️  소액(1주) 테스트 후 즉시 취소합니다.")
    logger.info(f"{'='*80}\n")

    # 현재 시간 확인
    now = datetime.now()
    current_hour = now.hour
    logger.info(f"⏰ 현재 시간: {now.strftime('%H:%M:%S')}")

    if current_hour < 8 or current_hour >= 20:
        logger.warning(f"⚠️  현재 시간은 거래 불가 시간대입니다 (20:00-08:00)")
        logger.warning(f"⚠️  테스트는 진행하지만 모두 실패할 가능성이 높습니다.")
    elif 16 <= current_hour < 20:
        logger.info(f"✅ 시간외 단일가 거래 시간대 (16:00-20:00)")
    elif 15 <= current_hour < 16:
        if now.minute >= 40:
            logger.info(f"✅ 장후 시간외 종가 거래 시간대 (15:40-16:00)")
        else:
            logger.info(f"⏸️  거래 대기 시간대 (15:30-15:40)")
    elif 9 <= current_hour < 15 or (current_hour == 15 and now.minute < 30):
        logger.info(f"✅ 정규장 거래 시간대 (09:00-15:30)")
    elif 8 <= current_hour < 9:
        logger.info(f"✅ 장시작전 시간외 거래 시간대 (08:00-09:00)")

    # 테스터 초기화
    tester = TradingCombinationTester()

    # 현재가 조회
    current_price = tester.get_current_price()
    if not current_price:
        logger.error(f"현재가를 조회할 수 없습니다. 테스트를 중단합니다.")
        return

    logger.info(f"📊 현재가: {current_price:,}원\n")

    # 테스트 케이스 정의
    test_cases = [
        # 1. 시간외 단일가 거래 (16:00-20:00 시간대)
        {
            'name': 'NXT + 시간외단일가(62) + 빈가격',
            'dmst_stex_tp': 'NXT',
            'trde_tp': '62',
            'ord_uv': '',
            'description': '키움 문서 기준 시간외 단일가 (가장 가능성 높음)'
        },
        {
            'name': 'NXT + 시간외단일가(62) + 가격지정',
            'dmst_stex_tp': 'NXT',
            'trde_tp': '62',
            'ord_uv': current_price,
            'description': '시간외 단일가 + 가격 지정'
        },
        {
            'name': 'KRX + 시간외단일가(62) + 빈가격',
            'dmst_stex_tp': 'KRX',
            'trde_tp': '62',
            'ord_uv': '',
            'description': 'KRX 거래소 + 시간외 단일가'
        },

        # 2. 장마감후 시간외 (15:40-16:00 시간대)
        {
            'name': 'NXT + 장마감후시간외(81) + 빈가격',
            'dmst_stex_tp': 'NXT',
            'trde_tp': '81',
            'ord_uv': '',
            'description': '장마감후 시간외 종가 거래'
        },
        {
            'name': 'KRX + 장마감후시간외(81) + 빈가격',
            'dmst_stex_tp': 'KRX',
            'trde_tp': '81',
            'ord_uv': '',
            'description': 'KRX + 장마감후 시간외'
        },

        # 3. 장시작전 시간외 (08:00-09:00 시간대)
        {
            'name': 'NXT + 장시작전시간외(61) + 빈가격',
            'dmst_stex_tp': 'NXT',
            'trde_tp': '61',
            'ord_uv': '',
            'description': '장시작전 시간외 거래'
        },
        {
            'name': 'KRX + 장시작전시간외(61) + 빈가격',
            'dmst_stex_tp': 'KRX',
            'trde_tp': '61',
            'ord_uv': '',
            'description': 'KRX + 장시작전 시간외'
        },

        # 4. 정규장 거래 (09:00-15:30)
        {
            'name': 'KRX + 보통지정가(0) + 가격지정',
            'dmst_stex_tp': 'KRX',
            'trde_tp': '0',
            'ord_uv': current_price,
            'description': '정규장 보통 지정가 거래'
        },
        {
            'name': 'KRX + 시장가(3) + 빈가격',
            'dmst_stex_tp': 'KRX',
            'trde_tp': '3',
            'ord_uv': '',
            'description': '정규장 시장가 거래'
        },

        # 5. 기타 조합들
        {
            'name': 'SOR + 시간외단일가(62) + 빈가격',
            'dmst_stex_tp': 'SOR',
            'trde_tp': '62',
            'ord_uv': '',
            'description': 'SOR 거래소 + 시간외 단일가'
        },
        {
            'name': 'NXT + 보통지정가(0) + 가격지정',
            'dmst_stex_tp': 'NXT',
            'trde_tp': '0',
            'ord_uv': current_price,
            'description': 'NXT + 보통 지정가 (잘못된 조합일 가능성)'
        },
    ]

    # 사용자 확인
    logger.info(f"📋 총 {len(test_cases)}개의 조합을 테스트합니다.")
    response = input(f"\n계속하시겠습니까? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        logger.info(f"테스트를 취소했습니다.")
        return

    # 각 테스트 케이스 실행
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n[{i}/{len(test_cases)}]")
        tester.test_order(test_case)

        # API 호출 간격 (0.5초)
        if i < len(test_cases):
            time.sleep(0.5)

    # 결과 요약
    tester.print_summary()

    logger.info(f"\n{'='*80}")
    logger.info(f"✅ 모든 테스트 완료")
    logger.info(f"{'='*80}\n")


if __name__ == "__main__":
    main()
