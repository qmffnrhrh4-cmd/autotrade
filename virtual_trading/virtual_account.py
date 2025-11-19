"""
virtual_trading/virtual_account.py
가상 계좌 관리
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path


@dataclass
class VirtualPosition:
    """가상 포지션"""
    stock_code: str
    stock_name: str
    quantity: int
    entry_price: int
    entry_time: datetime
    strategy_name: str = ""

    # 성과 추적
    current_price: int = 0
    unrealized_pnl: int = 0
    unrealized_pnl_rate: float = 0.0
    highest_price: int = 0  # 보유 중 최고가

    def update_price(self, current_price: int):
        """현재가 업데이트 및 평가손익 계산"""
        self.current_price = current_price
        # 최고가 업데이트
        if current_price > self.highest_price:
            self.highest_price = current_price
        self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        if self.entry_price > 0:
            self.unrealized_pnl_rate = ((current_price - self.entry_price) / self.entry_price) * 100

    @property
    def average_price(self) -> int:
        """평균 매수가 (entry_price의 별칭)"""
        return self.entry_price

    @property
    def days_held(self) -> int:
        """보유 일수"""
        return (datetime.now() - self.entry_time).days

    def to_dict(self):
        """딕셔너리 변환"""
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat(),
            'strategy_name': self.strategy_name,
            'current_price': self.current_price,
            'highest_price': self.highest_price,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_rate': self.unrealized_pnl_rate,
            'days_held': self.days_held,
        }


class VirtualAccount:
    """가상 계좌"""

    def __init__(self, initial_cash: int = 10_000_000, name: str = "Virtual Account"):
        """
        초기화

        Args:
            initial_cash: 초기 자금 (기본 1천만원)
            name: 계좌 이름
        """
        self.name = name
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, VirtualPosition] = {}

        # 거래 기록
        self.trade_history: List[Dict] = []

        # 성과 추적
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0
        self.max_cash = initial_cash
        self.min_cash = initial_cash

        # 시작 시간
        self.created_at = datetime.now()

    def get_total_value(self) -> int:
        """총 자산 = 현금 + 평가금액"""
        position_value = sum(
            pos.current_price * pos.quantity
            for pos in self.positions.values()
        )
        return self.cash + position_value

    def get_total_pnl(self) -> int:
        """총 손익 = 현재 자산 - 초기 자금"""
        return self.get_total_value() - self.initial_cash

    def get_total_pnl_rate(self) -> float:
        """총 수익률 (%)"""
        if self.initial_cash == 0:
            return 0.0
        return (self.get_total_pnl() / self.initial_cash) * 100

    def get_win_rate(self) -> float:
        """승률 (%)"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    def can_buy(self, price: int, quantity: int) -> bool:
        """매수 가능 여부 확인"""
        required_cash = price * quantity
        return self.cash >= required_cash

    def buy(self, stock_code: str, stock_name: str, price: int, quantity: int,
            strategy_name: str = "") -> bool:
        """
        가상 매수

        Returns:
            성공 여부
        """
        required_cash = price * quantity

        if not self.can_buy(price, quantity):
            return False

        # 현금 차감
        self.cash -= required_cash

        # 포지션 추가/업데이트
        if stock_code in self.positions:
            # 기존 포지션 있음 - 평균가 계산
            existing = self.positions[stock_code]
            total_quantity = existing.quantity + quantity
            total_cost = (existing.entry_price * existing.quantity) + (price * quantity)
            avg_price = total_cost // total_quantity

            existing.quantity = total_quantity
            existing.entry_price = avg_price
            # 최고가 업데이트
            if price > existing.highest_price:
                existing.highest_price = price
        else:
            # 신규 포지션
            self.positions[stock_code] = VirtualPosition(
                stock_code=stock_code,
                stock_name=stock_name,
                quantity=quantity,
                entry_price=price,
                entry_time=datetime.now(),
                strategy_name=strategy_name,
                highest_price=price,  # 매수가를 최고가로 초기화
            )

        # 거래 기록
        self.trade_history.append({
            'type': 'buy',
            'stock_code': stock_code,
            'stock_name': stock_name,
            'price': price,
            'quantity': quantity,
            'amount': required_cash,
            'strategy_name': strategy_name,
            'timestamp': datetime.now().isoformat(),
        })

        # 최소/최대 현금 업데이트
        if self.cash < self.min_cash:
            self.min_cash = self.cash

        return True

    def sell(self, stock_code: str, price: int, quantity: int = None,
             reason: str = "") -> Optional[int]:
        """
        가상 매도

        Args:
            quantity: None이면 전량 매도

        Returns:
            실현 손익 (매도 실패 시 None)
        """
        if stock_code not in self.positions:
            return None

        position = self.positions[stock_code]

        # 수량 결정
        if quantity is None or quantity >= position.quantity:
            quantity = position.quantity
            is_full_sale = True
        else:
            is_full_sale = False

        # 매도 금액
        sale_amount = price * quantity

        # 실현 손익 계산
        cost = position.entry_price * quantity
        realized_pnl = sale_amount - cost
        realized_pnl_rate = ((price - position.entry_price) / position.entry_price) * 100

        # 현금 증가
        self.cash += sale_amount

        # 포지션 업데이트
        if is_full_sale:
            del self.positions[stock_code]
        else:
            position.quantity -= quantity

        # 거래 통계 업데이트
        self.total_trades += 1
        self.total_pnl += realized_pnl

        if realized_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        # 거래 기록
        self.trade_history.append({
            'type': 'sell',
            'stock_code': stock_code,
            'stock_name': position.stock_name,
            'price': price,
            'quantity': quantity,
            'amount': sale_amount,
            'realized_pnl': realized_pnl,
            'realized_pnl_rate': realized_pnl_rate,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
        })

        # 최대 현금 업데이트
        if self.cash > self.max_cash:
            self.max_cash = self.cash

        return realized_pnl

    def update_positions(self, price_data: Dict[str, int]):
        """
        포지션 가격 업데이트

        Args:
            price_data: {stock_code: current_price}
        """
        for stock_code, position in self.positions.items():
            if stock_code in price_data:
                position.update_price(price_data[stock_code])

    def get_position(self, stock_code: str) -> Optional[VirtualPosition]:
        """포지션 조회"""
        return self.positions.get(stock_code)

    def has_position(self, stock_code: str) -> bool:
        """포지션 보유 여부"""
        return stock_code in self.positions

    def get_summary(self) -> Dict:
        """계좌 요약"""
        return {
            'name': self.name,
            'initial_cash': self.initial_cash,
            'current_cash': self.cash,
            'total_value': self.get_total_value(),
            'total_pnl': self.get_total_pnl(),
            'total_pnl_rate': self.get_total_pnl_rate(),
            'position_count': len(self.positions),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.get_win_rate(),
            'max_cash': self.max_cash,
            'min_cash': self.min_cash,
            'created_at': self.created_at.isoformat(),
        }

    def save_state(self, filepath: str):
        """계좌 상태 저장"""
        state = {
            'account': self.get_summary(),
            'positions': [pos.to_dict() for pos in self.positions.values()],
            'trade_history': self.trade_history[-100:],  # 최근 100건
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self, filepath: str):
        """계좌 상태 로드"""
        if not Path(filepath).exists():
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)

        # 계좌 정보 복원
        account = state['account']
        self.cash = account['current_cash']
        self.total_trades = account['total_trades']
        self.winning_trades = account['winning_trades']
        self.losing_trades = account['losing_trades']
        self.total_pnl = account['total_pnl']
        self.max_cash = account['max_cash']
        self.min_cash = account['min_cash']

        # 포지션 복원
        self.positions = {}
        for pos_dict in state['positions']:
            pos = VirtualPosition(
                stock_code=pos_dict['stock_code'],
                stock_name=pos_dict['stock_name'],
                quantity=pos_dict['quantity'],
                entry_price=pos_dict['entry_price'],
                entry_time=datetime.fromisoformat(pos_dict['entry_time']),
                strategy_name=pos_dict.get('strategy_name', ''),
            )
            pos.current_price = pos_dict.get('current_price', pos.entry_price)
            pos.unrealized_pnl = pos_dict.get('unrealized_pnl', 0)
            pos.unrealized_pnl_rate = pos_dict.get('unrealized_pnl_rate', 0.0)
            self.positions[pos.stock_code] = pos

        # 거래 기록 복원
        self.trade_history = state.get('trade_history', [])


__all__ = ['VirtualAccount', 'VirtualPosition']
