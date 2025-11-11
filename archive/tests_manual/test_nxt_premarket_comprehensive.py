#!/usr/bin/env python3
"""
NXT 프리마켓(08:00-09:00) 현재가 조회 종합 테스트

오전 8시~9시 사이에 실행하여 다양한 조건에서 NXT 현재가 조회 테스트

실행 방법:
    python tests/manual/test_nxt_premarket_comprehensive.py

테스트 항목:
    1. 종목코드 형식 변형 (기본, _NX, _AL 등)
    2. API 파라미터 조합 (dmst_stex_tp 등)
    3. 다양한 API 사용 (ka10003, ka10004, ka10087 등)
    4. Fallback 전략
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.rest_client import KiwoomRESTClient
from utils.trading_date import is_nxt_hours, is_market_hours

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class NXTPremarketTester:
    """NXT 프리마켓 현재가 조회 종합 테스트"""

    def __init__(self):
        # KiwoomRESTClient는 싱글톤 패턴이므로 직접 생성자 호출
        self.client = KiwoomRESTClient()
        self.results = []
        self.test_stocks = [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "088340",  # 사용자가 테스트한 종목
        ]

    def log_test_start(self, test_name: str, description: str):
        """테스트 시작 로깅"""
        logger.info(f"\n{'='*80}")
        logger.info(f"테스트: {test_name}")
        logger.info(f"설명: {description}")
        logger.info(f"{'='*80}")

    def log_test_result(self, test_name: str, success: bool, data: Any, error: str = ""):
        """테스트 결과 로깅 및 저장"""
        status = "✅ 성공" if success else "❌ 실패"
        logger.info(f"{status} - {test_name}")
        if success and data:
            logger.info(f"  현재가: {data.get('current_price', 'N/A'):,}원")
            logger.info(f"  출처: {data.get('source', 'N/A')}")
        elif error:
            logger.error(f"  에러: {error}")

        self.results.append({
            "test_name": test_name,
            "success": success,
            "data": data,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    # ========================================
    # 카테고리 1: 종목코드 형식 변형
    # ========================================

    def test_stock_code_basic(self, stock_code: str) -> Dict[str, Any]:
        """테스트 1: 기본 종목코드 (예: 005930)"""
        self.log_test_start(
            "1. 기본 종목코드",
            f"종목코드: {stock_code} (변형 없음)"
        )
        try:
            response = self.client.request(
                api_id="ka10003",
                body={"stk_cd": stock_code},
                path="stkinfo"
            )
            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr:
                    price = abs(int(cntr_infr[0].get('cur_prc', '0').replace('+', '').replace('-', '')))
                    data = {"current_price": price, "source": "basic_code"}
                    self.log_test_result("기본 종목코드", True, data)
                    return data
            self.log_test_result("기본 종목코드", False, None, "체결정보 없음")
            return None
        except Exception as e:
            self.log_test_result("기본 종목코드", False, None, str(e))
            return None

    def test_stock_code_nx(self, stock_code: str) -> Dict[str, Any]:
        """테스트 2: NXT 종목코드 (예: 005930_NX)"""
        self.log_test_start(
            "2. NXT 종목코드 (_NX 접미사)",
            f"종목코드: {stock_code}_NX"
        )
        try:
            response = self.client.request(
                api_id="ka10003",
                body={"stk_cd": f"{stock_code}_NX"},
                path="stkinfo"
            )
            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr:
                    price = abs(int(cntr_infr[0].get('cur_prc', '0').replace('+', '').replace('-', '')))
                    data = {"current_price": price, "source": "nx_code"}
                    self.log_test_result("NXT 종목코드", True, data)
                    return data
            self.log_test_result("NXT 종목코드", False, None, "체결정보 없음")
            return None
        except Exception as e:
            self.log_test_result("NXT 종목코드", False, None, str(e))
            return None

    def test_stock_code_al(self, stock_code: str) -> Dict[str, Any]:
        """테스트 3: SOR 종목코드 (예: 005930_AL)"""
        self.log_test_start(
            "3. SOR 종목코드 (_AL 접미사)",
            f"종목코드: {stock_code}_AL"
        )
        try:
            response = self.client.request(
                api_id="ka10003",
                body={"stk_cd": f"{stock_code}_AL"},
                path="stkinfo"
            )
            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr:
                    price = abs(int(cntr_infr[0].get('cur_prc', '0').replace('+', '').replace('-', '')))
                    data = {"current_price": price, "source": "al_code"}
                    self.log_test_result("SOR 종목코드", True, data)
                    return data
            self.log_test_result("SOR 종목코드", False, None, "체결정보 없음")
            return None
        except Exception as e:
            self.log_test_result("SOR 종목코드", False, None, str(e))
            return None

    # ========================================
    # 카테고리 2: dmst_stex_tp 파라미터 조합
    # ========================================

    def test_dmst_stex_tp_krx(self, stock_code: str) -> Dict[str, Any]:
        """테스트 4: dmst_stex_tp=KRX"""
        self.log_test_start(
            "4. dmst_stex_tp=KRX",
            f"종목코드: {stock_code}, 파라미터: dmst_stex_tp=KRX"
        )
        try:
            response = self.client.request(
                api_id="ka10003",
                body={"stk_cd": stock_code, "dmst_stex_tp": "KRX"},
                path="stkinfo"
            )
            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr:
                    price = abs(int(cntr_infr[0].get('cur_prc', '0').replace('+', '').replace('-', '')))
                    data = {"current_price": price, "source": "dmst_krx"}
                    self.log_test_result("dmst_stex_tp=KRX", True, data)
                    return data
            self.log_test_result("dmst_stex_tp=KRX", False, None, "체결정보 없음")
            return None
        except Exception as e:
            self.log_test_result("dmst_stex_tp=KRX", False, None, str(e))
            return None

    def test_dmst_stex_tp_nxt(self, stock_code: str) -> Dict[str, Any]:
        """테스트 5: dmst_stex_tp=NXT"""
        self.log_test_start(
            "5. dmst_stex_tp=NXT",
            f"종목코드: {stock_code}, 파라미터: dmst_stex_tp=NXT"
        )
        try:
            response = self.client.request(
                api_id="ka10003",
                body={"stk_cd": stock_code, "dmst_stex_tp": "NXT"},
                path="stkinfo"
            )
            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr:
                    price = abs(int(cntr_infr[0].get('cur_prc', '0').replace('+', '').replace('-', '')))
                    data = {"current_price": price, "source": "dmst_nxt"}
                    self.log_test_result("dmst_stex_tp=NXT", True, data)
                    return data
            self.log_test_result("dmst_stex_tp=NXT", False, None, "체결정보 없음")
            return None
        except Exception as e:
            self.log_test_result("dmst_stex_tp=NXT", False, None, str(e))
            return None

    def test_dmst_stex_tp_sor(self, stock_code: str) -> Dict[str, Any]:
        """테스트 6: dmst_stex_tp=SOR"""
        self.log_test_start(
            "6. dmst_stex_tp=SOR",
            f"종목코드: {stock_code}, 파라미터: dmst_stex_tp=SOR"
        )
        try:
            response = self.client.request(
                api_id="ka10003",
                body={"stk_cd": stock_code, "dmst_stex_tp": "SOR"},
                path="stkinfo"
            )
            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr:
                    price = abs(int(cntr_infr[0].get('cur_prc', '0').replace('+', '').replace('-', '')))
                    data = {"current_price": price, "source": "dmst_sor"}
                    self.log_test_result("dmst_stex_tp=SOR", True, data)
                    return data
            self.log_test_result("dmst_stex_tp=SOR", False, None, "체결정보 없음")
            return None
        except Exception as e:
            self.log_test_result("dmst_stex_tp=SOR", False, None, str(e))
            return None

    # ========================================
    # 카테고리 3: 종목코드 + 파라미터 조합
    # ========================================

    def test_nx_code_with_nxt_param(self, stock_code: str) -> Dict[str, Any]:
        """테스트 7: _NX 종목코드 + dmst_stex_tp=NXT"""
        self.log_test_start(
            "7. _NX 코드 + dmst_stex_tp=NXT",
            f"종목코드: {stock_code}_NX, 파라미터: dmst_stex_tp=NXT"
        )
        try:
            response = self.client.request(
                api_id="ka10003",
                body={"stk_cd": f"{stock_code}_NX", "dmst_stex_tp": "NXT"},
                path="stkinfo"
            )
            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr:
                    price = abs(int(cntr_infr[0].get('cur_prc', '0').replace('+', '').replace('-', '')))
                    data = {"current_price": price, "source": "nx_code_nxt_param"}
                    self.log_test_result("_NX+dmst_stex_tp=NXT", True, data)
                    return data
            self.log_test_result("_NX+dmst_stex_tp=NXT", False, None, "체결정보 없음")
            return None
        except Exception as e:
            self.log_test_result("_NX+dmst_stex_tp=NXT", False, None, str(e))
            return None

    def test_nx_code_with_krx_param(self, stock_code: str) -> Dict[str, Any]:
        """테스트 8: _NX 종목코드 + dmst_stex_tp=KRX"""
        self.log_test_start(
            "8. _NX 코드 + dmst_stex_tp=KRX",
            f"종목코드: {stock_code}_NX, 파라미터: dmst_stex_tp=KRX"
        )
        try:
            response = self.client.request(
                api_id="ka10003",
                body={"stk_cd": f"{stock_code}_NX", "dmst_stex_tp": "KRX"},
                path="stkinfo"
            )
            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr:
                    price = abs(int(cntr_infr[0].get('cur_prc', '0').replace('+', '').replace('-', '')))
                    data = {"current_price": price, "source": "nx_code_krx_param"}
                    self.log_test_result("_NX+dmst_stex_tp=KRX", True, data)
                    return data
            self.log_test_result("_NX+dmst_stex_tp=KRX", False, None, "체결정보 없음")
            return None
        except Exception as e:
            self.log_test_result("_NX+dmst_stex_tp=KRX", False, None, str(e))
            return None

    def test_al_code_with_sor_param(self, stock_code: str) -> Dict[str, Any]:
        """테스트 9: _AL 종목코드 + dmst_stex_tp=SOR"""
        self.log_test_start(
            "9. _AL 코드 + dmst_stex_tp=SOR",
            f"종목코드: {stock_code}_AL, 파라미터: dmst_stex_tp=SOR"
        )
        try:
            response = self.client.request(
                api_id="ka10003",
                body={"stk_cd": f"{stock_code}_AL", "dmst_stex_tp": "SOR"},
                path="stkinfo"
            )
            if response and response.get('return_code') == 0:
                cntr_infr = response.get('cntr_infr', [])
                if cntr_infr:
                    price = abs(int(cntr_infr[0].get('cur_prc', '0').replace('+', '').replace('-', '')))
                    data = {"current_price": price, "source": "al_code_sor_param"}
                    self.log_test_result("_AL+dmst_stex_tp=SOR", True, data)
                    return data
            self.log_test_result("_AL+dmst_stex_tp=SOR", False, None, "체결정보 없음")
            return None
        except Exception as e:
            self.log_test_result("_AL+dmst_stex_tp=SOR", False, None, str(e))
            return None

    # ========================================
    # 카테고리 4: 다른 API 사용
    # ========================================

    def test_orderbook_api(self, stock_code: str) -> Dict[str, Any]:
        """테스트 10: 호가 API (ka10004)"""
        self.log_test_start(
            "10. 호가 API (ka10004)",
            f"종목코드: {stock_code}"
        )
        try:
            response = self.client.request(
                api_id="ka10004",
                body={"stk_cd": stock_code},
                path="mrkcond"
            )
            if response and response.get('return_code') == 0:
                sell_price = response.get('sel_fpr_bid', '0').replace('+', '').replace('-', '')
                buy_price = response.get('buy_fpr_bid', '0').replace('+', '').replace('-', '')
                if sell_price and sell_price != '0':
                    price = abs(int(sell_price))
                    data = {"current_price": price, "source": "orderbook"}
                    self.log_test_result("호가 API", True, data)
                    return data
            self.log_test_result("호가 API", False, None, "호가 정보 없음")
            return None
        except Exception as e:
            self.log_test_result("호가 API", False, None, str(e))
            return None

    def test_orderbook_api_nx(self, stock_code: str) -> Dict[str, Any]:
        """테스트 11: 호가 API + _NX 코드"""
        self.log_test_start(
            "11. 호가 API + _NX 코드",
            f"종목코드: {stock_code}_NX"
        )
        try:
            response = self.client.request(
                api_id="ka10004",
                body={"stk_cd": f"{stock_code}_NX"},
                path="mrkcond"
            )
            if response and response.get('return_code') == 0:
                sell_price = response.get('sel_fpr_bid', '0').replace('+', '').replace('-', '')
                buy_price = response.get('buy_fpr_bid', '0').replace('+', '').replace('-', '')
                if sell_price and sell_price != '0':
                    price = abs(int(sell_price))
                    data = {"current_price": price, "source": "orderbook_nx"}
                    self.log_test_result("호가 API + _NX", True, data)
                    return data
            self.log_test_result("호가 API + _NX", False, None, "호가 정보 없음")
            return None
        except Exception as e:
            self.log_test_result("호가 API + _NX", False, None, str(e))
            return None

    def test_nxt_single_price_api(self, stock_code: str) -> Dict[str, Any]:
        """테스트 12: 시간외단일가 API (ka10087)"""
        self.log_test_start(
            "12. 시간외단일가 API (ka10087)",
            f"종목코드: {stock_code}"
        )
        try:
            response = self.client.request(
                api_id="ka10087",
                body={"stk_cd": stock_code},
                path="mrkcond"
            )
            if response and response.get('return_code') == 0:
                # ka10087 응답 구조 확인 필요
                logger.info(f"ka10087 응답 키: {list(response.keys())}")
                # 시간외단일가 현재가 추출 시도
                ovt_sigpric_cur_prc = response.get('ovt_sigpric_cur_prc', '0')
                if ovt_sigpric_cur_prc and ovt_sigpric_cur_prc != '0':
                    price = abs(int(ovt_sigpric_cur_prc.replace('+', '').replace('-', '')))
                    data = {"current_price": price, "source": "nxt_single_price"}
                    self.log_test_result("시간외단일가 API", True, data)
                    return data
            self.log_test_result("시간외단일가 API", False, None, "시간외단일가 정보 없음")
            return None
        except Exception as e:
            self.log_test_result("시간외단일가 API", False, None, str(e))
            return None

    # ========================================
    # 카테고리 5: 실시간 시세 (WebSocket)
    # ========================================

    def test_websocket_quote(self, stock_code: str) -> Dict[str, Any]:
        """테스트 13: WebSocket 실시간 호가 (0E - 주식시간외호가)"""
        self.log_test_start(
            "13. WebSocket 실시간 시간외호가",
            f"종목코드: {stock_code} (WebSocket TR=0E)"
        )
        # WebSocket은 별도 테스트 필요
        logger.warning("WebSocket 테스트는 별도 구현 필요")
        self.log_test_result("WebSocket 시간외호가", False, None, "미구현")
        return None

    # ========================================
    # 실행 메서드
    # ========================================

    def run_all_tests(self):
        """모든 테스트 실행"""
        logger.info(f"\n{'#'*80}")
        logger.info(f"# NXT 프리마켓 현재가 조회 종합 테스트")
        logger.info(f"# 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"# NXT 시간대: {is_nxt_hours()}")
        logger.info(f"# 정규장 시간대: {is_market_hours()}")
        logger.info(f"# 테스트 종목: {', '.join(self.test_stocks)}")
        logger.info(f"{'#'*80}\n")

        if not is_nxt_hours():
            logger.warning("⚠️  현재 NXT 시간대가 아닙니다!")
            logger.warning("    프리마켓: 08:00-09:00")
            logger.warning("    애프터마켓: 15:30-20:00")
            response = input("\n계속 진행하시겠습니까? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("테스트 중단")
                return

        # 각 종목에 대해 모든 테스트 실행
        for stock_code in self.test_stocks:
            logger.info(f"\n{'='*80}")
            logger.info(f"종목: {stock_code}")
            logger.info(f"{'='*80}\n")

            # 카테고리 1: 종목코드 형식
            self.test_stock_code_basic(stock_code)
            self.test_stock_code_nx(stock_code)
            self.test_stock_code_al(stock_code)

            # 카테고리 2: dmst_stex_tp 파라미터
            self.test_dmst_stex_tp_krx(stock_code)
            self.test_dmst_stex_tp_nxt(stock_code)
            self.test_dmst_stex_tp_sor(stock_code)

            # 카테고리 3: 조합
            self.test_nx_code_with_nxt_param(stock_code)
            self.test_nx_code_with_krx_param(stock_code)
            self.test_al_code_with_sor_param(stock_code)

            # 카테고리 4: 다른 API
            self.test_orderbook_api(stock_code)
            self.test_orderbook_api_nx(stock_code)
            self.test_nxt_single_price_api(stock_code)

            # 카테고리 5: WebSocket (참고용)
            self.test_websocket_quote(stock_code)

        # 결과 요약
        self.print_summary()

        # 결과 저장
        self.save_results()

    def print_summary(self):
        """테스트 결과 요약 출력"""
        logger.info(f"\n{'#'*80}")
        logger.info(f"# 테스트 결과 요약")
        logger.info(f"{'#'*80}\n")

        total_tests = len(self.results)
        successful_tests = [r for r in self.results if r['success']]
        failed_tests = [r for r in self.results if not r['success']]

        logger.info(f"총 테스트: {total_tests}개")
        logger.info(f"성공: {len(successful_tests)}개 ({len(successful_tests)/total_tests*100:.1f}%)")
        logger.info(f"실패: {len(failed_tests)}개 ({len(failed_tests)/total_tests*100:.1f}%)")

        if successful_tests:
            logger.info(f"\n✅ 성공한 테스트:")
            for r in successful_tests:
                price = r['data'].get('current_price', 'N/A')
                source = r['data'].get('source', 'N/A')
                logger.info(f"  - {r['test_name']}: {price:,}원 (출처: {source})")

        if failed_tests:
            logger.info(f"\n❌ 실패한 테스트:")
            for r in failed_tests:
                logger.info(f"  - {r['test_name']}: {r['error']}")

    def save_results(self):
        """테스트 결과를 JSON 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_nxt_premarket_results_{timestamp}.json"

        result_data = {
            "timestamp": datetime.now().isoformat(),
            "is_nxt_hours": is_nxt_hours(),
            "is_market_hours": is_market_hours(),
            "test_stocks": self.test_stocks,
            "total_tests": len(self.results),
            "successful_tests": len([r for r in self.results if r['success']]),
            "failed_tests": len([r for r in self.results if not r['success']]),
            "results": self.results,
            "summary": {
                "successful_approaches": [
                    {
                        "name": r['test_name'],
                        "source": r['data'].get('source'),
                        "price": r['data'].get('current_price')
                    }
                    for r in self.results if r['success']
                ]
            }
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        logger.info(f"\n테스트 결과 저장: {filename}")


if __name__ == "__main__":
    tester = NXTPremarketTester()
    tester.run_all_tests()
