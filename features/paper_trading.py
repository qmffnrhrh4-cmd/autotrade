"""
Paper Trading Engine
Real-time virtual trading system for strategy testing and AI learning

Features:
- Multiple strategies running simultaneously
- Separate virtual accounts per strategy
- Real-time market data simulation
- 24/7 background execution
- Performance tracking and ranking
- AI learning data source
"""
import json
import threading
import time
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import logging

from config.constants import DELAYS

logger = logging.getLogger(__name__)


@dataclass
class VirtualPosition:
    """Virtual stock position"""
    stock_code: str
    stock_name: str
    quantity: int
    buy_price: float
    buy_time: str
    current_price: float
    profit_loss: float
    profit_loss_pct: float
    strategy_name: str


@dataclass
class VirtualTrade:
    """Virtual trade record"""
    id: str
    strategy_name: str
    trade_type: str  # 'buy' or 'sell'
    stock_code: str
    stock_name: str
    quantity: int
    price: float
    timestamp: str
    reason: str
    total_amount: float


@dataclass
class VirtualAccount:
    """Virtual trading account"""
    strategy_name: str
    initial_balance: float
    current_balance: float
    total_value: float  # Balance + positions value
    positions: List[VirtualPosition]
    trades: List[VirtualTrade]
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    max_drawdown: float
    sharpe_ratio: float
    created_at: str
    last_updated: str


@dataclass
class StrategyConfig:
    """Strategy configuration for paper trading"""
    name: str
    description: str
    initial_balance: float
    max_positions: int
    position_size: float  # Amount per trade
    stop_loss_pct: float
    take_profit_pct: float
    entry_conditions: Dict[str, Any]
    exit_conditions: Dict[str, Any]
    is_active: bool = True


@dataclass
class StrategyPerformance:
    """Strategy performance metrics"""
    strategy_name: str
    rank: int
    total_return: float
    total_return_pct: float
    win_rate: float
    total_trades: int
    avg_profit_per_trade: float
    sharpe_ratio: float
    max_drawdown: float
    current_positions: int
    last_trade_time: str
    score: float  # Overall performance score


class PaperTradingEngine:
    """
    Real-time paper trading engine

    Runs multiple strategies simultaneously in virtual accounts
    Uses real market data for realistic simulation
    Runs 24/7 in background thread
    """

    def __init__(self, market_api=None, ai_agent=None):
        """
        Initialize paper trading engine

        Args:
            market_api: Market API for real-time data
            ai_agent: AI agent for learning integration
        """
        self.market_api = market_api
        self.ai_agent = ai_agent

        # Virtual accounts (one per strategy)
        self.accounts: Dict[str, VirtualAccount] = {}

        # Strategy configs
        self.strategies: Dict[str, StrategyConfig] = {}

        # Background execution
        self.is_running = False
        self.execution_thread: Optional[threading.Thread] = None

        # Data files
        self.data_dir = Path('data/paper_trading')
        self.accounts_file = self.data_dir / 'accounts.json'
        self.strategies_file = self.data_dir / 'strategies.json'
        self.trades_file = self.data_dir / 'trades.json'

        self._ensure_data_dir()
        self._load_state()
        self._initialize_default_strategies()

    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _load_state(self):
        """Load saved state from files"""
        try:
            # Load strategies
            if self.strategies_file.exists():
                with open(self.strategies_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for s in data.get('strategies', []):
                        self.strategies[s['name']] = StrategyConfig(**s)
                logger.info(f"Loaded {len(self.strategies)} paper trading strategies")

            # Load accounts
            if self.accounts_file.exists():
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for a in data.get('accounts', []):
                        # Reconstruct positions and trades
                        positions = [VirtualPosition(**p) for p in a.get('positions', [])]
                        trades = [VirtualTrade(**t) for t in a.get('trades', [])]
                        a['positions'] = positions
                        a['trades'] = trades
                        self.accounts[a['strategy_name']] = VirtualAccount(**a)
                logger.info(f"Loaded {len(self.accounts)} virtual accounts")

        except Exception as e:
            logger.error(f"Error loading paper trading state: {e}")

    def _save_state(self):
        """Save state to files"""
        try:
            # Save strategies
            with open(self.strategies_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'strategies': [asdict(s) for s in self.strategies.values()],
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

            # Save accounts
            with open(self.accounts_file, 'w', encoding='utf-8') as f:
                accounts_data = []
                for account in self.accounts.values():
                    acc_dict = asdict(account)
                    accounts_data.append(acc_dict)

                json.dump({
                    'accounts': accounts_data,
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Error saving paper trading state: {e}")

    def _initialize_default_strategies(self):
        """Initialize default strategies if none exist"""
        if len(self.strategies) > 0:
            return

        default_strategies = [
            StrategyConfig(
                name='공격적 모멘텀',
                description='높은 모멘텀 + 강한 거래량',
                initial_balance=10000000,  # 1000만원
                max_positions=3,
                position_size=3000000,  # 300만원
                stop_loss_pct=-2.0,
                take_profit_pct=8.0,
                entry_conditions={
                    'rsi_min': 50,
                    'rsi_max': 75,
                    'volume_ratio_min': 2.0,
                    'score_min': 350
                },
                exit_conditions={
                    'stop_loss': -2.0,
                    'take_profit': 8.0
                }
            ),
            StrategyConfig(
                name='보수적 가치',
                description='저평가 종목 장기 보유',
                initial_balance=10000000,
                max_positions=5,
                position_size=2000000,  # 200만원
                stop_loss_pct=-5.0,
                take_profit_pct=15.0,
                entry_conditions={
                    'rsi_min': 20,
                    'rsi_max': 40,
                    'score_min': 300
                },
                exit_conditions={
                    'stop_loss': -5.0,
                    'take_profit': 15.0
                }
            ),
            StrategyConfig(
                name='균형 분산',
                description='중립적 다각화 전략',
                initial_balance=10000000,
                max_positions=7,
                position_size=1400000,  # 140만원
                stop_loss_pct=-3.0,
                take_profit_pct=6.0,
                entry_conditions={
                    'rsi_min': 35,
                    'rsi_max': 65,
                    'volume_ratio_min': 1.3,
                    'score_min': 320
                },
                exit_conditions={
                    'stop_loss': -3.0,
                    'take_profit': 6.0
                }
            ),
            StrategyConfig(
                name='AI 동적',
                description='AI가 실시간 조정하는 전략',
                initial_balance=10000000,
                max_positions=5,
                position_size=2000000,
                stop_loss_pct=-3.0,
                take_profit_pct=5.0,
                entry_conditions={
                    'ai_confidence_min': 0.7,
                    'score_min': 300
                },
                exit_conditions={
                    'stop_loss': -3.0,
                    'take_profit': 5.0
                }
            ),
        ]

        for strategy in default_strategies:
            self.add_strategy(strategy)

        logger.info(f"Initialized {len(default_strategies)} default strategies")

    def add_strategy(self, strategy: StrategyConfig):
        """Add a new strategy"""
        self.strategies[strategy.name] = strategy

        # Create virtual account for strategy
        account = VirtualAccount(
            strategy_name=strategy.name,
            initial_balance=strategy.initial_balance,
            current_balance=strategy.initial_balance,
            total_value=strategy.initial_balance,
            positions=[],
            trades=[],
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_profit=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
        self.accounts[strategy.name] = account

        self._save_state()
        logger.info(f"Added paper trading strategy: {strategy.name}")

    def start(self):
        """Start paper trading engine in background"""
        if self.is_running:
            logger.warning("Paper trading engine already running")
            return

        self.is_running = True
        self.execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
        self.execution_thread.start()
        logger.info("📈 Paper Trading Engine STARTED - Running 24/7 in background")

    def stop(self):
        """Stop paper trading engine"""
        self.is_running = False
        if self.execution_thread:
            self.execution_thread.join(timeout=5)
        logger.info("📈 Paper Trading Engine STOPPED")

    def _execution_loop(self):
        """Main execution loop (runs in background thread)"""
        logger.info("Paper trading execution loop started")

        while self.is_running:
            try:
                # Execute one iteration for all strategies
                self._execute_iteration()

                # Save state periodically
                self._save_state()

                time.sleep(DELAYS['paper_trading_check'])

            except Exception as e:
                logger.error(f"Error in paper trading execution loop: {e}")
                time.sleep(DELAYS['paper_trading_error'])

    def _execute_iteration(self):
        """Execute one iteration of paper trading"""
        # Get available stocks from scanner (mock for now)
        candidates = self._get_candidates()

        if not candidates:
            return

        # Execute each strategy
        for strategy_name, strategy in self.strategies.items():
            if not strategy.is_active:
                continue

            try:
                self._execute_strategy(strategy_name, strategy, candidates)
            except Exception as e:
                logger.error(f"Error executing strategy {strategy_name}: {e}")

        # Update all positions with current prices
        self._update_positions()

        # Check exit conditions
        self._check_exit_conditions()

    def _get_candidates(self) -> List[Dict[str, Any]]:
        """Get candidate stocks (from scanner or mock)"""
        # TODO: Integrate with real scanner
        # For now, return mock candidates
        mock_candidates = [
            {
                'code': '005930',
                'name': '삼성전자',
                'current_price': 73500,
                'rsi': 55,
                'volume_ratio': 1.5,
                'score': 380
            },
            {
                'code': '000660',
                'name': 'SK하이닉스',
                'current_price': 130000,
                'rsi': 62,
                'volume_ratio': 1.8,
                'score': 360
            },
            {
                'code': '035720',
                'name': '카카오',
                'current_price': 45500,
                'rsi': 42,
                'volume_ratio': 1.2,
                'score': 340
            },
        ]
        return mock_candidates

    def _execute_strategy(
        self,
        strategy_name: str,
        strategy: StrategyConfig,
        candidates: List[Dict[str, Any]]
    ):
        """Execute a strategy with given candidates"""
        account = self.accounts[strategy_name]

        # Check if can buy more
        if len(account.positions) >= strategy.max_positions:
            return

        if account.current_balance < strategy.position_size:
            return

        # Find stocks matching entry conditions
        for candidate in candidates:
            # Check if already holding
            if any(p.stock_code == candidate['code'] for p in account.positions):
                continue

            # Check entry conditions
            if self._check_entry_conditions(strategy, candidate):
                # Execute virtual buy
                self._execute_virtual_buy(strategy_name, strategy, candidate)
                break  # One buy per iteration

    def _check_entry_conditions(
        self,
        strategy: StrategyConfig,
        candidate: Dict[str, Any]
    ) -> bool:
        """Check if candidate meets entry conditions"""
        conditions = strategy.entry_conditions

        # AI strategy - use AI decision
        if 'ai_confidence_min' in conditions:
            if self.ai_agent:
                decision = self.ai_agent.make_trading_decision(
                    candidate['code'],
                    candidate['name'],
                    candidate
                )
                return (decision.decision_type == 'buy' and
                        decision.confidence >= conditions['ai_confidence_min'])
            return False

        # Regular conditions
        rsi = candidate.get('rsi', 50)
        volume_ratio = candidate.get('volume_ratio', 1.0)
        score = candidate.get('score', 0)

        if 'rsi_min' in conditions and rsi < conditions['rsi_min']:
            return False
        if 'rsi_max' in conditions and rsi > conditions['rsi_max']:
            return False
        if 'volume_ratio_min' in conditions and volume_ratio < conditions['volume_ratio_min']:
            return False
        if 'score_min' in conditions and score < conditions['score_min']:
            return False

        return True

    def _execute_virtual_buy(
        self,
        strategy_name: str,
        strategy: StrategyConfig,
        candidate: Dict[str, Any]
    ):
        """Execute virtual buy order"""
        account = self.accounts[strategy_name]

        price = candidate['current_price']
        quantity = int(strategy.position_size / price)

        if quantity == 0:
            return

        total_cost = price * quantity

        # Create position
        position = VirtualPosition(
            stock_code=candidate['code'],
            stock_name=candidate['name'],
            quantity=quantity,
            buy_price=price,
            buy_time=datetime.now().isoformat(),
            current_price=price,
            profit_loss=0,
            profit_loss_pct=0,
            strategy_name=strategy_name
        )

        # Create trade record
        trade = VirtualTrade(
            id=f"{strategy_name}_{int(datetime.now().timestamp())}",
            strategy_name=strategy_name,
            trade_type='buy',
            stock_code=candidate['code'],
            stock_name=candidate['name'],
            quantity=quantity,
            price=price,
            timestamp=datetime.now().isoformat(),
            reason=f"Entry conditions met (RSI: {candidate.get('rsi', 'N/A')}, Score: {candidate.get('score', 'N/A')})",
            total_amount=total_cost
        )

        # Update account
        account.positions.append(position)
        account.trades.append(trade)
        account.current_balance -= total_cost
        account.total_trades += 1
        account.last_updated = datetime.now().isoformat()

        logger.info(f"[{strategy_name}] Virtual BUY: {candidate['name']} {quantity}주 @ {price:,}원")

    def _update_positions(self):
        """Update all positions with current prices"""
        for account in self.accounts.values():
            for position in account.positions:
                # Get current price (mock for now)
                # TODO: Use real market API
                price_change = np.random.uniform(-0.02, 0.02)  # -2% to +2%
                position.current_price = position.buy_price * (1 + price_change)

                # Calculate P/L
                position.profit_loss = (position.current_price - position.buy_price) * position.quantity
                position.profit_loss_pct = ((position.current_price - position.buy_price) / position.buy_price) * 100

            # Update total value
            positions_value = sum(p.current_price * p.quantity for p in account.positions)
            account.total_value = account.current_balance + positions_value
            account.total_profit = account.total_value - account.initial_balance

    def _check_exit_conditions(self):
        """Check exit conditions for all positions"""
        for strategy_name, account in self.accounts.items():
            strategy = self.strategies[strategy_name]

            positions_to_remove = []

            for i, position in enumerate(account.positions):
                should_exit = False
                exit_reason = ""

                # Stop loss
                if position.profit_loss_pct <= strategy.stop_loss_pct:
                    should_exit = True
                    exit_reason = f"Stop Loss ({position.profit_loss_pct:.1f}%)"

                # Take profit
                elif position.profit_loss_pct >= strategy.take_profit_pct:
                    should_exit = True
                    exit_reason = f"Take Profit ({position.profit_loss_pct:.1f}%)"

                if should_exit:
                    self._execute_virtual_sell(strategy_name, position, exit_reason)
                    positions_to_remove.append(i)

            # Remove sold positions
            for i in reversed(positions_to_remove):
                account.positions.pop(i)

    def _execute_virtual_sell(
        self,
        strategy_name: str,
        position: VirtualPosition,
        reason: str
    ):
        """Execute virtual sell order"""
        account = self.accounts[strategy_name]

        total_proceeds = position.current_price * position.quantity

        # Create trade record
        trade = VirtualTrade(
            id=f"{strategy_name}_{int(datetime.now().timestamp())}",
            strategy_name=strategy_name,
            trade_type='sell',
            stock_code=position.stock_code,
            stock_name=position.stock_name,
            quantity=position.quantity,
            price=position.current_price,
            timestamp=datetime.now().isoformat(),
            reason=reason,
            total_amount=total_proceeds
        )

        # Update account
        account.trades.append(trade)
        account.current_balance += total_proceeds
        account.last_updated = datetime.now().isoformat()

        # Update win/loss stats
        if position.profit_loss > 0:
            account.winning_trades += 1
        else:
            account.losing_trades += 1

        account.win_rate = (account.winning_trades / (account.winning_trades + account.losing_trades)
                           if (account.winning_trades + account.losing_trades) > 0 else 0)

        logger.info(f"[{strategy_name}] Virtual SELL: {position.stock_name} "
                   f"{position.quantity}주 @ {position.current_price:,.0f}원 "
                   f"({position.profit_loss_pct:+.1f}%) - {reason}")

        # Feed to AI for learning if profitable strategy
        if self.ai_agent and position.profit_loss > 0:
            self.ai_agent.learn_from_trade_result({
                'stock_code': position.stock_code,
                'profit': position.profit_loss,
                'profit_pct': position.profit_loss_pct,
                'strategy': strategy_name
            })

    def get_strategy_rankings(self) -> List[StrategyPerformance]:
        """Get strategy performance rankings"""
        performances = []

        for strategy_name, account in self.accounts.items():
            # Calculate performance score
            return_pct = ((account.total_value - account.initial_balance) / account.initial_balance) * 100
            score = (
                return_pct * 0.4 +
                account.win_rate * 100 * 0.3 +
                (account.total_trades / 10) * 0.2 -
                account.max_drawdown * 0.1
            )

            last_trade_time = (account.trades[-1].timestamp if account.trades
                              else account.created_at)

            perf = StrategyPerformance(
                strategy_name=strategy_name,
                rank=0,  # Will be set after sorting
                total_return=account.total_profit,
                total_return_pct=return_pct,
                win_rate=account.win_rate,
                total_trades=account.total_trades,
                avg_profit_per_trade=(account.total_profit / account.total_trades
                                     if account.total_trades > 0 else 0),
                sharpe_ratio=account.sharpe_ratio,
                max_drawdown=account.max_drawdown,
                current_positions=len(account.positions),
                last_trade_time=last_trade_time,
                score=score
            )
            performances.append(perf)

        # Sort by score
        performances.sort(key=lambda x: x.score, reverse=True)

        # Assign ranks
        for i, perf in enumerate(performances):
            perf.rank = i + 1

        return performances

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard"""
        rankings = self.get_strategy_rankings()

        return {
            'success': True,
            'is_running': self.is_running,
            'total_strategies': len(self.strategies),
            'active_strategies': sum(1 for s in self.strategies.values() if s.is_active),
            'rankings': [asdict(r) for r in rankings],
            'accounts': {name: asdict(acc) for name, acc in self.accounts.items()},
            'best_strategy': rankings[0].strategy_name if rankings else None,
            'last_updated': datetime.now().isoformat()
        }


# Global instance
_paper_trading_engine: Optional[PaperTradingEngine] = None


def get_paper_trading_engine(market_api=None, ai_agent=None) -> PaperTradingEngine:
    """Get or create paper trading engine instance"""
    global _paper_trading_engine
    if _paper_trading_engine is None:
        _paper_trading_engine = PaperTradingEngine(market_api, ai_agent)
    return _paper_trading_engine


# Example usage
if __name__ == '__main__':
    # Test paper trading engine
    engine = PaperTradingEngine()

    print("\n📈 Paper Trading Engine Test")
    print("=" * 60)

    # Start engine
    engine.start()

    print(f"Strategies: {len(engine.strategies)}")
    for name in engine.strategies:
        print(f"  - {name}")

    # Let it run for a bit
    time.sleep(5)

    # Get rankings
    rankings = engine.get_strategy_rankings()
    print(f"\n전략 순위:")
    for rank in rankings:
        print(f"  {rank.rank}. {rank.strategy_name}")
        print(f"     수익률: {rank.total_return_pct:+.1f}%")
        print(f"     승률: {rank.win_rate:.0%}")
        print(f"     거래 수: {rank.total_trades}")

    # Stop engine
    engine.stop()
