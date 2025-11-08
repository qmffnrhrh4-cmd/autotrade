"""
Strategy Backtester - 12가지 가상매매 전략 백테스팅
"""
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.logger_new import get_logger
from virtual_trading.diverse_strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    BreakoutStrategy,
    ValueInvestingStrategy,
    SwingTradingStrategy,
    MACDStrategy,
    ContrarianStrategy,
    SectorRotationStrategy,
    HotStockStrategy,
    DividendGrowthStrategy,
    InstitutionalFollowingStrategy,
    VolumeRSIStrategy
)

logger = get_logger()


@dataclass
class BacktestResult:
    strategy_name: str
    initial_cash: float
    final_cash: float
    total_return: float
    total_return_pct: float

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float

    daily_returns: List[float] = field(default_factory=list)
    daily_cash: List[float] = field(default_factory=list)
    daily_dates: List[str] = field(default_factory=list)

    trades: List[Dict[str, Any]] = field(default_factory=list)

    avg_profit_per_trade: float = 0.0
    avg_loss_per_trade: float = 0.0
    profit_factor: float = 0.0

    def calculate_metrics(self):
        if self.total_trades > 0:
            profits = [t['profit'] for t in self.trades if t['profit'] > 0]
            losses = [t['profit'] for t in self.trades if t['profit'] < 0]

            self.avg_profit_per_trade = sum(profits) / len(profits) if profits else 0
            self.avg_loss_per_trade = sum(losses) / len(losses) if losses else 0

            total_profit = sum(profits)
            total_loss = abs(sum(losses))
            self.profit_factor = total_profit / total_loss if total_loss > 0 else 0

        if len(self.daily_returns) > 1:
            returns = np.array(self.daily_returns)

            if np.std(returns) > 0:
                self.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)

            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0 and np.std(downside_returns) > 0:
                self.sortino_ratio = np.mean(returns) / np.std(downside_returns) * np.sqrt(252)

        if len(self.daily_cash) > 0:
            peak = self.initial_cash
            max_dd = 0

            for cash in self.daily_cash:
                if cash > peak:
                    peak = cash
                dd = peak - cash
                if dd > max_dd:
                    max_dd = dd

            self.max_drawdown = max_dd
            self.max_drawdown_pct = (max_dd / peak * 100) if peak > 0 else 0


class StrategyBacktester:

    def __init__(self, market_api, chart_api=None):
        self.market_api = market_api
        self.chart_api = chart_api

        # 백테스팅 비활성화 (전략 클래스 구조 변경으로 인한 임시 조치)
        self.strategies = []
        logger.warning("Backtesting disabled - strategy classes need refactoring")

        logger.info(f"Strategy Backtester initialized with {len(self.strategies)} strategies")

    def run_backtest(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        interval: str = '1',
        parallel: bool = True
    ) -> Dict[str, BacktestResult]:
        """
        백테스트 실행

        Args:
            stock_codes: 종목 코드 리스트
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            interval: 분봉 간격 (1, 3, 5, 10, 15, 30, 60)
            parallel: 병렬 처리 여부

        Returns:
            전략별 백테스트 결과
        """
        logger.info("="*80)
        logger.info(f"Starting Backtest: {len(stock_codes)} stocks, {start_date} ~ {end_date}")
        logger.info("="*80)

        historical_data = self._fetch_historical_data(stock_codes, start_date, end_date, interval)

        if not historical_data:
            logger.error("No historical data fetched")
            return {}

        results = {}

        if parallel and len(self.strategies) > 1:
            logger.info(f"Running {len(self.strategies)} strategies in parallel...")

            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_strategy = {
                    executor.submit(
                        self._backtest_strategy,
                        strategy,
                        historical_data,
                        start_date,
                        end_date
                    ): strategy
                    for strategy in self.strategies
                }

                for future in as_completed(future_to_strategy):
                    strategy = future_to_strategy[future]
                    try:
                        result = future.result()
                        results[strategy.name] = result
                        logger.info(f"✓ {strategy.name}: {result.total_return_pct:+.2f}%")
                    except Exception as e:
                        logger.error(f"✗ {strategy.name}: {e}")
        else:
            for strategy in self.strategies:
                try:
                    result = self._backtest_strategy(strategy, historical_data, start_date, end_date)
                    results[strategy.name] = result
                    logger.info(f"✓ {strategy.name}: {result.total_return_pct:+.2f}%")
                except Exception as e:
                    logger.error(f"✗ {strategy.name}: {e}")

        logger.info("="*80)
        logger.info("Backtest Complete")
        logger.info("="*80)

        return results

    def _fetch_historical_data(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        interval: str
    ) -> Dict[str, pd.DataFrame]:
        """
        과거 데이터 수집

        Returns:
            {stock_code: DataFrame}
        """
        logger.info(f"Fetching historical data for {len(stock_codes)} stocks...")

        historical_data = {}

        try:
            from api.market.chart_data import ChartDataAPI

            if not self.chart_api:
                self.chart_api = ChartDataAPI(self.market_api.client)

            for stock_code in stock_codes:
                try:
                    data = self.chart_api.get_minute_chart(
                        stock_code=stock_code,
                        interval=interval,
                        period='D',
                        count=1000
                    )

                    if data and isinstance(data, list) and len(data) > 0:
                        df = pd.DataFrame(data)

                        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
                        df['time'] = pd.to_datetime(df['time'], format='%H%M%S').dt.time
                        df['datetime'] = pd.to_datetime(
                            df['date'].dt.strftime('%Y%m%d') + ' ' + df['time'].astype(str),
                            format='%Y%m%d %H:%M:%S'
                        )

                        df = df.sort_values('datetime')

                        start_dt = pd.to_datetime(start_date, format='%Y%m%d')
                        end_dt = pd.to_datetime(end_date, format='%Y%m%d')

                        df = df[(df['datetime'] >= start_dt) & (df['datetime'] <= end_dt)]

                        if len(df) > 0:
                            historical_data[stock_code] = df
                            logger.info(f"  {stock_code}: {len(df)} bars")
                        else:
                            logger.warning(f"  {stock_code}: No data in date range")
                    else:
                        logger.warning(f"  {stock_code}: No data returned")

                except Exception as e:
                    logger.error(f"  {stock_code}: Failed - {e}")

                time.sleep(0.2)

        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")

            logger.info("Generating simulated data for testing...")
            historical_data = self._generate_simulated_data(stock_codes, start_date, end_date)

        return historical_data

    def _generate_simulated_data(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        시뮬레이션 데이터 생성 (테스트용)
        """
        logger.info("Generating simulated market data...")

        start_dt = pd.to_datetime(start_date, format='%Y%m%d')
        end_dt = pd.to_datetime(end_date, format='%Y%m%d')

        dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        dates = dates[dates.dayofweek < 5]

        historical_data = {}

        for stock_code in stock_codes:
            np.random.seed(hash(stock_code) % (2**32))

            data = []
            base_price = np.random.uniform(10000, 100000)

            for date in dates:
                for hour in range(9, 16):
                    for minute in range(0, 60, 5):
                        if hour == 9 and minute < 0:
                            continue
                        if hour == 15 and minute > 30:
                            continue

                        dt = pd.Timestamp(year=date.year, month=date.month, day=date.day,
                                        hour=hour, minute=minute)

                        price_change = np.random.normal(0, base_price * 0.005)
                        base_price += price_change
                        base_price = max(base_price, 1000)

                        open_price = base_price
                        high_price = base_price * (1 + abs(np.random.normal(0, 0.003)))
                        low_price = base_price * (1 - abs(np.random.normal(0, 0.003)))
                        close_price = np.random.uniform(low_price, high_price)
                        volume = int(np.random.lognormal(10, 2))

                        data.append({
                            'datetime': dt,
                            'open': int(open_price),
                            'high': int(high_price),
                            'low': int(low_price),
                            'close': int(close_price),
                            'volume': volume
                        })

            df = pd.DataFrame(data)
            historical_data[stock_code] = df
            logger.info(f"  {stock_code}: {len(df)} simulated bars")

        return historical_data

    def _backtest_strategy(
        self,
        strategy,
        historical_data: Dict[str, pd.DataFrame],
        start_date: str,
        end_date: str
    ) -> BacktestResult:
        """
        단일 전략 백테스트
        """
        strategy.reset()

        result = BacktestResult(
            strategy_name=strategy.name,
            initial_cash=strategy.cash,
            final_cash=strategy.cash,
            total_return=0.0,
            total_return_pct=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0
        )

        all_datetimes = set()
        for df in historical_data.values():
            all_datetimes.update(df['datetime'].tolist())

        all_datetimes = sorted(list(all_datetimes))

        daily_cash_map = {}

        for dt in all_datetimes:
            date_str = dt.strftime('%Y-%m-%d')

            current_prices = {}
            for stock_code, df in historical_data.items():
                row = df[df['datetime'] == dt]
                if not row.empty:
                    current_prices[stock_code] = int(row.iloc[0]['close'])

            for stock_code, price in current_prices.items():
                stock_data = {
                    'stock_code': stock_code,
                    'stock_name': stock_code,
                    'current_price': price,
                    'volume': 1000000,
                    'change_rate': np.random.uniform(-2, 2),
                    'institutional_net_buy': int(np.random.normal(0, 10_000_000)),
                    'foreign_net_buy': int(np.random.normal(0, 5_000_000)),
                }

                market_data = {
                    'fear_greed_index': 50,
                    'economic_cycle': 'expansion',
                    'market_trend': 'neutral'
                }

                ai_analysis = {
                    'signal': 'buy' if np.random.random() > 0.5 else 'hold',
                    'score': np.random.uniform(200, 350)
                }

                if strategy.should_buy(stock_data, market_data, ai_analysis):
                    buy_price = price
                    quantity = int(strategy.cash * 0.1 / buy_price)

                    if quantity > 0 and strategy.cash >= buy_price * quantity:
                        strategy.cash -= buy_price * quantity
                        strategy.positions[stock_code] = {
                            'quantity': quantity,
                            'buy_price': buy_price,
                            'buy_date': dt
                        }

            for stock_code in list(strategy.positions.keys()):
                if stock_code in current_prices:
                    position = strategy.positions[stock_code]
                    current_price = current_prices[stock_code]

                    profit_loss = (current_price - position['buy_price']) * position['quantity']
                    profit_loss_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100

                    if strategy.should_sell(stock_code, position, current_price):
                        sell_price = current_price
                        quantity = position['quantity']

                        strategy.cash += sell_price * quantity

                        result.trades.append({
                            'stock_code': stock_code,
                            'buy_date': position['buy_date'],
                            'sell_date': dt,
                            'buy_price': position['buy_price'],
                            'sell_price': sell_price,
                            'quantity': quantity,
                            'profit': profit_loss,
                            'profit_pct': profit_loss_pct
                        })

                        result.total_trades += 1
                        if profit_loss > 0:
                            result.winning_trades += 1
                        else:
                            result.losing_trades += 1

                        del strategy.positions[stock_code]

            portfolio_value = strategy.cash
            for stock_code, position in strategy.positions.items():
                if stock_code in current_prices:
                    portfolio_value += current_prices[stock_code] * position['quantity']

            if date_str not in daily_cash_map:
                daily_cash_map[date_str] = portfolio_value

        for date_str in sorted(daily_cash_map.keys()):
            result.daily_dates.append(date_str)
            result.daily_cash.append(daily_cash_map[date_str])

        if len(result.daily_cash) > 1:
            for i in range(1, len(result.daily_cash)):
                daily_return = (result.daily_cash[i] - result.daily_cash[i-1]) / result.daily_cash[i-1]
                result.daily_returns.append(daily_return * 100)

        result.final_cash = strategy.cash
        for stock_code, position in strategy.positions.items():
            if stock_code in historical_data:
                last_price = int(historical_data[stock_code].iloc[-1]['close'])
                result.final_cash += last_price * position['quantity']

        result.total_return = result.final_cash - result.initial_cash
        result.total_return_pct = (result.total_return / result.initial_cash) * 100

        if result.total_trades > 0:
            result.win_rate = (result.winning_trades / result.total_trades) * 100

        result.calculate_metrics()

        return result

    def get_ranking(self, results: Dict[str, BacktestResult]) -> List[Tuple[str, BacktestResult]]:
        """
        전략 순위 (수익률 기준)
        """
        return sorted(
            results.items(),
            key=lambda x: x[1].total_return_pct,
            reverse=True
        )

    def get_best_strategy(self, results: Dict[str, BacktestResult]) -> Optional[Tuple[str, BacktestResult]]:
        """
        최고 전략
        """
        ranking = self.get_ranking(results)
        return ranking[0] if ranking else None


__all__ = ['StrategyBacktester', 'BacktestResult']
