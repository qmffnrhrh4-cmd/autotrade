"""
Self-Healing Engine - 자가 치유 엔진
시스템 장애 감지 및 자동 복구
"""
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

from utils.logger_new import get_logger

logger = get_logger()


class HealthStatus(Enum):
    """건강 상태"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class ComponentType(Enum):
    """컴포넌트 타입"""
    API = "api"
    DATABASE = "database"
    WEBSOCKET = "websocket"
    SCHEDULER = "scheduler"
    EVOLUTION = "evolution"
    TRADING = "trading"


@dataclass
class HealthCheck:
    """건강 체크 설정"""
    name: str
    component_type: ComponentType
    check_func: Callable[[], bool]
    interval_seconds: float = 30.0
    timeout_seconds: float = 10.0
    failure_threshold: int = 3
    recovery_func: Optional[Callable[[], bool]] = None


@dataclass
class ComponentHealth:
    """컴포넌트 건강 상태"""
    name: str
    status: HealthStatus = HealthStatus.HEALTHY
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    total_failures: int = 0
    recovery_attempts: int = 0
    last_error: str = ""


class SelfHealingEngine:
    """자가 치유 엔진

    특징:
    - 주기적 건강 체크
    - 자동 장애 감지
    - 자동 복구 시도
    - 데이터 무결성 검증
    - 알림 및 에스컬레이션
    """

    def __init__(self):
        self._health_checks: Dict[str, HealthCheck] = {}
        self._component_health: Dict[str, ComponentHealth] = {}
        self._lock = threading.RLock()

        # 복구 큐
        self._recovery_queue: List[str] = []
        self._recovery_lock = threading.Lock()

        # 이벤트 콜백
        self._on_unhealthy_callbacks: List[Callable] = []
        self._on_recovery_callbacks: List[Callable] = []

        # 스레드
        self._running = False
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._recovery_thread: Optional[threading.Thread] = None

        # 통계
        self._stats = {
            'total_checks': 0,
            'total_failures': 0,
            'total_recoveries': 0,
            'failed_recoveries': 0
        }

        logger.info("SelfHealingEngine 초기화")

    def register_health_check(self, health_check: HealthCheck):
        """건강 체크 등록"""
        with self._lock:
            self._health_checks[health_check.name] = health_check
            self._component_health[health_check.name] = ComponentHealth(name=health_check.name)
        logger.info(f"건강 체크 등록: {health_check.name} (간격: {health_check.interval_seconds}s)")

    def register_component(
        self,
        name: str,
        component_type: ComponentType,
        check_func: Callable[[], bool],
        recovery_func: Callable[[], bool] = None,
        interval: float = 30.0,
        failure_threshold: int = 3
    ):
        """컴포넌트 등록 (간편 버전)"""
        health_check = HealthCheck(
            name=name,
            component_type=component_type,
            check_func=check_func,
            interval_seconds=interval,
            failure_threshold=failure_threshold,
            recovery_func=recovery_func
        )
        self.register_health_check(health_check)

    def on_unhealthy(self, callback: Callable):
        """비정상 상태 콜백 등록"""
        self._on_unhealthy_callbacks.append(callback)

    def on_recovery(self, callback: Callable):
        """복구 완료 콜백 등록"""
        self._on_recovery_callbacks.append(callback)

    def start(self):
        """모니터링 시작"""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="SelfHealing-Monitor",
            daemon=True
        )
        self._monitor_thread.start()

        self._recovery_thread = threading.Thread(
            target=self._recovery_loop,
            name="SelfHealing-Recovery",
            daemon=True
        )
        self._recovery_thread.start()

        logger.info("SelfHealingEngine 시작")

    def stop(self):
        """모니터링 중지"""
        self._running = False
        self._stop_event.set()

        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        if self._recovery_thread:
            self._recovery_thread.join(timeout=5)

        logger.info("SelfHealingEngine 중지")

    def _monitor_loop(self):
        """모니터링 루프"""
        last_check_times: Dict[str, datetime] = {}

        while self._running:
            try:
                now = datetime.now()

                with self._lock:
                    checks_to_run = []
                    for name, check in self._health_checks.items():
                        last_check = last_check_times.get(name, datetime.min)
                        if (now - last_check).total_seconds() >= check.interval_seconds:
                            checks_to_run.append(check)
                            last_check_times[name] = now

                for check in checks_to_run:
                    self._run_health_check(check)

                self._stop_event.wait(timeout=1.0)

            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
                time.sleep(1)

    def _run_health_check(self, check: HealthCheck):
        """건강 체크 실행"""
        self._stats['total_checks'] += 1

        with self._lock:
            health = self._component_health[check.name]
            health.total_checks += 1
            health.last_check = datetime.now()

        try:
            # 타임아웃 적용
            result = self._execute_with_timeout(check.check_func, check.timeout_seconds)

            if result:
                self._record_success(check.name)
            else:
                self._record_failure(check.name, "체크 함수 False 반환")

        except Exception as e:
            self._record_failure(check.name, str(e))

    def _execute_with_timeout(self, func: Callable, timeout: float) -> bool:
        """타임아웃을 적용하여 함수 실행"""
        result = [False]
        exception = [None]

        def target():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            raise TimeoutError(f"건강 체크 타임아웃 ({timeout}s)")

        if exception[0]:
            raise exception[0]

        return result[0]

    def _record_success(self, name: str):
        """성공 기록"""
        with self._lock:
            health = self._component_health[name]
            was_unhealthy = health.status != HealthStatus.HEALTHY

            health.last_success = datetime.now()
            health.consecutive_failures = 0
            health.status = HealthStatus.HEALTHY

            if was_unhealthy:
                logger.info(f"컴포넌트 복구됨: {name}")
                self._notify_recovery(name)

    def _record_failure(self, name: str, error: str):
        """실패 기록"""
        self._stats['total_failures'] += 1

        with self._lock:
            health = self._component_health[name]
            check = self._health_checks[name]

            health.last_failure = datetime.now()
            health.consecutive_failures += 1
            health.total_failures += 1
            health.last_error = error[:200]

            # 상태 결정
            if health.consecutive_failures >= check.failure_threshold * 2:
                health.status = HealthStatus.CRITICAL
            elif health.consecutive_failures >= check.failure_threshold:
                health.status = HealthStatus.UNHEALTHY
            else:
                health.status = HealthStatus.DEGRADED

            logger.warning(f"컴포넌트 장애: {name} ({health.consecutive_failures}회 연속) - {error}")

            # 복구 대상 추가
            if health.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                self._notify_unhealthy(name)
                if check.recovery_func and name not in self._recovery_queue:
                    with self._recovery_lock:
                        self._recovery_queue.append(name)

    def _notify_unhealthy(self, name: str):
        """비정상 상태 알림"""
        for callback in self._on_unhealthy_callbacks:
            try:
                callback(name, self._component_health[name])
            except Exception as e:
                logger.error(f"비정상 콜백 오류: {e}")

    def _notify_recovery(self, name: str):
        """복구 알림"""
        for callback in self._on_recovery_callbacks:
            try:
                callback(name, self._component_health[name])
            except Exception as e:
                logger.error(f"복구 콜백 오류: {e}")

    def _recovery_loop(self):
        """복구 루프"""
        while self._running:
            try:
                name_to_recover = None

                with self._recovery_lock:
                    if self._recovery_queue:
                        name_to_recover = self._recovery_queue.pop(0)

                if name_to_recover:
                    self._attempt_recovery(name_to_recover)

                self._stop_event.wait(timeout=5.0)

            except Exception as e:
                logger.error(f"복구 루프 오류: {e}")
                time.sleep(1)

    def _attempt_recovery(self, name: str):
        """복구 시도"""
        with self._lock:
            check = self._health_checks.get(name)
            health = self._component_health.get(name)

            if not check or not check.recovery_func:
                return

            health.recovery_attempts += 1

        logger.info(f"복구 시도: {name} (시도 {health.recovery_attempts}회)")

        try:
            success = check.recovery_func()

            if success:
                self._stats['total_recoveries'] += 1
                logger.info(f"복구 성공: {name}")
                # 다음 건강 체크에서 상태 갱신
            else:
                self._stats['failed_recoveries'] += 1
                logger.warning(f"복구 실패: {name}")
                # 재시도 대기열에 추가 (최대 3회)
                with self._lock:
                    if health.recovery_attempts < 3:
                        with self._recovery_lock:
                            self._recovery_queue.append(name)

        except Exception as e:
            self._stats['failed_recoveries'] += 1
            logger.error(f"복구 중 오류 ({name}): {e}")

    # === 데이터 무결성 검증 ===

    def verify_data_integrity(self, db_session) -> Dict[str, Any]:
        """데이터 무결성 검증"""
        issues = []

        try:
            # 1. 고아 포지션 검사 (전략 없는 포지션)
            from virtual_trading.database import VirtualPosition, VirtualStrategy
            orphaned = db_session.query(VirtualPosition).filter(
                ~VirtualPosition.strategy_id.in_(
                    db_session.query(VirtualStrategy.id)
                )
            ).count()

            if orphaned > 0:
                issues.append({
                    'type': 'orphaned_positions',
                    'count': orphaned,
                    'severity': 'high'
                })

            # 2. 음수 잔고 검사
            negative = db_session.query(VirtualStrategy).filter(
                VirtualStrategy.cash < 0
            ).count()

            if negative > 0:
                issues.append({
                    'type': 'negative_balance',
                    'count': negative,
                    'severity': 'critical'
                })

            # 3. 비정상 가격 검사
            from virtual_trading.database import VirtualPosition
            invalid_prices = db_session.query(VirtualPosition).filter(
                (VirtualPosition.current_price <= 0) |
                (VirtualPosition.entry_price <= 0)
            ).count()

            if invalid_prices > 0:
                issues.append({
                    'type': 'invalid_prices',
                    'count': invalid_prices,
                    'severity': 'high'
                })

        except Exception as e:
            logger.error(f"무결성 검증 오류: {e}")
            issues.append({
                'type': 'verification_error',
                'message': str(e),
                'severity': 'critical'
            })

        return {
            'verified_at': datetime.now().isoformat(),
            'issues': issues,
            'is_healthy': len(issues) == 0
        }

    def auto_repair(self, db_session, issue_type: str) -> bool:
        """자동 복구"""
        try:
            if issue_type == 'orphaned_positions':
                from virtual_trading.database import VirtualPosition, VirtualStrategy
                orphaned = db_session.query(VirtualPosition).filter(
                    ~VirtualPosition.strategy_id.in_(
                        db_session.query(VirtualStrategy.id)
                    )
                )
                count = orphaned.delete(synchronize_session=False)
                db_session.commit()
                logger.info(f"고아 포지션 {count}개 삭제")
                return True

            elif issue_type == 'invalid_prices':
                # 가격 0인 포지션 제거 또는 현재가로 업데이트
                logger.warning("비정상 가격 자동 복구 - 수동 확인 필요")
                return False

        except Exception as e:
            db_session.rollback()
            logger.error(f"자동 복구 실패 ({issue_type}): {e}")
            return False

        return False

    # === 상태 조회 ===

    def get_status(self) -> Dict:
        """전체 상태 반환"""
        with self._lock:
            components = {}
            for name, health in self._component_health.items():
                components[name] = {
                    'status': health.status.value,
                    'last_check': health.last_check.isoformat() if health.last_check else None,
                    'last_success': health.last_success.isoformat() if health.last_success else None,
                    'consecutive_failures': health.consecutive_failures,
                    'total_failures': health.total_failures,
                    'recovery_attempts': health.recovery_attempts,
                    'last_error': health.last_error
                }

            overall_status = HealthStatus.HEALTHY
            for health in self._component_health.values():
                if health.status == HealthStatus.CRITICAL:
                    overall_status = HealthStatus.CRITICAL
                    break
                elif health.status == HealthStatus.UNHEALTHY and overall_status != HealthStatus.CRITICAL:
                    overall_status = HealthStatus.UNHEALTHY
                elif health.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED

            return {
                'overall_status': overall_status.value,
                'components': components,
                'stats': self._stats.copy(),
                'recovery_queue_size': len(self._recovery_queue),
                'running': self._running
            }

    def is_healthy(self) -> bool:
        """전체 건강 여부"""
        with self._lock:
            return all(h.status == HealthStatus.HEALTHY for h in self._component_health.values())


# 싱글톤 인스턴스
_healing_engine: Optional[SelfHealingEngine] = None
_instance_lock = threading.Lock()


def get_healing_engine() -> SelfHealingEngine:
    """SelfHealingEngine 싱글톤 인스턴스 반환"""
    global _healing_engine

    with _instance_lock:
        if _healing_engine is None:
            _healing_engine = SelfHealingEngine()

    return _healing_engine
