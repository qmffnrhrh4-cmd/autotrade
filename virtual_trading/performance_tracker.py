"""
virtual_trading/performance_tracker.py
성과 추적 및 분석 - 강화 버전
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json
from pathlib import Path
import numpy as np


class PerformanceTracker:
    """성과 추적기 - 강화 버전"""

    def __init__(self):
        self.daily_snapshots: List[Dict] = []
        self.start_time = datetime.now()
        self.strategy_records = defaultdict(lambda: {
            'trades': [],
            'equity_curve': [],
            'parameters_history': [],
            'market_conditions': []
        })
        self.initial_capital = 10000000

    def take_snapshot(self, accounts_summary: Dict[str, Dict]):
        """일일 스냅샷"""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'accounts': accounts_summary,
        }
        self.daily_snapshots.append(snapshot)

    def record_trade(self, strategy_name: str, trade_data: Dict):
        self.strategy_records[strategy_name]['trades'].append({
            **trade_data,
            'timestamp': trade_data.get('timestamp', datetime.now().isoformat())
        })

    def record_equity(self, strategy_name: str, equity: float, timestamp: Optional[str] = None):
        self.strategy_records[strategy_name]['equity_curve'].append({
            'equity': equity,
            'timestamp': timestamp or datetime.now().isoformat()
        })

    def record_parameters(self, strategy_name: str, parameters: Dict):
        self.strategy_records[strategy_name]['parameters_history'].append({
            'parameters': parameters.copy(),
            'timestamp': datetime.now().isoformat()
        })

    def record_market_condition(self, strategy_name: str, condition: str, market_data: Dict):
        self.strategy_records[strategy_name]['market_conditions'].append({
            'condition': condition,
            'market_data': market_data.copy(),
            'timestamp': datetime.now().isoformat()
        })

    def calculate_win_rate(self, strategy_name: str) -> float:
        trades = self.strategy_records[strategy_name]['trades']
        if not trades:
            return 0.0

        completed_trades = [t for t in trades if t.get('profit_loss') is not None]
        if not completed_trades:
            return 0.0

        winning_trades = sum(1 for t in completed_trades if t['profit_loss'] > 0)
        return (winning_trades / len(completed_trades)) * 100

    def calculate_average_return(self, strategy_name: str) -> Dict[str, float]:
        trades = self.strategy_records[strategy_name]['trades']
        completed_trades = [t for t in trades if t.get('profit_loss_pct') is not None]

        if not completed_trades:
            return {'avg_return': 0.0, 'avg_win': 0.0, 'avg_loss': 0.0}

        returns = [t['profit_loss_pct'] for t in completed_trades]
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r < 0]

        return {
            'avg_return': np.mean(returns),
            'avg_win': np.mean(wins) if wins else 0.0,
            'avg_loss': np.mean(losses) if losses else 0.0
        }

    def calculate_sharpe_ratio(self, strategy_name: str, risk_free_rate: float = 0.02) -> float:
        trades = self.strategy_records[strategy_name]['trades']
        completed_trades = [t for t in trades if t.get('profit_loss_pct') is not None]

        if len(completed_trades) < 2:
            return 0.0

        returns = np.array([t['profit_loss_pct'] / 100 for t in completed_trades])
        excess_returns = returns - (risk_free_rate / 252)

        if np.std(excess_returns) == 0:
            return 0.0

        sharpe = np.mean(excess_returns) / np.std(excess_returns)
        return sharpe * np.sqrt(252)

    def calculate_max_drawdown(self, strategy_name: str) -> Dict[str, float]:
        equity_curve = self.strategy_records[strategy_name]['equity_curve']

        if len(equity_curve) < 2:
            return {'max_drawdown': 0.0, 'max_drawdown_pct': 0.0}

        equities = [e['equity'] for e in equity_curve]
        peak = equities[0]
        max_dd = 0.0
        max_dd_pct = 0.0

        for equity in equities:
            if equity > peak:
                peak = equity
            dd = peak - equity
            dd_pct = (dd / peak) * 100 if peak > 0 else 0

            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct

        return {
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct
        }

    def analyze_by_market_condition(self, strategy_name: str) -> Dict[str, Dict]:
        trades = self.strategy_records[strategy_name]['trades']

        condition_stats = defaultdict(lambda: {
            'trades': [],
            'wins': 0,
            'losses': 0,
            'total_pnl': 0
        })

        for trade in trades:
            if trade.get('profit_loss') is None:
                continue

            condition = trade.get('market_condition', 'unknown')
            condition_stats[condition]['trades'].append(trade)

            if trade['profit_loss'] > 0:
                condition_stats[condition]['wins'] += 1
            else:
                condition_stats[condition]['losses'] += 1

            condition_stats[condition]['total_pnl'] += trade['profit_loss']

        result = {}
        for condition, stats in condition_stats.items():
            total = stats['wins'] + stats['losses']
            result[condition] = {
                'total_trades': total,
                'win_rate': (stats['wins'] / total * 100) if total > 0 else 0,
                'total_pnl': stats['total_pnl'],
                'avg_pnl': stats['total_pnl'] / total if total > 0 else 0
            }

        return result

    def analyze_by_time_period(self, strategy_name: str) -> Dict[str, Dict]:
        trades = self.strategy_records[strategy_name]['trades']

        time_stats = {
            'early': {'trades': [], 'wins': 0, 'losses': 0, 'total_pnl': 0},
            'mid': {'trades': [], 'wins': 0, 'losses': 0, 'total_pnl': 0},
            'late': {'trades': [], 'wins': 0, 'losses': 0, 'total_pnl': 0}
        }

        for trade in trades:
            if trade.get('profit_loss') is None:
                continue

            timestamp_str = trade.get('timestamp')
            if not timestamp_str:
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                hour = timestamp.hour

                if 9 <= hour < 11:
                    period = 'early'
                elif 11 <= hour < 14:
                    period = 'mid'
                elif 14 <= hour < 16:
                    period = 'late'
                else:
                    continue

                time_stats[period]['trades'].append(trade)

                if trade['profit_loss'] > 0:
                    time_stats[period]['wins'] += 1
                else:
                    time_stats[period]['losses'] += 1

                time_stats[period]['total_pnl'] += trade['profit_loss']
            except:
                continue

        result = {}
        for period, stats in time_stats.items():
            total = stats['wins'] + stats['losses']
            result[period] = {
                'total_trades': total,
                'win_rate': (stats['wins'] / total * 100) if total > 0 else 0,
                'total_pnl': stats['total_pnl'],
                'avg_pnl': stats['total_pnl'] / total if total > 0 else 0
            }

        return result

    def get_optimal_parameters(self, strategy_name: str) -> Dict:
        params_history = self.strategy_records[strategy_name]['parameters_history']
        trades = self.strategy_records[strategy_name]['trades']

        if not params_history or not trades:
            return {}

        param_performance = defaultdict(lambda: {'pnl': 0, 'trades': 0, 'wins': 0})

        for trade in trades:
            if trade.get('profit_loss') is None:
                continue

            trade_time = datetime.fromisoformat(trade['timestamp'])

            relevant_params = None
            for param_record in reversed(params_history):
                param_time = datetime.fromisoformat(param_record['timestamp'])
                if param_time <= trade_time:
                    relevant_params = param_record['parameters']
                    break

            if relevant_params:
                param_key = json.dumps(relevant_params, sort_keys=True)
                param_performance[param_key]['pnl'] += trade['profit_loss']
                param_performance[param_key]['trades'] += 1
                if trade['profit_loss'] > 0:
                    param_performance[param_key]['wins'] += 1

        if not param_performance:
            return {}

        best_params_key = max(param_performance.keys(),
                             key=lambda k: param_performance[k]['pnl'])

        best_params = json.loads(best_params_key)
        best_stats = param_performance[best_params_key]

        return {
            'parameters': best_params,
            'total_pnl': best_stats['pnl'],
            'total_trades': best_stats['trades'],
            'win_rate': (best_stats['wins'] / best_stats['trades'] * 100) if best_stats['trades'] > 0 else 0
        }

    def get_strategy_performance_summary(self, strategy_name: str) -> Dict:
        if strategy_name not in self.strategy_records:
            return {}

        trades = self.strategy_records[strategy_name]['trades']
        completed_trades = [t for t in trades if t.get('profit_loss') is not None]

        if not completed_trades:
            return {
                'strategy_name': strategy_name,
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown_pct': 0.0,
                'total_pnl': 0.0
            }

        avg_returns = self.calculate_average_return(strategy_name)
        mdd = self.calculate_max_drawdown(strategy_name)

        total_pnl = sum(t['profit_loss'] for t in completed_trades)

        return {
            'strategy_name': strategy_name,
            'total_trades': len(completed_trades),
            'win_rate': self.calculate_win_rate(strategy_name),
            'avg_return': avg_returns['avg_return'],
            'avg_win': avg_returns['avg_win'],
            'avg_loss': avg_returns['avg_loss'],
            'sharpe_ratio': self.calculate_sharpe_ratio(strategy_name),
            'max_drawdown_pct': mdd['max_drawdown_pct'],
            'total_pnl': total_pnl,
            'market_condition_analysis': self.analyze_by_market_condition(strategy_name),
            'time_period_analysis': self.analyze_by_time_period(strategy_name)
        }

    def get_all_strategies_summary(self) -> List[Dict]:
        summaries = []
        for strategy_name in self.strategy_records.keys():
            summary = self.get_strategy_performance_summary(strategy_name)
            if summary:
                summaries.append(summary)

        return sorted(summaries, key=lambda x: x.get('total_pnl', 0), reverse=True)

    def get_performance_metrics(self, strategy_name: str) -> Dict:
        if not self.daily_snapshots:
            return {}

        snapshots = [
            s['accounts'].get(strategy_name)
            for s in self.daily_snapshots
            if strategy_name in s['accounts']
        ]

        if not snapshots:
            return {}

        pnl_rates = [s['total_pnl_rate'] for s in snapshots]

        max_drawdown = self._calculate_max_drawdown(pnl_rates)
        sharpe_ratio = self._calculate_sharpe(pnl_rates)

        return {
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'volatility': self._calculate_volatility(pnl_rates),
            'best_day': max(pnl_rates) if pnl_rates else 0,
            'worst_day': min(pnl_rates) if pnl_rates else 0,
        }

    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        if not returns:
            return 0.0

        peak = returns[0]
        max_dd = 0.0

        for r in returns:
            if r > peak:
                peak = r
            dd = peak - r
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def _calculate_sharpe(self, returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        return mean_return / std_return

    def _calculate_volatility(self, returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0

        return np.std(returns)

    def save(self, filepath: str = "data/virtual_trading/performance.json"):
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        data = {
            'start_time': self.start_time.isoformat(),
            'snapshots': self.daily_snapshots[-30:],
            'strategy_records': dict(self.strategy_records)
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


__all__ = ['PerformanceTracker']
