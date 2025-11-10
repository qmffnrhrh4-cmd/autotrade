"""
Trade Executor Module
매매 실행 모듈

Enhanced v2.0:
- Split buy/sell logic (1/3, 1/3, 1/3)
- Retry mechanism with exponential backoff
- Slippage-aware price adjustment
- Enhanced position management
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    거래 실행자 (Enhanced v2.0)

    Features:
    - 분할 매수/매도 로직
    - 체결 실패 재시도
    - 슬리피지 고려 가격 조정
    - NXT 시장 규칙 적용
    - 데이터베이스 기록
    - 알림 발송
    """

    def __init__(
        self,
        order_api,
        account_api,
        market_api,
        dynamic_risk_manager,
        db_session,
        alert_manager,
        monitor,
        enable_split_orders: bool = True,
        max_retries: int = 3
    ):
        """초기화"""
        self.order_api = order_api
        self.account_api = account_api
        self.market_api = market_api
        self.dynamic_risk_manager = dynamic_risk_manager
        self.db_session = db_session
        self.alert_manager = alert_manager
        self.monitor = monitor

        self.enable_split_orders = enable_split_orders
        self.max_retries = max_retries
        self.market_status = {}

        logger.info(f"거래 실행자 초기화: 분할주문={enable_split_orders}, 재시도={max_retries}회")

    def set_market_status(self, market_status: Dict[str, Any]):
        """시장 상태 설정"""
        self.market_status = market_status

    def execute_buy(
        self,
        candidate,
        scoring_result
    ) -> bool:
        """
        매수 실행 (분할 매수 지원)

        Args:
            candidate: 매수 후보
            scoring_result: 스코어링 결과

        Returns:
            성공 여부
        """

        try:
            if self.market_status.get('can_cancel_only'):
                logger.warning(f"⚠️  {self.market_status['market_type']}: 신규 매수 주문 불가")
                return False

            stock_code = candidate.code
            stock_name = candidate.name
            current_price = candidate.price

            deposit = self.account_api.get_deposit()
            available_cash = int(str(deposit.get('100stk_ord_alow_amt', '0')).replace(',', '')) if deposit else 0

            total_quantity = self.dynamic_risk_manager.calculate_position_size(
                stock_price=current_price,
                available_cash=available_cash
            )

            if total_quantity == 0:
                logger.warning("매수 가능 수량 0")
                return False

            if self.enable_split_orders and total_quantity >= 30:
                return self._execute_split_buy(
                    candidate,
                    scoring_result,
                    total_quantity,
                    current_price
                )
            else:
                return self._execute_single_buy(
                    candidate,
                    scoring_result,
                    total_quantity,
                    current_price
                )

        except Exception as e:
            logger.error(f"거래 기록 실패: {e}")
            return False

    def _execute_single_buy(
        self,
        candidate,
        scoring_result,
        quantity: int,
        price: int
    ) -> bool:
        """단일 매수 실행"""
        stock_code = candidate.code
        stock_name = candidate.name

        logger.info(
            f"💳 {stock_name} 매수: {quantity}주 @ {price:,}원 "
            f"(총 {price * quantity:,}원)"
        )

        adjusted_price = self._adjust_price_for_slippage(price, 'buy')
        order_type = self._determine_order_type()

        success = self._execute_order_with_retry(
            action='buy',
            stock_code=stock_code,
            quantity=quantity,
            price=adjusted_price,
            order_type=order_type
        )

        if success:
            self._record_trade(
                stock_code=stock_code,
                stock_name=stock_name,
                action='buy',
                quantity=quantity,
                price=adjusted_price,
                total_amount=adjusted_price * quantity,
                ai_score=getattr(candidate, 'ai_confidence', 0.5),
                ai_signal=getattr(candidate, 'ai_signal', 'unknown'),
                scoring_total=scoring_result.total_score,
                scoring_percentage=scoring_result.percentage
            )

            self.alert_manager.alert_position_opened(
                stock_code=stock_code,
                stock_name=stock_name,
                buy_price=adjusted_price,
                quantity=quantity
            )

            self.monitor.log_activity(
                'buy',
                f'✅ {stock_name} 매수: {quantity}주 @ {adjusted_price:,}원',
                level='success'
            )

        return success

    def _execute_split_buy(
        self,
        candidate,
        scoring_result,
        total_quantity: int,
        price: int
    ) -> bool:
        """분할 매수 실행 (1/3, 1/3, 1/3)"""
        stock_code = candidate.code
        stock_name = candidate.name

        split_qty = total_quantity // 3
        remaining_qty = total_quantity - (split_qty * 2)

        splits = [
            (split_qty, 1.0),
            (split_qty, 1.01),
            (remaining_qty, 1.02)
        ]

        logger.info(
            f"💳 {stock_name} 분할 매수: "
            f"{splits[0][0]}주 + {splits[1][0]}주 + {splits[2][0]}주 = {total_quantity}주"
        )

        total_executed = 0
        avg_price = 0

        for idx, (qty, price_mult) in enumerate(splits, 1):
            if qty == 0:
                continue

            adjusted_price = int(price * price_mult)
            adjusted_price = self._adjust_price_for_slippage(adjusted_price, 'buy')
            order_type = self._determine_order_type()

            logger.info(f"  [{idx}/3] {qty}주 @ {adjusted_price:,}원 주문 중...")

            success = self._execute_order_with_retry(
                action='buy',
                stock_code=stock_code,
                quantity=qty,
                price=adjusted_price,
                order_type=order_type
            )

            if success:
                total_executed += qty
                avg_price = ((avg_price * (total_executed - qty)) + (adjusted_price * qty)) / total_executed
                logger.info(f"  ✅ [{idx}/3] 체결 완료")
            else:
                logger.warning(f"  ❌ [{idx}/3] 체결 실패")

            time.sleep(0.2)

        if total_executed > 0:
            self._record_trade(
                stock_code=stock_code,
                stock_name=stock_name,
                action='buy',
                quantity=total_executed,
                price=int(avg_price),
                total_amount=int(avg_price * total_executed),
                ai_score=getattr(candidate, 'ai_confidence', 0.5),
                ai_signal=getattr(candidate, 'ai_signal', 'unknown'),
                scoring_total=scoring_result.total_score,
                scoring_percentage=scoring_result.percentage,
                notes=f'분할매수 {total_executed}/{total_quantity}주'
            )

            self.alert_manager.alert_position_opened(
                stock_code=stock_code,
                stock_name=stock_name,
                buy_price=int(avg_price),
                quantity=total_executed
            )

            self.monitor.log_activity(
                'buy',
                f'✅ {stock_name} 분할 매수: {total_executed}주 @ {int(avg_price):,}원',
                level='success'
            )

            return True

        return False

    def execute_sell(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: int,
        profit_loss: int,
        profit_loss_rate: float,
        reason: str
    ) -> bool:
        """
        매도 실행

        Returns:
            성공 여부
        """

        try:
            # 주문 불가 시간 확인
            if self.market_status.get('can_cancel_only'):
                logger.warning(f"⚠️  {self.market_status['market_type']}: 신규 매도 주문 불가")
                return False

            logger.info(
                f"💸 {stock_name} 매도 실행: {quantity}주 @ {price:,}원 "
                f"(손익: {profit_loss:+,}원, {profit_loss_rate:+.2f}%)"
            )

            # 주문 유형 결정
            order_type = self._determine_order_type()

            # 주문 실행
            order_result = self.order_api.sell(
                stock_code=stock_code,
                quantity=quantity,
                price=price,
                order_type=order_type
            )

            if order_result:
                order_no = order_result.get('order_no', '')

                # DB 기록
                self._record_trade(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    action='sell',
                    quantity=quantity,
                    price=price,
                    total_amount=price * quantity,
                    profit_loss=profit_loss,
                    profit_loss_ratio=profit_loss_rate / 100,
                    notes=reason
                )

                log_level = 'success' if profit_loss >= 0 else 'warning'
                logger.info(f"✅ {stock_name} 매도 성공 (주문번호: {order_no})")

                # 알림
                self.alert_manager.alert_position_closed(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    sell_price=price,
                    profit_loss_rate=profit_loss_rate,
                    profit_loss_amount=profit_loss,
                    reason=reason
                )

                # 모니터
                self.monitor.log_activity(
                    'sell',
                    f'✅ {stock_name} 매도: {quantity}주 @ {price:,}원 (손익: {profit_loss:+,}원)',
                    level=log_level
                )

                return True
            else:
                logger.error("매도 주문 실패")
                return False

        except Exception as e:
            logger.error(f"매도 실행 실패: {e}", exc_info=True)
            return False

    def _determine_order_type(self) -> str:
        """주문 유형 결정 (시간대별)"""

        from utils.trading_date import is_nxt_hours
        from datetime import datetime

        if is_nxt_hours():
            now = datetime.now()
            if now.hour == 8:
                return '61'  # 장시작전시간외
            else:
                return '81'  # 장마감후시간외
        else:
            return '0'  # 보통 지정가

    def _record_trade(self, **kwargs):
        """거래 기록"""

        try:
            from database import Trade

            trade = Trade(
                risk_mode=self.dynamic_risk_manager.current_mode.value,
                **kwargs
            )

            self.db_session.add(trade)
            self.db_session.commit()

        except Exception as e:
            logger.error(f"거래 기록 실패: {e}")

    def _adjust_price_for_slippage(self, price: int, action: str) -> int:
        """슬리피지를 고려한 가격 조정"""
        slippage_rate = 0.003

        if action == 'buy':
            adjusted = int(price * (1 + slippage_rate))
        else:
            adjusted = int(price * (1 - slippage_rate))

        tick_size = self._get_tick_size(price)
        adjusted = (adjusted // tick_size) * tick_size

        return adjusted

    def _get_tick_size(self, price: int) -> int:
        """가격대별 호가 단위"""
        if price < 1000:
            return 1
        elif price < 5000:
            return 5
        elif price < 10000:
            return 10
        elif price < 50000:
            return 50
        elif price < 100000:
            return 100
        elif price < 500000:
            return 500
        else:
            return 1000

    def _execute_order_with_retry(
        self,
        action: str,
        stock_code: str,
        quantity: int,
        price: int,
        order_type: str
    ) -> bool:
        """재시도 로직이 포함된 주문 실행"""
        for attempt in range(self.max_retries):
            try:
                if action == 'buy':
                    result = self.order_api.buy(
                        stock_code=stock_code,
                        quantity=quantity,
                        price=price,
                        order_type=order_type
                    )
                else:
                    result = self.order_api.sell(
                        stock_code=stock_code,
                        quantity=quantity,
                        price=price,
                        order_type=order_type
                    )

                if result:
                    return True

                logger.warning(f"{action} 주문 실패 (시도 {attempt + 1}/{self.max_retries})")

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"{wait_time}초 후 재시도...")
                    time.sleep(wait_time)

            except Exception as e:
                logger.error(f"{action} 주문 오류 (시도 {attempt + 1}/{self.max_retries}): {e}")

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)

        return False
