"""
core/emergency_controller.py
긴급 정지 컨트롤러

시스템 전체의 긴급 상황 관리 및 자동 보호 기능
"""
import os
import json
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class EmergencyLevel(Enum):
    """긴급 수준"""
    NORMAL = "normal"           # 정상
    WARNING = "warning"         # 경고 (모니터링 강화)
    ALERT = "alert"             # 주의 (신규 매수 중지)
    CRITICAL = "critical"       # 위험 (모든 거래 중지)
    SHUTDOWN = "shutdown"       # 시스템 종료


class EmergencyReason(Enum):
    """긴급 상황 사유"""
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    POSITION_LOSS_LIMIT = "position_loss_limit"
    VOLATILITY_SPIKE = "volatility_spike"
    API_FAILURE = "api_failure"
    SYSTEM_ERROR = "system_error"
    MANUAL_TRIGGER = "manual_trigger"
    MARKET_CIRCUIT_BREAKER = "market_circuit_breaker"
    NETWORK_ISSUE = "network_issue"


@dataclass
class EmergencyEvent:
    """긴급 이벤트"""
    event_id: str
    timestamp: str
    level: EmergencyLevel
    reason: EmergencyReason
    message: str
    triggered_by: str
    auto_recovery: bool = True
    recovery_time: str = ""
    resolved: bool = False


class EmergencyController:
    """
    긴급 정지 컨트롤러 (싱글톤)

    기능:
    - 자동 긴급 정지 (손실 한도, 변동성 급등)
    - 수동 긴급 정지
    - 단계별 대응 (경고 → 주의 → 위험 → 종료)
    - 자동 복구
    - 알림 연동
    """

    _instance = None
    _lock = threading.Lock()

    # 저장 경로
    STATE_FILE = Path("logs/emergency_state.json")

    # 기본 한도
    DEFAULT_LIMITS = {
        'daily_loss_limit': 1000000,        # 일일 손실 한도 100만원
        'daily_loss_pct_limit': 0.03,       # 일일 손실 비율 3%
        'position_loss_limit': 500000,      # 개별 포지션 손실 한도 50만원
        'position_loss_pct_limit': 0.10,    # 개별 포지션 손실 비율 10%
        'volatility_threshold': 0.08,       # 변동성 임계값 8%
        'api_failure_threshold': 5,         # API 실패 연속 횟수
        'max_daily_trades': 100,            # 일일 최대 거래
    }

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

        # 현재 상태
        self.current_level = EmergencyLevel.NORMAL
        self.active_events: List[EmergencyEvent] = []
        self.event_history: List[EmergencyEvent] = []

        # 설정
        self.limits = self.DEFAULT_LIMITS.copy()

        # 카운터
        self.api_failure_count = 0
        self.daily_loss = 0.0
        self.daily_trades = 0

        # 콜백
        self.on_emergency_callbacks: List[Callable] = []
        self.on_recovery_callbacks: List[Callable] = []

        # 수동 정지 플래그
        self.manual_stop = False
        self.manual_stop_reason = ""

        # 상태 로드
        self._load_state()

        logger.info(f"긴급 정지 컨트롤러 초기화 완료 (현재 수준: {self.current_level.value})")

    @classmethod
    def get_instance(cls) -> 'EmergencyController':
        return cls()

    def _load_state(self):
        """상태 로드"""
        try:
            if self.STATE_FILE.exists():
                with open(self.STATE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    level_str = data.get('current_level', 'normal')
                    self.current_level = EmergencyLevel(level_str)
                    self.manual_stop = data.get('manual_stop', False)
                    self.manual_stop_reason = data.get('manual_stop_reason', '')
        except Exception as e:
            logger.debug(f"긴급 상태 로드 실패: {e}")

    def _save_state(self):
        """상태 저장"""
        try:
            self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'current_level': self.current_level.value,
                'manual_stop': self.manual_stop,
                'manual_stop_reason': self.manual_stop_reason,
                'active_events': len(self.active_events),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"긴급 상태 저장 실패: {e}")

    def _create_event(
        self,
        level: EmergencyLevel,
        reason: EmergencyReason,
        message: str,
        triggered_by: str = "system"
    ) -> EmergencyEvent:
        """긴급 이벤트 생성"""
        event = EmergencyEvent(
            event_id=f"EMG_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.now().isoformat(),
            level=level,
            reason=reason,
            message=message,
            triggered_by=triggered_by
        )
        return event

    def _escalate_level(self, new_level: EmergencyLevel, event: EmergencyEvent):
        """긴급 수준 상승"""
        if new_level.value > self.current_level.value or \
           list(EmergencyLevel).index(new_level) > list(EmergencyLevel).index(self.current_level):

            old_level = self.current_level
            self.current_level = new_level

            self.active_events.append(event)
            self.event_history.append(event)

            self._save_state()

            # 콜백 실행
            for callback in self.on_emergency_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"긴급 콜백 실패: {e}")

            # 알림
            self._send_alert(event)

            logger.warning(
                f"🚨 긴급 수준 상승: {old_level.value} → {new_level.value}\n"
                f"   사유: {event.reason.value}\n"
                f"   메시지: {event.message}"
            )

    def _send_alert(self, event: EmergencyEvent):
        """알림 발송"""
        try:
            from core.telegram_notifier import get_telegram_notifier, AlertLevel

            notifier = get_telegram_notifier()

            level_map = {
                EmergencyLevel.WARNING: AlertLevel.WARNING,
                EmergencyLevel.ALERT: AlertLevel.WARNING,
                EmergencyLevel.CRITICAL: AlertLevel.CRITICAL,
                EmergencyLevel.SHUTDOWN: AlertLevel.CRITICAL,
            }

            alert_level = level_map.get(event.level, AlertLevel.INFO)

            notifier.send(
                f"긴급 상황 발생\n"
                f"수준: {event.level.value}\n"
                f"사유: {event.reason.value}\n"
                f"메시지: {event.message}",
                level=alert_level
            )
        except Exception as e:
            logger.debug(f"긴급 알림 실패: {e}")

    # === 자동 체크 함수들 ===

    def check_daily_loss(self, current_loss: float, portfolio_value: float) -> bool:
        """일일 손실 체크"""
        self.daily_loss = current_loss

        # 절대 금액 체크
        if abs(current_loss) > self.limits['daily_loss_limit']:
            event = self._create_event(
                EmergencyLevel.CRITICAL,
                EmergencyReason.DAILY_LOSS_LIMIT,
                f"일일 손실 한도 초과: {current_loss:,.0f}원 > {self.limits['daily_loss_limit']:,.0f}원"
            )
            self._escalate_level(EmergencyLevel.CRITICAL, event)
            return False

        # 비율 체크
        loss_pct = abs(current_loss) / portfolio_value if portfolio_value > 0 else 0
        if loss_pct > self.limits['daily_loss_pct_limit']:
            event = self._create_event(
                EmergencyLevel.CRITICAL,
                EmergencyReason.DAILY_LOSS_LIMIT,
                f"일일 손실 비율 초과: {loss_pct*100:.1f}% > {self.limits['daily_loss_pct_limit']*100:.1f}%"
            )
            self._escalate_level(EmergencyLevel.CRITICAL, event)
            return False

        # 경고 수준 (50% 도달)
        if loss_pct > self.limits['daily_loss_pct_limit'] * 0.5:
            if self.current_level == EmergencyLevel.NORMAL:
                event = self._create_event(
                    EmergencyLevel.WARNING,
                    EmergencyReason.DAILY_LOSS_LIMIT,
                    f"일일 손실 경고: {loss_pct*100:.1f}%"
                )
                self._escalate_level(EmergencyLevel.WARNING, event)

        return True

    def check_position_loss(
        self,
        stock_code: str,
        stock_name: str,
        loss: float,
        loss_pct: float
    ) -> bool:
        """개별 포지션 손실 체크"""
        if abs(loss) > self.limits['position_loss_limit']:
            event = self._create_event(
                EmergencyLevel.ALERT,
                EmergencyReason.POSITION_LOSS_LIMIT,
                f"포지션 손실 한도 초과: {stock_name} {loss:,.0f}원"
            )
            self._escalate_level(EmergencyLevel.ALERT, event)
            return False

        if abs(loss_pct) > self.limits['position_loss_pct_limit']:
            event = self._create_event(
                EmergencyLevel.ALERT,
                EmergencyReason.POSITION_LOSS_LIMIT,
                f"포지션 손실 비율 초과: {stock_name} {loss_pct*100:.1f}%"
            )
            self._escalate_level(EmergencyLevel.ALERT, event)
            return False

        return True

    def check_volatility(self, volatility: float) -> bool:
        """변동성 체크"""
        if volatility > self.limits['volatility_threshold']:
            if self.current_level.value < EmergencyLevel.ALERT.value:
                event = self._create_event(
                    EmergencyLevel.ALERT,
                    EmergencyReason.VOLATILITY_SPIKE,
                    f"시장 변동성 급등: {volatility*100:.1f}%"
                )
                self._escalate_level(EmergencyLevel.ALERT, event)
            return False
        return True

    def report_api_failure(self):
        """API 실패 보고"""
        self.api_failure_count += 1

        if self.api_failure_count >= self.limits['api_failure_threshold']:
            event = self._create_event(
                EmergencyLevel.ALERT,
                EmergencyReason.API_FAILURE,
                f"연속 API 실패: {self.api_failure_count}회"
            )
            self._escalate_level(EmergencyLevel.ALERT, event)

    def report_api_success(self):
        """API 성공 보고"""
        self.api_failure_count = 0

    # === 수동 제어 ===

    def trigger_emergency_stop(self, reason: str, triggered_by: str = "user"):
        """수동 긴급 정지"""
        self.manual_stop = True
        self.manual_stop_reason = reason

        event = self._create_event(
            EmergencyLevel.CRITICAL,
            EmergencyReason.MANUAL_TRIGGER,
            f"수동 긴급 정지: {reason}",
            triggered_by
        )
        self._escalate_level(EmergencyLevel.CRITICAL, event)

        logger.critical(f"🛑 수동 긴급 정지 활성화: {reason}")

    def release_emergency_stop(self, released_by: str = "user"):
        """긴급 정지 해제"""
        self.manual_stop = False
        self.manual_stop_reason = ""
        self.current_level = EmergencyLevel.NORMAL

        # 활성 이벤트 해결 처리
        for event in self.active_events:
            event.resolved = True
            event.recovery_time = datetime.now().isoformat()

        self.active_events.clear()

        self._save_state()

        # 복구 콜백 실행
        for callback in self.on_recovery_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"복구 콜백 실패: {e}")

        logger.info(f"✅ 긴급 정지 해제됨 (by {released_by})")

    # === 상태 확인 ===

    def is_trading_allowed(self) -> bool:
        """거래 허용 여부"""
        if self.manual_stop:
            return False

        return self.current_level in [EmergencyLevel.NORMAL, EmergencyLevel.WARNING]

    def is_new_buy_allowed(self) -> bool:
        """신규 매수 허용 여부

        - NORMAL: 정상 거래
        - WARNING: 경고 (모니터링 강화, 매수 허용)
        - ALERT 이상: 신규 매수 중지
        """
        if self.manual_stop:
            return False

        # Fix: WARNING 수준에서도 매수 허용 (경고는 모니터링만 강화)
        # 이전: NORMAL만 허용 → WARNING에서 불필요하게 매수 차단됨
        return self.current_level in [EmergencyLevel.NORMAL, EmergencyLevel.WARNING]

    def can_sell(self) -> bool:
        """매도 허용 여부 (위험 수준에서도 매도는 가능)"""
        return self.current_level != EmergencyLevel.SHUTDOWN

    def get_status(self) -> Dict[str, Any]:
        """현재 상태"""
        return {
            'level': self.current_level.value,
            'manual_stop': self.manual_stop,
            'manual_stop_reason': self.manual_stop_reason,
            'trading_allowed': self.is_trading_allowed(),
            'new_buy_allowed': self.is_new_buy_allowed(),
            'active_events': len(self.active_events),
            'api_failure_count': self.api_failure_count,
            'daily_loss': self.daily_loss,
            'limits': self.limits
        }

    def register_emergency_callback(self, callback: Callable):
        """긴급 콜백 등록"""
        self.on_emergency_callbacks.append(callback)

    def register_recovery_callback(self, callback: Callable):
        """복구 콜백 등록"""
        self.on_recovery_callbacks.append(callback)

    def reset_daily_counters(self):
        """일일 카운터 초기화"""
        self.daily_loss = 0.0
        self.daily_trades = 0
        self.api_failure_count = 0

        # 자동 복구 (수동 정지가 아닌 경우)
        if not self.manual_stop and self.current_level != EmergencyLevel.NORMAL:
            self.release_emergency_stop("daily_reset")


# 전역 접근 함수
def get_emergency_controller() -> EmergencyController:
    return EmergencyController.get_instance()


def is_trading_allowed() -> bool:
    """거래 허용 여부 편의 함수"""
    return get_emergency_controller().is_trading_allowed()


def trigger_emergency(reason: str):
    """긴급 정지 편의 함수"""
    get_emergency_controller().trigger_emergency_stop(reason)
