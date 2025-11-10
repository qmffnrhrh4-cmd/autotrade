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

from config.constants import URLS

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

    def __init__(self, server_url: str = None, auto_connect: bool = True):
        """
        OpenAPI 클라이언트 초기화

        Args:
            server_url: OpenAPI 서버 URL
            auto_connect: 자동 연결 확인 (기본값: True)
        """
        if server_url is None:
            server_url = URLS['openapi_server']
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
        print("🔍 [DEBUG] connect() 함수 시작")  # STDOUT로 직접 출력
        logger.info("📡 OpenAPI 서버 연결 확인 중...")

        # Health check
        result = self._request('GET', '/health')

        # DEBUG: 전체 응답 출력
        print(f"🔍 [DEBUG] Health check response: {result}")  # STDOUT로 직접 출력
        logger.info(f"🔍 Health check response: {result}")

        if result and result.get('status') == 'ok' and result.get('server_ready'):
            logger.info("✅ OpenAPI 서버 응답 확인!")

            # Check if already connected to kiwoom
            connection_status = result.get('connection_status')
            print(f"🔍 [DEBUG] Connection status: {connection_status}")  # STDOUT로 직접 출력
            logger.info(f"🔍 Connection status: {connection_status}")

            if connection_status == 'connected':
                self.is_connected = True
                self.account_list = result.get('accounts', [])
                logger.info("✅ OpenAPI 연결 완료!")
                logger.info(f"📋 계좌 목록: {self.account_list}")
                return True
            elif connection_status == 'connecting':
                logger.info("🔐 OpenAPI 로그인 진행 중...")
                logger.info("   서버에서 로그인 처리 중입니다")
                # 연결 진행 중이므로 나중에 재시도 가능
                return False
            elif connection_status in ['failed', 'timeout']:
                logger.warning(f"⚠️  OpenAPI 연결 실패 (상태: {connection_status})")
                return False
            else:
                logger.info("ℹ️  OpenAPI 서버 준비 중...")
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

    def get_comprehensive_data(self, stock_code: str) -> Dict[str, Any]:
        """
        종목 종합 데이터 조회 (20가지)

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            종합 데이터 딕셔너리
            {
                'stock_code': str,
                'timestamp': str,
                'success_count': int,
                'total_count': int,
                'data': {
                    '01_master': {...},
                    '02_basic': {...},
                    '03_quote': {...},
                    ...
                }
            }
        """
        if not self.is_connected:
            logger.warning("OpenAPI 연결 안 됨")
            return {}

        logger.info(f"📊 종합 데이터 조회: {stock_code}")

        # Timeout을 120초로 설정 (17개 TR * 0.3초 대기 + 여유)
        result = self._request('GET', f'/stock/{stock_code}/comprehensive', timeout=120)

        if result:
            success_count = result.get('success_count', 0)
            total_count = result.get('total_count', 0)
            logger.info(f"✅ 종합 데이터 수신: {success_count}/{total_count}")
            return result
        else:
            logger.error(f"❌ 종합 데이터 조회 실패: {stock_code}")
            return {}

    def get_minute_data(self, stock_code: str, interval: int = 1) -> List[Dict[str, Any]]:
        """
        분봉 데이터 조회 (과거 데이터 포함)

        Args:
            stock_code: 종목코드 (6자리)
            interval: 분봉 간격 (1, 5, 15, 30, 60)

        Returns:
            분봉 데이터 리스트
            [
                {
                    '일자': '20231201',
                    '체결시간': '153000',
                    '현재가': '70000',
                    '시가': '69500',
                    '고가': '70500',
                    '저가': '69000',
                    '거래량': '100000',
                    '등락률': '1.5'
                },
                ...
            ]
        """
        if not self.is_connected:
            logger.warning("OpenAPI 연결 안 됨")
            return []

        # 유효한 interval 체크
        valid_intervals = [1, 5, 15, 30, 60]
        if interval not in valid_intervals:
            logger.error(f"Invalid interval: {interval}. Valid: {valid_intervals}")
            return []

        logger.info(f"📊 분봉 데이터 조회: {stock_code} ({interval}분)")

        # Timeout을 10초로 설정 (분봉 1개 TR)
        result = self._request('GET', f'/stock/{stock_code}/minute/{interval}', timeout=10)

        if result and 'data' in result:
            data = result.get('data', {})
            items = data.get('items', [])

            if items:
                logger.info(f"✅ 분봉 데이터 수신: {len(items)}개")
                return items
            else:
                logger.warning(f"⚠️ 분봉 데이터 없음 (주말/휴일 가능성)")
                return []
        else:
            logger.error(f"❌ 분봉 데이터 조회 실패: {stock_code}")
            return []

    def extract_openapi_features(self, comprehensive_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        종합 데이터에서 스코어링/AI에 필요한 특징 추출

        Args:
            comprehensive_data: get_comprehensive_data() 결과

        Returns:
            추출된 특징 딕셔너리
        """
        features = {}

        if not comprehensive_data or 'data' not in comprehensive_data:
            return features

        data = comprehensive_data.get('data', {})

        # 1. 마스터 정보
        master = data.get('01_master', {})
        if master and 'error' not in master:
            features['stock_name'] = master.get('stock_name', '')
            features['listed_stock_cnt'] = master.get('listed_stock_cnt', 0)

        # 2. 주식기본정보
        basic = data.get('02_basic', {})
        if basic and 'error' not in basic:
            features['current_price_openapi'] = self._parse_int(basic.get('현재가'))
            features['volume_openapi'] = self._parse_int(basic.get('거래량'))
            features['change_rate_openapi'] = self._parse_float(basic.get('등락률'))
            features['market_cap'] = self._parse_int(basic.get('시가총액'))

        # 3. 호가잔량
        quote = data.get('03_quote', {})
        if quote and 'error' not in quote and 'items' in quote:
            items = quote.get('items', [])
            if items:
                # 호가 데이터가 있으면 매수/매도 강도 계산 가능
                features['has_quote_data'] = True

        # 4. 일봉차트
        daily_chart = data.get('04_daily_chart', {})
        if daily_chart and 'error' not in daily_chart and 'items' in daily_chart:
            items = daily_chart.get('items', [])
            if len(items) >= 2:
                # 최근 2일 데이터로 추세 분석
                today = items[0]
                yesterday = items[1]
                features['daily_trend'] = 'up' if self._parse_int(today.get('현재가')) > self._parse_int(yesterday.get('현재가')) else 'down'
                features['daily_volatility'] = self._calculate_volatility(items[:5])

        # 5. 분봉차트
        minute_chart = data.get('05_minute_chart', {})
        if minute_chart and 'error' not in minute_chart and 'items' in minute_chart:
            items = minute_chart.get('items', [])
            if items:
                features['minute_data_count'] = len(items)
                features['recent_price_action'] = self._analyze_price_action(items[:10])

        # 6. 투자자별 매매동향
        investor_trend = data.get('10_investor_trend', {})
        if investor_trend and 'error' not in investor_trend and 'items' in investor_trend:
            items = investor_trend.get('items', [])
            if items:
                latest = items[0]
                features['institutional_net_buy_openapi'] = self._parse_int(latest.get('기관순매수'))
                features['foreign_net_buy_openapi'] = self._parse_int(latest.get('외인순매수'))

        # 7. 프로그램매매
        program_trading = data.get('13_program_trading', {})
        if program_trading and 'error' not in program_trading and 'items' in program_trading:
            items = program_trading.get('items', [])
            if items:
                total_buy = sum(self._parse_int(item.get('매수량')) for item in items)
                total_sell = sum(self._parse_int(item.get('매도량')) for item in items)
                features['program_net_buy'] = total_buy - total_sell

        return features

    def _parse_int(self, value: Any) -> int:
        """문자열을 정수로 변환 (부호, 공백 처리)"""
        if value is None:
            return 0
        try:
            # '+', '-', ' ' 제거 후 변환
            cleaned = str(value).replace('+', '').replace('-', '').replace(' ', '').strip()
            if not cleaned:
                return 0
            # 부호 처리
            sign = -1 if str(value).strip().startswith('-') else 1
            return int(cleaned) * sign
        except:
            return 0

    def _parse_float(self, value: Any) -> float:
        """문자열을 실수로 변환"""
        if value is None:
            return 0.0
        try:
            cleaned = str(value).replace('+', '').replace(' ', '').strip()
            if not cleaned:
                return 0.0
            return float(cleaned)
        except:
            return 0.0

    def _calculate_volatility(self, candles: List[Dict]) -> float:
        """캔들 데이터로 변동성 계산"""
        if not candles or len(candles) < 2:
            return 0.0

        try:
            prices = [self._parse_int(c.get('현재가')) for c in candles if c.get('현재가')]
            if len(prices) < 2:
                return 0.0

            avg_price = sum(prices) / len(prices)
            variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
            volatility = (variance ** 0.5) / avg_price * 100 if avg_price > 0 else 0.0
            return round(volatility, 2)
        except:
            return 0.0

    def _analyze_price_action(self, candles: List[Dict]) -> str:
        """최근 가격 움직임 분석"""
        if not candles or len(candles) < 3:
            return 'neutral'

        try:
            prices = [self._parse_int(c.get('현재가')) for c in candles[:5] if c.get('현재가')]
            if len(prices) < 3:
                return 'neutral'

            # 상승 추세인지 확인
            up_count = sum(1 for i in range(len(prices)-1) if prices[i] > prices[i+1])
            if up_count >= len(prices) * 0.6:
                return 'strong_up'
            elif up_count >= len(prices) * 0.4:
                return 'weak_up'
            elif up_count <= len(prices) * 0.2:
                return 'strong_down'
            elif up_count <= len(prices) * 0.4:
                return 'weak_down'
            else:
                return 'neutral'
        except:
            return 'neutral'

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
