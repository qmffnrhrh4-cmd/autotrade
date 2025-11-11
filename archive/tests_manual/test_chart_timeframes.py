"""
차트 분봉 데이터 조회 테스트

일봉, 1분봉, 3분봉, 5분봉, 10분봉, 60분봉을 모두 테스트하여
성공하는 API ID와 파라미터 조합을 찾습니다.

실행 방법:
    python tests/manual_tests/test_chart_timeframes.py
"""

import sys
from pathlib import Path
import json
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import KiwoomRESTClient


class ChartTimeframesTester:
    """차트 분봉 테스트"""

    def __init__(self):
        self.client = KiwoomRESTClient()
        self.test_stock = "005930"  # 삼성전자
        self.today = datetime.now().strftime("%Y%m%d")
        self.yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        self.last_week = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

        self.success_results = []
        self.failed_results = []

    def test_api_call(self, test_name: str, api_id: str, path: str, body: dict):
        """API 호출 테스트"""
        print(f"\n{'='*80}")
        print(f"[테스트] {test_name}")
        print(f"{'='*80}")
        print(f"API ID: {api_id}")
        print(f"Path: {path}")
        print(f"Body: {json.dumps(body, ensure_ascii=False, indent=2)}")

        try:
            response = self.client.request(api_id=api_id, body=body, path=path)

            if response:
                print(f"✅ API 호출 성공!")
                print(f"응답 키: {list(response.keys())}")

                # 데이터 확인 - 실제 데이터가 있는지 체크
                has_data = False
                data_count = 0

                for key, value in response.items():
                    if isinstance(value, list):
                        data_count = len(value)
                        print(f"   - {key}: {data_count}개 항목")
                        if data_count > 0:
                            has_data = True
                            print(f"      첫 번째 항목 키: {list(value[0].keys())}")
                            print(f"      첫 번째 항목 샘플: {json.dumps(value[0], ensure_ascii=False, indent=8)}")
                        else:
                            print(f"      ⚠️ 데이터가 비어있음 (빈 배열)")
                    else:
                        print(f"   - {key}: {value}")

                # 실제 데이터가 있을 때만 성공으로 간주
                if has_data:
                    print(f"✅ 실제 데이터 있음: {data_count}개")
                    self.success_results.append({
                        'test_name': test_name,
                        'api_id': api_id,
                        'path': path,
                        'body': body,
                        'response_keys': list(response.keys()),
                        'data_count': data_count
                    })
                    return True
                else:
                    print(f"❌ API 호출은 성공했지만 데이터가 없음")
                    self.failed_results.append({
                        'test_name': test_name,
                        'api_id': api_id,
                        'path': path,
                        'body': body,
                        'error': 'No data in response (empty array)'
                    })
                    return False
            else:
                print(f"❌ 실패: 응답 없음")
                self.failed_results.append({
                    'test_name': test_name,
                    'api_id': api_id,
                    'path': path,
                    'body': body,
                    'error': 'No response'
                })
                return False

        except Exception as e:
            print(f"❌ 실패: {e}")
            self.failed_results.append({
                'test_name': test_name,
                'api_id': api_id,
                'path': path,
                'body': body,
                'error': str(e)
            })
            return False

    def run_all_tests(self):
        """모든 테스트 실행"""
        print(f"\n" + "="*80)
        print(f"차트 분봉 데이터 조회 테스트 시작")
        print(f"테스트 종목: {self.test_stock} (삼성전자)")
        print(f"기준일: {self.today}")
        print(f"="*80)

        # ===== 1. 일봉 (ka10081 - 검증 완료) =====
        self.test_api_call(
            test_name="1-1. 일봉 차트 조회 (ka10081)",
            api_id="ka10081",
            path="chart",
            body={
                "stk_cd": self.test_stock,
                "base_dt": self.today,
                "upd_stkpc_tp": "1"  # 수정주가
            }
        )

        # ===== 2. 분봉 시도 1: ka10081 + 분봉 파라미터 =====
        # 일봉 API에 분봉 파라미터 추가
        for timeframe, code in [("1분봉", "1"), ("3분봉", "3"), ("5분봉", "5"), ("10분봉", "10"), ("60분봉", "60")]:
            self.test_api_call(
                test_name=f"2-1. {timeframe} (ka10081 + inq_tp)",
                api_id="ka10081",
                path="chart",
                body={
                    "stk_cd": self.test_stock,
                    "base_dt": self.today,
                    "upd_stkpc_tp": "1",
                    "inq_tp": code  # 조회 타입
                }
            )

        # ===== 3. 분봉 시도 2: 다른 API ID 시도 =====
        # ka10002, ka10003, ka10004, ka10005 등
        minute_apis = [
            ("ka10002", "chart"),
            ("ka10003", "chart"),
            ("ka10004", "chart"),
            ("ka10005", "chart"),
            ("ka10080", "chart"),  # 틱차트
            ("ka10082", "chart"),  # 기간별차트
        ]

        for api_id, path in minute_apis:
            self.test_api_call(
                test_name=f"3-1. 1분봉 시도 ({api_id})",
                api_id=api_id,
                path=path,
                body={
                    "stk_cd": self.test_stock,
                    "base_dt": self.today,
                    "upd_stkpc_tp": "1"
                }
            )

        # ===== 4. 분봉 시도 3: 시간 범위 지정 =====
        self.test_api_call(
            test_name="4-1. 1분봉 + 시간범위 (ka10081)",
            api_id="ka10081",
            path="chart",
            body={
                "stk_cd": self.test_stock,
                "base_dt": self.today,
                "upd_stkpc_tp": "1",
                "fr_dt": self.last_week,  # 시작일
                "to_dt": self.today,      # 종료일
            }
        )

        # ===== 5. 분봉 시도 4: 다른 path 시도 =====
        paths = ["mrkcond", "stkinfo", "stkprc", "inquire"]

        for path in paths:
            self.test_api_call(
                test_name=f"5-1. 분봉 + {path} (ka10081)",
                api_id="ka10081",
                path=path,
                body={
                    "stk_cd": self.test_stock,
                    "base_dt": self.today,
                    "upd_stkpc_tp": "1"
                }
            )

        # ===== 6. 분봉 시도 5: 주기 파라미터 =====
        for timeframe, period in [("1분봉", "1"), ("3분봉", "3"), ("5분봉", "5"), ("10분봉", "10"), ("60분봉", "60")]:
            self.test_api_call(
                test_name=f"6-1. {timeframe} + period (ka10081)",
                api_id="ka10081",
                path="chart",
                body={
                    "stk_cd": self.test_stock,
                    "base_dt": self.today,
                    "upd_stkpc_tp": "1",
                    "period": period
                }
            )

        # ===== 7. 분봉 시도 6: 봉종류 파라미터 =====
        for timeframe, chart_type in [("1분봉", "M"), ("5분봉", "5"), ("10분봉", "10"), ("60분봉", "60")]:
            self.test_api_call(
                test_name=f"7-1. {timeframe} + chart_type (ka10081)",
                api_id="ka10081",
                path="chart",
                body={
                    "stk_cd": self.test_stock,
                    "base_dt": self.today,
                    "upd_stkpc_tp": "1",
                    "chart_type": chart_type
                }
            )

        # ===== 8. 분봉 시도 7: 실시간 차트 API =====
        self.test_api_call(
            test_name="8-1. 실시간 분봉 (WebSocket 형식?)",
            api_id="ka10000",  # 추측
            path="chart",
            body={
                "stk_cd": self.test_stock,
                "base_dt": self.today
            }
        )

        # ===== 9. 알려진 성공 API 재확인 =====
        print(f"\n{'='*80}")
        print(f"[최종] 알려진 성공 API 재확인")
        print(f"{'='*80}")

        known_apis = [
            ("ka10006", "chart", {"stk_cd": self.test_stock, "base_dt": self.today}),
            ("ka10045", "stkinfo", {"stk_cd": self.test_stock, "inq_strt_dt": self.last_week, "inq_end_dt": self.today}),
            ("ka10047", "mrkcond", {"stk_cd": self.test_stock}),
            ("ka90013", "mrkcond", {"stk_cd": self.test_stock}),
        ]

        for api_id, path, body in known_apis:
            self.test_api_call(
                test_name=f"9-1. 검증된 API ({api_id})",
                api_id=api_id,
                path=path,
                body=body
            )

        # ===== 결과 출력 =====
        self.print_summary()

    def print_summary(self):
        """테스트 결과 요약"""
        print(f"\n{'='*80}")
        print(f"테스트 결과 요약")
        print(f"{'='*80}")

        total = len(self.success_results) + len(self.failed_results)
        success_rate = len(self.success_results) / total * 100 if total > 0 else 0

        print(f"\n전체: {total}개")
        print(f"✅ 성공: {len(self.success_results)}개 ({success_rate:.1f}%)")
        print(f"❌ 실패: {len(self.failed_results)}개")

        if self.success_results:
            print(f"\n{'='*80}")
            print(f"✅ 성공한 API 목록")
            print(f"{'='*80}")
            for result in self.success_results:
                print(f"\n[{result['test_name']}]")
                print(f"  API ID: {result['api_id']}")
                print(f"  Path: {result['path']}")
                print(f"  Body: {json.dumps(result['body'], ensure_ascii=False)}")
                print(f"  응답 키: {result['response_keys']}")

        # 성공 결과를 JSON 파일로 저장
        if self.success_results:
            output_file = BASE_DIR / "tests" / "manual_tests" / "successful_chart_apis.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.success_results, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 성공 결과 저장: {output_file}")


def main():
    """메인 함수"""
    tester = ChartTimeframesTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
