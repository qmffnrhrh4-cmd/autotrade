"""
Input validation utilities for dashboard API
"""
import re
from typing import Any, Dict, List, Optional
from flask import request


def validate_stock_code(code: str) -> bool:
    """
    Validate stock code format

    Args:
        code: Stock code to validate

    Returns:
        True if valid, False otherwise

    Valid formats:
    - KRX: 6 digits (e.g., "005930")
    - US: alphanumeric (e.g., "AAPL", "MSFT")
    """
    if not code:
        return False

    # KRX stocks: 6 digits
    if re.match(r'^\d{6}$', code):
        return True

    # US stocks: 1-5 uppercase letters
    if re.match(r'^[A-Z]{1,5}$', code):
        return True

    return False


def validate_request_data(required_fields: List[str], optional_fields: Optional[List[str]] = None) -> tuple:
    """
    Validate request JSON data

    Args:
        required_fields: List of required field names
        optional_fields: List of optional field names

    Returns:
        Tuple of (is_valid: bool, data: dict, error_message: str or None)

    Example:
        is_valid, data, error = validate_request_data(['stock_code', 'quantity'])
        if not is_valid:
            return error_response(error)
    """
    if not request.is_json:
        return False, {}, "Request must be JSON"

    data = request.get_json()

    # Check required fields
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return False, {}, f"Missing required fields: {', '.join(missing_fields)}"

    # Extract only required and optional fields
    allowed_fields = required_fields + (optional_fields or [])
    validated_data = {key: value for key, value in data.items() if key in allowed_fields}

    return True, validated_data, None


def validate_pagination_params(default_page: int = 1, default_limit: int = 20, max_limit: int = 100) -> Dict[str, int]:
    """
    Validate and extract pagination parameters from request

    Args:
        default_page: Default page number
        default_limit: Default items per page
        max_limit: Maximum items per page

    Returns:
        Dict with 'page', 'limit', 'offset' keys
    """
    try:
        page = int(request.args.get('page', default_page))
        limit = int(request.args.get('limit', default_limit))

        # Validate ranges
        page = max(1, page)
        limit = max(1, min(limit, max_limit))

        offset = (page - 1) * limit

        return {
            'page': page,
            'limit': limit,
            'offset': offset
        }
    except (ValueError, TypeError):
        return {
            'page': default_page,
            'limit': default_limit,
            'offset': 0
        }


def validate_timeframe(timeframe: str) -> bool:
    """
    Validate chart timeframe parameter

    Args:
        timeframe: Timeframe string (e.g., 'D', 'W', 'M', '1', '5', '15', '30', '60')

    Returns:
        True if valid, False otherwise
    """
    valid_timeframes = ['D', 'W', 'M', '1', '3', '5', '10', '15', '30', '60']
    return timeframe in valid_timeframes


def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> tuple:
    """
    Validate date range parameters

    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)

    Returns:
        Tuple of (is_valid: bool, error_message: str or None)
    """
    from datetime import datetime

    if not start_date or not end_date:
        return True, None

    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        if start > end:
            return False, "Start date must be before end date"

        return True, None
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD"


def validate_quantity(quantity: Any, min_value: int = 1, max_value: int = 1000000) -> tuple:
    """
    Validate order quantity

    Args:
        quantity: Quantity value to validate
        min_value: Minimum allowed quantity
        max_value: Maximum allowed quantity

    Returns:
        Tuple of (is_valid: bool, cleaned_value: int or None, error_message: str or None)
    """
    try:
        qty = int(quantity)
        if qty < min_value:
            return False, None, f"Quantity must be at least {min_value}"
        if qty > max_value:
            return False, None, f"Quantity cannot exceed {max_value}"
        return True, qty, None
    except (ValueError, TypeError):
        return False, None, "Invalid quantity format"


def validate_price(price: Any, min_value: float = 0, max_value: float = 100000000) -> tuple:
    """
    Validate price value

    Args:
        price: Price value to validate
        min_value: Minimum allowed price
        max_value: Maximum allowed price

    Returns:
        Tuple of (is_valid: bool, cleaned_value: float or None, error_message: str or None)
    """
    try:
        p = float(price)
        if p < min_value:
            return False, None, f"Price must be positive"
        if p > max_value:
            return False, None, f"Price exceeds maximum ({max_value:,})"
        return True, p, None
    except (ValueError, TypeError):
        return False, None, "Invalid price format"


def validate_percentage(value: Any, min_value: float = -100, max_value: float = 100) -> tuple:
    """
    Validate percentage value

    Args:
        value: Percentage value to validate
        min_value: Minimum percentage
        max_value: Maximum percentage

    Returns:
        Tuple of (is_valid: bool, cleaned_value: float or None, error_message: str or None)
    """
    try:
        pct = float(value)
        if pct < min_value or pct > max_value:
            return False, None, f"Percentage must be between {min_value}% and {max_value}%"
        return True, pct, None
    except (ValueError, TypeError):
        return False, None, "Invalid percentage format"


def validate_strategy_params(params: Dict[str, Any]) -> tuple:
    """
    Validate strategy parameters

    Args:
        params: Strategy parameters dictionary

    Returns:
        Tuple of (is_valid: bool, cleaned_params: dict, error_messages: list)
    """
    errors = []
    cleaned = {}

    if 'stop_loss_pct' in params:
        valid, val, err = validate_percentage(params['stop_loss_pct'], 0, 30)
        if valid:
            cleaned['stop_loss_pct'] = val
        else:
            errors.append(f"stop_loss_pct: {err}")

    if 'take_profit_pct' in params:
        valid, val, err = validate_percentage(params['take_profit_pct'], 0, 100)
        if valid:
            cleaned['take_profit_pct'] = val
        else:
            errors.append(f"take_profit_pct: {err}")

    if 'max_positions' in params:
        valid, val, err = validate_quantity(params['max_positions'], 1, 50)
        if valid:
            cleaned['max_positions'] = val
        else:
            errors.append(f"max_positions: {err}")

    if 'position_size_pct' in params:
        valid, val, err = validate_percentage(params['position_size_pct'], 1, 50)
        if valid:
            cleaned['position_size_pct'] = val
        else:
            errors.append(f"position_size_pct: {err}")

    return len(errors) == 0, cleaned, errors


def sanitize_string(value: str, max_length: int = 500) -> str:
    """
    Sanitize string input

    Args:
        value: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""

    sanitized = value.strip()

    sanitized = sanitized[:max_length]

    sanitized = re.sub(r'<[^>]*>', '', sanitized)

    return sanitized


def validate_order_type(order_type: str) -> bool:
    """
    Validate order type

    Args:
        order_type: Order type string

    Returns:
        True if valid
    """
    valid_types = ['market', 'limit', 'stop', 'stop_limit']
    return order_type.lower() in valid_types


def validate_order_side(side: str) -> bool:
    """
    Validate order side

    Args:
        side: Order side string (buy/sell)

    Returns:
        True if valid
    """
    return side.lower() in ['buy', 'sell']
