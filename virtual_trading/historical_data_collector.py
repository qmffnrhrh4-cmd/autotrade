"""
Historical Data Collector for Evolution & Backtesting
OPEN API를 통한 실제 히스토리컬 데이터 수집

이 모듈이 없으면 진화/백테스팅이 가상 데이터로만 작동함 (CRITICAL!)
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time
import pandas as pd

logger = logging.getLogger(__name__)


class HistoricalDataCollector:
    """
    OPEN API 히스토리컬 데이터 수집기

    진화 알고리즘과 백테스팅에서 실제 시장 데이터를 사용하도록 함
    """

    def __init__(self, data_fetcher):
        """
        Args:
            data_fetcher: DataFetcher 인스턴스 (OPEN API 접근)
        """
        self.data_fetcher = data_fetcher
        self.cache = {}  # 데이터 캐시 {stock_code: {date_range: DataFrame}}

    def collect_for_backtesting(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        include_indicators: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        백테스팅용 히스토리컬 데이터 수집

        Args:
            stock_codes: 종목 코드 리스트
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            include_indicators: 기술적 지표 포함 여부

        Returns:
            {stock_code: DataFrame} 형식의 딕셔너리
            DataFrame columns: date, open, high, low, close, volume, [indicators...]
        """
        logger.info(f"")
        logger.info(f"📊 OPEN API 히스토리컬 데이터 수집 시작")
        logger.info(f"   종목: {len(stock_codes)}개")
        logger.info(f"   기간: {start_date} ~ {end_date}")
        logger.info(f"")

        collected_data = {}
        failed_stocks = []

        for idx, stock_code in enumerate(stock_codes):
            try:
                logger.info(f"[{idx+1}/{len(stock_codes)}] {stock_code} 데이터 수집 중...")

                # OPEN API 호출
                data = self.data_fetcher.get_daily_price(
                    stock_code=stock_code,
                    start_date=start_date,
                    end_date=end_date
                )

                if not data or len(data) == 0:
                    logger.warning(f"  ⚠️ {stock_code}: 데이터 없음")
                    failed_stocks.append(stock_code)
                    continue

                # DataFrame 변환
                df = self._convert_to_dataframe(data)

                if df is None or len(df) == 0:
                    logger.warning(f"  ⚠️ {stock_code}: DataFrame 변환 실패")
                    failed_stocks.append(stock_code)
                    continue

                # 기술적 지표 계산
                if include_indicators:
                    df = self._calculate_indicators(df)

                collected_data[stock_code] = df
                logger.info(f"  ✅ {stock_code}: {len(df)}일 데이터 수집 완료")

                # API 호출 제한 고려 (0.1초 대기)
                if idx < len(stock_codes) - 1:
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"  ❌ {stock_code} 데이터 수집 실패: {e}")
                failed_stocks.append(stock_code)

        logger.info(f"")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"✅ 히스토리컬 데이터 수집 완료")
        logger.info(f"   성공: {len(collected_data)}개")
        logger.info(f"   실패: {len(failed_stocks)}개")
        if failed_stocks:
            logger.info(f"   실패 종목: {', '.join(failed_stocks[:5])}...")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"")

        return collected_data

    def collect_for_strategy_evaluation(
        self,
        stock_codes: List[str],
        days: int = 30
    ) -> Dict[str, pd.DataFrame]:
        """
        전략 평가용 최근 N일 데이터 수집

        Args:
            stock_codes: 종목 코드 리스트
            days: 수집할 일수 (기본 30일)

        Returns:
            {stock_code: DataFrame} 형식의 딕셔너리
        """
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        return self.collect_for_backtesting(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            include_indicators=True
        )

    def _convert_to_dataframe(self, data: List[Dict]) -> Optional[pd.DataFrame]:
        """
        OPEN API 응답을 DataFrame으로 변환

        Args:
            data: OPEN API 응답 데이터

        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            if not data:
                return None

            # 데이터 형식 확인 및 변환
            records = []
            for item in data:
                # OPEN API 응답 형식에 따라 키 이름 다를 수 있음
                date = item.get('stck_bsop_date') or item.get('date')
                open_price = float(item.get('stck_oprc') or item.get('open') or 0)
                high_price = float(item.get('stck_hgpr') or item.get('high') or 0)
                low_price = float(item.get('stck_lwpr') or item.get('low') or 0)
                close_price = float(item.get('stck_clpr') or item.get('close') or 0)
                volume = int(item.get('acml_vol') or item.get('volume') or 0)

                if not date or close_price == 0:
                    continue

                records.append({
                    'date': date,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })

            if not records:
                return None

            df = pd.DataFrame(records)
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df = df.sort_values('date').reset_index(drop=True)

            return df

        except Exception as e:
            logger.error(f"DataFrame 변환 오류: {e}")
            return None

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        기술적 지표 계산

        Args:
            df: OHLCV DataFrame

        Returns:
            지표가 추가된 DataFrame
        """
        try:
            # RSI
            df['rsi'] = self._calculate_rsi(df['close'], period=14)

            # 이동평균선
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma60'] = df['close'].rolling(window=60).mean()

            # 볼린저 밴드
            bb_middle = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = bb_middle + (bb_std * 2)
            df['bb_lower'] = bb_middle - (bb_std * 2)
            df['bb_middle'] = bb_middle

            # MACD
            ema12 = df['close'].ewm(span=12, adjust=False).mean()
            ema26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema12 - ema26
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']

            # 거래량 비율
            df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()

            return df

        except Exception as e:
            logger.error(f"지표 계산 오류: {e}")
            return df

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI 계산"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            return rsi

        except Exception as e:
            logger.error(f"RSI 계산 오류: {e}")
            return pd.Series([50] * len(prices))

    def get_market_data_for_date_range(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        특정 종목의 특정 기간 데이터 조회 (캐시 활용)

        Args:
            stock_code: 종목코드
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)

        Returns:
            DataFrame
        """
        cache_key = f"{stock_code}_{start_date}_{end_date}"

        # 캐시 확인
        if cache_key in self.cache:
            logger.debug(f"캐시 히트: {cache_key}")
            return self.cache[cache_key]

        # 데이터 수집
        data = self.collect_for_backtesting(
            stock_codes=[stock_code],
            start_date=start_date,
            end_date=end_date,
            include_indicators=True
        )

        if stock_code in data:
            self.cache[cache_key] = data[stock_code]
            return data[stock_code]

        return None


# Singleton
_historical_data_collector = None


def get_historical_data_collector(data_fetcher=None) -> Optional[HistoricalDataCollector]:
    """히스토리컬 데이터 수집기 싱글톤"""
    global _historical_data_collector

    if _historical_data_collector is None and data_fetcher:
        _historical_data_collector = HistoricalDataCollector(data_fetcher)
        logger.info("✅ HistoricalDataCollector 초기화 완료")

    return _historical_data_collector


__all__ = ['HistoricalDataCollector', 'get_historical_data_collector']
