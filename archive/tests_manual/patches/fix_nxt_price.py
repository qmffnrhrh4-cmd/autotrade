"""
NXT 시장가격 조회 수정 패치
문제: NXT 시간에도 주식의 현재가 조회가 가능해야 함
해결: 시간대별로 적절한 API 호출

다양한 접근법:
1. approach_1: 시간 체크 후 적절한 API 호출
2. approach_2: NXT 전용 API 사용
3. approach_3: 보유종목의 현재가 활용
4. approach_4: 여러 소스 시도 (fallback)
"""

from typing import Dict, Any, Optional
from datetime import datetime, time


class NXTPriceFix:
    """NXT 시장가격 조회 수정"""

    @staticmethod
    def is_nxt_time() -> bool:
        """
        NXT 시간외 거래 시간인지 확인

        시간외 단일가:
        - 오전: 08:00 ~ 09:00
        - 오후: 15:30 ~ 20:00 (실제는 18:00까지지만 여유있게)
        """
        now = datetime.now().time()

        # 오전 시간외: 08:00 ~ 09:00
        morning_nxt_start = time(8, 0)
        morning_nxt_end = time(9, 0)

        # 오후 시간외: 15:30 ~ 20:00
        afternoon_nxt_start = time(15, 30)
        afternoon_nxt_end = time(20, 0)

        is_morning_nxt = morning_nxt_start <= now < morning_nxt_end
        is_afternoon_nxt = afternoon_nxt_start <= now <= afternoon_nxt_end

        return is_morning_nxt or is_afternoon_nxt

    @staticmethod
    def is_regular_market_time() -> bool:
        """
        정규시장 시간인지 확인

        정규시장: 09:00 ~ 15:30
        """
        now = datetime.now().time()

        # 정규시장: 09:00 ~ 15:30
        market_start = time(9, 0)
        market_close = time(15, 30)

        return market_start <= now < market_close

    @staticmethod
    def approach_1_time_aware_api(market_api, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        접근법 1: 시간대별 적절한 API 호출

        - 정규시장: ka10003 (종목체결정보)
        - NXT 시간: ka10003 (동일, 단 NXT 데이터 반환)
        - 시간외: 전일 종가
        """
        try:
            if NXTPriceFix.is_regular_market_time() or NXTPriceFix.is_nxt_time():
                # 정규시장 또는 NXT 시간: 체결정보 조회
                result = market_api.get_stock_price(stock_code)

                if result:
                    return {
                        'stock_code': stock_code,
                        'current_price': result.get('current_price', 0),
                        'source': 'nxt_market' if NXTPriceFix.is_nxt_time() else 'regular_market',
                        'success': True
                    }

            # 시간외: 전일 종가
            if hasattr(market_api, 'get_daily_price'):
                daily_data = market_api.get_daily_price(stock_code, days=1)
                if daily_data and len(daily_data) > 0:
                    return {
                        'stock_code': stock_code,
                        'current_price': daily_data[0].get('close', 0),
                        'source': 'previous_close',
                        'success': True
                    }

            return None

        except Exception as e:
            print(f"시간대별 가격 조회 실패: {e}")
            return None

    @staticmethod
    def approach_2_nxt_market_type(market_api, stock_code: str, market_type: str = "auto") -> Optional[Dict[str, Any]]:
        """
        접근법 2: market_type 파라미터 활용

        API가 market_type을 지원한다면 명시적으로 지정
        """
        try:
            # 자동 판단
            if market_type == "auto":
                if NXTPriceFix.is_nxt_time():
                    market_type = "NXT"
                else:
                    market_type = "KRX"

            # API 호출 (market_type 지원 여부 확인 필요)
            if hasattr(market_api, 'get_stock_price_with_market'):
                result = market_api.get_stock_price_with_market(stock_code, market_type)
            else:
                # 기본 API 사용
                result = market_api.get_stock_price(stock_code)

            if result:
                return {
                    'stock_code': stock_code,
                    'current_price': result.get('current_price', 0),
                    'market_type': market_type,
                    'source': 'api_with_market_type',
                    'success': True
                }

            return None

        except Exception as e:
            print(f"market_type 지정 조회 실패: {e}")
            return None

    @staticmethod
    def approach_3_holdings_fallback(market_api, account_api, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        접근법 3: 보유종목 현재가 Fallback

        1차: market_api로 조회
        2차: 보유종목에서 현재가 추출 (NXT 시간에도 업데이트됨)
        """
        try:
            # 1차: market_api
            result = market_api.get_stock_price(stock_code)
            if result and result.get('current_price', 0) > 0:
                return {
                    'stock_code': stock_code,
                    'current_price': result.get('current_price', 0),
                    'source': 'market_api',
                    'success': True
                }

            # 2차: 보유종목
            if account_api:
                holdings = account_api.get_holdings(market_type="KRX")

                for h in holdings:
                    code = h.get('pdno', h.get('stk_cd', ''))
                    if code == stock_code:
                        current_price = int(h.get('prpr', h.get('cur_prc', 0)))
                        if current_price > 0:
                            return {
                                'stock_code': stock_code,
                                'current_price': current_price,
                                'source': 'holdings',
                                'success': True
                            }

            return None

        except Exception as e:
            print(f"holdings fallback 조회 실패: {e}")
            return None

    @staticmethod
    def approach_4_multiple_sources(market_api, account_api, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        접근법 4: 여러 소스 시도 (가장 견고한 방법)

        우선순위:
        1. market_api (정규/NXT 시간)
        2. holdings (보유종목인 경우)
        3. 전일 종가
        """
        try:
            sources_tried = []

            # 1. market_api
            try:
                result = market_api.get_stock_price(stock_code)
                sources_tried.append('market_api')

                if result and result.get('current_price', 0) > 0:
                    return {
                        'stock_code': stock_code,
                        'current_price': result.get('current_price', 0),
                        'source': 'market_api',
                        'sources_tried': sources_tried,
                        'success': True
                    }
            except Exception as e:
                print(f"market_api 실패: {e}")

            # 2. holdings
            if account_api:
                try:
                    holdings = account_api.get_holdings(market_type="KRX")
                    sources_tried.append('holdings')

                    for h in holdings:
                        code = h.get('pdno', h.get('stk_cd', ''))
                        if code == stock_code:
                            current_price = int(h.get('prpr', h.get('cur_prc', 0)))
                            if current_price > 0:
                                return {
                                    'stock_code': stock_code,
                                    'current_price': current_price,
                                    'source': 'holdings',
                                    'sources_tried': sources_tried,
                                    'success': True
                                }
                except Exception as e:
                    print(f"holdings 실패: {e}")

            # 3. 전일 종가
            if hasattr(market_api, 'get_daily_price'):
                try:
                    daily_data = market_api.get_daily_price(stock_code, days=1)
                    sources_tried.append('previous_close')

                    if daily_data and len(daily_data) > 0:
                        return {
                            'stock_code': stock_code,
                            'current_price': daily_data[0].get('close', 0),
                            'source': 'previous_close',
                            'sources_tried': sources_tried,
                            'success': True
                        }
                except Exception as e:
                    print(f"previous_close 실패: {e}")

            # 모든 소스 실패
            return {
                'stock_code': stock_code,
                'current_price': 0,
                'source': 'none',
                'sources_tried': sources_tried,
                'success': False,
                'error': 'All sources failed'
            }

        except Exception as e:
            print(f"multiple sources 조회 실패: {e}")
            return None


# ============================================================================
# MarketAPI 확장
# ============================================================================

class MarketAPIExtended:
    """
    MarketAPI 확장 클래스
    NXT 시간 지원 추가
    """

    def __init__(self, market_api, account_api=None):
        self.market_api = market_api
        self.account_api = account_api

    def get_current_price(self, stock_code: str, use_fallback: bool = True) -> Optional[int]:
        """
        현재가 조회 (NXT 시간 지원)

        Args:
            stock_code: 종목코드
            use_fallback: Fallback 사용 여부

        Returns:
            현재가 (실패 시 None)
        """
        if use_fallback:
            result = NXTPriceFix.approach_4_multiple_sources(
                self.market_api,
                self.account_api,
                stock_code
            )
        else:
            result = NXTPriceFix.approach_1_time_aware_api(
                self.market_api,
                stock_code
            )

        if result and result.get('success'):
            return result.get('current_price', 0)

        return None

    def get_current_price_with_source(self, stock_code: str) -> Dict[str, Any]:
        """
        현재가 조회 (소스 정보 포함)

        Args:
            stock_code: 종목코드

        Returns:
            {'price': int, 'source': str, 'timestamp': str}
        """
        result = NXTPriceFix.approach_4_multiple_sources(
            self.market_api,
            self.account_api,
            stock_code
        )

        if result and result.get('success'):
            return {
                'price': result.get('current_price', 0),
                'source': result.get('source', 'unknown'),
                'sources_tried': result.get('sources_tried', []),
                'timestamp': datetime.now().isoformat(),
                'is_nxt_time': NXTPriceFix.is_nxt_time()
            }

        return {
            'price': 0,
            'source': 'failed',
            'sources_tried': result.get('sources_tried', []) if result else [],
            'timestamp': datetime.now().isoformat(),
            'is_nxt_time': NXTPriceFix.is_nxt_time()
        }


# ============================================================================
# 대시보드 적용 예시
# ============================================================================

def get_stock_chart_data_fixed(bot_instance, stock_code: str):
    """
    수정된 get_stock_chart_data() 함수

    dashboard/app_apple.py의 get_stock_chart_data() 대체용
    NXT 시간에도 현재가 조회 가능
    """
    try:
        if bot_instance and hasattr(bot_instance, 'market_api'):
            market_api_ext = MarketAPIExtended(
                bot_instance.market_api,
                bot_instance.account_api if hasattr(bot_instance, 'account_api') else None
            )

            # 현재가 조회 (NXT 지원)
            price_info = market_api_ext.get_current_price_with_source(stock_code)

            return {
                'stock_code': stock_code,
                'current_price': price_info['price'],
                'price_source': price_info['source'],
                'is_nxt_time': price_info['is_nxt_time'],
                'timestamp': price_info['timestamp']
            }

        return {
            'stock_code': stock_code,
            'current_price': 0,
            'price_source': 'unavailable',
            'error': 'market_api not available'
        }

    except Exception as e:
        print(f"Error getting stock chart data: {e}")
        return {
            'stock_code': stock_code,
            'current_price': 0,
            'price_source': 'error',
            'error': str(e)
        }


# ============================================================================
# 테스트
# ============================================================================

if __name__ == "__main__":
    print("NXT 시장가격 조회 수정 패치")
    print()
    print("현재 시간 정보:")
    print(f"  정규시장 시간: {NXTPriceFix.is_regular_market_time()}")
    print(f"  NXT 거래시간: {NXTPriceFix.is_nxt_time()}")
    print()
    print("사용법:")
    print("1. 접근법 1 (추천): 시간대별 API")
    print("   result = NXTPriceFix.approach_1_time_aware_api(market_api, stock_code)")
    print()
    print("2. 접근법 4 (가장 견고): 여러 소스 시도")
    print("   result = NXTPriceFix.approach_4_multiple_sources(market_api, account_api, stock_code)")
    print()
    print("3. MarketAPI 확장 사용:")
    print("   market_api_ext = MarketAPIExtended(market_api, account_api)")
    print("   price = market_api_ext.get_current_price(stock_code)")
    print()
    print("대시보드 적용:")
    print("  dashboard/app_apple.py의 현재가 조회 부분에")
    print("  MarketAPIExtended 사용")
