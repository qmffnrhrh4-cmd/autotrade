"""
virtual_trading/scheduler.py
가상매매 백그라운드 스케줄러

실시간 가격 업데이트, 자동 손절/익절 체크, 독립적인 자동 매매
"""
import time
import logging
import threading
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class VirtualTradingScheduler:
    """가상매매 백그라운드 스케줄러"""

    def __init__(self, virtual_manager, data_fetcher=None, bot_instance=None):
        """
        Args:
            virtual_manager: VirtualTradingManager 인스턴스
            data_fetcher: DataFetcher 인스턴스 (가격 조회용)
            bot_instance: AutoTradingBot 인스턴스 (독립 매매용)
        """
        self.virtual_manager = virtual_manager
        self.data_fetcher = data_fetcher
        self.bot_instance = bot_instance  # Fix v6.1.4: 독립적인 매매를 위한 bot 참조
        self.is_running = False
        self.update_thread = None
        self.check_thread = None
        self.trading_thread = None  # Fix v6.1.4: 자동 매매 스레드

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

        # Fix v6.1.4: 독립적인 자동 매매 스레드 (60초마다)
        if self.bot_instance:
            self.trading_thread = threading.Thread(
                target=self._auto_trading_loop,
                daemon=True
            )
            self.trading_thread.start()
            logger.info("✅ 가상매매 독립 매매 스레드 시작")

        logger.info("가상매매 스케줄러 시작")

    def stop(self):
        """스케줄러 중지"""
        self.is_running = False

        if self.update_thread:
            self.update_thread.join(timeout=2)

        if self.check_thread:
            self.check_thread.join(timeout=2)

        if self.trading_thread:
            self.trading_thread.join(timeout=2)

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

    def _auto_trading_loop(self):
        """
        독립적인 자동 매매 루프 (60초마다)
        Fix v6.1.4: 실제 매매 없이도 가상매매가 독립적으로 실행
        """
        logger.info("🤖 가상매매 독립 매매 스레드 시작")

        # 첫 실행은 30초 후 (초기화 완료 대기)
        time.sleep(30)

        while self.is_running:
            try:
                self._execute_virtual_trading()
            except Exception as e:
                logger.error(f"가상매매 자동 실행 실패: {e}", exc_info=True)

            # 60초 대기
            time.sleep(60)

    def _execute_virtual_trading(self):
        """
        가상매매 실행: 시장 스캔 → 분석 → 매수/매도 결정
        """
        # 장 시간 체크
        from utils.trading_date import is_any_trading_hours
        if not is_any_trading_hours():
            logger.debug("장외 시간 - 가상매매 건너뛰기")
            return

        # bot_instance가 없으면 실행 불가
        if not self.bot_instance:
            return

        # screener와 scoring_system이 없으면 실행 불가
        if not hasattr(self.bot_instance, 'screener') or not self.bot_instance.screener:
            logger.debug("Screener 없음 - 가상매매 건너뛰기")
            return

        if not hasattr(self.bot_instance, 'scoring_system') or not self.bot_instance.scoring_system:
            logger.debug("Scoring system 없음 - 가상매매 건너뛰기")
            return

        logger.info("🔍 가상매매: 시장 스캔 시작")

        try:
            # 1. 시장 스캔 (후보 종목 찾기)
            candidates = self._scan_market()

            if not candidates:
                logger.info("가상매매: 매수 후보 없음")
                return

            logger.info(f"가상매매: {len(candidates)}개 매수 후보 발견")

            # 2. 각 전략별로 매수 실행
            strategies = self.virtual_manager.db.get_all_strategies()

            if not strategies:
                logger.warning("가상매매: 전략 없음")
                return

            for strategy in strategies:
                self._try_buy_for_strategy(strategy, candidates)

        except Exception as e:
            logger.error(f"가상매매 실행 중 오류: {e}", exc_info=True)

    def _scan_market(self) -> List[Dict[str, Any]]:
        """
        시장 스캔하여 매수 후보 종목 찾기
        """
        try:
            # Screener를 사용하여 후보 종목 찾기
            screener = self.bot_instance.screener
            scoring_system = self.bot_instance.scoring_system

            # 시장 스캔 (상위 20개)
            candidates = screener.scan_market(limit=20)

            if not candidates:
                return []

            # 스코어링
            scored_candidates = []
            for candidate in candidates:
                try:
                    score = scoring_system.calculate_score(
                        stock_code=candidate['stock_code'],
                        stock_name=candidate.get('stock_name', ''),
                        data=candidate
                    )

                    if score > 60:  # 60점 이상만
                        scored_candidates.append({
                            **candidate,
                            'score': score
                        })
                except Exception as e:
                    logger.debug(f"스코어링 실패 ({candidate.get('stock_code')}): {e}")

            # 점수 높은 순으로 정렬
            scored_candidates.sort(key=lambda x: x['score'], reverse=True)

            return scored_candidates[:5]  # 상위 5개만

        except Exception as e:
            logger.error(f"시장 스캔 실패: {e}")
            return []

    def _try_buy_for_strategy(self, strategy: Dict[str, Any], candidates: List[Dict[str, Any]]):
        """
        특정 전략으로 매수 시도
        """
        strategy_id = strategy['id']
        strategy_name = strategy['name']

        try:
            # 해당 전략의 활성 포지션 확인
            positions = [p for p in self.virtual_manager.get_positions()
                        if p.get('strategy_id') == strategy_id]

            # 최대 3개 포지션까지
            if len(positions) >= 3:
                logger.debug(f"가상매매 ({strategy_name}): 포지션 가득참 ({len(positions)}/3)")
                return

            # 전략의 잔고 확인
            strategy_info = self.virtual_manager.get_strategy_performance(strategy_id)
            available_cash = strategy_info.get('current_capital', 0) - strategy_info.get('total_investment', 0)

            if available_cash < 100000:  # 10만원 미만
                logger.debug(f"가상매매 ({strategy_name}): 잔고 부족 ({available_cash:,}원)")
                return

            # 이미 보유한 종목은 제외
            held_codes = {p['stock_code'] for p in positions}
            available_candidates = [c for c in candidates if c['stock_code'] not in held_codes]

            if not available_candidates:
                logger.debug(f"가상매매 ({strategy_name}): 매수 가능한 종목 없음")
                return

            # 첫 번째 후보 매수
            candidate = available_candidates[0]
            stock_code = candidate['stock_code']
            stock_name = candidate.get('stock_name', stock_code)
            current_price = candidate.get('current_price', 0)

            if current_price <= 0:
                # 현재가 조회
                if self.data_fetcher:
                    price_info = self.data_fetcher.get_current_price(stock_code)
                    if price_info:
                        current_price = price_info.get('current_price', 0)

            if current_price <= 0:
                logger.warning(f"가상매매: 현재가 조회 실패 ({stock_code})")
                return

            # 매수 수량 계산 (자본의 30% 또는 사용 가능 금액 중 작은 값)
            target_amount = min(available_cash, strategy_info.get('current_capital', 1000000) * 0.3)
            quantity = int(target_amount // current_price)

            if quantity < 1:
                logger.debug(f"가상매매 ({strategy_name}): 수량 부족 (금액: {target_amount:,}원, 가격: {current_price:,}원)")
                return

            # 가상 매수 실행
            logger.info(f"🎯 가상매매 ({strategy_name}): {stock_name} {quantity}주 매수 시도 @ {current_price:,}원")

            result = self.virtual_manager.execute_buy(
                strategy_id=strategy_id,
                stock_code=stock_code,
                stock_name=stock_name,
                quantity=quantity,
                price=float(current_price),
                stop_loss_percent=5.0,
                take_profit_percent=10.0,
                use_split=False  # 독립 매매는 분할 안함
            )

            if result:
                logger.info(f"✅ 가상매매 ({strategy_name}): {stock_name} 매수 성공!")
            else:
                logger.warning(f"⚠️ 가상매매 ({strategy_name}): {stock_name} 매수 실패")

        except Exception as e:
            logger.error(f"가상매매 ({strategy_name}) 매수 시도 실패: {e}", exc_info=True)

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
            'trading_thread_alive': self.trading_thread.is_alive() if self.trading_thread else False,
            'positions_count': len(self.virtual_manager.get_positions()) if self.virtual_manager else 0
        }
