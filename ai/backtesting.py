"""
Backtesting Engine for Strategy Validation
Tests trading strategies on historical data

Author: AutoTrade Pro
Version: 4.2 - CRITICAL #2: Use standard Position/Trade from core
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Callable
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import json

# v4.2: Use standard types from core (CRITICAL #2)
from core import Position, Trade as CoreTrade, OrderAction


# Backtesting-specific classes
@dataclass
class BacktestTrade:
    """Backtest trade record (extends core.Trade with backtest-specific fields)"""
    trade_id: int
    timestamp: str  # ISO format
    stock_code: str
    action: str  # 'buy' or 'sell'
    quantity: int
    price: float
    value: float
    commission: float = 0.0
    reason: str = ""

    @classmethod
    def from_core_trade(cls, core_trade: CoreTrade, trade_id: int) -> 'BacktestTrade':
        """Convert core.Trade to BacktestTrade"""
        return cls(
            trade_id=trade_id,
            timestamp=core_trade.timestamp.isoformat(),
            stock_code=core_trade.stock_code,
            action=core_trade.action.value,
            quantity=core_trade.quantity,
            price=core_trade.price,
            value=core_trade.quantity * core_trade.price,
            commission=core_trade.commission,
            reason=core_trade.reason
        )


# Note: Using core.Position directly instead of custom Position class
# core.Position has all needed fields:
# - purchase_price (= avg_price)
# - current_price
# - profit_loss (= unrealized_pnl)
# - profit_loss_rate (= unrealized_pnl_pct)


@dataclass
class BacktestResult:
    """Backtest result summary"""
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float

    # Performance metrics
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    calmar_ratio: float

    # Trading metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float

    # Daily metrics
    avg_daily_return: float
    std_daily_return: float
    best_day: float
    worst_day: float

    # Positions
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)


@dataclass
class BacktestConfig:
    """Backtest configuration"""
    initial_capital: float = 10000000  # 1천만원
    commission_rate: float = 0.00015  # 0.015%
    slippage_pct: float = 0.0005  # 0.05%
    position_size_limit: float = 0.3  # 30% max per position
    stop_loss_pct: Optional[float] = None  # -5%
    take_profit_pct: Optional[float] = None  # +10%
    max_positions: int = 5


# ============================================================================
# Backtesting Engine
# ============================================================================

class BacktestEngine:
    """
    Comprehensive backtesting engine

    Features:
    - Historical data simulation
    - Transaction costs
    - Slippage modeling
    - Risk management
    - Performance analytics
    """

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()

        # Portfolio state
        self.cash = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.daily_returns: List[float] = []

        # Metrics
        self.trade_counter = 0
        self.peak_equity = self.config.initial_capital
        self.max_drawdown = 0.0

    def run_backtest(self, historical_data: List[Dict],
                    strategy_fn: Callable,
                    strategy_name: str = "Custom Strategy") -> BacktestResult:
        """
        Run backtest on historical data

        Args:
            historical_data: List of historical price data
                Each item: {
                    'date': '2024-01-01',
                    'stock_code': '005930',
                    'open': 73000,
                    'high': 74000,
                    'low': 72500,
                    'close': 73500,
                    'volume': 1000000
                }
            strategy_fn: Strategy function(current_data, portfolio) -> action
                Returns: {'action': 'buy'/'sell'/'hold', 'stock_code': '...', 'quantity': 100}
            strategy_name: Name of strategy

        Returns:
            Backtest result with performance metrics
        """
        print("\n" + "="*80)
        print(f"🔄 Backtesting: {strategy_name}")
        print("="*80)
        print(f"Initial Capital: {self.config.initial_capital:,.0f}원")
        print(f"Commission Rate: {self.config.commission_rate:.4%}")
        print(f"Data Points: {len(historical_data)}")
        print("="*80 + "\n")

        # Reset state
        self._reset()

        # Get date range
        if historical_data:
            start_date = historical_data[0].get('date', datetime.now().isoformat())
            end_date = historical_data[-1].get('date', datetime.now().isoformat())
        else:
            start_date = end_date = datetime.now().isoformat()

        # Simulate trading day by day
        prev_equity = self.config.initial_capital

        for i, data in enumerate(historical_data):
            current_date = data.get('date', '')

            # Update position prices
            self._update_positions(data)

            # Get current portfolio state
            portfolio = self._get_portfolio_state()

            # Execute strategy
            try:
                action = strategy_fn(data, portfolio)

                if action and isinstance(action, dict):
                    self._execute_action(action, data)
            except Exception as e:
                print(f"Strategy error on {current_date}: {e}")
                continue

            # Calculate equity
            equity = self._calculate_equity()
            self.equity_curve.append(equity)

            # Calculate daily return
            daily_return = (equity - prev_equity) / prev_equity * 100
            self.daily_returns.append(daily_return)
            prev_equity = equity

            # Update max drawdown
            if equity > self.peak_equity:
                self.peak_equity = equity

            if self.peak_equity > 0:
                drawdown = (self.peak_equity - equity) / self.peak_equity * 100
                # Cap drawdown at 100% (cannot lose more than all capital)
                drawdown = min(drawdown, 100.0)
                if drawdown > self.max_drawdown:
                    self.max_drawdown = drawdown

            # Progress update
            if (i + 1) % 50 == 0:
                print(f"Progress: {i+1}/{len(historical_data)} days | "
                      f"Equity: {equity:,.0f}원 | "
                      f"Return: {(equity - self.config.initial_capital) / self.config.initial_capital * 100:+.2f}%")

        # Calculate final metrics
        final_equity = self._calculate_equity()
        result = self._calculate_metrics(strategy_name, start_date, end_date, final_equity)

        print("\n" + "="*80)
        print("✅ Backtest Complete")
        print("="*80)
        print(f"Final Capital: {final_equity:,.0f}원")
        print(f"Total Return: {result.total_return:+,.0f}원 ({result.total_return_pct:+.2f}%)")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"Max Drawdown: {result.max_drawdown_pct:.2f}%")
        print(f"Win Rate: {result.win_rate:.1f}%")
        print(f"Total Trades: {result.total_trades}")
        print("="*80 + "\n")

        return result

    def _reset(self):
        """Reset backtest state"""
        self.cash = self.config.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        self.trade_counter = 0
        self.peak_equity = self.config.initial_capital
        self.max_drawdown = 0.0

    def _update_positions(self, data: Dict):
        """Update position prices (using core.Position.update_current_price)"""
        stock_code = data.get('stock_code')
        close_price = data.get('close', 0)

        if stock_code in self.positions:
            pos = self.positions[stock_code]
            pos.update_current_price(close_price)  # Automatically calculates P&L

    def _get_portfolio_state(self) -> Dict[str, Any]:
        """Get current portfolio state"""
        return {
            'cash': self.cash,
            'positions': {k: asdict(v) for k, v in self.positions.items()},
            'total_equity': self._calculate_equity(),
            'total_positions': len(self.positions)
        }

    def _execute_action(self, action: Dict, data: Dict):
        """Execute trading action"""
        action_type = action.get('action', 'hold')
        stock_code = action.get('stock_code', data.get('stock_code'))
        quantity = action.get('quantity', 0)

        if action_type == 'buy':
            self._execute_buy(stock_code, quantity, data)
        elif action_type == 'sell':
            self._execute_sell(stock_code, quantity, data)

    def _execute_buy(self, stock_code: str, quantity: int, data: Dict):
        """Execute buy order"""
        if quantity <= 0:
            return

        # Get price with slippage
        price = data.get('close', 0) * (1 + self.config.slippage_pct)
        value = price * quantity
        commission = value * self.config.commission_rate
        total_cost = value + commission

        # Check if we have enough cash
        if total_cost > self.cash:
            # Reduce quantity to fit available cash
            quantity = int(self.cash / (price * (1 + self.config.commission_rate)))
            if quantity <= 0:
                return
            value = price * quantity
            commission = value * self.config.commission_rate
            total_cost = value + commission

        # Check position size limit
        equity = self._calculate_equity()
        if value > equity * self.config.position_size_limit:
            return

        # Execute trade
        self.cash -= total_cost

        # Update or create position (using core.Position)
        if stock_code in self.positions:
            pos = self.positions[stock_code]
            total_quantity = pos.quantity + quantity
            total_cost_basis = pos.purchase_price * pos.quantity + price * quantity
            pos.purchase_price = total_cost_basis / total_quantity
            pos.quantity = total_quantity
            pos.update_current_price(price)  # Recalculate P&L
        else:
            self.positions[stock_code] = Position(
                stock_code=stock_code,
                quantity=quantity,
                purchase_price=price,
                current_price=price
            )

        # Record trade
        self.trade_counter += 1
        self.trades.append(BacktestTrade(
            trade_id=self.trade_counter,
            timestamp=data.get('date', ''),
            stock_code=stock_code,
            action='buy',
            quantity=quantity,
            price=price,
            value=value,
            commission=commission,
            reason=f"Strategy buy signal"
        ))

    def _execute_sell(self, stock_code: str, quantity: int, data: Dict):
        """Execute sell order"""
        if stock_code not in self.positions:
            return

        pos = self.positions[stock_code]

        # Limit quantity to available shares
        quantity = min(quantity, pos.quantity)
        if quantity <= 0:
            return

        # Get price with slippage
        price = data.get('close', 0) * (1 - self.config.slippage_pct)
        value = price * quantity
        commission = value * self.config.commission_rate
        total_proceeds = value - commission

        # Execute trade
        self.cash += total_proceeds
        pos.quantity -= quantity

        # Remove position if fully sold
        if pos.quantity == 0:
            del self.positions[stock_code]

        # Record trade
        self.trade_counter += 1
        self.trades.append(BacktestTrade(
            trade_id=self.trade_counter,
            timestamp=data.get('date', ''),
            stock_code=stock_code,
            action='sell',
            quantity=quantity,
            price=price,
            value=value,
            commission=commission,
            reason=f"Strategy sell signal"
        ))

    def _calculate_equity(self) -> float:
        """Calculate total equity"""
        position_value = sum(
            pos.current_price * pos.quantity
            for pos in self.positions.values()
        )
        return self.cash + position_value

    def _calculate_metrics(self, strategy_name: str, start_date: str,
                          end_date: str, final_equity: float) -> BacktestResult:
        """Calculate comprehensive performance metrics"""
        initial_capital = self.config.initial_capital

        # Safety check: prevent division by zero
        if initial_capital <= 0:
            print(f"⚠️ Warning: Invalid initial capital: {initial_capital}")
            initial_capital = 10000000  # Default to 10M KRW

        total_return = final_equity - initial_capital
        total_return_pct = total_return / initial_capital * 100

        # Safety check: warn if return is abnormally high
        if abs(total_return_pct) > 1000:  # More than 1000% is likely an error
            print(f"⚠️ Warning: Abnormally high return detected: {total_return_pct:.2f}%")
            print(f"   Initial: {initial_capital:,.0f}, Final: {final_equity:,.0f}")

        # Trading metrics
        winning_trades = [t for t in self.trades if t.action == 'sell' and
                         self._is_winning_trade(t)]
        losing_trades = [t for t in self.trades if t.action == 'sell' and
                        not self._is_winning_trade(t)]

        total_trades = len([t for t in self.trades if t.action == 'sell'])
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        win_rate = (num_wins / total_trades * 100) if total_trades > 0 else 0

        avg_win = np.mean([self._get_trade_pnl(t) for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([self._get_trade_pnl(t) for t in losing_trades]) if losing_trades else 0

        total_wins = sum([self._get_trade_pnl(t) for t in winning_trades])
        total_losses = abs(sum([self._get_trade_pnl(t) for t in losing_trades]))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

        # Daily returns metrics
        returns_array = np.array(self.daily_returns) if self.daily_returns else np.array([0])
        avg_daily_return = float(np.mean(returns_array))
        std_daily_return = float(np.std(returns_array))
        best_day = float(np.max(returns_array))
        worst_day = float(np.min(returns_array))

        # Sharpe ratio (annualized)
        if std_daily_return > 0:
            sharpe_ratio = (avg_daily_return / std_daily_return) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # Sortino ratio (downside deviation)
        downside_returns = returns_array[returns_array < 0]
        downside_std = float(np.std(downside_returns)) if len(downside_returns) > 0 else 1e-10
        sortino_ratio = (avg_daily_return / downside_std) * np.sqrt(252) if downside_std > 0 else 0

        # Calmar ratio
        calmar_ratio = (total_return_pct / self.max_drawdown) if self.max_drawdown > 0 else 0

        # Max drawdown in currency
        # Safety check: cap drawdown at 100%
        safe_max_drawdown = min(self.max_drawdown, 100.0)
        max_drawdown_value = self.peak_equity * (safe_max_drawdown / 100)

        return BacktestResult(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=final_equity,
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=float(sharpe_ratio),
            sortino_ratio=float(sortino_ratio),
            max_drawdown=max_drawdown_value,
            max_drawdown_pct=safe_max_drawdown,
            calmar_ratio=float(calmar_ratio),
            total_trades=total_trades,
            winning_trades=num_wins,
            losing_trades=num_losses,
            win_rate=win_rate,
            avg_win=float(avg_win),
            avg_loss=float(avg_loss),
            profit_factor=float(profit_factor),
            avg_daily_return=avg_daily_return,
            std_daily_return=std_daily_return,
            best_day=best_day,
            worst_day=worst_day,
            trades=self.trades,
            equity_curve=self.equity_curve,
            daily_returns=self.daily_returns
        )

    def _is_winning_trade(self, trade: BacktestTrade) -> bool:
        """Check if trade was profitable"""
        # Find corresponding buy trade
        for t in reversed(self.trades):
            if (t.stock_code == trade.stock_code and
                t.action == 'buy' and
                t.timestamp < trade.timestamp):
                return trade.price > t.price
        return False

    def _get_trade_pnl(self, sell_trade: BacktestTrade) -> float:
        """Get P&L for a sell trade"""
        # Find corresponding buy trade
        for buy_trade in reversed(self.trades):
            if (buy_trade.stock_code == sell_trade.stock_code and
                buy_trade.action == 'buy' and
                buy_trade.timestamp < sell_trade.timestamp):
                pnl = (sell_trade.price - buy_trade.price) * sell_trade.quantity
                pnl -= (sell_trade.commission + buy_trade.commission)
                return pnl
        return 0.0


# ============================================================================
# Strategy Templates
# ============================================================================

def moving_average_crossover_strategy(data: Dict, portfolio: Dict) -> Optional[Dict]:
    """
    Simple moving average crossover strategy

    Buy: When short MA crosses above long MA
    Sell: When short MA crosses below long MA
    """
    # This is a template - would need historical MA calculation
    # For demo purposes, using random signals

    signal = np.random.choice(['buy', 'sell', 'hold'], p=[0.1, 0.1, 0.8])

    if signal == 'buy' and portfolio['cash'] > 100000:
        return {
            'action': 'buy',
            'stock_code': data.get('stock_code'),
            'quantity': 10
        }
    elif signal == 'sell' and portfolio['total_positions'] > 0:
        stock_code = data.get('stock_code')
        if stock_code in portfolio['positions']:
            return {
                'action': 'sell',
                'stock_code': stock_code,
                'quantity': 5
            }

    return {'action': 'hold'}


def rsi_strategy(data: Dict, portfolio: Dict) -> Optional[Dict]:
    """
    RSI-based strategy

    Buy: RSI < 30 (oversold)
    Sell: RSI > 70 (overbought)
    """
    rsi = data.get('rsi', 50)

    if rsi < 30 and portfolio['cash'] > 100000:
        return {
            'action': 'buy',
            'stock_code': data.get('stock_code'),
            'quantity': 15
        }
    elif rsi > 70 and portfolio['total_positions'] > 0:
        return {
            'action': 'sell',
            'stock_code': data.get('stock_code'),
            'quantity': 10
        }

    return {'action': 'hold'}


# Singleton instance
_backtest_engine = None

def get_backtest_engine(config: BacktestConfig = None) -> BacktestEngine:
    """Get backtest engine instance"""
    global _backtest_engine
    if _backtest_engine is None:
        _backtest_engine = BacktestEngine(config)
    return _backtest_engine


if __name__ == '__main__':
    print("🔄 Backtesting Engine Test")

    # Generate mock historical data
    historical_data = []
    base_price = 73000
    for i in range(100):
        price_change = np.random.uniform(-0.03, 0.03)
        close_price = base_price * (1 + price_change)

        historical_data.append({
            'date': (datetime.now() - timedelta(days=100-i)).isoformat(),
            'stock_code': '005930',
            'open': base_price,
            'high': close_price * 1.02,
            'low': close_price * 0.98,
            'close': close_price,
            'volume': int(np.random.uniform(500000, 2000000)),
            'rsi': np.random.uniform(20, 80)
        })

        base_price = close_price

    # Run backtest
    engine = get_backtest_engine()
    result = engine.run_backtest(
        historical_data,
        moving_average_crossover_strategy,
        "Moving Average Crossover"
    )

    print(f"\n백테스트 결과:")
    print(f"총 수익: {result.total_return:+,.0f}원 ({result.total_return_pct:+.2f}%)")
    print(f"샤프 비율: {result.sharpe_ratio:.2f}")
    print(f"최대 낙폭: {result.max_drawdown_pct:.2f}%")
    print(f"승률: {result.win_rate:.1f}%")
    print(f"수익 팩터: {result.profit_factor:.2f}")
