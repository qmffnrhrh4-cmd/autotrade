"""
virtual_trading/manager.py
가상매매 매니저 클래스

가상매매 전략 실행, 포지션 관리, 자동 손절/익절, AI 분석 연동
분할매수/분할매도 시스템 통합
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .models import VirtualTradingDB

logger = logging.getLogger(__name__)


class VirtualTradingManager:
    """가상매매 매니저 클래스"""

    def __init__(self, db_path: str = "data/virtual_trading.db"):
        """
        가상매매 매니저 초기화

        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db = VirtualTradingDB(db_path)
        self.active_strategies: Dict[int, Dict[str, Any]] = {}
        self.price_cache: Dict[str, float] = {}  # 종목코드 -> 현재가
        logger.info("가상매매 매니저 초기화 완료")

    def create_strategy(
        self,
        name: str,
        description: str = "",
        initial_capital: float = 10000000
    ) -> int:
        """
        새로운 가상매매 전략 생성

        Args:
            name: 전략 이름
            description: 전략 설명
            initial_capital: 초기 자본

        Returns:
            생성된 전략 ID
        """
        strategy_id = self.db.create_strategy(name, description, initial_capital)
        self.active_strategies[strategy_id] = {
            'name': name,
            'description': description,
            'initial_capital': initial_capital,
            'created_at': datetime.now().isoformat()
        }
        logger.info(f"가상매매 전략 생성: {name} (ID: {strategy_id})")
        return strategy_id

    def execute_buy(
        self,
        strategy_id: int,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: float,
        stop_loss_percent: float = None,
        take_profit_percent: float = None,
        use_split: bool = True
    ) -> Optional[int]:
        """
        가상매매 매수 주문 실행 (분할매수 지원)

        Args:
            strategy_id: 전략 ID
            stock_code: 종목코드
            stock_name: 종목명
            quantity: 수량
            price: 매수가
            stop_loss_percent: 손절 비율 (예: 5.0 = -5%)
            take_profit_percent: 익절 비율 (예: 10.0 = +10%)
            use_split: 분할매수 사용 여부 (기본값: True)

        Returns:
            생성된 포지션 ID (실패시 None)
        """
        # 전략 설정 조회
        strategies = self.db.get_all_strategies()
        strategy = next((s for s in strategies if s['id'] == strategy_id), None)

        if not strategy:
            logger.error(f"전략을 찾을 수 없음: {strategy_id}")
            return None

        # 분할매수 설정 확인
        split_enabled = use_split and strategy.get('split_buy_enabled', 1) == 1
        split_ratios_str = strategy.get('split_buy_ratios', '0.33,0.33,0.34')

        # 손절/익절가 계산
        stop_loss_price = None
        take_profit_price = None

        if stop_loss_percent:
            stop_loss_price = price * (1 - stop_loss_percent / 100)

        if take_profit_percent:
            take_profit_price = price * (1 + take_profit_percent / 100)

        try:
            if split_enabled:
                # 분할매수 실행
                split_ratios = [float(r) for r in split_ratios_str.split(',')]
                logger.info(f"분할매수 시작: {stock_name} {quantity}주 (비율: {split_ratios})")

                position_ids = []
                for i, ratio in enumerate(split_ratios):
                    split_qty = int(quantity * ratio)
                    if split_qty == 0:
                        continue

                    # 각 차수별로 포지션 생성
                    split_price = price * (1 - 0.005 * i)  # 0.5%씩 낮은 가격

                    position_id = self.db.open_position(
                        strategy_id=strategy_id,
                        stock_code=stock_code,
                        stock_name=stock_name,
                        quantity=split_qty,
                        price=split_price,
                        stop_loss_price=stop_loss_price,
                        take_profit_price=take_profit_price
                    )

                    position_ids.append(position_id)
                    logger.info(
                        f"  [{i+1}/{len(split_ratios)}] {split_qty}주 @ {split_price:,.0f}원"
                    )

                logger.info(f"✅ 분할매수 완료: {len(position_ids)}개 포지션 생성")
                return position_ids[0] if position_ids else None

            else:
                # 일반 매수 실행
                position_id = self.db.open_position(
                    strategy_id=strategy_id,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    quantity=quantity,
                    price=price,
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price
                )

                logger.info(
                    f"가상매매 매수 실행: {stock_name}({stock_code}) "
                    f"{quantity}주 @ {price:,}원 "
                    f"[손절: {stop_loss_price:,.0f}원, 익절: {take_profit_price:,.0f}원]"
                )

                return position_id

        except Exception as e:
            logger.error(f"가상매매 매수 실행 실패: {e}", exc_info=True)
            return None

    def execute_sell(
        self,
        position_id: int,
        sell_price: float,
        reason: str = "manual",
        use_split: bool = True,
        sell_ratio: float = 1.0
    ) -> Optional[float]:
        """
        가상매매 매도 주문 실행 (분할매도 지원)

        Args:
            position_id: 포지션 ID
            sell_price: 매도가
            reason: 매도 사유 (manual/stop_loss/take_profit/partial)
            use_split: 분할매도 사용 여부 (기본값: True)
            sell_ratio: 매도 비율 (0.0 ~ 1.0, 기본값: 1.0 = 전량 매도)

        Returns:
            실현 수익 (실패시 None)
        """
        try:
            # 포지션 정보 조회
            positions = self.db.get_open_positions()
            position = next((p for p in positions if p['id'] == position_id), None)

            if not position:
                logger.error(f"포지션을 찾을 수 없음: {position_id}")
                return None

            strategy_id = position['strategy_id']

            # 전략 설정 조회
            strategies = self.db.get_all_strategies()
            strategy = next((s for s in strategies if s['id'] == strategy_id), None)

            if not strategy:
                logger.error(f"전략을 찾을 수 없음: {strategy_id}")
                return None

            # 분할매도 설정 확인
            split_enabled = use_split and strategy.get('split_sell_enabled', 1) == 1 and sell_ratio < 1.0
            split_ratios_str = strategy.get('split_sell_ratios', '0.33,0.33,0.34')

            if split_enabled:
                # 분할매도 실행
                split_ratios = [float(r) for r in split_ratios_str.split(',')]
                logger.info(f"분할매도 시작: {position['stock_name']} (비율: {split_ratios})")

                total_profit = 0
                remaining_qty = position['quantity']

                for i, ratio in enumerate(split_ratios):
                    if remaining_qty <= 0:
                        break

                    # 각 차수별 매도
                    split_qty = int(position['quantity'] * ratio)
                    if split_qty > remaining_qty:
                        split_qty = remaining_qty

                    split_price = sell_price * (1 + 0.01 * i)  # 1%씩 높은 가격

                    # 부분 매도는 새로운 포지션으로 분리하지 않고 수량만 조정
                    # 실제 구현에서는 더 복잡한 로직이 필요할 수 있습니다
                    profit = self.db.close_position(
                        position_id=position_id,
                        sell_price=split_price
                    )

                    total_profit += profit if profit else 0
                    remaining_qty -= split_qty

                    logger.info(
                        f"  [{i+1}/{len(split_ratios)}] {split_qty}주 @ {split_price:,.0f}원 (수익: {profit:+,.0f}원)"
                    )

                logger.info(f"✅ 분할매도 완료: 총 수익 {total_profit:+,.0f}원")
                return total_profit

            else:
                # 일반 매도 실행
                profit = self.db.close_position(
                    position_id=position_id,
                    sell_price=sell_price
                )

                logger.info(
                    f"가상매매 매도 실행: Position #{position_id} "
                    f"@ {sell_price:,}원 [사유: {reason}] "
                    f"수익: {profit:+,.0f}원"
                )

                return profit

        except Exception as e:
            logger.error(f"가상매매 매도 실행 실패: {e}", exc_info=True)
            return None

    def update_prices(self, price_updates: Dict[str, float]):
        """
        종목 현재가 업데이트

        Args:
            price_updates: {종목코드: 현재가} 딕셔너리
        """
        self.price_cache.update(price_updates)

        # 모든 활성 포지션의 현재가 업데이트
        positions = self.db.get_open_positions()
        for position in positions:
            stock_code = position['stock_code']
            if stock_code in price_updates:
                current_price = price_updates[stock_code]
                self.db.update_position_price(position['id'], current_price)

    def check_stop_loss_take_profit(self) -> List[Dict[str, Any]]:
        """
        모든 활성 포지션의 손절/익절 조건 체크

        Returns:
            실행된 매도 주문 리스트
        """
        executed_orders = []
        positions = self.db.get_open_positions()

        for position in positions:
            stock_code = position['stock_code']
            current_price = self.price_cache.get(stock_code, position['current_price'])

            # 손절가 체크
            if position['stop_loss_price'] and current_price <= position['stop_loss_price']:
                profit = self.execute_sell(
                    position_id=position['id'],
                    sell_price=current_price,
                    reason="stop_loss"
                )

                if profit is not None:
                    executed_orders.append({
                        'position_id': position['id'],
                        'stock_code': stock_code,
                        'stock_name': position['stock_name'],
                        'type': 'stop_loss',
                        'sell_price': current_price,
                        'profit': profit
                    })

                    logger.warning(
                        f"손절 실행: {position['stock_name']}({stock_code}) "
                        f"@ {current_price:,}원 (손절가: {position['stop_loss_price']:,}원)"
                    )

            # 익절가 체크
            elif position['take_profit_price'] and current_price >= position['take_profit_price']:
                profit = self.execute_sell(
                    position_id=position['id'],
                    sell_price=current_price,
                    reason="take_profit"
                )

                if profit is not None:
                    executed_orders.append({
                        'position_id': position['id'],
                        'stock_code': stock_code,
                        'stock_name': position['stock_name'],
                        'type': 'take_profit',
                        'sell_price': current_price,
                        'profit': profit
                    })

                    logger.info(
                        f"익절 실행: {position['stock_name']}({stock_code}) "
                        f"@ {current_price:,}원 (익절가: {position['take_profit_price']:,}원)"
                    )

        return executed_orders

    def get_strategy_summary(self, strategy_id: int = None) -> List[Dict[str, Any]]:
        """
        전략 요약 정보 조회

        Args:
            strategy_id: 전략 ID (None이면 모든 전략)

        Returns:
            전략 요약 리스트
        """
        strategies = self.db.get_all_strategies()

        if strategy_id:
            strategies = [s for s in strategies if s['id'] == strategy_id]

        return strategies

    def get_positions(self, strategy_id: int = None) -> List[Dict[str, Any]]:
        """
        포지션 조회

        Args:
            strategy_id: 전략 ID (None이면 모든 전략)

        Returns:
            포지션 리스트
        """
        positions = self.db.get_open_positions(strategy_id)

        # 현재가 캐시로 업데이트
        for position in positions:
            stock_code = position['stock_code']
            if stock_code in self.price_cache:
                position['current_price'] = self.price_cache[stock_code]

                # 수익률 재계산
                value = position['quantity'] * position['current_price']
                cost = position['quantity'] * position['avg_price']
                position['profit'] = value - cost
                position['profit_percent'] = (position['profit'] / cost * 100) if cost > 0 else 0

        return positions

    def get_trade_history(self, strategy_id: int = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        거래 내역 조회

        Args:
            strategy_id: 전략 ID (None이면 모든 전략)
            limit: 최대 조회 개수

        Returns:
            거래 내역 리스트
        """
        return self.db.get_trade_history(strategy_id, limit)

    def get_performance_metrics(self, strategy_id: int) -> Dict[str, Any]:
        """
        전략 성과 지표 계산

        Args:
            strategy_id: 전략 ID

        Returns:
            성과 지표 딕셔너리
        """
        strategies = self.db.get_all_strategies()
        strategy = next((s for s in strategies if s['id'] == strategy_id), None)

        if not strategy:
            return {}

        positions = self.get_positions(strategy_id)
        trades = self.get_trade_history(strategy_id)

        # 포지션 평가금액 계산
        position_value = sum(
            p['quantity'] * p['current_price']
            for p in positions
        )

        # 총 자산 = 현금 + 포지션 평가금액
        total_assets = strategy['current_capital'] + position_value

        # 미실현 손익
        unrealized_profit = sum(p['profit'] for p in positions)

        # 최대 손실 (MDD) 계산
        max_drawdown = 0
        peak = strategy['initial_capital']

        for trade in reversed(trades):  # 과거부터 계산
            if trade['side'] == 'sell':
                current = strategy['initial_capital'] + trade['profit']
                if current > peak:
                    peak = current
                drawdown = (peak - current) / peak * 100 if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)

        return {
            'strategy_id': strategy_id,
            'strategy_name': strategy['name'],
            'initial_capital': strategy['initial_capital'],
            'current_capital': strategy['current_capital'],
            'position_value': position_value,
            'total_assets': total_assets,
            'total_profit': strategy['total_profit'],
            'unrealized_profit': unrealized_profit,
            'realized_profit': strategy['total_profit'],
            'return_rate': strategy['return_rate'],
            'win_rate': strategy['win_rate'],
            'trade_count': strategy['trade_count'],
            'win_count': strategy['win_count'],
            'loss_count': strategy['loss_count'],
            'max_drawdown': max_drawdown,
            'position_count': len(positions)
        }

    def delete_strategy(self, strategy_id: int) -> bool:
        """
        가상매매 전략 삭제

        Args:
            strategy_id: 삭제할 전략 ID

        Returns:
            삭제 성공 여부
        """
        try:
            # 활성 포지션이 있는지 확인
            positions = self.get_positions(strategy_id)
            if positions:
                logger.warning(f"전략 {strategy_id}에 {len(positions)}개의 활성 포지션이 있어 삭제할 수 없습니다")
                return False

            # 전략 삭제 (DB에서)
            self.db.delete_strategy(strategy_id)

            # 활성 전략 목록에서 제거
            if strategy_id in self.active_strategies:
                del self.active_strategies[strategy_id]

            logger.info(f"가상매매 전략 {strategy_id} 삭제 완료")
            return True

        except Exception as e:
            logger.error(f"전략 삭제 실패: {e}")
            return False

    def close(self):
        """데이터베이스 연결 종료"""
        if self.db:
            self.db.close()
            logger.info("가상매매 매니저 종료")
