"""
core/event_bus.py
실시간 이벤트 버스 시스템

모든 트레이딩 이벤트를 관리하고 대시보드/알림으로 브로드캐스트
"""
import json
import asyncio
import threading
import logging
from typing import Dict, Any, List, Callable, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict
from queue import Queue, Empty
import time

logger = logging.getLogger(__name__)


class EventType(Enum):
    """이벤트 유형"""
    # 가격 이벤트
    PRICE_UPDATE = "price_update"
    PRICE_ALERT = "price_alert"

    # 거래 이벤트
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    ORDER_CANCELLED = "order_cancelled"

    # 포지션 이벤트
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_UPDATED = "position_updated"

    # 전략 이벤트
    SIGNAL_GENERATED = "signal_generated"
    STRATEGY_CHANGED = "strategy_changed"
    EVOLUTION_COMPLETED = "evolution_completed"

    # 리스크 이벤트
    RISK_WARNING = "risk_warning"
    RISK_CRITICAL = "risk_critical"
    EMERGENCY_STOP = "emergency_stop"

    # 시스템 이벤트
    SYSTEM_STATUS = "system_status"
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"
    ERROR = "error"

    # 성능 이벤트
    DAILY_REPORT = "daily_report"
    PROFIT_LOSS_UPDATE = "profit_loss_update"


@dataclass
class Event:
    """이벤트 데이터"""
    event_type: EventType
    timestamp: str
    data: Dict[str, Any]
    source: str = "system"
    priority: int = 5  # 1=highest, 10=lowest

    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type.value,
            'timestamp': self.timestamp,
            'data': self.data,
            'source': self.source,
            'priority': self.priority
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class EventBus:
    """
    이벤트 버스 (싱글톤)

    기능:
    - 이벤트 발행/구독
    - WebSocket 클라이언트 관리
    - 이벤트 큐 및 비동기 처리
    - 이벤트 히스토리
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True

        # 구독자 관리
        self.subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.all_event_subscribers: List[Callable] = []

        # WebSocket 클라이언트
        self.websocket_clients: Set = set()
        self.websocket_lock = threading.Lock()

        # 이벤트 큐
        self.event_queue: Queue = Queue()
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None

        # 이벤트 히스토리
        self.event_history: List[Event] = []
        self.max_history = 1000

        # 통계
        self.stats = {
            'total_events': 0,
            'events_by_type': defaultdict(int),
            'errors': 0
        }

        # 워커 시작
        self.start()

        logger.info("이벤트 버스 초기화 완료")

    @classmethod
    def get_instance(cls) -> 'EventBus':
        return cls()

    def start(self):
        """이벤트 처리 워커 시작"""
        if self.is_running:
            return

        self.is_running = True
        self.worker_thread = threading.Thread(target=self._event_worker, daemon=True)
        self.worker_thread.start()
        logger.info("이벤트 버스 워커 시작")

    def stop(self):
        """이벤트 처리 워커 중지"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2)
        logger.info("이벤트 버스 워커 중지")

    def _event_worker(self):
        """이벤트 처리 워커"""
        while self.is_running:
            try:
                event = self.event_queue.get(timeout=0.5)
                self._process_event(event)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"이벤트 처리 오류: {e}")
                self.stats['errors'] += 1

    def _process_event(self, event: Event):
        """이벤트 처리"""
        try:
            # 히스토리 저장
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history = self.event_history[-self.max_history//2:]

            # 통계 업데이트
            self.stats['total_events'] += 1
            self.stats['events_by_type'][event.event_type.value] += 1

            # 타입별 구독자에게 전달
            for callback in self.subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"구독자 콜백 오류 ({event.event_type}): {e}")

            # 전체 이벤트 구독자에게 전달
            for callback in self.all_event_subscribers:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"전체 이벤트 구독자 콜백 오류: {e}")

            # WebSocket 클라이언트에게 브로드캐스트
            self._broadcast_to_websockets(event)

        except Exception as e:
            logger.error(f"이벤트 처리 중 오류: {e}")

    def _broadcast_to_websockets(self, event: Event):
        """WebSocket 클라이언트에게 브로드캐스트"""
        if not self.websocket_clients:
            return

        message = event.to_json()

        with self.websocket_lock:
            disconnected = set()

            for client in self.websocket_clients:
                try:
                    # 비동기 WebSocket 전송
                    if hasattr(client, 'send_text'):
                        asyncio.create_task(client.send_text(message))
                    elif hasattr(client, 'send'):
                        client.send(message)
                except Exception as e:
                    logger.debug(f"WebSocket 전송 실패: {e}")
                    disconnected.add(client)

            # 연결 끊긴 클라이언트 제거
            self.websocket_clients -= disconnected

    def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        source: str = "system",
        priority: int = 5
    ):
        """이벤트 발행"""
        event = Event(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            data=data,
            source=source,
            priority=priority
        )

        self.event_queue.put(event)

    def subscribe(self, event_type: EventType, callback: Callable):
        """특정 이벤트 타입 구독"""
        self.subscribers[event_type].append(callback)
        logger.debug(f"구독 추가: {event_type.value}")

    def subscribe_all(self, callback: Callable):
        """모든 이벤트 구독"""
        self.all_event_subscribers.append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """구독 해제"""
        if callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)

    def register_websocket(self, client):
        """WebSocket 클라이언트 등록"""
        with self.websocket_lock:
            self.websocket_clients.add(client)
            logger.info(f"WebSocket 클라이언트 등록 (총 {len(self.websocket_clients)}개)")

    def unregister_websocket(self, client):
        """WebSocket 클라이언트 해제"""
        with self.websocket_lock:
            self.websocket_clients.discard(client)
            logger.info(f"WebSocket 클라이언트 해제 (총 {len(self.websocket_clients)}개)")

    def get_recent_events(self, count: int = 50, event_type: Optional[EventType] = None) -> List[Dict]:
        """최근 이벤트 조회"""
        events = self.event_history[-count:]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return [e.to_dict() for e in events]

    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        return {
            **self.stats,
            'websocket_clients': len(self.websocket_clients),
            'history_size': len(self.event_history),
            'queue_size': self.event_queue.qsize()
        }

    # === 편의 함수들 ===

    def emit_price_update(self, stock_code: str, price: float, change_rate: float):
        """가격 업데이트 이벤트"""
        self.emit(EventType.PRICE_UPDATE, {
            'stock_code': stock_code,
            'price': price,
            'change_rate': change_rate
        }, priority=8)

    def emit_order_submitted(self, stock_code: str, stock_name: str, order_type: str, quantity: int, price: float):
        """주문 제출 이벤트"""
        self.emit(EventType.ORDER_SUBMITTED, {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'order_type': order_type,
            'quantity': quantity,
            'price': price
        }, priority=3)

    def emit_order_filled(self, stock_code: str, stock_name: str, order_type: str, quantity: int, price: float, order_no: str):
        """주문 체결 이벤트"""
        self.emit(EventType.ORDER_FILLED, {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'order_type': order_type,
            'quantity': quantity,
            'price': price,
            'order_no': order_no
        }, priority=2)

    def emit_risk_warning(self, message: str, risk_level: str, details: Dict = None):
        """리스크 경고 이벤트"""
        self.emit(EventType.RISK_WARNING, {
            'message': message,
            'risk_level': risk_level,
            'details': details or {}
        }, priority=1)

    def emit_profit_loss_update(self, total_pnl: float, daily_pnl: float, positions: List[Dict]):
        """손익 업데이트 이벤트"""
        self.emit(EventType.PROFIT_LOSS_UPDATE, {
            'total_pnl': total_pnl,
            'daily_pnl': daily_pnl,
            'positions_count': len(positions)
        }, priority=5)

    def emit_signal_generated(self, stock_code: str, signal: str, confidence: float, reason: str):
        """시그널 생성 이벤트"""
        self.emit(EventType.SIGNAL_GENERATED, {
            'stock_code': stock_code,
            'signal': signal,
            'confidence': confidence,
            'reason': reason
        }, priority=4)

    def emit_emergency_stop(self, reason: str):
        """긴급 정지 이벤트"""
        self.emit(EventType.EMERGENCY_STOP, {
            'reason': reason,
            'triggered_at': datetime.now().isoformat()
        }, priority=1)


# 전역 접근 함수
def get_event_bus() -> EventBus:
    return EventBus.get_instance()


def emit_event(event_type: EventType, data: Dict[str, Any], **kwargs):
    """이벤트 발행 편의 함수"""
    get_event_bus().emit(event_type, data, **kwargs)
