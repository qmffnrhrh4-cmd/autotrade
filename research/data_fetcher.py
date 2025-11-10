"""
research/data_fetcher.py
데이터 수집 모듈
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, time
from utils.trading_date import get_last_trading_date

logger = logging.getLogger(__name__)


def is_nxt_hours() -> bool:
    """
    NXT 거래 시간 여부 확인

    Returns:
        NXT 거래 시간이면 True
    """
    now = datetime.now().time()

    # 오전: 08:00-09:00
    morning_start = time(8, 0)
    morning_end = time(9, 0)

    # 오후: 15:30-20:00
    afternoon_start = time(15, 30)
    afternoon_end = time(20, 0)

    is_morning = morning_start <= now < morning_end
    is_afternoon = afternoon_start <= now < afternoon_end

    return is_morning or is_afternoon


class DataFetcher:
    """
    키움증권 REST API 데이터 수집 클래스

    ⚠️ 중요: DOSK API ID는 키움증권 내부 API ID입니다
    - DOSK_XXXX는 한국투자증권이 아님!
    - 실제 요청은 키움증권 API 서버로 전송됨 (/api/dostk/...)
    - 모두 키움증권 REST API입니다

    주요 기능:
    - 계좌 정보 조회
    - 시세 데이터 조회 (DOSK API)
    - 종목 검색 (DOSK API)
    - 순위 정보 조회
    """
    
    def __init__(self, client):
        """
        DataFetcher 초기화
        
        Args:
            client: KiwoomRESTClient 인스턴스
        """
        self.client = client
        logger.info("DataFetcher 초기화 완료")
    
    # ==================== 계좌 정보 조회 ====================
    
    def get_balance(self, account_number: str = None) -> Optional[Dict[str, Any]]:
        """
        계좌 잔고 조회 (kt00018)

        Args:
            account_number: 계좌번호 (None이면 기본 계좌)

        Returns:
            잔고 정보 딕셔너리
            {
                'acnt_evlt_remn_indv_tot': [  # 보유 종목 리스트
                    {
                        'stk_cd': '005930',
                        'stk_nm': '삼성전자',
                        'rmnd_qty': '10',
                        'pur_pric': '70000',
                        'cur_prc': '72000',
                        'evltv_prft': '20000',
                        'prft_rt': '2.86',
                        'evlt_amt': '720000'
                    }
                ],
                'tot_evlt_amt': '720000',      # 총 평가금액
                'tot_evlt_pl': '20000',        # 총 평가손익
                'tot_prft_rt': '2.86',         # 총 수익률
                'prsm_dpst_aset_amt': '1000000'  # 추정예탁자산
            }
        """
        body = {
            "qry_tp": "1",           # 합산
            "dmst_stex_tp": "KRX"    # 한국거래소
        }

        response = self.client.request(
            api_id="kt00018",
            body=body,
            path="/api/dostk/acnt"
        )

        if response and response.get('return_code') == 0:
            logger.info("잔고 조회 성공")
            return response  # Response is data directly, no 'output' wrapper
        else:
            logger.error(f"잔고 조회 실패: {response.get('return_msg')}")
            return None
    
    def get_deposit(self, account_number: str = None) -> Optional[Dict[str, Any]]:
        """
        예수금 조회 (kt00001)

        Args:
            account_number: 계좌번호 (무시됨, 토큰에서 자동 추출)

        Returns:
            예수금 정보
            {
                'ord_alow_amt': '1000000',   # 주문 가능 금액
                'pymn_alow_amt': '1000000'   # 출금 가능 금액
            }
        """
        body = {"qry_tp": "2"}  # 일반조회

        response = self.client.request(
            api_id="kt00001",
            body=body,
            path="/api/dostk/acnt"
        )

        if response and response.get('return_code') == 0:
            ord_alow_amt = int(float(response.get('ord_alow_amt', 0)))
            logger.info(f"예수금 조회 성공: 주문가능금액 {ord_alow_amt:,}원")
            return response  # Response is data directly, no 'output' wrapper
        else:
            logger.error(f"예수금 조회 실패: {response.get('return_msg')}")
            return None
    
    def get_holdings(self, account_number: str = None) -> List[Dict[str, Any]]:
        """
        보유 종목 리스트 조회

        Args:
            account_number: 계좌번호

        Returns:
            보유 종목 리스트
        """
        balance = self.get_balance(account_number)

        if not balance:
            return []

        holdings = []
        output_list = balance.get('acnt_evlt_remn_indv_tot', [])

        for item in output_list:
            stock_code = item.get('stk_cd', '')
            # ✅ v5.16: _NX 접미사 유지 (NXT 현재가 조회를 위해 필요)

            holding = {
                'stock_code': stock_code,  # _NX 접미사 유지!
                'stock_name': item.get('stk_nm', ''),
                'quantity': int(float(item.get('rmnd_qty', 0))),
                'purchase_price': float(item.get('pur_pric', 0)),
                'current_price': float(item.get('cur_prc', 0)),
                'profit_loss': float(item.get('evltv_prft', 0)),
                'profit_loss_rate': float(item.get('prft_rt', 0)),
                'evaluation_amount': float(item.get('evlt_amt', 0)),
            }
            holdings.append(holding)

        logger.info(f"보유 종목 {len(holdings)}개 조회 완료")
        return holdings
    
    # ==================== 시세 조회 ====================
    
    def get_current_price(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        종목 현재가 조회 (시간대별 자동 처리)

        ✅ v5.16: NXT 시간대 자동 감지 및 _NX 접미사 처리
        - 08:00-09:00, 15:30-20:00: NXT 현재가 (_NX 접미사 사용)
        - 09:00-15:30: KRX 현재가 (기본 코드 사용)

        Args:
            stock_code: 종목코드 (6자리 또는 _NX 접미사 포함)

        Returns:
            현재가 정보
            {
                'stock_code': '005930',
                'stock_name': '삼성전자',
                'current_price': 72000,
                'change_price': 1000,
                'change_rate': 1.41,
                'exchange': 'KRX' or 'NXT',
                'time': '153045'
            }
        """
        # 기본 코드 추출 (이미 _NX가 있으면 유지)
        base_code = stock_code.replace('_NX', '')

        # NXT 시간대 확인 및 코드 결정
        in_nxt = is_nxt_hours()
        query_code = f"{base_code}_NX" if in_nxt else base_code

        # ka10003 API 사용 (체결정보)
        body = {"stk_cd": query_code}

        response = self.client.request(
            api_id="ka10003",
            body=body,
            path="stkinfo"
        )

        if response and response.get('return_code') == 0:
            cntr_list = response.get('cntr_infr', [])

            if not cntr_list or len(cntr_list) == 0:
                logger.warning(f"{query_code} 체결 정보 없음 (거래 없음)")
                return None

            # 최신 체결 정보 사용
            cntr_info = cntr_list[0]

            # 가격 파싱 (+/- 기호 제거)
            cur_prc_str = cntr_info.get('cur_prc', '0')
            current_price = abs(int(float(cur_prc_str.replace('+', '').replace('-', ''))))

            pred_pre_str = cntr_info.get('pred_pre', '0')
            change_price = int(float(pred_pre_str.replace('+', '').replace('-', '')))

            price_info = {
                'stock_code': base_code,
                'current_price': current_price,
                'change_price': change_price,
                'change_rate': float(cntr_info.get('pre_rt', '0').replace('+', '').replace('-', '')),
                'exchange': cntr_info.get('stex_tp', 'N/A'),
                'time': cntr_info.get('tm', ''),
                'volume': int(float(cntr_info.get('acc_trde_qty', 0)))
            }

            logger.info(f"{query_code} 현재가: {current_price:,}원 ({price_info['exchange']})")
            return price_info
        else:
            logger.error(f"현재가 조회 실패: {response.get('return_msg')}")
            return None
    
    def get_orderbook(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        호가 조회
        
        Args:
            stock_code: 종목코드
        
        Returns:
            호가 정보 (매도/매수 10호가)
            {
                'sell_hoga': [  # 매도 호가 (10개)
                    {'price': 72500, 'quantity': 1000},
                    {'price': 72400, 'quantity': 2000},
                    ...
                ],
                'buy_hoga': [  # 매수 호가 (10개)
                    {'price': 72300, 'quantity': 1500},
                    {'price': 72200, 'quantity': 2500},
                    ...
                ]
            }
        """
        body = {
            "stock_code": stock_code
        }
        
        response = self.client.request(
            api_id="DOSK_0003",
            body=body,
            path="/api/dostk/inquire/orderbook"
        )
        
        if response and response.get('return_code') == 0:
            orderbook = response.get('output', {})
            logger.info(f"{stock_code} 호가 조회 완료")
            return orderbook
        else:
            logger.error(f"호가 조회 실패: {response.get('return_msg')}")
            return None
    
    def get_daily_price(
        self,
        stock_code: str,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        일봉 데이터 조회 (검증된 API 사용: ka10081)

        Args:
            stock_code: 종목코드
            start_date: 시작일 (YYYYMMDD) - 사용되지 않음 (base_dt만 사용)
            end_date: 종료일 (YYYYMMDD) - base_dt로 사용

        Returns:
            일봉 데이터 리스트
            [
                {
                    'stck_bsop_date': '20251101',
                    'stck_oprc': 71000,
                    'stck_hgpr': 72500,
                    'stck_lwpr': 70500,
                    'stck_clpr': 72000,
                    'acml_vol': 10000000
                },
                ...
            ]
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')

        logger.info(f"📞 Calling ka10081 API for {stock_code} (base_dt: {end_date})")

        try:
            # Use verified API: ka10081 (주식일봉차트조회요청)
            response = self.client.call_verified_api(
                api_id="ka10081",
                variant_idx=1,
                body_override={
                    "stk_cd": stock_code,
                    "base_dt": end_date,  # 조회 기준일
                    "upd_stkpc_tp": "1"    # 수정주가 반영
                }
            )

            logger.info(f"📥 API Response received: {response is not None}")

            if response:
                return_code = response.get('return_code')
                return_msg = response.get('return_msg', 'No message')
                logger.info(f"📊 Return code: {return_code}")
                logger.info(f"📊 Return message: {return_msg}")
                logger.info(f"📦 Response keys: {list(response.keys())}")

                if return_code == 0:
                    # API returns data in 'stk_dt_pole_chart_qry' key (not 'output')
                    daily_data = response.get('stk_dt_pole_chart_qry', [])
                    logger.info(f"✅ {stock_code} 일봉 데이터 {len(daily_data)}개 조회 완료")

                    # Log sample data if available
                    if daily_data and len(daily_data) > 0:
                        logger.info(f"📊 Sample data (first item): {daily_data[0]}")
                    else:
                        logger.warning(f"⚠️ stk_dt_pole_chart_qry exists but is empty or None: {daily_data}")
                        logger.warning(f"⚠️ Full response: {response}")

                    # Convert to standard format
                    # API uses: dt, open_pric, high_pric, low_pric, cur_prc (close), trde_qty (volume)
                    standardized_data = []
                    for item in daily_data:
                        try:
                            standardized_data.append({
                                'date': item.get('dt', ''),
                                'open': int(float(item.get('open_pric', 0))),
                                'high': int(float(item.get('high_pric', 0))),
                                'low': int(float(item.get('low_pric', 0))),
                                'close': int(float(item.get('cur_prc', 0))),  # cur_prc = current/closing price
                                'volume': int(float(item.get('trde_qty', 0)))  # trde_qty = trade quantity
                            })
                        except (ValueError, TypeError) as e:
                            logger.warning(f"⚠️ Error parsing data item: {e}, item={item}")
                            continue

                    return standardized_data
                else:
                    logger.error(f"❌ 일봉 조회 실패 (return_code={return_code}): {return_msg}")
                    logger.error(f"❌ Full response: {response}")
                    return []
            else:
                logger.error(f"❌ API 응답 없음 (response is None)")
                return []

        except Exception as e:
            logger.error(f"❌ 일봉 조회 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_minute_price(
        self,
        stock_code: str,
        minute_type: str = '1'
    ) -> List[Dict[str, Any]]:
        """
        분봉 데이터 조회 (과거 데이터 포함, 검증된 API 사용: ka10080)

        Args:
            stock_code: 종목코드
            minute_type: 분봉 타입 ('1', '3', '5', '10', '30', '60')

        Returns:
            분봉 데이터 리스트
        """
        # Get current date as base_dt
        base_dt = datetime.now().strftime('%Y%m%d')

        logger.info(f"📞 Calling ka10080 API for {stock_code} (minute_type: {minute_type}, base_dt: {base_dt})")

        try:
            # Use verified API: ka10080 (주식 분봉 차트)
            response = self.client.call_verified_api(
                api_id="ka10080",
                variant_idx=1,
                body_override={
                    "stk_cd": stock_code,
                    "base_dt": base_dt,        # 조회 기준일
                    "chart_tp": minute_type,   # 분봉 타입 (1, 3, 5, 10, 30, 60)
                    "upd_stkpc_tp": "1"        # 수정주가 반영
                }
            )

            logger.info(f"📥 API Response received: {response is not None}")

            if response:
                return_code = response.get('return_code')
                return_msg = response.get('return_msg', 'No message')
                logger.info(f"📊 Return code: {return_code}")
                logger.info(f"📊 Return message: {return_msg}")
                logger.info(f"📦 Response keys: {list(response.keys())}")

                if return_code == 0:
                    # API returns data in 'stk_dt_pole_chart_qry' key (same as daily chart)
                    minute_data = response.get('stk_dt_pole_chart_qry', [])
                    logger.info(f"✅ {stock_code} {minute_type}분봉 데이터 {len(minute_data)}개 조회 완료")

                    # Log sample data if available
                    if minute_data and len(minute_data) > 0:
                        logger.info(f"📊 Sample data (first item): {minute_data[0]}")
                    else:
                        logger.warning(f"⚠️ stk_dt_pole_chart_qry exists but is empty or None: {minute_data}")
                        logger.warning(f"⚠️ Full response: {response}")

                    # Convert to standard format
                    # API uses: dt (date), time, open_pric, high_pric, low_pric, cur_prc (close), trde_qty (volume)
                    converted_data = []
                    for item in minute_data:
                        try:
                            converted_data.append({
                                'date': item.get('dt', ''),
                                'time': item.get('time', ''),
                                'open': int(float(item.get('open_pric', 0))),
                                'high': int(float(item.get('high_pric', 0))),
                                'low': int(float(item.get('low_pric', 0))),
                                'close': int(float(item.get('cur_pric', 0))),  # cur_pric = current/closing price
                                'volume': int(float(item.get('trde_qty', 0)))  # trde_qty = trade quantity
                            })
                        except (ValueError, TypeError) as e:
                            logger.warning(f"⚠️ Error parsing data item: {e}, item={item}")
                            continue

                    return converted_data
                else:
                    logger.error(f"❌ 분봉 조회 실패 (return_code={return_code}): {return_msg}")
                    logger.error(f"❌ Full response: {response}")
                    return []
            else:
                logger.error(f"❌ API 응답 없음 (response is None)")
                return []

        except Exception as e:
            logger.error(f"❌ 분봉 조회 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    # ==================== 종목 검색/순위 ====================
    
    def search_stock(self, keyword: str) -> List[Dict[str, Any]]:
        """
        종목 검색
        
        Args:
            keyword: 검색어 (종목명 또는 종목코드)
        
        Returns:
            검색 결과 리스트
            [
                {
                    'stock_code': '005930',
                    'stock_name': '삼성전자',
                    'market': 'KOSPI'
                },
                ...
            ]
        """
        body = {
            "keyword": keyword
        }
        
        response = self.client.request(
            api_id="DOSK_0006",
            body=body,
            path="/api/dostk/inquire/search"
        )
        
        if response and response.get('return_code') == 0:
            results = response.get('output', [])
            logger.info(f"'{keyword}' 검색 결과 {len(results)}개")
            return results
        else:
            logger.error(f"종목 검색 실패: {response.get('return_msg')}")
            return []
    
    def get_volume_rank(
        self,
        market: str = 'ALL',
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        거래량 순위 조회

        Args:
            market: 시장구분 ('ALL', 'KOSPI', 'KOSDAQ')
            limit: 조회 건수

        Returns:
            거래량 순위 리스트
        """
        try:
            from api.market import MarketAPI
            market_api = MarketAPI(self.client)
            rank_list = market_api.get_volume_rank(market, limit)
            logger.info(f"거래량 순위 {len(rank_list)}개 조회 완료")
            return rank_list
        except Exception as e:
            logger.error(f"거래량 순위 조회 실패: {e}")
            return []
    
    def get_price_change_rank(
        self,
        market: str = 'ALL',
        sort: str = 'rise',
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        등락률 순위 조회

        Args:
            market: 시장구분 ('ALL', 'KOSPI', 'KOSDAQ')
            sort: 정렬 ('rise': 상승률, 'fall': 하락률)
            limit: 조회 건수

        Returns:
            등락률 순위 리스트
        """
        try:
            from api.market import MarketAPI
            market_api = MarketAPI(self.client)
            rank_list = market_api.get_price_change_rank(market, sort, limit)
            logger.info(f"등락률 순위 {len(rank_list)}개 조회 완료")
            return rank_list
        except Exception as e:
            logger.error(f"등락률 순위 조회 실패: {e}")
            return []
    
    def get_trading_value_rank(
        self,
        market: str = 'ALL',
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        거래대금 순위 조회

        Args:
            market: 시장구분
            limit: 조회 건수

        Returns:
            거래대금 순위 리스트
        """
        try:
            from api.market import MarketAPI
            market_api = MarketAPI(self.client)
            # 거래대금은 거래량 API에서 sort 타입을 변경하여 조회
            body = {
                "market": market,
                "limit": limit,
                "sort": "trading_value"
            }
            response = market_api.client.request(
                api_id="DOSK_0010",
                body=body,
                path="/api/dostk/inquire/rank"
            )

            if response and response.get('return_code') == 0:
                rank_list = response.get('output', [])
                logger.info(f"거래대금 순위 {len(rank_list)}개 조회 완료")
                return rank_list
            else:
                logger.error(f"거래대금 순위 조회 실패: {response.get('return_msg')}")
                return []
        except Exception as e:
            logger.error(f"거래대금 순위 조회 실패: {e}")
            return []
    
    # ==================== 투자자별 매매 동향 ====================

    def get_investor_trading(
        self,
        stock_code: str,
        date: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        투자자별 매매 동향 조회 (외국인, 기관)

        Args:
            stock_code: 종목코드
            date: 조회일 (YYYYMMDD, None이면 최근 거래일 자동 계산)

        Returns:
            투자자별 매매 동향
            {
                'foreign_net': 10000,      # 외국인 순매수
                'institution_net': 5000,   # 기관 순매수
                'individual_net': -15000,  # 개인 순매수
                'foreign_hold_rate': 52.5  # 외국인 보유 비율
            }
        """
        # 날짜 자동 계산
        if not date:
            date = get_last_trading_date()

        body = {
            "stock_code": stock_code,
            "date": date
        }

        response = self.client.request(
            api_id="DOSK_0040",
            body=body,
            path="/api/dostk/inquire/investor"
        )

        if response and response.get('return_code') == 0:
            investor_info = response.get('output', {})
            logger.info(f"{stock_code} 투자자별 매매 동향 조회 완료 (날짜: {date})")
            return investor_info
        else:
            logger.error(f"투자자별 매매 동향 조회 실패: {response.get('return_msg')}")
            return None

    # v5.9: 외국인/기관 매매 순위 조회
    def get_foreign_buying_rank(
        self,
        market: str = 'KOSPI',
        amount_or_qty: str = 'amount',
        date: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        외국인 순매수 상위 종목 조회 (v5.9 NEW)

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            amount_or_qty: 조회구분 ('amount': 금액, 'qty': 수량)
            date: 조회일 (YYYYMMDD, None이면 최근 거래일)
            limit: 조회 건수

        Returns:
            외국인 순매수 상위 종목 리스트
            [
                {
                    'code': '005930',
                    'name': '삼성전자',
                    'net_amount': 100000,  # 백만원
                    'net_qty': 50000       # 천주
                },
                ...
            ]
        """
        try:
            from api.market import MarketAPI
            market_api = MarketAPI(self.client)
            rank_list = market_api.get_foreign_institution_trading_rank(
                market=market,
                amount_or_qty=amount_or_qty,
                date=date,
                limit=limit,
                investor_type='foreign_buy'
            )
            logger.info(f"외국인 순매수 순위 {len(rank_list)}개 조회 완료")
            return rank_list
        except Exception as e:
            logger.error(f"외국인 순매수 순위 조회 실패: {e}")
            return []

    def get_foreign_selling_rank(
        self,
        market: str = 'KOSPI',
        amount_or_qty: str = 'amount',
        date: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        외국인 순매도 상위 종목 조회 (v5.9 NEW)

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            amount_or_qty: 조회구분 ('amount': 금액, 'qty': 수량)
            date: 조회일 (YYYYMMDD, None이면 최근 거래일)
            limit: 조회 건수

        Returns:
            외국인 순매도 상위 종목 리스트
        """
        try:
            from api.market import MarketAPI
            market_api = MarketAPI(self.client)
            rank_list = market_api.get_foreign_institution_trading_rank(
                market=market,
                amount_or_qty=amount_or_qty,
                date=date,
                limit=limit,
                investor_type='foreign_sell'
            )
            logger.info(f"외국인 순매도 순위 {len(rank_list)}개 조회 완료")
            return rank_list
        except Exception as e:
            logger.error(f"외국인 순매도 순위 조회 실패: {e}")
            return []

    def get_institution_buying_rank(
        self,
        market: str = 'KOSPI',
        amount_or_qty: str = 'amount',
        date: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        기관 순매수 상위 종목 조회 (v5.9 NEW)

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            amount_or_qty: 조회구분 ('amount': 금액, 'qty': 수량)
            date: 조회일 (YYYYMMDD, None이면 최근 거래일)
            limit: 조회 건수

        Returns:
            기관 순매수 상위 종목 리스트
        """
        try:
            from api.market import MarketAPI
            market_api = MarketAPI(self.client)
            rank_list = market_api.get_foreign_institution_trading_rank(
                market=market,
                amount_or_qty=amount_or_qty,
                date=date,
                limit=limit,
                investor_type='institution_buy'
            )
            logger.info(f"기관 순매수 순위 {len(rank_list)}개 조회 완료")
            return rank_list
        except Exception as e:
            logger.error(f"기관 순매수 순위 조회 실패: {e}")
            return []

    def get_institution_selling_rank(
        self,
        market: str = 'KOSPI',
        amount_or_qty: str = 'amount',
        date: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        기관 순매도 상위 종목 조회 (v5.9 NEW)

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            amount_or_qty: 조회구분 ('amount': 금액, 'qty': 수량)
            date: 조회일 (YYYYMMDD, None이면 최근 거래일)
            limit: 조회 건수

        Returns:
            기관 순매도 상위 종목 리스트
        """
        try:
            from api.market import MarketAPI
            market_api = MarketAPI(self.client)
            rank_list = market_api.get_foreign_institution_trading_rank(
                market=market,
                amount_or_qty=amount_or_qty,
                date=date,
                limit=limit,
                investor_type='institution_sell'
            )
            logger.info(f"기관 순매도 순위 {len(rank_list)}개 조회 완료")
            return rank_list
        except Exception as e:
            logger.error(f"기관 순매도 순위 조회 실패: {e}")
            return []
    
    # ==================== 종목 상세 정보 ====================
    
    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        종목 상세 정보 조회
        
        Args:
            stock_code: 종목코드
        
        Returns:
            종목 상세 정보
            {
                'stock_code': '005930',
                'stock_name': '삼성전자',
                'market_cap': 500000000000000,  # 시가총액
                'per': 15.5,                     # PER
                'pbr': 1.2,                      # PBR
                'eps': 5000,                     # EPS
                'bps': 60000,                    # BPS
                'dividend_yield': 2.5,           # 배당수익률
                'listed_shares': 5000000000      # 상장주식수
            }
        """
        body = {
            "stock_code": stock_code
        }
        
        response = self.client.request(
            api_id="DOSK_0005",
            body=body,
            path="/api/dostk/inquire/stockinfo"
        )
        
        if response and response.get('return_code') == 0:
            stock_info = response.get('output', {})
            logger.info(f"{stock_code} 상세 정보 조회 완료")
            return stock_info
        else:
            logger.error(f"종목 정보 조회 실패: {response.get('return_msg')}")
            return None
    
    # ==================== 유틸리티 ====================
    
    def _get_market_code(self, market: str) -> str:
        """
        시장 코드 변환
        
        Args:
            market: 시장 문자열 ('ALL', 'KOSPI', 'KOSDAQ')
        
        Returns:
            시장 코드
        """
        market_map = {
            'ALL': '0',
            'KOSPI': '0',
            'KOSDAQ': '1'
        }
        return market_map.get(market.upper(), '0')


__all__ = ['DataFetcher']