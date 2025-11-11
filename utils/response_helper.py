from typing import Any, Dict, Optional
from flask import jsonify, Response


def success_response(
    data: Any = None,
    message: str = None,
    status: int = 200
) -> tuple[Response, int]:
    response = {'success': True}

    if data is not None:
        response['data'] = data

    if message:
        response['message'] = message

    return jsonify(response), status


def error_response(
    message: str,
    error: Exception = None,
    status: int = 500,
    error_code: str = None
) -> tuple[Response, int]:
    response = {
        'success': False,
        'message': message
    }

    if error_code:
        response['error_code'] = error_code

    if error and hasattr(error, '__str__'):
        response['error_detail'] = str(error)

    return jsonify(response), status


def validation_error_response(
    field: str,
    message: str = None
) -> tuple[Response, int]:
    if message is None:
        message = f'Invalid value for field: {field}'

    return error_response(
        message=message,
        status=400,
        error_code='VALIDATION_ERROR'
    )


def not_found_response(
    resource: str = 'Resource'
) -> tuple[Response, int]:
    return error_response(
        message=f'{resource} not found',
        status=404,
        error_code='NOT_FOUND'
    )


def unauthorized_response(
    message: str = 'Unauthorized access'
) -> tuple[Response, int]:
    return error_response(
        message=message,
        status=401,
        error_code='UNAUTHORIZED'
    )
