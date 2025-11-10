from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from itertools import product


class HistoricalOptimizer:
    def __init__(self, strategy_class, initial_capital: float = 10000000):
        self.strategy_class = strategy_class
        self.initial_capital = initial_capital
        self.results = []

    def fetch_historical_data(self, stock_code: str, days: int = 365) -> List[Dict]:
        candles = []
        for i in range(days):
            candles.append({
                'timestamp': datetime.now() - timedelta(days=days - i),
                'open': 10000 + np.random.randn() * 100,
                'high': 10100 + np.random.randn() * 100,
                'low': 9900 + np.random.randn() * 100,
                'close': 10000 + np.random.randn() * 100,
                'volume': 1000000 + np.random.randn() * 100000,
            })
        return candles

    def calculate_indicators(self, candles: List[Dict]) -> List[Dict]:
        enriched_data = []

        for i, candle in enumerate(candles):
            market_data = candle.copy()

            if i >= 20:
                prices = [c['close'] for c in candles[i-20:i+1]]
                market_data['ma20'] = np.mean(prices)
                market_data['std_20'] = np.std(prices)
            else:
                market_data['ma20'] = candle['close']
                market_data['std_20'] = 0

            if i >= 5:
                prices_5 = [c['close'] for c in candles[i-5:i+1]]
                market_data['ma5'] = np.mean(prices_5)
            else:
                market_data['ma5'] = candle['close']

            if i >= 14:
                gains = []
                losses = []
                for j in range(i-14, i):
                    change = candles[j+1]['close'] - candles[j]['close']
                    if change > 0:
                        gains.append(change)
                    else:
                        losses.append(abs(change))

                avg_gain = np.mean(gains) if gains else 0
                avg_loss = np.mean(losses) if losses else 1

                rs = avg_gain / avg_loss if avg_loss != 0 else 0
                market_data['rsi'] = 100 - (100 / (1 + rs))
            else:
                market_data['rsi'] = 50

            if i >= 1:
                market_data['price_change_percent'] = ((candle['close'] - candles[i-1]['close']) / candles[i-1]['close']) * 100
            else:
                market_data['price_change_percent'] = 0

            if i >= 20:
                volumes = [c['volume'] for c in candles[i-20:i+1]]
                avg_vol = np.mean(volumes[:-1]) if len(volumes) > 1 else 1
                market_data['volume_ratio'] = candle['volume'] / avg_vol if avg_vol > 0 else 1
            else:
                market_data['volume_ratio'] = 1.0

            market_data['current_price'] = candle['close']

            enriched_data.append(market_data)

        return enriched_data

    def backtest_strategy(self, strategy, market_data_list: List[Dict], params: Dict) -> Dict:
        strategy.update_params(params)

        capital = self.initial_capital
        position = None
        trades = []

        for i, market_data in enumerate(market_data_list):
            current_price = market_data['current_price']

            if position is None:
                signal = strategy.analyze(market_data)

                if signal == 'buy':
                    position = {
                        'entry_price': current_price,
                        'entry_time': market_data['timestamp'],
                        'quantity': 1
                    }
            else:
                days_held = i - market_data_list.index(next(
                    (m for m in market_data_list if m['timestamp'] == position['entry_time']),
                    market_data_list[0]
                ))

                pnl_rate = ((current_price - position['entry_price']) / position['entry_price']) * 100

                should_sell = False
                reason = ""

                if pnl_rate >= 10:
                    should_sell = True
                    reason = "익절"
                elif pnl_rate <= -5:
                    should_sell = True
                    reason = "손절"
                elif days_held >= 10:
                    should_sell = True
                    reason = "기간만료"

                if should_sell:
                    pnl = (current_price - position['entry_price']) * position['quantity']
                    capital += pnl

                    trades.append({
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'pnl': pnl,
                        'pnl_rate': pnl_rate,
                        'days_held': days_held,
                        'reason': reason
                    })

                    position = None

        total_pnl = sum(t['pnl'] for t in trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]

        return {
            'params': params,
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trades) * 100 if trades else 0,
            'total_pnl': total_pnl,
            'final_capital': self.initial_capital + total_pnl,
            'return_rate': (total_pnl / self.initial_capital) * 100,
            'avg_pnl': total_pnl / len(trades) if trades else 0,
            'trades': trades
        }

    def grid_search(self, market_data_list: List[Dict], param_grid: Dict[str, List]) -> List[Dict]:
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        results = []

        for param_combination in product(*param_values):
            params = dict(zip(param_names, param_combination))

            strategy = self.strategy_class(params)

            result = self.backtest_strategy(strategy, market_data_list, params)
            results.append(result)

        return sorted(results, key=lambda x: x['return_rate'], reverse=True)

    def optimize_strategy(self, stock_code: str, param_grid: Dict[str, List], days: int = 365) -> Dict:
        historical_data = self.fetch_historical_data(stock_code, days)

        market_data_list = self.calculate_indicators(historical_data)

        results = self.grid_search(market_data_list, param_grid)

        best_result = results[0] if results else None

        return {
            'stock_code': stock_code,
            'optimization_period': days,
            'total_combinations': len(results),
            'best_params': best_result['params'] if best_result else {},
            'best_performance': {
                'return_rate': best_result['return_rate'],
                'win_rate': best_result['win_rate'],
                'total_trades': best_result['total_trades'],
                'total_pnl': best_result['total_pnl']
            } if best_result else {},
            'all_results': results[:10]
        }

    def walk_forward_analysis(self, market_data_list: List[Dict], param_grid: Dict[str, List],
                             train_size: int = 180, test_size: int = 60) -> Dict:
        results = []
        total_data = len(market_data_list)

        for start in range(0, total_data - train_size - test_size, test_size):
            train_data = market_data_list[start:start + train_size]
            test_data = market_data_list[start + train_size:start + train_size + test_size]

            train_results = self.grid_search(train_data, param_grid)
            best_params = train_results[0]['params'] if train_results else {}

            strategy = self.strategy_class(best_params)
            test_result = self.backtest_strategy(strategy, test_data, best_params)

            results.append({
                'train_period': (train_data[0]['timestamp'], train_data[-1]['timestamp']),
                'test_period': (test_data[0]['timestamp'], test_data[-1]['timestamp']),
                'best_params': best_params,
                'test_performance': test_result
            })

        avg_return = np.mean([r['test_performance']['return_rate'] for r in results])
        avg_win_rate = np.mean([r['test_performance']['win_rate'] for r in results])

        return {
            'num_periods': len(results),
            'avg_return_rate': avg_return,
            'avg_win_rate': avg_win_rate,
            'results': results
        }

    def monte_carlo_simulation(self, trades: List[Dict], num_simulations: int = 1000) -> Dict:
        if not trades:
            return {}

        pnls = [t['pnl'] for t in trades]

        simulated_returns = []

        for _ in range(num_simulations):
            sampled_trades = np.random.choice(pnls, size=len(pnls), replace=True)
            total_return = sum(sampled_trades)
            simulated_returns.append(total_return)

        return {
            'mean_return': np.mean(simulated_returns),
            'std_return': np.std(simulated_returns),
            'percentile_5': np.percentile(simulated_returns, 5),
            'percentile_95': np.percentile(simulated_returns, 95),
            'var_95': np.percentile(simulated_returns, 5),
            'cvar_95': np.mean([r for r in simulated_returns if r <= np.percentile(simulated_returns, 5)])
        }


__all__ = ['HistoricalOptimizer']
