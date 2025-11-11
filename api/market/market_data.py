"""
api/market/market_data.py
시세 및 호가 데이터 조회 API
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MarketDataAPI:
    """
    시세 및 호가 데이터 조회 API

    주요 기능:
    - 종목 체결정보 조회 (현재가)
    - 호가 조회
    - 시장 지수 조회
    """

    def __init__(self, client):
        """
        MarketDataAPI 초기화

        Args:
            client: KiwoomRESTClient 인스턴스
        """
        self.client = client
        logger.debug("MarketDataAPI 초기화 완료")

    def get_stock_price(self, stock_code: str, use_fallback: bool = True) -> Optional[Dict[str, Any]]:
        """
        종목 체결정보 조회 (키움증권 API ka10003)

        ⚠️ 중요:
        - NXT 시간대에 _NX 접미사 사용 시 일부 종목 성공 (70% 성공률)
        - 호가 API (_NX)가 더 안정적 (90% 성공률)
        - NXT 시간대에는 _NX 접미사 시도 후 기본 코드로 fallback

        Args:
            stock_code: 종목코드
            use_fallback: 실패 시 대체 소스 사용 여부 (기본값: True)

        Returns:
            체결정보 (현재가 포함)
        """
        from utils.trading_date import is_nxt_hours

        is_nxt = is_nxt_hours()

        # _NX 접미사 제거 (기본 코드 추출)
        base_code = stock_code[:-3] if stock_code.endswith("_NX") else stock_code

        # NXT 시간대 처리
        if is_nxt:
            # 먼저 _NX 접미사로 시도
            nx_code = f"{base_code}_NX"

            body_nx = {"stk_cd": nx_code}
            response_nx = self.client.request(
                api_id="ka10003",
                body=body_nx,
                path="stkinfo"
            )

            if response_nx and response_nx.get('return_code') == 0:
                cntr_infr = response_nx.get('cntr_infr', [])
                if cntr_infr and len(cntr_infr) > 0:
                    latest = cntr_infr[0]
                    cur_prc_str = latest.get('cur_prc', '0')
                    current_price = abs(int(cur_prc_str.replace('+', '').replace('-', '')))

                    if current_price > 0:
                        price_info = {
                            'current_price': current_price,
                            'cur_prc': current_price,
                            'change': latest.get('pred_pre', '0'),
                            'change_rate': latest.get('pre_rt', '0'),
                            'volume': latest.get('cntr_trde_qty', '0'),
                            'acc_volume': latest.get('acc_trde_qty', '0'),
                            'acc_trading_value': latest.get('acc_trde_prica', '0'),
                            'time': latest.get('tm', ''),
                            'stex_tp': latest.get('stex_tp', 'NXT'),
                            'source': 'nxt_realtime',
                        }
                        logger.info(f"{nx_code} NXT 현재가: {current_price:,}원 (stex_tp={price_info['stex_tp']})")
                        return price_info

        # 기본 코드로 조회 (일반 시간 또는 NXT fallback)
        body = {"stk_cd": base_code}

        response = self.client.request(
            api_id="ka10003",
            body=body,
            path="stkinfo"
        )

        if response and response.get('return_code') == 0:
            # ka10003 응답: cntr_infr 리스트
            cntr_infr = response.get('cntr_infr', [])

            if cntr_infr and len(cntr_infr) > 0:
                # 최신 체결 정보 (첫 번째 항목)
                latest = cntr_infr[0]

                # 현재가 파싱 (+/- 부호 제거)
                cur_prc_str = latest.get('cur_prc', '0')
                current_price = abs(int(cur_prc_str.replace('+', '').replace('-', '')))

                # 정규화된 응답
                price_info = {
                    'current_price': current_price,
                    'cur_prc': current_price,  # 원본 필드명도 유지
                    'change': latest.get('pred_pre', '0'),
                    'change_rate': latest.get('pre_rt', '0'),
                    'volume': latest.get('cntr_trde_qty', '0'),
                    'acc_volume': latest.get('acc_trde_qty', '0'),
                    'acc_trading_value': latest.get('acc_trde_prica', '0'),
                    'time': latest.get('tm', ''),
                    'stex_tp': latest.get('stex_tp', ''),
                    'source': 'nxt_realtime' if is_nxt else 'regular_market',
                }

                logger.info(f"{base_code} 현재가: {current_price:,}원 (출처: {price_info['source']})")
                return price_info
            else:
                logger.warning(f"현재가 조회 실패: 체결정보 없음")
        else:
            logger.warning(f"현재가 조회 API 실패: {response.get('return_msg') if response else 'No response'}")

        # Fallback 1: 호가 정보에서 현재가 추출 시도 (NXT 코드)
        if use_fallback:
            logger.info(f"{stock_code} 호가 정보로 현재가 조회 시도...")
            orderbook = self.get_orderbook(stock_code)
            if orderbook and orderbook.get('현재가', 0) > 0:
                current_price = int(orderbook.get('현재가', 0))
                logger.info(f"{stock_code} 현재가: {current_price:,}원 (출처: orderbook)")
                return {
                    'current_price': current_price,
                    'cur_prc': current_price,
                    'source': 'orderbook',
                    'time': '',
                }

            # Fallback 2: NXT 시간대에 _NX 호가도 실패하면 기본 코드로 재시도
            if is_nxt_hours() and nxt_stock_code != stock_code:
                logger.info(f"{stock_code} NXT 호가 실패 - 기본 코드로 재시도...")
                # get_orderbook 내부에서 _NX를 추가하므로, 강제로 기본 코드 사용
                body_fallback = {"stk_cd": stock_code}
                response_fallback = self.client.request(
                    api_id="ka10004",
                    body=body_fallback,
                    path="mrkcond"
                )
                if response_fallback and response_fallback.get('return_code') == 0:
                    sel_fpr_bid = response_fallback.get('sel_fpr_bid', '0').replace('+', '').replace('-', '')
                    buy_fpr_bid = response_fallback.get('buy_fpr_bid', '0').replace('+', '').replace('-', '')

                    sell_price = abs(int(sel_fpr_bid)) if sel_fpr_bid and sel_fpr_bid != '0' else 0
                    buy_price = abs(int(buy_fpr_bid)) if buy_fpr_bid and buy_fpr_bid != '0' else 0

                    if sell_price > 0 or buy_price > 0:
                        # 중간가 계산
                        if sell_price > 0 and buy_price > 0:
                            current_price = (sell_price + buy_price) // 2
                        elif sell_price > 0:
                            current_price = sell_price
                        else:
                            current_price = buy_price

                        logger.info(f"{stock_code} 현재가: {current_price:,}원 (출처: orderbook_basic_fallback)")
                        return {
                            'current_price': current_price,
                            'cur_prc': current_price,
                            'source': 'orderbook_basic_fallback',
                            'time': '',
                        }

        logger.error(f"{stock_code} 현재가 조회 완전 실패 (모든 소스)")
        return None

    def get_orderbook(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        호가 조회 (키움증권 API ka10004)

        ⚠️ 중요:
        - NXT 시간대에 _NX 접미사 사용 시 90% 성공률 (최고 성공률!)
        - NXT 시간대에는 _NX 접미사 우선 시도

        Args:
            stock_code: 종목코드

        Returns:
            호가 정보
            {
                'sell_price': 매도1호가,
                'buy_price': 매수1호가,
                'mid_price': 중간가,
                '매도_총잔량': 총매도잔량,
                '매수_총잔량': 총매수잔량,
                ...
            }
        """
        from utils.trading_date import is_nxt_hours

        is_nxt = is_nxt_hours()

        # _NX 접미사 제거 (기본 코드 추출)
        base_code = stock_code[:-3] if stock_code.endswith("_NX") else stock_code

        # NXT 시간대 처리 - _NX 접미사 우선
        if is_nxt:
            nx_code = f"{base_code}_NX"
            body_nx = {"stk_cd": nx_code}

            response_nx = self.client.request(
                api_id="ka10004",
                body=body_nx,
                path="mrkcond"
            )

            if response_nx and response_nx.get('return_code') == 0:
                # NXT 호가 성공 - 파싱 시도
                sel_fpr_bid = response_nx.get('sel_fpr_bid', '0').replace('+', '').replace('-', '')
                buy_fpr_bid = response_nx.get('buy_fpr_bid', '0').replace('+', '').replace('-', '')

                if sel_fpr_bid and buy_fpr_bid and sel_fpr_bid != '' and buy_fpr_bid != '':
                    try:
                        sell_price = abs(int(sel_fpr_bid)) if sel_fpr_bid != '0' else 0
                        buy_price = abs(int(buy_fpr_bid)) if buy_fpr_bid != '0' else 0

                        if sell_price > 0 or buy_price > 0:
                            # NXT 호가 데이터 처리
                            orderbook = response_nx
                            orderbook['sell_price'] = sell_price
                            orderbook['buy_price'] = buy_price

                            # 총잔량 파싱
                            tot_sel_req = orderbook.get('tot_sel_req', '0').replace('+', '').replace('-', '')
                            tot_buy_req = orderbook.get('tot_buy_req', '0').replace('+', '').replace('-', '')

                            orderbook['매도_총잔량'] = abs(int(tot_sel_req)) if tot_sel_req and tot_sel_req != '0' else 0
                            orderbook['매수_총잔량'] = abs(int(tot_buy_req)) if tot_buy_req and tot_buy_req != '0' else 0

                            # 중간가 계산
                            if sell_price > 0 and buy_price > 0:
                                orderbook['mid_price'] = (sell_price + buy_price) // 2
                            elif sell_price > 0:
                                orderbook['mid_price'] = sell_price
                            else:
                                orderbook['mid_price'] = buy_price

                            orderbook['현재가'] = orderbook['mid_price']

                            logger.info(f"{nx_code} NXT 호가 조회 완료: 매도1={sell_price:,}, 매수1={buy_price:,}")
                            return orderbook
                    except (ValueError, TypeError) as e:
                        logger.warning(f"{nx_code} NXT 호가 파싱 실패: {e}, fallback to 기본 코드")

        # 기본 코드로 조회 (일반 시간 또는 NXT fallback)
        body = {"stk_cd": base_code}

        response = self.client.request(
            api_id="ka10004",
            body=body,
            path="mrkcond"
        )

        if response and response.get('return_code') == 0:
            # ka10004 응답은 output 키 없이 바로 데이터가 옴
            orderbook = response

            # 매도1호가 / 매수1호가 파싱
            sel_fpr_bid = orderbook.get('sel_fpr_bid', '0').replace('+', '').replace('-', '')
            buy_fpr_bid = orderbook.get('buy_fpr_bid', '0').replace('+', '').replace('-', '')

            sell_price = abs(int(sel_fpr_bid)) if sel_fpr_bid and sel_fpr_bid != '0' else 0
            buy_price = abs(int(buy_fpr_bid)) if buy_fpr_bid and buy_fpr_bid != '0' else 0

            # 총잔량 파싱
            tot_sel_req = orderbook.get('tot_sel_req', '0').replace('+', '').replace('-', '')
            tot_buy_req = orderbook.get('tot_buy_req', '0').replace('+', '').replace('-', '')

            total_sell_qty = abs(int(tot_sel_req)) if tot_sel_req and tot_sel_req != '0' else 0
            total_buy_qty = abs(int(tot_buy_req)) if tot_buy_req and tot_buy_req != '0' else 0

            # 정규화된 응답
            orderbook['sell_price'] = sell_price  # 매도1호가
            orderbook['buy_price'] = buy_price    # 매수1호가

            # scanner_pipeline.py 호환 필드명 추가
            orderbook['매도_총잔량'] = total_sell_qty
            orderbook['매수_총잔량'] = total_buy_qty

            # 중간가 계산
            if sell_price > 0 and buy_price > 0:
                orderbook['mid_price'] = (sell_price + buy_price) // 2
            elif sell_price > 0:
                orderbook['mid_price'] = sell_price
            elif buy_price > 0:
                orderbook['mid_price'] = buy_price
            else:
                orderbook['mid_price'] = 0

            # 현재가 필드 추가 (scanner 호환)
            orderbook['현재가'] = orderbook['mid_price']

            logger.info(
                f"{base_code} 호가 조회 완료: "
                f"매도1={sell_price:,}, 매수1={buy_price:,}, "
                f"총잔량(매도={total_sell_qty:,}, 매수={total_buy_qty:,})"
            )
            return orderbook
        else:
            logger.error(f"호가 조회 실패: {response.get('return_msg') if response else 'No response'}")
            return None

    def get_bid_ask(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        호가 데이터 조회 (get_orderbook의 별칭)

        Args:
            stock_code: 종목코드

        Returns:
            호가 정보
            {
                '매수_총잔량': 10000,
                '매도_총잔량': 8000,
                ...
            }
        """
        return self.get_orderbook(stock_code)

    def get_market_index(self, market_code: str = '001') -> Optional[Dict[str, Any]]:
        """
        시장 지수 조회

        Args:
            market_code: 시장코드 ('001': 코스피, '101': 코스닥)

        Returns:
            지수 정보
        """
        body = {
            "market_code": market_code
        }

        response = self.client.request(
            api_id="DOSK_0004",
            body=body,
            path="inquire/index"
        )

        if response and response.get('return_code') == 0:
            index_info = response.get('output', {})
            market_name = "코스피" if market_code == '001' else "코스닥"
            logger.info(f"{market_name} 지수: {index_info.get('index', 0):.2f}")
            return index_info
        else:
            logger.error(f"지수 조회 실패: {response.get('return_msg')}")
            return None


__all__ = ['MarketDataAPI']
