"""
utils/diagnostic_logger.py
시스템 진단 및 분석 로깅 시스템

Claude Code가 향후 세션에서 이전 문제를 분석할 수 있도록
모든 API 호출, 데이터 수신 상태, 시스템 상태를 기록합니다.

사용법:
    from utils.diagnostic_logger import DiagnosticLogger

    diag = DiagnosticLogger.get_instance()
    diag.log_api_call("get_stock_price", success=True, data_count=100)
    diag.log_error("scanner", "No data received", {"api": "ka10031"})
"""
import json
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field, asdict


@dataclass
class APICallRecord:
    """API 호출 기록"""
    api_name: str
    timestamp: str
    success: bool
    data_count: int
    response_time_ms: float
    error_message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """에러 기록"""
    component: str
    timestamp: str
    error_type: str
    message: str
    stack_trace: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealthSnapshot:
    """시스템 상태 스냅샷"""
    timestamp: str
    market_scan_stocks: int
    evolution_generation: int
    evolution_fitness: float
    virtual_trades_count: int
    real_trades_count: int
    api_success_rate: float
    active_strategies: List[str]
    market_condition: str
    last_price_update: str
    memory_usage_mb: float = 0.0


class DiagnosticLogger:
    """
    시스템 진단 로거 (싱글톤)

    모든 API 호출, 에러, 시스템 상태를 추적하고
    JSON 파일로 저장하여 향후 분석에 활용
    """

    _instance: Optional['DiagnosticLogger'] = None
    _lock = threading.Lock()

    # 진단 파일 경로
    DIAGNOSTIC_FILE = Path("logs/system_diagnostic.json")
    DIAGNOSTIC_HISTORY_FILE = Path("logs/diagnostic_history.json")

    # 최대 기록 수
    MAX_API_RECORDS = 500
    MAX_ERROR_RECORDS = 200
    MAX_HEALTH_SNAPSHOTS = 100

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

        # 기록 저장소
        self.api_calls: List[APICallRecord] = []
        self.errors: List[ErrorRecord] = []
        self.health_snapshots: List[SystemHealthSnapshot] = []

        # 통계
        self.api_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_calls': 0,
            'success_count': 0,
            'failure_count': 0,
            'total_data_count': 0,
            'avg_response_time_ms': 0.0,
            'last_call': None,
            'last_error': None
        })

        # 컴포넌트별 에러 카운트
        self.error_counts: Dict[str, int] = defaultdict(int)

        # 세션 시작 시간
        self.session_start = datetime.now().isoformat()

        # 로그 디렉토리 생성
        self.DIAGNOSTIC_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 이전 기록 로드
        self._load_history()

    @classmethod
    def get_instance(cls) -> 'DiagnosticLogger':
        """싱글톤 인스턴스 반환"""
        return cls()

    def _load_history(self):
        """이전 진단 기록 로드"""
        try:
            if self.DIAGNOSTIC_HISTORY_FILE.exists():
                with open(self.DIAGNOSTIC_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    # 이전 세션 정보만 로드 (현재 세션과 구분)
                    self._previous_sessions = history.get('sessions', [])
            else:
                self._previous_sessions = []
        except Exception:
            self._previous_sessions = []

    def log_api_call(
        self,
        api_name: str,
        success: bool,
        data_count: int = 0,
        response_time_ms: float = 0.0,
        error_message: str = "",
        **details
    ):
        """
        API 호출 기록

        Args:
            api_name: API 이름 (예: "get_stock_price", "get_volume_rank")
            success: 성공 여부
            data_count: 받은 데이터 수
            response_time_ms: 응답 시간 (밀리초)
            error_message: 실패 시 에러 메시지
            **details: 추가 상세 정보
        """
        record = APICallRecord(
            api_name=api_name,
            timestamp=datetime.now().isoformat(),
            success=success,
            data_count=data_count,
            response_time_ms=response_time_ms,
            error_message=error_message,
            details=details
        )

        with self._lock:
            self.api_calls.append(record)

            # 최대 기록 수 제한
            if len(self.api_calls) > self.MAX_API_RECORDS:
                self.api_calls = self.api_calls[-self.MAX_API_RECORDS:]

            # 통계 업데이트
            stats = self.api_stats[api_name]
            stats['total_calls'] += 1
            stats['last_call'] = record.timestamp

            if success:
                stats['success_count'] += 1
                stats['total_data_count'] += data_count
            else:
                stats['failure_count'] += 1
                stats['last_error'] = error_message

            # 평균 응답 시간 업데이트
            total = stats['total_calls']
            stats['avg_response_time_ms'] = (
                (stats['avg_response_time_ms'] * (total - 1) + response_time_ms) / total
            )

        # 자동 저장 (100번 호출마다)
        if len(self.api_calls) % 100 == 0:
            self.save()

    def log_error(
        self,
        component: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        error_type: str = "ERROR",
        stack_trace: str = ""
    ):
        """
        에러 기록

        Args:
            component: 컴포넌트 이름 (예: "scanner", "evolution", "api")
            message: 에러 메시지
            context: 추가 컨텍스트 정보
            error_type: 에러 유형
            stack_trace: 스택 트레이스
        """
        record = ErrorRecord(
            component=component,
            timestamp=datetime.now().isoformat(),
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
            context=context or {}
        )

        with self._lock:
            self.errors.append(record)
            self.error_counts[component] += 1

            # 최대 기록 수 제한
            if len(self.errors) > self.MAX_ERROR_RECORDS:
                self.errors = self.errors[-self.MAX_ERROR_RECORDS:]

        # 에러는 즉시 저장
        self.save()

    def log_health_snapshot(
        self,
        market_scan_stocks: int = 0,
        evolution_generation: int = 0,
        evolution_fitness: float = 0.0,
        virtual_trades_count: int = 0,
        real_trades_count: int = 0,
        active_strategies: Optional[List[str]] = None,
        market_condition: str = "unknown",
        last_price_update: str = ""
    ):
        """
        시스템 상태 스냅샷 기록

        Args:
            market_scan_stocks: 시장 스캔된 종목 수
            evolution_generation: 진화 세대
            evolution_fitness: 진화 적합도
            virtual_trades_count: 가상 거래 수
            real_trades_count: 실제 거래 수
            active_strategies: 활성 전략 목록
            market_condition: 시장 상황
            last_price_update: 마지막 가격 업데이트 시간
        """
        # 메모리 사용량 측정
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
        except ImportError:
            memory_mb = 0.0

        # API 성공률 계산
        total_calls = sum(s['total_calls'] for s in self.api_stats.values())
        success_calls = sum(s['success_count'] for s in self.api_stats.values())
        api_success_rate = (success_calls / total_calls * 100) if total_calls > 0 else 0.0

        snapshot = SystemHealthSnapshot(
            timestamp=datetime.now().isoformat(),
            market_scan_stocks=market_scan_stocks,
            evolution_generation=evolution_generation,
            evolution_fitness=evolution_fitness,
            virtual_trades_count=virtual_trades_count,
            real_trades_count=real_trades_count,
            api_success_rate=round(api_success_rate, 2),
            active_strategies=active_strategies or [],
            market_condition=market_condition,
            last_price_update=last_price_update,
            memory_usage_mb=round(memory_mb, 2)
        )

        with self._lock:
            self.health_snapshots.append(snapshot)

            # 최대 기록 수 제한
            if len(self.health_snapshots) > self.MAX_HEALTH_SNAPSHOTS:
                self.health_snapshots = self.health_snapshots[-self.MAX_HEALTH_SNAPSHOTS:]

        self.save()

    def get_api_summary(self) -> Dict[str, Any]:
        """API 호출 요약 반환"""
        summary = {}
        for api_name, stats in self.api_stats.items():
            success_rate = (
                stats['success_count'] / stats['total_calls'] * 100
                if stats['total_calls'] > 0 else 0
            )
            summary[api_name] = {
                'total_calls': stats['total_calls'],
                'success_rate': round(success_rate, 2),
                'avg_data_count': (
                    stats['total_data_count'] / stats['success_count']
                    if stats['success_count'] > 0 else 0
                ),
                'avg_response_time_ms': round(stats['avg_response_time_ms'], 2),
                'last_call': stats['last_call'],
                'last_error': stats['last_error']
            }
        return summary

    def get_error_summary(self) -> Dict[str, Any]:
        """에러 요약 반환"""
        # 최근 에러 (최신 10개)
        recent_errors = [asdict(e) for e in self.errors[-10:]]

        # 컴포넌트별 에러 수
        by_component = dict(self.error_counts)

        # 시간대별 에러 분포 (최근 1시간)
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        recent_count = sum(
            1 for e in self.errors
            if e.timestamp >= one_hour_ago
        )

        return {
            'total_errors': len(self.errors),
            'errors_last_hour': recent_count,
            'by_component': by_component,
            'recent_errors': recent_errors
        }

    def get_health_trend(self) -> Dict[str, Any]:
        """시스템 상태 트렌드 반환"""
        if not self.health_snapshots:
            return {'status': 'no_data'}

        latest = self.health_snapshots[-1]

        # 이전 스냅샷과 비교 (있는 경우)
        if len(self.health_snapshots) >= 2:
            previous = self.health_snapshots[-2]
            trend = {
                'market_scan_trend': latest.market_scan_stocks - previous.market_scan_stocks,
                'evolution_trend': latest.evolution_generation - previous.evolution_generation,
                'fitness_trend': round(latest.evolution_fitness - previous.evolution_fitness, 4),
                'api_success_trend': round(latest.api_success_rate - previous.api_success_rate, 2)
            }
        else:
            trend = {}

        return {
            'latest': asdict(latest),
            'trend': trend,
            'total_snapshots': len(self.health_snapshots)
        }

    def generate_diagnostic_report(self) -> Dict[str, Any]:
        """
        전체 진단 보고서 생성

        Claude Code가 읽고 분석할 수 있는 형태의 종합 보고서
        """
        now = datetime.now()

        # 문제 감지
        problems = []
        warnings = []

        # API 문제 감지
        for api_name, stats in self.api_stats.items():
            if stats['total_calls'] > 0:
                success_rate = stats['success_count'] / stats['total_calls'] * 100
                if success_rate < 50:
                    problems.append({
                        'type': 'api_failure',
                        'api': api_name,
                        'success_rate': round(success_rate, 2),
                        'message': f"API '{api_name}' 성공률이 50% 미만입니다."
                    })
                elif success_rate < 80:
                    warnings.append({
                        'type': 'api_degraded',
                        'api': api_name,
                        'success_rate': round(success_rate, 2),
                        'message': f"API '{api_name}' 성공률이 80% 미만입니다."
                    })

        # 데이터 부족 감지
        if self.health_snapshots:
            latest = self.health_snapshots[-1]
            if latest.market_scan_stocks < 10:
                problems.append({
                    'type': 'insufficient_data',
                    'component': 'market_scan',
                    'value': latest.market_scan_stocks,
                    'message': f"시장 스캔 종목이 10개 미만입니다. ({latest.market_scan_stocks}개)"
                })
            if latest.evolution_fitness == 0 and latest.evolution_generation > 0:
                problems.append({
                    'type': 'evolution_stalled',
                    'generation': latest.evolution_generation,
                    'fitness': latest.evolution_fitness,
                    'message': "진화 알고리즘 적합도가 0입니다. 거래 데이터가 부족합니다."
                })

        # 에러 빈도 감지
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        recent_errors = [e for e in self.errors if e.timestamp >= one_hour_ago]
        if len(recent_errors) > 20:
            problems.append({
                'type': 'high_error_rate',
                'count': len(recent_errors),
                'message': f"최근 1시간 동안 에러가 {len(recent_errors)}건 발생했습니다."
            })

        report = {
            'report_generated': now.isoformat(),
            'session_start': self.session_start,
            'session_duration_minutes': round(
                (now - datetime.fromisoformat(self.session_start)).total_seconds() / 60, 2
            ),
            'summary': {
                'total_api_calls': sum(s['total_calls'] for s in self.api_stats.values()),
                'total_errors': len(self.errors),
                'health_snapshots': len(self.health_snapshots),
                'problem_count': len(problems),
                'warning_count': len(warnings)
            },
            'problems': problems,
            'warnings': warnings,
            'api_summary': self.get_api_summary(),
            'error_summary': self.get_error_summary(),
            'health_trend': self.get_health_trend(),
            'recommendations': self._generate_recommendations(problems, warnings)
        }

        return report

    def _generate_recommendations(
        self,
        problems: List[Dict],
        warnings: List[Dict]
    ) -> List[str]:
        """문제에 대한 권장 사항 생성"""
        recommendations = []

        for problem in problems:
            if problem['type'] == 'api_failure':
                recommendations.append(
                    f"API '{problem['api']}' 연결 상태를 확인하세요. "
                    f"네트워크 또는 API 서버 문제일 수 있습니다."
                )
            elif problem['type'] == 'insufficient_data':
                recommendations.append(
                    f"시장 스캔 필터 조건을 완화하거나 "
                    f"다중 API 소스를 추가로 활성화하세요."
                )
            elif problem['type'] == 'evolution_stalled':
                recommendations.append(
                    "가상 매매 스코어 임계값을 낮추거나 "
                    "분석 후보 종목 수를 늘려 거래 데이터를 확보하세요."
                )
            elif problem['type'] == 'high_error_rate':
                recommendations.append(
                    "에러 로그를 확인하여 반복되는 문제의 원인을 파악하세요."
                )

        if not recommendations:
            recommendations.append("현재 시스템이 정상적으로 작동 중입니다.")

        return recommendations

    def save(self):
        """진단 데이터 파일 저장"""
        try:
            report = self.generate_diagnostic_report()

            # 최근 API 호출 기록 추가
            report['recent_api_calls'] = [
                asdict(call) for call in self.api_calls[-50:]
            ]

            with open(self.DIAGNOSTIC_FILE, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 저장 실패해도 계속 진행
            pass

    def save_session_history(self):
        """세션 종료 시 히스토리 저장"""
        try:
            session_summary = {
                'session_start': self.session_start,
                'session_end': datetime.now().isoformat(),
                'summary': {
                    'total_api_calls': sum(s['total_calls'] for s in self.api_stats.values()),
                    'total_errors': len(self.errors),
                    'api_stats': self.get_api_summary()
                }
            }

            # 기존 히스토리에 추가
            self._previous_sessions.append(session_summary)

            # 최근 30세션만 유지
            if len(self._previous_sessions) > 30:
                self._previous_sessions = self._previous_sessions[-30:]

            history = {'sessions': self._previous_sessions}

            with open(self.DIAGNOSTIC_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


# 전역 인스턴스 접근 함수들
def get_diagnostic_logger() -> DiagnosticLogger:
    """진단 로거 인스턴스 반환"""
    return DiagnosticLogger.get_instance()


def log_api_call(api_name: str, success: bool, **kwargs):
    """API 호출 기록 (편의 함수)"""
    get_diagnostic_logger().log_api_call(api_name, success, **kwargs)


def log_error(component: str, message: str, **kwargs):
    """에러 기록 (편의 함수)"""
    get_diagnostic_logger().log_error(component, message, **kwargs)


def log_health_snapshot(**kwargs):
    """시스템 상태 스냅샷 기록 (편의 함수)"""
    get_diagnostic_logger().log_health_snapshot(**kwargs)


__all__ = [
    'DiagnosticLogger',
    'get_diagnostic_logger',
    'log_api_call',
    'log_error',
    'log_health_snapshot',
    'APICallRecord',
    'ErrorRecord',
    'SystemHealthSnapshot'
]
