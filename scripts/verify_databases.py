#!/usr/bin/env python3
"""
Database Verification Script
데이터베이스 검증 스크립트

Verifies that all database tables and indexes are created properly.
"""
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verify_virtual_trading_db(db_path: str = "data/virtual_trading.db"):
    """Verify virtual_trading.db schema"""
    logger.info(f"Verifying {db_path}...")

    if not Path(db_path).exists():
        logger.error(f"  ❌ Database file not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    expected_tables = ['virtual_strategies', 'virtual_positions', 'virtual_trades']

    logger.info("  Tables:")
    for table in expected_tables:
        if table in tables:
            logger.info(f"    ✅ {table}")
        else:
            logger.error(f"    ❌ {table} NOT FOUND")
            return False

    # Check indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [row[0] for row in cursor.fetchall()]

    logger.info(f"  Indexes: {len(indexes)} created")
    for idx in indexes[:5]:  # Show first 5
        logger.info(f"    - {idx}")
    if len(indexes) > 5:
        logger.info(f"    ... and {len(indexes) - 5} more")

    # Check sample data structure
    cursor.execute("PRAGMA table_info(virtual_strategies)")
    columns = cursor.fetchall()
    logger.info(f"  virtual_strategies columns: {len(columns)}")

    conn.close()
    return True


def verify_strategy_evolution_db(db_path: str = "data/strategy_evolution.db"):
    """Verify strategy_evolution.db schema"""
    logger.info(f"Verifying {db_path}...")

    if not Path(db_path).exists():
        logger.error(f"  ❌ Database file not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    expected_tables = ['evolved_strategies', 'fitness_results', 'generation_stats']

    logger.info("  Tables:")
    for table in expected_tables:
        if table in tables:
            logger.info(f"    ✅ {table}")
        else:
            logger.error(f"    ❌ {table} NOT FOUND")
            return False

    # Check indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [row[0] for row in cursor.fetchall()]

    logger.info(f"  Indexes: {len(indexes)} created")
    for idx in indexes:
        logger.info(f"    - {idx}")

    # Check sample data structure
    cursor.execute("PRAGMA table_info(evolved_strategies)")
    columns = cursor.fetchall()
    logger.info(f"  evolved_strategies columns: {len(columns)}")

    conn.close()
    return True


def main():
    """Main verification function"""
    logger.info("=" * 80)
    logger.info("Database Verification Script")
    logger.info("=" * 80)
    logger.info("")

    success = True

    # Verify virtual_trading.db
    if not verify_virtual_trading_db():
        success = False
    logger.info("")

    # Verify strategy_evolution.db
    if not verify_strategy_evolution_db():
        success = False
    logger.info("")

    # Summary
    logger.info("=" * 80)
    if success:
        logger.info("✅ All databases verified successfully!")
    else:
        logger.error("❌ Database verification failed!")
    logger.info("=" * 80)

    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
