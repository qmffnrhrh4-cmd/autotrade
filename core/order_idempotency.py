"""
Order Idempotency System - 주문 중복 방지 시스템
멱등성 키 기반 중복 주문 방지
"""
import uuid
import time
import threading
import hashlib
from typing import Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from utils.logger_new import get_logger

logger = get_logger()


class OrderState(Enum):
    """주문 상태"""
    PENDING = "pending"       # 주문 진행 중
    COMPLETED = "completed"   # 완료
    FAILED = "failed"         # 실패
    EXPIRED = "expired"       # 만료


@dataclass
class IdempotencyRecord:
    """멱등성 기록"""
    idempotency_key: str
    stock_code: str
    order_type: str  # 'buy' or 'sell'
    quantity: int
    price: int
    state: OrderState = OrderState.PENDING
    order_no: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: str = ""
    retry_count: int = 0

    @property
    def is_expired(self) -> bool:
        """10분 후 만료"""
        return (datetime.now() - self.created_at).total_seconds() > 600

    @property
    def can_retry(self) -> bool:
        """재시도 가능 여부 (실패 시 최대 3회)"""
        return self.state == OrderState.FAILED and self.retry_count < 3


class OrderIdempotencyManager:
    """주문 멱등성 관리자

    특징:
    - 중복 주문 방지
    - 멱등성 키 기반 추적
    - 자동 만료 및 정리
    - 재시도 관리
    """

    def __init__(self, dedup_window_seconds: float = 60.0):
        self.dedup_window = dedup_window_seconds

        # 멱등성 기록: {idempotency_key: IdempotencyRecord}
        self._records: Dict[str, IdempotencyRecord] = {}
        self._lock = threading.RLock()

        # 최근 주문 해시 (빠른 중복 체크)
        self._recent_order_hashes: Dict[str, datetime] = {}
        self._hash_lock = threading.Lock()

        # 통계
        self._stats = {
            'orders_processed': 0,
            'duplicates_blocked': 0,
            'retries': 0
        }

        logger.info(f"OrderIdempotencyManager 초기화 (dedup_window={dedup_window_seconds}s)")

    def generate_idempotency_key(self, stock_code: str, order_type: str,
                                  quantity: int, price: int) -> str:
        """멱등성 키 생성

        Args:
            stock_code: 종목 코드
            order_type: 주문 유형 ('buy' or 'sell')
            quantity: 수량
            price: 가격

        Returns:
            고유한 멱등성 키
        """
        # UUID + 타임스탬프 기반 고유 키
        unique_part = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime("%H%M%S%f")
        return f"{stock_code}_{order_type}_{quantity}_{price}_{timestamp}_{unique_part}"

    def _compute_order_hash(self, stock_code: str, order_type: str,
                            quantity: int, price: int) -> str:
        """주문 해시 계산 (빠른 중복 체크용)"""
        data = f"{stock_code}:{order_type}:{quantity}:{price}"
        return hashlib.md5(data.encode()).hexdigest()

    def is_duplicate(self, stock_code: str, order_type: str,
                     quantity: int, price: int) -> Tuple[bool, Optional[str]]:
        """중복 주문 체크

        Args:
            stock_code: 종목 코드
            order_type: 주문 유형
            quantity: 수량
            price: 가격

        Returns:
            (중복 여부, 기존 멱등성 키 또는 None)
        """
        order_hash = self._compute_order_hash(stock_code, order_type, quantity, price)

        with self._hash_lock:
            if order_hash in self._recent_order_hashes:
                last_time = self._recent_order_hashes[order_hash]
                if (datetime.now() - last_time).total_seconds() < self.dedup_window:
                    self._stats['duplicates_blocked'] += 1
                    logger.warning(
                        f"중복 주문 감지: {stock_code} {order_type} {quantity}주 @ {price:,}원"
                    )

                    # 해당 기록 찾기
                    with self._lock:
                        for key, record in self._records.items():
                            if (record.stock_code == stock_code and
                                record.order_type == order_type and
                                record.quantity == quantity and
                                record.price == price and
                                not record.is_expired):
                                return True, key

                    return True, None

        return False, None

    def start_order(self, stock_code: str, order_type: str,
                    quantity: int, price: int) -> Optional[str]:
        """주문 시작 등록

        Args:
            stock_code: 종목 코드
            order_type: 주문 유형
            quantity: 수량
            price: 가격

        Returns:
            멱등성 키 (중복이면 None)
        """
        # 중복 체크
        is_dup, existing_key = self.is_duplicate(stock_code, order_type, quantity, price)
        if is_dup:
            return None

        # 새 멱등성 키 생성
        idempotency_key = self.generate_idempotency_key(stock_code, order_type, quantity, price)

        # 기록 저장
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            stock_code=stock_code,
            order_type=order_type,
            quantity=quantity,
            price=price
        )

        with self._lock:
            self._records[idempotency_key] = record

        # 해시 기록
        order_hash = self._compute_order_hash(stock_code, order_type, quantity, price)
        with self._hash_lock:
            self._recent_order_hashes[order_hash] = datetime.now()

        self._stats['orders_processed'] += 1
        logger.debug(f"주문 시작: {idempotency_key}")

        return idempotency_key

    def complete_order(self, idempotency_key: str, order_no: str) -> bool:
        """주문 완료 처리

        Args:
            idempotency_key: 멱등성 키
            order_no: 주문 번호

        Returns:
            성공 여부
        """
        with self._lock:
            record = self._records.get(idempotency_key)
            if not record:
                logger.warning(f"멱등성 키 찾을 수 없음: {idempotency_key}")
                return False

            record.state = OrderState.COMPLETED
            record.order_no = order_no
            record.completed_at = datetime.now()

        logger.debug(f"주문 완료: {idempotency_key} -> {order_no}")
        return True

    def fail_order(self, idempotency_key: str, error_message: str) -> bool:
        """주문 실패 처리

        Args:
            idempotency_key: 멱등성 키
            error_message: 에러 메시지

        Returns:
            성공 여부
        """
        with self._lock:
            record = self._records.get(idempotency_key)
            if not record:
                logger.warning(f"멱등성 키 찾을 수 없음: {idempotency_key}")
                return False

            record.state = OrderState.FAILED
            record.error_message = error_message
            record.completed_at = datetime.now()

        logger.debug(f"주문 실패: {idempotency_key} - {error_message}")
        return True

    def retry_order(self, idempotency_key: str) -> bool:
        """주문 재시도

        Args:
            idempotency_key: 멱등성 키

        Returns:
            재시도 가능 여부
        """
        with self._lock:
            record = self._records.get(idempotency_key)
            if not record:
                return False

            if not record.can_retry:
                logger.warning(f"재시도 불가: {idempotency_key} (retry_count={record.retry_count})")
                return False

            record.state = OrderState.PENDING
            record.retry_count += 1
            record.error_message = ""
            self._stats['retries'] += 1

        logger.debug(f"주문 재시도: {idempotency_key} (attempt {record.retry_count})")
        return True

    def get_order_status(self, idempotency_key: str) -> Optional[Dict]:
        """주문 상태 조회"""
        with self._lock:
            record = self._records.get(idempotency_key)
            if not record:
                return None

            return {
                'idempotency_key': record.idempotency_key,
                'stock_code': record.stock_code,
                'order_type': record.order_type,
                'quantity': record.quantity,
                'price': record.price,
                'state': record.state.value,
                'order_no': record.order_no,
                'created_at': record.created_at.isoformat(),
                'completed_at': record.completed_at.isoformat() if record.completed_at else None,
                'error_message': record.error_message,
                'retry_count': record.retry_count
            }

    def has_pending_order(self, stock_code: str, order_type: str = None) -> bool:
        """진행 중인 주문 존재 여부 확인

        Args:
            stock_code: 종목 코드
            order_type: 주문 유형 (None이면 모든 유형)

        Returns:
            진행 중인 주문 존재 여부
        """
        with self._lock:
            for record in self._records.values():
                if record.stock_code != stock_code:
                    continue
                if order_type and record.order_type != order_type:
                    continue
                if record.state == OrderState.PENDING and not record.is_expired:
                    return True
        return False

    def cleanup_expired(self) -> int:
        """만료된 기록 정리"""
        count = 0

        with self._lock:
            expired_keys = [
                key for key, record in self._records.items()
                if record.is_expired
            ]
            for key in expired_keys:
                del self._records[key]
                count += 1

        with self._hash_lock:
            cutoff = datetime.now() - timedelta(seconds=self.dedup_window)
            expired_hashes = [
                h for h, t in self._recent_order_hashes.items()
                if t < cutoff
            ]
            for h in expired_hashes:
                del self._recent_order_hashes[h]

        if count > 0:
            logger.debug(f"만료된 멱등성 기록 정리: {count}개")

        return count

    def get_stats(self) -> Dict:
        """통계 반환"""
        with self._lock:
            stats = self._stats.copy()
            stats['pending_orders'] = sum(
                1 for r in self._records.values()
                if r.state == OrderState.PENDING and not r.is_expired
            )
            stats['total_records'] = len(self._records)

        with self._hash_lock:
            stats['recent_hashes'] = len(self._recent_order_hashes)

        return stats


# 싱글톤 인스턴스
_order_idempotency: Optional[OrderIdempotencyManager] = None
_instance_lock = threading.Lock()


def get_order_idempotency() -> OrderIdempotencyManager:
    """OrderIdempotencyManager 싱글톤 인스턴스 반환"""
    global _order_idempotency

    with _instance_lock:
        if _order_idempotency is None:
            _order_idempotency = OrderIdempotencyManager()

    return _order_idempotency
