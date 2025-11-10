"""
research/analyzer.py
데이터 분석 모듈
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, time

logger = logging.getLogger(__name__)


class Analyzer:
    """
    데이터 분석 클래스
    
    주요 기능:
    - AI 분석용 데이터 수집
    - 매수 가능 수량 계산
    - 기술적 지표 계산
    - 장 운영 시간 확인
    """
    
    def __init__(self, client):
        """
        Analyzer 초기화
        
        Args:
            client: KiwoomRESTClient 인스턴스
        """
        self.client = client
        from .data_fetcher import DataFetcher
        self.fetcher = DataFetcher(client)
        logger.info("Analyzer 초기화 완료")
    
    # ==================== AI 분석용 데이터 ====================
    
    def get_stock_data_for_analysis(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        AI 분석용 종목 데이터 수집
        
        Args:
            stock_code: 종목코드
        
        Returns:
            분석용 종목 데이터
            {
                'stock_code': '005930',
                'stock_name': '삼성전자',
                'current_price': 72000,
                'change_rate': 1.41,
                'volume': 10000000,
                'trading_value': 720000000000,
                'market_cap': 500000000000000,
                'per': 15.5,
                'pbr': 1.2,
                'investor': {외국인/기관 매매 동향},
                'daily_data': [일봉 20개],
                'technical': {기술적 지표},
                'timestamp': '2025-01-30 15:30:00'
            }
        """
        # 현재가 정보
        price_info = self.fetcher.get_current_price(stock_code)
        if not price_info:
            logger.error(f"{stock_code} 현재가 조회 실패")
            return None
        
        # 종목 상세 정보
        stock_info = self.fetcher.get_stock_info(stock_code)
        
        # 투자자별 매매 동향
        investor_info = self.fetcher.get_investor_trading(stock_code)
        
        # 일봉 데이터 (최근 20일)
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        daily_data = self.fetcher.get_daily_price(stock_code, start_date, end_date)
        
        # 기술적 지표 계산
        technical = self._calculate_technical_indicators(daily_data)
        
        # 데이터 통합
        analysis_data = {
            'stock_code': stock_code,
            'stock_name': price_info.get('stock_name', ''),
            'current_price': int(float(price_info.get('current_price', 0))),
            'change_rate': float(price_info.get('change_rate', 0)),
            'volume': int(float(price_info.get('volume', 0))),
            'trading_value': int(float(price_info.get('trading_value', 0))),
            'open_price': int(float(price_info.get('open_price', 0))),
            'high_price': int(float(price_info.get('high_price', 0))),
            'low_price': int(float(price_info.get('low_price', 0))),
            'prev_close': int(float(price_info.get('prev_close', 0))),
            'market_cap': int(float(stock_info.get('market_cap', 0))) if stock_info else 0,
            'per': float(stock_info.get('per', 0)) if stock_info else 0,
            'pbr': float(stock_info.get('pbr', 0)) if stock_info else 0,
            'eps': float(stock_info.get('eps', 0)) if stock_info else 0,
            'bps': float(stock_info.get('bps', 0)) if stock_info else 0,
            'dividend_yield': float(stock_info.get('dividend_yield', 0)) if stock_info else 0,
            'investor': investor_info if investor_info else {},
            'daily_data': daily_data if daily_data else [],
            'technical': technical,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        logger.info(f"{stock_code} 분석용 데이터 수집 완료")
        return analysis_data
    
    # ==================== 매수 가능 계산 ====================
    
    def get_available_cash(self, account_number: str = None) -> int:
        """
        주문 가능 현금 조회

        Args:
            account_number: 계좌번호

        Returns:
            주문 가능 금액 (원)
        """
        deposit = self.fetcher.get_deposit(account_number)

        if deposit:
            available = int(float(deposit.get('ord_alow_amt', 0)))
            logger.info(f"주문 가능 현금: {available:,}원")
            return available
        else:
            logger.error("주문 가능 현금 조회 실패")
            return 0
    
    def get_buyable_quantity(
        self,
        stock_code: str,
        price: int = None,
        account_number: str = None
    ) -> int:
        """
        매수 가능 수량 계산
        
        Args:
            stock_code: 종목코드
            price: 매수 희망가 (None이면 현재가)
            account_number: 계좌번호
        
        Returns:
            매수 가능 수량 (주)
        """
        # 주문 가능 현금 조회
        available_cash = self.get_available_cash(account_number)
        
        if available_cash == 0:
            return 0
        
        # 가격 결정
        if price is None:
            price_info = self.fetcher.get_current_price(stock_code)
            if not price_info:
                return 0
            price = int(float(price_info.get('current_price', 0)))

        if price == 0:
            return 0

        # 매수 가능 수량 계산
        # 수수료: 0.015% (매수), 세금: 0.3% (매도 시만)
        commission_rate = 0.00015
        buyable_quantity = int(float(available_cash / (price * (1 + commission_rate))))
        
        logger.info(f"{stock_code} 매수 가능 수량: {buyable_quantity}주 @ {price:,}원")
        return buyable_quantity
    
    def calculate_order_amount(
        self,
        price: int,
        quantity: int,
        order_type: str = 'buy'
    ) -> Dict[str, int]:
        """
        주문 금액 계산 (수수료 포함)
        
        Args:
            price: 주문가격
            quantity: 주문수량
            order_type: 주문유형 ('buy': 매수, 'sell': 매도)
        
        Returns:
            주문 금액 정보
            {
                'order_amount': 1000000,      # 주문금액 (가격 * 수량)
                'commission': 150,            # 수수료
                'tax': 3000,                  # 세금 (매도 시만)
                'total_amount': 1003150       # 총 금액
            }
        """
        order_amount = price * quantity
        commission = int(order_amount * 0.00015)  # 수수료 0.015%
        
        if order_type.lower() == 'sell':
            tax = int(order_amount * 0.003)  # 증권거래세 0.3% (매도 시만)
            total_amount = order_amount - commission - tax
        else:
            tax = 0
            total_amount = order_amount + commission
        
        result = {
            'order_amount': order_amount,
            'commission': commission,
            'tax': tax,
            'total_amount': total_amount
        }
        
        logger.debug(f"주문금액 계산: {result}")
        return result
    
    # ==================== 기술적 지표 계산 ====================
    
    def _calculate_technical_indicators(
        self,
        daily_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        기술적 지표 계산
        
        Args:
            daily_data: 일봉 데이터
        
        Returns:
            기술적 지표
            {
                'ma5': 72000,      # 5일 이동평균
                'ma20': 70000,     # 20일 이동평균
                'ma60': 68000,     # 60일 이동평균
                'rsi': 65.5,       # RSI (14일)
                'volume_ma5': 10000000,  # 거래량 5일 이동평균
                'price_position': 0.85,  # 가격 위치 (0~1)
            }
        """
        if not daily_data or len(daily_data) == 0:
            return {}
        
        # 종가 리스트 추출
        closes = [float(d.get('close', 0)) for d in daily_data]
        volumes = [int(float(d.get('volume', 0))) for d in daily_data]
        
        technical = {}
        
        # 이동평균 계산
        technical['ma5'] = self._calculate_ma(closes, 5)
        technical['ma20'] = self._calculate_ma(closes, 20)
        technical['ma60'] = self._calculate_ma(closes, 60)
        
        # 거래량 이동평균
        technical['volume_ma5'] = self._calculate_ma(volumes, 5)
        technical['volume_ma20'] = self._calculate_ma(volumes, 20)
        
        # RSI 계산
        technical['rsi'] = self._calculate_rsi(closes, 14)
        
        # 가격 위치 계산 (최근 20일 기준)
        if len(closes) >= 20:
            recent_closes = closes[:20]
            current_price = closes[0]
            min_price = min(recent_closes)
            max_price = max(recent_closes)
            
            if max_price > min_price:
                technical['price_position'] = (current_price - min_price) / (max_price - min_price)
            else:
                technical['price_position'] = 0.5
        else:
            technical['price_position'] = 0.5
        
        return technical
    
    def _calculate_ma(self, data: List[float], period: int) -> float:
        """
        이동평균 계산
        
        Args:
            data: 데이터 리스트
            period: 기간
        
        Returns:
            이동평균값
        """
        if len(data) < period:
            return 0.0
        
        recent_data = data[:period]
        return sum(recent_data) / period if recent_data else 0.0
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """
        RSI (Relative Strength Index) 계산
        
        Args:
            closes: 종가 리스트
            period: 기간 (기본 14일)
        
        Returns:
            RSI 값 (0~100)
        """
        if len(closes) < period + 1:
            return 50.0  # 데이터 부족 시 중립값
        
        # 가격 변화 계산
        changes = []
        for i in range(period):
            if i + 1 < len(closes):
                change = closes[i] - closes[i + 1]
                changes.append(change)
        
        if not changes:
            return 50.0
        
        # 상승/하락 분리
        gains = [c if c > 0 else 0 for c in changes]
        losses = [-c if c < 0 else 0 for c in changes]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    # ==================== 시장 상태 분석 ====================

    def is_market_open(self) -> bool:
        """
        장 운영 시간 확인 (정규장 + 시간외 + NXT)

        Returns:
            장 개장 여부
        """
        market_info = self.get_market_status()
        is_open = market_info['is_trading_hours']
        market_type = market_info['market_type']

        if is_open:
            logger.info(f"장 운영 상태: {market_type} (현재 시각: {market_info['current_time']})")
        else:
            logger.info(f"장 운영 상태: 폐장 (현재 시각: {market_info['current_time']})")

        return is_open
    
    def get_market_status(self) -> Dict[str, Any]:
        """
        시장 상태 정보 (정규장 + NXT 시장)

        NXT 시장 운영 시간: 오전 8시 ~ 오후 8시
        - 프리마켓: 08:00~08:50 (지정가만)
        - 메인마켓: 09:00~15:20
        - KRX 종가 결정: 15:20~15:30 (신규 주문 불가, 취소만 가능)
        - NXT 일시 중단: 15:30~15:40 (거래 불가)
        - 애프터마켓: 15:40~20:00 (지정가만)

        Returns:
            시장 상태 정보
            {
                'is_trading_hours': True,
                'is_test_mode': False,
                'market_type': 'NXT 프리마켓',
                'current_time': '15:30:00',
                'market_status': 'NXT 프리마켓 운영 중',
                'next_open': '2025-01-31 08:00:00',
                'order_type_limit': 'limit_only'  # 'limit_only' or 'all'
            }
        """
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()

        # 시장 유형 및 거래 가능 여부 판단
        is_trading_hours = False
        is_test_mode = False
        market_type = '폐장'
        market_status = '폐장'
        order_type_limit = 'all'  # 'limit_only' or 'all'
        can_cancel_only = False  # 취소만 가능한지 여부

        # 주말 체크 - 종가 기준 테스트 모드
        if weekday >= 5:  # 토요일, 일요일
            market_status = '주말 (종가 테스트 모드)'
            is_trading_hours = True  # 테스트 모드 활성화
            is_test_mode = True
            market_type = '테스트 모드'

        # 평일 NXT 시장 시간 체크
        else:
            # 1. NXT 프리마켓: 08:00 ~ 08:50 (지정가만)
            if time(8, 0) <= current_time < time(8, 50):
                is_trading_hours = True
                market_type = 'NXT 프리마켓'
                market_status = 'NXT 프리마켓 운영 중 (지정가만)'
                is_test_mode = False
                order_type_limit = 'limit_only'

            # 2. NXT 프리마켓 종료 대기: 08:50 ~ 09:00
            elif time(8, 50) <= current_time < time(9, 0):
                is_trading_hours = False
                market_type = 'NXT 프리마켓 종료'
                market_status = 'NXT 메인마켓 시작 대기'
                is_test_mode = False

            # 3. NXT 메인마켓: 09:00 ~ 15:20
            elif time(9, 0) <= current_time < time(15, 20):
                is_trading_hours = True
                market_type = 'NXT 메인마켓'
                market_status = 'NXT 메인마켓 운영 중'
                is_test_mode = False
                order_type_limit = 'all'

            # 4. KRX 종가 결정 시간: 15:20 ~ 15:30 (취소만 가능)
            elif time(15, 20) <= current_time < time(15, 30):
                is_trading_hours = True
                market_type = 'KRX 종가 결정'
                market_status = 'KRX 종가 결정 시간 (취소만 가능)'
                is_test_mode = False
                can_cancel_only = True

            # 5. NXT 일시 중단: 15:30 ~ 15:40
            elif time(15, 30) <= current_time < time(15, 40):
                is_trading_hours = False
                market_type = 'NXT 일시 중단'
                market_status = 'NXT 애프터마켓 시작 대기'
                is_test_mode = False

            # 6. NXT 애프터마켓: 15:40 ~ 20:00 (지정가만)
            elif time(15, 40) <= current_time < time(20, 0):
                is_trading_hours = True
                market_type = 'NXT 애프터마켓'
                market_status = 'NXT 애프터마켓 운영 중 (지정가만)'
                is_test_mode = False
                order_type_limit = 'limit_only'

            # 7. 그 외 시간 (폐장) - 종가 테스트 모드
            else:
                is_trading_hours = True  # 테스트 모드 활성화
                is_test_mode = True
                market_type = '테스트 모드'
                if current_time < time(8, 0):
                    market_status = '장 시작 전 (종가 테스트 모드)'
                elif current_time >= time(20, 0):
                    market_status = '장 종료 후 (종가 테스트 모드)'

        # 다음 개장 시간 계산
        next_open = self._calculate_next_market_open(now)

        return {
            'is_trading_hours': is_trading_hours,
            'is_test_mode': is_test_mode,
            'market_type': market_type,
            'current_time': now.strftime('%H:%M:%S'),
            'weekday': ['월', '화', '수', '목', '금', '토', '일'][weekday],
            'market_status': market_status,
            'next_open': next_open.strftime('%Y-%m-%d %H:%M:%S') if next_open else None,
            'order_type_limit': order_type_limit,  # 주문 유형 제한
            'can_cancel_only': can_cancel_only,  # 취소만 가능 여부
            # 호환성을 위한 필드
            'is_open': is_trading_hours
        }
    
    def _calculate_next_market_open(self, now: datetime) -> Optional[datetime]:
        """다음 NXT 장 시작 시간 계산 (오전 8시)"""
        current_time = now.time()
        weekday = now.weekday()

        # 오늘 NXT 시장 시작 전이면 오늘 08:00
        if weekday < 5 and current_time < time(8, 0):
            return datetime.combine(now.date(), time(8, 0))

        # 평일이고 NXT 시장 마감 후면 내일 08:00
        if weekday < 4:  # 월~목
            next_day = now + timedelta(days=1)
            return datetime.combine(next_day.date(), time(8, 0))

        # 금요일 장 마감 후 또는 주말이면 다음 월요일 08:00
        days_until_monday = (7 - weekday) % 7
        if days_until_monday == 0:
            days_until_monday = 7

        next_monday = now + timedelta(days=days_until_monday)
        return datetime.combine(next_monday.date(), time(8, 0))
    
    # ==================== 포지션 분석 ====================
    
    def analyze_portfolio(
        self,
        account_number: str = None
    ) -> Dict[str, Any]:
        """
        포트폴리오 분석
        
        Args:
            account_number: 계좌번호
        
        Returns:
            포트폴리오 분석 결과
            {
                'total_assets': 10000000,
                'cash': 3000000,
                'stocks_value': 7000000,
                'profit_loss': 500000,
                'profit_loss_rate': 7.14,
                'holdings_count': 5,
                'holdings': [보유 종목 리스트]
            }
        """
        # 예수금 조회
        deposit = self.fetcher.get_deposit(account_number)
        cash = int(float(deposit.get('deposit_available', 0))) if deposit else 0
        
        # 보유 종목 조회
        holdings = self.fetcher.get_holdings(account_number)
        
        # 보유 종목 평가액 및 손익 계산
        stocks_value = 0
        total_profit_loss = 0
        
        for holding in holdings:
            stocks_value += holding.get('evaluation_amount', 0)
            total_profit_loss += holding.get('profit_loss', 0)
        
        # 총 자산
        total_assets = cash + stocks_value
        
        # 수익률 계산
        if total_assets > 0 and total_profit_loss != 0:
            profit_loss_rate = (total_profit_loss / (total_assets - total_profit_loss)) * 100
        else:
            profit_loss_rate = 0.0
        
        analysis = {
            'total_assets': total_assets,
            'cash': cash,
            'cash_ratio': (cash / total_assets * 100) if total_assets > 0 else 0,
            'stocks_value': stocks_value,
            'stocks_ratio': (stocks_value / total_assets * 100) if total_assets > 0 else 0,
            'profit_loss': total_profit_loss,
            'profit_loss_rate': round(profit_loss_rate, 2),
            'holdings_count': len(holdings),
            'holdings': holdings,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        logger.info(f"포트폴리오 분석 완료: 총 자산 {total_assets:,}원, 수익률 {profit_loss_rate:.2f}%")
        return analysis


__all__ = ['Analyzer']