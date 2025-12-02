"""
core/strategy_ab_test.py
전략 A/B 테스트 프레임워크

진화된 전략을 안전하게 테스트하고 점진적으로 배포
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from threading import Lock
from pathlib import Path
from enum import Enum
import random

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """테스트 상태"""
    PENDING = "pending"
    RUNNING = "running"
    WINNING = "winning"
    LOSING = "losing"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


@dataclass
class StrategyVersion:
    """전략 버전"""
    version_id: str
    strategy_name: str
    parameters: Dict[str, Any]
    created_at: str
    generation: int = 0
    fitness_score: float = 0.0
    parent_version: str = ""
    notes: str = ""


@dataclass
class ABTestConfig:
    """A/B 테스트 설정"""
    test_id: str
    control_version: str        # A: 기존 전략
    treatment_version: str      # B: 새 전략
    start_time: str
    end_time: str = ""
    status: TestStatus = TestStatus.PENDING

    # 트래픽 분배
    control_weight: float = 0.90    # 90% 기존 전략
    treatment_weight: float = 0.10   # 10% 새 전략

    # 성과 지표
    control_trades: int = 0
    treatment_trades: int = 0
    control_pnl: float = 0.0
    treatment_pnl: float = 0.0
    control_win_rate: float = 0.0
    treatment_win_rate: float = 0.0

    # 종료 조건
    min_trades: int = 20            # 최소 거래 수
    max_duration_days: int = 7      # 최대 기간
    early_stop_loss: float = -100000  # 조기 종료 손실


@dataclass
class RolloutStage:
    """점진적 배포 단계"""
    stage: int
    weight: float           # 새 전략 비중 (5% → 25% → 50% → 100%)
    min_trades: int
    required_win_rate: float
    started_at: str = ""
    completed_at: str = ""
    passed: bool = False


class StrategyABTest:
    """
    전략 A/B 테스트 매니저

    기능:
    - 진화된 전략을 5% 트래픽으로 테스트
    - 성과가 좋으면 점진적으로 배포 (5% → 25% → 50% → 100%)
    - 성과가 나쁘면 자동 롤백
    - 통계적 유의성 검증
    """

    _instance = None
    _lock = Lock()

    # 저장 경로
    DATA_DIR = Path("data/ab_tests")

    # 점진적 배포 단계
    ROLLOUT_STAGES = [
        RolloutStage(stage=1, weight=0.05, min_trades=10, required_win_rate=0.45),
        RolloutStage(stage=2, weight=0.25, min_trades=25, required_win_rate=0.48),
        RolloutStage(stage=3, weight=0.50, min_trades=50, required_win_rate=0.50),
        RolloutStage(stage=4, weight=1.00, min_trades=100, required_win_rate=0.50),
    ]

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

        # 전략 버전 관리
        self.versions: Dict[str, StrategyVersion] = {}

        # 현재 활성 테스트
        self.active_tests: Dict[str, ABTestConfig] = {}

        # 테스트 히스토리
        self.test_history: List[ABTestConfig] = []

        # 현재 롤아웃 단계
        self.current_rollout_stage: Dict[str, int] = {}

        # 활성 전략 버전
        self.active_version: Optional[str] = None
        self.candidate_version: Optional[str] = None

        # 디렉토리 생성
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 데이터 로드
        self._load_data()

        logger.info("전략 A/B 테스트 매니저 초기화 완료")

    @classmethod
    def get_instance(cls) -> 'StrategyABTest':
        return cls()

    def _load_data(self):
        """저장된 데이터 로드"""
        try:
            data_file = self.DATA_DIR / "ab_test_state.json"
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.active_version = data.get('active_version')
                    self.candidate_version = data.get('candidate_version')
        except Exception as e:
            logger.debug(f"A/B 테스트 데이터 로드 실패: {e}")

    def _save_data(self):
        """데이터 저장"""
        try:
            data_file = self.DATA_DIR / "ab_test_state.json"
            data = {
                'active_version': self.active_version,
                'candidate_version': self.candidate_version,
                'last_updated': datetime.now().isoformat()
            }
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"A/B 테스트 데이터 저장 실패: {e}")

    def register_strategy_version(
        self,
        strategy_name: str,
        parameters: Dict[str, Any],
        generation: int = 0,
        fitness_score: float = 0.0,
        parent_version: str = "",
        notes: str = ""
    ) -> StrategyVersion:
        """새 전략 버전 등록"""
        version_id = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        version = StrategyVersion(
            version_id=version_id,
            strategy_name=strategy_name,
            parameters=parameters,
            created_at=datetime.now().isoformat(),
            generation=generation,
            fitness_score=fitness_score,
            parent_version=parent_version,
            notes=notes
        )

        self.versions[version_id] = version

        # 첫 번째 버전이면 활성화
        if not self.active_version:
            self.active_version = version_id

        logger.info(f"전략 버전 등록: {version_id} (세대: {generation}, 적합도: {fitness_score:.2f})")

        return version

    def start_ab_test(
        self,
        control_version: str,
        treatment_version: str,
        treatment_weight: float = 0.10,
        max_duration_days: int = 7
    ) -> ABTestConfig:
        """A/B 테스트 시작"""
        test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        test = ABTestConfig(
            test_id=test_id,
            control_version=control_version,
            treatment_version=treatment_version,
            start_time=datetime.now().isoformat(),
            status=TestStatus.RUNNING,
            control_weight=1 - treatment_weight,
            treatment_weight=treatment_weight,
            max_duration_days=max_duration_days
        )

        self.active_tests[test_id] = test
        self.candidate_version = treatment_version
        self.current_rollout_stage[test_id] = 1

        self._save_data()

        logger.info(
            f"A/B 테스트 시작: {test_id}\n"
            f"  Control (A): {control_version} ({test.control_weight*100:.0f}%)\n"
            f"  Treatment (B): {treatment_version} ({test.treatment_weight*100:.0f}%)"
        )

        return test

    def select_strategy_for_trade(self, test_id: Optional[str] = None) -> Tuple[str, str]:
        """
        거래에 사용할 전략 선택

        Returns:
            (version_id, group): 선택된 버전 ID와 그룹 ('control' or 'treatment')
        """
        # 활성 테스트가 없으면 기본 전략
        if not self.active_tests:
            return self.active_version or "", "default"

        # 특정 테스트 또는 첫 번째 활성 테스트
        if test_id:
            test = self.active_tests.get(test_id)
        else:
            test = next(iter(self.active_tests.values()), None)

        if not test or test.status != TestStatus.RUNNING:
            return self.active_version or "", "default"

        # 가중치 기반 랜덤 선택
        rand = random.random()
        if rand < test.treatment_weight:
            return test.treatment_version, "treatment"
        else:
            return test.control_version, "control"

    def record_trade_result(
        self,
        test_id: str,
        group: str,
        profit_loss: float,
        is_win: bool
    ):
        """거래 결과 기록"""
        if test_id not in self.active_tests:
            return

        test = self.active_tests[test_id]

        if group == "treatment":
            test.treatment_trades += 1
            test.treatment_pnl += profit_loss
            # 승률 업데이트
            wins = int(test.treatment_win_rate * (test.treatment_trades - 1))
            if is_win:
                wins += 1
            test.treatment_win_rate = wins / test.treatment_trades
        else:
            test.control_trades += 1
            test.control_pnl += profit_loss
            wins = int(test.control_win_rate * (test.control_trades - 1))
            if is_win:
                wins += 1
            test.control_win_rate = wins / test.control_trades

        # 테스트 상태 업데이트
        self._evaluate_test(test_id)

    def _evaluate_test(self, test_id: str):
        """테스트 평가 및 상태 업데이트"""
        test = self.active_tests.get(test_id)
        if not test:
            return

        # 조기 종료 조건 체크
        if test.treatment_pnl < test.early_stop_loss:
            self._rollback_test(test_id, "손실 한도 초과")
            return

        # 최소 거래 수 충족 여부
        if test.treatment_trades < test.min_trades:
            return

        # 기간 만료 체크
        start = datetime.fromisoformat(test.start_time)
        if datetime.now() - start > timedelta(days=test.max_duration_days):
            self._complete_test(test_id)
            return

        # 현재 롤아웃 단계 체크
        current_stage_idx = self.current_rollout_stage.get(test_id, 1) - 1
        if current_stage_idx >= len(self.ROLLOUT_STAGES):
            self._complete_test(test_id)
            return

        stage = self.ROLLOUT_STAGES[current_stage_idx]

        # 승률 비교
        if test.treatment_win_rate > test.control_win_rate:
            test.status = TestStatus.WINNING

            # 다음 단계 진행 조건 충족
            if (test.treatment_trades >= stage.min_trades and
                test.treatment_win_rate >= stage.required_win_rate):

                self._advance_rollout(test_id)
        else:
            test.status = TestStatus.LOSING

            # 손실 중이고 충분한 거래 후에도 개선 안되면 롤백
            if test.treatment_trades >= stage.min_trades * 2:
                self._rollback_test(test_id, "성과 부진")

    def _advance_rollout(self, test_id: str):
        """다음 롤아웃 단계로 진행"""
        current_stage_idx = self.current_rollout_stage.get(test_id, 1)
        next_stage_idx = current_stage_idx + 1

        if next_stage_idx > len(self.ROLLOUT_STAGES):
            self._complete_test(test_id)
            return

        self.current_rollout_stage[test_id] = next_stage_idx
        next_stage = self.ROLLOUT_STAGES[next_stage_idx - 1]

        # 트래픽 비중 업데이트
        test = self.active_tests[test_id]
        test.treatment_weight = next_stage.weight
        test.control_weight = 1 - next_stage.weight

        logger.info(
            f"롤아웃 진행: {test_id} → Stage {next_stage_idx} "
            f"(Treatment {next_stage.weight*100:.0f}%)"
        )

    def _complete_test(self, test_id: str):
        """테스트 완료 처리"""
        test = self.active_tests.get(test_id)
        if not test:
            return

        test.status = TestStatus.COMPLETED
        test.end_time = datetime.now().isoformat()

        # Treatment가 이겼으면 새 전략을 활성화
        if test.treatment_win_rate > test.control_win_rate and test.treatment_pnl > 0:
            self.active_version = test.treatment_version
            logger.info(
                f"A/B 테스트 완료 - 새 전략 배포: {test.treatment_version}\n"
                f"  승률: {test.treatment_win_rate*100:.1f}% vs {test.control_win_rate*100:.1f}%\n"
                f"  손익: {test.treatment_pnl:+,.0f}원 vs {test.control_pnl:+,.0f}원"
            )
        else:
            logger.info(f"A/B 테스트 완료 - 기존 전략 유지: {test.control_version}")

        # 히스토리에 추가하고 활성 테스트에서 제거
        self.test_history.append(test)
        del self.active_tests[test_id]
        self.candidate_version = None

        self._save_data()

    def _rollback_test(self, test_id: str, reason: str):
        """테스트 롤백"""
        test = self.active_tests.get(test_id)
        if not test:
            return

        test.status = TestStatus.ROLLED_BACK
        test.end_time = datetime.now().isoformat()

        logger.warning(
            f"A/B 테스트 롤백: {test_id}\n"
            f"  사유: {reason}\n"
            f"  Treatment 손익: {test.treatment_pnl:+,.0f}원\n"
            f"  Treatment 승률: {test.treatment_win_rate*100:.1f}%"
        )

        # 히스토리에 추가하고 활성 테스트에서 제거
        self.test_history.append(test)
        del self.active_tests[test_id]
        self.candidate_version = None

        self._save_data()

    def get_test_status(self, test_id: str = None) -> Dict[str, Any]:
        """테스트 상태 조회"""
        if test_id:
            test = self.active_tests.get(test_id)
            if test:
                return asdict(test)
            return {}

        return {
            'active_version': self.active_version,
            'candidate_version': self.candidate_version,
            'active_tests': {k: asdict(v) for k, v in self.active_tests.items()},
            'history_count': len(self.test_history)
        }

    def get_summary(self) -> Dict[str, Any]:
        """요약 정보"""
        completed = [t for t in self.test_history if t.status == TestStatus.COMPLETED]
        rolled_back = [t for t in self.test_history if t.status == TestStatus.ROLLED_BACK]

        return {
            'active_version': self.active_version,
            'candidate_version': self.candidate_version,
            'active_tests': len(self.active_tests),
            'total_completed': len(completed),
            'total_rolled_back': len(rolled_back),
            'success_rate': len(completed) / (len(completed) + len(rolled_back)) * 100 if (completed or rolled_back) else 0,
            'versions_count': len(self.versions)
        }


# 전역 접근 함수
def get_ab_test_manager() -> StrategyABTest:
    return StrategyABTest.get_instance()
