"""
AutoTrade Pro - 통합 포지션 관리자
모든 전략에서 공통으로 사용하는 포지션 관리 로직
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from core import Position
from utils.base_manager import BaseManager

logger = logging.getLogger(__name__)


class PositionManager(BaseManager):
    """통합 포지션 관리자"""

    def __init__(self):
        super().__init__(name="PositionManager")
        self.positions: Dict[str, Position] = {}
        self.initialized = False

    def add_position(
        self,
        stock_code: str,
        quantity: int,
        purchase_price: float,
        stock_name: str = "",
        order_id: Optional[str] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        **metadata
    ) -> Position:
        """
        포지션 추가

        Args:
            stock_code: 종목 코드
            quantity: 수량
            purchase_price: 매수가
            stock_name: 종목명
            order_id: 주문 ID
            stop_loss_price: 손절가
            take_profit_price: 익절가
            **metadata: 추가 메타데이터

        Returns:
            추가된 Position 객체
        """
        if stock_code in self.positions:
            logger.warning(f"[{stock_code}] 이미 포지션이 존재합니다. 기존 포지션을 업데이트합니다.")
            # 기존 포지션 업데이트 (평균 단가 계산)
            existing = self.positions[stock_code]
            total_quantity = existing.quantity + quantity
            total_cost = (existing.quantity * existing.purchase_price) + (quantity * purchase_price)
            avg_price = total_cost / total_quantity if total_quantity > 0 else 0

            existing.quantity = total_quantity
            existing.purchase_price = avg_price
            existing.update_current_price(purchase_price)

            return existing
        else:
            # Prepare metadata (include order_id if provided)
            meta = dict(metadata)
            if order_id:
                meta['order_id'] = order_id

            position = Position(
                stock_code=stock_code,
                stock_name=stock_name,
                quantity=quantity,
                purchase_price=purchase_price,
                current_price=purchase_price,
                entry_time=datetime.now(),  # core.Position uses entry_time
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                metadata=meta
            )
            position.update_current_price(purchase_price)

            self.positions[stock_code] = position
            logger.info(f"[{stock_code}] 포지션 추가: {quantity}주 @ {purchase_price:,}원")

            return position

    def remove_position(self, stock_code: str) -> Optional[Position]:
        """
        포지션 제거

        Args:
            stock_code: 종목 코드

        Returns:
            제거된 Position 객체 (없으면 None)
        """
        if stock_code in self.positions:
            position = self.positions.pop(stock_code)
            logger.info(f"[{stock_code}] 포지션 제거: 손익 {position.profit_loss:+,.0f}원 ({position.profit_loss_rate:+.2%})")
            return position
        else:
            logger.warning(f"[{stock_code}] 제거할 포지션이 없습니다.")
            return None

    def update_position_price(self, stock_code: str, current_price: float) -> bool:
        """
        포지션의 현재가 업데이트

        Args:
            stock_code: 종목 코드
            current_price: 현재가

        Returns:
            업데이트 성공 여부
        """
        if stock_code in self.positions:
            self.positions[stock_code].update_current_price(current_price)
            return True
        else:
            logger.warning(f"[{stock_code}] 업데이트할 포지션이 없습니다.")
            return False

    def update_position_quantity(self, stock_code: str, quantity_change: int) -> bool:
        """
        포지션 수량 변경 (부분 청산 등)

        Args:
            stock_code: 종목 코드
            quantity_change: 수량 변화 (음수면 감소)

        Returns:
            업데이트 성공 여부
        """
        if stock_code in self.positions:
            position = self.positions[stock_code]
            new_quantity = position.quantity + quantity_change

            if new_quantity <= 0:
                # 전체 청산
                self.remove_position(stock_code)
            else:
                position.quantity = new_quantity
                position.update_current_price(position.current_price)
                logger.info(f"[{stock_code}] 수량 변경: {quantity_change:+d} -> {new_quantity}주")

            return True
        else:
            logger.warning(f"[{stock_code}] 업데이트할 포지션이 없습니다.")
            return False

    def get_position(self, stock_code: str) -> Optional[Position]:
        """포지션 조회"""
        return self.positions.get(stock_code)

    def has_position(self, stock_code: str) -> bool:
        """포지션 보유 여부"""
        return stock_code in self.positions

    def get_all_positions(self) -> List[Position]:
        """모든 포지션 조회"""
        return list(self.positions.values())

    def get_position_count(self) -> int:
        """보유 포지션 개수"""
        return len(self.positions)

    def get_total_evaluation(self) -> float:
        """총 평가액"""
        return sum(pos.evaluation_amount for pos in self.positions.values())

    def get_total_profit_loss(self) -> float:
        """총 손익"""
        return sum(pos.profit_loss for pos in self.positions.values())

    def get_total_profit_loss_rate(self) -> float:
        """총 수익률"""
        total_cost = sum(pos.quantity * pos.purchase_price for pos in self.positions.values())
        if total_cost > 0:
            return self.get_total_profit_loss() / total_cost
        return 0.0

    def clear_all_positions(self):
        """모든 포지션 초기화"""
        count = len(self.positions)
        self.positions.clear()
        logger.info(f"모든 포지션 초기화: {count}개 제거")

    def initialize(self) -> bool:
        """초기화"""
        self.initialized = True
        self.logger.info("포지션 관리자 초기화 완료")
        return True

    def get_status(self) -> Dict[str, Any]:
        """상태 정보"""
        return {
            **super().get_stats(),
            'position_count': self.get_position_count(),
            'total_evaluation': self.get_total_evaluation(),
            'total_profit_loss': self.get_total_profit_loss(),
            'total_profit_loss_rate': self.get_total_profit_loss_rate()
        }

    def get_positions_summary(self) -> Dict[str, Any]:
        """포지션 요약 정보"""
        return {
            'position_count': self.get_position_count(),
            'total_evaluation': self.get_total_evaluation(),
            'total_profit_loss': self.get_total_profit_loss(),
            'total_profit_loss_rate': self.get_total_profit_loss_rate(),
            'positions': [pos.to_dict() for pos in self.get_all_positions()]
        }

    def check_stop_loss(self, stock_code: str) -> bool:
        """손절가 체크"""
        position = self.get_position(stock_code)
        if position and position.stop_loss_price:
            if position.current_price <= position.stop_loss_price:
                logger.warning(f"[{stock_code}] 손절가 도달: {position.current_price:,} <= {position.stop_loss_price:,}")
                return True
        return False

    def check_take_profit(self, stock_code: str) -> bool:
        """익절가 체크"""
        position = self.get_position(stock_code)
        if position and position.take_profit_price:
            if position.current_price >= position.take_profit_price:
                logger.info(f"[{stock_code}] 익절가 도달: {position.current_price:,} >= {position.take_profit_price:,}")
                return True
        return False

    def update_stop_loss(self, stock_code: str, stop_loss_price: float) -> bool:
        """손절가 변경"""
        if stock_code in self.positions:
            old_price = self.positions[stock_code].stop_loss_price
            self.positions[stock_code].stop_loss_price = stop_loss_price
            logger.info(f"[{stock_code}] 손절가 변경: {old_price:,} -> {stop_loss_price:,}")
            return True
        return False

    def update_take_profit(self, stock_code: str, take_profit_price: float) -> bool:
        """익절가 변경"""
        if stock_code in self.positions:
            old_price = self.positions[stock_code].take_profit_price
            self.positions[stock_code].take_profit_price = take_profit_price
            logger.info(f"[{stock_code}] 익절가 변경: {old_price:,} -> {take_profit_price:,}")
            return True
        return False


# 싱글톤 패턴을 위한 글로벌 인스턴스
_position_manager_instance: Optional[PositionManager] = None


def get_position_manager() -> PositionManager:
    """글로벌 포지션 관리자 인스턴스 반환"""
    global _position_manager_instance
    if _position_manager_instance is None:
        _position_manager_instance = PositionManager()
    return _position_manager_instance
