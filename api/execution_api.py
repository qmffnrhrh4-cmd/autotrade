import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import deque
from enum import Enum
from dataclasses import dataclass, field
import threading

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    MODIFIED = "modified"


@dataclass
class OrderRecord:
    order_no: str
    stock_code: str
    side: str
    quantity: int
    price: int
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    original_order_no: str = None


class ExecutionAPI:
    def __init__(self, client):
        self.client = client
        logger.info("ExecutionAPI 초기화")

    def get_outstanding_orders(self, stock_code: str = None, trade_type: str = "0") -> Optional[Dict[str, Any]]:
        try:
            body = {
                "all_stk_tp": "1" if stock_code else "0",
                "trde_tp": trade_type,
                "stex_tp": "0"
            }
            if stock_code:
                body["stk_cd"] = stock_code

            result = self.client.request(
                api_id='ka10075',
                body=body,
                path='/api/dostk/acnt'
            )

            if result and result.get('return_code') == 0:
                logger.debug(f"미체결 조회 성공")
                return result
            return None
        except Exception as e:
            logger.error(f"미체결 조회 오류: {e}")
            return None

    def get_executed_orders(self, stock_code: str = None, query_type: str = "0") -> Optional[Dict[str, Any]]:
        try:
            body = {
                "qry_tp": "1" if stock_code else "0",
                "sell_tp": "0",
                "stex_tp": "0"
            }
            if stock_code:
                body["stk_cd"] = stock_code

            result = self.client.request(
                api_id='ka10076',
                body=body,
                path='/api/dostk/acnt'
            )

            if result and result.get('return_code') == 0:
                logger.debug(f"체결 조회 성공")
                return result
            return None
        except Exception as e:
            logger.error(f"체결 조회 오류: {e}")
            return None

    def get_order_detail(self, order_date: str = None, query_type: str = "1") -> Optional[Dict[str, Any]]:
        try:
            if not order_date:
                order_date = datetime.now().strftime('%Y%m%d')

            body = {
                "ord_dt": order_date,
                "qry_tp": query_type,
                "stk_bond_tp": "0",
                "sell_tp": "0",
                "stk_cd": "",
                "fr_ord_no": "",
                "dmst_stex_tp": "KRX"
            }

            result = self.client.request(
                api_id='kt00007',
                body=body,
                path='/api/dostk/acnt'
            )

            if result and result.get('return_code') == 0:
                logger.debug(f"체결내역 상세 조회 성공")
                return result
            return None
        except Exception as e:
            logger.error(f"체결내역 상세 조회 오류: {e}")
            return None

    def modify_order(
        self,
        original_order_no: str,
        stock_code: str,
        quantity: int,
        price: int,
        exchange: str = "KRX"
    ) -> Optional[Dict[str, Any]]:
        try:
            logger.info(f"주문 정정: 원주문={original_order_no}, 수량={quantity}, 가격={price:,}")

            body = {
                "dmst_stex_tp": exchange,
                "stk_cd": stock_code,
                "orig_ord_no": original_order_no,
                "mdfy_qty": str(quantity),
                "mdfy_uv": str(price),
                "trde_tp": "0"
            }

            result = self.client.request(
                api_id='kt10002',
                body=body,
                path='/api/dostk/ordr'
            )

            if result and result.get('return_code') == 0:
                new_order_no = result.get('ord_no', '')
                logger.info(f"주문 정정 성공: {original_order_no} -> {new_order_no}")
                return {
                    'success': True,
                    'original_order_no': original_order_no,
                    'new_order_no': new_order_no,
                    'quantity': quantity,
                    'price': price,
                    'result': result
                }
            else:
                error_msg = result.get('return_msg', '오류') if result else '응답 없음'
                logger.error(f"주문 정정 실패: {error_msg}")
                return {'success': False, 'error': error_msg}

        except Exception as e:
            logger.error(f"주문 정정 예외: {e}")
            return {'success': False, 'error': str(e)}

    def cancel_order(
        self,
        original_order_no: str,
        stock_code: str,
        quantity: int = 0,
        exchange: str = "KRX"
    ) -> Optional[Dict[str, Any]]:
        try:
            cancel_all = quantity == 0
            logger.info(f"주문 취소: 원주문={original_order_no}, 수량={'전량' if cancel_all else quantity}")

            body = {
                "dmst_stex_tp": exchange,
                "stk_cd": stock_code,
                "orig_ord_no": original_order_no,
                "cncl_qty": "0" if cancel_all else str(quantity),
                "trde_tp": "0"
            }

            result = self.client.request(
                api_id='kt10003',
                body=body,
                path='/api/dostk/ordr'
            )

            if result and result.get('return_code') == 0:
                logger.info(f"주문 취소 성공: {original_order_no}")
                return {
                    'success': True,
                    'order_no': original_order_no,
                    'cancelled_quantity': quantity if quantity > 0 else 'all',
                    'result': result
                }
            else:
                error_msg = result.get('return_msg', '오류') if result else '응답 없음'
                logger.error(f"주문 취소 실패: {error_msg}")
                return {'success': False, 'error': error_msg}

        except Exception as e:
            logger.error(f"주문 취소 예외: {e}")
            return {'success': False, 'error': str(e)}


class OrderTracker:
    MAX_HISTORY = 1000
    ORDER_EXPIRY_HOURS = 24
    SYNC_INTERVAL_SECONDS = 60

    def __init__(self, execution_api: ExecutionAPI = None):
        self.execution_api = execution_api
        self._orders: Dict[str, OrderRecord] = {}
        self._stock_orders: Dict[str, List[str]] = {}
        self._pending_stocks: set = set()
        self._history: deque = deque(maxlen=self.MAX_HISTORY)
        self._lock = threading.RLock()
        self._last_sync = None
        logger.info("OrderTracker 초기화")

    def register_order(
        self,
        order_no: str,
        stock_code: str,
        side: str,
        quantity: int,
        price: int
    ) -> OrderRecord:
        with self._lock:
            record = OrderRecord(
                order_no=order_no,
                stock_code=stock_code,
                side=side,
                quantity=quantity,
                price=price,
                status=OrderStatus.SUBMITTED
            )
            self._orders[order_no] = record

            if stock_code not in self._stock_orders:
                self._stock_orders[stock_code] = []
            self._stock_orders[stock_code].append(order_no)
            self._pending_stocks.add(stock_code)

            logger.info(f"주문 등록: {order_no} ({stock_code} {side} {quantity}@{price:,})")
            return record

    def update_status(
        self,
        order_no: str,
        status: OrderStatus,
        filled_quantity: int = None,
        filled_price: int = None
    ) -> bool:
        with self._lock:
            record = self._orders.get(order_no)
            if not record:
                logger.debug(f"주문 없음: {order_no}")
                return False

            record.status = status
            record.updated_at = datetime.now()

            if filled_quantity is not None:
                record.filled_quantity = filled_quantity
            if filled_price is not None:
                record.filled_price = filled_price

            if status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
                self._move_to_history(order_no)
                if record.stock_code in self._pending_stocks:
                    active = [o for o in self._stock_orders.get(record.stock_code, [])
                              if o in self._orders and self._orders[o].status == OrderStatus.SUBMITTED]
                    if not active:
                        self._pending_stocks.discard(record.stock_code)

            logger.debug(f"주문 상태 변경: {order_no} -> {status.value}")
            return True

    def _move_to_history(self, order_no: str):
        record = self._orders.pop(order_no, None)
        if record:
            self._history.append(record)
            if record.stock_code in self._stock_orders:
                self._stock_orders[record.stock_code] = [
                    o for o in self._stock_orders[record.stock_code] if o != order_no
                ]

    def has_pending_order(self, stock_code: str) -> bool:
        with self._lock:
            return stock_code in self._pending_stocks

    def get_pending_orders(self, stock_code: str = None) -> List[OrderRecord]:
        with self._lock:
            if stock_code:
                order_nos = self._stock_orders.get(stock_code, [])
                return [self._orders[o] for o in order_nos
                        if o in self._orders and self._orders[o].status == OrderStatus.SUBMITTED]
            return [r for r in self._orders.values() if r.status == OrderStatus.SUBMITTED]

    def get_order(self, order_no: str) -> Optional[OrderRecord]:
        with self._lock:
            return self._orders.get(order_no)

    def sync_with_api(self, force: bool = False) -> int:
        if not self.execution_api:
            return 0

        now = datetime.now()
        if not force and self._last_sync:
            if (now - self._last_sync).total_seconds() < self.SYNC_INTERVAL_SECONDS:
                return 0

        synced = 0
        try:
            outstanding = self.execution_api.get_outstanding_orders()
            if outstanding:
                orders = outstanding.get('ord_list', [])
                api_order_nos = set()

                for order in orders:
                    order_no = order.get('ord_no', '')
                    if not order_no:
                        continue
                    api_order_nos.add(order_no)

                    if order_no not in self._orders:
                        stock_code = order.get('stk_cd', '')
                        side = 'buy' if order.get('sell_tp') == '2' else 'sell'
                        qty = int(order.get('ord_qty', 0))
                        price = int(order.get('ord_uv', 0))
                        self.register_order(order_no, stock_code, side, qty, price)
                        synced += 1

                for order_no, record in list(self._orders.items()):
                    if record.status == OrderStatus.SUBMITTED and order_no not in api_order_nos:
                        self.update_status(order_no, OrderStatus.FILLED)
                        synced += 1

            self._last_sync = now
            if synced > 0:
                logger.info(f"주문 동기화 완료: {synced}건")

        except Exception as e:
            logger.error(f"주문 동기화 오류: {e}")

        return synced

    def cleanup_expired(self) -> int:
        with self._lock:
            cutoff = datetime.now() - timedelta(hours=self.ORDER_EXPIRY_HOURS)
            expired = [o for o, r in self._orders.items() if r.created_at < cutoff]

            for order_no in expired:
                self._move_to_history(order_no)

            if expired:
                logger.info(f"만료 주문 정리: {len(expired)}건")
            return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            status_counts = {}
            for record in self._orders.values():
                status_counts[record.status.value] = status_counts.get(record.status.value, 0) + 1

            return {
                'active_orders': len(self._orders),
                'pending_stocks': len(self._pending_stocks),
                'history_size': len(self._history),
                'status_breakdown': status_counts,
                'last_sync': self._last_sync.isoformat() if self._last_sync else None
            }


__all__ = ['ExecutionAPI', 'OrderTracker', 'OrderStatus', 'OrderRecord']
