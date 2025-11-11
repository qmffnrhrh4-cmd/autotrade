"""
종합 테스트: 스코어링 데이터 수집 + WebSocket 연결 조건 찾기

이 테스트는 다음 두 가지를 수행합니다:
1. 스코어링에 필요한 데이터를 다양한 API 조합으로 수집 테스트
2. WebSocket 연결 조건을 다양한 조합으로 테스트

✅ 검증 완료된 API (Production Ready):
  - ka10081: 일봉차트조회 (path=chart) ← 평균거래량/변동성
  - ka10047: 체결강도추이 (path=mrkcond) ← 체결강도
  - ka90013: 프로그램매매추이 (path=mrkcond) ← 프로그램순매수
  - ka10078: 증권사별매매동향 (path=mrkcond) ← 증권사 순매수
  - ka10045: 기관매매추이 (path=mrkcond) ← 기관 트렌드
  - ka10059: 투자자별매매 (path=stkinfo) ← 기관/외국인 순매수
  - ka10004: 주식호가 (path=mrkcond) ← 호가비율

실행 방법:
    python tests/manual_tests/test_comprehensive_data_collection.py

결과:
    - 각 API별 성공/실패 상태
    - 샘플 데이터 (JSON)
    - 자동으로 _test_results/ 디렉토리에 저장

주의: 실제 API 호출이 발생하며, 시간이 다소 소요될 수 있습니다.
"""

import sys
import os
from datetime import datetime
import json
import time
import asyncio
import websockets

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.rest_client import KiwoomRESTClient
from utils.trading_date import get_last_trading_date


class ComprehensiveDataTester:
    """종합 데이터 수집 및 WebSocket 테스트"""

    def __init__(self):
        """테스터 초기화"""
        self.rest_client = KiwoomRESTClient()  # 싱글톤 패턴으로 동작
        self.test_stock = "005930"  # 삼성전자 (테스트용)
        self.test_results = {
            'scoring_apis': [],
            'websocket_tests': [],
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
        }

        # WebSocket 테스트를 위한 토큰 추출
        self.access_token = self.rest_client.token if hasattr(self.rest_client, 'token') else ''
        self.base_url = self.rest_client.base_url

        # WebSocket URL 결정
        if 'mockapi' in self.base_url:
            self.ws_url = "wss://mockapi.kiwoom.com:10000/api/dostk/websocket"
        else:
            self.ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"

    def print_section(self, title: str):
        """섹션 헤더 출력"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80 + "\n")

    # ================================================================
    # Part 1: 스코어링 데이터 수집 API 테스트
    # ================================================================

    def test_scoring_api(self, test_name: str, api_id: str, body: dict, path: str) -> dict:
        """
        스코어링 API 테스트

        Args:
            test_name: 테스트 이름
            api_id: API ID (예: ka10004)
            body: 요청 Body
            path: 요청 Path

        Returns:
            테스트 결과
        """
        print(f"\n🧪 테스트: {test_name}")
        print(f"   API: {api_id}")
        print(f"   Body: {json.dumps(body, ensure_ascii=False)}")

        try:
            response = self.rest_client.request(
                api_id=api_id,
                body=body,
                path=path
            )

            success = response and response.get('return_code') == 0

            result = {
                'test_name': test_name,
                'api_id': api_id,
                'body': body,
                'path': path,
                'success': success,
                'return_code': response.get('return_code') if response else None,
                'return_msg': response.get('return_msg') if response else 'No response',
                'has_data': False,
                'data_keys': [],
                'sample_data': None
            }

            if success:
                # 응답에서 데이터 키 추출 (return_code, return_msg 제외)
                data_keys = [k for k in response.keys() if k not in ['return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key']]
                result['data_keys'] = data_keys
                result['has_data'] = len(data_keys) > 0

                # 샘플 데이터 추출 (첫 번째 데이터만)
                if data_keys:
                    first_key = data_keys[0]
                    first_value = response.get(first_key)

                    if isinstance(first_value, list) and len(first_value) > 0:
                        result['sample_data'] = first_value[0]
                    elif isinstance(first_value, dict):
                        result['sample_data'] = first_value
                    else:
                        result['sample_data'] = first_value

                print(f"   ✅ 성공: {result['return_msg']}")
                print(f"   📊 데이터 키: {data_keys}")
                if result['sample_data']:
                    print(f"   📦 샘플 데이터 (첫 번째):")
                    print(f"      {json.dumps(result['sample_data'], ensure_ascii=False, indent=6)[:200]}...")
            else:
                print(f"   ❌ 실패: {result['return_msg']}")

            self.test_results['scoring_apis'].append(result)
            return result

        except Exception as e:
            print(f"   ❌ 예외 발생: {str(e)}")
            error_result = {
                'test_name': test_name,
                'api_id': api_id,
                'body': body,
                'path': path,
                'success': False,
                'error': str(e)
            }
            self.test_results['scoring_apis'].append(error_result)
            return error_result

    def run_scoring_tests(self):
        """스코어링 데이터 수집 API 테스트 실행"""
        self.print_section("Part 1: 스코어링 데이터 수집 API 테스트")

        print("📋 스코어링에 필요한 데이터:")
        print("   1. 주식 호가 (매도/매수 호가, 잔량)")
        print("   2. 기관 매매 정보")
        print("   3. 외국인 매매 정보")
        print("   4. 투자자별 매매 동향")
        print("   5. 종목 체결 정보 (현재가, 거래량 등)")
        print("\n🎯 다양한 API 조합으로 데이터 수집을 테스트합니다...\n")

        # 날짜 파라미터 준비
        today = get_last_trading_date()

        # ===== 테스트 케이스 1: 주식호가 (ka10004) =====
        self.test_scoring_api(
            test_name="Case 1-1: 주식호가 기본 조회 (KRX)",
            api_id="ka10004",
            body={"stk_cd": self.test_stock},
            path="mrkcond"
        )

        self.test_scoring_api(
            test_name="Case 1-2: 주식호가 NXT 거래소",
            api_id="ka10004",
            body={"stk_cd": f"{self.test_stock}_NX"},
            path="mrkcond"
        )

        self.test_scoring_api(
            test_name="Case 1-3: 주식호가 SOR 거래소",
            api_id="ka10004",
            body={"stk_cd": f"{self.test_stock}_AL"},
            path="mrkcond"
        )

        # ===== 테스트 케이스 2: 주식체결정보 (ka10003) =====
        self.test_scoring_api(
            test_name="Case 2-1: 주식체결정보 기본 조회",
            api_id="ka10003",
            body={"stk_cd": self.test_stock},
            path="stkinfo"
        )

        self.test_scoring_api(
            test_name="Case 2-2: 주식체결정보 NXT",
            api_id="ka10003",
            body={"stk_cd": f"{self.test_stock}_NX"},
            path="stkinfo"
        )

        # ===== 테스트 케이스 3: 투자자별 매매 (ka10059) =====
        self.test_scoring_api(
            test_name="Case 3-1: 투자자별 매매 - 금액/순매수",
            api_id="ka10059",
            body={
                "stk_cd": self.test_stock,
                "dt": today,
                "amt_qty_tp": "1",  # 1:금액
                "trde_tp": "0",     # 0:순매수
                "unit_tp": "1000"   # 1000:천주
            },
            path="stkinfo"
        )

        self.test_scoring_api(
            test_name="Case 3-2: 투자자별 매매 - 수량/순매수",
            api_id="ka10059",
            body={
                "stk_cd": self.test_stock,
                "dt": today,
                "amt_qty_tp": "2",  # 2:수량
                "trde_tp": "0",
                "unit_tp": "1000"
            },
            path="stkinfo"
        )

        self.test_scoring_api(
            test_name="Case 3-3: 투자자별 매매 - 매수량",
            api_id="ka10059",
            body={
                "stk_cd": self.test_stock,
                "dt": today,
                "amt_qty_tp": "2",
                "trde_tp": "1",     # 1:매수
                "unit_tp": "1000"
            },
            path="stkinfo"
        )

        self.test_scoring_api(
            test_name="Case 3-4: 투자자별 매매 - 매도량",
            api_id="ka10059",
            body={
                "stk_cd": self.test_stock,
                "dt": today,
                "amt_qty_tp": "2",
                "trde_tp": "2",     # 2:매도
                "unit_tp": "1000"
            },
            path="stkinfo"
        )

        # ===== 테스트 케이스 4: 외국인 종목별 매매동향 (ka10008) =====
        self.test_scoring_api(
            test_name="Case 4-1: 외국인 종목별 매매동향",
            api_id="ka10008",
            body={"stk_cd": self.test_stock},
            path="frgnistt"
        )

        self.test_scoring_api(
            test_name="Case 4-2: 외국인 종목별 매매동향 (NXT)",
            api_id="ka10008",
            body={"stk_cd": f"{self.test_stock}_NX"},
            path="frgnistt"
        )

        # ===== 테스트 케이스 5: 기관 요청 (ka10009) =====
        self.test_scoring_api(
            test_name="Case 5-1: 주식기관 정보",
            api_id="ka10009",
            body={"stk_cd": self.test_stock},
            path="frgnistt"
        )

        # ===== 테스트 케이스 6: 기관외국인 연속매매 (ka10131) =====
        self.test_scoring_api(
            test_name="Case 6-1: 기관외국인 연속매매 - 최근 1일/KRX/순매수",
            api_id="ka10131",
            body={
                "dt": "1",           # 1:최근일
                "strt_dt": "",
                "end_dt": "",
                "mrkt_tp": "001",    # 001:코스피
                "netslmt_tp": "2",   # 2:순매수
                "stk_inds_tp": "0",  # 0:종목
                "amt_qty_tp": "0",   # 0:금액
                "stex_tp": "1"       # 1:KRX
            },
            path="frgnistt"
        )

        self.test_scoring_api(
            test_name="Case 6-2: 기관외국인 연속매매 - 5일/수량",
            api_id="ka10131",
            body={
                "dt": "5",
                "strt_dt": "",
                "end_dt": "",
                "mrkt_tp": "001",
                "netslmt_tp": "2",
                "stk_inds_tp": "0",
                "amt_qty_tp": "1",   # 1:수량
                "stex_tp": "1"
            },
            path="frgnistt"
        )

        self.test_scoring_api(
            test_name="Case 6-3: 기관외국인 연속매매 - NXT 거래소",
            api_id="ka10131",
            body={
                "dt": "1",
                "strt_dt": "",
                "end_dt": "",
                "mrkt_tp": "001",
                "netslmt_tp": "2",
                "stk_inds_tp": "0",
                "amt_qty_tp": "0",
                "stex_tp": "2"       # 2:NXT
            },
            path="frgnistt"
        )

        self.test_scoring_api(
            test_name="Case 6-4: 기관외국인 연속매매 - 통합 거래소",
            api_id="ka10131",
            body={
                "dt": "1",
                "strt_dt": "",
                "end_dt": "",
                "mrkt_tp": "001",
                "netslmt_tp": "2",
                "stk_inds_tp": "0",
                "amt_qty_tp": "0",
                "stex_tp": "3"       # 3:통합
            },
            path="frgnistt"
        )

        # ===== 테스트 케이스 7: 장중 투자자별 매매 (ka10063) =====
        self.test_scoring_api(
            test_name="Case 7-1: 장중 투자자별매매 - 기관계/금액",
            api_id="ka10063",
            body={
                "mrkt_tp": "001",         # 시장구분: 001=코스피
                "amt_qty_tp": "1",        # 금액수량구분: 1=금액
                "invsr": "7",             # 투자자별: 7=기관계
                "frgn_all": "0",          # 외국계전체: 0=미체크
                "smtm_netprps_tp": "0",   # 동시순매수구분: 0=미체크
                "stex_tp": "1"            # 거래소구분: 1=KRX
            },
            path="mrkcond"
        )

        self.test_scoring_api(
            test_name="Case 7-2: 장중 투자자별매매 - 외국인/수량",
            api_id="ka10063",
            body={
                "mrkt_tp": "001",
                "amt_qty_tp": "2",        # 금액수량구분: 2=수량
                "invsr": "6",             # 투자자별: 6=외국인
                "frgn_all": "1",          # 외국계전체: 1=체크
                "smtm_netprps_tp": "0",
                "stex_tp": "1"
            },
            path="mrkcond"
        )

        # ===== 테스트 케이스 8: 장마감후 투자자별 매매 (ka10066) =====
        self.test_scoring_api(
            test_name="Case 8-1: 장마감후 투자자별매매 - 순매수/금액",
            api_id="ka10066",
            body={
                "mrkt_tp": "001",      # 시장구분: 001=코스피
                "amt_qty_tp": "1",     # 금액수량구분: 1=금액
                "trde_tp": "0",        # 매매구분: 0=순매수
                "stex_tp": "1"         # 거래소구분: 1=KRX
            },
            path="mrkcond"
        )

        self.test_scoring_api(
            test_name="Case 8-2: 장마감후 투자자별매매 - 순매수/수량",
            api_id="ka10066",
            body={
                "mrkt_tp": "001",
                "amt_qty_tp": "2",     # 금액수량구분: 2=수량
                "trde_tp": "0",
                "stex_tp": "1"
            },
            path="mrkcond"
        )

        # ===== 테스트 케이스 9: 종목별 기관매매추이 (ka10045) =====
        # 날짜 범위 계산 (최근 5일)
        from datetime import datetime, timedelta
        end_date = datetime.strptime(today, "%Y%m%d")
        start_date = end_date - timedelta(days=5)
        start_dt_str = start_date.strftime("%Y%m%d")

        self.test_scoring_api(
            test_name="Case 9-1: 종목별 기관매매추이 - 5일/매수단가",
            api_id="ka10045",
            body={
                "stk_cd": self.test_stock,
                "strt_dt": start_dt_str,      # 필수: 시작일자
                "end_dt": today,               # 필수: 종료일자
                "orgn_prsm_unp_tp": "1",       # 필수: 기관추정단가구분 (1=매수단가, 2=매도단가)
                "for_prsm_unp_tp": "1"         # 필수: 외인추정단가구분 (1=매수단가, 2=매도단가)
            },
            path="mrkcond"
        )

        self.test_scoring_api(
            test_name="Case 9-2: 종목별 기관매매추이 - 1일/매도단가",
            api_id="ka10045",
            body={
                "stk_cd": self.test_stock,
                "strt_dt": today,
                "end_dt": today,
                "orgn_prsm_unp_tp": "2",       # 매도단가
                "for_prsm_unp_tp": "2"         # 매도단가
            },
            path="mrkcond"
        )

        # ===== 테스트 케이스 10: 증권사별 종목매매동향 (ka10078) =====
        # 주요 증권사 코드 예시
        securities_firms = [
            ("040", "KB증권"),
            ("039", "교보증권"),
            ("001", "한국투자증권")
        ]

        # 날짜 범위 계산 (최근 3일)
        end_date_10 = datetime.strptime(today, "%Y%m%d")
        start_date_10 = end_date_10 - timedelta(days=3)
        start_dt_10 = start_date_10.strftime("%Y%m%d")

        for firm_code, firm_name in securities_firms[:2]:  # 처음 2개만 테스트
            self.test_scoring_api(
                test_name=f"Case 10-{securities_firms.index((firm_code, firm_name)) + 1}: 증권사별 종목매매동향 - {firm_name}",
                api_id="ka10078",
                body={
                    "mmcm_cd": firm_code,     # 필수: 회원사코드
                    "stk_cd": self.test_stock,
                    "strt_dt": start_dt_10,   # 필수: 시작일자
                    "end_dt": today           # 필수: 종료일자
                },
                path="mrkcond"
            )

        # ===== 테스트 케이스 11: 일봉차트조회 (ka10081) ✅ VERIFIED =====
        print("\n" + "=" * 80)
        print("✅ 테스트 케이스 11: 일봉차트조회 (ka10081) - 검증 완료!")
        print("=" * 80)

        self.test_scoring_api(
            test_name="Case 11-1: 일봉차트조회 - 기본 (path=chart)",
            api_id="ka10081",
            body={
                "stk_cd": self.test_stock,
                "base_dt": today,
                "upd_stkpc_tp": "1"  # 수정주가 반영
            },
            path="chart"  # ⚠️ 중요: chart 경로 사용!
        )

        self.test_scoring_api(
            test_name="Case 11-2: 일봉차트조회 - 과거 날짜",
            api_id="ka10081",
            body={
                "stk_cd": self.test_stock,
                "base_dt": start_dt_10,  # 3일 전
                "upd_stkpc_tp": "1"
            },
            path="chart"
        )

        # ===== 테스트 케이스 12: 체결강도추이 (ka10047) ✅ VERIFIED =====
        print("\n" + "=" * 80)
        print("✅ 테스트 케이스 12: 체결강도추이 (ka10047) - 검증 완료!")
        print("=" * 80)

        self.test_scoring_api(
            test_name="Case 12-1: 체결강도추이 - 기본",
            api_id="ka10047",
            body={
                "stk_cd": self.test_stock
            },
            path="mrkcond"
        )

        self.test_scoring_api(
            test_name="Case 12-2: 체결강도추이 - 다른 종목 (SK하이닉스)",
            api_id="ka10047",
            body={
                "stk_cd": "000660"
            },
            path="mrkcond"
        )

        # ===== 테스트 케이스 13: 프로그램매매추이 (ka90013) ✅ VERIFIED =====
        print("\n" + "=" * 80)
        print("✅ 테스트 케이스 13: 프로그램매매추이 (ka90013) - 검증 완료!")
        print("=" * 80)

        self.test_scoring_api(
            test_name="Case 13-1: 프로그램매매추이 - 금액 기준",
            api_id="ka90013",
            body={
                "stk_cd": self.test_stock,
                "amt_qty_tp": "1",  # 1: 금액
                "date": ""
            },
            path="mrkcond"
        )

        self.test_scoring_api(
            test_name="Case 13-2: 프로그램매매추이 - 수량 기준",
            api_id="ka90013",
            body={
                "stk_cd": self.test_stock,
                "amt_qty_tp": "2",  # 2: 수량
                "date": ""
            },
            path="mrkcond"
        )

        self.test_scoring_api(
            test_name="Case 13-3: 프로그램매매추이 - 특정 날짜",
            api_id="ka90013",
            body={
                "stk_cd": self.test_stock,
                "amt_qty_tp": "1",
                "date": today
            },
            path="mrkcond"
        )

        print("\n" + "=" * 80)
        print(f"✅ 스코어링 API 테스트 완료: 총 {len(self.test_results['scoring_apis'])}개")
        successful = sum(1 for r in self.test_results['scoring_apis'] if r.get('success', False))
        print(f"   성공: {successful}개 / 실패: {len(self.test_results['scoring_apis']) - successful}개")
        print("=" * 80)

    # ================================================================
    # Part 2: WebSocket 연결 조건 테스트
    # ================================================================

    async def test_websocket_connection(
        self,
        test_name: str,
        subscribe_request: dict,
        duration: int = 5
    ) -> dict:
        """
        WebSocket 연결 테스트

        Args:
            test_name: 테스트 이름
            subscribe_request: 구독 요청 메시지
            duration: 테스트 대기 시간 (초)

        Returns:
            테스트 결과
        """
        print(f"\n🧪 테스트: {test_name}")
        print(f"   URL: {self.ws_url}")
        print(f"   구독 요청: {json.dumps(subscribe_request, ensure_ascii=False)}")

        result = {
            'test_name': test_name,
            'subscribe_request': subscribe_request,
            'success': False,
            'connected': False,
            'subscription_success': False,
            'messages_received': 0,
            'error': None,
            'sample_messages': []
        }

        try:
            # WebSocket 연결 - Python 3.13+ 호환
            # additional_headers 또는 직접 URL에 토큰 전달
            async with websockets.connect(
                self.ws_url,
                additional_headers={
                    'authorization': f'Bearer {self.access_token}'
                },
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                result['connected'] = True
                print(f"   ✅ WebSocket 연결 성공")

                # 구독 요청 전송
                await websocket.send(json.dumps(subscribe_request))
                print(f"   📤 구독 요청 전송")

                # 응답 대기
                start_time = time.time()
                while time.time() - start_time < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)

                        result['messages_received'] += 1

                        # 처음 3개 메시지만 샘플로 저장
                        if len(result['sample_messages']) < 3:
                            result['sample_messages'].append(data)

                        # 구독 응답 확인
                        if data.get('trnm') == 'REG' and data.get('return_code') == 0:
                            result['subscription_success'] = True
                            print(f"   ✅ 구독 성공: {data.get('return_msg', '')}")

                        # 실시간 데이터 수신 확인
                        if data.get('trnm') == 'REAL':
                            print(f"   📨 실시간 데이터 수신 (총 {result['messages_received']}개)")
                            if result['messages_received'] <= 3:
                                print(f"      데이터: {json.dumps(data, ensure_ascii=False)[:200]}...")

                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"   ⚠️ 메시지 수신 오류: {str(e)}")
                        break

                result['success'] = result['connected'] and result['subscription_success']

                if result['success']:
                    print(f"   ✅ 테스트 성공: 연결 성공, 구독 성공, {result['messages_received']}개 메시지 수신")
                else:
                    print(f"   ⚠️ 테스트 부분 성공: 연결={result['connected']}, 구독={result['subscription_success']}, 수신={result['messages_received']}개")

        except Exception as e:
            result['error'] = str(e)
            print(f"   ❌ 실패: {str(e)}")

        self.test_results['websocket_tests'].append(result)
        return result

    async def run_websocket_tests(self):
        """WebSocket 연결 조건 테스트 실행"""
        self.print_section("Part 2: WebSocket 연결 조건 테스트")

        print("📋 WebSocket 테스트 목표:")
        print("   1. 다양한 구독 형식 테스트")
        print("   2. 다양한 실시간 항목 조드 테스트")
        print("   3. grp_no, refresh 파라미터 조합 테스트")
        print("\n🎯 다양한 WebSocket 연결 조건을 테스트합니다...\n")

        # ===== 테스트 케이스 1: 기본 구독 (주문체결) =====
        await self.test_websocket_connection(
            test_name="WS Case 1-1: 주문체결 구독 (type=00, refresh=1)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [""],
                    "type": ["00"]
                }]
            },
            duration=5
        )

        await self.test_websocket_connection(
            test_name="WS Case 1-2: 주문체결 구독 (type=00, refresh=0)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "0",
                "data": [{
                    "item": [""],
                    "type": ["00"]
                }]
            },
            duration=5
        )

        # ===== 테스트 케이스 2: 주식체결 구독 (0B) =====
        await self.test_websocket_connection(
            test_name="WS Case 2-1: 주식체결 구독 (삼성전자)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0B"]
                }]
            },
            duration=10
        )

        await self.test_websocket_connection(
            test_name="WS Case 2-2: 주식체결 구독 (빈 item)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [""],
                    "type": ["0B"]
                }]
            },
            duration=5
        )

        # ===== 테스트 케이스 3: 주식호가잔량 구독 (0D) =====
        await self.test_websocket_connection(
            test_name="WS Case 3-1: 주식호가잔량 구독 (삼성전자)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "2",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0D"]
                }]
            },
            duration=10
        )

        # ===== 테스트 케이스 4: 복수 항목 구독 =====
        await self.test_websocket_connection(
            test_name="WS Case 4-1: 복수 항목 구독 (0B + 0D)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0B", "0D"]
                }]
            },
            duration=10
        )

        await self.test_websocket_connection(
            test_name="WS Case 4-2: 복수 종목 구독",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock, "000660"],  # 삼성전자, SK하이닉스
                    "type": ["0B"]
                }]
            },
            duration=10
        )

        # ===== 테스트 케이스 5: 잔고 구독 (04) =====
        await self.test_websocket_connection(
            test_name="WS Case 5-1: 잔고 구독",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "3",
                "refresh": "1",
                "data": [{
                    "item": [""],
                    "type": ["04"]
                }]
            },
            duration=5
        )

        # ===== 테스트 케이스 6: 주식기세 구독 (0A) =====
        await self.test_websocket_connection(
            test_name="WS Case 6-1: 주식기세 구독 (삼성전자)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0A"]
                }]
            },
            duration=10
        )

        # ===== 테스트 케이스 7: 주식우선호가 구독 (0C) =====
        await self.test_websocket_connection(
            test_name="WS Case 7-1: 주식우선호가 구독 (삼성전자)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0C"]
                }]
            },
            duration=10
        )

        # ===== 테스트 케이스 8: 다양한 grp_no 테스트 =====
        await self.test_websocket_connection(
            test_name="WS Case 8-1: grp_no=99 테스트",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "99",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0B"]
                }]
            },
            duration=5
        )

        await self.test_websocket_connection(
            test_name="WS Case 8-2: grp_no=1234 테스트",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1234",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0B"]
                }]
            },
            duration=5
        )

        # ===== 테스트 케이스 9: data 배열 복수 항목 =====
        await self.test_websocket_connection(
            test_name="WS Case 9-1: data 배열 복수 항목",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [
                    {
                        "item": [self.test_stock],
                        "type": ["0B"]
                    },
                    {
                        "item": [self.test_stock],
                        "type": ["0D"]
                    }
                ]
            },
            duration=10
        )

        print("\n" + "=" * 80)
        print(f"✅ WebSocket 테스트 완료: 총 {len(self.test_results['websocket_tests'])}개")
        successful = sum(1 for r in self.test_results['websocket_tests'] if r.get('success', False))
        connected = sum(1 for r in self.test_results['websocket_tests'] if r.get('connected', False))
        subscribed = sum(1 for r in self.test_results['websocket_tests'] if r.get('subscription_success', False))
        print(f"   성공: {successful}개")
        print(f"   연결 성공: {connected}개")
        print(f"   구독 성공: {subscribed}개")
        print("=" * 80)

    # ================================================================
    # 결과 저장 및 분석
    # ================================================================

    def save_results(self):
        """테스트 결과 저장"""
        filename = f"test_results_{self.test_results['timestamp']}.json"
        filepath = os.path.join(os.path.dirname(__file__), filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 결과 저장: {filepath}")

    def print_summary(self):
        """테스트 결과 요약 출력"""
        self.print_section("테스트 결과 요약")

        # 스코어링 API 성공 케이스
        print("\n📊 스코어링 API - 성공한 케이스:")
        scoring_success = [r for r in self.test_results['scoring_apis'] if r.get('success', False) and r.get('has_data', False)]

        if scoring_success:
            for result in scoring_success:
                print(f"\n  ✅ {result['test_name']}")
                print(f"     API: {result['api_id']}")
                print(f"     데이터 키: {result['data_keys']}")
        else:
            print("  ❌ 성공한 케이스 없음")

        # 스코어링 API 추천 조합
        print("\n\n🎯 스코어링을 위한 추천 API 조합:")
        if scoring_success:
            # API별로 그룹화
            api_groups = {}
            for result in scoring_success:
                api_id = result['api_id']
                if api_id not in api_groups:
                    api_groups[api_id] = []
                api_groups[api_id].append(result)

            for api_id, results in api_groups.items():
                print(f"\n  📌 {api_id}:")
                for result in results:
                    print(f"     - {result['test_name']}")
                    print(f"       Body: {json.dumps(result['body'], ensure_ascii=False)}")

        # WebSocket 성공 케이스
        print("\n\n📡 WebSocket - 성공한 케이스:")
        ws_success = [r for r in self.test_results['websocket_tests'] if r.get('success', False)]

        if ws_success:
            for result in ws_success:
                print(f"\n  ✅ {result['test_name']}")
                print(f"     구독 요청: {json.dumps(result['subscribe_request'], ensure_ascii=False)}")
                print(f"     수신 메시지: {result['messages_received']}개")
        else:
            print("  ❌ 성공한 케이스 없음")

        # WebSocket 부분 성공 케이스
        ws_partial = [r for r in self.test_results['websocket_tests']
                     if not r.get('success', False) and (r.get('connected', False) or r.get('subscription_success', False))]

        if ws_partial:
            print("\n\n⚠️ WebSocket - 부분 성공 케이스 (디버깅 참고):")
            for result in ws_partial:
                print(f"\n  ⚠️ {result['test_name']}")
                print(f"     연결: {'✅' if result['connected'] else '❌'}")
                print(f"     구독: {'✅' if result['subscription_success'] else '❌'}")
                print(f"     수신: {result['messages_received']}개")
                if result.get('error'):
                    print(f"     오류: {result['error']}")

        print("\n" + "=" * 80)
        print("🎉 모든 테스트 완료!")
        print("=" * 80 + "\n")


async def main():
    """메인 함수"""
    print("\n" + "=" * 80)
    print("  종합 데이터 수집 및 WebSocket 연결 테스트")
    print("=" * 80)

    tester = ComprehensiveDataTester()

    try:
        # Part 1: 스코어링 API 테스트
        tester.run_scoring_tests()

        # Part 2: WebSocket 테스트
        await tester.run_websocket_tests()

        # 결과 저장 및 요약
        tester.save_results()
        tester.print_summary()

    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 테스트가 중단되었습니다.")
        tester.save_results()
        tester.print_summary()
    except Exception as e:
        print(f"\n\n❌ 예외 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        tester.save_results()


if __name__ == "__main__":
    asyncio.run(main())
