"""
Circuit Breaker Pattern - 외부 서비스 장애 격리
CLOSED → OPEN → HALF_OPEN 상태 머신
"""
import time
import threading
from typing import Callable, TypeVar, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from collections import deque

from utils.logger_new import get_logger

logger = get_logger()

T = TypeVar('T')


class CircuitState(Enum):
    """회로 상태"""
    CLOSED = "closed"       # 정상 - 요청 허용
    OPEN = "open"           # 차단 - 요청 거부
    HALF_OPEN = "half_open" # 테스트 - 일부 요청만 허용


@dataclass
class CircuitStats:
    """회로 통계"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    state_changes: int = 0


class CircuitBreaker:
    """서킷 브레이커

    특징:
    - 연속 실패 시 회로 열기 (요청 차단)
    - 복구 시간 후 반개방 상태로 테스트
    - 슬라이딩 윈도우 기반 실패율 계산
    - Fallback 함수 지원
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
        window_size: int = 10,
        failure_rate_threshold: float = 0.5
    ):
        """
        Args:
            name: 서킷 이름
            failure_threshold: 연속 실패 횟수 (회로 열림)
            success_threshold: 연속 성공 횟수 (회로 닫힘)
            recovery_timeout: 복구 대기 시간 (초)
            half_open_max_calls: 반개방 상태 최대 호출 수
            window_size: 슬라이딩 윈도우 크기
            failure_rate_threshold: 실패율 임계값 (0.0 ~ 1.0)
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.window_size = window_size
        self.failure_rate_threshold = failure_rate_threshold

        self._state = CircuitState.CLOSED
        self._state_lock = threading.RLock()
        self._last_state_change = datetime.now()
        self._half_open_calls = 0

        # 슬라이딩 윈도우 (True=성공, False=실패)
        self._call_history: deque = deque(maxlen=window_size)

        # 통계
        self._stats = CircuitStats()

        # Fallback 함수
        self._fallback: Optional[Callable] = None

        logger.info(f"CircuitBreaker '{name}' 초기화 (threshold={failure_threshold}, timeout={recovery_timeout}s)")

    @property
    def state(self) -> CircuitState:
        """현재 상태"""
        with self._state_lock:
            # OPEN 상태에서 복구 시간 경과 시 HALF_OPEN으로 전환
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def set_fallback(self, fallback: Callable):
        """Fallback 함수 설정"""
        self._fallback = fallback

    def _should_attempt_reset(self) -> bool:
        """복구 시도 여부 확인"""
        elapsed = (datetime.now() - self._last_state_change).total_seconds()
        return elapsed >= self.recovery_timeout

    def _transition_to(self, new_state: CircuitState):
        """상태 전환"""
        old_state = self._state
        self._state = new_state
        self._last_state_change = datetime.now()
        self._stats.state_changes += 1

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0

        logger.warning(f"CircuitBreaker '{self.name}': {old_state.value} → {new_state.value}")

    def _record_success(self):
        """성공 기록"""
        with self._state_lock:
            self._stats.successful_calls += 1
            self._stats.last_success_time = datetime.now()
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._call_history.append(True)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._stats.consecutive_successes >= self.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def _record_failure(self, error: Exception = None):
        """실패 기록"""
        with self._state_lock:
            self._stats.failed_calls += 1
            self._stats.last_failure_time = datetime.now()
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._call_history.append(False)

            # 실패율 체크
            if len(self._call_history) >= self.window_size:
                failure_rate = self._call_history.count(False) / len(self._call_history)
                if failure_rate >= self.failure_rate_threshold:
                    if self._state != CircuitState.OPEN:
                        self._transition_to(CircuitState.OPEN)
                        logger.error(f"CircuitBreaker '{self.name}' OPEN: 실패율 {failure_rate*100:.1f}%")
                    return

            # 연속 실패 체크
            if self._stats.consecutive_failures >= self.failure_threshold:
                if self._state != CircuitState.OPEN:
                    self._transition_to(CircuitState.OPEN)
                    logger.error(f"CircuitBreaker '{self.name}' OPEN: 연속 {self.failure_threshold}회 실패")

            elif self._state == CircuitState.HALF_OPEN:
                # 반개방 상태에서 실패 → 다시 열기
                self._transition_to(CircuitState.OPEN)

    def can_execute(self) -> bool:
        """실행 가능 여부 확인"""
        current_state = self.state

        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.OPEN:
            return False
        else:  # HALF_OPEN
            with self._state_lock:
                return self._half_open_calls < self.half_open_max_calls

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """서킷 브레이커를 통해 함수 실행

        Args:
            func: 실행할 함수
            *args, **kwargs: 함수 인자

        Returns:
            함수 실행 결과

        Raises:
            CircuitOpenError: 회로가 열려 있을 때
            원본 예외: 함수 실행 중 발생한 예외
        """
        self._stats.total_calls += 1

        if not self.can_execute():
            self._stats.rejected_calls += 1

            if self._fallback:
                logger.debug(f"CircuitBreaker '{self.name}': Fallback 실행")
                return self._fallback(*args, **kwargs)

            raise CircuitOpenError(f"CircuitBreaker '{self.name}' is OPEN")

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result

        except Exception as e:
            self._record_failure(e)
            raise

    def reset(self):
        """회로 강제 리셋"""
        with self._state_lock:
            self._transition_to(CircuitState.CLOSED)
            self._stats.consecutive_failures = 0
            self._stats.consecutive_successes = 0
            self._call_history.clear()
        logger.info(f"CircuitBreaker '{self.name}' 리셋")

    def get_stats(self) -> Dict:
        """통계 반환"""
        with self._state_lock:
            failure_rate = 0
            if self._call_history:
                failure_rate = self._call_history.count(False) / len(self._call_history) * 100

            return {
                'name': self.name,
                'state': self._state.value,
                'total_calls': self._stats.total_calls,
                'successful_calls': self._stats.successful_calls,
                'failed_calls': self._stats.failed_calls,
                'rejected_calls': self._stats.rejected_calls,
                'failure_rate': round(failure_rate, 2),
                'consecutive_failures': self._stats.consecutive_failures,
                'consecutive_successes': self._stats.consecutive_successes,
                'last_failure': self._stats.last_failure_time.isoformat() if self._stats.last_failure_time else None,
                'last_success': self._stats.last_success_time.isoformat() if self._stats.last_success_time else None,
                'state_changes': self._stats.state_changes,
                'recovery_timeout': self.recovery_timeout,
                'time_in_state': (datetime.now() - self._last_state_change).total_seconds()
            }


class CircuitOpenError(Exception):
    """회로 열림 예외"""
    pass


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    fallback: Callable = None
):
    """서킷 브레이커 데코레이터

    사용법:
        @circuit_breaker("api_call", failure_threshold=3, recovery_timeout=30)
        def call_external_api():
            ...
    """
    breaker = CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )
    if fallback:
        breaker.set_fallback(fallback)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return breaker.execute(func, *args, **kwargs)
        wrapper._circuit_breaker = breaker
        return wrapper
    return decorator


# 전역 서킷 브레이커 레지스트리
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """이름으로 서킷 브레이커 가져오기 (없으면 생성)"""
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name=name, **kwargs)
        return _circuit_breakers[name]


def get_all_circuit_stats() -> Dict[str, Dict]:
    """모든 서킷 브레이커 통계 반환"""
    with _registry_lock:
        return {name: cb.get_stats() for name, cb in _circuit_breakers.items()}
