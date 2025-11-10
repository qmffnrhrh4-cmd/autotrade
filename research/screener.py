"""
research/screener.py
종목 스크리닝 모듈
"""
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class Screener:
    """
    종목 스크리닝 클래스
    
    주요 기능:
    - 거래량 기준 필터링
    - 가격대 기준 필터링
    - 등락률 기준 필터링
    - 복합 조건 스크리닝
    """
    
    def __init__(self, client):
        """
        Screener 초기화
        
        Args:
            client: KiwoomRESTClient 인스턴스
        """
        self.client = client
        from .data_fetcher import DataFetcher
        self.fetcher = DataFetcher(client)
        logger.info("Screener 초기화 완료")
    
    # ==================== 단일 조건 스크리닝 ====================

    def filter_exclude_etf_and_derivatives(
        self,
        stocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        ETF, 레버리지, 인버스, SPAC 등 제외 필터

        Args:
            stocks: 종목 리스트

        Returns:
            필터링된 종목 리스트 (일반 주식만)
        """
        # 제외할 키워드 (대소문자 구분 안함)
        exclude_keywords = [
            # ETF 관련
            'ETF', 'KODEX', 'TIGER', 'KINDEX', 'ARIRANG', 'HANARO',
            'KBSTAR', 'KOSEF', 'TIMEFOLIO', 'SOL',
            # 레버리지/인버스
            '레버리지', '인버스', '레버', '인버',
            'LEVERAGE', 'INVERSE',
            # SPAC
            'SPAC', '스팩',
            # 기타
            '리츠', 'REIT',
        ]

        filtered = []
        excluded_count = 0

        for stock in stocks:
            name = stock.get('name', '').upper()

            # 제외 키워드 체크
            should_exclude = False
            for keyword in exclude_keywords:
                if keyword.upper() in name:
                    should_exclude = True
                    excluded_count += 1
                    logger.debug(f"제외: {stock.get('name')} (키워드: {keyword})")
                    break

            if not should_exclude:
                filtered.append(stock)

        logger.info(f"ETF/레버리지/SPAC 필터링 완료: {excluded_count}개 제외, {len(filtered)}개 남음")
        return filtered

    # ==================== 단일 조건 스크리닝 ====================

    def screen_by_volume(
        self,
        min_volume: int = 100000,
        market: str = 'ALL',
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        거래량 기준 스크리닝
        
        Args:
            min_volume: 최소 거래량
            market: 시장구분 ('ALL', 'KOSPI', 'KOSDAQ')
            limit: 조회 건수
        
        Returns:
            필터링된 종목 리스트
        """
        # 거래량 순위 조회
        volume_rank = self.fetcher.get_volume_rank(market, limit)
        
        # 최소 거래량 필터
        filtered = [
            stock for stock in volume_rank
            if int(stock.get('volume', 0)) >= min_volume
        ]
        
        logger.info(f"거래량 스크리닝 완료: {len(filtered)}개 종목 (최소 {min_volume:,}주)")
        return filtered
    
    def screen_by_price_range(
        self,
        min_price: int = 1000,
        max_price: int = 1000000,
        stocks: List[Dict[str, Any]] = None,
        market: str = 'ALL'
    ) -> List[Dict[str, Any]]:
        """
        가격대 기준 스크리닝
        
        Args:
            min_price: 최소 가격 (원)
            max_price: 최대 가격 (원)
            stocks: 대상 종목 리스트 (None이면 거래량 순위 조회)
            market: 시장구분
        
        Returns:
            필터링된 종목 리스트
        """
        if stocks is None:
            stocks = self.fetcher.get_volume_rank(market, 100)
        
        # 가격 필터
        filtered = [
            stock for stock in stocks
            if min_price <= int(stock.get('current_price', 0)) <= max_price
        ]
        
        logger.info(f"가격대 스크리닝 완료: {len(filtered)}개 종목 ({min_price:,}원 ~ {max_price:,}원)")
        return filtered
    
    def screen_by_price_change(
        self,
        min_rate: float = 1.0,
        max_rate: float = 15.0,
        market: str = 'ALL',
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        등락률 기준 스크리닝
        
        Args:
            min_rate: 최소 등락률 (%)
            max_rate: 최대 등락률 (%)
            market: 시장구분
            limit: 조회 건수
        
        Returns:
            필터링된 종목 리스트
        """
        # 상승률 순위 조회
        rise_rank = self.fetcher.get_price_change_rank(market, 'rise', limit)
        
        # 등락률 필터
        filtered = [
            stock for stock in rise_rank
            if min_rate <= float(stock.get('change_rate', 0)) <= max_rate
        ]
        
        logger.info(f"등락률 스크리닝 완료: {len(filtered)}개 종목 ({min_rate}% ~ {max_rate}%)")
        return filtered
    
    def screen_by_trading_value(
        self,
        min_value: int = 1000000000,
        market: str = 'ALL',
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        거래대금 기준 스크리닝

        Args:
            min_value: 최소 거래대금 (원)
            market: 시장구분
            limit: 조회 건수

        Returns:
            필터링된 종목 리스트
        """
        # 거래대금 순위 조회
        trading_rank = self.fetcher.get_trading_value_rank(market, limit)

        # 최소 거래대금 필터
        filtered = [
            stock for stock in trading_rank
            if int(stock.get('trading_value', 0)) >= min_value
        ]

        logger.info(f"거래대금 스크리닝 완료: {len(filtered)}개 종목 (최소 {min_value:,}원)")
        return filtered

    # v5.9: 투자자별 매매 기준 스크리닝
    def screen_by_foreign_buying(
        self,
        market: str = 'KOSPI',
        min_net_amount: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        외국인 순매수 종목 스크리닝 (v5.9 NEW)

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            min_net_amount: 최소 순매수 금액 (백만원)
            limit: 조회 건수

        Returns:
            외국인 순매수 종목 리스트
        """
        # 외국인 순매수 순위 조회
        foreign_rank = self.fetcher.get_foreign_buying_rank(market, limit=limit)

        # 최소 순매수 금액 필터
        filtered = [
            stock for stock in foreign_rank
            if int(stock.get('net_amount', 0)) >= min_net_amount
        ]

        logger.info(f"외국인 순매수 스크리닝 완료: {len(filtered)}개 종목 (최소 {min_net_amount:,}백만원)")
        return filtered

    def screen_by_institution_buying(
        self,
        market: str = 'KOSPI',
        min_net_amount: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        기관 순매수 종목 스크리닝 (v5.9 NEW)

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            min_net_amount: 최소 순매수 금액 (백만원)
            limit: 조회 건수

        Returns:
            기관 순매수 종목 리스트
        """
        # 기관 순매수 순위 조회
        inst_rank = self.fetcher.get_institution_buying_rank(market, limit=limit)

        # 최소 순매수 금액 필터
        filtered = [
            stock for stock in inst_rank
            if int(stock.get('net_amount', 0)) >= min_net_amount
        ]

        logger.info(f"기관 순매수 스크리닝 완료: {len(filtered)}개 종목 (최소 {min_net_amount:,}백만원)")
        return filtered

    def screen_by_smart_money(
        self,
        market: str = 'KOSPI',
        min_foreign_amount: int = 0,
        min_inst_amount: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        스마트머니 (외국인+기관 동시 순매수) 종목 스크리닝 (v5.9 NEW)

        외국인과 기관이 동시에 순매수하는 종목을 찾습니다.
        일반적으로 이런 종목은 상승 가능성이 높습니다.

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            min_foreign_amount: 최소 외국인 순매수 금액 (백만원)
            min_inst_amount: 최소 기관 순매수 금액 (백만원)
            limit: 조회 건수

        Returns:
            스마트머니 종목 리스트
        """
        # 외국인 & 기관 순매수 순위 조회
        foreign_rank = self.fetcher.get_foreign_buying_rank(market, limit=limit)
        inst_rank = self.fetcher.get_institution_buying_rank(market, limit=limit)

        # 종목코드로 매핑
        foreign_map = {s['code']: s for s in foreign_rank}
        inst_map = {s['code']: s for s in inst_rank}

        # 교집합 찾기 (둘 다 순매수)
        smart_money = []
        for code in set(foreign_map.keys()) & set(inst_map.keys()):
            foreign_data = foreign_map[code]
            inst_data = inst_map[code]

            foreign_amt = int(foreign_data.get('net_amount', 0))
            inst_amt = int(inst_data.get('net_amount', 0))

            # 최소 금액 조건 체크
            if foreign_amt >= min_foreign_amount and inst_amt >= min_inst_amount:
                smart_money.append({
                    'code': code,
                    'name': foreign_data.get('name', ''),
                    'foreign_net_amount': foreign_amt,
                    'institution_net_amount': inst_amt,
                    'total_net_amount': foreign_amt + inst_amt,
                    'foreign_net_qty': foreign_data.get('net_qty', 0),
                    'institution_net_qty': inst_data.get('net_qty', 0),
                })

        # 총 순매수 금액으로 정렬
        smart_money.sort(key=lambda x: x['total_net_amount'], reverse=True)

        logger.info(f"스마트머니 스크리닝 완료: {len(smart_money)}개 종목 (외국인+기관 동시 순매수)")
        return smart_money

    def screen_by_foreign_selling(
        self,
        market: str = 'KOSPI',
        min_net_amount: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        외국인 순매도 종목 스크리닝 (v5.9 NEW)

        역발상 투자나 저점 매수 타이밍을 찾는데 활용

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            min_net_amount: 최소 순매도 금액 (백만원)
            limit: 조회 건수

        Returns:
            외국인 순매도 종목 리스트
        """
        # 외국인 순매도 순위 조회
        foreign_rank = self.fetcher.get_foreign_selling_rank(market, limit=limit)

        # 최소 순매도 금액 필터
        filtered = [
            stock for stock in foreign_rank
            if int(stock.get('net_amount', 0)) >= min_net_amount
        ]

        logger.info(f"외국인 순매도 스크리닝 완료: {len(filtered)}개 종목 (최소 {min_net_amount:,}백만원)")
        return filtered

    def screen_by_institution_selling(
        self,
        market: str = 'KOSPI',
        min_net_amount: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        기관 순매도 종목 스크리닝 (v5.9 NEW)

        Args:
            market: 시장구분 ('KOSPI', 'KOSDAQ')
            min_net_amount: 최소 순매도 금액 (백만원)
            limit: 조회 건수

        Returns:
            기관 순매도 종목 리스트
        """
        # 기관 순매도 순위 조회
        inst_rank = self.fetcher.get_institution_selling_rank(market, limit=limit)

        # 최소 순매도 금액 필터
        filtered = [
            stock for stock in inst_rank
            if int(stock.get('net_amount', 0)) >= min_net_amount
        ]

        logger.info(f"기관 순매도 스크리닝 완료: {len(filtered)}개 종목 (최소 {min_net_amount:,}백만원)")
        return filtered

    # ==================== 복합 조건 스크리닝 ====================

    def screen_stocks(
        self,
        min_volume: int = 100000,
        min_price: int = 1000,
        max_price: int = 1000000,
        min_rate: float = 1.0,
        max_rate: float = 15.0,
        min_market_cap: int = 0,
        market: str = 'ALL',
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        종목 스크리닝 (screen_combined의 별칭)

        Args:
            min_volume: 최소 거래량
            min_price: 최소 가격
            max_price: 최대 가격
            min_rate: 최소 등락률
            max_rate: 최대 등락률
            min_market_cap: 최소 시가총액 (현재 미사용)
            market: 시장구분
            limit: 초기 조회 건수

        Returns:
            필터링된 종목 리스트
        """
        return self.screen_combined(
            min_volume=min_volume,
            min_price=min_price,
            max_price=max_price,
            min_rate=min_rate,
            max_rate=max_rate,
            market=market,
            limit=limit
        )

    def screen_combined(
        self,
        min_volume: int = 100000,
        min_price: int = 1000,
        max_price: int = 1000000,
        min_rate: float = 1.0,
        max_rate: float = 15.0,
        market: str = 'ALL',
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        복합 조건 스크리닝
        
        Args:
            min_volume: 최소 거래량
            min_price: 최소 가격
            max_price: 최대 가격
            min_rate: 최소 등락률
            max_rate: 최대 등락률
            market: 시장구분
            limit: 초기 조회 건수
        
        Returns:
            필터링된 종목 리스트
        """
        logger.info(f"복합 조건 스크리닝 시작...")
        logger.info(f"  - 거래량: {min_volume:,}주 이상")
        logger.info(f"  - 가격: {min_price:,}원 ~ {max_price:,}원")
        logger.info(f"  - 등락률: {min_rate}% ~ {max_rate}%")
        
        # 1단계: 거래량 순위 조회
        candidates = self.fetcher.get_volume_rank(market, limit)
        logger.info(f"1단계 후보: {len(candidates)}개")
        
        # 2단계: 복합 필터 적용
        filtered = []
        for stock in candidates:
            volume = int(stock.get('volume', 0))
            price = int(stock.get('current_price', 0))
            change_rate = float(stock.get('change_rate', 0))
            
            # 모든 조건 만족 체크
            if (volume >= min_volume and
                min_price <= price <= max_price and
                min_rate <= change_rate <= max_rate):
                filtered.append(stock)
        
        logger.info(f"복합 조건 스크리닝 완료: {len(filtered)}개 종목")
        return filtered
    
    def screen_with_filters(
        self,
        filters: Dict[str, Any],
        market: str = 'ALL'
    ) -> List[Dict[str, Any]]:
        """
        딕셔너리 필터로 스크리닝
        
        Args:
            filters: 필터 조건 딕셔너리
                {
                    'min_volume': 100000,
                    'min_price': 1000,
                    'max_price': 100000,
                    'min_rate': 1.0,
                    'max_rate': 15.0,
                    'min_market_cap': 1000000000000
                }
            market: 시장구분
        
        Returns:
            필터링된 종목 리스트
        """
        min_volume = filters.get('min_volume', 100000)
        min_price = filters.get('min_price', 1000)
        max_price = filters.get('max_price', 1000000)
        min_rate = filters.get('min_rate', 1.0)
        max_rate = filters.get('max_rate', 15.0)
        
        return self.screen_combined(
            min_volume=min_volume,
            min_price=min_price,
            max_price=max_price,
            min_rate=min_rate,
            max_rate=max_rate,
            market=market
        )
    
    # ==================== 고급 스크리닝 ====================
    
    def screen_with_investor_trend(
        self,
        stocks: List[Dict[str, Any]],
        foreign_net_positive: bool = True,
        institution_net_positive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        투자자 매매 동향 기준 필터링
        
        Args:
            stocks: 대상 종목 리스트
            foreign_net_positive: 외국인 순매수 조건
            institution_net_positive: 기관 순매수 조건
        
        Returns:
            필터링된 종목 리스트
        """
        filtered = []
        
        for stock in stocks:
            stock_code = stock.get('stock_code')
            if not stock_code:
                continue
            
            # 투자자 매매 동향 조회
            investor_info = self.fetcher.get_investor_trading(stock_code)
            if not investor_info:
                continue
            
            foreign_net = int(investor_info.get('foreign_net', 0))
            institution_net = int(investor_info.get('institution_net', 0))
            
            # 조건 체크
            foreign_ok = (foreign_net > 0) if foreign_net_positive else (foreign_net <= 0)
            institution_ok = (institution_net > 0) if institution_net_positive else (institution_net <= 0)
            
            if foreign_ok and institution_ok:
                stock['investor_info'] = investor_info
                filtered.append(stock)
        
        logger.info(f"투자자 동향 필터링 완료: {len(filtered)}개 종목")
        return filtered
    
    def screen_momentum_stocks(
        self,
        market: str = 'ALL',
        min_rate: float = 3.0,
        min_volume_ratio: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        모멘텀 종목 스크리닝
        
        Args:
            market: 시장구분
            min_rate: 최소 등락률 (%)
            min_volume_ratio: 평균 대비 최소 거래량 비율
        
        Returns:
            모멘텀 종목 리스트
        """
        # 상승률 순위 조회
        rise_rank = self.fetcher.get_price_change_rank(market, 'rise', 100)
        
        filtered = []
        for stock in rise_rank:
            change_rate = float(stock.get('change_rate', 0))
            
            # 등락률 조건
            if change_rate < min_rate:
                continue
            
            # 거래량 조건은 실제 구현 시 추가
            # (현재 거래량 / 평균 거래량 비율 계산 필요)
            
            filtered.append(stock)
        
        logger.info(f"모멘텀 종목 스크리닝 완료: {len(filtered)}개 종목")
        return filtered
    
    def get_screening_summary(
        self,
        stocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        스크리닝 결과 요약
        
        Args:
            stocks: 종목 리스트
        
        Returns:
            요약 정보
            {
                'count': 10,
                'avg_price': 50000,
                'avg_volume': 500000,
                'avg_change_rate': 5.2,
                'price_range': [10000, 100000],
                'top_3': [상위 3개 종목]
            }
        """
        if not stocks:
            return {
                'count': 0,
                'avg_price': 0,
                'avg_volume': 0,
                'avg_change_rate': 0,
                'price_range': [0, 0],
                'top_3': []
            }
        
        prices = [int(s.get('current_price', 0)) for s in stocks]
        volumes = [int(s.get('volume', 0)) for s in stocks]
        rates = [float(s.get('change_rate', 0)) for s in stocks]
        
        summary = {
            'count': len(stocks),
            'avg_price': int(sum(prices) / len(prices)) if prices else 0,
            'avg_volume': int(sum(volumes) / len(volumes)) if volumes else 0,
            'avg_change_rate': round(sum(rates) / len(rates), 2) if rates else 0,
            'price_range': [min(prices), max(prices)] if prices else [0, 0],
            'top_3': stocks[:3]
        }
        
        logger.info(f"스크리닝 요약: {summary['count']}개 종목, 평균 등락률 {summary['avg_change_rate']}%")
        return summary


__all__ = ['Screener']