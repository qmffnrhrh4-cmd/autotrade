"""
Split Order Manager
분할매수/분할매도 시스템

여러 차수로 나뉜 매수와 매도를 추적하고 관리하는 시스템
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "pending"       # 대기 중
    PARTIAL = "partial"       # 부분 체결
    FILLED = "filled"         # 전체 체결
    CANCELLED = "cancelled"   # 취소됨


class SplitType(Enum):
    """분할 타입"""
    BUY = "buy"   # 분할 매수
    SELL = "sell"  # 분할 매도


@dataclass
class SplitOrderEntry:
    """분할 주문 단위"""
    entry_id: str
    order_number: str
    stock_code: str
    quantity: int
    price: float
    status: OrderStatus
    filled_quantity: int = 0
    filled_price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def is_filled(self) -> bool:
        """체결 완료 여부"""
        return self.status == OrderStatus.FILLED

    def fill_ratio(self) -> float:
        """체결 비율"""
        if self.quantity == 0:
            return 0.0
        return self.filled_quantity / self.quantity


@dataclass
class SplitOrderGroup:
    """분할 주문 그룹 (전체 분할매수/분할매도 관리)"""
    group_id: str
    stock_code: str
    stock_name: str
    split_type: SplitType
    total_quantity: int
    entries: List[SplitOrderEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def add_entry(self, entry: SplitOrderEntry):
        """분할 주문 추가"""
        self.entries.append(entry)

    def get_filled_quantity(self) -> int:
        """전체 체결 수량"""
        return sum(entry.filled_quantity for entry in self.entries)

    def get_average_price(self) -> float:
        """평균 체결가"""
        total_amount = sum(
            entry.filled_quantity * entry.filled_price
            for entry in self.entries
            if entry.filled_quantity > 0
        )
        total_quantity = self.get_filled_quantity()

        if total_quantity == 0:
            return 0.0

        return total_amount / total_quantity

    def is_completed(self) -> bool:
        """전체 완료 여부"""
        return all(entry.is_filled() for entry in self.entries)

    def get_completion_ratio(self) -> float:
        """완료 비율"""
        if self.total_quantity == 0:
            return 0.0
        return self.get_filled_quantity() / self.total_quantity

    def get_pending_entries(self) -> List[SplitOrderEntry]:
        """미체결 주문 목록"""
        return [
            entry for entry in self.entries
            if entry.status in [OrderStatus.PENDING, OrderStatus.PARTIAL]
        ]


class SplitOrderManager:
    """
    분할 주문 관리자

    기능:
    - 분할매수 계획 생성
    - 분할매도 계획 생성
    - 주문 추적 및 업데이트
    - 상황에 맞는 동적 조정
    """

    def __init__(self):
        self.active_groups: Dict[str, SplitOrderGroup] = {}
        self.completed_groups: List[SplitOrderGroup] = []

    def create_split_buy_plan(
        self,
        stock_code: str,
        stock_name: str,
        total_quantity: int,
        current_price: float,
        num_splits: int = 3,
        price_gaps: List[float] = None
    ) -> SplitOrderGroup:
        """
        분할 매수 계획 생성

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            total_quantity: 총 매수 수량
            current_price: 현재가
            num_splits: 분할 횟수 (기본 3회)
            price_gaps: 각 분할 간 가격 간격 (% 단위)

        Returns:
            분할 주문 그룹
        """
        if price_gaps is None:
            # 기본 분할 전략: -1%, -2%, -3% 에 각각 매수
            price_gaps = [-0.01, -0.02, -0.03][:num_splits]

        group_id = f"BUY_{stock_code}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        group = SplitOrderGroup(
            group_id=group_id,
            stock_code=stock_code,
            stock_name=stock_name,
            split_type=SplitType.BUY,
            total_quantity=total_quantity
        )

        # 수량을 균등하게 분할 (마지막에 나머지 배정)
        base_qty = total_quantity // num_splits
        remainder = total_quantity % num_splits

        for i in range(num_splits):
            qty = base_qty + (1 if i < remainder else 0)
            price = current_price * (1 + price_gaps[i])

            entry = SplitOrderEntry(
                entry_id=f"{group_id}_ENTRY_{i+1}",
                order_number="",  # 실제 주문 후 설정
                stock_code=stock_code,
                quantity=qty,
                price=price,
                status=OrderStatus.PENDING
            )
            group.add_entry(entry)

        self.active_groups[group_id] = group
        return group

    def create_split_sell_plan(
        self,
        stock_code: str,
        stock_name: str,
        total_quantity: int,
        current_price: float,
        entry_price: float,
        num_splits: int = 3,
        profit_targets: List[float] = None
    ) -> SplitOrderGroup:
        """
        분할 매도 계획 생성

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            total_quantity: 총 매도 수량
            current_price: 현재가
            entry_price: 진입가 (평균 매수가)
            num_splits: 분할 횟수 (기본 3회)
            profit_targets: 각 익절 목표 (% 단위)

        Returns:
            분할 주문 그룹
        """
        if profit_targets is None:
            # 기본 분할 전략: +3%, +5%, +10% 에 각각 매도
            profit_targets = [0.03, 0.05, 0.10][:num_splits]

        group_id = f"SELL_{stock_code}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        group = SplitOrderGroup(
            group_id=group_id,
            stock_code=stock_code,
            stock_name=stock_name,
            split_type=SplitType.SELL,
            total_quantity=total_quantity
        )

        # 수량을 균등하게 분할 (마지막에 나머지 배정)
        base_qty = total_quantity // num_splits
        remainder = total_quantity % num_splits

        for i in range(num_splits):
            qty = base_qty + (1 if i < remainder else 0)
            price = entry_price * (1 + profit_targets[i])

            entry = SplitOrderEntry(
                entry_id=f"{group_id}_ENTRY_{i+1}",
                order_number="",  # 실제 주문 후 설정
                stock_code=stock_code,
                quantity=qty,
                price=price,
                status=OrderStatus.PENDING
            )
            group.add_entry(entry)

        self.active_groups[group_id] = group
        return group

    def update_entry_status(
        self,
        group_id: str,
        entry_id: str,
        order_number: str,
        filled_quantity: int,
        filled_price: float,
        status: OrderStatus
    ):
        """
        주문 상태 업데이트

        Args:
            group_id: 그룹 ID
            entry_id: 주문 ID
            order_number: 실제 주문 번호
            filled_quantity: 체결 수량
            filled_price: 체결가
            status: 주문 상태
        """
        if group_id not in self.active_groups:
            return

        group = self.active_groups[group_id]
        for entry in group.entries:
            if entry.entry_id == entry_id:
                entry.order_number = order_number
                entry.filled_quantity = filled_quantity
                entry.filled_price = filled_price
                entry.status = status
                break

        # 그룹 전체가 완료되었는지 확인
        if group.is_completed():
            group.completed_at = datetime.now()
            self.completed_groups.append(group)
            del self.active_groups[group_id]

    def get_group_status(self, group_id: str) -> Optional[Dict]:
        """
        그룹 상태 조회

        Args:
            group_id: 그룹 ID

        Returns:
            그룹 상태 정보
        """
        group = self.active_groups.get(group_id)
        if not group:
            return None

        return {
            'group_id': group.group_id,
            'stock_code': group.stock_code,
            'stock_name': group.stock_name,
            'split_type': group.split_type.value,
            'total_quantity': group.total_quantity,
            'filled_quantity': group.get_filled_quantity(),
            'average_price': group.get_average_price(),
            'completion_ratio': group.get_completion_ratio(),
            'is_completed': group.is_completed(),
            'entries': [
                {
                    'entry_id': entry.entry_id,
                    'order_number': entry.order_number,
                    'quantity': entry.quantity,
                    'price': entry.price,
                    'filled_quantity': entry.filled_quantity,
                    'filled_price': entry.filled_price,
                    'status': entry.status.value,
                    'fill_ratio': entry.fill_ratio()
                }
                for entry in group.entries
            ]
        }

    def cancel_pending_entries(self, group_id: str):
        """
        대기 중인 주문 취소

        Args:
            group_id: 그룹 ID
        """
        if group_id not in self.active_groups:
            return

        group = self.active_groups[group_id]
        for entry in group.entries:
            if entry.status == OrderStatus.PENDING:
                entry.status = OrderStatus.CANCELLED


# Singleton instance
_split_order_manager = None


def get_split_order_manager() -> SplitOrderManager:
    """Get split order manager singleton"""
    global _split_order_manager
    if _split_order_manager is None:
        _split_order_manager = SplitOrderManager()
    return _split_order_manager


__all__ = [
    'SplitOrderManager',
    'SplitOrderGroup',
    'SplitOrderEntry',
    'OrderStatus',
    'SplitType',
    'get_split_order_manager'
]
