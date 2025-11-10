"""
virtual_trading/models.py
가상매매 데이터 모델

SQLite 데이터베이스를 사용하여 가상매매 전략, 포지션, 거래 내역을 관리
"""
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class VirtualTradingDB:
    """가상매매 데이터베이스 관리 클래스"""

    def __init__(self, db_path: str = "data/virtual_trading.db"):
        """
        데이터베이스 초기화

        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path

        # data 디렉토리가 없으면 생성
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = None
        self._initialize_db()

    def _initialize_db(self):
        """데이터베이스 초기화 및 테이블 생성"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # 1. 가상매매 전략 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS virtual_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                initial_capital REAL NOT NULL DEFAULT 10000000,
                current_capital REAL NOT NULL DEFAULT 10000000,
                total_profit REAL DEFAULT 0,
                return_rate REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                trade_count INTEGER DEFAULT 0,
                win_count INTEGER DEFAULT 0,
                loss_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. 가상매매 포지션 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS virtual_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                stock_code TEXT NOT NULL,
                stock_name TEXT,
                quantity INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                current_price REAL NOT NULL,
                buy_date TEXT NOT NULL,
                stop_loss_price REAL,
                take_profit_price REAL,
                is_closed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_id) REFERENCES virtual_strategies(id)
            )
        """)

        # 3. 가상매매 거래 내역 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS virtual_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                stock_code TEXT NOT NULL,
                stock_name TEXT,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total_amount REAL NOT NULL,
                profit REAL DEFAULT 0,
                profit_percent REAL DEFAULT 0,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_id) REFERENCES virtual_strategies(id)
            )
        """)

        # 인덱스 생성
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_strategy
            ON virtual_positions(strategy_id, is_closed)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_strategy
            ON virtual_trades(strategy_id, timestamp DESC)
        """)

        self.conn.commit()
        logger.info("가상매매 데이터베이스 초기화 완료")

    def create_strategy(
        self,
        name: str,
        description: str = "",
        initial_capital: float = 10000000
    ) -> int:
        """
        가상매매 전략 생성

        Args:
            name: 전략 이름
            description: 전략 설명
            initial_capital: 초기 자본

        Returns:
            생성된 전략 ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO virtual_strategies (name, description, initial_capital, current_capital)
            VALUES (?, ?, ?, ?)
        """, (name, description, initial_capital, initial_capital))
        self.conn.commit()

        strategy_id = cursor.lastrowid
        logger.info(f"가상매매 전략 생성: {name} (ID: {strategy_id})")
        return strategy_id

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """모든 가상매매 전략 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM virtual_strategies
            WHERE is_active = 1
            ORDER BY created_at DESC
        """)

        strategies = []
        for row in cursor.fetchall():
            # 활성 포지션 수 계산
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM virtual_positions
                WHERE strategy_id = ? AND is_closed = 0
            """, (row['id'],))
            position_count = cursor.fetchone()['cnt']

            strategies.append({
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'initial_capital': row['initial_capital'],
                'current_capital': row['current_capital'],
                'total_assets': row['current_capital'],  # TODO: + 주식 평가금액
                'total_profit': row['total_profit'],
                'return_rate': row['return_rate'],
                'win_rate': row['win_rate'],
                'trade_count': row['trade_count'],
                'win_count': row['win_count'],
                'loss_count': row['loss_count'],
                'position_count': position_count,
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })

        return strategies

    def open_position(
        self,
        strategy_id: int,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: float,
        stop_loss_price: float = None,
        take_profit_price: float = None
    ) -> int:
        """
        가상매매 포지션 열기 (매수)

        Args:
            strategy_id: 전략 ID
            stock_code: 종목코드
            stock_name: 종목명
            quantity: 수량
            price: 매수가
            stop_loss_price: 손절가
            take_profit_price: 익절가

        Returns:
            생성된 포지션 ID
        """
        cursor = self.conn.cursor()

        # 포지션 생성
        buy_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO virtual_positions
            (strategy_id, stock_code, stock_name, quantity, avg_price, current_price,
             buy_date, stop_loss_price, take_profit_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (strategy_id, stock_code, stock_name, quantity, price, price,
              buy_date, stop_loss_price, take_profit_price))

        position_id = cursor.lastrowid

        # 거래 내역 기록
        total_amount = quantity * price
        cursor.execute("""
            INSERT INTO virtual_trades
            (strategy_id, stock_code, stock_name, side, quantity, price, total_amount, timestamp)
            VALUES (?, ?, ?, 'buy', ?, ?, ?, ?)
        """, (strategy_id, stock_code, stock_name, quantity, price, total_amount, buy_date))

        # 전략 현금 차감
        cursor.execute("""
            UPDATE virtual_strategies
            SET current_capital = current_capital - ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (total_amount, strategy_id))

        self.conn.commit()

        logger.info(f"가상매매 포지션 열기: {stock_name} {quantity}주 @ {price:,}원")
        return position_id

    def close_position(
        self,
        position_id: int,
        sell_price: float,
        current_time: str = None
    ) -> float:
        """
        가상매매 포지션 닫기 (매도)

        Args:
            position_id: 포지션 ID
            sell_price: 매도가
            current_time: 매도 시간 (None이면 현재 시간)

        Returns:
            실현 수익
        """
        if not current_time:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor = self.conn.cursor()

        # 포지션 정보 조회
        cursor.execute("""
            SELECT * FROM virtual_positions WHERE id = ?
        """, (position_id,))
        position = cursor.execute("""
            SELECT * FROM virtual_positions WHERE id = ?
        """, (position_id,)).fetchone()

        if not position:
            logger.error(f"포지션을 찾을 수 없음: {position_id}")
            return 0

        # 수익 계산
        buy_amount = position['quantity'] * position['avg_price']
        sell_amount = position['quantity'] * sell_price
        profit = sell_amount - buy_amount
        profit_percent = (profit / buy_amount) * 100 if buy_amount > 0 else 0

        # 포지션 닫기
        cursor.execute("""
            UPDATE virtual_positions
            SET is_closed = 1,
                current_price = ?,
                updated_at = ?
            WHERE id = ?
        """, (sell_price, current_time, position_id))

        # 거래 내역 기록
        cursor.execute("""
            INSERT INTO virtual_trades
            (strategy_id, stock_code, stock_name, side, quantity, price, total_amount,
             profit, profit_percent, timestamp)
            VALUES (?, ?, ?, 'sell', ?, ?, ?, ?, ?, ?)
        """, (position['strategy_id'], position['stock_code'], position['stock_name'],
              position['quantity'], sell_price, sell_amount, profit, profit_percent, current_time))

        # 전략 업데이트
        cursor.execute("""
            UPDATE virtual_strategies
            SET current_capital = current_capital + ?,
                total_profit = total_profit + ?,
                trade_count = trade_count + 1,
                win_count = win_count + ?,
                loss_count = loss_count + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (sell_amount, profit, 1 if profit > 0 else 0, 1 if profit < 0 else 0, position['strategy_id']))

        # 승률 및 수익률 업데이트
        cursor.execute("""
            UPDATE virtual_strategies
            SET win_rate = CAST(win_count AS REAL) / trade_count * 100,
                return_rate = (current_capital - initial_capital) / initial_capital * 100
            WHERE id = ?
        """, (position['strategy_id'],))

        self.conn.commit()

        logger.info(f"가상매매 포지션 닫기: {position['stock_name']} 수익: {profit:+,.0f}원 ({profit_percent:+.2f}%)")
        return profit

    def get_open_positions(self, strategy_id: int = None) -> List[Dict[str, Any]]:
        """
        활성 포지션 조회

        Args:
            strategy_id: 전략 ID (None이면 모든 전략)

        Returns:
            활성 포지션 리스트
        """
        cursor = self.conn.cursor()

        if strategy_id:
            cursor.execute("""
                SELECT p.*, s.name as strategy_name
                FROM virtual_positions p
                JOIN virtual_strategies s ON p.strategy_id = s.id
                WHERE p.strategy_id = ? AND p.is_closed = 0
                ORDER BY p.buy_date DESC
            """, (strategy_id,))
        else:
            cursor.execute("""
                SELECT p.*, s.name as strategy_name
                FROM virtual_positions p
                JOIN virtual_strategies s ON p.strategy_id = s.id
                WHERE p.is_closed = 0
                ORDER BY p.buy_date DESC
            """)

        positions = []
        for row in cursor.fetchall():
            value = row['quantity'] * row['current_price']
            profit_loss = value - (row['quantity'] * row['avg_price'])
            profit_percent = (profit_loss / (row['quantity'] * row['avg_price'])) * 100 if row['avg_price'] > 0 else 0

            positions.append({
                'id': row['id'],
                'strategy_id': row['strategy_id'],
                'strategy_name': row['strategy_name'],
                'stock_code': row['stock_code'],
                'stock_name': row['stock_name'],
                'quantity': row['quantity'],
                'avg_price': row['avg_price'],
                'current_price': row['current_price'],
                'value': value,
                'profit': profit_loss,
                'profit_percent': profit_percent,
                'buy_date': row['buy_date'],
                'stop_loss_price': row['stop_loss_price'],
                'take_profit_price': row['take_profit_price']
            })

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
        cursor = self.conn.cursor()

        if strategy_id:
            cursor.execute("""
                SELECT t.*, s.name as strategy_name
                FROM virtual_trades t
                JOIN virtual_strategies s ON t.strategy_id = s.id
                WHERE t.strategy_id = ?
                ORDER BY t.timestamp DESC
                LIMIT ?
            """, (strategy_id, limit))
        else:
            cursor.execute("""
                SELECT t.*, s.name as strategy_name
                FROM virtual_trades t
                JOIN virtual_strategies s ON t.strategy_id = s.id
                ORDER BY t.timestamp DESC
                LIMIT ?
            """, (limit,))

        trades = []
        for row in cursor.fetchall():
            trades.append({
                'id': row['id'],
                'strategy_id': row['strategy_id'],
                'strategy_name': row['strategy_name'],
                'stock_code': row['stock_code'],
                'stock_name': row['stock_name'],
                'side': row['side'],
                'quantity': row['quantity'],
                'price': row['price'],
                'total_amount': row['total_amount'],
                'profit': row['profit'],
                'profit_percent': row['profit_percent'],
                'timestamp': row['timestamp']
            })

        return trades

    def update_position_price(self, position_id: int, current_price: float):
        """포지션의 현재가 업데이트"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE virtual_positions
            SET current_price = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (current_price, position_id))
        self.conn.commit()

    def close(self):
        """데이터베이스 연결 닫기"""
        if self.conn:
            self.conn.close()
            logger.info("가상매매 데이터베이스 연결 종료")
