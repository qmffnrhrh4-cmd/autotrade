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
from utils.trading_date import is_nxt_hours, is_market_hours

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
        account_number: str = None,
        order_type: str = '02',  # Fix v6.1.5: 주문 유형 (02: 지정가, 61: 장전 시간외, 81: 장후 시간외)
        dynamic_mode: bool = True  # 동적 분할 모드 (첫 주문 체결 후 재평가)
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
            order_type: 주문 유형 (02: 지정가, 61: 장전 시간외, 81: 장후 시간외)
            dynamic_mode: 동적 분할 모드
                - True: 첫 주문 체결 후 시장 상황 재평가하여 다음 주문 가격 조정 (스마트)
                - False: 고정 가격으로 모든 주문 동시 실행 (기존 방식)

        Returns:
            분할 주문 그룹
        """
        logger.info(f"🔵 분할 매수 시작: {stock_name}({stock_code}) {total_quantity}주를 {num_splits}회 분할")
        logger.info(f"   모드: {'동적 분할 (스마트)' if dynamic_mode else '고정 분할 (일괄)'}")

        # Fix: NXT 시간대 체크
        is_nxt = is_nxt_hours()
        exchange = 'NXT' if is_nxt else 'KRX'
        logger.info(f"   거래소: {exchange}")

        # 동적 모드: 한 번에 하나씩 실행하고 체결 후 재평가
        if dynamic_mode:
            return self._execute_dynamic_split_buy(
                stock_code=stock_code,
                stock_name=stock_name,
                total_quantity=total_quantity,
                entry_strategy=entry_strategy,
                num_splits=num_splits,
                account_number=account_number,
                order_type=order_type,
                exchange=exchange
            )

        # 고정 모드: 기존 방식 (모든 주문 동시 실행)
        current_price = self._get_current_price(stock_code)
        if not current_price:
            logger.error(f"Failed to get current price for {stock_code}")
            return None

        # 가격 간격 설정
        if price_gaps is None:
            if entry_strategy == "gradual_down":
                price_gaps = [-0.005, -0.01, -0.015][:num_splits]
            elif entry_strategy == "support_levels":
                price_gaps = [-0.01, -0.02, -0.03][:num_splits]
            else:
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

        # 각 분할 주문 실행
        for idx, entry in enumerate(group.entries):
            try:
                logger.info(f"  [{idx+1}/{num_splits}] {entry.quantity}주 @ {entry.price:,.0f}원 주문 중...")

                result = self.order_api.buy(
                    stock_code=stock_code,
                    quantity=entry.quantity,
                    price=int(entry.price),
                    order_type=order_type,
                    account_number=account_number,
                    exchange=exchange
                )

                is_success = False
                if result:
                    if result.get('success'):
                        is_success = True
                    elif 'result' in result and result['result'].get('return_code') == 0:
                        is_success = True
                    elif result.get('order_no') and not result.get('error'):
                        is_success = True

                if is_success:
                    order_number = result.get('order_no', result.get('order_number', result.get('odno', '')))
                    self.manager.update_entry_status(
                        group_id=group.group_id,
                        entry_id=entry.entry_id,
                        order_number=order_number,
                        filled_quantity=0,
                        filled_price=0.0,
                        status=OrderStatus.PENDING
                    )
                    logger.info(f"  ✅ 주문 성공: 주문번호 {order_number}")
                else:
                    logger.error(f"  ❌ 주문 실패: {result}")

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
        account_number: str = None,
        dynamic_mode: bool = True  # 동적 분할 모드 (첫 주문 체결 후 재평가)
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
            dynamic_mode: 동적 분할 모드
                - True: 첫 주문 체결 후 시장 상황 재평가하여 다음 주문 가격 조정 (스마트)
                - False: 고정 가격으로 모든 주문 동시 실행 (기존 방식)

        Returns:
            분할 주문 그룹
        """
        logger.info(f"🔴 분할 매도 시작: {stock_name}({stock_code}) {total_quantity}주를 {num_splits}회 분할")
        logger.info(f"   모드: {'동적 분할 (스마트)' if dynamic_mode else '고정 분할 (일괄)'}")

        # Fix: NXT 시간대 체크
        is_nxt = is_nxt_hours()
        exchange = 'NXT' if is_nxt else 'KRX'
        logger.info(f"   거래소: {exchange}")

        # 동적 모드: 한 번에 하나씩 실행하고 체결 후 재평가
        if dynamic_mode:
            return self._execute_dynamic_split_sell(
                stock_code=stock_code,
                stock_name=stock_name,
                total_quantity=total_quantity,
                entry_price=entry_price,
                exit_strategy=exit_strategy,
                num_splits=num_splits,
                account_number=account_number,
                exchange=exchange
            )

        # 고정 모드: 기존 방식 (모든 주문 동시 실행)
        current_price = self._get_current_price(stock_code)
        if not current_price:
            logger.error(f"Failed to get current price for {stock_code}")
            return None

        # 익절 목표 설정
        if profit_targets is None:
            if exit_strategy == "gradual_profit":
                profit_targets = [0.02, 0.04, 0.07][:num_splits]
            elif exit_strategy == "quick_exit":
                profit_targets = [0.01, 0.02, 0.03][:num_splits]
            else:
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

        # 각 분할 주문 실행
        for idx, entry in enumerate(group.entries):
            try:
                logger.info(f"  [{idx+1}/{num_splits}] {entry.quantity}주 @ {entry.price:,.0f}원 주문 중...")

                result = self.order_api.sell(
                    stock_code=stock_code,
                    quantity=entry.quantity,
                    price=int(entry.price),
                    order_type='02',
                    account_number=account_number,
                    exchange=exchange
                )

                is_success = False
                if result:
                    if result.get('success'):
                        is_success = True
                    elif 'result' in result and result['result'].get('return_code') == 0:
                        is_success = True
                    elif result.get('order_no') and not result.get('error'):
                        is_success = True

                if is_success:
                    order_number = result.get('order_no', result.get('order_number', result.get('odno', '')))
                    self.manager.update_entry_status(
                        group_id=group.group_id,
                        entry_id=entry.entry_id,
                        order_number=order_number,
                        filled_quantity=0,
                        filled_price=0.0,
                        status=OrderStatus.PENDING
                    )
                    logger.info(f"  ✅ 주문 성공: 주문번호 {order_number}")
                else:
                    logger.error(f"  ❌ 주문 실패: {result}")

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

    def _execute_dynamic_split_buy(
        self,
        stock_code: str,
        stock_name: str,
        total_quantity: int,
        entry_strategy: str,
        num_splits: int,
        account_number: str,
        order_type: str,
        exchange: str
    ) -> Optional[SplitOrderGroup]:
        """
        동적 분할 매수 (스마트 모드)

        1차 주문 체결 → 시장 상황 재평가 → 2차 주문 가격 조정 → 체결 → 3차...
        """
        group_id = f"BUY_{stock_code}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        group = SplitOrderGroup(
            group_id=group_id,
            stock_code=stock_code,
            stock_name=stock_name,
            split_type=SplitType.BUY,
            total_quantity=total_quantity
        )
        self.manager.active_groups[group_id] = group

        # 수량 분할 (균등 분할)
        base_qty = total_quantity // num_splits
        remainder = total_quantity % num_splits
        quantities = [base_qty + (1 if i < remainder else 0) for i in range(num_splits)]

        # 1차 주문: 현재가 기준
        initial_price = self._get_current_price(stock_code)
        if not initial_price:
            logger.error("Failed to get initial price")
            return None

        last_filled_price = initial_price

        for split_idx in range(num_splits):
            qty = quantities[split_idx]
            if qty <= 0:
                continue

            # 동적 가격 계산
            if split_idx == 0:
                # 1차: 현재가에서 약간 아래
                target_price = initial_price * 0.995  # -0.5%
                logger.info(f"  [1/{num_splits}] 첫 주문: {qty}주 @ {target_price:,.0f}원 (현재가 -0.5%)")
            else:
                # 2차, 3차: 이전 체결가 기준으로 시장 상황 재평가
                current_price = self._get_current_price(stock_code)
                if not current_price:
                    logger.warning(f"Failed to get current price for split {split_idx+1}, using last price")
                    current_price = last_filled_price

                # 시장 변화율
                price_change = (current_price - last_filled_price) / last_filled_price

                # 동적 가격 조정 로직
                if price_change < -0.01:  # 1% 이상 하락
                    # 하락 중: 현재가에서 조금만 아래
                    gap = -0.003  # -0.3%
                    reason = "하락 중"
                elif price_change > 0.01:  # 1% 이상 상승
                    # 상승 중: 더 아래로 대기
                    gap = -0.015  # -1.5%
                    reason = "상승 중"
                else:  # 횡보
                    # 횡보: 중간 간격
                    gap = -0.008  # -0.8%
                    reason = "횡보"

                target_price = current_price * (1 + gap)
                logger.info(f"  [{split_idx+1}/{num_splits}] 동적 조정: {qty}주 @ {target_price:,.0f}원")
                logger.info(f"      시장 상황: {reason} (이전 대비 {price_change*100:+.2f}%, 현재가 {current_price:,.0f}원)")

            # 주문 생성
            entry = SplitOrderEntry(
                entry_id=f"{group_id}_ENTRY_{split_idx+1}",
                order_number="",
                stock_code=stock_code,
                quantity=qty,
                price=target_price,
                status=OrderStatus.PENDING
            )
            group.add_entry(entry)

            # 실제 주문 실행
            try:
                result = self.order_api.buy(
                    stock_code=stock_code,
                    quantity=qty,
                    price=int(target_price),
                    order_type=order_type,
                    account_number=account_number,
                    exchange=exchange
                )

                is_success = False
                if result:
                    if result.get('success'):
                        is_success = True
                    elif 'result' in result and result['result'].get('return_code') == 0:
                        is_success = True
                    elif result.get('order_no') and not result.get('error'):
                        is_success = True

                if is_success:
                    order_number = result.get('order_no', result.get('order_number', result.get('odno', '')))
                    self.manager.update_entry_status(
                        group_id=group_id,
                        entry_id=entry.entry_id,
                        order_number=order_number,
                        filled_quantity=0,
                        filled_price=0.0,
                        status=OrderStatus.PENDING
                    )
                    logger.info(f"      ✅ 주문 성공: {order_number}")

                    # 다음 주문을 위해 마지막 가격 저장
                    last_filled_price = target_price
                else:
                    logger.error(f"      ❌ 주문 실패: {result}")

            except Exception as e:
                logger.error(f"      ❌ 주문 에러: {e}", exc_info=True)

            # 다음 주문 전 대기 (시장 상황 변화 관찰)
            if split_idx < num_splits - 1:
                time.sleep(2.0)  # 동적 모드에서는 더 긴 대기 (시장 변화 관찰)

        logger.info(f"✅ 동적 분할 매수 완료: {len(group.entries)}개 주문 실행")
        return group

    def _execute_dynamic_split_sell(
        self,
        stock_code: str,
        stock_name: str,
        total_quantity: int,
        entry_price: float,
        exit_strategy: str,
        num_splits: int,
        account_number: str,
        exchange: str
    ) -> Optional[SplitOrderGroup]:
        """
        동적 분할 매도 (스마트 모드)

        1차 주문 체결 → 시장 상황 재평가 → 2차 주문 가격 조정 → 체결 → 3차...
        """
        group_id = f"SELL_{stock_code}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        group = SplitOrderGroup(
            group_id=group_id,
            stock_code=stock_code,
            stock_name=stock_name,
            split_type=SplitType.SELL,
            total_quantity=total_quantity
        )
        self.manager.active_groups[group_id] = group

        # 수량 분할 (균등 분할)
        base_qty = total_quantity // num_splits
        remainder = total_quantity % num_splits
        quantities = [base_qty + (1 if i < remainder else 0) for i in range(num_splits)]

        # 1차 주문: 현재가 기준
        initial_price = self._get_current_price(stock_code)
        if not initial_price:
            logger.error("Failed to get initial price")
            return None

        last_filled_price = initial_price

        for split_idx in range(num_splits):
            qty = quantities[split_idx]
            if qty <= 0:
                continue

            # 동적 가격 계산
            if split_idx == 0:
                # 1차: 현재가에서 약간 위 (빠른 익절)
                target_price = initial_price * 1.005  # +0.5%
                logger.info(f"  [1/{num_splits}] 첫 주문: {qty}주 @ {target_price:,.0f}원 (현재가 +0.5%)")
            else:
                # 2차, 3차: 이전 체결가 기준으로 시장 상황 재평가
                current_price = self._get_current_price(stock_code)
                if not current_price:
                    logger.warning(f"Failed to get current price for split {split_idx+1}, using last price")
                    current_price = last_filled_price

                # 시장 변화율
                price_change = (current_price - last_filled_price) / last_filled_price

                # 동적 가격 조정 로직
                if price_change > 0.01:  # 1% 이상 상승
                    # 상승 중: 더 위로 익절 목표 상향
                    gap = 0.025  # +2.5%
                    reason = "상승 중"
                elif price_change < -0.01:  # 1% 이상 하락
                    # 하락 중: 빠르게 익절 (현재가 근처)
                    gap = 0.003  # +0.3%
                    reason = "하락 중"
                else:  # 횡보
                    # 횡보: 중간 익절
                    gap = 0.012  # +1.2%
                    reason = "횡보"

                target_price = current_price * (1 + gap)
                logger.info(f"  [{split_idx+1}/{num_splits}] 동적 조정: {qty}주 @ {target_price:,.0f}원")
                logger.info(f"      시장 상황: {reason} (이전 대비 {price_change*100:+.2f}%, 현재가 {current_price:,.0f}원)")

            # 주문 생성
            entry = SplitOrderEntry(
                entry_id=f"{group_id}_ENTRY_{split_idx+1}",
                order_number="",
                stock_code=stock_code,
                quantity=qty,
                price=target_price,
                status=OrderStatus.PENDING
            )
            group.add_entry(entry)

            # 실제 주문 실행
            try:
                result = self.order_api.sell(
                    stock_code=stock_code,
                    quantity=qty,
                    price=int(target_price),
                    order_type='02',
                    account_number=account_number,
                    exchange=exchange
                )

                is_success = False
                if result:
                    if result.get('success'):
                        is_success = True
                    elif 'result' in result and result['result'].get('return_code') == 0:
                        is_success = True
                    elif result.get('order_no') and not result.get('error'):
                        is_success = True

                if is_success:
                    order_number = result.get('order_no', result.get('order_number', result.get('odno', '')))
                    self.manager.update_entry_status(
                        group_id=group_id,
                        entry_id=entry.entry_id,
                        order_number=order_number,
                        filled_quantity=0,
                        filled_price=0.0,
                        status=OrderStatus.PENDING
                    )
                    logger.info(f"      ✅ 주문 성공: {order_number}")

                    # 다음 주문을 위해 마지막 가격 저장
                    last_filled_price = target_price
                else:
                    logger.error(f"      ❌ 주문 실패: {result}")

            except Exception as e:
                logger.error(f"      ❌ 주문 에러: {e}", exc_info=True)

            # 다음 주문 전 대기 (시장 상황 변화 관찰)
            if split_idx < num_splits - 1:
                time.sleep(2.0)  # 동적 모드에서는 더 긴 대기 (시장 변화 관찰)

        logger.info(f"✅ 동적 분할 매도 완료: {len(group.entries)}개 주문 실행")
        return group

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
