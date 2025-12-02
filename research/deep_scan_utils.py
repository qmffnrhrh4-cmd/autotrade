"""
research/deep_scan_utils.py
 Deep Scan 공통 유틸리티

모든 스캔 전략에서 사용하는 Deep Scan 로직을 공통화
"""
import time
from typing import List, Optional, Dict
from datetime import datetime

from utils.logger_new import get_logger
from research.scanner_pipeline import StockCandidate

logger = get_logger()

# Deep Scan 데이터 캐시 (메모리 기반)
_deep_scan_cache = {}
CACHE_TTL_SECONDS = 30  # 30초로 단축 (전략 분석용)


def _calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """RSI (Relative Strength Index) 계산"""
    if len(prices) < period + 1:
        return None

    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _calculate_macd(prices: List[float]) -> Optional[Dict[str, float]]:
    """MACD (Moving Average Convergence Divergence) 계산"""
    if len(prices) < 26:
        return None

    def ema(data: List[float], period: int) -> float:
        """지수 이동 평균"""
        multiplier = 2 / (period + 1)
        ema_value = sum(data[:period]) / period

        for price in data[period:]:
            ema_value = (price - ema_value) * multiplier + ema_value

        return ema_value

    ema12 = ema(prices, 12)
    ema26 = ema(prices, 26)
    macd_line = ema12 - ema26

    return {
        'macd': macd_line,
        'ema12': ema12,
        'ema26': ema26
    }


def _calculate_bollinger_bands(prices: List[float], period: int = 20) -> Optional[Dict[str, float]]:
    """볼린저 밴드 계산"""
    if len(prices) < period:
        return None

    import statistics

    recent_prices = prices[-period:]
    ma = sum(recent_prices) / period
    std_dev = statistics.stdev(recent_prices)

    upper_band = ma + (2 * std_dev)
    lower_band = ma - (2 * std_dev)

    current_price = prices[-1]
    bb_position = (current_price - lower_band) / (upper_band - lower_band) if upper_band != lower_band else 0.5

    return {
        'upper': upper_band,
        'middle': ma,
        'lower': lower_band,
        'position': bb_position  # 0~1 사이, 0.5가 중간
    }


def _get_from_cache(cache_key: str) -> Optional[Dict]:
    """캐시에서 데이터 조회"""
    global _deep_scan_cache

    if cache_key not in _deep_scan_cache:
        return None

    entry = _deep_scan_cache[cache_key]
    timestamp = entry['timestamp']

    # TTL 체크
    if (datetime.now() - timestamp).total_seconds() > CACHE_TTL_SECONDS:
        del _deep_scan_cache[cache_key]
        return None

    return entry['data']


def _save_to_cache(cache_key: str, data: Dict):
    """캐시에 데이터 저장"""
    global _deep_scan_cache

    _deep_scan_cache[cache_key] = {
        'data': data,
        'timestamp': datetime.now()
    }


def enrich_candidates_with_deep_scan(
    candidates: List[StockCandidate],
    market_api,
    max_candidates: int = 20,
    verbose: bool = True
) -> List[StockCandidate]:
    """
     모든 스캔 전략에서 사용하는 Deep Scan 공통 로직

    후보 종목들에 대해 상세 데이터를 조회하여 enrichment:
    1. 기관/외국인 매매 데이터 (ka10059)
    2. 호가 데이터 (ka10004)
    3. 기관매매추이 (ka10045)
    4. 일봉 데이터 - 평균거래량, 변동성 (ka10006)
    5. 증권사별 매매 (ka10078)
    6. 체결강도 (ka10047)
    7. 프로그램매매 (ka90013)

    Args:
        candidates: 후보 종목 리스트
        market_api: MarketAPI 인스턴스
        max_candidates: Deep Scan할 최대 종목 수
        verbose: 상세 로그 출력 여부

    Returns:
        enrichment된 후보 종목 리스트
    """
    if not candidates:
        return candidates

    if verbose:
        print(f"\n🔬 Deep Scan 실행 중 (상위 {min(len(candidates), max_candidates)}개)...")

    top_candidates = candidates[:max_candidates]

    for idx, candidate in enumerate(top_candidates, 1):
        try:
            if verbose:
                print(f"   [{idx}/{len(top_candidates)}] {candidate.name} ({candidate.code})")

            # 1. 기관/외국인 매매 데이터 조회 (ka10059)
            investor_data = market_api.get_investor_data(candidate.code)
            if investor_data:
                candidate.institutional_net_buy = investor_data.get('기관_순매수', 0)
                candidate.foreign_net_buy = investor_data.get('외국인_순매수', 0)
                if verbose:
                    print(f"      일별 - 기관={candidate.institutional_net_buy:,}, 외국인={candidate.foreign_net_buy:,}")
            else:
                candidate.institutional_net_buy = 0
                candidate.foreign_net_buy = 0

            # 2. 호가 데이터 조회 (ka10004)
            bid_ask_data = market_api.get_bid_ask(candidate.code)
            if bid_ask_data:
                bid_total = bid_ask_data.get('매수_총잔량', 1)
                ask_total = bid_ask_data.get('매도_총잔량', 1)
                candidate.bid_ask_ratio = bid_total / ask_total if ask_total > 0 else 0
                if verbose:
                    print(f"      호가비율={candidate.bid_ask_ratio:.2f}")
            else:
                candidate.bid_ask_ratio = 0

            # 3. 기관매매추이 조회 (ka10045) - 5일 트렌드
            trend_data = market_api.get_institutional_trading_trend(
                candidate.code,
                days=5,
                price_type='buy'
            )
            if trend_data:
                candidate.institutional_trend = trend_data
                if verbose:
                    print(f"      기관추이: 5일 데이터 수집")
            else:
                if verbose:
                    print(f"      기관추이: 데이터 없음")

            # 4. 일봉 데이터 조회 (ka10006) - 평균거래량 & 변동성
            daily_data = market_api.get_daily_chart(candidate.code, period=20)
            if daily_data and len(daily_data) > 1:
                # 평균 거래량 (20일)
                volumes = [d.get('volume', 0) for d in daily_data if d.get('volume')]
                if volumes:
                    candidate.avg_volume = sum(volumes) / len(volumes)
                    if verbose:
                        print(f"      일봉: 평균거래량={candidate.avg_volume:,.0f}")

                # 변동성 (20일 일별 등락률 표준편차)
                rates = []
                for d in daily_data:
                    close = d.get('close', 0)
                    open_price = d.get('open', 0)
                    if open_price and open_price > 0:
                        rate = (close - open_price) / open_price
                        rates.append(rate)

                if len(rates) > 1:
                    import statistics
                    candidate.volatility = statistics.stdev(rates)
                    if verbose:
                        print(f"      일봉: 변동성={candidate.volatility*100:.2f}%")

                #  기술적 지표 계산 (RSI, MACD, BB)
                closes = [d.get('close', 0) for d in daily_data if d.get('close')]
                if len(closes) >= 14:
                    # RSI 계산
                    candidate.rsi = _calculate_rsi(closes)
                    if verbose and candidate.rsi:
                        print(f"      기술: RSI={candidate.rsi:.1f}")

                    # MACD 계산
                    candidate.macd = _calculate_macd(closes)
                    if verbose and candidate.macd:
                        print(f"      기술: MACD={candidate.macd['macd']:.2f}")

                    # 볼린저 밴드 계산
                    candidate.bollinger_bands = _calculate_bollinger_bands(closes)
                    if verbose and candidate.bollinger_bands:
                        bb_pos = candidate.bollinger_bands['position']
                        bb_status = "상단" if bb_pos > 0.8 else "하단" if bb_pos < 0.2 else "중간"
                        print(f"      기술: BB위치={bb_status} ({bb_pos*100:.0f}%)")
                else:
                    candidate.rsi = None
                    candidate.macd = None
                    candidate.bollinger_bands = None
            else:
                if verbose:
                    print(f"      일봉: 데이터 없음")
                candidate.rsi = None
                candidate.macd = None
                candidate.bollinger_bands = None

            # 5. 증권사별매매 조회 (ka10078)
            major_firms = [
                ('001', '한국투자'),
                ('003', '미래에셋'),
                ('030', 'NH투자'),
                ('005', '삼성'),
                ('038', 'KB증권'),
            ]

            buy_count = 0
            total_net_buy = 0

            for firm_code, firm_name in major_firms:
                try:
                    firm_data = market_api.get_securities_firm_trading(
                        firm_code=firm_code,
                        stock_code=candidate.code,
                        days=5
                    )

                    if firm_data and len(firm_data) > 0:
                        latest = firm_data[0]
                        net_qty = latest.get('net_qty', 0)
                        if verbose:
                            print(f"         └ {firm_name}: net_qty={net_qty:,}주", end="")

                        if net_qty > 0:
                            buy_count += 1
                            total_net_buy += net_qty
                            if verbose:
                                print(f" ✅ 순매수")
                        elif net_qty < 0:
                            if verbose:
                                print(f" ⚠️ 순매도")
                        else:
                            if verbose:
                                print(f" - 변동없음")
                    else:
                        if verbose:
                            print(f"         └ {firm_name}: 데이터 없음")

                    time.sleep(0.05)

                except Exception as e:
                    if verbose:
                        print(f"         └ {firm_name}: 오류 - {e}")
                    continue

            candidate.top_broker_buy_count = buy_count
            candidate.top_broker_net_buy = total_net_buy

            if verbose:
                if buy_count > 0:
                    print(f"      증권사: 순매수증권사={buy_count}개, 순매수총량={total_net_buy:,}주")
                else:
                    print(f"      증권사: 순매수 없음")

            # 6. 체결강도 조회 (ka10047) - 캐시 우선
            cache_key_exec = f"execution_{candidate.code}"
            cached_exec = _get_from_cache(cache_key_exec)

            if cached_exec:
                candidate.execution_intensity = cached_exec.get('execution_intensity')
                if verbose:
                    if candidate.execution_intensity:
                        print(f"      체결강도={candidate.execution_intensity:.1f} [캐시]")
                    else:
                        print(f"      체결강도: 값 없음 [캐시]")
            else:
                execution_data = market_api.get_execution_intensity(candidate.code)
                if execution_data:
                    candidate.execution_intensity = execution_data.get('execution_intensity')
                    _save_to_cache(cache_key_exec, execution_data)
                    if verbose:
                        if candidate.execution_intensity:
                            print(f"      체결강도={candidate.execution_intensity:.1f}")
                        else:
                            print(f"      체결강도: 값 없음")
                else:
                    if verbose:
                        print(f"      체결강도: 데이터 없음")

            # 7. 프로그램매매 조회 (ka90013) - 캐시 우선
            cache_key_prog = f"program_{candidate.code}"
            cached_prog = _get_from_cache(cache_key_prog)

            if cached_prog:
                candidate.program_net_buy = cached_prog.get('program_net_buy')
                if verbose:
                    if candidate.program_net_buy:
                        print(f"      프로그램순매수={candidate.program_net_buy:,} [캐시]")
                    else:
                        print(f"      프로그램매매: 값 없음 [캐시]")
            else:
                program_data = market_api.get_program_trading(candidate.code)
                if program_data:
                    candidate.program_net_buy = program_data.get('program_net_buy')
                    _save_to_cache(cache_key_prog, program_data)
                    if verbose:
                        if candidate.program_net_buy:
                            print(f"      프로그램순매수={candidate.program_net_buy:,}")
                        else:
                            print(f"      프로그램매매: 값 없음")
                else:
                    if verbose:
                        print(f"      프로그램매매: 데이터 없음")

            time.sleep(0.1)  # API 호출 간격

        except Exception as e:
            logger.error(f"Deep Scan 오류 ({candidate.name}): {e}")
            if verbose:
                print(f"      오류: {e}")
            # 오류 시 기본값 설정
            candidate.institutional_net_buy = 0
            candidate.foreign_net_buy = 0
            candidate.bid_ask_ratio = 0
            candidate.avg_volume = None
            candidate.volatility = None
            candidate.top_broker_buy_count = 0
            candidate.top_broker_net_buy = 0
            candidate.execution_intensity = None
            candidate.program_net_buy = None
            candidate.rsi = None
            candidate.macd = None
            candidate.bollinger_bands = None
            continue

    if verbose:
        print(f"✅ Deep Scan 완료\n")

    return candidates
