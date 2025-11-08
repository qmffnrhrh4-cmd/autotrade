"""
OpenAPI Client using koapy
키움증권 OpenAPI+ 클라이언트 (32비트 자동매매용)

koapy를 사용하여 키움 OpenAPI+ 연결 및 자동매매를 수행합니다.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class KiwoomOpenAPIClient:
    """
    키움 OpenAPI+ 클라이언트

    koapy를 사용하여 32비트 OpenAPI+ 서버와 통신합니다.

    주요 기능:
    - 자동 로그인
    - 계좌 조회
    - 주문 실행 (매수/매도)
    - 잔고 조회
    - 체결 내역 조회
    """

    def __init__(self, auto_login: bool = True):
        """
        OpenAPI 클라이언트 초기화

        Args:
            auto_login: 자동 로그인 여부 (기본값: True)
        """
        self.context = None
        self.is_connected = False
        self.account_list = []
        self.auto_login = auto_login

        # QT_API 설정 (koapy에 필요)
        os.environ['QT_API'] = 'pyqt5'

        logger.info("🔧 OpenAPI 클라이언트 초기화 중...")

    def connect(self) -> bool:
        """
        OpenAPI 서버 연결 및 로그인

        Returns:
            연결 성공 여부
        """
        try:
            from koapy import KiwoomOpenApiPlusEntrypoint

            logger.info("📡 OpenAPI 서버 연결 중...")
            logger.info("   (32비트 서버가 자동으로 시작됩니다)")

            # Context manager 패턴 사용
            self.context = KiwoomOpenApiPlusEntrypoint().__enter__()

            if self.auto_login:
                # 자동 로그인 시도
                logger.info("🔐 자동 로그인 시도 중...")
                self.context.EnsureConnected()

                # 연결 상태 확인
                state = self.context.GetConnectState()

                if state == 1:
                    logger.info("✅ OpenAPI 로그인 성공!")
                    self.is_connected = True

                    # 계좌 목록 조회
                    self.account_list = self.context.GetAccountList()
                    logger.info(f"📋 계좌 목록: {self.account_list}")

                    return True
                else:
                    logger.error(f"❌ 로그인 실패 (상태: {state})")
                    return False
            else:
                logger.info("⚠️  수동 로그인 모드 (auto_login=False)")
                self.is_connected = True
                return True

        except ImportError as e:
            logger.error("❌ koapy를 import할 수 없습니다!")
            logger.error("   해결책: pip install koapy PyQt5 protobuf==3.20.3")
            logger.error(f"   상세: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ OpenAPI 연결 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def disconnect(self):
        """OpenAPI 서버 연결 해제"""
        try:
            if self.context:
                self.context.__exit__(None, None, None)
                logger.info("🔌 OpenAPI 연결 해제됨")
            self.is_connected = False
        except Exception as e:
            logger.error(f"연결 해제 실패: {e}")

    def get_account_list(self) -> List[str]:
        """
        계좌 목록 조회

        Returns:
            계좌 번호 리스트
        """
        if not self.is_connected:
            logger.warning("OpenAPI 연결 안 됨")
            return []

        try:
            if not self.account_list:
                self.account_list = self.context.GetAccountList()
            return self.account_list
        except Exception as e:
            logger.error(f"계좌 조회 실패: {e}")
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

        try:
            if account_no is None:
                accounts = self.get_account_list()
                if not accounts:
                    logger.error("사용 가능한 계좌 없음")
                    return {}
                account_no = accounts[0]

            # opw00018: 예수금상세현황
            # opw00004: 계좌평가잔고내역
            balance_data = self.context.GetAccountEvaluationStatusAsSeriesDict(account_no)

            return balance_data
        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            return {}

    def get_holdings(self, account_no: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        보유 종목 조회

        Args:
            account_no: 계좌번호 (None이면 첫 번째 계좌)

        Returns:
            보유 종목 리스트
        """
        if not self.is_connected:
            logger.warning("OpenAPI 연결 안 됨")
            return []

        try:
            if account_no is None:
                accounts = self.get_account_list()
                if not accounts:
                    return []
                account_no = accounts[0]

            # 계좌평가잔고내역 조회
            holdings = self.context.GetAccountStocksAsDataFrame(account_no)

            if holdings is not None and not holdings.empty:
                return holdings.to_dict('records')
            return []
        except Exception as e:
            logger.error(f"보유 종목 조회 실패: {e}")
            return []

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

        try:
            if account_no is None:
                accounts = self.get_account_list()
                if not accounts:
                    return None
                account_no = accounts[0]

            logger.info(f"📈 시장가 매수 주문: {stock_code} x {quantity}주")

            # 시장가 매수
            order_no = self.context.BuyStockAtMarketPrice(
                account_no=account_no,
                code=stock_code,
                quantity=quantity
            )

            if order_no:
                logger.info(f"✅ 매수 주문 성공: 주문번호 {order_no}")
            else:
                logger.error("❌ 매수 주문 실패")

            return order_no
        except Exception as e:
            logger.error(f"매수 주문 실패: {e}")
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

        try:
            if account_no is None:
                accounts = self.get_account_list()
                if not accounts:
                    return None
                account_no = accounts[0]

            logger.info(f"📉 시장가 매도 주문: {stock_code} x {quantity}주")

            # 시장가 매도
            order_no = self.context.SellStockAtMarketPrice(
                account_no=account_no,
                code=stock_code,
                quantity=quantity
            )

            if order_no:
                logger.info(f"✅ 매도 주문 성공: 주문번호 {order_no}")
            else:
                logger.error("❌ 매도 주문 실패")

            return order_no
        except Exception as e:
            logger.error(f"매도 주문 실패: {e}")
            return None

    def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """
        종목 정보 조회

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            종목 정보 딕셔너리
        """
        if not self.is_connected:
            logger.warning("OpenAPI 연결 안 됨")
            return {}

        try:
            info = self.context.GetStockBasicInfoAsDict(stock_code)
            return info if info else {}
        except Exception as e:
            logger.error(f"종목 정보 조회 실패: {e}")
            return {}

    def __enter__(self):
        """Context manager 진입"""
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


def get_openapi_client(auto_login: bool = True) -> Optional[KiwoomOpenAPIClient]:
    """
    OpenAPI 클라이언트 싱글톤 인스턴스 반환

    Args:
        auto_login: 자동 로그인 여부

    Returns:
        OpenAPI 클라이언트 인스턴스 (연결 실패 시 None)
    """
    global _openapi_client_instance

    if _openapi_client_instance is None:
        _openapi_client_instance = KiwoomOpenAPIClient(auto_login=auto_login)
        if not _openapi_client_instance.connect():
            _openapi_client_instance = None
            return None

    return _openapi_client_instance
