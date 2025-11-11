"""
AutoTrade Pro - 퀀트 팩터 스크리닝
마법공식, 가치/모멘텀/퀄리티 팩터 스크리닝

주요 기능:
- 조엘 그린블랫 마법공식
- 멀티 팩터 스크리닝
- 팩터 점수 계산
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StockFactors:
    """종목 팩터 데이터"""
    stock_code: str
    stock_name: str

    # 가치 팩터
    per: float  # 주가수익비율
    pbr: float  # 주가순자산비율
    pcr: float  # 주가현금흐름비율
    psr: float  # 주가매출액비율

    # 퀄리티 팩터
    roe: float  # 자기자본이익률
    roa: float  # 총자산이익률
    debt_ratio: float  # 부채비율
    current_ratio: float  # 유동비율

    # 모멘텀 팩터
    return_1m: float  # 1개월 수익률
    return_3m: float  # 3개월 수익률
    return_6m: float  # 6개월 수익률
    return_12m: float  # 12개월 수익률

    # 변동성
    volatility: float  # 변동성

    # 마법공식
    earnings_yield: float  # 이익수익률 (EBIT/EV)
    return_on_capital: float  # 자본수익률 (EBIT/(운전자본+순유형자산))

    # 종합 점수
    total_score: float = 0.0


class QuantScreener:
    """퀀트 팩터 스크리너"""

    def __init__(self, settings: Dict[str, Any] = None):
        """
        초기화

        Args:
            settings: 스크리닝 설정
        """
        self.settings = settings or {}
        self.min_market_cap = self.settings.get('min_market_cap', 100000000000)
        self.min_volume = self.settings.get('min_volume', 100000)

        logger.info("퀀트 스크리너 초기화")

    def magic_formula_screen(
        self,
        stocks: List[StockFactors],
        top_n: int = 30
    ) -> List[StockFactors]:
        """
        마법공식 스크리닝 (조엘 그린블랫)

        Args:
            stocks: 종목 리스트
            top_n: 상위 N개 선택

        Returns:
            스크리닝된 종목 리스트
        """
        # 이익수익률 순위 계산
        stocks_sorted_ey = sorted(stocks, key=lambda x: x.earnings_yield, reverse=True)
        ey_ranks = {stock.stock_code: rank for rank, stock in enumerate(stocks_sorted_ey, 1)}

        # 자본수익률 순위 계산
        stocks_sorted_roc = sorted(stocks, key=lambda x: x.return_on_capital, reverse=True)
        roc_ranks = {stock.stock_code: rank for rank, stock in enumerate(stocks_sorted_roc, 1)}

        # 통합 순위
        for stock in stocks:
            stock.total_score = ey_ranks[stock.stock_code] + roc_ranks[stock.stock_code]

        # 순위 낮은 순(점수 낮은 순)으로 정렬
        result = sorted(stocks, key=lambda x: x.total_score)[:top_n]

        logger.info(f"마법공식 스크리닝: {len(result)}개 종목 선정")
        return result

    def multi_factor_screen(
        self,
        stocks: List[StockFactors],
        weights: Dict[str, float] = None,
        top_n: int = 50
    ) -> List[StockFactors]:
        """
        멀티 팩터 스크리닝

        Args:
            stocks: 종목 리스트
            weights: 팩터 가중치
            top_n: 상위 N개

        Returns:
            스크리닝된 종목
        """
        if weights is None:
            weights = {
                'value': 0.30,
                'quality': 0.30,
                'momentum': 0.30,
                'low_volatility': 0.10
            }

        for stock in stocks:
            # 가치 점수 (낮을수록 좋음)
            value_score = 0
            if stock.per > 0 and stock.per < 20:
                value_score += 1
            if stock.pbr > 0 and stock.pbr < 1.5:
                value_score += 1
            value_score = value_score / 2.0 * 10  # 0~10점

            # 퀄리티 점수
            quality_score = 0
            if stock.roe > 10:
                quality_score += 1
            if stock.debt_ratio < 100:
                quality_score += 1
            quality_score = quality_score / 2.0 * 10

            # 모멘텀 점수
            momentum_score = 0
            if stock.return_3m > 0.05:
                momentum_score += 1
            if stock.return_6m > 0.10:
                momentum_score += 1
            momentum_score = momentum_score / 2.0 * 10

            # 저변동성 점수
            low_vol_score = max(0, 10 - stock.volatility * 100)

            # 가중 평균
            stock.total_score = (
                value_score * weights['value'] +
                quality_score * weights['quality'] +
                momentum_score * weights['momentum'] +
                low_vol_score * weights['low_volatility']
            )

        result = sorted(stocks, key=lambda x: x.total_score, reverse=True)[:top_n]

        logger.info(f"멀티 팩터 스크리닝: {len(result)}개 종목 선정")
        return result

    def value_screen(self, stocks: List[StockFactors], top_n: int = 50) -> List[StockFactors]:
        """가치 팩터 스크리닝"""
        filtered = [s for s in stocks if s.per > 0 and s.pbr > 0]
        result = sorted(filtered, key=lambda x: (x.per + x.pbr))[:top_n]
        return result

    def momentum_screen(self, stocks: List[StockFactors], top_n: int = 50) -> List[StockFactors]:
        """모멘텀 팩터 스크리닝"""
        result = sorted(stocks, key=lambda x: (x.return_3m + x.return_6m), reverse=True)[:top_n]
        return result

    def quality_screen(self, stocks: List[StockFactors], top_n: int = 50) -> List[StockFactors]:
        """퀄리티 팩터 스크리닝"""
        filtered = [s for s in stocks if s.roe > 10 and s.debt_ratio < 100]
        result = sorted(filtered, key=lambda x: x.roe, reverse=True)[:top_n]
        return result


if __name__ == "__main__":
    # 샘플 데이터
    import random

    stocks = []
    for i in range(100):
        stock = StockFactors(
            stock_code=f"{i:06d}",
            stock_name=f"Stock_{i}",
            per=random.uniform(5, 30),
            pbr=random.uniform(0.5, 3.0),
            pcr=random.uniform(5, 25),
            psr=random.uniform(0.5, 2.0),
            roe=random.uniform(5, 25),
            roa=random.uniform(3, 15),
            debt_ratio=random.uniform(20, 200),
            current_ratio=random.uniform(80, 200),
            return_1m=random.uniform(-0.10, 0.10),
            return_3m=random.uniform(-0.20, 0.20),
            return_6m=random.uniform(-0.30, 0.30),
            return_12m=random.uniform(-0.40, 0.40),
            volatility=random.uniform(0.10, 0.30),
            earnings_yield=random.uniform(0.05, 0.20),
            return_on_capital=random.uniform(0.10, 0.40)
        )
        stocks.append(stock)

    screener = QuantScreener()

    # 마법공식
    magic_stocks = screener.magic_formula_screen(stocks, top_n=10)
    print("마법공식 상위 10개:")
    for stock in magic_stocks:
        print(f"  {stock.stock_code}: score={stock.total_score:.1f}")
