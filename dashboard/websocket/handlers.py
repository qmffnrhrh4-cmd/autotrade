"""
WebSocket connection handlers for real-time dashboard updates
"""
from flask import request
from flask_socketio import emit
import logging

logger = logging.getLogger(__name__)

# 모듈 레벨 변수
_socketio = None


def register_websocket_handlers(socketio):
    """Register all WebSocket event handlers"""
    global _socketio
    _socketio = socketio

    @socketio.on('connect')
    def handle_connect():
        """Client connected"""
        emit('connected', {'message': 'Connected to AutoTrade Pro'})
        logger.info(f"✅ 클라이언트 연결: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        """Client disconnected"""
        logger.info(f"❌ 클라이언트 연결 해제: {request.sid}")

    @socketio.on('subscribe_evolution')
    def handle_subscribe_evolution(data):
        """진화 알고리즘 실시간 구독"""
        logger.info(f"진화 알고리즘 구독: {request.sid}")
        emit('evolution_subscribed', {'message': '구독 완료'})

    @socketio.on('request_market_data')
    def handle_request_market_data(data):
        """실시간 시장 데이터 요청"""
        stock_code = data.get('stock_code')
        logger.info(f"시장 데이터 요청: {stock_code} from {request.sid}")


def emit_evolution_update(data):
    """진화 알고리즘 업데이트 전송"""
    if _socketio:
        _socketio.emit('evolution_update', data)


def emit_market_data(data):
    """시장 데이터 업데이트 전송"""
    if _socketio:
        _socketio.emit('market_data', data)


def emit_trade_executed(data):
    """거래 체결 알림 전송"""
    if _socketio:
        _socketio.emit('trade_executed', data)
