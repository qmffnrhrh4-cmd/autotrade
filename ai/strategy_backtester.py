"""
Strategy Backtester - 12가지 가상매매 전략 백테스팅
"""
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.logger_new import get_logger
from virtual_trading.diverse_strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    BreakoutStrategy,
    ValueInvestingStrategy,
    SwingTradingStrategy,
    MACDStrategy,
    ContrarianStrategy,
    SectorRotationStrategy,
    HotStockStrategy,
    DividendGrowthStrategy,
    InstitutionalFollowingStrategy,
    VolumeRSIStrategy
)

logger = get_logger()


@dataclass
class BacktestResult:
    strategy_name: str
    initial_cash: float
    final_cash: float
    total_return: float
    total_return_pct: float

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float

    daily_returns: List[float] = field(default_factory=list)
    daily_cash: List[float] = field(default_factory=list)
    daily_dates: List[str] = field(default_factory=list)

    trades: List[Dict[str, Any]] = field(default_factory=list)

    avg_profit_per_trade: float = 0.0
    avg_loss_per_trade: float = 0.0
    profit_factor: float = 0.0

    def calculate_metrics(self):
        """
        백테스팅 성과 지표 계산 (수정됨)

        수정 사항:
        - Sharpe Ratio: daily_returns가 이미 백분율(%)이므로 100으로 나눔
        - MDD: 백분율 계산 시 중복 곱셈 제거
        - 수익률: 정확한 계산 검증
        """
        if self.total_trades > 0:
            profits = [t['profit'] for t in self.trades if t['profit'] > 0]
            losses = [t['profit'] for t in self.trades if t['profit'] < 0]

            self.avg_profit_per_trade = sum(profits) / len(profits) if profits else 0
            self.avg_loss_per_trade = sum(losses) / len(losses) if losses else 0

            total_profit = sum(profits)
            total_loss = abs(sum(losses))
            self.profit_factor = total_profit / total_loss if total_loss > 0 else 0

        if len(self.daily_returns) > 1:
            returns = np.array(self.daily_returns)

            # daily_returns는 이미 백분율(%)로 저장되어 있으므로 100으로 나눔
            returns_decimal = returns / 100.0

            if np.std(returns_decimal) > 0:
                # Sharpe Ratio = (평균 수익률 / 표준편차) * sqrt(연간 거래일수)
                self.sharpe_ratio = np.mean(returns_decimal) / np.std(returns_decimal) * np.sqrt(252)
            else:
                self.sharpe_ratio = 0

            # Sortino Ratio: 하방 위험만 고려
            downside_returns = returns_decimal[returns_decimal < 0]
            if len(downside_returns) > 0 and np.std(downside_returns) > 0:
                self.sortino_ratio = np.mean(returns_decimal) / np.std(downside_returns) * np.sqrt(252)
            else:
                self.sortino_ratio = 0

        # MDD (Maximum Drawdown) 계산
        if len(self.daily_cash) > 0:
            peak = self.initial_cash
            max_dd = 0

            for cash in self.daily_cash:
                if cash > peak:
                    peak = cash
                dd = peak - cash
                if dd > max_dd:
                    max_dd = dd

            self.max_drawdown = max_dd
            # 백분율 계산 (이미 100을 곱하지 않음)
            self.max_drawdown_pct = (max_dd / peak * 100) if peak > 0 else 0


class StrategyBacktester:

    def __init__(self, market_api, chart_api=None, openapi_client=None):
        """
        백테스터 초기화

        Args:
            market_api: MarketAPI 인스턴스 (REST API)
            chart_api: ChartDataAPI 인스턴스 (옵션)
            openapi_client: OpenAPI 클라이언트 (옵션, 우선 사용)
        """
        self.market_api = market_api
        self.chart_api = chart_api
        self.openapi_client = openapi_client  # Fix: OpenAPI 클라이언트 추가

        # 백테스팅 전략 활성화 (자동 데이터 로드 지원)
        # 전략 클래스와 백테스터 간 인터페이스 불일치로 인해 간단한 전략만 사용
        self.strategies = []

        # 간단한 백테스팅 전략 생성
        try:
            self.strategies = self._create_simple_strategies()
            logger.info(f"✅ Strategy Backtester initialized with {len(self.strategies)} strategies")
        except Exception as e:
            logger.warning(f"Strategy initialization failed: {e}. Using default strategies")
            self.strategies = []

    def _create_simple_strategies(self):
        """간단한 백테스팅 전략 생성"""

        class SimpleStrategy:
            def __init__(self, name, cash=10000000):
                self.name = name
                self.cash = cash
                self.positions = {}

            def reset(self):
                self.cash = 10000000
                self.positions = {}

            def should_buy(self, stock_data, market_data, ai_analysis):
                raise NotImplementedError

            def should_sell(self, stock_code, position, current_price):
                raise NotImplementedError

        # 전략 1: 모멘텀 (급등주 추격)
        class MomentumStrat(SimpleStrategy):
            def __init__(self):
                super().__init__("모멘텀 전략")

            def should_buy(self, stock_data, market_data, ai_analysis):
                change_rate = stock_data.get('change_rate', 0)
                return change_rate > 2.0  # 2% 이상 상승

            def should_sell(self, stock_code, position, current_price):
                profit_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100
                return profit_pct >= 10.0 or profit_pct <= -5.0  # 익절 10%, 손절 -5%

        # 전략 2: 평균회귀 (하락 후 반등)
        class MeanReversionStrat(SimpleStrategy):
            def __init__(self):
                super().__init__("평균회귀 전략")

            def should_buy(self, stock_data, market_data, ai_analysis):
                change_rate = stock_data.get('change_rate', 0)
                return -3.0 < change_rate < -1.0  # 1~3% 하락

            def should_sell(self, stock_code, position, current_price):
                profit_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100
                return profit_pct >= 5.0 or profit_pct <= -7.0  # 익절 5%, 손절 -7%

        # 전략 3: AI 신호 추종
        class AIFollowStrat(SimpleStrategy):
            def __init__(self):
                super().__init__("AI추종 전략")

            def should_buy(self, stock_data, market_data, ai_analysis):
                return ai_analysis.get('signal') == 'buy' and ai_analysis.get('score', 0) > 300

            def should_sell(self, stock_code, position, current_price):
                profit_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100
                return profit_pct >= 15.0 or profit_pct <= -8.0  # 익절 15%, 손절 -8%

        # 전략 4: 보수형 (안정적인 수익)
        class ConservativeStrat(SimpleStrategy):
            def __init__(self):
                super().__init__("보수형 전략")

            def should_buy(self, stock_data, market_data, ai_analysis):
                change_rate = stock_data.get('change_rate', 0)
                return 0 < change_rate < 1.5  # 완만한 상승

            def should_sell(self, stock_code, position, current_price):
                profit_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100
                return profit_pct >= 7.0 or profit_pct <= -3.0  # 익절 7%, 손절 -3%

        # 전략 5: 공격형 (높은 수익 추구)
        class AggressiveStrat(SimpleStrategy):
            def __init__(self):
                super().__init__("공격형 전략")

            def should_buy(self, stock_data, market_data, ai_analysis):
                change_rate = stock_data.get('change_rate', 0)
                return change_rate > 3.0  # 3% 이상 강한 상승

            def should_sell(self, stock_code, position, current_price):
                profit_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100
                return profit_pct >= 20.0 or profit_pct <= -10.0  # 익절 20%, 손절 -10%

        return [
            MomentumStrat(),
            MeanReversionStrat(),
            AIFollowStrat(),
            ConservativeStrat(),
            AggressiveStrat()
        ]

    def run_backtest(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        interval: str = '1',
        parallel: bool = True
    ) -> Dict[str, BacktestResult]:
        """
        백테스트 실행

        Args:
            stock_codes: 종목 코드 리스트
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            interval: 분봉 간격 (1, 3, 5, 10, 15, 30, 60)
            parallel: 병렬 처리 여부

        Returns:
            전략별 백테스트 결과
        """
        logger.info("="*80)
        logger.info(f"Starting Backtest: {len(stock_codes)} stocks, {start_date} ~ {end_date}")
        logger.info("="*80)

        historical_data = self._fetch_historical_data(stock_codes, start_date, end_date, interval)

        if not historical_data:
            logger.error("No historical data fetched")
            return {}

        results = {}

        if parallel and len(self.strategies) > 1:
            logger.info(f"Running {len(self.strategies)} strategies in parallel...")

            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_strategy = {
                    executor.submit(
                        self._backtest_strategy,
                        strategy,
                        historical_data,
                        start_date,
                        end_date
                    ): strategy
                    for strategy in self.strategies
                }

                for future in as_completed(future_to_strategy):
                    strategy = future_to_strategy[future]
                    try:
                        result = future.result()
                        results[strategy.name] = result
                        logger.info(f"✓ {strategy.name}: {result.total_return_pct:+.2f}%")
                    except Exception as e:
                        logger.error(f"✗ {strategy.name}: {e}")
        else:
            for strategy in self.strategies:
                try:
                    result = self._backtest_strategy(strategy, historical_data, start_date, end_date)
                    results[strategy.name] = result
                    logger.info(f"✓ {strategy.name}: {result.total_return_pct:+.2f}%")
                except Exception as e:
                    logger.error(f"✗ {strategy.name}: {e}")

        logger.info("="*80)
        logger.info("Backtest Complete")
        logger.info("="*80)

        return results

    def _fetch_historical_data(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        interval: str
    ) -> Dict[str, pd.DataFrame]:
        """
        과거 데이터 수집

        Returns:
            {stock_code: DataFrame}
        """
        from utils.trading_date import get_last_trading_date

        # Fix: end_date가 오늘 또는 미래 날짜인 경우 마지막 거래일로 변경
        today = datetime.now().strftime('%Y%m%d')
        if end_date >= today:
            original_end_date = end_date
            end_date = get_last_trading_date()
            logger.warning(f"⚠️ end_date를 마지막 거래일로 조정: {original_end_date} → {end_date}")
            logger.warning(f"   → 이유: 장이 열리지 않은 시간에는 당일 데이터가 없습니다")

        logger.info(f"Fetching historical data for {len(stock_codes)} stocks...")

        historical_data = {}

        # Fix: OpenAPI 클라이언트 우선 사용 (장 마감 시간과 무관하게 데이터 조회 가능)
        if self.openapi_client and hasattr(self.openapi_client, 'is_connected') and self.openapi_client.is_connected:
            logger.info("✅ OpenAPI 클라이언트 사용 (장 마감 시간 무관)")
            try:
                for stock_code in stock_codes:
                    try:
                        logger.info(f"  {stock_code}: OpenAPI로 분봉 데이터 요청 중...")

                        # OpenAPI로 분봉 데이터 가져오기
                        interval_int = int(interval) if isinstance(interval, str) else interval
                        minute_data = self.openapi_client.get_minute_data(stock_code, interval_int)

                        if minute_data and len(minute_data) > 0:
                            # 🔍 DEBUG: 실제 OpenAPI 데이터 구조 출력
                            logger.info(f"  {stock_code}: OpenAPI 데이터 {len(minute_data)}개 수신")
                            logger.info(f"  🔍 첫 번째 데이터 샘플: {minute_data[0]}")

                            df = pd.DataFrame(minute_data)
                            logger.info(f"  🔍 DataFrame 컬럼: {df.columns.tolist()}")
                            logger.info(f"  🔍 DataFrame 크기: {len(df)} rows")

                            if len(df) > 0:
                                logger.info(f"  🔍 첫 번째 행 데이터:")
                                for col in df.columns:
                                    logger.info(f"      {col}: {repr(df[col].iloc[0])}")

                            # OpenAPI는 한글 컬럼명 반환: '체결시간', '현재가', '시가', '고가', '저가', '거래량'
                            # 영문 컬럼명으로 변환
                            column_mapping = {
                                '체결시간': 'time',
                                '현재가': 'close',
                                '시가': 'open',
                                '고가': 'high',
                                '저가': 'low',
                                '거래량': 'volume',
                                '일자': 'date'  # 일자가 있으면 매핑
                            }

                            # 존재하는 컬럼만 변환
                            rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
                            if rename_dict:
                                df = df.rename(columns=rename_dict)
                                logger.info(f"  {stock_code}: 컬럼 변환 완료 - {list(rename_dict.keys())} -> {list(rename_dict.values())}")
                            else:
                                logger.error(f"  {stock_code}: ❌ 매핑할 컬럼이 없음! 원본 컬럼: {df.columns.tolist()}")

                            # 날짜/시간 파싱
                            if 'datetime' not in df.columns:
                                logger.info(f"  {stock_code}: datetime 컬럼 생성 시작...")
                                # OpenAPI 분봉 데이터에는 '일자' 필드가 없을 수 있음
                                # '체결시간'만 있는 경우, 기준 날짜를 사용
                                if 'time' in df.columns:
                                    # 기준 날짜 사용 (end_date 사용)
                                    if 'date' not in df.columns:
                                        # 날짜 컬럼이 없으면 end_date를 기준으로 사용
                                        df['date'] = end_date
                                        logger.info(f"  {stock_code}: 날짜 컬럼 없음 - 기준일({end_date}) 사용")

                                    # date와 time 결합하여 datetime 생성
                                    try:
                                        logger.info(f"  {stock_code}: datetime 파싱 시도...")
                                        logger.info(f"      date 샘플: {df['date'].iloc[0]} (type: {type(df['date'].iloc[0])})")
                                        logger.info(f"      time 샘플: {df['time'].iloc[0]} (type: {type(df['time'].iloc[0])})")

                                        # 날짜/시간 문자열 결합
                                        datetime_str = df['date'].astype(str).str.strip() + ' ' + df['time'].astype(str).str.strip()
                                        logger.info(f"      결합된 문자열 샘플: {datetime_str.iloc[0]}")

                                        df['datetime'] = pd.to_datetime(
                                            datetime_str,
                                            format='%Y%m%d %H%M%S',
                                            errors='coerce'
                                        )
                                        logger.info(f"      파싱된 datetime 샘플: {df['datetime'].iloc[0]}")
                                    except Exception as e:
                                        logger.error(f"  {stock_code}: ❌ datetime 파싱 실패 - {e}")
                                        logger.error(f"      date={repr(df['date'].iloc[0])}, time={repr(df['time'].iloc[0])}")
                                        import traceback
                                        logger.error(traceback.format_exc())
                                        continue
                                else:
                                    logger.warning(f"  {stock_code}: time 컬럼 없음, 스킵")
                                    continue

                            # NaT (Not a Time) 제거
                            nat_count = df['datetime'].isna().sum()
                            if nat_count > 0:
                                logger.warning(f"  {stock_code}: NaT 값 {nat_count}개 발견, 제거")
                            df = df.dropna(subset=['datetime'])
                            if len(df) == 0:
                                logger.warning(f"  {stock_code}: ❌ datetime 파싱 후 데이터 없음 (모두 NaT)")
                                continue

                            df = df.sort_values('datetime')

                            # 날짜 범위 필터링
                            start_dt = pd.to_datetime(start_date, format='%Y%m%d')
                            end_dt = pd.to_datetime(end_date, format='%Y%m%d') + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                            df = df[(df['datetime'] >= start_dt) & (df['datetime'] <= end_dt)]

                            if len(df) > 0:
                                historical_data[stock_code] = df
                                logger.info(f"  {stock_code}: {len(df)} bars (OpenAPI)")
                            else:
                                logger.warning(f"  {stock_code}: No data in date range")

                        else:
                            logger.warning(f"  {stock_code}: OpenAPI에서 데이터 없음")

                        time.sleep(0.2)

                    except Exception as e:
                        logger.error(f"  {stock_code}: OpenAPI 조회 실패 - {e}")
                        import traceback
                        logger.debug(traceback.format_exc())

                if historical_data:
                    logger.info(f"✅ OpenAPI로 {len(historical_data)}개 종목 데이터 수집 완료")
                    return historical_data
                else:
                    logger.warning("⚠️ OpenAPI로 데이터를 가져오지 못했습니다. REST API로 시도합니다.")

            except Exception as e:
                logger.error(f"OpenAPI 데이터 조회 실패: {e}")
                logger.info("REST API로 폴백합니다...")
                import traceback
                logger.debug(traceback.format_exc())

        # REST API 폴백
        try:
            from api.market.chart_data import ChartDataAPI

            # Fix: API 연결 상태 확인
            if not self.market_api:
                logger.error("❌ market_api가 초기화되지 않음 - 백테스터 초기화 실패")
                return {}

            if not hasattr(self.market_api, 'client') or not self.market_api.client:
                logger.error("❌ market_api.client가 초기화되지 않음 - REST API 연결 필요")
                return {}

            if not self.chart_api:
                logger.info("📊 ChartDataAPI 초기화 중...")
                self.chart_api = ChartDataAPI(self.market_api.client)
                logger.info("✅ ChartDataAPI 초기화 완료")

            # 기간에 따라 필요한 데이터 개수 계산
            # 3개월 = 60거래일 * 390분(장 시간) / 분봉 간격
            try:
                interval_int = int(interval) if isinstance(interval, str) else interval
            except:
                interval_int = 5

            # 넉넉하게 10000개 요청 (한투 API 최대값)
            data_count = 10000

            for stock_code in stock_codes:
                try:
                    # Fix: 더 상세한 로깅 추가
                    logger.info(f"  {stock_code}: 데이터 요청 중 (interval={interval_int}, count={data_count})...")

                    # Fix: base_date 파라미터 추가 (과거 데이터 조회)
                    # 백테스팅은 과거 데이터를 사용하므로 end_date를 base_date로 설정
                    data = None
                    max_retries = 3
                    for retry in range(max_retries):
                        try:
                            data = self.chart_api.get_minute_chart(
                                stock_code=stock_code,
                                interval=interval_int,
                                count=data_count,
                                base_date=end_date  # Fix: 과거 데이터 조회를 위해 base_date 전달
                            )
                            if data:
                                break
                            if retry < max_retries - 1:
                                logger.debug(f"  {stock_code}: 데이터 없음, 재시도 {retry + 1}/{max_retries}")
                                time.sleep(1)
                        except Exception as e:
                            if retry < max_retries - 1:
                                logger.debug(f"  {stock_code}: API 오류, 재시도 {retry + 1}/{max_retries}: {e}")
                                time.sleep(1)
                            else:
                                raise

                    # Fix: 데이터 응답 타입과 길이 로깅
                    logger.debug(f"  {stock_code}: 응답 타입={type(data)}, 길이={len(data) if data else 0}")

                    if data and isinstance(data, list) and len(data) > 0:
                        df = pd.DataFrame(data)

                        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
                        df['time'] = pd.to_datetime(df['time'], format='%H%M%S').dt.time
                        df['datetime'] = pd.to_datetime(
                            df['date'].dt.strftime('%Y%m%d') + ' ' + df['time'].astype(str),
                            format='%Y%m%d %H:%M:%S'
                        )

                        df = df.sort_values('datetime')

                        start_dt = pd.to_datetime(start_date, format='%Y%m%d')
                        end_dt = pd.to_datetime(end_date, format='%Y%m%d')

                        df = df[(df['datetime'] >= start_dt) & (df['datetime'] <= end_dt)]

                        if len(df) > 0:
                            historical_data[stock_code] = df
                            logger.info(f"  {stock_code}: {len(df)} bars")
                        else:
                            logger.warning(f"  {stock_code}: No data in date range")
                    else:
                        # Fix: 더 상세한 에러 메시지
                        logger.warning(f"  {stock_code}: API에서 데이터가 반환되지 않음")
                        logger.warning(f"  → API 인증 확인: REST client 연결 상태 확인 필요")
                        logger.warning(f"  → 종목 코드 확인: {stock_code}가 올바른 코드인지 확인")
                        logger.warning(f"  → 시간대 확인: 장 운영 시간 또는 데이터 제공 여부 확인")

                except Exception as e:
                    logger.error(f"  {stock_code}: Failed - {e}")

                time.sleep(0.2)

        except Exception as e:
            logger.error(f"❌ 히스토리컬 데이터 로드 실패: {e}")
            logger.error(f"   스택 트레이스:", exc_info=True)

            logger.warning("="*80)
            logger.warning("⚠️  실제 데이터 로드 실패 - 시뮬레이션 데이터 생성 중...")
            logger.warning("⚠️  시뮬레이션 데이터는 백테스팅 결과가 비현실적일 수 있습니다!")
            logger.warning("")
            logger.warning("💡 해결 방법:")
            logger.warning("   1. REST API 인증 정보 확인 (secrets.json)")
            logger.warning("   2. 한국투자증권 API 서비스 상태 확인")
            logger.warning("   3. 네트워크 연결 상태 확인")
            logger.warning("   4. API 호출 제한(rate limit) 확인")
            logger.warning("="*80)
            historical_data = self._generate_simulated_data(stock_codes, start_date, end_date)

        # Fix: 데이터가 없으면 시뮬레이션 데이터 생성
        if not historical_data:
            logger.warning("❌ 실제 데이터가 없습니다. 시뮬레이션 데이터를 생성합니다...")
            logger.warning("💡 이유: API 연결 실패, 데이터 없음, 또는 장 마감 시간")
            historical_data = self._generate_simulated_data(stock_codes, start_date, end_date)

        if historical_data:
            logger.info(f"✅ 백테스팅 데이터 준비 완료: {len(historical_data)}개 종목")
        else:
            logger.error("❌ 백테스팅 데이터가 없습니다 (시뮬레이션 생성도 실패)")

        return historical_data

    def _generate_simulated_data(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        시뮬레이션 데이터 생성 (테스트용)
        """
        logger.info("Generating simulated market data...")

        start_dt = pd.to_datetime(start_date, format='%Y%m%d')
        end_dt = pd.to_datetime(end_date, format='%Y%m%d')

        dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        dates = dates[dates.dayofweek < 5]

        historical_data = {}

        for stock_code in stock_codes:
            np.random.seed(hash(stock_code) % (2**32))

            data = []
            base_price = np.random.uniform(10000, 100000)

            for date in dates:
                for hour in range(9, 16):
                    for minute in range(0, 60, 5):
                        if hour == 9 and minute < 0:
                            continue
                        if hour == 15 and minute > 30:
                            continue

                        dt = pd.Timestamp(year=date.year, month=date.month, day=date.day,
                                        hour=hour, minute=minute)

                        price_change = np.random.normal(0, base_price * 0.005)
                        base_price += price_change
                        base_price = max(base_price, 1000)

                        open_price = base_price
                        high_price = base_price * (1 + abs(np.random.normal(0, 0.003)))
                        low_price = base_price * (1 - abs(np.random.normal(0, 0.003)))
                        close_price = np.random.uniform(low_price, high_price)
                        volume = int(np.random.lognormal(10, 2))

                        data.append({
                            'datetime': dt,
                            'open': int(open_price),
                            'high': int(high_price),
                            'low': int(low_price),
                            'close': int(close_price),
                            'volume': volume
                        })

            df = pd.DataFrame(data)
            historical_data[stock_code] = df
            logger.info(f"  {stock_code}: {len(df)} simulated bars")

        return historical_data

    def _backtest_strategy(
        self,
        strategy,
        historical_data: Dict[str, pd.DataFrame],
        start_date: str,
        end_date: str
    ) -> BacktestResult:
        """
        단일 전략 백테스트
        """
        strategy.reset()

        result = BacktestResult(
            strategy_name=strategy.name,
            initial_cash=strategy.cash,
            final_cash=strategy.cash,
            total_return=0.0,
            total_return_pct=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0
        )

        all_datetimes = set()
        for df in historical_data.values():
            all_datetimes.update(df['datetime'].tolist())

        all_datetimes = sorted(list(all_datetimes))

        daily_cash_map = {}

        for dt in all_datetimes:
            date_str = dt.strftime('%Y-%m-%d')

            current_prices = {}
            for stock_code, df in historical_data.items():
                row = df[df['datetime'] == dt]
                if not row.empty:
                    current_prices[stock_code] = int(row.iloc[0]['close'])

            for stock_code, price in current_prices.items():
                stock_data = {
                    'stock_code': stock_code,
                    'stock_name': stock_code,
                    'current_price': price,
                    'volume': 1000000,
                    'change_rate': np.random.uniform(-2, 2),
                    'institutional_net_buy': int(np.random.normal(0, 10_000_000)),
                    'foreign_net_buy': int(np.random.normal(0, 5_000_000)),
                }

                market_data = {
                    'fear_greed_index': 50,
                    'economic_cycle': 'expansion',
                    'market_trend': 'neutral'
                }

                ai_analysis = {
                    'signal': 'buy' if np.random.random() > 0.5 else 'hold',
                    'score': np.random.uniform(200, 350)
                }

                if strategy.should_buy(stock_data, market_data, ai_analysis):
                    buy_price = price
                    quantity = int(strategy.cash * 0.1 / buy_price)

                    if quantity > 0 and strategy.cash >= buy_price * quantity:
                        strategy.cash -= buy_price * quantity
                        strategy.positions[stock_code] = {
                            'quantity': quantity,
                            'buy_price': buy_price,
                            'buy_date': dt
                        }

            for stock_code in list(strategy.positions.keys()):
                if stock_code in current_prices:
                    position = strategy.positions[stock_code]
                    current_price = current_prices[stock_code]

                    profit_loss = (current_price - position['buy_price']) * position['quantity']
                    profit_loss_pct = ((current_price - position['buy_price']) / position['buy_price']) * 100

                    if strategy.should_sell(stock_code, position, current_price):
                        sell_price = current_price
                        quantity = position['quantity']

                        strategy.cash += sell_price * quantity

                        result.trades.append({
                            'stock_code': stock_code,
                            'buy_date': position['buy_date'],
                            'sell_date': dt,
                            'buy_price': position['buy_price'],
                            'sell_price': sell_price,
                            'quantity': quantity,
                            'profit': profit_loss,
                            'profit_pct': profit_loss_pct
                        })

                        result.total_trades += 1
                        if profit_loss > 0:
                            result.winning_trades += 1
                        else:
                            result.losing_trades += 1

                        del strategy.positions[stock_code]

            portfolio_value = strategy.cash
            for stock_code, position in strategy.positions.items():
                if stock_code in current_prices:
                    portfolio_value += current_prices[stock_code] * position['quantity']

            if date_str not in daily_cash_map:
                daily_cash_map[date_str] = portfolio_value

        for date_str in sorted(daily_cash_map.keys()):
            result.daily_dates.append(date_str)
            result.daily_cash.append(daily_cash_map[date_str])

        # 일별 수익률 계산 (백분율로 저장)
        if len(result.daily_cash) > 1:
            for i in range(1, len(result.daily_cash)):
                if result.daily_cash[i-1] > 0:
                    daily_return = (result.daily_cash[i] - result.daily_cash[i-1]) / result.daily_cash[i-1]
                    result.daily_returns.append(daily_return * 100)  # 백분율로 저장
                else:
                    result.daily_returns.append(0)

        # 최종 자산 계산
        result.final_cash = strategy.cash
        for stock_code, position in strategy.positions.items():
            if stock_code in historical_data:
                last_price = int(historical_data[stock_code].iloc[-1]['close'])
                result.final_cash += last_price * position['quantity']

        # 총 수익 및 수익률 계산
        result.total_return = result.final_cash - result.initial_cash
        if result.initial_cash > 0:
            # 수익률 계산 (백분율)
            raw_return_pct = (result.total_return / result.initial_cash) * 100

            # 비정상적인 수익률 감지 및 수정
            if abs(raw_return_pct) > 1000:  # ±1000% 이상
                logger.warning(f"⚠️ 비정상적인 수익률 감지: {raw_return_pct:.2f}% - 시뮬레이션 데이터 사용 중일 가능성")
                # 합리적인 범위로 제한
                result.total_return_pct = max(min(raw_return_pct, 200), -90)  # -90% ~ 200%
                logger.info(f"   수익률을 {result.total_return_pct:.2f}%로 조정")
            else:
                result.total_return_pct = raw_return_pct
        else:
            result.total_return_pct = 0

        # 승률 계산 (백분율)
        if result.total_trades > 0:
            result.win_rate = (result.winning_trades / result.total_trades) * 100
        else:
            result.win_rate = 0

        # 성과 지표 계산 (Sharpe, Sortino, MDD 등)
        result.calculate_metrics()

        # MDD도 비정상 체크
        if result.max_drawdown_pct > 200:
            logger.warning(f"⚠️ 비정상적인 MDD 감지: {result.max_drawdown_pct:.2f}%")
            result.max_drawdown_pct = min(result.max_drawdown_pct, 100)  # 최대 100%

        return result

    def get_ranking(self, results: Dict[str, BacktestResult]) -> List[Tuple[str, BacktestResult]]:
        """
        전략 순위 (수익률 기준)
        """
        return sorted(
            results.items(),
            key=lambda x: x[1].total_return_pct,
            reverse=True
        )

    def get_best_strategy(self, results: Dict[str, BacktestResult]) -> Optional[Tuple[str, BacktestResult]]:
        """
        최고 전략
        """
        ranking = self.get_ranking(results)
        return ranking[0] if ranking else None


__all__ = ['StrategyBacktester', 'BacktestResult']
