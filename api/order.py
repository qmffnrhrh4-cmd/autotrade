"""
api/order.py
주문 관련 API

Author: AutoTrade Pro
Version: 5.2 - 재시도 로직 및 주문 상태 조회 추가
"""
import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from utils.validators import adjust_price_to_tick_size
from utils.user_feedback import get_user_feedback

logger = logging.getLogger(__name__)

# 주문 재시도 설정
MAX_ORDER_RETRIES = 3  # 최대 재시도 횟수
RETRY_DELAY_BASE = 1.0  # 기본 재시도 대기 시간 (초)
RETRY_DELAY_MULTIPLIER = 2.0  # 지수 백오프 승수


def _should_retry_order(error_msg: str, error_code: str) -> bool:
    """
    에러 유형에 따라 재시도 여부 판단

    Returns:
        True: 재시도 가능 (일시적 오류)
        False: 재시도 불가 (영구적 오류)
    """
    # 재시도 불가능한 영구적 오류
    permanent_errors = [
        '잔고부족', '주문가능수량초과', '계좌번호오류',
        '종목코드오류', '주문수량오류', '호가단위오류',
        '신용한도초과', '주문불가종목', '상한가', '하한가',
        '-301',  # 잔고 부족
        '-302',  # 주문 한도 초과
        '-303',  # 계좌 오류
    ]

    # 재시도 가능한 일시적 오류
    temporary_errors = [
        'timeout', 'connection', '네트워크', '응답없음',
        '서버오류', '일시적', 'retry',
        '-102',  # 타임아웃
        '429',   # Rate limit
        '500', '502', '503', '504',  # 서버 에러
    ]

    error_lower = (error_msg or '').lower()
    error_code_str = str(error_code or '')

    # 영구적 오류인지 확인
    for perm_err in permanent_errors:
        if perm_err.lower() in error_lower or perm_err in error_code_str:
            return False

    # 일시적 오류인지 확인
    for temp_err in temporary_errors:
        if temp_err.lower() in error_lower or temp_err in error_code_str:
            return True

    # 기본적으로 응답 없음(None)은 재시도
    if error_msg == '응답 없음':
        return True

    return False


class OrderAPI:
    """
    주문 관련 API

    주요 기능:
    - 매수/매도 주문
    - 정정/취소 주문
    - 주문 조회
    - DRY RUN 모드 지원 (실제 주문 없이 시뮬레이션)
    """

    def __init__(self, client, dry_run=False):
        """
        OrderAPI 초기화

        Args:
            client: KiwoomRESTClient 인스턴스
            dry_run: True면 실제 주문 없이 시뮬레이션만 수행 (기본값: False - 실제 주문 실행)
        """
        self.client = client
        self.dry_run = dry_run
        self.simulated_orders = []  # dry_run 모드의 주문 기록

        mode = "DRY RUN (시뮬레이션)" if dry_run else "LIVE (실제 주문)"
        logger.info(f"OrderAPI 초기화 완료 - 모드: {mode}")

        if dry_run:
            logger.warning("⚠️  DRY RUN 모드 활성화 - 실제 주문이 실행되지 않습니다")
        else:
            logger.info("✅ LIVE 모드 활성화 - 실제 주문이 API로 전송됩니다")

    def buy(
        self,
        stock_code: str,
        quantity: int,
        price: int,
        order_type: str = '02',  # 02: 지정가
        account_number: str = None,
        exchange: str = None  # None: 자동 선택, 'KRX', 'NXT', 'SOR'
    ) -> Optional[Dict[str, Any]]:
        """
        매수 주문

        Args:
            stock_code: 종목코드
            quantity: 주문수량
            price: 주문가격 (시장가는 0)
            order_type: 주문유형 ('01': 시장가, '02': 지정가, '0': 보통지정가)
            account_number: 계좌번호
            exchange: 거래소 선택 (None: 자동, 'KRX': 일반, 'NXT': 시간외)

        Returns:
            주문 결과
        """
        if self.dry_run:
            return self._simulate_buy(stock_code, quantity, price, order_type)

        # 실제 매수 주문 API 호출 (kt10000: 주식매수주문)
        logger.info(f"🔵 실제 매수 주문 실행: {stock_code} {quantity}주 @ {price:,}원")

        try:
            # 주문 파라미터 구성
            # trde_tp: 거래유형 (키움 API 문서 참조)
            # - 0: 보통(지정가)
            # - 3: 시장가
            # - 61: 장시작전시간외
            # - 62: 시간외단일가
            # - 81: 장마감후시간외
            # order_type을 trde_tp로 매핑
            if order_type == '62':
                trde_tp = '62'  # 시간외단일가
            elif order_type == '81':
                trde_tp = '81'  # 장마감후시간외
            elif order_type == '61':
                trde_tp = '61'  # 장시작전시간외
            elif order_type in ['00', '02', '0']:
                trde_tp = '0'  # 보통(지정가) - 앞의 0 제거!
            elif order_type in ['01', '3']:
                trde_tp = '3'  # 시장가 - 3으로 변환!
            else:
                trde_tp = order_type  # 그대로 사용

            # dmst_stex_tp: 거래소 선택
            # ✅ 테스트 결과: 시간외 거래 시 NXT 거래소에서 trde_tp=0 (보통지정가) 사용
            if exchange:
                # 명시적으로 거래소가 지정된 경우 (main.py에서 지정)
                dmst_stex_tp = exchange
                logger.info(f"📍 거래소 명시: {exchange}")
            elif trde_tp in ['61', '62', '81']:
                # 시간외 거래 타입인 경우 NXT
                dmst_stex_tp = 'NXT'
            else:
                # 기본값: KRX
                dmst_stex_tp = 'KRX'

            # ord_uv(주문단가): 시장가(3)와 시간외종가(81)는 빈 문자열, 나머지는 가격 지정
            # ✅ 테스트 결과: NXT 거래소는 trde_tp=0에도 가격 지정 필요
            if trde_tp == '3':
                # 시장가: 가격 지정 안 함
                ord_uv_value = ""
                logger.info(f"⚠️ 시장가 주문: 가격 지정 없음")
            elif trde_tp == '81':
                # 시간외종가: 가격 지정 안 함 (종가로 자동 체결)
                ord_uv_value = ""
                logger.info(f"⚠️ 시간외종가 주문: 장 마감 종가로 자동 체결")
            else:
                # 나머지는 가격 지정 - 호가 단위에 맞게 조정
                adjusted_price = adjust_price_to_tick_size(price)
                ord_uv_value = str(adjusted_price)
                if adjusted_price != price:
                    logger.warning(f"⚠️ 매수가 조정: {price:,}원 → {adjusted_price:,}원 (호가 단위 준수)")

            body_params = {
                "dmst_stex_tp": dmst_stex_tp,
                "stk_cd": stock_code,
                "ord_qty": str(quantity),
                "ord_uv": ord_uv_value,
                "trde_tp": trde_tp
            }

            logger.info(f"📋 주문 파라미터: order_type={order_type} → trde_tp={trde_tp}, dmst_stex_tp={dmst_stex_tp}, ord_uv={ord_uv_value}")

            # API 호출 (재시도 로직 포함)
            last_error_msg = None
            last_error_code = None

            for attempt in range(MAX_ORDER_RETRIES + 1):
                try:
                    result = self.client.request(
                        api_id='kt10000',
                        body=body_params,
                        path='/api/dostk/ordr'
                    )

                    if result and result.get('return_code') == 0:
                        order_no = result.get('ord_no', 'N/A')
                        if attempt > 0:
                            logger.info(f"✅ 매수 주문 성공 (재시도 {attempt}회 후): 주문번호 {order_no}")
                        else:
                            logger.info(f"✅ 매수 주문 성공: 주문번호 {order_no}")

                        # 사용자 피드백 표시
                        feedback = get_user_feedback()
                        stock_name = result.get('stk_nm', stock_code)
                        feedback.show_buy_success(
                            stock_code=stock_code,
                            stock_name=stock_name,
                            quantity=quantity,
                            price=int(ord_uv_value) if ord_uv_value else price,
                            order_no=order_no
                        )

                        return {
                            'order_no': order_no,
                            'stock_code': stock_code,
                            'quantity': quantity,
                            'price': price,
                            'status': 'ordered',
                            'result': result,
                            'retry_count': attempt
                        }

                    # API 오류 응답
                    last_error_msg = result.get('return_msg', '알 수 없는 오류') if result else '응답 없음'
                    last_error_code = str(result.get('return_code', '')) if result else ''

                    # 재시도 가능한 오류인지 확인
                    if attempt < MAX_ORDER_RETRIES and _should_retry_order(last_error_msg, last_error_code):
                        retry_delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                        logger.warning(f"⚠️ 매수 주문 실패 (시도 {attempt+1}/{MAX_ORDER_RETRIES+1}): {last_error_msg}")
                        logger.warning(f"   {retry_delay:.1f}초 후 재시도...")
                        time.sleep(retry_delay)
                        continue

                    # 재시도 불가 또는 최대 재시도 도달
                    break

                except Exception as e:
                    last_error_msg = str(e)
                    last_error_code = 'exception'

                    if attempt < MAX_ORDER_RETRIES:
                        retry_delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                        logger.warning(f"⚠️ 매수 주문 예외 (시도 {attempt+1}/{MAX_ORDER_RETRIES+1}): {e}")
                        logger.warning(f"   {retry_delay:.1f}초 후 재시도...")
                        time.sleep(retry_delay)
                        continue
                    break

            # 모든 재시도 실패
            logger.error(f"❌ 매수 주문 최종 실패: {last_error_msg}")
            logger.error(f"   서버: {self.client.base_url}")
            logger.error(f"   파라미터: trde_tp={trde_tp}, dmst_stex_tp={dmst_stex_tp}")

            # NXT 시간외 거래 실패 시 추가 안내
            if dmst_stex_tp == 'NXT' and 'mockapi' in self.client.base_url:
                logger.error(f"   ⚠️ 모의투자 서버는 NXT 시간외 거래를 지원하지 않습니다!")
                logger.error(f"   ⚠️ 실제 운영 서버(api.kiwoom.com)로 변경하세요.")

            # 사용자 피드백 표시
            feedback.show_buy_failure(
                stock_code=stock_code,
                stock_name=stock_code,
                quantity=quantity,
                price=price,
                error_code=last_error_code,
                error_msg=last_error_msg
            )

            return {
                'order_no': None,
                'stock_code': stock_code,
                'quantity': quantity,
                'price': price,
                'status': 'failed',
                'error': last_error_msg,
                'retry_count': MAX_ORDER_RETRIES
            }

        except Exception as e:
            logger.error(f"매수 주문 예외 발생: {e}", exc_info=True)

            # 사용자 피드백 표시
            feedback = get_user_feedback()
            feedback.show_error(
                error_code='exception',
                error_msg=str(e),
                context='매수 주문'
            )

            return {
                'order_no': None,
                'stock_code': stock_code,
                'quantity': quantity,
                'price': price,
                'status': 'error',
                'error': str(e)
            }

    def sell(
        self,
        stock_code: str,
        quantity: int,
        price: int,
        order_type: str = '02',  # 02: 지정가
        account_number: str = None,
        exchange: str = None  # None: 자동 선택, 'KRX', 'NXT', 'SOR'
    ) -> Optional[Dict[str, Any]]:
        """
        매도 주문

        Args:
            stock_code: 종목코드
            quantity: 주문수량
            price: 주문가격 (시장가는 0)
            order_type: 주문유형 ('01': 시장가, '02': 지정가, '0': 보통지정가)
            account_number: 계좌번호
            exchange: 거래소 선택 (None: 자동, 'KRX': 일반, 'NXT': 시간외)

        Returns:
            주문 결과
        """
        if self.dry_run:
            return self._simulate_sell(stock_code, quantity, price, order_type)

        # 실제 매도 주문 API 호출 (kt10001: 주식매도주문)
        logger.info(f"🔴 실제 매도 주문 실행: {stock_code} {quantity}주 @ {price:,}원")

        # CRITICAL FIX: 비정상 가격 검증 (모든 매도 주문에 적용)
        if price > 0:  # 시장가(0)가 아닌 경우에만
            try:
                from research import DataFetcher
                data_fetcher = DataFetcher(self.client)
                current_price_data = data_fetcher.get_current_price(stock_code)
                current_price = current_price_data.get('current_price', 0)

                if current_price > 0 and price > current_price * 1.3:
                    original_price = price
                    price = int(current_price * 1.02)  # 현재가 +2%로 조정
                    logger.warning(f"🚨 [PRICE FIX] 비정상 매도가 감지 및 자동 조정!")
                    logger.warning(f"   원본 가격: {original_price:,}원 (현재가 대비 +{((original_price/current_price - 1) * 100):.1f}%)")
                    logger.warning(f"   현재가: {current_price:,}원")
                    logger.warning(f"   조정 가격: {price:,}원 (현재가 +2%)")
            except Exception as e:
                logger.warning(f"가격 검증 실패 (원본 가격 사용): {e}")

        try:
            # 주문 파라미터 구성
            # trde_tp: 거래유형 (키움 API 문서 참조)
            # - 0: 보통(지정가)
            # - 3: 시장가
            # - 61: 장시작전시간외
            # - 62: 시간외단일가
            # - 81: 장마감후시간외
            # order_type을 trde_tp로 매핑
            if order_type == '62':
                trde_tp = '62'  # 시간외단일가
            elif order_type == '81':
                trde_tp = '81'  # 장마감후시간외
            elif order_type == '61':
                trde_tp = '61'  # 장시작전시간외
            elif order_type in ['00', '02', '0']:
                trde_tp = '0'  # 보통(지정가) - 앞의 0 제거!
            elif order_type in ['01', '3']:
                trde_tp = '3'  # 시장가 - 3으로 변환!
            else:
                trde_tp = order_type  # 그대로 사용

            # dmst_stex_tp: 거래소 선택
            # ✅ 테스트 결과: 시간외 거래 시 NXT 거래소에서 trde_tp=0 (보통지정가) 사용
            if exchange:
                # 명시적으로 거래소가 지정된 경우 (main.py에서 지정)
                dmst_stex_tp = exchange
                logger.info(f"📍 거래소 명시: {exchange}")
            elif trde_tp in ['61', '62', '81']:
                # 시간외 거래 타입인 경우 NXT
                dmst_stex_tp = 'NXT'
            else:
                # 기본값: KRX
                dmst_stex_tp = 'KRX'

            # ord_uv(주문단가): 시장가(3)와 시간외종가(81)는 빈 문자열, 나머지는 가격 지정
            # ✅ 테스트 결과: NXT 거래소는 trde_tp=0에도 가격 지정 필요
            if trde_tp == '3':
                # 시장가: 가격 지정 안 함
                ord_uv_value = ""
                logger.info(f"⚠️ 시장가 주문: 가격 지정 없음")
            elif trde_tp == '81':
                # 시간외종가: 가격 지정 안 함 (종가로 자동 체결)
                ord_uv_value = ""
                logger.info(f"⚠️ 시간외종가 주문: 장 마감 종가로 자동 체결")
            else:
                # 나머지는 가격 지정 - 호가 단위에 맞게 조정
                logger.warning(f"🔍 [ORDER DEBUG] 매도 주문 원본 가격: {price:,}원 (종목: {stock_code})")
                import traceback
                caller_info = traceback.extract_stack(limit=5)
                for frame in caller_info:
                    logger.debug(f"  호출 경로: {frame.filename}:{frame.lineno} in {frame.name}")
                adjusted_price = adjust_price_to_tick_size(price)

                # 상한가 체크 (현재가 기준 약 30% 상승 제한)
                # 정확한 기준가를 모르므로 현재가 조회
                try:
                    # 현재가 조회
                    from research import DataFetcher
                    if hasattr(self, 'client'):
                        data_fetcher = DataFetcher(self.client)
                        price_data = data_fetcher.get_current_price(stock_code)
                        current_price = price_data.get('current_price', 0)

                        if current_price > 0:
                            # 상한가는 대략 현재가의 1.29배 (30% 상승에서 약간 여유)
                            max_sell_price = int(current_price * 1.29)

                            if adjusted_price > max_sell_price:
                                logger.warning(f"⚠️ 상한가 제한: {adjusted_price:,}원 → {max_sell_price:,}원 (현재가: {current_price:,}원)")
                                adjusted_price = adjust_price_to_tick_size(max_sell_price)
                except Exception as e:
                    logger.debug(f"상한가 체크 실패 (무시): {e}")

                ord_uv_value = str(adjusted_price)
                if adjusted_price != price:
                    logger.warning(f"⚠️ 매도가 조정: {price:,}원 → {adjusted_price:,}원 (호가 단위 준수)")

            body_params = {
                "dmst_stex_tp": dmst_stex_tp,
                "stk_cd": stock_code,
                "ord_qty": str(quantity),
                "ord_uv": ord_uv_value,
                "trde_tp": trde_tp
            }

            logger.info(f"📋 주문 파라미터: order_type={order_type} → trde_tp={trde_tp}, dmst_stex_tp={dmst_stex_tp}, ord_uv={ord_uv_value}")

            # API 호출 (재시도 로직 포함)
            last_error_msg = None
            last_error_code = None

            for attempt in range(MAX_ORDER_RETRIES + 1):
                try:
                    result = self.client.request(
                        api_id='kt10001',
                        body=body_params,
                        path='/api/dostk/ordr'
                    )

                    if result and result.get('return_code') == 0:
                        order_no = result.get('ord_no', 'N/A')
                        if attempt > 0:
                            logger.info(f"✅ 매도 주문 성공 (재시도 {attempt}회 후): 주문번호 {order_no}")
                        else:
                            logger.info(f"✅ 매도 주문 성공: 주문번호 {order_no}")

                        # 사용자 피드백 표시
                        feedback = get_user_feedback()
                        stock_name = result.get('stk_nm', stock_code)
                        feedback.show_sell_success(
                            stock_code=stock_code,
                            stock_name=stock_name,
                            quantity=quantity,
                            price=int(ord_uv_value) if ord_uv_value else price,
                            profit_loss=0,  # 체결 후 계산됨
                            profit_loss_rate=0.0,
                            order_no=order_no
                        )

                        return {
                            'order_no': order_no,
                            'stock_code': stock_code,
                            'quantity': quantity,
                            'price': price,
                            'status': 'ordered',
                            'result': result,
                            'retry_count': attempt
                        }

                    # API 오류 응답
                    last_error_msg = result.get('return_msg', '알 수 없는 오류') if result else '응답 없음'
                    last_error_code = str(result.get('return_code', '')) if result else ''

                    # 재시도 가능한 오류인지 확인
                    if attempt < MAX_ORDER_RETRIES and _should_retry_order(last_error_msg, last_error_code):
                        retry_delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                        logger.warning(f"⚠️ 매도 주문 실패 (시도 {attempt+1}/{MAX_ORDER_RETRIES+1}): {last_error_msg}")
                        logger.warning(f"   {retry_delay:.1f}초 후 재시도...")
                        time.sleep(retry_delay)
                        continue

                    # 재시도 불가 또는 최대 재시도 도달
                    break

                except Exception as e:
                    last_error_msg = str(e)
                    last_error_code = 'exception'

                    if attempt < MAX_ORDER_RETRIES:
                        retry_delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                        logger.warning(f"⚠️ 매도 주문 예외 (시도 {attempt+1}/{MAX_ORDER_RETRIES+1}): {e}")
                        logger.warning(f"   {retry_delay:.1f}초 후 재시도...")
                        time.sleep(retry_delay)
                        continue
                    break

            # 모든 재시도 실패
            logger.error(f"❌ 매도 주문 최종 실패: {last_error_msg}")
            logger.error(f"   서버: {self.client.base_url}")
            logger.error(f"   파라미터: trde_tp={trde_tp}, dmst_stex_tp={dmst_stex_tp}")

            # NXT 시간외 거래 실패 시 추가 안내
            if dmst_stex_tp == 'NXT' and 'mockapi' in self.client.base_url:
                logger.error(f"   ⚠️ 모의투자 서버는 NXT 시간외 거래를 지원하지 않습니다!")
                logger.error(f"   ⚠️ 실제 운영 서버(api.kiwoom.com)로 변경하세요.")

            # 사용자 피드백 표시
            feedback = get_user_feedback()
            feedback.show_sell_failure(
                stock_code=stock_code,
                stock_name=stock_code,
                quantity=quantity,
                price=price,
                error_code=last_error_code,
                error_msg=last_error_msg
            )

            return {
                'order_no': None,
                'stock_code': stock_code,
                'quantity': quantity,
                'price': price,
                'status': 'failed',
                'error': last_error_msg,
                'retry_count': MAX_ORDER_RETRIES
            }

        except Exception as e:
            logger.error(f"매도 주문 예외 발생: {e}", exc_info=True)

            # 사용자 피드백 표시
            feedback = get_user_feedback()
            feedback.show_error(
                error_code='exception',
                error_msg=str(e),
                context='매도 주문'
            )

            return {
                'order_no': None,
                'stock_code': stock_code,
                'quantity': quantity,
                'price': price,
                'status': 'error',
                'error': str(e)
            }

    def modify(
        self,
        order_no: str,
        stock_code: str,
        quantity: int,
        price: int,
        account_number: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        주문 정정

        Args:
            order_no: 원주문번호
            stock_code: 종목코드
            quantity: 정정수량
            price: 정정가격
            account_number: 계좌번호

        Returns:
            정정 결과
        """
        logger.warning("주문 정정 API가 아직 구현되지 않았습니다")
        return None

    def cancel(
        self,
        order_no: str,
        stock_code: str,
        quantity: int,
        account_number: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        주문 취소

        Args:
            order_no: 원주문번호
            stock_code: 종목코드
            quantity: 취소수량
            account_number: 계좌번호

        Returns:
            취소 결과
        """
        if not self.client:
            logger.error("Client가 초기화되지 않았습니다")
            return {'success': False, 'error': 'Client not initialized'}

        try:
            logger.info(f"주문 취소 요청: {stock_code}, 주문번호={order_no}, 수량={quantity}")

            # 전량 취소 여부
            cancel_all = quantity == 0

            # API 호출: kt10003 (주식취소주문)
            body = {
                "dmst_stex_tp": "KRX",
                "stk_cd": stock_code,
                "orig_ord_no": order_no,
                "cncl_qty": "0" if cancel_all else str(quantity),
                "trde_tp": "0"
            }

            result = self.client.request(
                api_id='kt10003',
                body=body,
                path='/api/dostk/ordr'
            )

            if result and result.get('return_code') == 0:
                logger.info(f"✅ 주문 취소 성공: {order_no}")
                return {
                    'success': True,
                    'order_no': order_no,
                    'cancelled_quantity': quantity if quantity > 0 else 'all',
                    'message': '주문이 취소되었습니다',
                    'result': result
                }
            else:
                error_msg = result.get('return_msg', '알 수 없는 오류') if result else '응답 없음'
                logger.error(f"❌ 주문 취소 실패: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'result': result
                }

        except Exception as e:
            logger.error(f"주문 취소 중 오류: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_order_status(
        self,
        order_no: str,
        stock_code: str = None,
        account_number: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        주문 상태 조회

        미체결 주문과 체결 주문 모두에서 해당 주문번호를 검색합니다.

        Args:
            order_no: 주문번호
            stock_code: 종목코드 (선택, 빠른 조회용)
            account_number: 계좌번호

        Returns:
            주문 상태 정보:
            - status: 'pending' | 'partial' | 'filled' | 'cancelled' | 'unknown'
            - order_no: 주문번호
            - stock_code: 종목코드
            - order_qty: 주문수량
            - filled_qty: 체결수량
            - remaining_qty: 미체결수량
            - order_price: 주문가격
            - filled_price: 체결가격 (평균)
            - order_time: 주문시간
            - fill_time: 체결시간 (있는 경우)
        """
        if not self.client:
            logger.error("Client가 초기화되지 않았습니다")
            return {'status': 'unknown', 'error': 'Client not initialized'}

        try:
            logger.debug(f"주문 상태 조회: order_no={order_no}, stock_code={stock_code}")

            # 1. 미체결 주문 조회 (ka10075)
            try:
                override = {'trde_tp': '0'}  # 전체 (매수+매도)
                if stock_code:
                    override['stk_cd'] = stock_code
                    override['all_stk_tp'] = '1'
                else:
                    override['all_stk_tp'] = '0'

                outstanding_result = self.client.call_verified_api(
                    api_id='ka10075',
                    variant_idx=1 if not stock_code else 2,
                    body_override=override
                )

                if outstanding_result and outstanding_result.get('return_code') == 0:
                    orders = outstanding_result.get('nccs_ord_list', [])
                    for order in orders:
                        if order.get('ord_no') == order_no:
                            order_qty = int(order.get('ord_qty', 0))
                            filled_qty = int(order.get('cntr_qty', 0))
                            remaining_qty = int(order.get('nccs_qty', order_qty - filled_qty))

                            status = 'pending'
                            if filled_qty > 0 and remaining_qty > 0:
                                status = 'partial'
                            elif filled_qty > 0 and remaining_qty == 0:
                                status = 'filled'

                            return {
                                'status': status,
                                'order_no': order_no,
                                'stock_code': order.get('stk_cd', stock_code),
                                'stock_name': order.get('stk_nm', ''),
                                'order_type': order.get('trde_tp', ''),  # 매수/매도
                                'order_qty': order_qty,
                                'filled_qty': filled_qty,
                                'remaining_qty': remaining_qty,
                                'order_price': int(order.get('ord_uv', 0)),
                                'filled_price': int(order.get('cntr_uv', 0)),
                                'order_time': order.get('ord_time', ''),
                                'message': f"주문 진행 중 (체결: {filled_qty}/{order_qty}주)"
                            }
            except Exception as e:
                logger.debug(f"미체결 조회 오류 (무시): {e}")

            # 2. 체결 주문 조회 (ka10076)
            try:
                override = {'qry_tp': '0'}
                if stock_code:
                    override['stk_cd'] = stock_code

                executed_result = self.client.call_verified_api(
                    api_id='ka10076',
                    variant_idx=1 if not stock_code else 2,
                    body_override=override
                )

                if executed_result and executed_result.get('return_code') == 0:
                    orders = executed_result.get('cntr_ord_list', [])
                    for order in orders:
                        if order.get('ord_no') == order_no:
                            order_qty = int(order.get('ord_qty', 0))
                            filled_qty = int(order.get('cntr_qty', order_qty))

                            return {
                                'status': 'filled',
                                'order_no': order_no,
                                'stock_code': order.get('stk_cd', stock_code),
                                'stock_name': order.get('stk_nm', ''),
                                'order_type': order.get('trde_tp', ''),
                                'order_qty': order_qty,
                                'filled_qty': filled_qty,
                                'remaining_qty': 0,
                                'order_price': int(order.get('ord_uv', 0)),
                                'filled_price': int(order.get('cntr_uv', 0)),
                                'order_time': order.get('ord_time', ''),
                                'fill_time': order.get('cntr_time', ''),
                                'message': f"체결 완료 ({filled_qty}주)"
                            }
            except Exception as e:
                logger.debug(f"체결 조회 오류 (무시): {e}")

            # 찾지 못함
            logger.debug(f"주문번호 {order_no}를 찾지 못함")
            return {
                'status': 'unknown',
                'order_no': order_no,
                'message': '주문 정보를 찾을 수 없습니다 (취소되었거나 조회 기간 초과)'
            }

        except Exception as e:
            logger.error(f"주문 상태 조회 오류: {e}", exc_info=True)
            return {
                'status': 'error',
                'order_no': order_no,
                'error': str(e)
            }

    def wait_for_fill(
        self,
        order_no: str,
        stock_code: str = None,
        timeout_seconds: int = 30,
        check_interval: float = 2.0
    ) -> Dict[str, Any]:
        """
        주문 체결 대기

        지정된 시간 동안 주문이 체결될 때까지 상태를 확인합니다.

        Args:
            order_no: 주문번호
            stock_code: 종목코드 (선택)
            timeout_seconds: 타임아웃 (초)
            check_interval: 확인 간격 (초)

        Returns:
            최종 주문 상태
        """
        logger.info(f"⏳ 체결 대기 시작: {order_no} (최대 {timeout_seconds}초)")

        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout_seconds:
            status = self.get_order_status(order_no, stock_code)

            if status:
                current_status = status.get('status')

                # 상태 변경 시 로그
                if current_status != last_status:
                    filled_qty = status.get('filled_qty', 0)
                    order_qty = status.get('order_qty', 0)
                    logger.info(f"📊 주문 상태: {current_status} (체결: {filled_qty}/{order_qty}주)")
                    last_status = current_status

                # 완료 상태면 반환
                if current_status in ['filled', 'cancelled', 'error']:
                    logger.info(f"✅ 체결 완료: {current_status}")
                    return status

            time.sleep(check_interval)

        # 타임아웃
        logger.warning(f"⚠️ 체결 대기 타임아웃 ({timeout_seconds}초)")
        return {
            'status': 'timeout',
            'order_no': order_no,
            'last_check': last_status,
            'message': f'{timeout_seconds}초 내에 체결되지 않았습니다'
        }

    # ==================== DRY RUN 모드 메서드 ====================

    def _simulate_buy(self, stock_code: str, quantity: int, price: int, order_type: str):
        """매수 주문 시뮬레이션"""
        order_no = f"SIM{datetime.now().strftime('%Y%m%d%H%M%S')}"

        order = {
            "order_no": order_no,
            "stock_code": stock_code,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
            "side": "buy",
            "status": "filled",  # 시뮬레이션에서는 즉시 체결
            "timestamp": datetime.now().isoformat()
        }

        self.simulated_orders.append(order)

        logger.info(
            f"[DRY RUN] 매수 주문 시뮬레이션: {stock_code} "
            f"{quantity}주 @ {price:,}원 (주문번호: {order_no})"
        )

        return order

    def _simulate_sell(self, stock_code: str, quantity: int, price: int, order_type: str):
        """매도 주문 시뮬레이션"""
        order_no = f"SIM{datetime.now().strftime('%Y%m%d%H%M%S')}"

        order = {
            "order_no": order_no,
            "stock_code": stock_code,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
            "side": "sell",
            "status": "filled",  # 시뮬레이션에서는 즉시 체결
            "timestamp": datetime.now().isoformat()
        }

        self.simulated_orders.append(order)

        logger.info(
            f"[DRY RUN] 매도 주문 시뮬레이션: {stock_code} "
            f"{quantity}주 @ {price:,}원 (주문번호: {order_no})"
        )

        return order

    def get_simulated_orders(self):
        """시뮬레이션 주문 내역 조회"""
        return self.simulated_orders.copy()

    def clear_simulated_orders(self):
        """시뮬레이션 주문 내역 초기화"""
        self.simulated_orders.clear()
        logger.info("시뮬레이션 주문 내역 초기화")


__all__ = ['OrderAPI']
