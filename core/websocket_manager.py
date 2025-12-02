"""
core/websocket_manager.py
WebSocket 실시간 시세 매니저

성공 패턴:
1. WebSocket 연결
2. LOGIN 메시지 전송 ({"trnm": "LOGIN", "token": access_token})
3. 로그인 응답 확인
4. 구독 요청 전송 (REG)
5. 실시간 데이터 수신 (REAL)
"""

import asyncio
import websockets
import json
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from utils.logger_new import get_logger
from config.constants import URLS

logger = get_logger()


class WebSocketManager:
    """WebSocket 실시간 시세 매니저"""

    def __init__(self, access_token: str, base_url: str = None):
        """
        WebSocketManager 초기화

        Args:
            access_token: API 액세스 토큰
            base_url: API 베이스 URL
        """
        if base_url is None:
            base_url = URLS['kiwoom_api_base']
        self.access_token = access_token
        self.base_url = base_url

        # WebSocket URL 결정
        if 'mockapi' in base_url:
            self.ws_url = "wss://mockapi.kiwoom.com:10000/api/dostk/websocket"
        else:
            self.ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"

        self.websocket = None
        self.is_connected = False
        self.is_logged_in = False
        self.subscriptions = {}  # {grp_no: subscription_info}
        self.callbacks = {}  # {type: callback_function}

        # 재연결 설정
        self.reconnect_delay = 5  # 재연결 대기 시간 (초)
        self.max_reconnect_attempts = 5
        self.reconnect_attempts = 0

        logger.info(f"WebSocketManager 초기화: {self.ws_url}")

    async def connect(self) -> bool:
        """
        WebSocket 연결

        Returns:
            연결 성공 여부
        """
        try:
            logger.info(f"WebSocket 연결 시도: {self.ws_url}")

            # WebSocket 연결
            self.websocket = await websockets.connect(
                self.ws_url,
                additional_headers={
                    'authorization': f'Bearer {self.access_token}'
                },
                ping_interval=20,
                ping_timeout=10
            )

            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("✅ WebSocket 연결 성공")

            # 로그인 수행
            login_success = await self._login()
            if not login_success:
                logger.error("❌ 로그인 실패")
                await self.disconnect()
                return False

            logger.info("✅ WebSocket 로그인 성공")
            return True

        except Exception as e:
            logger.error(f"❌ WebSocket 연결 실패: {e}")
            self.is_connected = False
            return False

    async def _login(self) -> bool:
        """
        WebSocket 로그인

        Returns:
            로그인 성공 여부
        """
        try:
            # 로그인 메시지 전송
            login_request = {
                "trnm": "LOGIN",
                "token": self.access_token
            }

            await self.websocket.send(json.dumps(login_request))
            logger.info("📤 로그인 요청 전송")

            # 로그인 응답 대기 (최대 3초)
            login_response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=3.0
            )

            login_data = json.loads(login_response)

            if login_data.get('return_code') == 0:
                self.is_logged_in = True
                logger.info(f"✅ 로그인 성공: {login_data.get('return_msg', '')}")
                return True
            else:
                logger.error(f"❌ 로그인 실패 (코드 {login_data.get('return_code')}): {login_data.get('return_msg')}")
                return False

        except asyncio.TimeoutError:
            logger.error("❌ 로그인 응답 타임아웃")
            return False
        except Exception as e:
            logger.error(f"❌ 로그인 중 오류: {e}")
            return False

    async def subscribe(
        self,
        stock_codes: List[str],
        types: List[str],
        grp_no: str = "1",
        refresh: str = "1"
    ) -> bool:
        """
        실시간 시세 구독

        Args:
            stock_codes: 종목코드 리스트 (예: ["005930", "000660"])
            types: 구독 타입 리스트 (예: ["0B", "0D"])
            grp_no: 그룹 번호
            refresh: 기존 구독 유지 여부 (0: 유지 안 함, 1: 유지)

        Returns:
            구독 성공 여부

        구독 타입:
            00: 주문체결
            04: 잔고
            0A: 주식기세
            0B: 주식체결
            0C: 주식우선호가
            0D: 주식호가잔량
        """
        if not self.is_connected or not self.is_logged_in:
            logger.error("❌ WebSocket 미연결 또는 미로그인")
            return False

        try:
            subscribe_request = {
                "trnm": "REG",
                "grp_no": grp_no,
                "refresh": refresh,
                "data": [{
                    "item": stock_codes,
                    "type": types
                }]
            }

            await self.websocket.send(json.dumps(subscribe_request))
            logger.info(f"📤 구독 요청 전송: 종목={stock_codes}, 타입={types}, grp_no={grp_no}")

            # 구독 응답 대기 (최대 2초)
            subscribe_response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=2.0
            )

            subscribe_data = json.loads(subscribe_response)

            if subscribe_data.get('return_code') == 0:
                # 구독 정보 저장
                self.subscriptions[grp_no] = {
                    'stock_codes': stock_codes,
                    'types': types,
                    'refresh': refresh,
                    'subscribed_at': datetime.now()
                }
                logger.info(f"✅ 구독 성공: {subscribe_data.get('return_msg', '')}")
                return True
            else:
                logger.error(f"❌ 구독 실패 (코드 {subscribe_data.get('return_code')}): {subscribe_data.get('return_msg')}")
                return False

        except asyncio.TimeoutError:
            logger.warning("⚠️ 구독 응답 타임아웃 (구독은 성공했을 수 있음)")
            # 구독 정보는 저장
            self.subscriptions[grp_no] = {
                'stock_codes': stock_codes,
                'types': types,
                'refresh': refresh,
                'subscribed_at': datetime.now()
            }
            return True
        except Exception as e:
            logger.error(f"❌ 구독 중 오류: {e}")
            return False

    def register_callback(self, data_type: str, callback: Callable[[Dict[str, Any]], None]):
        """
        실시간 데이터 콜백 등록

        Args:
            data_type: 데이터 타입 (예: '0B', '0D', 'ALL')
            callback: 콜백 함수 (data를 인자로 받음)
        """
        self.callbacks[data_type] = callback
        logger.info(f"콜백 등록: {data_type}")

    async def receive_loop(self):
        """
        실시간 데이터 수신 루프

        무한 루프로 실행되며, 데이터 수신 시 콜백 호출
        """
        if not self.is_connected or not self.is_logged_in:
            logger.error("❌ WebSocket 미연결 또는 미로그인")
            return

        logger.info("🔄 실시간 데이터 수신 시작")

        try:
            message_count = 0
            while self.is_connected:
                try:
                    # 메시지 수신 (타임아웃 1초)
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=1.0
                    )

                    message_count += 1
                    # JSON 파싱
                    data = json.loads(message)
                    trnm = data.get('trnm', '')


                    # REAL 데이터인 경우 콜백 호출
                    if trnm == 'REAL':
                        await self._handle_real_data(data)
                    elif trnm == 'SYSTEM':
                        # 시스템 메시지
                        code = data.get('code', '')
                        msg = data.get('message', '')
                        logger.warning(f"⚠️ 시스템 메시지 (코드 {code}): {msg}")

                        # 연결 종료 메시지인 경우 재연결 시도
                        if code == 'R10004':
                            logger.error("❌ 접속 종료됨, 재연결 시도...")
                            await self.reconnect()
                    else:
                        # 기타 메시지
                        logger.debug(f"기타 메시지: {trnm}")

                except asyncio.TimeoutError:
                    # 타임아웃은 정상 (계속 수신 대기)
                    continue
                except websockets.ConnectionClosed:
                    logger.error("❌ WebSocket 연결 끊김")
                    self.is_connected = False
                    await self.reconnect()
                    break
                except Exception as e:
                    logger.error(f"❌ 메시지 수신 중 오류: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ 수신 루프 중 오류: {e}")
        finally:
            logger.info("🔄 실시간 데이터 수신 종료")

    async def _handle_real_data(self, data: Dict[str, Any]):
        """
        REAL 데이터 처리 및 콜백 호출

        Args:
            data: REAL 데이터
        """
        try:
            # data 구조:
            # {
            #   "trnm": "REAL",
            #   "data": [{
            #       "type": "0B",
            #       "name": "주식체결",
            #       "item": "005930",
            #       "values": {...}
            #   }]
            # }

            data_list = data.get('data', [])
            for item in data_list:
                data_type = item.get('type', '')
                stock_code = item.get('item', '')
                values = item.get('values', {})

                # 타입별 콜백 호출
                if data_type in self.callbacks:
                    try:
                        await self.callbacks[data_type](item)
                    except Exception as e:
                        logger.error(f"❌ 콜백 실행 오류 ({data_type}): {e}")

                # ALL 콜백 호출
                if 'ALL' in self.callbacks:
                    try:
                        await self.callbacks['ALL'](item)
                    except Exception as e:
                        logger.error(f"❌ ALL 콜백 실행 오류: {e}")

        except Exception as e:
            logger.error(f"❌ REAL 데이터 처리 중 오류: {e}")

    async def reconnect(self):
        """WebSocket 재연결"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"❌ 최대 재연결 시도 횟수 초과 ({self.max_reconnect_attempts})")
            return

        self.reconnect_attempts += 1
        logger.info(f"🔄 재연결 시도 {self.reconnect_attempts}/{self.max_reconnect_attempts}")

        # 기존 연결 종료
        await self.disconnect()

        # 대기
        await asyncio.sleep(self.reconnect_delay)

        # 재연결
        success = await self.connect()
        if success:
            # 기존 구독 재등록
            for grp_no, sub_info in self.subscriptions.items():
                await self.subscribe(
                    stock_codes=sub_info['stock_codes'],
                    types=sub_info['types'],
                    grp_no=grp_no,
                    refresh=sub_info['refresh']
                )

    async def disconnect(self):
        """WebSocket 연결 종료"""
        try:
            if self.websocket:
                await self.websocket.close()
                logger.info("WebSocket 연결 종료")
        except Exception as e:
            logger.error(f"연결 종료 중 오류: {e}")
        finally:
            self.is_connected = False
            self.is_logged_in = False
            self.websocket = None

    async def unsubscribe(self, grp_no: str) -> bool:
        """
        구독 해지

        Args:
            grp_no: 그룹 번호

        Returns:
            해지 성공 여부
        """
        if not self.is_connected or not self.is_logged_in:
            logger.error("❌ WebSocket 미연결 또는 미로그인")
            return False

        try:
            unsubscribe_request = {
                "trnm": "REMOVE",
                "grp_no": grp_no
            }

            await self.websocket.send(json.dumps(unsubscribe_request))
            logger.info(f"📤 구독 해지 요청 전송: grp_no={grp_no}")

            # 구독 정보 삭제
            if grp_no in self.subscriptions:
                del self.subscriptions[grp_no]

            return True

        except Exception as e:
            logger.error(f"❌ 구독 해지 중 오류: {e}")
            return False

    def get_subscription_info(self) -> Dict[str, Any]:
        """
        현재 구독 정보 반환

        Returns:
            구독 정보 딕셔너리
        """
        return {
            'connected': self.is_connected,
            'logged_in': self.is_logged_in,
            'subscriptions': self.subscriptions,
            'ws_url': self.ws_url
        }


async def test_websocket():
    """WebSocketManager 테스트"""
    from core.rest_client import KiwoomRESTClient


    # REST 클라이언트 초기화
    rest_client = KiwoomRESTClient()
    access_token = rest_client.token
    base_url = rest_client.base_url


    # WebSocketManager 초기화
    ws_manager = WebSocketManager(access_token, base_url)

    # 콜백 등록
    async def on_price_data(data):
        """체결 데이터 콜백"""
        stock_code = data.get('item', '')
        values = data.get('values', {})
        price = values.get('10', '0')  # 현재가

    async def on_orderbook_data(data):
        """호가 데이터 콜백"""
        stock_code = data.get('item', '')
        values = data.get('values', {})
        sell_price = values.get('27', '0')  # 매도호가
        buy_price = values.get('28', '0')   # 매수호가

    ws_manager.register_callback('0B', on_price_data)      # 주식체결
    ws_manager.register_callback('0D', on_orderbook_data)  # 주식호가잔량

    try:
        # 연결
        success = await ws_manager.connect()
        if not success:
            return

        # 구독 - 더 많은 종목으로 테스트
        stock_codes = ["005930", "000660", "035720", "051910", "035420"]  # 삼성전자, SK하이닉스, 카카오, LG화학, NAVER
        success = await ws_manager.subscribe(
            stock_codes=stock_codes,
            types=["0B", "0D"],      # 체결 + 호가
            grp_no="1"
        )
        if not success:
            return


        # 실시간 데이터 수신 (30초)
        await asyncio.wait_for(ws_manager.receive_loop(), timeout=30.0)

    except asyncio.TimeoutError:
    except KeyboardInterrupt:
    finally:
        # 연결 종료
        await ws_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(test_websocket())
