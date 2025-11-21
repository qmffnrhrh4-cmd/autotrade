#!/usr/bin/env python3
"""
Database Initialization Script
데이터베이스 초기화 스크립트

This script creates and initializes all database files with proper schemas:
1. virtual_trading.db - Virtual trading strategies, positions, and trades
2. strategy_evolution.db - Strategy evolution, fitness results, and generation stats
"""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_virtual_trading_db(db_path: str = "data/virtual_trading.db"):
    """
    Initialize virtual_trading.db with proper schema

    Tables:
    - virtual_strategies: Virtual trading strategies
    - virtual_positions: Open positions
    - virtual_trades: Trade history
    """
    logger.info(f"Initializing virtual_trading.db at {db_path}...")

    # Create data directory if not exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row

    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=10000")
    conn.execute("PRAGMA synchronous=NORMAL")

    cursor = conn.cursor()

    # 1. Virtual Strategies Table
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
            split_buy_enabled INTEGER DEFAULT 1,
            split_sell_enabled INTEGER DEFAULT 1,
            split_buy_ratios TEXT DEFAULT '0.33,0.33,0.34',
            split_sell_ratios TEXT DEFAULT '0.33,0.33,0.34',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("  ✅ virtual_strategies table created")

    # 2. Virtual Positions Table
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
    logger.info("  ✅ virtual_positions table created")

    # 3. Virtual Trades Table
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
    logger.info("  ✅ virtual_trades table created")

    # Create Indexes
    logger.info("  Creating indexes...")

    # Strategy indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_strategies_created_at
        ON virtual_strategies(created_at DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_strategies_updated_at
        ON virtual_strategies(updated_at DESC)
    """)

    # Position indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_positions_strategy
        ON virtual_positions(strategy_id, is_closed)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_positions_strategy_active
        ON virtual_positions(strategy_id, is_closed, updated_at DESC)
    """)

    # Trade indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_strategy
        ON virtual_trades(strategy_id, timestamp DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_strategy_timestamp
        ON virtual_trades(strategy_id, timestamp DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_stock_timestamp
        ON virtual_trades(stock_code, timestamp DESC)
    """)

    logger.info("  ✅ All indexes created")

    conn.commit()
    conn.close()

    logger.info(f"✅ virtual_trading.db initialized successfully!")
    return db_path


def init_strategy_evolution_db(db_path: str = "data/strategy_evolution.db"):
    """
    Initialize strategy_evolution.db with proper schema

    Tables:
    - evolved_strategies: Evolved strategy genes by generation
    - fitness_results: Fitness evaluation results
    - generation_stats: Statistics for each generation
    """
    logger.info(f"Initializing strategy_evolution.db at {db_path}...")

    # Create data directory if not exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    # 1. Evolved Strategies Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evolved_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generation INTEGER NOT NULL,
            genes TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("  ✅ evolved_strategies table created")

    # 2. Fitness Results Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fitness_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER NOT NULL,
            generation INTEGER NOT NULL,
            total_return_pct REAL,
            sharpe_ratio REAL,
            win_rate REAL,
            max_drawdown_pct REAL,
            profit_factor REAL,
            total_trades INTEGER,
            fitness_score REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (strategy_id) REFERENCES evolved_strategies(id)
        )
    """)
    logger.info("  ✅ fitness_results table created")

    # 3. Generation Stats Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generation_stats (
            generation INTEGER PRIMARY KEY,
            best_fitness REAL NOT NULL,
            avg_fitness REAL NOT NULL,
            worst_fitness REAL NOT NULL,
            best_strategy_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("  ✅ generation_stats table created")

    # Create Indexes
    logger.info("  Creating indexes...")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_evolved_strategies_generation
        ON evolved_strategies(generation DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fitness_results_strategy
        ON fitness_results(strategy_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fitness_results_generation
        ON fitness_results(generation DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fitness_results_score
        ON fitness_results(fitness_score DESC)
    """)

    logger.info("  ✅ All indexes created")

    conn.commit()
    conn.close()

    logger.info(f"✅ strategy_evolution.db initialized successfully!")
    return db_path


def init_all_databases():
    """Initialize all databases"""
    logger.info("=" * 80)
    logger.info("Database Initialization Script")
    logger.info("=" * 80)
    logger.info("")

    # Initialize databases
    virtual_db = init_virtual_trading_db()
    logger.info("")
    evolution_db = init_strategy_evolution_db()

    logger.info("")
    logger.info("=" * 80)
    logger.info("Database Initialization Complete!")
    logger.info("=" * 80)
    logger.info(f"✅ virtual_trading.db: {virtual_db}")
    logger.info(f"✅ strategy_evolution.db: {evolution_db}")
    logger.info("")
    logger.info("You can now run the dashboard:")
    logger.info("  python main.py --dashboard")
    logger.info("")


if __name__ == "__main__":
    init_all_databases()
