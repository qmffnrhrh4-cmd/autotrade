"""
Database Transaction Safety - DB 트랜잭션 안전성 강화
롤백, 재시도, 연결 풀링 지원
"""
import time
import threading
from typing import Callable, TypeVar, Optional, Any
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from sqlalchemy.orm import Session

from utils.logger_new import get_logger

logger = get_logger()

T = TypeVar('T')


@dataclass
class TransactionStats:
    """트랜잭션 통계"""
    total_transactions: int = 0
    successful: int = 0
    failed: int = 0
    retried: int = 0
    rollbacks: int = 0
    total_time_ms: float = 0
    last_error: str = ""
    last_error_time: Optional[datetime] = None


class TransactionManager:
    """트랜잭션 관리자

    특징:
    - 자동 롤백
    - 재시도 로직 (지수 백오프)
    - 연결 오류 복구
    - 성능 모니터링
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 0.5):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._stats = TransactionStats()
        self._stats_lock = threading.Lock()

        logger.info(f"TransactionManager 초기화 (max_retries={max_retries})")

    @contextmanager
    def transaction(self, session: Session, auto_commit: bool = True):
        """안전한 트랜잭션 컨텍스트 매니저

        사용법:
            with transaction_manager.transaction(db_session) as txn:
                db_session.add(obj)
                # 자동 커밋/롤백

        Args:
            session: SQLAlchemy 세션
            auto_commit: 자동 커밋 여부

        Yields:
            세션 객체
        """
        start_time = time.time()

        with self._stats_lock:
            self._stats.total_transactions += 1

        try:
            yield session

            if auto_commit:
                session.commit()

            with self._stats_lock:
                self._stats.successful += 1
                self._stats.total_time_ms += (time.time() - start_time) * 1000

        except IntegrityError as e:
            session.rollback()
            with self._stats_lock:
                self._stats.failed += 1
                self._stats.rollbacks += 1
                self._stats.last_error = f"IntegrityError: {str(e)[:100]}"
                self._stats.last_error_time = datetime.now()
            logger.error(f"무결성 오류, 롤백 완료: {e}")
            raise

        except OperationalError as e:
            session.rollback()
            with self._stats_lock:
                self._stats.failed += 1
                self._stats.rollbacks += 1
                self._stats.last_error = f"OperationalError: {str(e)[:100]}"
                self._stats.last_error_time = datetime.now()
            logger.error(f"운영 오류, 롤백 완료: {e}")
            raise

        except SQLAlchemyError as e:
            session.rollback()
            with self._stats_lock:
                self._stats.failed += 1
                self._stats.rollbacks += 1
                self._stats.last_error = f"SQLAlchemyError: {str(e)[:100]}"
                self._stats.last_error_time = datetime.now()
            logger.error(f"DB 오류, 롤백 완료: {e}")
            raise

        except Exception as e:
            session.rollback()
            with self._stats_lock:
                self._stats.failed += 1
                self._stats.rollbacks += 1
                self._stats.last_error = f"Exception: {str(e)[:100]}"
                self._stats.last_error_time = datetime.now()
            logger.error(f"예외 발생, 롤백 완료: {e}")
            raise

    def execute_with_retry(self, session: Session, operation: Callable[[], T],
                           max_retries: int = None) -> T:
        """재시도 로직을 포함한 DB 작업 실행

        Args:
            session: SQLAlchemy 세션
            operation: 실행할 작업 (callable)
            max_retries: 최대 재시도 횟수

        Returns:
            작업 결과

        Raises:
            마지막 예외 (모든 재시도 실패 시)
        """
        max_retries = max_retries or self.max_retries
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                with self.transaction(session, auto_commit=True):
                    return operation()

            except OperationalError as e:
                last_exception = e
                if attempt < max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # 지수 백오프
                    with self._stats_lock:
                        self._stats.retried += 1
                    logger.warning(f"DB 연결 오류, {delay:.1f}초 후 재시도 ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"DB 작업 실패 (모든 재시도 소진): {e}")
                    raise

            except IntegrityError as e:
                # 무결성 오류는 재시도 의미 없음
                logger.error(f"무결성 오류, 재시도 불가: {e}")
                raise

            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    with self._stats_lock:
                        self._stats.retried += 1
                    logger.warning(f"예외 발생, {delay:.1f}초 후 재시도 ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(delay)
                else:
                    raise

        raise last_exception

    def safe_add(self, session: Session, obj: Any) -> bool:
        """안전한 객체 추가

        Args:
            session: SQLAlchemy 세션
            obj: 추가할 객체

        Returns:
            성공 여부
        """
        try:
            with self.transaction(session):
                session.add(obj)
            return True
        except Exception as e:
            logger.error(f"객체 추가 실패: {e}")
            return False

    def safe_delete(self, session: Session, obj: Any) -> bool:
        """안전한 객체 삭제

        Args:
            session: SQLAlchemy 세션
            obj: 삭제할 객체

        Returns:
            성공 여부
        """
        try:
            with self.transaction(session):
                session.delete(obj)
            return True
        except Exception as e:
            logger.error(f"객체 삭제 실패: {e}")
            return False

    def get_stats(self) -> dict:
        """통계 반환"""
        with self._stats_lock:
            stats = {
                'total_transactions': self._stats.total_transactions,
                'successful': self._stats.successful,
                'failed': self._stats.failed,
                'retried': self._stats.retried,
                'rollbacks': self._stats.rollbacks,
                'success_rate': (
                    self._stats.successful / self._stats.total_transactions * 100
                    if self._stats.total_transactions > 0 else 0
                ),
                'avg_time_ms': (
                    self._stats.total_time_ms / self._stats.successful
                    if self._stats.successful > 0 else 0
                ),
                'last_error': self._stats.last_error,
                'last_error_time': (
                    self._stats.last_error_time.isoformat()
                    if self._stats.last_error_time else None
                )
            }
        return stats

    def reset_stats(self):
        """통계 초기화"""
        with self._stats_lock:
            self._stats = TransactionStats()


def transactional(session_getter: Callable[[], Session], max_retries: int = 3):
    """트랜잭션 데코레이터

    사용법:
        @transactional(lambda: db_session, max_retries=3)
        def save_trade(trade_data):
            ...

    Args:
        session_getter: 세션을 반환하는 함수
        max_retries: 최대 재시도 횟수
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            session = session_getter()
            manager = get_transaction_manager()

            def operation():
                return func(*args, **kwargs)

            return manager.execute_with_retry(session, operation, max_retries)
        return wrapper
    return decorator


# 싱글톤 인스턴스
_transaction_manager: Optional[TransactionManager] = None
_instance_lock = threading.Lock()


def get_transaction_manager() -> TransactionManager:
    """TransactionManager 싱글톤 인스턴스 반환"""
    global _transaction_manager

    with _instance_lock:
        if _transaction_manager is None:
            _transaction_manager = TransactionManager()

    return _transaction_manager
