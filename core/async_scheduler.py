"""
Async Scheduler - 비동기 스케줄러
Event 기반 스케줄링으로 time.sleep() 대체
"""
import time
import threading
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import heapq

from utils.logger_new import get_logger

logger = get_logger()


class TaskPriority(Enum):
    """태스크 우선순위"""
    CRITICAL = 0   # 긴급 (즉시 실행)
    HIGH = 1       # 높음
    NORMAL = 2     # 보통
    LOW = 3        # 낮음
    BACKGROUND = 4 # 백그라운드


@dataclass(order=True)
class ScheduledTask:
    """스케줄된 태스크"""
    next_run: datetime = field(compare=True)
    priority: int = field(compare=True)
    task_id: str = field(compare=False)
    callback: Callable = field(compare=False)
    interval_seconds: float = field(compare=False)
    name: str = field(compare=False, default="")
    enabled: bool = field(compare=False, default=True)
    last_run: Optional[datetime] = field(compare=False, default=None)
    run_count: int = field(compare=False, default=0)
    error_count: int = field(compare=False, default=0)
    last_error: str = field(compare=False, default="")
    avg_duration_ms: float = field(compare=False, default=0)


class AsyncScheduler:
    """비동기 이벤트 기반 스케줄러

    특징:
    - Event 기반으로 CPU 사용 최소화
    - 우선순위 기반 실행
    - 동적 태스크 추가/제거
    - 성능 모니터링
    """

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self._running = False
        self._stop_event = threading.Event()

        # 태스크 큐 (힙 기반 우선순위 큐)
        self._task_queue: List[ScheduledTask] = []
        self._task_map: Dict[str, ScheduledTask] = {}
        self._queue_lock = threading.Lock()

        # 워커 스레드
        self._worker_thread: Optional[threading.Thread] = None
        self._executor_threads: List[threading.Thread] = []

        # 실행 대기 이벤트
        self._work_available = threading.Event()

        # 통계
        self._stats = {
            'tasks_executed': 0,
            'tasks_failed': 0,
            'total_wait_time_ms': 0
        }

        logger.info(f"AsyncScheduler 초기화 (max_workers={max_workers})")

    def add_task(self, task_id: str, callback: Callable, interval_seconds: float,
                 name: str = "", priority: TaskPriority = TaskPriority.NORMAL,
                 run_immediately: bool = False) -> bool:
        """태스크 추가

        Args:
            task_id: 태스크 고유 ID
            callback: 실행할 콜백 함수
            interval_seconds: 실행 간격 (초)
            name: 태스크 이름
            priority: 우선순위
            run_immediately: 즉시 실행 여부

        Returns:
            성공 여부
        """
        with self._queue_lock:
            if task_id in self._task_map:
                logger.warning(f"태스크 ID 중복: {task_id}")
                return False

            next_run = datetime.now() if run_immediately else datetime.now() + timedelta(seconds=interval_seconds)

            task = ScheduledTask(
                next_run=next_run,
                priority=priority.value,
                task_id=task_id,
                callback=callback,
                interval_seconds=interval_seconds,
                name=name or task_id
            )

            heapq.heappush(self._task_queue, task)
            self._task_map[task_id] = task

            # 워커 깨우기
            self._work_available.set()

        logger.info(f"태스크 추가: {name} (간격: {interval_seconds}초, 우선순위: {priority.name})")
        return True

    def remove_task(self, task_id: str) -> bool:
        """태스크 제거

        Args:
            task_id: 태스크 ID

        Returns:
            성공 여부
        """
        with self._queue_lock:
            if task_id not in self._task_map:
                return False

            task = self._task_map[task_id]
            task.enabled = False
            del self._task_map[task_id]

        logger.info(f"태스크 제거: {task_id}")
        return True

    def enable_task(self, task_id: str, enabled: bool = True) -> bool:
        """태스크 활성화/비활성화"""
        with self._queue_lock:
            if task_id not in self._task_map:
                return False
            self._task_map[task_id].enabled = enabled
        return True

    def start(self):
        """스케줄러 시작"""
        if self._running:
            logger.warning("스케줄러 이미 실행 중")
            return

        self._running = True
        self._stop_event.clear()

        self._worker_thread = threading.Thread(
            target=self._scheduler_loop,
            name="AsyncScheduler-Main",
            daemon=True
        )
        self._worker_thread.start()

        logger.info("AsyncScheduler 시작")

    def stop(self, timeout: float = 5.0):
        """스케줄러 중지"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()
        self._work_available.set()  # 대기 중인 스레드 깨우기

        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)

        logger.info("AsyncScheduler 중지")

    def _scheduler_loop(self):
        """메인 스케줄러 루프"""
        while self._running:
            try:
                # 다음 태스크까지 대기 시간 계산
                wait_time = self._get_next_wait_time()

                if wait_time > 0:
                    # 이벤트 대기 (sleep 대신)
                    wait_start = time.time()
                    triggered = self._stop_event.wait(timeout=wait_time)
                    actual_wait = (time.time() - wait_start) * 1000
                    self._stats['total_wait_time_ms'] += actual_wait

                    if triggered:
                        # 중지 신호
                        break

                # 실행할 태스크 가져오기
                tasks_to_run = self._get_due_tasks()

                # 태스크 실행
                for task in tasks_to_run:
                    self._execute_task(task)

            except Exception as e:
                logger.error(f"스케줄러 루프 오류: {e}")
                time.sleep(1)  # 오류 시 잠시 대기

    def _get_next_wait_time(self) -> float:
        """다음 태스크까지 대기 시간 반환"""
        with self._queue_lock:
            if not self._task_queue:
                return 60.0  # 태스크 없으면 1분 대기

            # 힙에서 다음 태스크 확인 (제거하지 않음)
            next_task = self._task_queue[0]
            wait_seconds = (next_task.next_run - datetime.now()).total_seconds()
            return max(0.1, min(wait_seconds, 60.0))  # 0.1초 ~ 60초

    def _get_due_tasks(self) -> List[ScheduledTask]:
        """실행할 태스크 목록 반환"""
        now = datetime.now()
        due_tasks = []

        with self._queue_lock:
            while self._task_queue:
                task = self._task_queue[0]

                if task.next_run > now:
                    break  # 아직 실행 시간 안 됨

                heapq.heappop(self._task_queue)

                if not task.enabled or task.task_id not in self._task_map:
                    continue  # 비활성화되었거나 제거됨

                due_tasks.append(task)

        return due_tasks

    def _execute_task(self, task: ScheduledTask):
        """태스크 실행"""
        start_time = time.time()

        try:
            task.callback()
            task.run_count += 1
            task.last_run = datetime.now()
            self._stats['tasks_executed'] += 1

            # 평균 실행 시간 업데이트
            duration_ms = (time.time() - start_time) * 1000
            task.avg_duration_ms = (
                (task.avg_duration_ms * (task.run_count - 1) + duration_ms) / task.run_count
            )

        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)[:200]
            self._stats['tasks_failed'] += 1
            logger.error(f"태스크 실행 오류 ({task.name}): {e}")

        finally:
            # 다음 실행 예약
            self._reschedule_task(task)

    def _reschedule_task(self, task: ScheduledTask):
        """태스크 재스케줄"""
        if not task.enabled or task.task_id not in self._task_map:
            return

        with self._queue_lock:
            task.next_run = datetime.now() + timedelta(seconds=task.interval_seconds)
            heapq.heappush(self._task_queue, task)

    def trigger_task(self, task_id: str) -> bool:
        """태스크 즉시 실행 트리거"""
        with self._queue_lock:
            if task_id not in self._task_map:
                return False

            task = self._task_map[task_id]
            task.next_run = datetime.now()

            # 힙 재정렬
            heapq.heapify(self._task_queue)

        # 워커 깨우기
        self._work_available.set()
        return True

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """태스크 상태 조회"""
        with self._queue_lock:
            task = self._task_map.get(task_id)
            if not task:
                return None

            return {
                'task_id': task.task_id,
                'name': task.name,
                'enabled': task.enabled,
                'interval_seconds': task.interval_seconds,
                'next_run': task.next_run.isoformat(),
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'run_count': task.run_count,
                'error_count': task.error_count,
                'last_error': task.last_error,
                'avg_duration_ms': round(task.avg_duration_ms, 2)
            }

    def get_all_tasks(self) -> List[Dict]:
        """모든 태스크 상태 조회"""
        result = []
        with self._queue_lock:
            for task_id in self._task_map:
                status = self.get_task_status(task_id)
                if status:
                    result.append(status)
        return sorted(result, key=lambda x: x['next_run'])

    def get_stats(self) -> Dict:
        """스케줄러 통계 반환"""
        with self._queue_lock:
            stats = self._stats.copy()
            stats['active_tasks'] = len(self._task_map)
            stats['queue_size'] = len(self._task_queue)
            stats['running'] = self._running

        return stats


# 싱글톤 인스턴스
_async_scheduler: Optional[AsyncScheduler] = None
_instance_lock = threading.Lock()


def get_async_scheduler() -> AsyncScheduler:
    """AsyncScheduler 싱글톤 인스턴스 반환"""
    global _async_scheduler

    with _instance_lock:
        if _async_scheduler is None:
            _async_scheduler = AsyncScheduler()

    return _async_scheduler
