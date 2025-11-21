"""
utils/validators.py
데이터 검증 유틸리티
"""
import re
import logging
from typing import Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def validate_stock_code(stock_code: str) -> Tuple[bool, str]:
    """
    종목코드 검증
    
    Args:
        stock_code: 종목코드
    
    Returns:
        (검증 통과 여부, 메시지)
    """
    if not stock_code:
        return False, "종목코드가 비어있습니다"
    
    # 6자리 숫자 확인
    if not re.match(r'^\d{6}$', stock_code):
        return False, f"종목코드는 6자리 숫자여야 합니다: {stock_code}"
    
    return True, "유효한 종목코드"


def validate_price(price: Any, min_price: int = 0, max_price: int = 10000000) -> Tuple[bool, str]:
    """
    가격 검증
    
    Args:
        price: 가격
        min_price: 최소 가격
        max_price: 최대 가격
    
    Returns:
        (검증 통과 여부, 메시지)
    """
    try:
        price = int(price)
    except (ValueError, TypeError):
        return False, f"가격은 숫자여야 합니다: {price}"
    
    if price < min_price:
        return False, f"가격이 최소값({min_price:,}원)보다 작습니다: {price:,}원"
    
    if price > max_price:
        return False, f"가격이 최대값({max_price:,}원)을 초과합니다: {price:,}원"
    
    return True, "유효한 가격"


def validate_quantity(quantity: Any, min_quantity: int = 1, max_quantity: int = 1000000) -> Tuple[bool, str]:
    """
    수량 검증
    
    Args:
        quantity: 수량
        min_quantity: 최소 수량
        max_quantity: 최대 수량
    
    Returns:
        (검증 통과 여부, 메시지)
    """
    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        return False, f"수량은 정수여야 합니다: {quantity}"
    
    if quantity < min_quantity:
        return False, f"수량이 최소값({min_quantity}주)보다 작습니다: {quantity}주"
    
    if quantity > max_quantity:
        return False, f"수량이 최대값({max_quantity:,}주)을 초과합니다: {quantity:,}주"
    
    return True, "유효한 수량"


def validate_account_number(account_number: str) -> Tuple[bool, str]:
    """
    계좌번호 검증
    
    Args:
        account_number: 계좌번호 (형식: XXXXXXXX-XX)
    
    Returns:
        (검증 통과 여부, 메시지)
    """
    if not account_number:
        return False, "계좌번호가 비어있습니다"
    
    # 형식 확인: XXXXXXXX-XX
    if not re.match(r'^\d{8}-\d{2}$', account_number):
        return False, f"계좌번호 형식이 잘못되었습니다 (XXXXXXXX-XX): {account_number}"
    
    return True, "유효한 계좌번호"


def validate_date(date_str: str, date_format: str = '%Y%m%d') -> Tuple[bool, str]:
    """
    날짜 검증
    
    Args:
        date_str: 날짜 문자열
        date_format: 날짜 형식 (기본: YYYYMMDD)
    
    Returns:
        (검증 통과 여부, 메시지)
    """
    if not date_str:
        return False, "날짜가 비어있습니다"
    
    try:
        datetime.strptime(date_str, date_format)
        return True, "유효한 날짜"
    except ValueError:
        return False, f"날짜 형식이 잘못되었습니다 (형식: {date_format}): {date_str}"


def validate_rate(rate: Any, min_rate: float = -100.0, max_rate: float = 100.0) -> Tuple[bool, str]:
    """
    비율 검증
    
    Args:
        rate: 비율 (%)
        min_rate: 최소 비율
        max_rate: 최대 비율
    
    Returns:
        (검증 통과 여부, 메시지)
    """
    try:
        rate = float(rate)
    except (ValueError, TypeError):
        return False, f"비율은 숫자여야 합니다: {rate}"
    
    if rate < min_rate:
        return False, f"비율이 최소값({min_rate}%)보다 작습니다: {rate}%"
    
    if rate > max_rate:
        return False, f"비율이 최대값({max_rate}%)을 초과합니다: {rate}%"
    
    return True, "유효한 비율"


def validate_order_type(order_type: str) -> Tuple[bool, str]:
    """
    주문 유형 검증
    
    Args:
        order_type: 주문 유형 ('00': 지정가, '03': 시장가)
    
    Returns:
        (검증 통과 여부, 메시지)
    """
    valid_types = ['00', '03']
    
    if order_type not in valid_types:
        return False, f"유효하지 않은 주문 유형: {order_type} (00: 지정가, 03: 시장가)"
    
    return True, "유효한 주문 유형"


def validate_buy_sell_code(buy_sell_code: str) -> Tuple[bool, str]:
    """
    매수/매도 구분 검증
    
    Args:
        buy_sell_code: 매수/매도 구분 ('1': 매도, '2': 매수)
    
    Returns:
        (검증 통과 여부, 메시지)
    """
    valid_codes = ['1', '2']
    
    if buy_sell_code not in valid_codes:
        return False, f"유효하지 않은 매수/매도 구분: {buy_sell_code} (1: 매도, 2: 매수)"
    
    return True, "유효한 매수/매도 구분"


def validate_api_response(response: dict) -> Tuple[bool, str]:
    """
    API 응답 검증
    
    Args:
        response: API 응답
    
    Returns:
        (검증 통과 여부, 메시지)
    """
    if not response:
        return False, "응답이 비어있습니다"
    
    if not isinstance(response, dict):
        return False, f"응답이 딕셔너리가 아닙니다: {type(response)}"
    
    # return_code 확인
    return_code = response.get('return_code')
    
    if return_code is None:
        return False, "return_code가 없습니다"
    
    if return_code != 0:
        return_msg = response.get('return_msg', '알 수 없는 오류')
        return False, f"API 오류 (코드: {return_code}): {return_msg}"
    
    return True, "유효한 API 응답"


def validate_position_size(
    position_value: float,
    total_assets: float,
    max_position_ratio: float = 0.30
) -> Tuple[bool, str]:
    """
    포지션 크기 검증
    
    Args:
        position_value: 포지션 가치
        total_assets: 총 자산
        max_position_ratio: 최대 포지션 비율 (기본 30%)
    
    Returns:
        (검증 통과 여부, 메시지)
    """
    if total_assets <= 0:
        return False, "총 자산이 0 이하입니다"
    
    if position_value < 0:
        return False, "포지션 가치가 음수입니다"
    
    position_ratio = position_value / total_assets
    
    if position_ratio > max_position_ratio:
        return False, f"포지션 비중이 너무 큽니다: {position_ratio*100:.1f}% (최대: {max_position_ratio*100:.1f}%)"
    
    return True, "유효한 포지션 크기"


def validate_trading_params(params: dict) -> Tuple[bool, list]:
    """
    매매 파라미터 검증
    
    Args:
        params: 매매 파라미터
    
    Returns:
        (검증 통과 여부, 오류 메시지 리스트)
    """
    errors = []
    
    # 필수 파라미터 확인
    required_params = [
        'MAX_OPEN_POSITIONS',
        'RISK_PER_TRADE_RATIO',
        'TAKE_PROFIT_RATIO',
        'STOP_LOSS_RATIO',
    ]
    
    for param in required_params:
        if param not in params:
            errors.append(f"필수 파라미터 누락: {param}")
    
    # 범위 검증
    if 'MAX_OPEN_POSITIONS' in params:
        if not (1 <= params['MAX_OPEN_POSITIONS'] <= 50):
            errors.append("MAX_OPEN_POSITIONS는 1~50 사이여야 합니다")
    
    if 'RISK_PER_TRADE_RATIO' in params:
        if not (0 < params['RISK_PER_TRADE_RATIO'] <= 1.0):
            errors.append("RISK_PER_TRADE_RATIO는 0~1 사이여야 합니다")
    
    if 'TAKE_PROFIT_RATIO' in params:
        if not (0 < params['TAKE_PROFIT_RATIO'] <= 1.0):
            errors.append("TAKE_PROFIT_RATIO는 0~1 사이여야 합니다")
    
    if 'STOP_LOSS_RATIO' in params:
        if not (-1.0 <= params['STOP_LOSS_RATIO'] < 0):
            errors.append("STOP_LOSS_RATIO는 -1~0 사이여야 합니다")
    
    return len(errors) == 0, errors


def sanitize_stock_code(stock_code: str) -> str:
    """
    종목코드 정제
    
    Args:
        stock_code: 원본 종목코드
    
    Returns:
        정제된 종목코드 (6자리 숫자)
    """
    # 숫자만 추출
    digits = ''.join(filter(str.isdigit, stock_code))
    
    # 6자리 맞추기
    if len(digits) < 6:
        digits = digits.zfill(6)
    elif len(digits) > 6:
        digits = digits[:6]
    
    return digits


def sanitize_account_number(account_number: str) -> str:
    """
    계좌번호 정제

    Args:
        account_number: 원본 계좌번호

    Returns:
        정제된 계좌번호 (XXXXXXXX-XX 형식)
    """
    # 숫자만 추출
    digits = ''.join(filter(str.isdigit, account_number))

    # 형식 맞추기
    if len(digits) >= 10:
        return f"{digits[:8]}-{digits[8:10]}"

    return account_number


def adjust_price_to_tick_size(price: int) -> int:
    """
    호가 단위에 맞게 가격 조정 (내림)

    한국 주식 시장 호가 단위:
    - 1,000원 미만: 1원 단위
    - 1,000원 이상 5,000원 미만: 5원 단위
    - 5,000원 이상 10,000원 미만: 10원 단위
    - 10,000원 이상 50,000원 미만: 50원 단위
    - 50,000원 이상 100,000원 미만: 100원 단위
    - 100,000원 이상 500,000원 미만: 500원 단위
    - 500,000원 이상: 1,000원 단위

    Args:
        price: 원본 가격

    Returns:
        조정된 가격 (호가 단위에 맞춤)

    Example:
        >>> adjust_price_to_tick_size(50541)
        50500
        >>> adjust_price_to_tick_size(12345)
        12300
        >>> adjust_price_to_tick_size(999)
        999
    """
    try:
        price = int(price)
    except (ValueError, TypeError):
        logger.error(f"Invalid price format: {price}")
        return 0

    if price < 0:
        return 0

    # 호가 단위 결정 및 조정
    if price < 1000:
        # 1원 단위
        tick_size = 1
    elif price < 5000:
        # 5원 단위
        tick_size = 5
    elif price < 10000:
        # 10원 단위
        tick_size = 10
    elif price < 50000:
        # 50원 단위
        tick_size = 50
    elif price < 100000:
        # 100원 단위
        tick_size = 100
    elif price < 500000:
        # 500원 단위
        tick_size = 500
    else:
        # 1,000원 단위
        tick_size = 1000

    # 내림으로 조정
    adjusted_price = (price // tick_size) * tick_size

    if adjusted_price != price:
        logger.info(f"💰 가격 조정: {price:,}원 → {adjusted_price:,}원 (호가단위: {tick_size}원)")

    return adjusted_price


def validate_tick_size(price: int) -> Tuple[bool, str]:
    """
    가격이 호가 단위에 맞는지 검증

    Args:
        price: 가격

    Returns:
        (검증 통과 여부, 메시지)
    """
    adjusted_price = adjust_price_to_tick_size(price)

    if price != adjusted_price:
        return False, f"호가 단위 오류: {price:,}원은 허용되지 않습니다. {adjusted_price:,}원을 사용하세요."

    return True, "유효한 호가 단위"


__all__ = [
    'validate_stock_code',
    'validate_price',
    'validate_quantity',
    'validate_account_number',
    'validate_date',
    'validate_rate',
    'validate_order_type',
    'validate_buy_sell_code',
    'validate_api_response',
    'validate_position_size',
    'validate_trading_params',
    'sanitize_stock_code',
    'sanitize_account_number',
    'adjust_price_to_tick_size',
    'validate_tick_size',
]