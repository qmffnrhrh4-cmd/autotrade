"""
ai/unified_backtester.py
통합 백테스팅 엔진 - 기존 4개 파일 통합

- backtesting.py
- strategy_backtester.py
- advanced_backtester.py
- virtual_trading/backtest_adapter.py

Features:
- 다양한 전략 백테스팅
- 슬리피지 & 수수료 반영
- 리스크 메트릭 계산 (Sharpe, Sortino, MDD)
- Monte Carlo 시뮬레이션
- 워크포워드 분석
- OpenAPI 연동 데이터 조회
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from collections import OrderedDict
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import statistics

from utils.logger_new import get_logger
from core import Position, Trade as CoreTrade, OrderAction

logger = get_logger()


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class BacktestConfig:
    """백테스트 설정"""
    initial_capital: float = 10_000_000
    commission_rate: float = 0.00015
    slippage_pct: float = 0.001
    tax_rate: float = 0.0023
    risk_free_rate: float = 0.02
    position_size_limit: float = 0.3
    max_positions: int = 5
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None


@dataclass
class BacktestTrade:
    """백테스트 거래 기록"""
    trade_id: int
    timestamp: datetime
    stock_code: str
    side: str
    quantity: int
    price: float
    value: float
    commission: float = 0.0
    slippage: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    holding_days: int = 0
    reason: str = ""


@dataclass
class BacktestResult:
    """백테스트 결과"""
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float

    total_return: float
    total_return_pct: float

    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    calmar_ratio: float

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    avg_win: float
    avg_loss: float
    max_win: float
    max_loss: float
    profit_factor: float

    avg_holding_days: float
    total_commission: float

    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)
    drawdown_curve: List[Tuple[datetime, float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'strategy_name': self.strategy_name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_return': self.total_return,
            'total_return_pct': self.total_return_pct,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'calmar_ratio': self.calmar_ratio,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'avg_holding_days': self.avg_holding_days,
            'total_commission': self.total_commission,
        }


class UnifiedBacktester:
    """
    통합 백테스팅 엔진

    기존 4개 백테스터의 모든 기능을 통합:
    - BacktestEngine (backtesting.py)
    - StrategyBacktester (strategy_backtester.py)
    - AdvancedBacktester (advanced_backtester.py)
    - BacktestAdapter (backtest_adapter.py)
    """

    def __init__(
        self,
        config: Optional[BacktestConfig] = None,
        market_api=None,
        openapi_client=None
    ):
        """
        초기화

        Args:
            config: 백테스트 설정
            market_api: MarketAPI 인스턴스 (REST API)
            openapi_client: OpenAPI 클라이언트
        """
        self.config = config or BacktestConfig()
        self.market_api = market_api
        self.openapi_client = openapi_client

        self._reset()

        logger.info(f"UnifiedBacktester 초기화 - 초기자본: {self.config.initial_capital:,}원")

    def _reset(self):
        """상태 초기화"""
        self.cash = self.config.initial_capital
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.daily_returns: List[float] = []
        self.trade_counter = 0
        self.peak_equity = self.config.initial_capital
        self.max_drawdown = 0.0
        self.current_time: Optional[datetime] = None

    def run_backtest(
        self,
        strategy_fn: Callable,
        historical_data: Dict[str, pd.DataFrame],
        strategy_name: str = "Custom Strategy",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> BacktestResult:
        """
        백테스트 실행

        Args:
            strategy_fn: 전략 함수 (context, data) -> signals
            historical_data: {stock_code: DataFrame} 형태의 과거 데이터
            strategy_name: 전략 이름
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)

        Returns:
            BacktestResult
        """
        self._reset()

        logger.info(f"백테스트 시작: {strategy_name}")
        logger.info(f"  - 초기자본: {self.config.initial_capital:,}원")
        logger.info(f"  - 수수료율: {self.config.commission_rate:.4%}")
        logger.info(f"  - 슬리피지: {self.config.slippage_pct:.4%}")

        all_dates = self._get_all_dates(historical_data, start_date, end_date)

        if not all_dates:
            logger.error("거래일 데이터가 없습니다")
            return self._create_empty_result(strategy_name)

        prev_equity = self.config.initial_capital

        for i, date in enumerate(all_dates):
            self.current_time = date

            current_data = self._get_data_until(historical_data, date)

            self._update_positions(current_data)

            try:
                signals = strategy_fn(self, current_data)

                if signals:
                    self._execute_signals(signals, current_data)

            except Exception as e:
                logger.debug(f"전략 실행 오류 ({date}): {e}")

            equity = self._calculate_equity(current_data)
            self.equity_curve.append((date, equity))

            daily_return = (equity - prev_equity) / prev_equity * 100 if prev_equity > 0 else 0
            self.daily_returns.append(daily_return)
            prev_equity = equity

            if equity > self.peak_equity:
                self.peak_equity = equity

            if self.peak_equity > 0:
                drawdown = (self.peak_equity - equity) / self.peak_equity * 100
                drawdown = min(drawdown, 100.0)
                if drawdown > self.max_drawdown:
                    self.max_drawdown = drawdown

            if (i + 1) % 30 == 0:
                logger.debug(f"진행: {i+1}/{len(all_dates)} | 자산: {equity:,.0f}원")

        self._close_all_positions(historical_data)

        result = self._calculate_results(strategy_name, all_dates)

        logger.info(f"백테스트 완료: {strategy_name}")
        logger.info(f"  - 최종자산: {result.final_capital:,.0f}원")
        logger.info(f"  - 총수익률: {result.total_return_pct:+.2f}%")
        logger.info(f"  - Sharpe: {result.sharpe_ratio:.2f}")
        logger.info(f"  - MDD: {result.max_drawdown_pct:.2f}%")

        return result

    def run_multi_strategy_backtest(
        self,
        strategies: List[Tuple[str, Callable]],
        historical_data: Dict[str, pd.DataFrame],
        parallel: bool = True
    ) -> Dict[str, BacktestResult]:
        """
        다중 전략 백테스트

        Args:
            strategies: [(전략명, 전략함수), ...] 리스트
            historical_data: 과거 데이터
            parallel: 병렬 실행 여부

        Returns:
            {전략명: BacktestResult}
        """
        results = {}

        if parallel and len(strategies) > 1:
            logger.info(f"{len(strategies)}개 전략 병렬 백테스트 시작")

            with ThreadPoolExecutor(max_workers=min(4, len(strategies))) as executor:
                future_to_strategy = {
                    executor.submit(
                        self._run_single_strategy,
                        name, fn, historical_data
                    ): name
                    for name, fn in strategies
                }

                for future in as_completed(future_to_strategy):
                    name = future_to_strategy[future]
                    try:
                        result = future.result()
                        results[name] = result
                        logger.info(f"  ✓ {name}: {result.total_return_pct:+.2f}%")
                    except Exception as e:
                        logger.error(f"  ✗ {name}: {e}")
        else:
            for name, fn in strategies:
                try:
                    result = self.run_backtest(fn, historical_data, name)
                    results[name] = result
                except Exception as e:
                    logger.error(f"전략 '{name}' 백테스트 실패: {e}")

        return results

    def _run_single_strategy(
        self,
        name: str,
        strategy_fn: Callable,
        historical_data: Dict[str, pd.DataFrame]
    ) -> BacktestResult:
        """단일 전략 백테스트 (새 인스턴스)"""
        backtester = UnifiedBacktester(
            config=self.config,
            market_api=self.market_api,
            openapi_client=self.openapi_client
        )
        return backtester.run_backtest(strategy_fn, historical_data, name)

    def fetch_historical_data(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        interval: str = '1'
    ) -> Dict[str, pd.DataFrame]:
        """
        OpenAPI로 과거 데이터 조회

        Args:
            stock_codes: 종목 코드 리스트
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            interval: 분봉 간격

        Returns:
            {stock_code: DataFrame}
        """
        from utils.trading_date import get_last_trading_date

        today = datetime.now().strftime('%Y%m%d')
        if end_date >= today:
            end_date = get_last_trading_date()
            logger.warning(f"종료일을 마지막 거래일로 조정: {end_date}")

        historical_data = {}

        if not self.openapi_client:
            logger.warning("OpenAPI 클라이언트가 없습니다")
            return historical_data

        if not getattr(self.openapi_client, 'is_connected', False):
            logger.warning("OpenAPI가 연결되지 않았습니다")
            return historical_data

        logger.info(f"{len(stock_codes)}개 종목 과거 데이터 조회 중...")

        for stock_code in stock_codes:
            try:
                interval_int = int(interval) if isinstance(interval, str) else interval
                minute_data = self.openapi_client.get_minute_data(stock_code, interval_int)

                if not minute_data:
                    continue

                df = pd.DataFrame(minute_data)

                column_mapping = {
                    '체결시간': 'time', '현재가': 'close', '시가': 'open',
                    '고가': 'high', '저가': 'low', '거래량': 'volume', '일자': 'date'
                }
                rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
                if rename_dict:
                    df = df.rename(columns=rename_dict)

                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').abs()

                if 'datetime' not in df.columns and 'time' in df.columns:
                    time_str = df['time'].astype(str).str.strip()
                    sample_time = time_str.iloc[0] if len(time_str) > 0 else ""

                    if len(sample_time) == 14:
                        df['datetime'] = pd.to_datetime(time_str, format='%Y%m%d%H%M%S', errors='coerce')
                    elif 'date' in df.columns:
                        datetime_str = df['date'].astype(str).str.strip() + ' ' + time_str
                        df['datetime'] = pd.to_datetime(datetime_str, format='%Y%m%d %H%M%S', errors='coerce')
                    else:
                        df['date'] = end_date
                        datetime_str = df['date'].astype(str) + ' ' + time_str
                        df['datetime'] = pd.to_datetime(datetime_str, format='%Y%m%d %H%M%S', errors='coerce')

                df = df.dropna(subset=['datetime'])
                df = df.sort_values('datetime')

                start_dt = pd.to_datetime(start_date, format='%Y%m%d')
                end_dt = pd.to_datetime(end_date, format='%Y%m%d') + pd.Timedelta(days=1)
                df = df[(df['datetime'] >= start_dt) & (df['datetime'] < end_dt)]

                if len(df) > 0:
                    historical_data[stock_code] = df
                    logger.debug(f"  {stock_code}: {len(df)} bars")

                time.sleep(0.2)

            except Exception as e:
                logger.error(f"  {stock_code}: 조회 실패 - {e}")

        logger.info(f"{len(historical_data)}개 종목 데이터 조회 완료")
        return historical_data

    def buy(
        self,
        stock_code: str,
        quantity: int,
        price: Optional[float] = None,
        reason: str = ""
    ) -> Optional[BacktestTrade]:
        """
        매수 주문

        Args:
            stock_code: 종목 코드
            quantity: 수량
            price: 가격 (None이면 현재가)
            reason: 매수 사유

        Returns:
            거래 기록
        """
        if quantity <= 0 or price is None or price <= 0:
            return None

        filled_price = price * (1 + self.config.slippage_pct)

        cost = filled_price * quantity
        commission = cost * self.config.commission_rate
        total_cost = cost + commission

        if total_cost > self.cash:
            quantity = int(self.cash / (filled_price * (1 + self.config.commission_rate)))
            if quantity <= 0:
                return None
            cost = filled_price * quantity
            commission = cost * self.config.commission_rate
            total_cost = cost + commission

        equity = self._calculate_equity({})
        if cost > equity * self.config.position_size_limit:
            return None

        self.cash -= total_cost

        if stock_code in self.positions:
            pos = self.positions[stock_code]
            total_qty = pos['quantity'] + quantity
            avg_price = (pos['avg_price'] * pos['quantity'] + filled_price * quantity) / total_qty
            pos['quantity'] = total_qty
            pos['avg_price'] = avg_price
            pos['current_price'] = price
        else:
            self.positions[stock_code] = {
                'quantity': quantity,
                'avg_price': filled_price,
                'entry_time': self.current_time,
                'current_price': price
            }

        self.trade_counter += 1
        trade = BacktestTrade(
            trade_id=self.trade_counter,
            timestamp=self.current_time,
            stock_code=stock_code,
            side='buy',
            quantity=quantity,
            price=filled_price,
            value=cost,
            commission=commission,
            slippage=filled_price - price,
            reason=reason
        )
        self.trades.append(trade)

        return trade

    def sell(
        self,
        stock_code: str,
        quantity: int,
        price: Optional[float] = None,
        reason: str = ""
    ) -> Optional[BacktestTrade]:
        """
        매도 주문

        Args:
            stock_code: 종목 코드
            quantity: 수량
            price: 가격 (None이면 현재가)
            reason: 매도 사유

        Returns:
            거래 기록
        """
        if stock_code not in self.positions:
            return None

        position = self.positions[stock_code]
        quantity = min(quantity, position['quantity'])

        if quantity <= 0 or price is None or price <= 0:
            return None

        filled_price = price * (1 - self.config.slippage_pct)

        proceeds = filled_price * quantity
        commission = proceeds * self.config.commission_rate
        tax = proceeds * self.config.tax_rate
        net_proceeds = proceeds - commission - tax

        self.cash += net_proceeds

        entry_price = position['avg_price']
        pnl = (filled_price - entry_price) * quantity - commission - tax
        pnl_percent = (filled_price - entry_price) / entry_price * 100

        holding_days = 0
        if position.get('entry_time'):
            holding_days = (self.current_time - position['entry_time']).days

        position['quantity'] -= quantity
        if position['quantity'] <= 0:
            del self.positions[stock_code]

        self.trade_counter += 1
        trade = BacktestTrade(
            trade_id=self.trade_counter,
            timestamp=self.current_time,
            stock_code=stock_code,
            side='sell',
            quantity=quantity,
            price=filled_price,
            value=proceeds,
            commission=commission + tax,
            slippage=price - filled_price,
            pnl=pnl,
            pnl_percent=pnl_percent,
            holding_days=holding_days,
            reason=reason
        )
        self.trades.append(trade)

        return trade

    def get_position(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """포지션 조회"""
        return self.positions.get(stock_code)

    def has_position(self, stock_code: str) -> bool:
        """포지션 보유 여부"""
        return stock_code in self.positions

    def get_equity(self) -> float:
        """현재 자산 조회"""
        return self._calculate_equity({})

    def get_cash(self) -> float:
        """현금 조회"""
        return self.cash

    def monte_carlo_simulation(
        self,
        result: BacktestResult,
        num_simulations: int = 1000,
        num_trades: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Monte Carlo 시뮬레이션

        Args:
            result: 백테스트 결과
            num_simulations: 시뮬레이션 횟수
            num_trades: 거래 수 (None이면 원래 거래 수)

        Returns:
            시뮬레이션 결과
        """
        sell_trades = [t for t in result.trades if t.side == 'sell']

        if not sell_trades:
            return {'error': '시뮬레이션할 거래가 없습니다'}

        returns = [t.pnl_percent for t in sell_trades]

        if num_trades is None:
            num_trades = len(returns)

        logger.info(f"Monte Carlo 시뮬레이션: {num_simulations}회, {num_trades}거래")

        final_equities = []

        for _ in range(num_simulations):
            simulated_returns = np.random.choice(returns, size=num_trades, replace=True)

            equity = self.config.initial_capital
            for ret in simulated_returns:
                equity *= (1 + ret / 100)

            final_equities.append(equity)

        final_returns = [(eq - self.config.initial_capital) / self.config.initial_capital * 100
                        for eq in final_equities]

        return {
            'num_simulations': num_simulations,
            'num_trades': num_trades,
            'mean_final_equity': statistics.mean(final_equities),
            'median_final_equity': statistics.median(final_equities),
            'std_final_equity': statistics.stdev(final_equities) if len(final_equities) > 1 else 0,
            'min_final_equity': min(final_equities),
            'max_final_equity': max(final_equities),
            'mean_return_pct': statistics.mean(final_returns),
            'percentile_5': float(np.percentile(final_returns, 5)),
            'percentile_25': float(np.percentile(final_returns, 25)),
            'percentile_50': float(np.percentile(final_returns, 50)),
            'percentile_75': float(np.percentile(final_returns, 75)),
            'percentile_95': float(np.percentile(final_returns, 95)),
            'probability_of_profit': sum(1 for r in final_returns if r > 0) / len(final_returns) * 100
        }

    def optimize_stop_conditions(
        self,
        stock_code: str,
        daily_data: List[Dict],
        stop_loss_range: List[float] = [3.0, 5.0, 7.0],
        take_profit_range: List[float] = [5.0, 10.0, 15.0]
    ) -> Dict[str, Any]:
        """
        손절/익절 조건 최적화

        Args:
            stock_code: 종목 코드
            daily_data: 일봉 데이터
            stop_loss_range: 테스트할 손절 비율 리스트
            take_profit_range: 테스트할 익절 비율 리스트

        Returns:
            최적화 결과
        """
        results = []

        for stop_loss in stop_loss_range:
            for take_profit in take_profit_range:
                result = self._simulate_stop_conditions(
                    stock_code, daily_data, stop_loss, take_profit
                )
                result['stop_loss_percent'] = stop_loss
                result['take_profit_percent'] = take_profit
                results.append(result)

        best_result = max(results, key=lambda x: x.get('return_rate', -999))

        return {
            'stock_code': stock_code,
            'total_days': len(daily_data),
            'all_results': results,
            'best_result': best_result,
            'recommendation': {
                'stop_loss_percent': best_result['stop_loss_percent'],
                'take_profit_percent': best_result['take_profit_percent'],
                'expected_return': best_result.get('return_rate', 0),
                'expected_win_rate': best_result.get('win_rate', 0)
            }
        }

    def _simulate_stop_conditions(
        self,
        stock_code: str,
        daily_data: List[Dict],
        stop_loss_percent: float,
        take_profit_percent: float
    ) -> Dict[str, Any]:
        """손절/익절 조건 시뮬레이션"""
        initial_capital = 1000000
        capital = initial_capital
        position = None
        trades = []

        for i, day in enumerate(daily_data):
            open_price = day.get('open', day.get('open_price', day.get('stck_oprc', 0)))
            high_price = day.get('high', day.get('high_price', day.get('stck_hgpr', 0)))
            low_price = day.get('low', day.get('low_price', day.get('stck_lwpr', 0)))
            close_price = day.get('close', day.get('close_price', day.get('stck_clpr', 0)))

            if position is None and open_price > 0:
                quantity = int(capital / open_price)
                if quantity > 0:
                    position = {
                        'buy_price': open_price,
                        'quantity': quantity,
                        'stop_loss_price': open_price * (1 - stop_loss_percent / 100),
                        'take_profit_price': open_price * (1 + take_profit_percent / 100)
                    }
                    capital -= quantity * open_price

            elif position is not None:
                sell_price = None
                sell_reason = None

                if low_price <= position['stop_loss_price']:
                    sell_price = position['stop_loss_price']
                    sell_reason = 'stop_loss'
                elif high_price >= position['take_profit_price']:
                    sell_price = position['take_profit_price']
                    sell_reason = 'take_profit'
                elif i == len(daily_data) - 1:
                    sell_price = close_price
                    sell_reason = 'final_close'

                if sell_price:
                    sell_amount = position['quantity'] * sell_price
                    capital += sell_amount

                    profit = sell_amount - (position['quantity'] * position['buy_price'])
                    profit_percent = profit / (position['quantity'] * position['buy_price']) * 100

                    trades.append({
                        'profit': profit,
                        'profit_percent': profit_percent,
                        'reason': sell_reason
                    })

                    position = None

        total_profit = capital - initial_capital
        return_rate = (total_profit / initial_capital) * 100
        win_trades = [t for t in trades if t['profit'] > 0]
        win_rate = (len(win_trades) / len(trades) * 100) if trades else 0

        return {
            'initial_capital': initial_capital,
            'final_capital': capital,
            'total_profit': total_profit,
            'return_rate': return_rate,
            'trade_count': len(trades),
            'win_count': len(win_trades),
            'win_rate': win_rate
        }

    def _get_all_dates(
        self,
        data: Dict[str, pd.DataFrame],
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> List[datetime]:
        """모든 거래일 추출"""
        all_dates = set()

        for df in data.values():
            if 'datetime' in df.columns:
                dates = df['datetime'].dropna().tolist()
            elif 'date' in df.columns:
                dates = pd.to_datetime(df['date'], errors='coerce').dropna().tolist()
            else:
                continue

            for d in dates:
                if isinstance(d, str):
                    d = pd.to_datetime(d)

                if start_date and d < pd.to_datetime(start_date, format='%Y%m%d'):
                    continue
                if end_date and d > pd.to_datetime(end_date, format='%Y%m%d'):
                    continue

                all_dates.add(d)

        return sorted(list(all_dates))

    def _get_data_until(
        self,
        data: Dict[str, pd.DataFrame],
        date: datetime
    ) -> Dict[str, pd.DataFrame]:
        """특정 날짜까지 데이터 추출"""
        result = {}

        for stock_code, df in data.items():
            date_col = 'datetime' if 'datetime' in df.columns else 'date'

            if date_col in df.columns:
                filtered = df[pd.to_datetime(df[date_col]) <= date]
                if len(filtered) > 0:
                    result[stock_code] = filtered

        return result

    def _update_positions(self, data: Dict[str, pd.DataFrame]):
        """포지션 가격 업데이트"""
        for stock_code, pos in self.positions.items():
            if stock_code in data and len(data[stock_code]) > 0:
                last_row = data[stock_code].iloc[-1]
                if 'close' in last_row:
                    pos['current_price'] = float(last_row['close'])

    def _execute_signals(self, signals: List[Dict], data: Dict[str, pd.DataFrame]):
        """신호 실행"""
        if not isinstance(signals, list):
            signals = [signals]

        for signal in signals:
            action = signal.get('action', 'hold')
            stock_code = signal.get('stock_code')
            quantity = signal.get('quantity', 0)

            if not stock_code:
                continue

            price = None
            if stock_code in data and len(data[stock_code]) > 0:
                price = float(data[stock_code].iloc[-1].get('close', 0))

            if action == 'buy' and price:
                self.buy(stock_code, quantity, price, signal.get('reason', ''))
            elif action == 'sell' and price:
                self.sell(stock_code, quantity, price, signal.get('reason', ''))

    def _calculate_equity(self, data: Dict[str, pd.DataFrame]) -> float:
        """현재 자산 계산"""
        position_value = 0

        for stock_code, pos in self.positions.items():
            current_price = pos.get('current_price', 0)

            if stock_code in data and len(data[stock_code]) > 0:
                current_price = float(data[stock_code].iloc[-1].get('close', current_price))
                pos['current_price'] = current_price

            if current_price > 0 and pos['quantity'] > 0:
                position_value += current_price * pos['quantity']

        total_equity = self.cash + position_value

        max_reasonable = self.config.initial_capital * 100
        if total_equity > max_reasonable:
            return max_reasonable

        return max(0, total_equity)

    def _close_all_positions(self, data: Dict[str, pd.DataFrame]):
        """모든 포지션 청산"""
        for stock_code in list(self.positions.keys()):
            pos = self.positions[stock_code]
            price = pos.get('current_price')

            if stock_code in data and len(data[stock_code]) > 0:
                price = float(data[stock_code].iloc[-1].get('close', price))

            if price and price > 0:
                self.sell(stock_code, pos['quantity'], price, 'final_close')

    def _calculate_results(
        self,
        strategy_name: str,
        all_dates: List[datetime]
    ) -> BacktestResult:
        """결과 계산"""
        if not all_dates:
            return self._create_empty_result(strategy_name)

        start_date = all_dates[0].strftime('%Y-%m-%d')
        end_date = all_dates[-1].strftime('%Y-%m-%d')

        final_capital = self.cash
        initial_capital = self.config.initial_capital

        total_return = final_capital - initial_capital
        total_return_pct = (total_return / initial_capital * 100) if initial_capital > 0 else 0

        total_return_pct = max(min(total_return_pct, 1000), -100)

        sell_trades = [t for t in self.trades if t.side == 'sell']
        winning_trades = [t for t in sell_trades if t.pnl > 0]
        losing_trades = [t for t in sell_trades if t.pnl <= 0]

        total_trades = len(sell_trades)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

        avg_win = statistics.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = statistics.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        max_win = max([t.pnl for t in winning_trades]) if winning_trades else 0
        max_loss = min([t.pnl for t in losing_trades]) if losing_trades else 0

        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

        avg_holding = statistics.mean([t.holding_days for t in sell_trades]) if sell_trades else 0
        total_commission = sum(t.commission for t in self.trades)

        sharpe_ratio = self._calculate_sharpe_ratio()
        sortino_ratio = self._calculate_sortino_ratio()
        calmar_ratio = (total_return_pct / self.max_drawdown) if self.max_drawdown > 0 else 0

        drawdown_curve = self._calculate_drawdown_curve()

        return BacktestResult(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=self.peak_equity * (self.max_drawdown / 100),
            max_drawdown_pct=self.max_drawdown,
            calmar_ratio=calmar_ratio,
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_win=max_win,
            max_loss=max_loss,
            profit_factor=profit_factor,
            avg_holding_days=avg_holding,
            total_commission=total_commission,
            trades=self.trades,
            equity_curve=self.equity_curve,
            daily_returns=self.daily_returns,
            drawdown_curve=drawdown_curve
        )

    def _create_empty_result(self, strategy_name: str) -> BacktestResult:
        """빈 결과 생성"""
        return BacktestResult(
            strategy_name=strategy_name,
            start_date="",
            end_date="",
            initial_capital=self.config.initial_capital,
            final_capital=self.config.initial_capital,
            total_return=0,
            total_return_pct=0,
            sharpe_ratio=0,
            sortino_ratio=0,
            max_drawdown=0,
            max_drawdown_pct=0,
            calmar_ratio=0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            avg_win=0,
            avg_loss=0,
            max_win=0,
            max_loss=0,
            profit_factor=0,
            avg_holding_days=0,
            total_commission=0
        )

    def _calculate_sharpe_ratio(self) -> float:
        """Sharpe Ratio 계산"""
        if len(self.daily_returns) < 2:
            return 0

        returns = np.array(self.daily_returns) / 100

        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0

        daily_rf_rate = self.config.risk_free_rate / 252
        sharpe = (avg_return - daily_rf_rate) / std_return * np.sqrt(252)

        return float(sharpe)

    def _calculate_sortino_ratio(self) -> float:
        """Sortino Ratio 계산"""
        if len(self.daily_returns) < 2:
            return 0

        returns = np.array(self.daily_returns) / 100
        avg_return = np.mean(returns)

        downside_returns = returns[returns < 0]

        if len(downside_returns) < 2:
            return 0

        downside_std = np.std(downside_returns)

        if downside_std == 0:
            return 0

        daily_rf_rate = self.config.risk_free_rate / 252
        sortino = (avg_return - daily_rf_rate) / downside_std * np.sqrt(252)

        return float(sortino)

    def _calculate_drawdown_curve(self) -> List[Tuple[datetime, float]]:
        """낙폭 곡선 계산"""
        if not self.equity_curve:
            return []

        drawdown_curve = []
        peak = self.equity_curve[0][1]

        for date, equity in self.equity_curve:
            if equity > peak:
                peak = equity

            dd_percent = ((peak - equity) / peak) * 100 if peak > 0 else 0
            drawdown_curve.append((date, dd_percent))

        return drawdown_curve


def get_backtest_engine(config: Optional[BacktestConfig] = None) -> UnifiedBacktester:
    """싱글톤 백테스터 인스턴스"""
    return UnifiedBacktester(config)


class SimpleStrategy:
    """간단한 전략 베이스 클래스"""

    def __init__(self, name: str, cash: float = 10_000_000):
        self.name = name
        self.initial_cash = cash

    def reset(self):
        pass

    def should_buy(self, stock_data: Dict, market_data: Dict, ai_analysis: Dict) -> bool:
        raise NotImplementedError

    def should_sell(self, stock_code: str, position: Dict, current_price: float) -> bool:
        raise NotImplementedError


class MomentumStrategy(SimpleStrategy):
    """모멘텀 전략"""

    def __init__(self):
        super().__init__("모멘텀 전략")
        self.buy_threshold = 1.0
        self.take_profit = 10.0
        self.stop_loss = 5.0

    def should_buy(self, stock_data: Dict, market_data: Dict, ai_analysis: Dict) -> bool:
        change_rate = stock_data.get('change_rate', 0)
        return change_rate > self.buy_threshold

    def should_sell(self, stock_code: str, position: Dict, current_price: float) -> bool:
        profit_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100
        return profit_pct >= self.take_profit or profit_pct <= -self.stop_loss


class MeanReversionStrategy(SimpleStrategy):
    """평균회귀 전략"""

    def __init__(self):
        super().__init__("평균회귀 전략")
        self.take_profit = 5.0
        self.stop_loss = 7.0

    def should_buy(self, stock_data: Dict, market_data: Dict, ai_analysis: Dict) -> bool:
        change_rate = stock_data.get('change_rate', 0)
        return -3.0 < change_rate < -1.0

    def should_sell(self, stock_code: str, position: Dict, current_price: float) -> bool:
        profit_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100
        return profit_pct >= self.take_profit or profit_pct <= -self.stop_loss


class ConservativeStrategy(SimpleStrategy):
    """보수형 전략"""

    def __init__(self):
        super().__init__("보수형 전략")
        self.take_profit = 7.0
        self.stop_loss = 3.0

    def should_buy(self, stock_data: Dict, market_data: Dict, ai_analysis: Dict) -> bool:
        change_rate = stock_data.get('change_rate', 0)
        return 0 < change_rate < 1.5

    def should_sell(self, stock_code: str, position: Dict, current_price: float) -> bool:
        profit_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100
        return profit_pct >= self.take_profit or profit_pct <= -self.stop_loss


class AggressiveStrategy(SimpleStrategy):
    """공격형 전략"""

    def __init__(self):
        super().__init__("공격형 전략")
        self.take_profit = 20.0
        self.stop_loss = 10.0

    def should_buy(self, stock_data: Dict, market_data: Dict, ai_analysis: Dict) -> bool:
        change_rate = stock_data.get('change_rate', 0)
        return change_rate > 1.5

    def should_sell(self, stock_code: str, position: Dict, current_price: float) -> bool:
        profit_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100
        return profit_pct >= self.take_profit or profit_pct <= -self.stop_loss


BUILTIN_STRATEGIES = {
    'momentum': MomentumStrategy,
    'mean_reversion': MeanReversionStrategy,
    'conservative': ConservativeStrategy,
    'aggressive': AggressiveStrategy,
}


__all__ = [
    'UnifiedBacktester',
    'BacktestConfig',
    'BacktestResult',
    'BacktestTrade',
    'get_backtest_engine',
    'SimpleStrategy',
    'MomentumStrategy',
    'MeanReversionStrategy',
    'ConservativeStrategy',
    'AggressiveStrategy',
    'BUILTIN_STRATEGIES',
]
