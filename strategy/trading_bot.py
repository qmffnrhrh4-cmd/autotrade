"""
Automated Trading Bot - v5.14
Multi-strategy automated trading with risk management and position control
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class BotStatus(Enum):
    """봇 상태"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class TradingMode(Enum):
    """트레이딩 모드"""
    LIVE = "live"  # 실제 거래
    PAPER = "paper"  # 모의 거래
    BACKTEST = "backtest"  # 백테스트


class OrderSide(Enum):
    """주문 방향"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Position:
    """포지션"""
    stock_code: str
    stock_name: str
    quantity: int
    entry_price: float
    current_price: float
    entry_time: datetime
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_name: str = ""


@dataclass
class Trade:
    """거래"""
    trade_id: str
    stock_code: str
    stock_name: str
    side: OrderSide
    quantity: int
    price: float
    cost: float
    timestamp: datetime
    strategy_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BotPerformance:
    """봇 성능"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    sharpe_ratio: float
    max_drawdown: float
    avg_trade_pnl: float
    best_trade: float
    worst_trade: float
    current_positions: int
    total_capital: float
    available_capital: float


class TradingStrategy:
    """트레이딩 전략 베이스 클래스"""

    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params

    def generate_signals(self, market_data: Dict[str, Any],
                        price_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        시그널 생성

        Returns:
            List[Dict]: [{'action': 'buy'/'sell', 'stock_code': str, 'confidence': float, ...}]
        """
        raise NotImplementedError


class MomentumStrategy(TradingStrategy):
    """모멘텀 전략"""

    def __init__(self, lookback_period: int = 20, threshold: float = 0.05):
        super().__init__("Momentum", {
            'lookback_period': lookback_period,
            'threshold': threshold
        })

    def generate_signals(self, market_data: Dict[str, Any],
                        price_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        signals = []

        if len(price_history) < self.params['lookback_period']:
            return signals

        closes = [h['close'] for h in price_history[-self.params['lookback_period']:]]
        momentum = (closes[-1] - closes[0]) / closes[0]

        if momentum > self.params['threshold']:
            signals.append({
                'action': 'buy',
                'stock_code': market_data.get('stock_code'),
                'confidence': min(0.9, 0.5 + abs(momentum)),
                'reason': f"Strong upward momentum: {momentum:.2%}"
            })
        elif momentum < -self.params['threshold']:
            signals.append({
                'action': 'sell',
                'stock_code': market_data.get('stock_code'),
                'confidence': min(0.9, 0.5 + abs(momentum)),
                'reason': f"Strong downward momentum: {momentum:.2%}"
            })

        return signals


class MeanReversionStrategy(TradingStrategy):
    """평균 회귀 전략"""

    def __init__(self, lookback_period: int = 20, std_threshold: float = 2.0):
        super().__init__("MeanReversion", {
            'lookback_period': lookback_period,
            'std_threshold': std_threshold
        })

    def generate_signals(self, market_data: Dict[str, Any],
                        price_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        signals = []

        if len(price_history) < self.params['lookback_period']:
            return signals

        closes = np.array([h['close'] for h in price_history[-self.params['lookback_period']:]])
        mean = np.mean(closes)
        std = np.std(closes)
        current_price = market_data.get('price', closes[-1])

        z_score = (current_price - mean) / std if std > 0 else 0

        # Oversold → Buy
        if z_score < -self.params['std_threshold']:
            signals.append({
                'action': 'buy',
                'stock_code': market_data.get('stock_code'),
                'confidence': min(0.9, 0.5 + abs(z_score) * 0.1),
                'reason': f"Oversold (Z-score: {z_score:.2f})"
            })
        # Overbought → Sell
        elif z_score > self.params['std_threshold']:
            signals.append({
                'action': 'sell',
                'stock_code': market_data.get('stock_code'),
                'confidence': min(0.9, 0.5 + abs(z_score) * 0.1),
                'reason': f"Overbought (Z-score: {z_score:.2f})"
            })

        return signals


class BreakoutStrategy(TradingStrategy):
    """돌파 전략"""

    def __init__(self, lookback_period: int = 20, breakout_threshold: float = 0.02):
        super().__init__("Breakout", {
            'lookback_period': lookback_period,
            'breakout_threshold': breakout_threshold
        })

    def generate_signals(self, market_data: Dict[str, Any],
                        price_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        signals = []

        if len(price_history) < self.params['lookback_period']:
            return signals

        recent = price_history[-self.params['lookback_period']:]
        resistance = max([h['high'] for h in recent])
        support = min([h['low'] for h in recent])

        current_price = market_data.get('price', recent[-1]['close'])

        # Upward breakout
        if current_price > resistance * (1 + self.params['breakout_threshold']):
            signals.append({
                'action': 'buy',
                'stock_code': market_data.get('stock_code'),
                'confidence': 0.80,
                'reason': f"Upward breakout above {resistance:,.0f}"
            })
        # Downward breakout
        elif current_price < support * (1 - self.params['breakout_threshold']):
            signals.append({
                'action': 'sell',
                'stock_code': market_data.get('stock_code'),
                'confidence': 0.75,
                'reason': f"Downward breakout below {support:,.0f}"
            })

        return signals


class AutomatedTradingBot:
    """
    자동화된 트레이딩 봇

    Features:
    - Multi-strategy support
    - Risk management (position sizing, stop-loss, take-profit)
    - Portfolio management
    - Performance tracking
    - Emergency stop
    """

    def __init__(self,
                 initial_capital: float = 10000000,
                 max_position_size: float = 0.2,
                 max_positions: int = 10,
                 stop_loss_pct: float = 0.05,
                 take_profit_pct: float = 0.10,
                 trading_mode: TradingMode = TradingMode.PAPER):
        """
        Args:
            initial_capital: 초기 자본
            max_position_size: 최대 포지션 크기 (자본 대비 비율)
            max_positions: 최대 동시 포지션 수
            stop_loss_pct: 손절 비율
            take_profit_pct: 익절 비율
            trading_mode: 거래 모드
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_position_size = max_position_size
        self.max_positions = max_positions
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trading_mode = trading_mode

        # Status
        self.status = BotStatus.IDLE
        self.start_time: Optional[datetime] = None

        # Positions and trades
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Trade] = []

        # Strategies
        self.strategies: List[TradingStrategy] = []

        # Performance tracking
        self.equity_curve: List[Dict[str, Any]] = []
        self.daily_returns: List[float] = []

        # Emergency stop
        self.max_drawdown_limit = 0.20  # 20% max drawdown
        self.emergency_stopped = False

        logger.info(f"Trading Bot initialized: capital={initial_capital:,.0f}, "
                   f"mode={trading_mode.value}")

    def add_strategy(self, strategy: TradingStrategy):
        """전략 추가"""
        self.strategies.append(strategy)
        logger.info(f"Strategy added: {strategy.name}")

    def start(self):
        """봇 시작"""
        if self.status == BotStatus.RUNNING:
            logger.warning("Bot is already running")
            return

        self.status = BotStatus.RUNNING
        self.start_time = datetime.now()
        logger.info("Trading Bot started")

    def stop(self):
        """봇 정지"""
        self.status = BotStatus.STOPPED
        logger.info("Trading Bot stopped")

    def pause(self):
        """봇 일시정지"""
        self.status = BotStatus.PAUSED
        logger.info("Trading Bot paused")

    def resume(self):
        """봇 재개"""
        if self.status == BotStatus.PAUSED:
            self.status = BotStatus.RUNNING
            logger.info("Trading Bot resumed")

    def execute_cycle(self,
                      market_data: Dict[str, Dict[str, Any]],
                      price_histories: Dict[str, List[Dict[str, Any]]]):
        """
        트레이딩 사이클 실행

        Args:
            market_data: 실시간 시장 데이터
            price_histories: 가격 히스토리
        """
        if self.status != BotStatus.RUNNING:
            return

        if self.emergency_stopped:
            logger.warning("Emergency stop activated")
            return

        # Update positions
        self._update_positions(market_data)

        # Check emergency stop
        if self._check_emergency_stop():
            return

        # Check exit conditions for existing positions
        self._check_exit_conditions(market_data)

        # Generate new signals if we have capacity
        if len(self.positions) < self.max_positions:
            signals = self._generate_all_signals(market_data, price_histories)
            self._process_signals(signals, market_data)

        # Update equity curve
        self._update_equity_curve()

        logger.debug(f"Cycle complete: positions={len(self.positions)}, "
                    f"cash={self.cash:,.0f}")

    def get_performance(self) -> BotPerformance:
        """성능 조회"""
        if not self.trade_history:
            return BotPerformance(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_pnl_pct=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                avg_trade_pnl=0.0,
                best_trade=0.0,
                worst_trade=0.0,
                current_positions=len(self.positions),
                total_capital=self.initial_capital,
                available_capital=self.cash
            )

        # Calculate P&L from closed trades
        closed_trades_pnl = []
        for i in range(0, len(self.trade_history), 2):
            if i + 1 < len(self.trade_history):
                entry = self.trade_history[i]
                exit_trade = self.trade_history[i + 1]

                if entry.side == OrderSide.BUY and exit_trade.side == OrderSide.SELL:
                    pnl = (exit_trade.price - entry.price) * entry.quantity
                    closed_trades_pnl.append(pnl)

        winning = len([p for p in closed_trades_pnl if p > 0])
        losing = len([p for p in closed_trades_pnl if p < 0])
        win_rate = winning / len(closed_trades_pnl) if closed_trades_pnl else 0.0

        total_pnl = sum(closed_trades_pnl) + sum(p.unrealized_pnl for p in self.positions.values())
        total_pnl_pct = (total_pnl / self.initial_capital) * 100

        # Sharpe ratio
        if len(self.daily_returns) > 1:
            sharpe = np.mean(self.daily_returns) / (np.std(self.daily_returns) + 1e-10) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Max drawdown
        if self.equity_curve:
            equities = [e['equity'] for e in self.equity_curve]
            running_max = np.maximum.accumulate(equities)
            drawdowns = (equities - running_max) / running_max
            max_dd = np.min(drawdowns) if len(drawdowns) > 0 else 0.0
        else:
            max_dd = 0.0

        return BotPerformance(
            total_trades=len(self.trade_history),
            winning_trades=winning,
            losing_trades=losing,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            avg_trade_pnl=np.mean(closed_trades_pnl) if closed_trades_pnl else 0.0,
            best_trade=max(closed_trades_pnl) if closed_trades_pnl else 0.0,
            worst_trade=min(closed_trades_pnl) if closed_trades_pnl else 0.0,
            current_positions=len(self.positions),
            total_capital=self.cash + sum(p.quantity * p.current_price for p in self.positions.values()),
            available_capital=self.cash
        )

    def emergency_stop(self):
        """긴급 정지"""
        self.emergency_stopped = True
        self.status = BotStatus.ERROR
        logger.critical("EMERGENCY STOP ACTIVATED")

        # Close all positions
        for position in list(self.positions.values()):
            self._close_position(position.stock_code, position.current_price, "Emergency stop")

    # ===== PRIVATE METHODS =====

    def _generate_all_signals(self,
                             market_data: Dict[str, Dict[str, Any]],
                             price_histories: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """모든 전략에서 시그널 생성"""
        all_signals = []

        for stock_code, data in market_data.items():
            if stock_code not in price_histories:
                continue

            history = price_histories[stock_code]

            for strategy in self.strategies:
                signals = strategy.generate_signals(data, history)
                for signal in signals:
                    signal['strategy_name'] = strategy.name
                    signal['stock_code'] = stock_code
                    signal['stock_name'] = data.get('stock_name', stock_code)
                    signal['current_price'] = data.get('price', history[-1]['close'])
                    all_signals.append(signal)

        # Sort by confidence
        all_signals.sort(key=lambda s: s.get('confidence', 0), reverse=True)

        return all_signals

    def _process_signals(self, signals: List[Dict[str, Any]],
                        market_data: Dict[str, Dict[str, Any]]):
        """시그널 처리 및 주문 실행"""
        for signal in signals:
            stock_code = signal['stock_code']

            # Skip if already have position
            if stock_code in self.positions:
                continue

            # Only process buy signals for new positions
            if signal['action'] != 'buy':
                continue

            # Check confidence threshold
            if signal.get('confidence', 0) < 0.70:
                continue

            # Calculate position size
            max_invest = self.cash * self.max_position_size
            current_price = signal['current_price']
            quantity = int(max_invest / current_price)

            if quantity <= 0:
                continue

            cost = quantity * current_price

            # Check if enough cash
            if cost > self.cash:
                continue

            # Execute buy order
            self._execute_buy(
                stock_code=stock_code,
                stock_name=signal['stock_name'],
                price=current_price,
                quantity=quantity,
                strategy_name=signal['strategy_name']
            )

            # Stop after filling one position per cycle
            break

    def _execute_buy(self, stock_code: str, stock_name: str,
                    price: float, quantity: int, strategy_name: str):
        """매수 실행"""
        cost = price * quantity

        if cost > self.cash:
            logger.warning(f"Insufficient cash for {stock_code}")
            return

        # Create position
        position = Position(
            stock_code=stock_code,
            stock_name=stock_name,
            quantity=quantity,
            entry_price=price,
            current_price=price,
            entry_time=datetime.now(),
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            stop_loss=price * (1 - self.stop_loss_pct),
            take_profit=price * (1 + self.take_profit_pct),
            strategy_name=strategy_name
        )

        self.positions[stock_code] = position
        self.cash -= cost

        # Record trade
        trade = Trade(
            trade_id=f"BUY_{stock_code}_{int(datetime.now().timestamp())}",
            stock_code=stock_code,
            stock_name=stock_name,
            side=OrderSide.BUY,
            quantity=quantity,
            price=price,
            cost=cost,
            timestamp=datetime.now(),
            strategy_name=strategy_name
        )
        self.trade_history.append(trade)

        logger.info(f"BUY: {stock_name} {quantity} @ {price:,.0f} (strategy={strategy_name})")

    def _execute_sell(self, stock_code: str, price: float, reason: str = ""):
        """매도 실행"""
        if stock_code not in self.positions:
            return

        position = self.positions[stock_code]

        # Calculate P&L
        proceeds = price * position.quantity
        pnl = proceeds - (position.entry_price * position.quantity)
        pnl_pct = (pnl / (position.entry_price * position.quantity)) * 100

        # Update cash
        self.cash += proceeds

        # Record trade
        trade = Trade(
            trade_id=f"SELL_{stock_code}_{int(datetime.now().timestamp())}",
            stock_code=stock_code,
            stock_name=position.stock_name,
            side=OrderSide.SELL,
            quantity=position.quantity,
            price=price,
            cost=proceeds,
            timestamp=datetime.now(),
            strategy_name=position.strategy_name,
            metadata={'pnl': pnl, 'pnl_pct': pnl_pct, 'reason': reason}
        )
        self.trade_history.append(trade)

        # Remove position
        del self.positions[stock_code]

        logger.info(f"SELL: {position.stock_name} {position.quantity} @ {price:,.0f} "
                   f"(P&L: {pnl:+,.0f}원 / {pnl_pct:+.2f}%, reason={reason})")

    def _update_positions(self, market_data: Dict[str, Dict[str, Any]]):
        """포지션 업데이트"""
        for stock_code, position in self.positions.items():
            if stock_code in market_data:
                current_price = market_data[stock_code].get('price', position.current_price)
                position.current_price = current_price

                # Update P&L
                position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
                position.unrealized_pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100

    def _check_exit_conditions(self, market_data: Dict[str, Dict[str, Any]]):
        """청산 조건 확인"""
        to_close = []

        for stock_code, position in self.positions.items():
            if stock_code not in market_data:
                continue

            current_price = position.current_price

            # Stop-loss
            if position.stop_loss and current_price <= position.stop_loss:
                to_close.append((stock_code, current_price, "Stop-loss"))

            # Take-profit
            elif position.take_profit and current_price >= position.take_profit:
                to_close.append((stock_code, current_price, "Take-profit"))

        # Close positions
        for stock_code, price, reason in to_close:
            self._execute_sell(stock_code, price, reason)

    def _close_position(self, stock_code: str, price: float, reason: str):
        """포지션 청산"""
        self._execute_sell(stock_code, price, reason)

    def _check_emergency_stop(self) -> bool:
        """긴급 정지 확인"""
        current_equity = self.cash + sum(p.quantity * p.current_price for p in self.positions.values())
        drawdown = (self.initial_capital - current_equity) / self.initial_capital

        if drawdown > self.max_drawdown_limit:
            logger.critical(f"Max drawdown exceeded: {drawdown:.2%}")
            self.emergency_stop()
            return True

        return False

    def _update_equity_curve(self):
        """자산 곡선 업데이트"""
        current_equity = self.cash + sum(p.quantity * p.current_price for p in self.positions.values())

        self.equity_curve.append({
            'timestamp': datetime.now().isoformat(),
            'equity': current_equity,
            'cash': self.cash,
            'positions_value': current_equity - self.cash,
            'num_positions': len(self.positions)
        })

        MAX_EQUITY_POINTS = 1000
        if len(self.equity_curve) > MAX_EQUITY_POINTS:
            self.equity_curve.pop(0)

        if len(self.equity_curve) > 1:
            prev_equity = self.equity_curve[-2]['equity']
            daily_return = (current_equity - prev_equity) / prev_equity
            self.daily_returns.append(daily_return)


# Global singleton
_trading_bot: Optional[AutomatedTradingBot] = None


def get_trading_bot() -> AutomatedTradingBot:
    """트레이딩 봇 싱글톤"""
    global _trading_bot
    if _trading_bot is None:
        _trading_bot = AutomatedTradingBot(
            initial_capital=10000000,
            max_position_size=0.2,
            max_positions=10,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            trading_mode=TradingMode.PAPER
        )

        # Add default strategies
        _trading_bot.add_strategy(MomentumStrategy(lookback_period=20, threshold=0.05))
        _trading_bot.add_strategy(MeanReversionStrategy(lookback_period=20, std_threshold=2.0))
        _trading_bot.add_strategy(BreakoutStrategy(lookback_period=20, breakout_threshold=0.02))

    return _trading_bot
