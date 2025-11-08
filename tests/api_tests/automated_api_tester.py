#!/usr/bin/env python3
# automated_api_tester.py - CLI 기반 자동 API 테스터
# 목적: GUI 없이 API를 테스트하고 성공한 조회 방식을 저장/재사용

import sys
import logging
import json
import datetime
import time
import traceback
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

# 기존 모듈 import
try:
    from core import KiwoomRESTClient
    from config.manager import get_config
    import account
except ImportError as e:
    print(f"오류: 필수 모듈을 찾을 수 없습니다. {e}")
    print("현재 경로:", Path.cwd())
    print("sys.path:", sys.path)
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AutoAPITester")

# 결과 파일 경로
VERIFIED_CALLS_FILE = Path("verified_api_calls.json")
TEST_RESULTS_FILE = Path("api_test_results.json")
FAILED_CALLS_FILE = Path("failed_api_calls.json")


class APITester:
    """CLI 기반 API 자동 테스터"""

    def __init__(self):
        self.api_client = None
        self.client_ready = False
        self.test_results = []
        self.verified_calls = {}  # 성공한 API 호출 저장
        self.failed_calls = {}     # 실패한 API 호출 저장

        # API 이름 매핑 (comprehensive_api_debugger.py에서 가져옴)
        self.api_names = {
            "kt00001": "예수금상세현황요청",
            "kt00018": "계좌평가잔고내역요청",
            "ka10085": "계좌수익률요청",
            "ka10075": "미체결요청",
            "ka10076": "체결요청",
            "ka10001": "주식기본정보",
            "ka10027": "전일대비등락률상위요청",
            "ka10020": "호가잔량상위요청",
            "ka10021": "호가잔량급증요청",
            "ka10023": "거래량급증요청",
            "ka10029": "예상체결등락률상위요청",
            "ka10030": "당일거래량상위요청",
            "ka10031": "전일거래량상위요청",
            "ka10032": "거래대금상위요청",
            "ka10033": "신용비율상위요청",
            "ka10035": "외인연속순매매상위요청",
            "ka10036": "외인한도소진율증가상위",
            "ka10037": "외국계창구매매상위요청",
            "ka10038": "종목별증권사순위요청",
            "ka10040": "당일주요거래원요청",
            "ka10053": "당일상위이탈원요청",
            "ka10062": "동일순매매순위요청",
            "ka10098": "시간외단일가등락율순위요청",
            "ka90009": "외국인기관매매상위요청"
        }

    def initialize_client(self) -> bool:
        """API 클라이언트 초기화"""
        logger.info("API 클라이언트 초기화 시작...")

        try:
            config = get_config()
            self.api_client = KiwoomRESTClient()

            # config에서 필요한 값 확인
            required_keys = ['appkey', 'appsecret', 'account_number', 'base_url']
            api_config = config.get('api', {})

            if not all(api_config.get(key) for key in required_keys):
                logger.error("config.yaml에 API 설정이 누락되었습니다.")
                logger.error(f"필요한 키: {required_keys}")
                return False

            if hasattr(self.api_client, 'token') and self.api_client.token:
                logger.info("✅ API 클라이언트 준비 완료 (토큰 발급 성공)")
                self.client_ready = True
                return True
            else:
                logger.error(f"❌ API 클라이언트 초기화 실패: 토큰 발급 실패")
                return False

        except Exception as e:
            logger.error(f"❌ API 클라이언트 초기화 중 예외: {e}")
            logger.debug(traceback.format_exc())
            return False

    def get_common_params(self) -> Dict[str, str]:
        """공통 파라미터 생성"""
        params = account.p_common.copy()
        # 추가 파라미터 설정
        params["stk_cd"] = params.get("placeholder_stk_kospi", "005930")  # 삼성전자
        params["ord_qty"] = "1"
        params["ord_uv"] = "0"
        params["start_dt"] = params.get("week_ago_str", "")
        params["end_dt"] = params.get("today_str", "")
        params["base_dt"] = params.get("today_str", "")
        return params

    def test_single_variant(self, api_id: str, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """단일 Variant 테스트"""
        result_info = {
            "api_id": api_id,
            "path": path,
            "body": body,
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "unknown",
            "return_code": None,
            "return_msg": None,
            "data_received": False,
            "data_count": 0,
            "error": None
        }

        try:
            # API 호출
            result = self.api_client.request(api_id=api_id, body=body, path_prefix=path)

            if isinstance(result, dict):
                rc = result.get('return_code')
                rm = result.get('return_msg', '')

                result_info["return_code"] = rc
                result_info["return_msg"] = rm

                if rc == 0:
                    # 데이터 확인
                    list_keys = [k for k, v in result.items()
                                if isinstance(v, list) and k not in ['return_code', 'return_msg']]

                    if list_keys:
                        data_key = list_keys[0]
                        data_list = result.get(data_key, [])
                        result_info["data_count"] = len(data_list)
                        result_info["data_received"] = len(data_list) > 0

                        if len(data_list) > 0:
                            result_info["status"] = "success"
                            result_info["sample_data"] = data_list[0] if data_list else None
                        else:
                            result_info["status"] = "no_data"
                    else:
                        # 단일 값 확인
                        single_keys = [k for k, v in result.items()
                                     if not isinstance(v, list) and k not in
                                     ['return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key']]

                        if single_keys:
                            result_info["data_received"] = True
                            result_info["status"] = "success"
                        else:
                            result_info["status"] = "no_data"
                else:
                    result_info["status"] = "api_error"
            else:
                result_info["status"] = "unexpected_response"
                result_info["error"] = f"Unexpected response type: {type(result)}"

        except Exception as e:
            result_info["status"] = "exception"
            result_info["error"] = f"{e.__class__.__name__}: {str(e)}"
            logger.debug(traceback.format_exc())

        return result_info

    def test_api(self, api_id: str) -> List[Dict[str, Any]]:
        """특정 API의 모든 Variants 테스트"""
        api_name = self.api_names.get(api_id, api_id)
        logger.info(f"▶ '{api_id}: {api_name}' 테스트 시작...")

        results = []
        common_params = self.get_common_params()

        try:
            # account.py에서 variants 가져오기
            func = account.get_api_definition(api_id)
            if not func:
                logger.warning(f"⚪ '{api_id}' 정의 없음 - 건너뜀")
                return results

            variants = func(common_params)
            if not variants or not isinstance(variants, list):
                logger.warning(f"⚪ '{api_id}' Variants 없음 - 건너뜀")
                return results

            logger.info(f"  → {len(variants)} Variants 테스트 중...")

            for idx, (path, body) in enumerate(variants, 1):
                logger.debug(f"    Variant {idx}/{len(variants)}: path={path}, body={body}")

                result = self.test_single_variant(api_id, path, body)
                result["variant_index"] = idx
                result["total_variants"] = len(variants)
                result["api_name"] = api_name

                results.append(result)

                # 결과 로깅
                status = result["status"]
                if status == "success":
                    logger.info(f"  ✅ Variant {idx}/{len(variants)}: 성공 (데이터 {result['data_count']}개)")
                elif status == "no_data":
                    logger.warning(f"  ⚠️ Variant {idx}/{len(variants)}: 성공 (데이터 없음)")
                elif status == "api_error":
                    logger.error(f"  ❌ Variant {idx}/{len(variants)}: API 오류 - {result['return_msg']}")
                else:
                    logger.error(f"  ❌ Variant {idx}/{len(variants)}: {status} - {result.get('error', '')}")

                # API 요청 간격
                time.sleep(0.05)

            # 성공한 Variant 저장
            success_variants = [r for r in results if r["status"] == "success" and r["data_received"]]
            if success_variants:
                self.verified_calls[api_id] = {
                    "api_name": api_name,
                    "success_count": len(success_variants),
                    "total_variants": len(variants),
                    "verified_calls": [
                        {"path": r["path"], "body": r["body"], "data_count": r["data_count"]}
                        for r in success_variants
                    ],
                    "last_tested": datetime.datetime.now().isoformat()
                }
                logger.info(f"  💾 {len(success_variants)}개 성공 Variant 저장됨")

            # 실패한 Variant 저장
            failed_variants = [r for r in results if r["status"] not in ["success", "no_data"]]
            if failed_variants:
                self.failed_calls[api_id] = {
                    "api_name": api_name,
                    "failed_count": len(failed_variants),
                    "failures": [
                        {"path": r["path"], "body": r["body"], "error": r.get("error", r.get("return_msg", ""))}
                        for r in failed_variants
                    ],
                    "last_tested": datetime.datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"❌ '{api_id}' 테스트 중 예외: {e}")
            logger.debug(traceback.format_exc())

        return results

    def run_all_tests(self, exclude_orders: bool = True):
        """모든 API 테스트 실행"""
        logger.info("=" * 80)
        logger.info("🚀 전체 API 자동 테스트 시작")
        logger.info("=" * 80)

        if not self.client_ready:
            logger.error("API 클라이언트가 준비되지 않았습니다.")
            return

        # 제외할 API (주문, WS 등)
        exclude_api_ids = set()
        if exclude_orders:
            exclude_api_ids = {
                "kt10000", "kt10001", "kt10002", "kt10003",  # 주식 주문
                "kt10006", "kt10007", "kt10008", "kt10009",  # 신용 주문
                "kt50000", "kt50001", "kt50002", "kt50003",  # 금현물 주문
                "ka10171", "ka10172", "ka10173", "ka10174",  # 조건검색 WS
            }

        # account.py에서 모든 API ID 가져오기
        all_api_ids = [api_id for api_id in self.api_names.keys()
                      if api_id not in exclude_api_ids]

        logger.info(f"총 {len(all_api_ids)}개 API 테스트 예정")

        start_time = time.time()
        total_tests = 0

        for api_id in all_api_ids:
            results = self.test_api(api_id)
            self.test_results.extend(results)
            total_tests += len(results)

        elapsed_time = time.time() - start_time

        logger.info("=" * 80)
        logger.info(f"✅ 전체 테스트 완료 - {total_tests}개 Variant 테스트 ({elapsed_time:.1f}초)")
        logger.info("=" * 80)

        # 결과 저장
        self.save_results()

    def run_verified_tests(self):
        """저장된 성공 API만 재테스트"""
        logger.info("=" * 80)
        logger.info("🔄 검증된 API 재테스트 시작")
        logger.info("=" * 80)

        if not self.client_ready:
            logger.error("API 클라이언트가 준비되지 않았습니다.")
            return

        # 저장된 검증 파일 로드
        verified = self.load_verified_calls()
        if not verified:
            logger.warning("저장된 검증 API가 없습니다. 먼저 전체 테스트를 실행하세요.")
            return

        logger.info(f"총 {len(verified)}개 검증된 API 재테스트")

        for api_id, info in verified.items():
            api_name = info.get("api_name", api_id)
            verified_calls = info.get("verified_calls", [])

            logger.info(f"▶ '{api_id}: {api_name}' - {len(verified_calls)}개 검증된 호출")

            for idx, call in enumerate(verified_calls, 1):
                path = call["path"]
                body = call["body"]

                result = self.test_single_variant(api_id, path, body)
                result["variant_index"] = idx
                result["total_variants"] = len(verified_calls)
                result["api_name"] = api_name

                self.test_results.append(result)

                if result["status"] == "success":
                    logger.info(f"  ✅ 호출 {idx}/{len(verified_calls)}: 성공")
                else:
                    logger.error(f"  ❌ 호출 {idx}/{len(verified_calls)}: {result['status']}")

                time.sleep(0.05)

        logger.info("=" * 80)
        logger.info("✅ 검증된 API 재테스트 완료")
        logger.info("=" * 80)

        self.save_results()

    def save_results(self):
        """테스트 결과 저장"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # 전체 테스트 결과 저장
        result_file = Path(f"api_test_results_{timestamp}.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        logger.info(f"📄 테스트 결과 저장: {result_file}")

        # 검증된 API 저장
        if self.verified_calls:
            with open(VERIFIED_CALLS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.verified_calls, f, ensure_ascii=False, indent=2)
            logger.info(f"📄 검증된 API 저장: {VERIFIED_CALLS_FILE} ({len(self.verified_calls)}개)")

        # 실패한 API 저장
        if self.failed_calls:
            with open(FAILED_CALLS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.failed_calls, f, ensure_ascii=False, indent=2)
            logger.info(f"📄 실패한 API 저장: {FAILED_CALLS_FILE} ({len(self.failed_calls)}개)")

        # 요약 통계
        self.print_summary()

    def load_verified_calls(self) -> Dict:
        """저장된 검증 API 로드"""
        if not VERIFIED_CALLS_FILE.exists():
            return {}

        try:
            with open(VERIFIED_CALLS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"검증 파일 로드 오류: {e}")
            return {}

    def print_summary(self):
        """테스트 결과 요약 출력"""
        if not self.test_results:
            return

        total = len(self.test_results)
        success = len([r for r in self.test_results if r["status"] == "success" and r["data_received"]])
        no_data = len([r for r in self.test_results if r["status"] == "no_data"])
        failed = total - success - no_data

        logger.info("\n" + "=" * 80)
        logger.info("📊 테스트 결과 요약")
        logger.info("=" * 80)
        logger.info(f"  총 테스트: {total}개")
        logger.info(f"  ✅ 성공 (데이터 확인): {success}개 ({success/total*100:.1f}%)")
        logger.info(f"  ⚠️ 성공 (데이터 없음): {no_data}개 ({no_data/total*100:.1f}%)")
        logger.info(f"  ❌ 실패: {failed}개 ({failed/total*100:.1f}%)")
        logger.info("=" * 80)

        # 검증된 API 목록
        if self.verified_calls:
            logger.info(f"\n💾 검증된 API ({len(self.verified_calls)}개):")
            for api_id, info in sorted(self.verified_calls.items()):
                logger.info(f"  - {api_id}: {info['api_name']} ({info['success_count']}개 호출)")


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="Kiwoom REST API 자동 테스터")
    parser.add_argument("mode", choices=["all", "verified", "list"],
                       help="실행 모드: all=전체 테스트, verified=검증된 API만, list=검증된 API 목록")
    parser.add_argument("--debug", action="store_true", help="디버그 모드 활성화")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    tester = APITester()

    if args.mode == "list":
        # 검증된 API 목록만 출력
        verified = tester.load_verified_calls()
        if verified:
            print(f"\n검증된 API ({len(verified)}개):")
            for api_id, info in sorted(verified.items()):
                print(f"  {api_id}: {info['api_name']} - {info['success_count']}개 성공 호출")
                print(f"    마지막 테스트: {info['last_tested']}")
        else:
            print("저장된 검증 API가 없습니다.")
        return

    # API 클라이언트 초기화
    if not tester.initialize_client():
        logger.error("API 클라이언트 초기화 실패. 종료합니다.")
        sys.exit(1)

    # 모드에 따라 실행
    if args.mode == "all":
        tester.run_all_tests(exclude_orders=True)
    elif args.mode == "verified":
        tester.run_verified_tests()


if __name__ == "__main__":
    main()
