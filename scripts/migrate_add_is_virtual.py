#!/usr/bin/env python3
"""
DB Migration Script: Add is_virtual column to trades table
Version: 6.1.1
Date: 2025-11-18

This script adds the is_virtual column to existing trades table
and sets all existing records to is_virtual=False (real trades).
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db_session, Trade
from sqlalchemy import inspect, Boolean, Column
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_column_exists(engine, table_name, column_name):
    """Check if column exists in table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_database():
    """Add is_virtual column and set default values"""
    try:
        session = get_db_session()
        engine = session.bind

        logger.info("=" * 60)
        logger.info("Starting database migration: Add is_virtual column")
        logger.info("=" * 60)

        # Check if column already exists
        if check_column_exists(engine, 'trades', 'is_virtual'):
            logger.info("✅ Column 'is_virtual' already exists in 'trades' table")
            logger.info("Nothing to migrate.")
            return

        # Add column using raw SQL
        logger.info("📝 Adding 'is_virtual' column to 'trades' table...")

        # SQLite doesn't support ALTER TABLE ADD COLUMN with DEFAULT and NOT NULL directly
        # So we add it as nullable first, then update all records, then make it NOT NULL
        session.execute("ALTER TABLE trades ADD COLUMN is_virtual BOOLEAN DEFAULT 0")
        session.commit()
        logger.info("✅ Column added successfully")

        # Update all existing records to is_virtual=False (real trades)
        logger.info("📝 Setting is_virtual=False for all existing trades...")
        count = session.query(Trade).filter(Trade.is_virtual == None).count()
        logger.info(f"Found {count} existing trades to update")

        if count > 0:
            session.query(Trade).filter(Trade.is_virtual == None).update(
                {Trade.is_virtual: False},
                synchronize_session='fetch'
            )
            session.commit()
            logger.info(f"✅ Updated {count} trades to is_virtual=False")

        # Create index for better query performance
        logger.info("📝 Creating index on is_virtual column...")
        session.execute("CREATE INDEX IF NOT EXISTS idx_trades_is_virtual ON trades(is_virtual)")
        session.commit()
        logger.info("✅ Index created successfully")

        logger.info("=" * 60)
        logger.info("✅ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  - Added 'is_virtual' column to 'trades' table")
        logger.info(f"  - Set {count} existing trades as is_virtual=False (real trades)")
        logger.info(f"  - Created index for better query performance")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  - All future real trades will be marked as is_virtual=False")
        logger.info("  - Virtual trading logs should be marked as is_virtual=True")
        logger.info("  - Performance metrics will now only show real trading results")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise
    finally:
        if session:
            session.close()


if __name__ == "__main__":
    logger.info("\n")
    logger.info("🚀 AutoTrade Pro - Database Migration Tool")
    logger.info("Migration: Add is_virtual column to trades table")
    logger.info("\n")

    try:
        migrate_database()
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Migration failed with error: {e}\n")
        sys.exit(1)
