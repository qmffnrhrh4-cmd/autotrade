"""
NXT 실시간 현재가 처리 모듈 - v5.15
NXT 시장 시간대(15:30~20:00)의 실시간 현재가 정확한 반영
"""
from datetime import datetime, time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class NXTRealtimePriceManager:
    """
    NXT 실시간 현재가 관리자

    문제: NXT 시간대(15:30~20:00)에 종가를 사용하여 실시간 가격 변동 반영 안됨
    해결: NXT 시간대에 실시간 현재가 API 호출로 변경
    """

    def __init__(self, market_api):
        """
        Args:
            market_api: MarketAPI 인스턴스
        """
        self.market_api = market_api
        self.price_cache = {}  # 캐시 (5초 TTL)
        self.cache_ttl_seconds = 5

    def is_nxt_trading_hours(self) -> bool:
        """
        NXT 거래 시간 확인

        오전: 08:00 ~ 09:00
        오후: 15:30 ~ 20:00 (실제 거래는 18:00까지지만 여유있게)

        Returns:
            bool: NXT 거래 시간 여부
        """
        now = datetime.now().time()

        # 오전 NXT: 08:00 ~ 09:00
        morning_start = time(8, 0)
        morning_end = time(9, 0)

        # 오후 NXT: 15:30 ~ 20:00
        afternoon_start = time(15, 30)
        afternoon_end = time(20, 0)

        is_morning = morning_start <= now < morning_end
        is_afternoon = afternoon_start <= now <= afternoon_end

        return is_morning or is_afternoon

    def get_realtime_price(self, stock_code: str,
                          force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        실시간 현재가 조회

        ⚠️ 중요 발견 (v5.15 테스트 결과):
        - NXT 시간대에도 _NX 접미사 사용하면 실패 (0% 성공률)
        - 기본 코드로 조회하면 정상 작동 (100% 성공률)
        - ka10003, ka10004 모두 기본 코드 사용

        Args:
            stock_code: 종목코드 (예: "249420")
            force_refresh: 캐시 무시하고 강제 조회

        Returns:
            {
                'current_price': int,
                'source': str,
                'timestamp': str,
                'is_nxt_hours': bool
            }
        """
        is_nxt = self.is_nxt_trading_hours()

        # _NX 접미사 제거 (테스트 결과: _NX는 항상 실패)
        base_code = stock_code[:-3] if stock_code.endswith('_NX') else stock_code

        # 캐시 확인
        if not force_refresh:
            cached = self._get_from_cache(base_code)
            if cached:
                cached['source'] = 'cache'
                return cached

        try:
            # ✅ 핵심: NXT 시간대에도 기본 코드로 조회 (테스트로 검증됨)
            result = self.market_api.get_stock_price(base_code)

            if result and result.get('current_price', 0) > 0:
                price_data = {
                    'current_price': int(result.get('current_price', 0)),
                    'source': 'nxt_realtime' if is_nxt else 'regular_market',
                    'timestamp': datetime.now().isoformat(),
                    'is_nxt_hours': is_nxt,
                    'volume': int(result.get('volume', 0)),
                    'change_rate': float(result.get('change_rate', 0))
                }

                # 캐시 저장
                self._save_to_cache(base_code, price_data)

                if is_nxt:
                    logger.debug(f"✓ {base_code} NXT 현재가: {price_data['current_price']:,}원")

                return price_data

            logger.error(f"{base_code} 현재가 조회 실패")
            return None

        except Exception as e:
            logger.error(f"{base_code} 현재가 조회 오류: {e}")
            return None

    def get_multiple_prices(self, stock_codes: list) -> Dict[str, Dict[str, Any]]:
        """
        여러 종목 실시간 현재가 일괄 조회

        Args:
            stock_codes: 종목코드 리스트

        Returns:
            {stock_code: price_data} 딕셔너리
        """
        results = {}

        for stock_code in stock_codes:
            price_data = self.get_realtime_price(stock_code)
            if price_data:
                results[stock_code] = price_data

        logger.info(f"일괄 조회 완료: {len(results)}/{len(stock_codes)} 성공")
        return results

    def _get_from_cache(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """캐시에서 가격 조회"""
        if stock_code not in self.price_cache:
            return None

        cached_data, cached_time = self.price_cache[stock_code]

        # TTL 확인
        age = (datetime.now() - cached_time).total_seconds()
        if age > self.cache_ttl_seconds:
            del self.price_cache[stock_code]
            return None

        return cached_data

    def _save_to_cache(self, stock_code: str, price_data: Dict[str, Any]):
        """캐시에 가격 저장"""
        self.price_cache[stock_code] = (price_data, datetime.now())

    def clear_cache(self):
        """캐시 전체 삭제"""
        self.price_cache.clear()
        logger.info("가격 캐시 삭제됨")


def get_current_price_fixed(market_api, stock_code: str,
                           use_chart_close: bool = False) -> int:
    """
    현재가 조회 (NXT 시간대 수정 버전)

    ⚠️ 중요: NXT 시간대(15:30~20:00)에는 차트 종가가 아닌 실시간 현재가 사용

    Args:
        market_api: MarketAPI 인스턴스
        stock_code: 종목코드
        use_chart_close: 차트 종가 사용 여부 (기본값: False)

    Returns:
        현재가 (int)
    """
    manager = NXTRealtimePriceManager(market_api)

    # NXT 시간대 확인
    is_nxt = manager.is_nxt_trading_hours()

    # NXT 시간대에는 무조건 실시간 현재가 사용
    if is_nxt and not use_chart_close:
        price_data = manager.get_realtime_price(stock_code)
        if price_data:
            return price_data['current_price']

    # 일반 현재가 조회
    result = market_api.get_stock_price(stock_code)
    if result and result.get('current_price', 0) > 0:
        return int(result.get('current_price', 0))

    # 모두 실패시 0 반환
    logger.warning(f"{stock_code} 현재가 조회 실패 - 0 반환")
    return 0


def patch_chart_current_price(chart_data: list, market_api, stock_code: str) -> list:
    """
    차트 데이터의 마지막 현재가 패치

    문제: 차트의 마지막 캔들 종가(close)를 현재가로 사용
    해결: NXT 시간대에는 실시간 현재가로 마지막 캔들 업데이트

    Args:
        chart_data: 차트 데이터 리스트
        market_api: MarketAPI 인스턴스
        stock_code: 종목코드

    Returns:
        업데이트된 차트 데이터
    """
    if not chart_data:
        return chart_data

    manager = NXTRealtimePriceManager(market_api)

    # NXT 시간대 확인
    if not manager.is_nxt_trading_hours():
        return chart_data  # NXT 시간이 아니면 그대로 반환

    # 실시간 현재가 조회
    price_data = manager.get_realtime_price(stock_code)

    if not price_data:
        return chart_data  # 조회 실패시 그대로 반환

    # 마지막 캔들 업데이트
    last_candle = chart_data[-1]
    current_price = price_data['current_price']

    # close 가격 업데이트
    original_close = last_candle.get('close', 0)
    last_candle['close'] = current_price

    # high/low 조정
    if current_price > last_candle.get('high', current_price):
        last_candle['high'] = current_price
    if current_price < last_candle.get('low', current_price):
        last_candle['low'] = current_price

    logger.info(f"NXT 차트 현재가 업데이트: {stock_code} "
               f"{original_close:,} → {current_price:,}원")

    return chart_data


def is_price_stale(timestamp_str: str, max_age_seconds: int = 60) -> bool:
    """
    가격 데이터가 오래되었는지 확인

    Args:
        timestamp_str: ISO format timestamp
        max_age_seconds: 최대 허용 시간 (초)

    Returns:
        bool: 오래되었으면 True
    """
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        age = (datetime.now() - timestamp).total_seconds()
        return age > max_age_seconds
    except (ValueError, TypeError, AttributeError):
        return True  # 파싱 실패시 오래된 것으로 간주


# Global singleton
_nxt_price_manager: Optional[NXTRealtimePriceManager] = None


def get_nxt_price_manager(market_api) -> NXTRealtimePriceManager:
    """NXT 실시간 가격 관리자 싱글톤"""
    global _nxt_price_manager
    if _nxt_price_manager is None or _nxt_price_manager.market_api != market_api:
        _nxt_price_manager = NXTRealtimePriceManager(market_api)
    return _nxt_price_manager
