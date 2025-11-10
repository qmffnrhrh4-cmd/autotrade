"""
virtual_trading/scheduler.py
가상매매 백그라운드 스케줄러

실시간 가격 업데이트, 자동 손절/익절 체크
"""
import time
import logging
import threading
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class VirtualTradingScheduler:
    """가상매매 백그라운드 스케줄러"""

    def __init__(self, virtual_manager, data_fetcher=None):
        """
        Args:
            virtual_manager: VirtualTradingManager 인스턴스
            data_fetcher: DataFetcher 인스턴스 (가격 조회용)
        """
        self.virtual_manager = virtual_manager
        self.data_fetcher = data_fetcher
        self.is_running = False
        self.update_thread = None
        self.check_thread = None

        logger.info("가상매매 스케줄러 초기화")

    def start(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return

        self.is_running = True

        # 가격 업데이트 스레드 (5초마다)
        self.update_thread = threading.Thread(
            target=self._price_update_loop,
            daemon=True
        )
        self.update_thread.start()

        # 손절/익절 체크 스레드 (5초마다)
        self.check_thread = threading.Thread(
            target=self._stop_loss_take_profit_loop,
            daemon=True
        )
        self.check_thread.start()

        logger.info("가상매매 스케줄러 시작")

    def stop(self):
        """스케줄러 중지"""
        self.is_running = False

        if self.update_thread:
            self.update_thread.join(timeout=2)

        if self.check_thread:
            self.check_thread.join(timeout=2)

        logger.info("가상매매 스케줄러 중지")

    def _price_update_loop(self):
        """가격 업데이트 루프 (5초마다)"""
        logger.info("가격 업데이트 스레드 시작")

        while self.is_running:
            try:
                self._update_prices()
            except Exception as e:
                logger.error(f"가격 업데이트 실패: {e}")

            # 5초 대기
            time.sleep(5)

    def _stop_loss_take_profit_loop(self):
        """손절/익절 체크 루프 (5초마다)"""
        logger.info("손절/익절 체크 스레드 시작")

        while self.is_running:
            try:
                self._check_stop_loss_take_profit()
            except Exception as e:
                logger.error(f"손절/익절 체크 실패: {e}")

            # 5초 대기
            time.sleep(5)

    def _update_prices(self):
        """활성 포지션의 현재가 업데이트"""
        try:
            # 모든 활성 포지션 조회
            positions = self.virtual_manager.get_positions()

            if not positions:
                return

            # 종목별 현재가 수집
            price_updates = {}

            for position in positions:
                stock_code = position['stock_code']

                # 이미 조회한 종목은 스킵
                if stock_code in price_updates:
                    continue

                # 현재가 조회
                if self.data_fetcher:
                    try:
                        price_info = self.data_fetcher.get_current_price(stock_code)
                        if price_info and 'current_price' in price_info:
                            price_updates[stock_code] = price_info['current_price']
                    except Exception as e:
                        logger.debug(f"{stock_code} 가격 조회 실패: {e}")

            # 가격 업데이트
            if price_updates:
                self.virtual_manager.update_prices(price_updates)
                logger.debug(f"가격 업데이트: {len(price_updates)}개 종목")

        except Exception as e:
            logger.error(f"가격 업데이트 중 오류: {e}", exc_info=True)

    def _check_stop_loss_take_profit(self):
        """자동 손절/익절 조건 체크 및 실행"""
        try:
            executed_orders = self.virtual_manager.check_stop_loss_take_profit()

            if executed_orders:
                logger.info(f"자동 매도 실행: {len(executed_orders)}건")

                for order in executed_orders:
                    order_type = order['type']
                    stock_name = order['stock_name']
                    profit = order['profit']

                    type_text = '손절' if order_type == 'stop_loss' else '익절'
                    logger.info(
                        f"  [{type_text}] {stock_name}: "
                        f"{profit:+,.0f}원 @ {order['sell_price']:,}원"
                    )

        except Exception as e:
            logger.error(f"손절/익절 체크 중 오류: {e}", exc_info=True)

    def get_status(self) -> Dict[str, Any]:
        """스케줄러 상태 조회"""
        return {
            'is_running': self.is_running,
            'update_thread_alive': self.update_thread.is_alive() if self.update_thread else False,
            'check_thread_alive': self.check_thread.is_alive() if self.check_thread else False,
            'positions_count': len(self.virtual_manager.get_positions()) if self.virtual_manager else 0
        }
