"""
WebSocket 전용 테스트
다양한 WebSocket 구독 조건을 테스트하여 정답을 찾습니다.

🎯 테스트 목표:
  1. 다양한 실시간 데이터 구독 패턴 테스트
  2. 로그인/인증 방식 검증
  3. grp_no, refresh 파라미터 조합 테스트
  4. 복수 종목 구독 테스트

✅ 검증된 WebSocket 패턴:
  - 주문체결 (type=00): 내 주문 체결 정보
  - 주식체결 (type=0B): 실시간 종목 체결가
  - 주식호가 (type=0D): 실시간 호가 정보
  - 주식기세 (type=0A): 체결강도 등 시세 정보

실행 방법:
    python tests/manual_tests/test_websocket_only.py

결과:
    - 각 테스트 케이스별 연결/구독 성공 여부
    - 수신된 실시간 메시지 샘플
    - 자동으로 _test_results/ 디렉토리에 JSON 저장

주의:
    - 실제 WebSocket 연결이 발생합니다
    - 일부 테스트는 5-10초 소요됩니다
    - 비거래 시간에는 실시간 데이터가 없을 수 있습니다
"""

import sys
import os
from datetime import datetime
import json
import asyncio
import websockets
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.rest_client import KiwoomRESTClient


class WebSocketTester:
    """WebSocket 전용 테스터"""

    def __init__(self):
        """테스터 초기화"""
        self.rest_client = KiwoomRESTClient()
        self.test_stock = "005930"  # 삼성전자
        self.test_results = {
            'websocket_tests': [],
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'summary': {
                'total': 0,
                'connected': 0,
                'subscription_success': 0,
                'received_messages': 0
            }
        }

        # 토큰 추출
        self.access_token = self.rest_client.token if hasattr(self.rest_client, 'token') else ''
        self.base_url = self.rest_client.base_url

        # WebSocket URL 결정
        if 'mockapi' in self.base_url:
            self.ws_url = "wss://mockapi.kiwoom.com:10000/api/dostk/websocket"
        else:
            self.ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"

        print(f"\n{'='*80}")
        print(f"  WebSocket 전용 테스트")
        print(f"{'='*80}")
        print(f"WebSocket URL: {self.ws_url}")
        print(f"테스트 종목: {self.test_stock} (삼성전자)")
        print(f"{'='*80}\n")

    async def test_websocket(
        self,
        test_name: str,
        subscribe_request: dict,
        duration: int = 5,
        expected_response_type: str = None,
        login_request: dict = None
    ) -> dict:
        """
        WebSocket 연결 및 구독 테스트

        Args:
            test_name: 테스트 이름
            subscribe_request: 구독 요청 메시지
            duration: 테스트 대기 시간 (초)
            expected_response_type: 예상 응답 타입 (예: 'REG', 'REAL')
            login_request: 로그인 요청 메시지 (선택)

        Returns:
            테스트 결과
        """
        print(f"\n{'─'*80}")
        print(f"🧪 {test_name}")
        print(f"{'─'*80}")
        if login_request:
            print(f"로그인 요청: {json.dumps(login_request, ensure_ascii=False, indent=2)}")
        print(f"구독 요청: {json.dumps(subscribe_request, ensure_ascii=False, indent=2)}")

        result = {
            'test_name': test_name,
            'login_request': login_request,
            'subscribe_request': subscribe_request,
            'expected_response_type': expected_response_type,
            'success': False,
            'connected': False,
            'login_success': False,
            'subscription_success': False,
            'messages_received': 0,
            'error': None,
            'sample_messages': [],
            'response_types': []
        }

        try:
            # WebSocket 연결 (Python 3.13+ 호환)
            async with websockets.connect(
                self.ws_url,
                additional_headers={
                    'authorization': f'Bearer {self.access_token}'
                },
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                result['connected'] = True
                print(f"✅ WebSocket 연결 성공")

                # 로그인/인증 메시지 전송 (있는 경우)
                if login_request:
                    login_json = json.dumps(login_request)
                    await websocket.send(login_json)
                    print(f"📤 로그인 요청 전송 완료")

                    # 로그인 응답 대기 (짧게 1초)
                    try:
                        login_response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        login_data = json.loads(login_response)
                        result['messages_received'] += 1

                        if len(result['sample_messages']) < 5:
                            result['sample_messages'].append(login_data)

                        msg_type = login_data.get('trnm', 'UNKNOWN')
                        if msg_type not in result['response_types']:
                            result['response_types'].append(msg_type)

                        if login_data.get('return_code') == 0:
                            result['login_success'] = True
                            print(f"✅ 로그인 성공: {login_data.get('return_msg', '')}")
                        else:
                            print(f"⚠️  로그인 응답 - 코드 {login_data.get('return_code')}: {login_data.get('return_msg', '')}")
                    except asyncio.TimeoutError:
                        print(f"⚠️  로그인 응답 없음 (타임아웃)")
                    except Exception as e:
                        print(f"⚠️  로그인 응답 처리 오류: {e}")

                # 구독 요청 전송
                subscribe_json = json.dumps(subscribe_request)
                await websocket.send(subscribe_json)
                print(f"📤 구독 요청 전송 완료")

                # 응답 대기 및 수집
                start_time = time.time()
                while time.time() - start_time < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)

                        # JSON 파싱
                        try:
                            data = json.loads(message)
                        except json.JSONDecodeError:
                            print(f"⚠️  JSON 파싱 실패: {message[:100]}...")
                            continue

                        result['messages_received'] += 1
                        msg_type = data.get('trnm', 'UNKNOWN')

                        # 응답 타입 추적
                        if msg_type not in result['response_types']:
                            result['response_types'].append(msg_type)

                        # 처음 5개 메시지만 샘플로 저장
                        if len(result['sample_messages']) < 5:
                            result['sample_messages'].append(data)

                        # 구독 응답 확인 (다양한 패턴)
                        if msg_type == 'REG':
                            return_code = data.get('return_code')
                            if return_code == 0:
                                result['subscription_success'] = True
                                print(f"✅ 구독 성공 (REG): {data.get('return_msg', '')}")
                            else:
                                print(f"⚠️  구독 응답 (REG) - 코드 {return_code}: {data.get('return_msg', '')}")

                        # 실시간 데이터 수신 확인
                        elif msg_type == 'REAL':
                            if result['messages_received'] == 1 or result['messages_received'] % 10 == 0:
                                print(f"📨 실시간 데이터 수신 (REAL) - 총 {result['messages_received']}개")
                                if result['messages_received'] <= 3:
                                    print(f"   샘플: {json.dumps(data, ensure_ascii=False)[:150]}...")

                        # 기타 응답
                        else:
                            print(f"📩 응답 수신 ({msg_type}): {json.dumps(data, ensure_ascii=False)[:150]}...")

                    except asyncio.TimeoutError:
                        # 타임아웃은 정상 (메시지 없을 수 있음)
                        continue
                    except Exception as e:
                        print(f"⚠️  메시지 수신 오류: {str(e)}")
                        break

                # 결과 판정
                # 로그인이 필요한 경우: 연결 AND 로그인 AND (구독 성공 OR 메시지 수신)
                # 로그인 없는 경우: 연결 AND (구독 성공 OR 메시지 수신)
                if login_request:
                    result['success'] = result['connected'] and result['login_success'] and (
                        result['subscription_success'] or result['messages_received'] > 1  # 로그인 응답 제외
                    )
                else:
                    result['success'] = result['connected'] and (
                        result['subscription_success'] or result['messages_received'] > 0
                    )

                # 결과 출력
                print(f"\n{'─'*80}")
                if result['success']:
                    print(f"✅ 테스트 성공")
                else:
                    print(f"⚠️  테스트 부분 성공")

                print(f"   연결: {'✅' if result['connected'] else '❌'}")
                if login_request:
                    print(f"   로그인: {'✅' if result['login_success'] else '❌'}")
                print(f"   구독 성공: {'✅' if result['subscription_success'] else '❌'}")
                print(f"   수신 메시지: {result['messages_received']}개")
                print(f"   응답 타입: {', '.join(result['response_types'])}")
                print(f"{'─'*80}")

        except Exception as e:
            result['error'] = str(e)
            print(f"\n{'─'*80}")
            print(f"❌ 테스트 실패: {str(e)}")
            print(f"{'─'*80}")

        self.test_results['websocket_tests'].append(result)
        return result

    async def run_all_tests(self):
        """모든 WebSocket 테스트 실행"""
        print(f"\n{'='*80}")
        print(f"  WebSocket 테스트 시작")
        print(f"{'='*80}\n")

        # ===== 카테고리 0: 로그인 패턴 테스트 =====
        print(f"\n{'='*80}")
        print(f"📦 카테고리 0: 로그인/인증 패턴 테스트")
        print(f"{'='*80}")

        # 다양한 로그인 메시지 패턴 시도
        login_patterns = [
            {"trnm": "LOGIN", "token": self.access_token},
            {"trnm": "AUTH", "token": self.access_token},
            {"trnm": "CON", "token": self.access_token},
            {"trnm": "CONN", "token": self.access_token},
            {"trnm": "CONNECT", "token": self.access_token},
            {"trnm": "REG", "token": self.access_token, "grp_no": "0"},
            {"token": self.access_token},  # trnm 없이
        ]

        for idx, login_pattern in enumerate(login_patterns, 1):
            await self.test_websocket(
                test_name=f"Case 0-{idx}: 로그인 패턴 - {json.dumps(login_pattern, ensure_ascii=False)}",
                login_request=login_pattern,
                subscribe_request={
                    "trnm": "REG",
                    "grp_no": "1",
                    "refresh": "1",
                    "data": [{
                        "item": [self.test_stock],
                        "type": ["0B"]
                    }]
                },
                duration=8,
                expected_response_type='REAL'
            )

        # ===== 카테고리 1: 주문/체결 관련 =====
        print(f"\n{'='*80}")
        print(f"📦 카테고리 1: 주문/체결 구독 (로그인 없이)")
        print(f"{'='*80}")

        await self.test_websocket(
            test_name="Case 1-1: 주문체결 구독 (type=00, refresh=1)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [""],
                    "type": ["00"]
                }]
            },
            duration=5,
            expected_response_type='REG'
        )

        await self.test_websocket(
            test_name="Case 1-2: 잔고 구독 (type=04)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [""],
                    "type": ["04"]
                }]
            },
            duration=5,
            expected_response_type='REG'
        )

        # ===== 카테고리 2: 실시간 시세 (단일 종목) =====
        print(f"\n{'='*80}")
        print(f"📦 카테고리 2: 실시간 시세 구독 (단일 종목)")
        print(f"{'='*80}")

        await self.test_websocket(
            test_name="Case 2-1: 주식체결 (type=0B, 삼성전자)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0B"]
                }]
            },
            duration=10,
            expected_response_type='REAL'
        )

        await self.test_websocket(
            test_name="Case 2-2: 주식호가잔량 (type=0D, 삼성전자)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0D"]
                }]
            },
            duration=10,
            expected_response_type='REAL'
        )

        await self.test_websocket(
            test_name="Case 2-3: 주식기세 (type=0A, 삼성전자)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0A"]
                }]
            },
            duration=10,
            expected_response_type='REAL'
        )

        await self.test_websocket(
            test_name="Case 2-4: 주식우선호가 (type=0C, 삼성전자)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0C"]
                }]
            },
            duration=10,
            expected_response_type='REAL'
        )

        # ===== 카테고리 3: 복수 구독 =====
        print(f"\n{'='*80}")
        print(f"📦 카테고리 3: 복수 항목 구독")
        print(f"{'='*80}")

        await self.test_websocket(
            test_name="Case 3-1: 체결+호가 동시 구독 (0B+0D, type 배열)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0B", "0D"]
                }]
            },
            duration=10,
            expected_response_type='REAL'
        )

        await self.test_websocket(
            test_name="Case 3-2: 체결+호가 동시 구독 (data 배열 분리)",
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
            duration=10,
            expected_response_type='REAL'
        )

        await self.test_websocket(
            test_name="Case 3-3: 복수 종목 구독 (삼성전자+SK하이닉스)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock, "000660"],
                    "type": ["0B"]
                }]
            },
            duration=10,
            expected_response_type='REAL'
        )

        # ===== 카테고리 4: refresh 파라미터 테스트 =====
        print(f"\n{'='*80}")
        print(f"📦 카테고리 4: refresh 파라미터 테스트")
        print(f"{'='*80}")

        await self.test_websocket(
            test_name="Case 4-1: refresh=0 (갱신 안 함)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "0",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0B"]
                }]
            },
            duration=8,
            expected_response_type='REAL'
        )

        await self.test_websocket(
            test_name="Case 4-2: refresh=1 (갱신 함)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [self.test_stock],
                    "type": ["0B"]
                }]
            },
            duration=8,
            expected_response_type='REAL'
        )

        # ===== 카테고리 5: grp_no 다양한 값 테스트 =====
        print(f"\n{'='*80}")
        print(f"📦 카테고리 5: grp_no 파라미터 테스트")
        print(f"{'='*80}")

        for grp_no in ["1", "2", "10", "99", "100", "1234"]:
            await self.test_websocket(
                test_name=f"Case 5-{grp_no}: grp_no={grp_no}",
                subscribe_request={
                    "trnm": "REG",
                    "grp_no": grp_no,
                    "refresh": "1",
                    "data": [{
                        "item": [self.test_stock],
                        "type": ["0B"]
                    }]
                },
                duration=5,
                expected_response_type='REAL'
            )

        # ===== 카테고리 6: item 빈 값 테스트 =====
        print(f"\n{'='*80}")
        print(f"📦 카테고리 6: item 빈 값 테스트")
        print(f"{'='*80}")

        await self.test_websocket(
            test_name="Case 6-1: item=빈문자열 (주식체결)",
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

        await self.test_websocket(
            test_name="Case 6-2: item=빈배열 (주식체결)",
            subscribe_request={
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{
                    "item": [],
                    "type": ["0B"]
                }]
            },
            duration=5
        )

    def print_summary(self):
        """테스트 결과 요약 출력"""
        print(f"\n{'='*80}")
        print(f"  테스트 결과 요약")
        print(f"{'='*80}\n")

        total = len(self.test_results['websocket_tests'])
        connected = sum(1 for r in self.test_results['websocket_tests'] if r.get('connected', False))
        login_success = sum(1 for r in self.test_results['websocket_tests'] if r.get('login_success', False))
        subscription_success = sum(1 for r in self.test_results['websocket_tests'] if r.get('subscription_success', False))
        success = sum(1 for r in self.test_results['websocket_tests'] if r.get('success', False))
        total_messages = sum(r.get('messages_received', 0) for r in self.test_results['websocket_tests'])

        self.test_results['summary'] = {
            'total': total,
            'connected': connected,
            'login_success': login_success,
            'subscription_success': subscription_success,
            'success': success,
            'received_messages': total_messages
        }

        print(f"총 테스트: {total}개")
        print(f"연결 성공: {connected}개 ({connected/total*100:.1f}%)")
        print(f"로그인 성공: {login_success}개")
        print(f"구독 성공: {subscription_success}개 ({subscription_success/total*100:.1f}%)")
        print(f"전체 성공: {success}개 ({success/total*100:.1f}%)")
        print(f"총 수신 메시지: {total_messages}개")

        # 성공한 케이스
        print(f"\n{'─'*80}")
        print(f"✅ 성공한 케이스:")
        print(f"{'─'*80}")
        success_cases = [r for r in self.test_results['websocket_tests'] if r.get('success', False)]
        if success_cases:
            for result in success_cases:
                print(f"\n  ✅ {result['test_name']}")
                print(f"     구독 요청: {json.dumps(result['subscribe_request'], ensure_ascii=False)}")
                print(f"     수신: {result['messages_received']}개 메시지")
                print(f"     응답 타입: {', '.join(result['response_types'])}")
        else:
            print("  없음")

        # 실패한 케이스
        print(f"\n{'─'*80}")
        print(f"❌ 실패한 케이스:")
        print(f"{'─'*80}")
        failed_cases = [r for r in self.test_results['websocket_tests'] if not r.get('success', False)]
        if failed_cases:
            for result in failed_cases:
                print(f"\n  ❌ {result['test_name']}")
                print(f"     연결: {'✅' if result['connected'] else '❌'}")
                if result.get('login_request'):
                    print(f"     로그인: {'✅' if result['login_success'] else '❌'}")
                print(f"     구독: {'✅' if result['subscription_success'] else '❌'}")
                print(f"     수신: {result['messages_received']}개")
                if result.get('error'):
                    print(f"     오류: {result['error']}")
        else:
            print("  없음")

        print(f"\n{'='*80}")

    def save_results(self):
        """테스트 결과 저장"""
        filename = f"websocket_test_results_{self.test_results['timestamp']}.json"
        filepath = os.path.join(os.path.dirname(__file__), filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 결과 저장: {filepath}")


async def main():
    """메인 함수"""
    tester = WebSocketTester()

    try:
        # 모든 테스트 실행
        await tester.run_all_tests()

        # 결과 요약 및 저장
        tester.print_summary()
        tester.save_results()

        print(f"\n{'='*80}")
        print(f"🎉 모든 테스트 완료!")
        print(f"{'='*80}\n")

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
