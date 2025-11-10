"""
research/learned_selector.py
Learning-based Stock Selector - 가상매매 성공 패턴 학습

Features:
- Extract characteristics from successful virtual trades
- Discover similar stocks based on learned patterns
- Avoid stocks with failure patterns
- Continuous learning from trading results
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
from collections import defaultdict

from utils.logger_new import get_logger


logger = get_logger()


@dataclass
class StockPattern:
    """종목 패턴"""
    stock_code: str
    stock_name: str
    avg_price: int
    avg_volume: int
    avg_change_rate: float
    success_rate: float
    avg_profit: float
    total_trades: int
    last_trade_date: Optional[str] = None


class LearnedSelector:
    """학습 기반 종목 선정기"""

    def __init__(self, performance_tracker=None):
        """
        초기화

        Args:
            performance_tracker: 가상매매 성과 추적기 (선택)
        """
        self.performance_tracker = performance_tracker
        self.success_patterns = {}
        self.failure_patterns = {}
        self.pattern_cache = {}

        self._load_patterns()

        logger.info(f"학습 기반 선정기 초기화: 성공 패턴 {len(self.success_patterns)}개, 실패 패턴 {len(self.failure_patterns)}개")

    def _load_patterns(self):
        """과거 거래 패턴 로드"""
        try:
            perf_file = Path('data/virtual_trading/performance.json')
            if not perf_file.exists():
                logger.debug("가상매매 성과 데이터 없음")
                return

            with open(perf_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            strategy_records = data.get('strategy_records', {})

            stock_stats = defaultdict(lambda: {
                'trades': [],
                'total_pnl': 0,
                'wins': 0,
                'losses': 0
            })

            for records in strategy_records.values():
                trades = records.get('trades', [])

                for trade in trades:
                    stock_code = trade.get('stock_code')
                    stock_name = trade.get('stock_name')
                    pnl = trade.get('profit_loss')

                    if not stock_code or pnl is None:
                        continue

                    stats = stock_stats[stock_code]
                    stats['trades'].append(trade)
                    stats['total_pnl'] += pnl
                    stats['stock_name'] = stock_name

                    if pnl > 0:
                        stats['wins'] += 1
                    else:
                        stats['losses'] += 1

            for stock_code, stats in stock_stats.items():
                total_trades = len(stats['trades'])
                if total_trades == 0:
                    continue

                success_rate = (stats['wins'] / total_trades) * 100
                avg_profit = stats['total_pnl'] / total_trades

                prices = [t.get('buy_price', 0) for t in stats['trades'] if t.get('buy_price')]
                volumes = [t.get('volume', 0) for t in stats['trades'] if t.get('volume')]
                change_rates = [t.get('change_rate', 0) for t in stats['trades'] if t.get('change_rate')]

                pattern = StockPattern(
                    stock_code=stock_code,
                    stock_name=stats.get('stock_name', ''),
                    avg_price=int(float(sum(prices)) / len(prices)) if prices else 0,
                    avg_volume=int(float(sum(volumes)) / len(volumes)) if volumes else 0,
                    avg_change_rate=sum(change_rates) / len(change_rates) if change_rates else 0,
                    success_rate=success_rate,
                    avg_profit=avg_profit,
                    total_trades=total_trades,
                    last_trade_date=stats['trades'][-1].get('timestamp')
                )

                if success_rate >= 60 and avg_profit > 10000:
                    self.success_patterns[stock_code] = pattern
                elif success_rate <= 40 or avg_profit < -10000:
                    self.failure_patterns[stock_code] = pattern

            logger.info(
                f"패턴 로드 완료: 성공 {len(self.success_patterns)}개, "
                f"실패 {len(self.failure_patterns)}개"
            )

        except Exception as e:
            logger.warning(f"패턴 로드 실패: {e}")

    def find_similar_stocks(
        self,
        candidate_stocks: List[Dict[str, Any]],
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        성공 패턴과 유사한 종목 발굴

        Args:
            candidate_stocks: 후보 종목 리스트
            top_n: 상위 N개 선택

        Returns:
            유사도 순으로 정렬된 종목 리스트
        """
        if not self.success_patterns:
            logger.debug("학습된 성공 패턴 없음")
            return candidate_stocks[:top_n]

        scored_stocks = []

        for stock in candidate_stocks:
            similarity_score = self._calculate_similarity_score(stock)
            stock['similarity_score'] = similarity_score
            scored_stocks.append(stock)

        scored_stocks.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)

        logger.info(
            f"유사 종목 발굴: {len(scored_stocks)}개 중 상위 {top_n}개 선택 "
            f"(최고 유사도: {scored_stocks[0]['similarity_score']:.2f})"
        )

        return scored_stocks[:top_n]

    def _calculate_similarity_score(self, stock: Dict[str, Any]) -> float:
        """성공 패턴과의 유사도 계산"""
        stock_code = stock.get('stock_code', stock.get('code'))
        price = stock.get('current_price', stock.get('price', 0))
        volume = stock.get('volume', 0)
        change_rate = stock.get('change_rate', stock.get('rate', 0))

        if stock_code in self.failure_patterns:
            return -50.0

        if stock_code in self.success_patterns:
            return 100.0

        total_similarity = 0.0
        pattern_count = 0

        for pattern in self.success_patterns.values():
            price_similarity = self._compare_price(price, pattern.avg_price)
            volume_similarity = self._compare_volume(volume, pattern.avg_volume)
            change_similarity = self._compare_change_rate(change_rate, pattern.avg_change_rate)

            pattern_similarity = (
                price_similarity * 0.3 +
                volume_similarity * 0.3 +
                change_similarity * 0.4
            ) * (pattern.success_rate / 100)

            total_similarity += pattern_similarity
            pattern_count += 1

        return total_similarity / pattern_count if pattern_count > 0 else 0.0

    def _compare_price(self, price1: int, price2: int) -> float:
        """가격 유사도 (0-100)"""
        if price2 == 0:
            return 0.0

        ratio = price1 / price2
        if 0.8 <= ratio <= 1.2:
            return 100.0
        elif 0.5 <= ratio <= 2.0:
            return 70.0
        elif 0.3 <= ratio <= 3.0:
            return 40.0
        else:
            return 10.0

    def _compare_volume(self, volume1: int, volume2: int) -> float:
        """거래량 유사도 (0-100)"""
        if volume2 == 0:
            return 0.0

        ratio = volume1 / volume2
        if 0.7 <= ratio <= 1.5:
            return 100.0
        elif 0.4 <= ratio <= 3.0:
            return 70.0
        elif 0.2 <= ratio <= 5.0:
            return 40.0
        else:
            return 10.0

    def _compare_change_rate(self, rate1: float, rate2: float) -> float:
        """등락률 유사도 (0-100)"""
        diff = abs(rate1 - rate2)

        if diff < 1.0:
            return 100.0
        elif diff < 2.0:
            return 80.0
        elif diff < 3.0:
            return 60.0
        elif diff < 5.0:
            return 40.0
        else:
            return 20.0

    def filter_failure_patterns(
        self,
        candidate_stocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """실패 패턴 종목 제외"""
        if not self.failure_patterns:
            return candidate_stocks

        filtered = []
        excluded_count = 0

        for stock in candidate_stocks:
            stock_code = stock.get('stock_code', stock.get('code'))

            if stock_code in self.failure_patterns:
                pattern = self.failure_patterns[stock_code]
                logger.debug(
                    f"제외: {pattern.stock_name} (승률 {pattern.success_rate:.1f}%, "
                    f"평균손익 {pattern.avg_profit:,.0f}원)"
                )
                excluded_count += 1
                continue

            filtered.append(stock)

        if excluded_count > 0:
            logger.info(f"실패 패턴 필터링: {excluded_count}개 종목 제외")

        return filtered

    def get_success_characteristics(self) -> Dict[str, Any]:
        """성공 종목들의 공통 특징 추출"""
        if not self.success_patterns:
            return {}

        patterns = list(self.success_patterns.values())

        avg_price = sum(p.avg_price for p in patterns) / len(patterns)
        avg_volume = sum(p.avg_volume for p in patterns) / len(patterns)
        avg_change_rate = sum(p.avg_change_rate for p in patterns) / len(patterns)
        avg_success_rate = sum(p.success_rate for p in patterns) / len(patterns)
        avg_profit = sum(p.avg_profit for p in patterns) / len(patterns)

        return {
            'total_success_stocks': len(patterns),
            'avg_price': avg_price,
            'avg_volume': avg_volume,
            'avg_change_rate': avg_change_rate,
            'avg_success_rate': avg_success_rate,
            'avg_profit': avg_profit,
            'top_stocks': sorted(
                patterns,
                key=lambda p: p.avg_profit,
                reverse=True
            )[:5]
        }

    def recommend_stocks(
        self,
        all_stocks: List[Dict[str, Any]],
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        종합 추천 (실패 패턴 제외 + 유사 종목 발굴)

        Args:
            all_stocks: 전체 종목 리스트
            top_n: 추천 개수

        Returns:
            추천 종목 리스트
        """
        filtered = self.filter_failure_patterns(all_stocks)

        similar = self.find_similar_stocks(filtered, top_n)

        return similar

    def update_from_trade_result(
        self,
        stock_code: str,
        stock_name: str,
        trade_data: Dict[str, Any]
    ):
        """거래 결과로부터 학습 업데이트"""
        try:
            pnl = trade_data.get('profit_loss')
            if pnl is None:
                return

            if stock_code in self.success_patterns:
                pattern = self.success_patterns[stock_code]
            elif stock_code in self.failure_patterns:
                pattern = self.failure_patterns[stock_code]
            else:
                pattern = StockPattern(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    avg_price=trade_data.get('buy_price', 0),
                    avg_volume=trade_data.get('volume', 0),
                    avg_change_rate=trade_data.get('change_rate', 0),
                    success_rate=0,
                    avg_profit=0,
                    total_trades=0
                )

            old_total = pattern.total_trades
            new_total = old_total + 1

            pattern.avg_profit = (
                (pattern.avg_profit * old_total + pnl) / new_total
            )

            if pnl > 0:
                pattern.success_rate = (
                    (pattern.success_rate * old_total / 100 + 1) / new_total * 100
                )
            else:
                pattern.success_rate = (
                    (pattern.success_rate * old_total / 100) / new_total * 100
                )

            pattern.total_trades = new_total
            pattern.last_trade_date = datetime.now().isoformat()

            if pattern.success_rate >= 60 and pattern.avg_profit > 10000:
                self.success_patterns[stock_code] = pattern
                if stock_code in self.failure_patterns:
                    del self.failure_patterns[stock_code]
            elif pattern.success_rate <= 40 or pattern.avg_profit < -10000:
                self.failure_patterns[stock_code] = pattern
                if stock_code in self.success_patterns:
                    del self.success_patterns[stock_code]

            logger.debug(f"패턴 업데이트: {stock_name} (승률 {pattern.success_rate:.1f}%)")

        except Exception as e:
            logger.error(f"패턴 업데이트 실패: {e}")


__all__ = ['LearnedSelector', 'StockPattern']
