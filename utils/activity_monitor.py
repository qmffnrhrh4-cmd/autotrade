"""
Real-time Trading Activity Monitor
실시간 매매 활동 추적
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import deque
import threading


class TradingActivityMonitor:
    """
    실시간 매매 활동 모니터

    Features:
    - 현재 검색 조건
    - 후보 종목 리스트
    - AI 분석 결과
    - 매수 계획
    - 실시간 활동 로그
    """

    def __init__(self, max_activities: int = 100, max_candidates: int = 20):
        """
        Initialize activity monitor

        Args:
            max_activities: 최대 활동 로그 수
            max_candidates: 최대 후보 종목 수
        """
        self.max_activities = max_activities
        self.max_candidates = max_candidates

        # 실시간 데이터 (메모리 관리를 위해 최대 크기 제한)
        self.activities = deque(maxlen=max_activities)  # 활동 로그
        self.candidates = []  # 후보 종목
        self.ai_analyses = {}  # AI 분석 결과 (최대 100개 유지)
        self.buy_plans = {}  # 매수 계획 (최대 50개 유지)
        self._max_ai_analyses = 100
        self._max_buy_plans = 50

        # 현재 상태
        self.current_screening = {
            'status': 'idle',  # idle, screening, analyzing, trading
            'market': '',
            'conditions': {},
            'total_screened': 0,
            'candidates_found': 0,
            'timestamp': None
        }

        # 사용자 설정 (오버라이드 가능)
        self.user_settings = {
            'auto_trade': True,
            'max_buy_amount': 1000000,  # 종목당 최대 매수 금액
            'position_size_ratio': 0.20,  # 포지션 크기 비율
            'take_profit_ratio': 0.10,  # 익절 비율
            'stop_loss_ratio': -0.05,  # 손절 비율
            'split_orders': 2,  # 분할 매수 횟수
            'ai_min_score': 7.0,  # AI 최소 점수
            'ai_min_confidence': 'Medium',  # AI 최소 신뢰도
        }

        # Thread lock
        self._lock = threading.Lock()

    def log_activity(
        self,
        activity_type: str,
        message: str,
        data: Optional[Dict] = None,
        level: str = 'info'
    ):
        """
        활동 로그 추가

        Args:
            activity_type: 활동 유형 (screening, analysis, buy, sell, etc.)
            message: 메시지
            data: 추가 데이터
            level: 로그 레벨 (info, success, warning, error)
        """
        with self._lock:
            activity = {
                'timestamp': datetime.now().isoformat(),
                'type': activity_type,
                'message': message,
                'data': data or {},
                'level': level
            }
            self.activities.append(activity)

    def update_screening_status(
        self,
        status: str,
        market: str = '',
        conditions: Optional[Dict] = None,
        total_screened: int = 0,
        candidates_found: int = 0
    ):
        """
        스크리닝 상태 업데이트

        Args:
            status: 상태
            market: 시장 (KOSPI, KOSDAQ)
            conditions: 검색 조건
            total_screened: 총 스크리닝 종목 수
            candidates_found: 발견된 후보 수
        """
        with self._lock:
            self.current_screening = {
                'status': status,
                'market': market,
                'conditions': conditions or {},
                'total_screened': total_screened,
                'candidates_found': candidates_found,
                'timestamp': datetime.now().isoformat()
            }

    def add_candidate(
        self,
        stock_code: str,
        stock_name: str,
        score: float,
        reason: str,
        data: Optional[Dict] = None
    ):
        """
        후보 종목 추가

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            score: 점수
            reason: 선정 이유
            data: 추가 데이터
        """
        with self._lock:
            candidate = {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'score': score,
                'reason': reason,
                'timestamp': datetime.now().isoformat(),
                'data': data or {},
                'ai_analyzed': False,
                'buy_plan_ready': False
            }

            # 중복 제거
            self.candidates = [c for c in self.candidates if c['stock_code'] != stock_code]
            self.candidates.append(candidate)

            # 최대 개수 유지
            if len(self.candidates) > self.max_candidates:
                self.candidates = self.candidates[-self.max_candidates:]

            # 점수순 정렬
            self.candidates.sort(key=lambda x: x['score'], reverse=True)

    def add_ai_analysis(
        self,
        stock_code: str,
        analysis_result: Dict[str, Any]
    ):
        """
        AI 분석 결과 추가

        Args:
            stock_code: 종목 코드
            analysis_result: AI 분석 결과
        """
        with self._lock:
            self.ai_analyses[stock_code] = {
                'timestamp': datetime.now().isoformat(),
                'result': analysis_result
            }

            # 메모리 관리: 최대 크기 초과시 오래된 항목 제거
            if len(self.ai_analyses) > self._max_ai_analyses:
                # 가장 오래된 항목 제거 (timestamp 기준)
                sorted_items = sorted(
                    self.ai_analyses.items(),
                    key=lambda x: x[1].get('timestamp', ''),
                    reverse=True
                )
                self.ai_analyses = dict(sorted_items[:self._max_ai_analyses])

            # 후보 종목 업데이트
            for candidate in self.candidates:
                if candidate['stock_code'] == stock_code:
                    candidate['ai_analyzed'] = True
                    break

    def add_buy_plan(
        self,
        stock_code: str,
        buy_plan: Dict[str, Any]
    ):
        """
        매수 계획 추가

        Args:
            stock_code: 종목 코드
            buy_plan: 매수 계획
        """
        with self._lock:
            # 사용자 설정 적용
            total_amount = min(
                buy_plan.get('total_amount', 0),
                self.user_settings['max_buy_amount']
            )

            split_orders = self.user_settings['split_orders']
            amount_per_order = total_amount / split_orders

            enhanced_plan = {
                'timestamp': datetime.now().isoformat(),
                'total_amount': total_amount,
                'entry_price': buy_plan.get('entry_price', 0),
                'split_orders': split_orders,
                'amount_per_order': amount_per_order,
                'target_price': buy_plan.get('target_price', 0),
                'stop_loss_price': buy_plan.get('stop_loss_price', 0),
                'take_profit_ratio': self.user_settings['take_profit_ratio'],
                'stop_loss_ratio': self.user_settings['stop_loss_ratio'],
                'status': 'pending',  # pending, executing, completed, cancelled
                'user_overridden': False
            }

            self.buy_plans[stock_code] = enhanced_plan

            # 메모리 관리: 최대 크기 초과시 오래된 항목 제거
            if len(self.buy_plans) > self._max_buy_plans:
                sorted_items = sorted(
                    self.buy_plans.items(),
                    key=lambda x: x[1].get('timestamp', ''),
                    reverse=True
                )
                self.buy_plans = dict(sorted_items[:self._max_buy_plans])

            # 후보 종목 업데이트
            for candidate in self.candidates:
                if candidate['stock_code'] == stock_code:
                    candidate['buy_plan_ready'] = True
                    break

    def cleanup_old_data(self, max_age_hours: int = 24):
        """
        오래된 데이터 정리 (메모리 관리)

        Args:
            max_age_hours: 최대 보관 시간 (시간 단위)
        """
        from datetime import timedelta

        with self._lock:
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            cutoff_str = cutoff.isoformat()

            # AI 분석 정리
            self.ai_analyses = {
                k: v for k, v in self.ai_analyses.items()
                if v.get('timestamp', '') > cutoff_str
            }

            # 매수 계획 정리 (완료/취소된 항목만)
            self.buy_plans = {
                k: v for k, v in self.buy_plans.items()
                if v.get('status') in ('pending', 'executing') or v.get('timestamp', '') > cutoff_str
            }

    def update_user_settings(self, settings: Dict[str, Any]):
        """
        사용자 설정 업데이트

        Args:
            settings: 설정 딕셔너리
        """
        with self._lock:
            self.user_settings.update(settings)
            self.log_activity(
                'settings',
                '사용자 설정 업데이트됨',
                {'settings': settings},
                'info'
            )

    def override_buy_plan(
        self,
        stock_code: str,
        overrides: Dict[str, Any]
    ):
        """
        매수 계획 수동 조정

        Args:
            stock_code: 종목 코드
            overrides: 조정할 값들
        """
        with self._lock:
            if stock_code in self.buy_plans:
                self.buy_plans[stock_code].update(overrides)
                self.buy_plans[stock_code]['user_overridden'] = True

                self.log_activity(
                    'override',
                    f'매수 계획 수동 조정: {stock_code}',
                    {'overrides': overrides},
                    'warning'
                )

    def get_recent_activities(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        최근 활동 로그 반환

        Args:
            limit: 반환할 최대 활동 수

        Returns:
            최근 활동 리스트
        """
        with self._lock:
            return list(self.activities)[-limit:]

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        대시보드용 데이터 반환

        Returns:
            실시간 데이터
        """
        with self._lock:
            return {
                'screening': self.current_screening,
                'activities': list(self.activities)[-50:],  # 최근 50개
                'candidates': self.candidates[:10],  # 상위 10개
                'ai_analyses': self.ai_analyses,
                'buy_plans': self.buy_plans,
                'user_settings': self.user_settings,
                'timestamp': datetime.now().isoformat()
            }

    def clear_candidates(self):
        """후보 종목 초기화"""
        with self._lock:
            self.candidates = []
            self.ai_analyses = {}
            self.buy_plans = {}

    def cancel_buy_plan(self, stock_code: str):
        """
        매수 계획 취소

        Args:
            stock_code: 종목 코드
        """
        with self._lock:
            if stock_code in self.buy_plans:
                self.buy_plans[stock_code]['status'] = 'cancelled'

                self.log_activity(
                    'cancel',
                    f'매수 계획 취소: {stock_code}',
                    {'stock_code': stock_code},
                    'warning'
                )


# 싱글톤 인스턴스
_monitor_instance = None


def get_monitor() -> TradingActivityMonitor:
    """활동 모니터 싱글톤 인스턴스 반환"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = TradingActivityMonitor()
    return _monitor_instance
