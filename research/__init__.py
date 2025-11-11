"""
research 패키지
데이터 조회 및 분석 모듈
"""
from .data_fetcher import DataFetcher
from .analyzer import Analyzer
from .screener import Screener

from .quant_screener import QuantScreener, StockFactors

# 기존 코드 호환성을 위한 Research 클래스
class Research:
    """
    Research 통합 클래스 (기존 코드 호환용)
    """
    
    def __init__(self, client):
        self.client = client
        self.fetcher = DataFetcher(client)
        self.analyzer = Analyzer(client)
        self.screener = Screener(client)
    
    # DataFetcher 메서드 위임
    def get_balance(self, account_number=None):
        return self.fetcher.get_balance(account_number)
    
    def get_deposit(self, account_number=None):
        return self.fetcher.get_deposit(account_number)
    
    def get_holdings(self, account_number=None):
        return self.fetcher.get_holdings(account_number)
    
    def get_current_price(self, stock_code):
        return self.fetcher.get_current_price(stock_code)
    
    def get_orderbook(self, stock_code):
        return self.fetcher.get_orderbook(stock_code)
    
    def get_daily_price(self, stock_code, start_date=None, end_date=None):
        return self.fetcher.get_daily_price(stock_code, start_date, end_date)

    def get_minute_price(self, stock_code, minute_type='1'):
        return self.fetcher.get_minute_price(stock_code, minute_type)

    def search_stock(self, keyword):
        return self.fetcher.search_stock(keyword)
    
    def get_volume_rank(self, market='ALL', limit=20):
        return self.fetcher.get_volume_rank(market, limit)
    
    def get_price_change_rank(self, market='ALL', sort='rise', limit=20):
        return self.fetcher.get_price_change_rank(market, sort, limit)
    
    def get_investor_trading(self, stock_code, date=None):
        return self.fetcher.get_investor_trading(stock_code, date)
    
    def get_stock_info(self, stock_code):
        return self.fetcher.get_stock_info(stock_code)
    
    # Analyzer 메서드 위임
    def get_stock_data_for_analysis(self, stock_code):
        return self.analyzer.get_stock_data_for_analysis(stock_code)
    
    def get_available_cash(self, account_number=None):
        return self.analyzer.get_available_cash(account_number)
    
    def get_buyable_quantity(self, stock_code, price=None, account_number=None):
        return self.analyzer.get_buyable_quantity(stock_code, price, account_number)
    
    def is_market_open(self):
        return self.analyzer.is_market_open()
    
    # Screener 메서드 위임
    def screen_stocks(self, **filters):
        return self.screener.screen_combined(**filters)


__all__ = [
    'Research',
    'DataFetcher',
    'Analyzer',
    'Screener',
    
    'QuantScreener',
    'StockFactors',
]