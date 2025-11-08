"""
OpenAPI Client (HTTP-based)
===========================
HTTP 클라이언트로 32비트 OpenAPI 서버와 통신합니다.

Architecture:
- This client runs in 64-bit Python (main.py)
- Communicates with openapi_server.py (32-bit) via HTTP
- openapi_server.py handles actual koapy/OpenAPI calls

Usage:
    client = KiwoomOpenAPIClient(auto_connect=True)
    accounts = client.get_account_list()
"""
import logging
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class KiwoomOpenAPIClient:
    """
    키움 OpenAPI+ HTTP 클라이언트

    32비트 OpenAPI 서버(openapi_server.py)와 HTTP로 통신합니다.

    주요 기능:
    - 자동 연결 확인
    - 계좌 조회
    - 주문 실행 (매수/매도)
    - 잔고 조회
    - 실시간 시세
    """

    def __init__(self, server_url: str = "http://127.0.0.1:5001", auto_connect: bool = True):
        """
        OpenAPI 클라이언트 초기화

        Args:
            server_url: OpenAPI 서버 URL (기본값: http://127.0.0.1:5001)
            auto_connect: 자동 연결 확인 (기본값: True)
        """
        self.server_url = server_url.rstrip('/')
        self.is_connected = False
        self.account_list = []
        self.timeout = 30  # HTTP timeout in seconds

        logger.info("🔧 OpenAPI HTTP 클라이언트 초기화...")
        logger.info(f"   서버 URL: {self.server_url}")

        if auto_connect:
            self.connect()

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        HTTP 요청 헬퍼

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/health')
            **kwargs: requests 라이브러리 인자

        Returns:
            응답 JSON 딕셔너리 또는 None
        """
        url = f"{self.server_url}{endpoint}"

        try:
            if 'timeout' not in kwargs:
                kwargs['timeout'] = self.timeout

            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError:
            logger.error(f"❌ OpenAPI 서버 연결 실패: {url}")
            logger.error("   서버가 실행 중인지 확인하세요 (openapi_server.py)")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"❌ 요청 시간 초과: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP 에러: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 요청 실패: {e}")
            return None

    def connect(self) -> bool:
        """
        OpenAPI 서버 연결 확인

        Returns:
            연결 성공 여부
        """
        logger.info("📡 OpenAPI 서버 연결 확인 중...")

        # Health check
        result = self._request('GET', '/health')

        if result and result.get('status') == 'ok' and result.get('server_ready'):
            logger.info("✅ OpenAPI 서버 응답 확인!")

            # Check if already connected to koapy
            if result.get('openapi_connected', False):
                self.is_connected = True
                self.account_list = result.get('accounts', [])
                logger.info("✅ OpenAPI 이미 연결됨!")
                logger.info(f"📋 계좌 목록: {self.account_list}")
                return True
            else:
                logger.info("🔐 OpenAPI 연결 시작...")
                logger.info("   (로그인 창이 나타나면 로그인하세요, 최대 60초 대기)")

                # Start connection (async)
                connect_result = self._request('POST', '/connect', timeout=5)
                if not connect_result:
                    logger.error("❌ 연결 시작 실패")
                    return False

                # Poll for connection status (max 60 seconds)
                import time
                max_wait = 60
                poll_interval = 2
                elapsed = 0

                while elapsed < max_wait:
                    time.sleep(poll_interval)
                    elapsed += poll_interval

                    try:
                        status_result = self._request('GET', '/health', timeout=5)
                        if status_result:
                            status = status_result.get('connection_status')

                            if status == 'connected':
                                self.is_connected = True
                                self.account_list = status_result.get('accounts', [])
                                logger.info("✅ OpenAPI 연결 성공!")
                                logger.info(f"📋 계좌 목록: {self.account_list}")
                                return True
                            elif status in ['failed', 'timeout']:
                                logger.error(f"❌ OpenAPI 연결 실패 (상태: {status})")
                                return False
                            elif status == 'connecting':
                                if elapsed % 10 == 0:  # 10초마다 로그
                                    logger.info(f"   대기 중... ({elapsed}초)")
                                continue
                    except Exception as e:
                        # Timeout or connection error during polling - ignore and retry
                        if elapsed % 10 == 0:
                            logger.info(f"   연결 대기 중... ({elapsed}초)")
                        continue

                logger.error("❌ 연결 시간 초과 (60초)")
                logger.error("   로그인을 완료했는지 확인하세요")
                return False
        else:
            logger.error("❌ OpenAPI 서버 응답 없음")
            logger.error("   서버가 시작되지 않았거나 응답하지 않습니다")
            return False

    def disconnect(self):
        """OpenAPI 서버 연결 해제 (서버는 계속 실행)"""
        self.is_connected = False
        logger.info("🔌 OpenAPI 클라이언트 연결 해제")

    def shutdown_server(self):
        """OpenAPI 서버 종료"""
        logger.info("🛑 OpenAPI 서버 종료 요청...")
        result = self._request('POST', '/shutdown')
        if result:
            logger.info("✅ OpenAPI 서버 종료됨")
        else:
            logger.warning("⚠️  서버 종료 실패 (이미 종료되었을 수 있음)")

    def get_account_list(self) -> List[str]:
        """
        계좌 목록 조회

        Returns:
            계좌 번호 리스트
        """
        if not self.is_connected:
            logger.warning("OpenAPI 연결 안 됨")
            return []

        result = self._request('GET', '/accounts')
        if result:
            return result.get('accounts', [])
        return []

    def get_balance(self, account_no: Optional[str] = None) -> Dict[str, Any]:
        """
        계좌 잔고 조회

        Args:
            account_no: 계좌번호 (None이면 첫 번째 계좌)

        Returns:
            잔고 정보 딕셔너리
        """
        if not self.is_connected:
            logger.warning("OpenAPI 연결 안 됨")
            return {}

        if account_no is None:
            accounts = self.get_account_list()
            if not accounts:
                logger.error("사용 가능한 계좌 없음")
                return {}
            account_no = accounts[0]

        result = self._request('GET', f'/balance/{account_no}')
        return result if result else {}

    def get_holdings(self, account_no: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        보유 종목 조회

        Args:
            account_no: 계좌번호 (None이면 첫 번째 계좌)

        Returns:
            보유 종목 리스트
        """
        balance = self.get_balance(account_no)
        return balance.get('positions', [])

    def buy_market_order(
        self,
        stock_code: str,
        quantity: int,
        account_no: Optional[str] = None
    ) -> Optional[str]:
        """
        시장가 매수 주문

        Args:
            stock_code: 종목코드 (6자리)
            quantity: 수량
            account_no: 계좌번호 (None이면 첫 번째 계좌)

        Returns:
            주문번호 (실패 시 None)
        """
        if not self.is_connected:
            logger.warning("OpenAPI 연결 안 됨")
            return None

        if account_no is None:
            accounts = self.get_account_list()
            if not accounts:
                return None
            account_no = accounts[0]

        logger.info(f"📈 시장가 매수 주문: {stock_code} x {quantity}주")

        result = self._request('POST', '/order', json={
            'account_no': account_no,
            'code': stock_code,
            'qty': quantity,
            'order_type': 'market',
            'side': 'buy'
        })

        if result and result.get('success'):
            order_id = result.get('order_id')
            logger.info(f"✅ 매수 주문 성공: 주문번호 {order_id}")
            return order_id
        else:
            logger.error("❌ 매수 주문 실패")
            return None

    def sell_market_order(
        self,
        stock_code: str,
        quantity: int,
        account_no: Optional[str] = None
    ) -> Optional[str]:
        """
        시장가 매도 주문

        Args:
            stock_code: 종목코드 (6자리)
            quantity: 수량
            account_no: 계좌번호 (None이면 첫 번째 계좌)

        Returns:
            주문번호 (실패 시 None)
        """
        if not self.is_connected:
            logger.warning("OpenAPI 연결 안 됨")
            return None

        if account_no is None:
            accounts = self.get_account_list()
            if not accounts:
                return None
            account_no = accounts[0]

        logger.info(f"📉 시장가 매도 주문: {stock_code} x {quantity}주")

        result = self._request('POST', '/order', json={
            'account_no': account_no,
            'code': stock_code,
            'qty': quantity,
            'order_type': 'market',
            'side': 'sell'
        })

        if result and result.get('success'):
            order_id = result.get('order_id')
            logger.info(f"✅ 매도 주문 성공: 주문번호 {order_id}")
            return order_id
        else:
            logger.error("❌ 매도 주문 실패")
            return None

    def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """
        종목 정보 조회 (실시간 가격)

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            종목 정보 딕셔너리
        """
        if not self.is_connected:
            logger.warning("OpenAPI 연결 안 됨")
            return {}

        result = self._request('GET', f'/realtime/price/{stock_code}')
        return result if result else {}

    def __enter__(self):
        """Context manager 진입"""
        if not self.is_connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.disconnect()
        return False

    def __del__(self):
        """소멸자"""
        self.disconnect()


# 싱글톤 인스턴스
_openapi_client_instance = None


def get_openapi_client(auto_connect: bool = True) -> Optional[KiwoomOpenAPIClient]:
    """
    OpenAPI 클라이언트 싱글톤 인스턴스 반환

    Args:
        auto_connect: 자동 연결 여부

    Returns:
        OpenAPI 클라이언트 인스턴스 (연결 실패 시 None)
    """
    global _openapi_client_instance

    if _openapi_client_instance is None:
        _openapi_client_instance = KiwoomOpenAPIClient(auto_connect=auto_connect)
        if not _openapi_client_instance.is_connected:
            logger.warning("⚠️  OpenAPI 서버 연결 실패 - 일부 기능 비활성화")
            # 연결 실패해도 인스턴스는 반환 (나중에 재연결 가능)

    return _openapi_client_instance
