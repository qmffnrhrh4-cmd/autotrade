"""
virtual_trading/trade_logger.py
거래 로그 및 분석 - SQLite 기반
"""
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)


class TradeLogger:
    """거래 로거 - 모든 가상 거래 기록 및 분석 (SQLite 기반)"""

    def __init__(self, db_path: str = "data/virtual_trading/trades.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.trades: List[Dict] = []
        self._initialize_database()

    def _initialize_database(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                action TEXT NOT NULL,
                stock_code TEXT NOT NULL,
                stock_name TEXT,
                price INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                realized_pnl INTEGER,
                pnl_rate REAL,
                reason TEXT,
                technical_indicators TEXT,
                market_condition TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                total_pnl INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_profit INTEGER DEFAULT 0,
                avg_loss INTEGER DEFAULT 0,
                sharpe_ratio REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                parameters TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                market_condition TEXT,
                fear_greed_index INTEGER,
                rsi REAL,
                macd REAL,
                volume_ratio REAL,
                price_change REAL,
                additional_data TEXT
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_strategy ON strategy_performance(strategy)')

        conn.commit()
        conn.close()

    def log_trade(self, trade_data: Dict):
        """거래 로그 기록"""
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            **trade_data
        }
        self.trades.append(trade_record)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        technical_indicators = json.dumps(trade_data.get('technical_indicators', {}))

        cursor.execute('''
            INSERT INTO trades (
                strategy, action, stock_code, stock_name, price, quantity,
                amount, timestamp, realized_pnl, pnl_rate, reason,
                technical_indicators, market_condition
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data.get('strategy', ''),
            trade_data.get('type', 'UNKNOWN'),
            trade_data.get('stock_code', ''),
            trade_data.get('stock_name', ''),
            trade_data.get('price', 0),
            trade_data.get('quantity', 0),
            trade_data.get('amount', 0),
            trade_record['timestamp'],
            trade_data.get('realized_pnl'),
            trade_data.get('pnl_rate'),
            trade_data.get('reason', ''),
            technical_indicators,
            trade_data.get('market_condition', '')
        ))

        conn.commit()
        conn.close()

    def log_buy(self, strategy: str, stock_code: str, stock_name: str,
                price: int, quantity: int, reason: str = ""):
        """매수 로그"""
        self.log_trade({
            'type': 'BUY',
            'strategy': strategy,
            'stock_code': stock_code,
            'stock_name': stock_name,
            'price': price,
            'quantity': quantity,
            'amount': price * quantity,
            'reason': reason,
        })

    def log_sell(self, strategy: str, stock_code: str, stock_name: str,
                 price: int, quantity: int, realized_pnl: int,
                 pnl_rate: float, reason: str = ""):
        """매도 로그"""
        self.log_trade({
            'type': 'SELL',
            'strategy': strategy,
            'stock_code': stock_code,
            'stock_name': stock_name,
            'price': price,
            'quantity': quantity,
            'amount': price * quantity,
            'realized_pnl': realized_pnl,
            'pnl_rate': pnl_rate,
            'reason': reason,
        })

    def log_strategy_performance(self, performance_data: Dict):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        parameters = json.dumps(performance_data.get('parameters', {}))

        cursor.execute('''
            INSERT INTO strategy_performance (
                strategy, timestamp, total_trades, winning_trades,
                losing_trades, total_pnl, win_rate, avg_profit,
                avg_loss, sharpe_ratio, max_drawdown, parameters
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            performance_data.get('strategy'),
            performance_data.get('timestamp', datetime.now().isoformat()),
            performance_data.get('total_trades', 0),
            performance_data.get('winning_trades', 0),
            performance_data.get('losing_trades', 0),
            performance_data.get('total_pnl', 0),
            performance_data.get('win_rate', 0),
            performance_data.get('avg_profit', 0),
            performance_data.get('avg_loss', 0),
            performance_data.get('sharpe_ratio', 0),
            performance_data.get('max_drawdown', 0),
            parameters
        ))

        conn.commit()
        conn.close()

    def log_market_snapshot(self, market_data: Dict):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        additional_data = json.dumps(market_data.get('additional', {}))

        cursor.execute('''
            INSERT INTO market_snapshots (
                timestamp, market_condition, fear_greed_index,
                rsi, macd, volume_ratio, price_change, additional_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            market_data.get('timestamp', datetime.now().isoformat()),
            market_data.get('market_condition', 'unknown'),
            market_data.get('fear_greed_index'),
            market_data.get('rsi'),
            market_data.get('macd'),
            market_data.get('volume_ratio'),
            market_data.get('price_change'),
            additional_data
        ))

        conn.commit()
        conn.close()

    def get_trade_analysis(self, strategy: Optional[str] = None) -> Dict:
        """거래 분석 (SQLite 기반)"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        if strategy:
            cursor.execute('''
                SELECT action, realized_pnl, pnl_rate, stock_name, stock_code
                FROM trades
                WHERE strategy = ?
            ''', (strategy,))
        else:
            cursor.execute('SELECT action, realized_pnl, pnl_rate, stock_name, stock_code FROM trades')

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {}

        buy_count = sum(1 for r in rows if r[0] == 'BUY')
        sell_trades = [r for r in rows if r[0] == 'SELL' and r[1] is not None]

        if not sell_trades:
            return {
                'total_trades': 0,
                'total_buys': buy_count,
                'total_sells': 0,
                'win_trades': 0,
                'lose_trades': 0,
            }

        win_trades = [t for t in sell_trades if t[1] > 0]
        lose_trades = [t for t in sell_trades if t[1] <= 0]

        total_profit = sum(t[1] for t in win_trades)
        total_loss = sum(t[1] for t in lose_trades)

        avg_profit = total_profit / len(win_trades) if win_trades else 0
        avg_loss = total_loss / len(lose_trades) if lose_trades else 0

        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else 0

        best_trade = max(sell_trades, key=lambda x: x[1]) if sell_trades else None
        worst_trade = min(sell_trades, key=lambda x: x[1]) if sell_trades else None

        return {
            'total_trades': len(sell_trades),
            'total_buys': buy_count,
            'total_sells': len(sell_trades),
            'win_trades': len(win_trades),
            'lose_trades': len(lose_trades),
            'win_rate': len(win_trades) / len(sell_trades) if sell_trades else 0,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'best_trade': {
                'stock': f"{best_trade[3]}({best_trade[4]})",
                'pnl': best_trade[1],
                'pnl_rate': best_trade[2],
            } if best_trade else None,
            'worst_trade': {
                'stock': f"{worst_trade[3]}({worst_trade[4]})",
                'pnl': worst_trade[1],
                'pnl_rate': worst_trade[2],
            } if worst_trade else None,
        }

    def get_strategy_comparison(self) -> Dict[str, Dict]:
        """전략별 비교"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('SELECT DISTINCT strategy FROM trades WHERE strategy IS NOT NULL')
        strategies = [row[0] for row in cursor.fetchall()]
        conn.close()

        return {
            strategy: self.get_trade_analysis(strategy)
            for strategy in strategies
        }

    def get_stock_analysis(self, stock_code: str) -> Dict:
        """종목별 거래 분석"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT action, stock_name, amount, realized_pnl, strategy
            FROM trades
            WHERE stock_code = ?
        ''', (stock_code,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {}

        buy_trades = [r for r in rows if r[0] == 'BUY']
        sell_trades = [r for r in rows if r[0] == 'SELL']

        total_buy_amount = sum(r[2] for r in buy_trades)
        total_sell_amount = sum(r[2] for r in sell_trades)
        total_realized_pnl = sum(r[3] for r in sell_trades if r[3] is not None)

        return {
            'stock_code': stock_code,
            'stock_name': rows[0][1] if rows else '',
            'total_buys': len(buy_trades),
            'total_sells': len(sell_trades),
            'total_buy_amount': total_buy_amount,
            'total_sell_amount': total_sell_amount,
            'total_realized_pnl': total_realized_pnl,
            'strategies': list(set(r[4] for r in rows if r[4])),
        }

    def get_recent_trades(self, limit: int = 10, strategy: Optional[str] = None) -> List[Dict]:
        """최근 거래 내역"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if strategy:
            cursor.execute('''
                SELECT * FROM trades
                WHERE strategy = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (strategy, limit))
        else:
            cursor.execute('''
                SELECT * FROM trades
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_all_strategies_stats(self) -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('SELECT DISTINCT strategy FROM trades WHERE strategy IS NOT NULL')
        strategies = [row[0] for row in cursor.fetchall()]
        conn.close()

        stats = []
        for strategy in strategies:
            analysis = self.get_trade_analysis(strategy)
            if analysis:
                stats.append({
                    'strategy': strategy,
                    **analysis
                })

        return sorted(stats, key=lambda x: x.get('total_profit', 0), reverse=True)

    def print_summary(self):
        """거래 요약 출력"""
        analysis = self.get_trade_analysis()

        if not analysis:
            print("📊 거래 내역 없음")
            return

        print("\n" + "="*60)
        print("📊 가상 거래 로그 요약")
        print("="*60)

        print(f"\n총 거래: {analysis['total_buys']}회 매수, {analysis['total_sells']}회 매도")

        if analysis['total_sells'] > 0:
            print(f"승률: {analysis['win_rate']:.1%} ({analysis['win_trades']}승 {analysis['lose_trades']}패)")
            print(f"총 수익: {analysis['total_profit']:+,}원")
            print(f"총 손실: {analysis['total_loss']:+,}원")
            print(f"평균 수익: {analysis['avg_profit']:+,.0f}원")
            print(f"평균 손실: {analysis['avg_loss']:+,.0f}원")
            print(f"Profit Factor: {analysis['profit_factor']:.2f}")

            if analysis['best_trade']:
                print(f"\n최고 거래: {analysis['best_trade']['stock']} "
                      f"{analysis['best_trade']['pnl']:+,}원 ({analysis['best_trade']['pnl_rate']:+.1%})")

            if analysis['worst_trade']:
                print(f"최악 거래: {analysis['worst_trade']['stock']} "
                      f"{analysis['worst_trade']['pnl']:+,}원 ({analysis['worst_trade']['pnl_rate']:+.1%})")

        print("="*60)

    def get_trades_by_date_range(self, start_date: str, end_date: str, strategy: Optional[str] = None) -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if strategy:
            cursor.execute('''
                SELECT * FROM trades
                WHERE timestamp BETWEEN ? AND ? AND strategy = ?
                ORDER BY timestamp DESC
            ''', (start_date, end_date, strategy))
        else:
            cursor.execute('''
                SELECT * FROM trades
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
            ''', (start_date, end_date))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def clear_old_data(self, days: int = 30):
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('DELETE FROM trades WHERE timestamp < ?', (cutoff_str,))
        cursor.execute('DELETE FROM market_snapshots WHERE timestamp < ?', (cutoff_str,))

        conn.commit()
        conn.close()

    def load_historical_trades(self, days: int = 7) -> int:
        """
        과거 거래 기록 로드 (내부 캐시 업데이트)

        Args:
            days: 로드할 기간 (일)

        Returns:
            로드된 거래 수
        """
        from datetime import timedelta

        try:
            start_date = datetime.now() - timedelta(days=days)
            end_date = datetime.now()

            start_str = start_date.isoformat()
            end_str = end_date.isoformat()

            # DB에서 과거 거래 로드
            trades = self.get_trades_by_date_range(start_str, end_str)

            # 내부 캐시 업데이트
            self.trades = trades

            return len(trades)

        except Exception as e:
            logger.warning(f"과거 거래 기록 로드 실패: {e}")
            return 0


__all__ = ['TradeLogger']
