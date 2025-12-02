"""
Trade Coordinator - 통합 거래 코디네이터
중앙 집중식 거래 관리, 부분 청산, 분할 주문 지원
"""
import time
import threading
import uuid
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

from utils.logger_new import get_logger

logger = get_logger()


class OrderType(Enum):
    """주문 유형"""
    BUY = "buy"
    SELL = "sell"
    PARTIAL_CLOSE = "partial_close"


class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ExecutionStrategy(Enum):
    """실행 전략"""
    IMMEDIATE = "immediate"      # 즉시 실행
    SPLIT_TIME = "split_time"    # 시간 분할
    SPLIT_SIZE = "split_size"    # 수량 분할
    VWAP = "vwap"                # VWAP 추종
    TWAP = "twap"                # TWAP 추종


@dataclass
class TradeOrder:
    """거래 주문"""
    order_id: str
    stock_code: str
    stock_name: str
    order_type: OrderType
    total_quantity: int
    target_price: int
    status: OrderStatus = OrderStatus.PENDING
    execution_strategy: ExecutionStrategy = ExecutionStrategy.IMMEDIATE
    split_count: int = 1
    executed_quantity: int = 0
    executed_amount: int = 0
    avg_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    splits: List['SplitOrder'] = field(default_factory=list)
    error_message: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class SplitOrder:
    """분할 주문"""
    split_id: str
    parent_order_id: str
    sequence: int
    quantity: int
    price: int
    status: OrderStatus = OrderStatus.PENDING
    order_no: str = ""
    executed_quantity: int = 0
    executed_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None


@dataclass
class Position:
    """포지션"""
    position_id: str
    stock_code: str
    stock_name: str
    total_quantity: int
    remaining_quantity: int
    entry_price: float
    current_price: float = 0.0
    entry_time: datetime = field(default_factory=datetime.now)
    partial_closes: List[Dict] = field(default_factory=list)

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.entry_price) * self.remaining_quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0
        return (self.current_price - self.entry_price) / self.entry_price * 100


class TradeCoordinator:
    """통합 거래 코디네이터

    특징:
    - 중앙 집중식 거래 관리
    - 부분 청산 지원
    - 분할 주문 관리
    - 주문 상태 추적
    - 실행 전략 지원
    """

    def __init__(self, order_api=None):
        self.order_api = order_api
        self._lock = threading.RLock()

        # 주문 관리
        self._orders: Dict[str, TradeOrder] = {}
        self._positions: Dict[str, Position] = {}

        # 실행 대기열
        self._execution_queue: deque = deque()
        self._queue_lock = threading.Lock()

        # 콜백
        self._on_order_filled_callbacks: List[Callable] = []
        self._on_partial_fill_callbacks: List[Callable] = []
        self._on_order_failed_callbacks: List[Callable] = []

        # 스레드
        self._running = False
        self._stop_event = threading.Event()
        self._executor_thread: Optional[threading.Thread] = None

        # 통계
        self._stats = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'partial_closes': 0,
            'splits_executed': 0
        }

        logger.info("TradeCoordinator 초기화")

    def set_order_api(self, order_api):
        """Order API 설정"""
        self.order_api = order_api

    # === 주문 생성 ===

    def create_buy_order(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: int,
        strategy: ExecutionStrategy = ExecutionStrategy.IMMEDIATE,
        split_count: int = 1,
        metadata: Dict = None
    ) -> str:
        """매수 주문 생성

        Returns:
            주문 ID
        """
        order_id = self._generate_order_id()

        order = TradeOrder(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_name,
            order_type=OrderType.BUY,
            total_quantity=quantity,
            target_price=price,
            execution_strategy=strategy,
            split_count=split_count,
            metadata=metadata or {}
        )

        # 분할 주문 생성
        if split_count > 1:
            order.splits = self._create_splits(order)

        with self._lock:
            self._orders[order_id] = order
            self._stats['total_orders'] += 1

        # 실행 대기열에 추가
        with self._queue_lock:
            self._execution_queue.append(order_id)

        logger.info(f"매수 주문 생성: {order_id} ({stock_name} {quantity}주 @ {price:,}원)")
        return order_id

    def create_sell_order(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: int,
        position_id: str = None,
        strategy: ExecutionStrategy = ExecutionStrategy.IMMEDIATE,
        split_count: int = 1,
        metadata: Dict = None
    ) -> str:
        """매도 주문 생성"""
        order_id = self._generate_order_id()

        order = TradeOrder(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_name,
            order_type=OrderType.SELL,
            total_quantity=quantity,
            target_price=price,
            execution_strategy=strategy,
            split_count=split_count,
            metadata={**(metadata or {}), 'position_id': position_id}
        )

        if split_count > 1:
            order.splits = self._create_splits(order)

        with self._lock:
            self._orders[order_id] = order
            self._stats['total_orders'] += 1

        with self._queue_lock:
            self._execution_queue.append(order_id)

        logger.info(f"매도 주문 생성: {order_id} ({stock_name} {quantity}주 @ {price:,}원)")
        return order_id

    def create_partial_close(
        self,
        position_id: str,
        close_ratio: float,
        price: int,
        reason: str = ""
    ) -> Optional[str]:
        """부분 청산 주문 생성

        Args:
            position_id: 포지션 ID
            close_ratio: 청산 비율 (0.0 ~ 1.0)
            price: 청산 가격
            reason: 청산 사유

        Returns:
            주문 ID
        """
        with self._lock:
            position = self._positions.get(position_id)
            if not position:
                logger.warning(f"포지션 찾을 수 없음: {position_id}")
                return None

            if position.remaining_quantity <= 0:
                logger.warning(f"청산할 수량 없음: {position_id}")
                return None

            close_quantity = int(position.remaining_quantity * close_ratio)
            if close_quantity <= 0:
                return None

        order_id = self._generate_order_id()

        order = TradeOrder(
            order_id=order_id,
            stock_code=position.stock_code,
            stock_name=position.stock_name,
            order_type=OrderType.PARTIAL_CLOSE,
            total_quantity=close_quantity,
            target_price=price,
            metadata={
                'position_id': position_id,
                'close_ratio': close_ratio,
                'reason': reason
            }
        )

        with self._lock:
            self._orders[order_id] = order
            self._stats['total_orders'] += 1
            self._stats['partial_closes'] += 1

        with self._queue_lock:
            self._execution_queue.append(order_id)

        logger.info(f"부분 청산 주문: {order_id} ({position.stock_name} {close_quantity}주, {close_ratio*100:.0f}%)")
        return order_id

    def _create_splits(self, order: TradeOrder) -> List[SplitOrder]:
        """분할 주문 생성"""
        splits = []
        base_quantity = order.total_quantity // order.split_count
        remainder = order.total_quantity % order.split_count

        for i in range(order.split_count):
            quantity = base_quantity + (1 if i < remainder else 0)
            if quantity <= 0:
                continue

            split = SplitOrder(
                split_id=f"{order.order_id}_split_{i+1}",
                parent_order_id=order.order_id,
                sequence=i + 1,
                quantity=quantity,
                price=order.target_price
            )
            splits.append(split)

        return splits

    def _generate_order_id(self) -> str:
        """주문 ID 생성"""
        return f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # === 주문 실행 ===

    def start(self):
        """실행 엔진 시작"""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        self._executor_thread = threading.Thread(
            target=self._executor_loop,
            name="TradeCoordinator-Executor",
            daemon=True
        )
        self._executor_thread.start()

        logger.info("TradeCoordinator 시작")

    def stop(self):
        """실행 엔진 중지"""
        self._running = False
        self._stop_event.set()

        if self._executor_thread:
            self._executor_thread.join(timeout=5)

        logger.info("TradeCoordinator 중지")

    def _executor_loop(self):
        """실행 루프"""
        while self._running:
            try:
                order_id = None

                with self._queue_lock:
                    if self._execution_queue:
                        order_id = self._execution_queue.popleft()

                if order_id:
                    self._execute_order(order_id)

                self._stop_event.wait(timeout=0.1)

            except Exception as e:
                logger.error(f"실행 루프 오류: {e}")
                time.sleep(1)

    def _execute_order(self, order_id: str):
        """주문 실행"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order or order.status not in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
                return

            order.status = OrderStatus.SUBMITTED
            order.submitted_at = datetime.now()

        try:
            if order.splits:
                # 분할 주문 실행
                self._execute_split_order(order)
            else:
                # 단일 주문 실행
                self._execute_single_order(order)

        except Exception as e:
            self._handle_order_failure(order, str(e))

    def _execute_single_order(self, order: TradeOrder):
        """단일 주문 실행"""
        if not self.order_api:
            self._handle_order_failure(order, "Order API 없음")
            return

        try:
            if order.order_type in [OrderType.BUY]:
                result = self.order_api.buy(
                    stock_code=order.stock_code,
                    quantity=order.total_quantity,
                    price=order.target_price
                )
            else:  # SELL or PARTIAL_CLOSE
                result = self.order_api.sell(
                    stock_code=order.stock_code,
                    quantity=order.total_quantity,
                    price=order.target_price
                )

            if result and result.get('order_no'):
                self._handle_order_success(order, result)
            else:
                self._handle_order_failure(order, "주문 응답 없음")

        except Exception as e:
            self._handle_order_failure(order, str(e))

    def _execute_split_order(self, order: TradeOrder):
        """분할 주문 실행"""
        for split in order.splits:
            if split.status != OrderStatus.PENDING:
                continue

            try:
                if order.order_type in [OrderType.BUY]:
                    result = self.order_api.buy(
                        stock_code=order.stock_code,
                        quantity=split.quantity,
                        price=split.price
                    )
                else:
                    result = self.order_api.sell(
                        stock_code=order.stock_code,
                        quantity=split.quantity,
                        price=split.price
                    )

                if result and result.get('order_no'):
                    split.status = OrderStatus.FILLED
                    split.order_no = result.get('order_no', '')
                    split.executed_quantity = split.quantity
                    split.executed_price = split.price
                    split.executed_at = datetime.now()

                    order.executed_quantity += split.quantity
                    order.executed_amount += split.quantity * split.price
                    self._stats['splits_executed'] += 1
                else:
                    split.status = OrderStatus.FAILED

                # 분할 간 대기
                time.sleep(0.5)

            except Exception as e:
                split.status = OrderStatus.FAILED
                logger.error(f"분할 주문 실패 ({split.split_id}): {e}")

        # 주문 상태 업데이트
        self._finalize_split_order(order)

    def _finalize_split_order(self, order: TradeOrder):
        """분할 주문 최종화"""
        filled_count = sum(1 for s in order.splits if s.status == OrderStatus.FILLED)
        total_count = len(order.splits)

        if filled_count == total_count:
            order.status = OrderStatus.FILLED
            order.avg_price = order.executed_amount / order.executed_quantity if order.executed_quantity > 0 else 0
            order.completed_at = datetime.now()
            self._stats['successful_orders'] += 1
            self._notify_order_filled(order)

        elif filled_count > 0:
            order.status = OrderStatus.PARTIALLY_FILLED
            self._notify_partial_fill(order)

        else:
            order.status = OrderStatus.FAILED
            self._stats['failed_orders'] += 1
            self._notify_order_failed(order)

    def _handle_order_success(self, order: TradeOrder, result: Dict):
        """주문 성공 처리"""
        with self._lock:
            order.status = OrderStatus.FILLED
            order.executed_quantity = order.total_quantity
            order.executed_amount = order.total_quantity * order.target_price
            order.avg_price = order.target_price
            order.completed_at = datetime.now()
            self._stats['successful_orders'] += 1

            # 포지션 업데이트
            if order.order_type == OrderType.BUY:
                self._add_position(order)
            elif order.order_type in [OrderType.SELL, OrderType.PARTIAL_CLOSE]:
                self._update_position_on_sell(order)

        self._notify_order_filled(order)
        logger.info(f"주문 체결: {order.order_id} ({order.stock_name})")

    def _handle_order_failure(self, order: TradeOrder, error: str):
        """주문 실패 처리"""
        with self._lock:
            order.status = OrderStatus.FAILED
            order.error_message = error[:200]
            order.completed_at = datetime.now()
            self._stats['failed_orders'] += 1

        self._notify_order_failed(order)
        logger.error(f"주문 실패: {order.order_id} - {error}")

    # === 포지션 관리 ===

    def _add_position(self, order: TradeOrder):
        """포지션 추가"""
        position_id = f"POS_{order.stock_code}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        position = Position(
            position_id=position_id,
            stock_code=order.stock_code,
            stock_name=order.stock_name,
            total_quantity=order.executed_quantity,
            remaining_quantity=order.executed_quantity,
            entry_price=order.avg_price
        )

        self._positions[position_id] = position

    def _update_position_on_sell(self, order: TradeOrder):
        """매도 시 포지션 업데이트"""
        position_id = order.metadata.get('position_id')

        if position_id and position_id in self._positions:
            position = self._positions[position_id]
            position.remaining_quantity -= order.executed_quantity

            if order.order_type == OrderType.PARTIAL_CLOSE:
                position.partial_closes.append({
                    'quantity': order.executed_quantity,
                    'price': order.avg_price,
                    'time': datetime.now().isoformat(),
                    'reason': order.metadata.get('reason', '')
                })

            # 전량 청산 시 포지션 제거
            if position.remaining_quantity <= 0:
                del self._positions[position_id]

    def add_external_position(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        entry_price: float
    ) -> str:
        """외부 포지션 등록 (기존 보유 종목)"""
        position_id = f"POS_{stock_code}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        position = Position(
            position_id=position_id,
            stock_code=stock_code,
            stock_name=stock_name,
            total_quantity=quantity,
            remaining_quantity=quantity,
            entry_price=entry_price
        )

        with self._lock:
            self._positions[position_id] = position

        return position_id

    def update_position_price(self, position_id: str, current_price: float):
        """포지션 현재가 업데이트"""
        with self._lock:
            if position_id in self._positions:
                self._positions[position_id].current_price = current_price

    # === 콜백 ===

    def _notify_order_filled(self, order: TradeOrder):
        for callback in self._on_order_filled_callbacks:
            try:
                callback(order)
            except Exception as e:
                logger.error(f"체결 콜백 오류: {e}")

    def _notify_partial_fill(self, order: TradeOrder):
        for callback in self._on_partial_fill_callbacks:
            try:
                callback(order)
            except Exception as e:
                logger.error(f"부분 체결 콜백 오류: {e}")

    def _notify_order_failed(self, order: TradeOrder):
        for callback in self._on_order_failed_callbacks:
            try:
                callback(order)
            except Exception as e:
                logger.error(f"실패 콜백 오류: {e}")

    def on_order_filled(self, callback: Callable):
        self._on_order_filled_callbacks.append(callback)

    def on_partial_fill(self, callback: Callable):
        self._on_partial_fill_callbacks.append(callback)

    def on_order_failed(self, callback: Callable):
        self._on_order_failed_callbacks.append(callback)

    # === 조회 ===

    def get_order(self, order_id: str) -> Optional[Dict]:
        """주문 조회"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                return None

            return {
                'order_id': order.order_id,
                'stock_code': order.stock_code,
                'stock_name': order.stock_name,
                'order_type': order.order_type.value,
                'total_quantity': order.total_quantity,
                'executed_quantity': order.executed_quantity,
                'target_price': order.target_price,
                'avg_price': order.avg_price,
                'status': order.status.value,
                'created_at': order.created_at.isoformat(),
                'completed_at': order.completed_at.isoformat() if order.completed_at else None,
                'error_message': order.error_message
            }

    def get_position(self, position_id: str) -> Optional[Dict]:
        """포지션 조회"""
        with self._lock:
            position = self._positions.get(position_id)
            if not position:
                return None

            return {
                'position_id': position.position_id,
                'stock_code': position.stock_code,
                'stock_name': position.stock_name,
                'total_quantity': position.total_quantity,
                'remaining_quantity': position.remaining_quantity,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'unrealized_pnl': position.unrealized_pnl,
                'unrealized_pnl_pct': position.unrealized_pnl_pct,
                'partial_closes': position.partial_closes
            }

    def get_all_positions(self) -> List[Dict]:
        """모든 포지션 조회"""
        with self._lock:
            return [self.get_position(pid) for pid in self._positions.keys()]

    def get_stats(self) -> Dict:
        """통계 반환"""
        with self._lock:
            stats = self._stats.copy()
            stats['active_orders'] = sum(
                1 for o in self._orders.values()
                if o.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
            )
            stats['open_positions'] = len(self._positions)
            stats['queue_size'] = len(self._execution_queue)
            stats['running'] = self._running
        return stats


# 싱글톤 인스턴스
_coordinator: Optional[TradeCoordinator] = None
_instance_lock = threading.Lock()


def get_trade_coordinator(order_api=None) -> TradeCoordinator:
    """TradeCoordinator 싱글톤 인스턴스 반환"""
    global _coordinator

    with _instance_lock:
        if _coordinator is None:
            _coordinator = TradeCoordinator(order_api=order_api)
        elif order_api:
            _coordinator.set_order_api(order_api)

    return _coordinator
