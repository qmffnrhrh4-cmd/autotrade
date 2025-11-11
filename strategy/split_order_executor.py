"""
Split Order Executor
분할 주문 실행기 - 실제 API 연동

OrderAPI와 통합하여 분할매수/분할매도를 실제로 실행
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import time

from .split_order_manager import (
    SplitOrderManager,
    SplitOrderGroup,
    SplitOrderEntry,
    OrderStatus,
    SplitType,
    get_split_order_manager
)

logger = logging.getLogger(__name__)


class SplitOrderExecutor:
    """
    분할 주문 실행기

    SplitOrderManager와 OrderAPI를 연결하여 실제 분할 주문 실행
    """

    def __init__(self, order_api, data_fetcher=None):
        """
        Args:
            order_api: OrderAPI 인스턴스
            data_fetcher: DataFetcher 인스턴스 (현재가 조회용)
        """
        self.order_api = order_api
        self.data_fetcher = data_fetcher
        self.manager = get_split_order_manager()

    def execute_split_buy(
        self,
        stock_code: str,
        stock_name: str,
        total_quantity: int,
        entry_strategy: str = "gradual_down",
        num_splits: int = 3,
        price_gaps: List[float] = None,
        account_number: str = None
    ) -> Optional[SplitOrderGroup]:
        """
        분할 매수 실행

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            total_quantity: 총 매수 수량
            entry_strategy: 진입 전략
                - "gradual_down": 점진적 하락 시 분할 매수 (기본)
                - "immediate": 즉시 전량 매수
                - "support_levels": 지지선 기반 분할 매수
            num_splits: 분할 횟수
            price_gaps: 가격 간격 (% 단위), None이면 전략에 따라 자동 계산
            account_number: 계좌번호

        Returns:
            분할 주문 그룹
        """
        # 현재가 조회
        current_price = self._get_current_price(stock_code)
        if not current_price:
            logger.error(f"Failed to get current price for {stock_code}")
            return None

        # 가격 간격 설정
        if price_gaps is None:
            if entry_strategy == "gradual_down":
                # 하락 시 분할 매수: -0.5%, -1.0%, -1.5%
                price_gaps = [-0.005, -0.01, -0.015][:num_splits]
            elif entry_strategy == "support_levels":
                # 지지선 기반: -1%, -2%, -3%
                price_gaps = [-0.01, -0.02, -0.03][:num_splits]
            else:  # immediate
                # 즉시 매수: 현재가
                price_gaps = [0.0] * num_splits

        # 분할 매수 계획 생성
        group = self.manager.create_split_buy_plan(
            stock_code=stock_code,
            stock_name=stock_name,
            total_quantity=total_quantity,
            current_price=current_price,
            num_splits=num_splits,
            price_gaps=price_gaps
        )

        logger.info(f"🔵 분할 매수 시작: {stock_name}({stock_code}) {total_quantity}주를 {num_splits}회 분할")

        # 각 분할 주문 실행
        for idx, entry in enumerate(group.entries):
            try:
                logger.info(f"  [{idx+1}/{num_splits}] {entry.quantity}주 @ {entry.price:,.0f}원 주문 중...")

                # 실제 매수 주문 실행
                result = self.order_api.buy(
                    stock_code=stock_code,
                    quantity=entry.quantity,
                    price=int(entry.price),
                    order_type='02',  # 지정가
                    account_number=account_number
                )

                if result and result.get('success'):
                    order_number = result.get('order_number', result.get('odno', ''))

                    # 주문 상태 업데이트
                    self.manager.update_entry_status(
                        group_id=group.group_id,
                        entry_id=entry.entry_id,
                        order_number=order_number,
                        filled_quantity=0,  # 초기에는 0
                        filled_price=0.0,
                        status=OrderStatus.PENDING
                    )

                    logger.info(f"  ✅ 주문 성공: 주문번호 {order_number}")
                else:
                    logger.error(f"  ❌ 주문 실패: {result}")

                # 주문 간 딜레이 (시스템 부하 방지)
                if idx < len(group.entries) - 1:
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"  ❌ 주문 실행 에러: {e}", exc_info=True)

        return group

    def execute_split_sell(
        self,
        stock_code: str,
        stock_name: str,
        total_quantity: int,
        entry_price: float,
        exit_strategy: str = "gradual_profit",
        num_splits: int = 3,
        profit_targets: List[float] = None,
        account_number: str = None
    ) -> Optional[SplitOrderGroup]:
        """
        분할 매도 실행

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            total_quantity: 총 매도 수량
            entry_price: 진입가 (평균 매수가)
            exit_strategy: 탈출 전략
                - "gradual_profit": 점진적 익절 (기본)
                - "quick_exit": 빠른 익절
                - "trailing": 트레일링 익절
            num_splits: 분할 횟수
            profit_targets: 익절 목표 (% 단위), None이면 전략에 따라 자동 계산
            account_number: 계좌번호

        Returns:
            분할 주문 그룹
        """
        # 현재가 조회
        current_price = self._get_current_price(stock_code)
        if not current_price:
            logger.error(f"Failed to get current price for {stock_code}")
            return None

        # 익절 목표 설정
        if profit_targets is None:
            if exit_strategy == "gradual_profit":
                # 점진적 익절: +2%, +4%, +7%
                profit_targets = [0.02, 0.04, 0.07][:num_splits]
            elif exit_strategy == "quick_exit":
                # 빠른 익절: +1%, +2%, +3%
                profit_targets = [0.01, 0.02, 0.03][:num_splits]
            else:  # trailing
                # 트레일링: +3%, +6%, +10%
                profit_targets = [0.03, 0.06, 0.10][:num_splits]

        # 분할 매도 계획 생성
        group = self.manager.create_split_sell_plan(
            stock_code=stock_code,
            stock_name=stock_name,
            total_quantity=total_quantity,
            current_price=current_price,
            entry_price=entry_price,
            num_splits=num_splits,
            profit_targets=profit_targets
        )

        logger.info(f"🔴 분할 매도 시작: {stock_name}({stock_code}) {total_quantity}주를 {num_splits}회 분할")

        # 각 분할 주문 실행
        for idx, entry in enumerate(group.entries):
            try:
                logger.info(f"  [{idx+1}/{num_splits}] {entry.quantity}주 @ {entry.price:,.0f}원 주문 중...")

                # 실제 매도 주문 실행
                result = self.order_api.sell(
                    stock_code=stock_code,
                    quantity=entry.quantity,
                    price=int(entry.price),
                    order_type='02',  # 지정가
                    account_number=account_number
                )

                if result and result.get('success'):
                    order_number = result.get('order_number', result.get('odno', ''))

                    # 주문 상태 업데이트
                    self.manager.update_entry_status(
                        group_id=group.group_id,
                        entry_id=entry.entry_id,
                        order_number=order_number,
                        filled_quantity=0,  # 초기에는 0
                        filled_price=0.0,
                        status=OrderStatus.PENDING
                    )

                    logger.info(f"  ✅ 주문 성공: 주문번호 {order_number}")
                else:
                    logger.error(f"  ❌ 주문 실패: {result}")

                # 주문 간 딜레이
                if idx < len(group.entries) - 1:
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"  ❌ 주문 실행 에러: {e}", exc_info=True)

        return group

    def update_order_fills(self, group_id: str) -> bool:
        """
        주문 체결 상태 업데이트

        Args:
            group_id: 그룹 ID

        Returns:
            업데이트 성공 여부
        """
        if group_id not in self.manager.active_groups:
            return False

        group = self.manager.active_groups[group_id]

        # 미체결 주문들의 상태 확인
        for entry in group.get_pending_entries():
            if not entry.order_number:
                continue

            try:
                # TODO: 실제 주문 체결 조회 API 호출
                # order_status = self.order_api.get_order_status(entry.order_number)
                # 현재는 시뮬레이션

                # 체결 정보 업데이트 (실제로는 API 응답에서 가져옴)
                # self.manager.update_entry_status(
                #     group_id=group_id,
                #     entry_id=entry.entry_id,
                #     order_number=entry.order_number,
                #     filled_quantity=체결수량,
                #     filled_price=체결가,
                #     status=OrderStatus.FILLED if 전량체결 else OrderStatus.PARTIAL
                # )

                pass

            except Exception as e:
                logger.error(f"Order status update error: {e}")

        return True

    def cancel_group(self, group_id: str) -> bool:
        """
        그룹 내 모든 대기 주문 취소

        Args:
            group_id: 그룹 ID

        Returns:
            취소 성공 여부
        """
        if group_id not in self.manager.active_groups:
            return False

        group = self.manager.active_groups[group_id]

        logger.info(f"🛑 분할 주문 그룹 취소: {group_id}")

        # 미체결 주문들 취소
        for entry in group.get_pending_entries():
            if not entry.order_number:
                continue

            try:
                # 실제 주문 취소 API 호출
                result = self.order_api.cancel_order(
                    order_number=entry.order_number
                )

                if result and result.get('success'):
                    logger.info(f"  ✅ 주문 취소 성공: {entry.order_number}")

                    # 상태 업데이트
                    self.manager.update_entry_status(
                        group_id=group_id,
                        entry_id=entry.entry_id,
                        order_number=entry.order_number,
                        filled_quantity=entry.filled_quantity,
                        filled_price=entry.filled_price,
                        status=OrderStatus.CANCELLED
                    )
                else:
                    logger.error(f"  ❌ 주문 취소 실패: {entry.order_number}")

            except Exception as e:
                logger.error(f"Order cancel error: {e}", exc_info=True)

        return True

    def _get_current_price(self, stock_code: str) -> Optional[float]:
        """현재가 조회"""
        if not self.data_fetcher:
            logger.warning("DataFetcher not available, using fallback price")
            return 10000.0  # 임시 가격

        try:
            price_info = self.data_fetcher.get_current_price(stock_code)
            if price_info:
                return float(price_info.get('stck_prpr', 10000))
        except Exception as e:
            logger.error(f"Failed to get current price: {e}")

        return None


__all__ = ['SplitOrderExecutor']
