"""
Refactored Modules Integration Test
통합 모듈 테스트

테스트 대상:
- UnifiedBacktester (ai/unified_backtester.py)
- UnifiedCache (utils/unified_cache.py)
- 호환성 레이어
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from datetime import datetime, timedelta

try:
    import pandas as pd
    import numpy as np
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class TestUnifiedBacktester(unittest.TestCase):
    """UnifiedBacktester 테스트"""

    def setUp(self):
        from ai.unified_backtester import UnifiedBacktester, BacktestConfig
        self.config = BacktestConfig(
            initial_capital=10_000_000,
            commission_rate=0.00015,
            slippage_pct=0.001,
            tax_rate=0.0023
        )
        self.backtester = UnifiedBacktester(config=self.config)

    def test_initialization(self):
        """초기화 테스트"""
        self.assertEqual(self.backtester.cash, 10_000_000)
        self.assertEqual(len(self.backtester.positions), 0)
        self.assertEqual(len(self.backtester.trades), 0)

    def test_buy_operation(self):
        """매수 연산 테스트"""
        self.backtester.current_time = datetime.now()
        trade = self.backtester.buy("005930", 10, 70000)

        self.assertIsNotNone(trade)
        self.assertEqual(trade.stock_code, "005930")
        self.assertEqual(trade.side, "buy")
        self.assertEqual(trade.quantity, 10)
        self.assertIn("005930", self.backtester.positions)

    def test_sell_operation(self):
        """매도 연산 테스트"""
        self.backtester.current_time = datetime.now()

        self.backtester.buy("005930", 10, 70000)

        trade = self.backtester.sell("005930", 10, 72000)

        self.assertIsNotNone(trade)
        self.assertEqual(trade.side, "sell")
        self.assertNotIn("005930", self.backtester.positions)
        self.assertGreater(trade.pnl, 0)

    def test_equity_calculation(self):
        """자산 계산 테스트"""
        initial_equity = self.backtester.get_equity()
        self.assertEqual(initial_equity, 10_000_000)

    def test_config_dataclass(self):
        """BacktestConfig 테스트"""
        from ai.unified_backtester import BacktestConfig
        config = BacktestConfig()
        self.assertEqual(config.initial_capital, 10_000_000)
        self.assertEqual(config.commission_rate, 0.00015)

    def test_result_dataclass(self):
        """BacktestResult 테스트"""
        from ai.unified_backtester import BacktestResult
        result = BacktestResult(
            strategy_name="Test",
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=10_000_000,
            final_capital=11_000_000,
            total_return=1_000_000,
            total_return_pct=10.0,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=500_000,
            max_drawdown_pct=5.0,
            calmar_ratio=2.0,
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            win_rate=60.0,
            avg_win=50000,
            avg_loss=-30000,
            max_win=100000,
            max_loss=-50000,
            profit_factor=1.5,
            avg_holding_days=5,
            total_commission=50000
        )
        self.assertEqual(result.strategy_name, "Test")
        self.assertEqual(result.win_rate, 60.0)

        result_dict = result.to_dict()
        self.assertIn('sharpe_ratio', result_dict)


class TestUnifiedCache(unittest.TestCase):
    """UnifiedCache 테스트"""

    def setUp(self):
        from utils.unified_cache import UnifiedCache
        self.cache = UnifiedCache(max_size=100, max_memory_mb=10, default_ttl=5)

    def test_set_and_get(self):
        """저장 및 조회 테스트"""
        self.cache.set("test_key", {"value": 123})
        result = self.cache.get("test_key")
        self.assertEqual(result["value"], 123)

    def test_cache_miss(self):
        """캐시 미스 테스트"""
        result = self.cache.get("nonexistent_key")
        self.assertIsNone(result)

    def test_default_value(self):
        """기본값 테스트"""
        result = self.cache.get("nonexistent", default="default_value")
        self.assertEqual(result, "default_value")

    def test_delete(self):
        """삭제 테스트"""
        self.cache.set("to_delete", "value")
        self.assertTrue(self.cache.delete("to_delete"))
        self.assertIsNone(self.cache.get("to_delete"))

    def test_get_or_set(self):
        """get_or_set 테스트"""
        result = self.cache.get_or_set("lazy_key", lambda: "lazy_value")
        self.assertEqual(result, "lazy_value")

        result2 = self.cache.get_or_set("lazy_key", lambda: "new_value")
        self.assertEqual(result2, "lazy_value")

    def test_stats(self):
        """통계 테스트"""
        self.cache.set("stat_key", "value")
        self.cache.get("stat_key")
        self.cache.get("missing_key")

        stats = self.cache.get_stats()
        self.assertGreater(stats.hits, 0)
        self.assertGreater(stats.misses, 0)

    def test_clear(self):
        """전체 삭제 테스트"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.clear()
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))

    def test_tag_invalidation(self):
        """태그 기반 무효화 테스트"""
        self.cache.set("tagged1", "value1", tags=["tag1"])
        self.cache.set("tagged2", "value2", tags=["tag1"])
        self.cache.set("untagged", "value3")

        count = self.cache.invalidate_by_tag("tag1")
        self.assertEqual(count, 2)
        self.assertIsNone(self.cache.get("tagged1"))
        self.assertIsNotNone(self.cache.get("untagged"))


class TestCompatibilityLayers(unittest.TestCase):
    """호환성 레이어 테스트"""

    def test_backtesting_import(self):
        """backtesting.py 임포트 테스트"""
        from ai.backtesting import BacktestEngine, BacktestConfig, BacktestResult
        self.assertIsNotNone(BacktestEngine)
        self.assertIsNotNone(BacktestConfig)
        self.assertIsNotNone(BacktestResult)

    def test_strategy_backtester_import(self):
        """strategy_backtester.py 임포트 테스트"""
        from ai.strategy_backtester import StrategyBacktester, BacktestConfig
        self.assertIsNotNone(StrategyBacktester)

    def test_advanced_backtester_import(self):
        """advanced_backtester.py 임포트 테스트"""
        from ai.advanced_backtester import AdvancedBacktester, BacktestConfig
        self.assertIsNotNone(AdvancedBacktester)

    def test_cache_manager_import(self):
        """cache_manager.py 임포트 테스트"""
        from utils.cache_manager import CacheManager, CacheTTL, get_cache_manager
        self.assertIsNotNone(CacheManager)
        self.assertIsNotNone(CacheTTL)

    def test_data_cache_import(self):
        """data_cache.py 임포트 테스트"""
        from utils.data_cache import LRUCache, MultiLevelCache, cached
        self.assertIsNotNone(LRUCache)
        self.assertIsNotNone(MultiLevelCache)

    def test_rate_limited_logger_import(self):
        """rate_limited_logger.py 임포트 테스트"""
        from utils.rate_limited_logger import RateLimitedLogger, get_rate_limited_logger
        self.assertIsNotNone(RateLimitedLogger)


class TestCacheTTL(unittest.TestCase):
    """CacheTTL 상수 테스트"""

    def test_ttl_values(self):
        """TTL 값 테스트"""
        from utils.unified_cache import CacheTTL

        self.assertEqual(CacheTTL.REALTIME, 3)
        self.assertEqual(CacheTTL.STOCK_PRICE, 5)
        self.assertEqual(CacheTTL.MARKET_DATA, 60)
        self.assertEqual(CacheTTL.HISTORICAL_DATA, 600)
        self.assertEqual(CacheTTL.NEVER_EXPIRE, 0)


class TestValidation(unittest.TestCase):
    """검증 유틸리티 테스트"""

    def test_stock_code_validation(self):
        """종목 코드 검증 테스트"""
        from dashboard.utils.validation import validate_stock_code

        self.assertTrue(validate_stock_code("005930"))
        self.assertTrue(validate_stock_code("AAPL"))
        self.assertFalse(validate_stock_code(""))
        self.assertFalse(validate_stock_code("12345"))

    def test_quantity_validation(self):
        """수량 검증 테스트"""
        from dashboard.utils.validation import validate_quantity

        valid, val, err = validate_quantity(100)
        self.assertTrue(valid)
        self.assertEqual(val, 100)

        valid, val, err = validate_quantity(-1)
        self.assertFalse(valid)

    def test_price_validation(self):
        """가격 검증 테스트"""
        from dashboard.utils.validation import validate_price

        valid, val, err = validate_price(50000)
        self.assertTrue(valid)
        self.assertEqual(val, 50000.0)

        valid, val, err = validate_price(-100)
        self.assertFalse(valid)

    def test_percentage_validation(self):
        """퍼센트 검증 테스트"""
        from dashboard.utils.validation import validate_percentage

        valid, val, err = validate_percentage(5.0)
        self.assertTrue(valid)

        valid, val, err = validate_percentage(150)
        self.assertFalse(valid)


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Refactored Modules Integration Test")
    print("=" * 60)

    unittest.main(verbosity=2)
