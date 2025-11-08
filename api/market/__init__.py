"""
api/market/__init__.py
시장 정보 API 통합 모듈

모듈화 구조:
- market_data.py: 시세/호가 데이터
- chart_data.py: 차트 데이터
- ranking.py: 순위 정보
- investor_data.py: 투자자 매매 데이터
- stock_info.py: 종목/업종/테마 정보
"""
from .market_data import MarketDataAPI
from .chart_data import ChartDataAPI, get_daily_chart
from .ranking import RankingAPI
from .investor_data import InvestorDataAPI
from .stock_info import StockInfoAPI
import logging

logger = logging.getLogger(__name__)


class MarketAPI:
    """
    통합 시장 정보 API (Unified Facade Pattern)

    5개 모듈을 통합한 단일 인터페이스:
    - MarketDataAPI: 시세/호가 데이터
    - ChartDataAPI: 차트 데이터
    - RankingAPI: 순위 정보
    - InvestorDataAPI: 투자자 매매 데이터
    - StockInfoAPI: 종목/업종/테마 정보

    Usage:
        from api.market import MarketAPI

        market_api = MarketAPI(client)

        # 시세 조회
        price = market_api.get_stock_price('005930')

        # 순위 조회
        volume_rank = market_api.get_volume_rank()

        # 차트 조회
        daily_chart = market_api.get_daily_chart('005930', period=20)
    """

    def __init__(self, client):
        """
        MarketAPI 초기화

        Args:
            client: KiwoomRESTClient 인스턴스
        """
        self.client = client

        # 5개 서브 API 초기화
        self.market_data = MarketDataAPI(client)
        self.chart_data = ChartDataAPI(client)
        self.ranking = RankingAPI(client)
        self.investor_data = InvestorDataAPI(client)
        self.stock_info = StockInfoAPI(client)

        logger.info("MarketAPI 초기화 완료 (5개 모듈 통합)")

    # =========================================================================
    # MarketDataAPI 메서드 위임 (시세/호가)
    # =========================================================================

    def get_stock_price(self, stock_code: str, use_fallback: bool = True):
        """종목 체결정보 조회 (현재가)"""
        return self.market_data.get_stock_price(stock_code, use_fallback)

    def get_orderbook(self, stock_code: str):
        """호가 조회"""
        return self.market_data.get_orderbook(stock_code)

    def get_bid_ask(self, stock_code: str):
        """호가 데이터 조회 (get_orderbook 별칭)"""
        return self.market_data.get_bid_ask(stock_code)

    def get_market_index(self, market_code: str = '001'):
        """시장 지수 조회"""
        return self.market_data.get_market_index(market_code)

    # =========================================================================
    # ChartDataAPI 메서드 위임 (차트)
    # =========================================================================

    def get_daily_chart(self, stock_code: str, period: int = 20, date: str = None):
        """일봉 차트 데이터 조회"""
        return self.chart_data.get_daily_chart(stock_code, period, date)

    def get_daily_price(self, stock_code: str, days: int = 20, date: str = None):
        """일봉 가격 데이터 조회 (get_daily_chart 별칭)"""
        return self.chart_data.get_daily_chart(stock_code, period=days, date=date)

    def get_minute_chart(self, stock_code: str, interval: int = 1, count: int = 100,
                        adjusted: bool = True, base_date: str = None, use_nxt_fallback: bool = True):
        """분봉 차트 데이터 조회 (v6.0 NXT 지원)"""
        return self.chart_data.get_minute_chart(stock_code, interval, count, adjusted, base_date, use_nxt_fallback)

    def get_multi_timeframe_data(self, stock_code: str, timeframes=None):
        """다중 시간프레임 데이터 조회"""
        if timeframes is None:
            timeframes = [1, 5, 15, 'daily']
        return self.chart_data.get_multi_timeframe_data(stock_code, timeframes)

    # =========================================================================
    # RankingAPI 메서드 위임 (순위)
    # =========================================================================

    def get_volume_rank(self, market: str = 'ALL', limit: int = 20, date: str = None):
        """전일 거래량 순위 조회"""
        return self.ranking.get_volume_rank(market, limit, date)

    def get_price_change_rank(self, market: str = 'ALL', sort: str = 'rise', limit: int = 20, date: str = None):
        """전일대비 등락률 상위 조회"""
        return self.ranking.get_price_change_rank(market, sort, limit, date)

    def get_trading_value_rank(self, market: str = 'ALL', limit: int = 20, include_managed: bool = False):
        """거래대금 상위 조회"""
        return self.ranking.get_trading_value_rank(market, limit, include_managed)

    def get_volume_surge_rank(self, market: str = 'ALL', limit: int = 20, time_interval: int = 5):
        """거래량 급증 종목 조회"""
        return self.ranking.get_volume_surge_rank(market, limit, time_interval)

    def get_intraday_change_rank(self, market: str = 'ALL', sort: str = 'rise', limit: int = 20):
        """시가대비 등락률 순위 조회"""
        return self.ranking.get_intraday_change_rank(market, sort, limit)

    def get_foreign_period_trading_rank(self, market: str = 'KOSPI', trade_type: str = 'buy', period_days: int = 5, limit: int = 20):
        """외국인 기간별 매매 상위"""
        return self.ranking.get_foreign_period_trading_rank(market, trade_type, period_days, limit)

    def get_foreign_continuous_trading_rank(self, market: str = 'KOSPI', trade_type: str = 'buy', limit: int = 20):
        """외국인 연속 순매매 상위"""
        return self.ranking.get_foreign_continuous_trading_rank(market, trade_type, limit)

    def get_foreign_institution_trading_rank(self, market: str = 'KOSPI', amount_or_qty: str = 'amount', date: str = None, limit: int = 20, investor_type: str = 'foreign_buy'):
        """외국인/기관 매매 상위"""
        return self.ranking.get_foreign_institution_trading_rank(market, amount_or_qty, date, limit, investor_type)

    def get_credit_ratio_rank(self, market: str = 'KOSPI', limit: int = 20):
        """신용비율 상위"""
        return self.ranking.get_credit_ratio_rank(market, limit)

    def get_investor_intraday_trading_rank(self, market: str = 'KOSPI', investor_type: str = 'foreign', limit: int = 20):
        """장중 투자자별 매매 상위"""
        return self.ranking.get_investor_intraday_trading_rank(market, investor_type, limit)

    # =========================================================================
    # InvestorDataAPI 메서드 위임 (투자자 매매)
    # =========================================================================

    def get_investor_trading(self, stock_code: str, date: str = None):
        """투자자별 매매 동향 조회"""
        return self.investor_data.get_investor_trading(stock_code, date)

    def get_investor_data(self, stock_code: str, date: str = None):
        """투자자 매매 데이터 조회 (get_investor_trading 별칭)"""
        return self.investor_data.get_investor_data(stock_code, date)

    def get_intraday_investor_trading_market(self, market: str = 'KOSPI', investor_type: str = 'institution', amount_or_qty: str = 'amount', exchange: str = 'KRX'):
        """장중 투자자별 매매 상위 (시장 전체)"""
        return self.investor_data.get_intraday_investor_trading_market(market, investor_type, amount_or_qty, exchange)

    def get_postmarket_investor_trading_market(self, market: str = 'KOSPI', amount_or_qty: str = 'amount', trade_type: str = 'net_buy', exchange: str = 'KRX'):
        """장마감후 투자자별 매매 상위 (시장 전체)"""
        return self.investor_data.get_postmarket_investor_trading_market(market, amount_or_qty, trade_type, exchange)

    def get_institutional_trading_trend(self, stock_code: str, days: int = 5, price_type: str = 'buy'):
        """종목별 기관매매추이"""
        return self.investor_data.get_institutional_trading_trend(stock_code, days, price_type)

    def get_securities_firm_trading(self, firm_code: str, stock_code: str, days: int = 3):
        """증권사별 종목매매동향"""
        return self.investor_data.get_securities_firm_trading(firm_code, stock_code, days)

    def get_execution_intensity(self, stock_code: str, days: int = 1):
        """체결강도 조회"""
        return self.investor_data.get_execution_intensity(stock_code, days)

    def get_program_trading(self, stock_code: str, days: int = 1):
        """프로그램매매 추이 조회"""
        return self.investor_data.get_program_trading(stock_code, days)

    # =========================================================================
    # StockInfoAPI 메서드 위임 (종목/업종/테마)
    # =========================================================================

    def get_sector_list(self):
        """업종 목록 조회"""
        return self.stock_info.get_sector_list()

    def get_sector_info(self, sector_code: str):
        """업종 정보 조회"""
        return self.stock_info.get_sector_info(sector_code)

    def get_theme_list(self):
        """테마 목록 조회"""
        return self.stock_info.get_theme_list()

    def get_theme_stocks(self, theme_code: str):
        """테마 종목 조회"""
        return self.stock_info.get_theme_stocks(theme_code)

    def get_stock_info(self, stock_code: str):
        """종목 상세 정보 조회"""
        return self.stock_info.get_stock_info(stock_code)

    def search_stock(self, keyword: str):
        """종목 검색"""
        return self.stock_info.search_stock(keyword)


# Export consolidated API
__all__ = [
    'MarketAPI',
    'MarketDataAPI',
    'ChartDataAPI',
    'RankingAPI',
    'InvestorDataAPI',
    'StockInfoAPI',
    'get_daily_chart',
]
