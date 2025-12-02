"""
api/market/ranking.py
순위 정보 조회 API

개선사항:
- API 에러와 "데이터 없음" 구분
- 진단 로깅 통합
- 호출자에게 명확한 상태 전달
"""
import logging
from typing import Dict, Any, List, Optional, NamedTuple
from enum import Enum
from utils.trading_date import get_last_trading_date

# 진단 로거 통합
try:
    from utils.diagnostic_logger import log_api_call, log_error
except ImportError:
    def log_api_call(*args, **kwargs):
        pass
    def log_error(*args, **kwargs):
        pass

logger = logging.getLogger(__name__)


class RankingResultStatus(Enum):
    """순위 조회 결과 상태"""
    SUCCESS = "success"                    # 정상 조회
    NO_DATA = "no_data"                    # 장외 시간 등으로 데이터 없음
    API_ERROR = "api_error"                # API 호출 실패
    NETWORK_ERROR = "network_error"        # 네트워크 오류
    PARSE_ERROR = "parse_error"            # 응답 파싱 오류


class RankingResult(NamedTuple):
    """순위 조회 결과"""
    status: RankingResultStatus
    data: List[Dict[str, Any]]
    message: str
    error_code: Optional[int] = None

    @property
    def is_success(self) -> bool:
        return self.status == RankingResultStatus.SUCCESS

    @property
    def has_data(self) -> bool:
        return len(self.data) > 0


class RankingAPI:
    """
    순위 정보 조회 API

    주요 기능:
    - 거래량 순위
    - 등락률 순위
    - 거래대금 순위
    - 외국인/기관 매매 순위
    - 신용비율 순위
    등
    """

    # 마지막 조회 결과 상태 저장 (진단용)
    _last_result_status: Dict[str, RankingResult] = {}

    def __init__(self, client):
        """
        RankingAPI 초기화

        Args:
            client: KiwoomRESTClient 인스턴스
        """
        self.client = client
        logger.debug("RankingAPI 초기화 완료")

    @classmethod
    def get_last_status(cls, api_name: str) -> Optional[RankingResult]:
        """마지막 API 호출 상태 반환 (진단용)"""
        return cls._last_result_status.get(api_name)

    def _record_result(self, api_name: str, result: RankingResult):
        """결과 기록 (진단용)"""
        RankingAPI._last_result_status[api_name] = result

        # 진단 로거에 기록
        log_api_call(
            api_name=f"ranking_{api_name}",
            success=result.is_success,
            data_count=len(result.data),
            error_message="" if result.is_success else result.message,
            status=result.status.value
        )

    def get_volume_rank(
        self,
        market: str = 'ALL',
        limit: int = 20,
        date: str = None
    ) -> List[Dict[str, Any]]:
        """
        전일 거래량 순위 조회 (ka10031)

        Args:
            market: 시장구분 ('0': 전체, '1': KOSPI, '2': KOSDAQ)
            limit: 조회 건수 (최대 200)
            date: 조회일 (현재 미사용, 자동으로 전일 데이터 조회)

        Returns:
            거래량 순위 리스트

        Note:
            이 API는 실시간 전일 데이터만 제공합니다.
            주말/공휴일/장마감 후에는 데이터가 제공되지 않을 수 있습니다.
        """
        try:
            # 시장 코드 변환 (successful_apis.json 검증된 값)
            market_map = {'ALL': '000', 'KOSPI': '001', 'KOSDAQ': '101'}
            mrkt_tp = market_map.get(market.upper(), '001')

            # 순위 범위 설정 (1위부터 limit까지)
            body = {
                "mrkt_tp": mrkt_tp,        # 시장구분 (000:전체, 001:KOSPI, 101:KOSDAQ)
                "qry_tp": "1",              # 조회구분 (1:거래량, 2:거래대금) - 검증됨
                "stex_tp": "3",             # 증권거래소 (3:전체) - 검증됨
                "rank_strt": "1",           # 시작순위
                "rank_end": str(limit)      # 종료순위
            }

            print(f"📍 거래량 순위 조회 시작 (market={market}, limit={limit})")
            logger.info(f"거래량 순위 조회 시작 (market={market}, limit={limit})")

            response = self.client.request(
                api_id="ka10031",
                body=body,
                path="rkinfo"
            )

            print(f"📍 API 응답 received: return_code={response.get('return_code') if response else None}")

            if response and response.get('return_code') == 0:
                # ka10031 API는 'pred_trde_qty_upper' 키에 데이터 반환
                rank_list = response.get('pred_trde_qty_upper', [])
                print(f"📍 rank_list 크기: {len(rank_list) if rank_list else 0}개")

                if not rank_list:
                    msg = "⚠️ API 호출 성공했으나 데이터가 비어있습니다 (장마감 후/주말/공휴일일 수 있음)"
                    print(msg)
                    logger.warning(msg)
                    print(f"📍 전체 응답 키: {list(response.keys())}")

                    # 진단: NO_DATA 상태 기록
                    self._record_result("volume_rank", RankingResult(
                        status=RankingResultStatus.NO_DATA,
                        data=[],
                        message="장마감/주말/공휴일로 데이터 없음"
                    ))
                    return []

                # 데이터 정규화: API 응답 키 -> 표준 키
                normalized_list = []
                debug_printed = False

                for item in rank_list:
                    # 현재가 파싱 (부호 포함 가능)
                    cur_prc_str = item.get('cur_prc', '0')
                    current_price = abs(int(float(cur_prc_str.replace('+', '').replace('-', ''))))

                    # 등락폭 파싱 (부호 포함 가능)
                    pred_pre_str = item.get('pred_pre', '0')
                    change = int(float(pred_pre_str.replace('+', '').replace('-', '')))

                    # 등락 부호 확인 (2: 상승, 3: 보합, 5: 하락)
                    pred_pre_sig = item.get('pred_pre_sig', '3')
                    is_positive = pred_pre_sig == '2' or pred_pre_str.startswith('+')

                    # 전일 종가 계산
                    if is_positive:
                        prev_price = current_price - change
                    else:
                        prev_price = current_price + change

                    # 등락률 계산: (등락폭 / 전일종가) * 100
                    if prev_price > 0:
                        change_rate = abs(change / prev_price * 100)
                    else:
                        change_rate = 0.0

                    # API 응답에 등락률 필드가 있으면 사용
                    if 'flu_rt' in item:
                        change_rate = abs(float(item.get('flu_rt', '0').replace('+', '').replace('-', '')))

                    normalized_list.append({
                        'code': item.get('stk_cd', '').replace('_AL', ''),  # _AL 접미사 제거
                        'name': item.get('stk_nm', ''),
                        'price': current_price,
                        'current_price': current_price,  # Screener 호환
                        'volume': int(float(item.get('trde_qty', '0'))),
                        'change': change,
                        'change_rate': change_rate,  # Screener 호환
                        'rate': change_rate,  # StockCandidate 호환
                        'change_sign': item.get('pred_pre_sig', ''),
                    })

                logger.info(f"✅ 거래량 순위 {len(normalized_list)}개 조회 완료")

                # 진단: 성공 기록
                self._record_result("volume_rank", RankingResult(
                    status=RankingResultStatus.SUCCESS,
                    data=normalized_list,
                    message=f"{len(normalized_list)}개 조회 완료"
                ))
                return normalized_list
            else:
                error_msg = response.get('return_msg', 'Unknown error') if response else 'No response'
                error_code = response.get('return_code') if response else -1
                logger.error(f"❌ 거래량 순위 조회 실패: {error_msg}")
                logger.error(f"Response code: {error_code}")
                logger.debug(f"Full response: {response}")

                # 진단: API_ERROR 기록
                self._record_result("volume_rank", RankingResult(
                    status=RankingResultStatus.API_ERROR,
                    data=[],
                    message=error_msg,
                    error_code=error_code
                ))
                return []

        except Exception as e:
            logger.error(f"❌ 거래량 순위 조회 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()

            # 진단: 예외 기록
            self._record_result("volume_rank", RankingResult(
                status=RankingResultStatus.NETWORK_ERROR,
                data=[],
                message=str(e)
            ))
            log_error("ranking_api", str(e), error_type="VOLUME_RANK_ERROR")
            return []

    def get_price_change_rank(
        self,
        market: str = 'ALL',
        sort: str = 'rise',
        limit: int = 20,
        date: str = None
    ) -> List[Dict[str, Any]]:
        """
        전일대비 등락률 상위 조회 (ka10027)

        Args:
            market: 시장구분 ('ALL', 'KOSPI', 'KOSDAQ')
            sort: 정렬 ('rise': 상승률, 'fall': 하락률)
            limit: 조회 건수 (최대 200, 실제로는 40개씩 반환)
            date: 조회일 (현재 미사용)

        Returns:
            등락률 순위 리스트

        Note:
            이 API는 실시간 전일 데이터만 제공합니다.
            주말/공휴일/장마감 후에는 데이터가 제공되지 않을 수 있습니다.
        """
        try:
            # 시장 코드 변환 (successful_apis.json 검증된 값)
            market_map = {'ALL': '000', 'KOSPI': '001', 'KOSDAQ': '101'}
            mrkt_tp = market_map.get(market.upper(), '001')

            # 정렬 타입 변환 (검증된 값: 1=상승률, 2=하락률로 추정)
            sort_map = {'rise': '1', 'fall': '2'}
            sort_tp = sort_map.get(sort.lower(), '1')

            sort_name = "상승률" if sort == 'rise' else "하락률"
            logger.info(f"{sort_name} 순위 조회 시작 (market={market}, limit={limit})")

            body = {
                "mrkt_tp": mrkt_tp,          # 시장구분 (000:전체, 001:KOSPI, 101:KOSDAQ)
                "sort_tp": sort_tp,           # 정렬구분 (1:상승률, 2:하락률)
                "trde_qty_cnd": "0100",       # 거래량 조건 (검증된 값)
                "stk_cnd": "1",               # 종목 조건 (검증된 값)
                "crd_cnd": "0",               # 신용 조건 (0: 전체)
                "updown_incls": "1",          # 상한하한 포함 (0: 제외, 1: 포함)
                "pric_cnd": "0",              # 가격 조건 (0: 전체)
                "trde_prica_cnd": "0",        # 거래대금 조건 (0: 전체)
                "stex_tp": "3"                # 증권거래소 (3: 전체)
            }

            response = self.client.request(
                api_id="ka10027",
                body=body,
                path="rkinfo"
            )

            if response and response.get('return_code') == 0:
                # ka10027 API는 'pred_pre_flu_rt_upper' 키에 데이터 반환
                rank_list = response.get('pred_pre_flu_rt_upper', [])

                if not rank_list:
                    logger.warning("⚠️ API 호출 성공했으나 데이터가 비어있습니다 (장마감 후/주말/공휴일일 수 있음)")
                    self._record_result("price_change_rank", RankingResult(
                        status=RankingResultStatus.NO_DATA, data=[], message="장마감/주말/공휴일"
                    ))
                    return []

                # 데이터 정규화: API 응답 키 -> 표준 키
                normalized_list = []
                for item in rank_list[:limit]:
                    normalized_list.append({
                        'code': item.get('stk_cd', '').replace('_AL', ''),  # _AL 접미사 제거
                        'name': item.get('stk_nm', ''),
                        'price': int(float(item.get('cur_prc', '0').replace('+', '').replace('-', ''))),
                        'change_rate': float(item.get('flu_rt', '0').replace('+', '').replace('-', '')),
                        'rate': float(item.get('flu_rt', '0').replace('+', '').replace('-', '')),  # 호환성
                        'volume': int(float(item.get('now_trde_qty', '0'))),
                        'change': int(float(item.get('pred_pre', '0').replace('+', '').replace('-', ''))),
                        'change_sign': item.get('pred_pre_sig', ''),
                    })

                logger.info(f"✅ {sort_name} 순위 {len(normalized_list)}개 조회 완료")
                self._record_result("price_change_rank", RankingResult(
                    status=RankingResultStatus.SUCCESS, data=normalized_list, message=f"{len(normalized_list)}개 조회"
                ))
                return normalized_list
            else:
                error_msg = response.get('return_msg', 'Unknown error') if response else 'No response'
                logger.error(f"❌ 등락률 순위 조회 실패: {error_msg}")
                logger.error(f"Response code: {response.get('return_code') if response else 'N/A'}")
                logger.debug(f"Full response: {response}")
                self._record_result("price_change_rank", RankingResult(
                    status=RankingResultStatus.API_ERROR, data=[], message=error_msg
                ))
                return []

        except Exception as e:
            logger.error(f"❌ 등락률 순위 조회 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            self._record_result("price_change_rank", RankingResult(
                status=RankingResultStatus.NETWORK_ERROR, data=[], message=str(e)
            ))
            log_error("ranking_api", str(e), error_type="PRICE_CHANGE_RANK_ERROR")
            return []

    def get_trading_value_rank(
        self,
        market: str = 'ALL',
        limit: int = 20,
        include_managed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        거래대금 상위 조회 (ka10032)

        Args:
            market: 시장구분 ('ALL', 'KOSPI', 'KOSDAQ')
            limit: 조회 건수 (최대 200)
            include_managed: 관리종목 포함 여부

        Returns:
            거래대금 순위 리스트

        Note:
            이 API는 실시간 전일 데이터만 제공합니다.
            주말/공휴일/장마감 후에는 데이터가 제공되지 않을 수 있습니다.
        """
        try:
            # 시장 코드 변환 (successful_apis.json 검증된 값)
            market_map = {'ALL': '000', 'KOSPI': '001', 'KOSDAQ': '101'}
            mrkt_tp = market_map.get(market.upper(), '001')

            logger.info(f"거래대금 순위 조회 시작 (market={market}, limit={limit})")

            body = {
                "mrkt_tp": mrkt_tp,               # 시장구분
                "mang_stk_incls": "1" if include_managed else "0",  # 관리종목 포함
                "stex_tp": "3"                    # 증권거래소 (3: 전체)
            }

            response = self.client.request(
                api_id="ka10032",
                body=body,
                path="rkinfo"
            )

            if response and response.get('return_code') == 0:
                # 응답 키 찾기 (자동 탐색)
                data_keys = [k for k in response.keys() if k not in ['return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key']]

                # 첫 번째 리스트 키 사용
                rank_list = []
                for key in data_keys:
                    val = response.get(key)
                    if isinstance(val, list) and len(val) > 0:
                        rank_list = val
                        break

                if not rank_list:
                    logger.warning("⚠️ API 호출 성공했으나 데이터가 비어있습니다 (장마감 후/주말/공휴일일 수 있음)")
                    self._record_result("trading_value_rank", RankingResult(
                        status=RankingResultStatus.NO_DATA, data=[], message="장마감/주말/공휴일"
                    ))
                    return []

                # 데이터 정규화
                normalized_list = []
                for item in rank_list[:limit]:
                    normalized_list.append({
                        'code': item.get('stk_cd', '').replace('_AL', ''),
                        'name': item.get('stk_nm', ''),
                        'price': int(float(item.get('cur_prc', item.get('cur_pric', '0')).replace('+', '').replace('-', ''))),
                        'trading_value': int(float(item.get('trde_prica', '0'))),  # 거래대금
                        'volume': int(float(item.get('trde_qty', '0'))),
                        'change': int(float(item.get('pred_pre', '0').replace('+', '').replace('-', ''))),
                        'change_sign': item.get('pred_pre_sig', ''),
                        'rate': 0.0,  # 호환성
                    })

                logger.info(f"✅ 거래대금 순위 {len(normalized_list)}개 조회 완료")
                self._record_result("trading_value_rank", RankingResult(
                    status=RankingResultStatus.SUCCESS, data=normalized_list, message=f"{len(normalized_list)}개 조회"
                ))
                return normalized_list
            else:
                error_msg = response.get('return_msg', 'Unknown error') if response else 'No response'
                logger.error(f"❌ 거래대금 순위 조회 실패: {error_msg}")
                logger.error(f"Response code: {response.get('return_code') if response else 'N/A'}")
                logger.debug(f"Full response: {response}")
                self._record_result("trading_value_rank", RankingResult(
                    status=RankingResultStatus.API_ERROR, data=[], message=error_msg
                ))
                return []

        except Exception as e:
            logger.error(f"❌ 거래대금 순위 조회 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            self._record_result("trading_value_rank", RankingResult(
                status=RankingResultStatus.NETWORK_ERROR, data=[], message=str(e)
            ))
            log_error("ranking_api", str(e), error_type="TRADING_VALUE_RANK_ERROR")
            return []

    def get_volume_surge_rank(
        self,
        market: str = 'ALL',
        limit: int = 20,
        time_interval: int = 5
    ) -> List[Dict[str, Any]]:
        """
        거래량 급증 종목 조회 (ka10023)

        Args:
            market: 시장구분 ('ALL', 'KOSPI', 'KOSDAQ')
            limit: 조회 건수
            time_interval: 시간 간격 (분)

        Returns:
            거래량 급증 순위 리스트
        """
        market_map = {'ALL': '000', 'KOSPI': '001', 'KOSDAQ': '101'}
        mrkt_tp = market_map.get(market.upper(), '000')

        body = {
            "mrkt_tp": mrkt_tp,
            "trde_qty_tp": "100",  # 거래량 조건
            "sort_tp": "2",        # 정렬 타입
            "tm_tp": "1",          # 시간 타입 (1:분, 2:시간)
            "tm": str(time_interval),  # 시간 간격
            "stk_cnd": "0",
            "pric_tp": "0",
            "stex_tp": "3"
        }

        response = self.client.request(
            api_id="ka10023",
            body=body,
            path="rkinfo"
        )

        if response and response.get('return_code') == 0:
            # 응답 키 찾기
            data_keys = [k for k in response.keys() if k not in ['return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key']]

            rank_list = []
            for key in data_keys:
                val = response.get(key)
                if isinstance(val, list) and len(val) > 0:
                    rank_list = val
                    break

            # 데이터 정규화
            normalized_list = []
            for item in rank_list[:limit]:
                normalized_list.append({
                    'code': item.get('stk_cd', '').replace('_AL', ''),
                    'name': item.get('stk_nm', ''),
                    'price': int(float(item.get('cur_prc', '0').replace('+', '').replace('-', ''))),
                    'volume': int(float(item.get('trde_qty', '0'))),
                    'volume_increase_rate': float(item.get('qty_incrs_rt', '0')),  # 거래량 증가율
                    'change_rate': float(item.get('flu_rt', '0').replace('+', '').replace('-', '')),
                })

            logger.info(f"거래량 급증 {len(normalized_list)}개 조회 완료")
            return normalized_list
        else:
            logger.error(f"거래량 급증 조회 실패: {response.get('return_msg')}")
            return []

    def get_intraday_change_rank(
        self,
        market: str = 'ALL',
        sort: str = 'rise',
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        시가대비 등락률 순위 조회 (ka10028)

        Args:
            market: 시장구분 ('ALL', 'KOSPI', 'KOSDAQ')
            sort: 정렬 ('rise': 상승률, 'fall': 하락률)
            limit: 조회 건수

        Returns:
            시가대비 등락률 순위 리스트
        """
        market_map = {'ALL': '000', 'KOSPI': '001', 'KOSDAQ': '101'}
        mrkt_tp = market_map.get(market.upper(), '000')

        # 정렬 타입 (1:상승률, 2:하락률)
        sort_map = {'rise': '1', 'fall': '2'}
        sort_tp = sort_map.get(sort.lower(), '1')

        body = {
            "sort_tp": sort_tp,
            "trde_qty_cnd": "0000",
            "mrkt_tp": mrkt_tp,
            "updown_incls": "1",
            "stk_cnd": "0",
            "crd_cnd": "0",
            "trde_prica_cnd": "0",
            "flu_cnd": "1",
            "stex_tp": "3"
        }

        response = self.client.request(
            api_id="ka10028",
            body=body,
            path="stkinfo"
        )

        if response and response.get('return_code') == 0:
            # 응답 키 찾기
            data_keys = [k for k in response.keys() if k not in ['return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key']]

            rank_list = []
            for key in data_keys:
                val = response.get(key)
                if isinstance(val, list) and len(val) > 0:
                    rank_list = val
                    break

            # 데이터 정규화
            normalized_list = []
            for item in rank_list[:limit]:
                normalized_list.append({
                    'code': item.get('stk_cd', '').replace('_AL', ''),
                    'name': item.get('stk_nm', ''),
                    'price': int(float(item.get('cur_prc', '0').replace('+', '').replace('-', ''))),
                    'open_price': int(float(item.get('open_prc', '0'))),  # 시가
                    'intraday_change_rate': float(item.get('flu_rt', '0').replace('+', '').replace('-', '')),
                    'volume': int(float(item.get('trde_qty', '0'))),
                })

            sort_name = "상승률" if sort == 'rise' else "하락률"
            logger.info(f"시가대비 {sort_name} {len(normalized_list)}개 조회 완료")
            return normalized_list
        else:
            logger.error(f"시가대비 등락률 조회 실패: {response.get('return_msg')}")
            return []

    def get_foreign_period_trading_rank(
        self,
        market: str = 'KOSPI',
        trade_type: str = 'buy',
        period_days: int = 5,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        외국인 기간별 매매 상위 (ka10034)

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            trade_type: 매매구분 ('buy': 순매수, 'sell': 순매도)
            period_days: 기간 (1, 3, 5, 10, 20일)
            limit: 조회 건수

        Returns:
            외국인 기간별 매매 순위
        """
        market_map = {'KOSPI': '001', 'KOSDAQ': '101'}
        mrkt_tp = market_map.get(market.upper(), '001')

        trade_map = {'buy': '2', 'sell': '1'}
        trde_tp = trade_map.get(trade_type.lower(), '2')

        body = {
            "mrkt_tp": mrkt_tp,
            "trde_tp": trde_tp,
            "dt": str(period_days),
            "stex_tp": "1"
        }

        response = self.client.request(api_id="ka10034", body=body, path="rkinfo")

        if response and response.get('return_code') == 0:
            data_keys = [k for k in response.keys() if k not in ['return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key']]
            rank_list = []
            for key in data_keys:
                val = response.get(key)
                if isinstance(val, list) and len(val) > 0:
                    rank_list = val
                    break

            normalized_list = []
            for item in rank_list[:limit]:
                normalized_list.append({
                    'code': item.get('stk_cd', '').replace('_AL', ''),
                    'name': item.get('stk_nm', ''),
                    'price': int(float(item.get('cur_prc', '0').replace('+', '').replace('-', ''))),
                    'foreign_net_buy': int(float(item.get('frg_nt_qty', '0'))),  # 외국인 순매수량
                    'change_rate': float(item.get('flu_rt', '0').replace('+', '').replace('-', '')),
                })

            logger.info(f"외국인 {period_days}일 매매 {len(normalized_list)}개 조회")
            return normalized_list
        else:
            logger.error(f"외국인 기간별 매매 조회 실패: {response.get('return_msg')}")
            return []

    def get_foreign_continuous_trading_rank(
        self,
        market: str = 'KOSPI',
        trade_type: str = 'buy',
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        외국인 연속 순매매 상위 (ka10035)

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            trade_type: 매매구분 ('buy': 순매수, 'sell': 순매도)
            limit: 조회 건수

        Returns:
            외국인 연속 순매매 순위
        """
        market_map = {'KOSPI': '001', 'KOSDAQ': '101'}
        mrkt_tp = market_map.get(market.upper(), '001')

        trade_map = {'buy': '2', 'sell': '1'}
        trde_tp = trade_map.get(trade_type.lower(), '2')

        body = {
            "mrkt_tp": mrkt_tp,
            "trde_tp": trde_tp,
            "base_dt_tp": "0",
            "stex_tp": "1"
        }

        response = self.client.request(api_id="ka10035", body=body, path="rkinfo")

        if response and response.get('return_code') == 0:
            data_keys = [k for k in response.keys() if k not in ['return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key']]
            rank_list = []
            for key in data_keys:
                val = response.get(key)
                if isinstance(val, list) and len(val) > 0:
                    rank_list = val
                    break

            normalized_list = []
            for item in rank_list[:limit]:
                normalized_list.append({
                    'code': item.get('stk_cd', '').replace('_AL', ''),
                    'name': item.get('stk_nm', ''),
                    'price': int(float(item.get('cur_prc', '0').replace('+', '').replace('-', ''))),
                    'continuous_days': int(float(item.get('cont_dt', '0'))),  # 연속일수
                    'total_net_buy': int(float(item.get('tot_nt_qty', '0'))),  # 총 순매수량
                })

            logger.info(f"외국인 연속매매 {len(normalized_list)}개 조회")
            return normalized_list
        else:
            logger.error(f"외국인 연속 순매매 조회 실패: {response.get('return_msg')}")
            return []

    def get_foreign_institution_trading_rank(
        self,
        market: str = 'KOSPI',
        amount_or_qty: str = 'amount',
        date: str = None,
        limit: int = 20,
        investor_type: str = 'foreign_buy'
    ) -> List[Dict[str, Any]]:
        """
        외국인/기관 매매 상위 (ka90009)

        ⚠️ 주의: 이 API는 현재가를 제공하지 않습니다!
        각 항목은 4개의 카테고리로 구성됩니다:
        - for_netprps_: 외국인 순매수 상위
        - for_netslmt_: 외국인 순매도 상위
        - orgn_netprps_: 기관 순매수 상위
        - orgn_netslmt_: 기관 순매도 상위

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            amount_or_qty: 조회구분 ('amount': 금액, 'qty': 수량)
            date: 조회일 (YYYYMMDD, None이면 오늘)
            limit: 조회 건수
            investor_type: 투자자 유형 ('foreign_buy': 외국인 순매수, 'foreign_sell': 외국인 순매도,
                                      'institution_buy': 기관 순매수, 'institution_sell': 기관 순매도)

        Returns:
            외국인/기관 매매 순위 (현재가 없음)
        """
        from utils.trading_date import get_last_trading_date

        market_map = {'KOSPI': '001', 'KOSDAQ': '101'}
        mrkt_tp = market_map.get(market.upper(), '001')

        amt_qty_map = {'amount': '1', 'qty': '2'}
        amt_qty_tp = amt_qty_map.get(amount_or_qty.lower(), '1')

        if date is None:
            date = get_last_trading_date()  # 이미 'YYYYMMDD' 형식 문자열 반환

        body = {
            "mrkt_tp": mrkt_tp,
            "amt_qty_tp": amt_qty_tp,
            "qry_dt_tp": "1",
            "date": date,
            "stex_tp": "1"
        }

        response = self.client.request(api_id="ka90009", body=body, path="rkinfo")

        if response and response.get('return_code') == 0:
            # ka90009 API는 'frgnr_orgn_trde_upper' 키에 데이터 반환
            rank_list = response.get('frgnr_orgn_trde_upper', [])

            # 투자자 유형에 따른 필드명 매핑
            field_map = {
                'foreign_buy': ('for_netprps_stk_cd', 'for_netprps_stk_nm', 'for_netprps_amt', 'for_netprps_qty'),
                'foreign_sell': ('for_netslmt_stk_cd', 'for_netslmt_stk_nm', 'for_netslmt_amt', 'for_netslmt_qty'),
                'institution_buy': ('orgn_netprps_stk_cd', 'orgn_netprps_stk_nm', 'orgn_netprps_amt', 'orgn_netprps_qty'),
                'institution_sell': ('orgn_netslmt_stk_cd', 'orgn_netslmt_stk_nm', 'orgn_netslmt_amt', 'orgn_netslmt_qty'),
            }

            code_field, name_field, amt_field, qty_field = field_map.get(investor_type, field_map['foreign_buy'])

            normalized_list = []
            for item in rank_list[:limit]:
                normalized_list.append({
                    'code': item.get(code_field, '').replace('_AL', ''),
                    'name': item.get(name_field, ''),
                    'net_amount': int(float(item.get(amt_field, '0').replace('+', '').replace('-', ''))),  # 순매수/매도 금액 (백만원)
                    'net_qty': int(float(item.get(qty_field, '0').replace('+', '').replace('-', ''))),  # 순매수/매도 수량 (천주)
                })

            type_name = {
                'foreign_buy': '외국인 순매수',
                'foreign_sell': '외국인 순매도',
                'institution_buy': '기관 순매수',
                'institution_sell': '기관 순매도'
            }.get(investor_type, investor_type)

            logger.info(f"{type_name} {len(normalized_list)}개 조회")
            return normalized_list
        else:
            logger.error(f"외국인/기관 매매 조회 실패: {response.get('return_msg')}")
            return []

    def get_credit_ratio_rank(
        self,
        market: str = 'KOSPI',
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        신용비율 상위 (ka10033)

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            limit: 조회 건수

        Returns:
            신용비율 상위 순위
        """
        market_map = {'KOSPI': '001', 'KOSDAQ': '101'}
        mrkt_tp = market_map.get(market.upper(), '001')

        body = {
            "mrkt_tp": mrkt_tp,
            "trde_qty_tp": "100",
            "stk_cnd": "0",
            "updown_incls": "1",
            "crd_cnd": "0",
            "stex_tp": "3"
        }

        response = self.client.request(api_id="ka10033", body=body, path="rkinfo")

        if response and response.get('return_code') == 0:
            data_keys = [k for k in response.keys() if k not in ['return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key']]
            rank_list = []
            for key in data_keys:
                val = response.get(key)
                if isinstance(val, list) and len(val) > 0:
                    rank_list = val
                    break

            normalized_list = []
            for item in rank_list[:limit]:
                normalized_list.append({
                    'code': item.get('stk_cd', '').replace('_AL', ''),
                    'name': item.get('stk_nm', ''),
                    'price': int(float(item.get('cur_prc', '0').replace('+', '').replace('-', ''))),
                    'credit_ratio': float(item.get('crd_rt', '0')),  # 신용비율
                    'credit_balance': int(float(item.get('crd_rmn_qty', '0'))),  # 신용잔고
                })

            logger.info(f"신용비율 {len(normalized_list)}개 조회")
            return normalized_list
        else:
            logger.error(f"신용비율 조회 실패: {response.get('return_msg')}")
            return []

    def get_investor_intraday_trading_rank(
        self,
        market: str = 'KOSPI',
        investor_type: str = 'foreign',
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        장중 투자자별 매매 상위 (ka10065)

        ⚠️ 주의: 이 API는 현재가를 제공하지 않습니다!
        매도수량, 매수수량, 순매수량만 제공됩니다.

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            investor_type: 투자자구분 ('foreign': 외국인, 'institution': 기관, 'individual': 개인)
            limit: 조회 건수

        Returns:
            투자자별 매매 순위 (현재가 없음)
        """
        market_map = {'KOSPI': '001', 'KOSDAQ': '101'}
        mrkt_tp = market_map.get(market.upper(), '001')

        # 투자자 타입: 9000=외국인, 1000=개인, 8000=기관
        investor_map = {
            'foreign': '9000',
            'institution': '8000',
            'individual': '1000'
        }
        orgn_tp = investor_map.get(investor_type.lower(), '9000')

        body = {
            "trde_tp": "1",  # 1: 순매수
            "mrkt_tp": mrkt_tp,
            "orgn_tp": orgn_tp
        }

        response = self.client.request(api_id="ka10065", body=body, path="rkinfo")

        if response and response.get('return_code') == 0:
            # ka10065 API는 'opmr_invsr_trde_upper' 키에 데이터 반환
            rank_list = response.get('opmr_invsr_trde_upper', [])

            normalized_list = []
            for item in rank_list[:limit]:
                # 값에서 +,- 기호 제거하고 숫자로 변환
                sel_qty = int(float(item.get('sel_qty', '0').replace('+', '').replace('-', '')))
                buy_qty = int(float(item.get('buy_qty', '0').replace('+', '').replace('-', '')))
                netslmt = int(float(item.get('netslmt', '0').replace('+', '').replace('-', '')))

                normalized_list.append({
                    'code': item.get('stk_cd', '').replace('_AL', ''),
                    'name': item.get('stk_nm', ''),
                    'sell_qty': sel_qty,      # 매도수량
                    'buy_qty': buy_qty,       # 매수수량
                    'net_buy_qty': netslmt,   # 순매수량 (매수-매도)
                })

            investor_name = {'foreign': '외국인', 'institution': '기관', 'individual': '개인'}.get(investor_type.lower(), investor_type)
            logger.info(f"{investor_name} 장중매매 {len(normalized_list)}개 조회")
            return normalized_list
        else:
            logger.error(f"투자자별 매매 조회 실패: {response.get('return_msg')}")
            return []


__all__ = ['RankingAPI']
