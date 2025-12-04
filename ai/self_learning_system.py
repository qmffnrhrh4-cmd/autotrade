"""
Self-Learning Reinforcement System
자기 강화 학습 시스템

모든 거래에서 학습하여 전략을 지속적으로 개선
"""
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TradeExperience:
    """거래 경험 (강화학습의 경험)"""
    trade_id: str
    timestamp: datetime
    stock_code: str
    stock_name: str

    # 상태 (State)
    state: Dict[str, Any]  # 진입 시 시장 상태

    # 행동 (Action)
    action: Dict[str, Any]  # 취한 행동 (파라미터)

    # 보상 (Reward)
    reward: float  # 수익률

    # 다음 상태 (Next State)
    next_state: Optional[Dict[str, Any]] = None

    # 메타데이터
    duration_hours: float = 0.0
    max_drawdown: float = 0.0
    is_win: bool = False


@dataclass
class LearningStats:
    """학습 통계"""
    total_experiences: int = 0
    total_wins: int = 0
    total_losses: int = 0
    avg_reward: float = 0.0
    best_reward: float = -np.inf
    worst_reward: float = np.inf
    learning_episodes: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


class SelfLearningSystem:
    """
    자기 강화 학습 시스템

    기능:
    - Q-Learning 기반 전략 학습
    - 경험 리플레이 (Experience Replay)
    - 상태-행동 가치 학습
    - 패턴 인식 및 예측
    - 적응형 학습률
    """

    def __init__(
        self,
        db_path: str = "data/self_learning.json",
        memory_size: int = 10000,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95
    ):
        """
        Args:
            db_path: 학습 데이터 저장 경로
            memory_size: 경험 메모리 크기
            learning_rate: 학습률
            discount_factor: 할인 계수 (미래 보상)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 하이퍼파라미터
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = 0.3  # 탐험 비율
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.05

        # 경험 메모리 (Experience Replay)
        self.memory: deque = deque(maxlen=memory_size)

        # Q-테이블 (상태-행동 가치)
        self.q_table: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # 상태-행동 방문 횟수
        self.visit_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # 학습 통계
        self.stats = LearningStats()

        # 패턴 인식
        self.successful_patterns: List[Dict] = []
        self.failed_patterns: List[Dict] = []

        # 성과 추적
        self.recent_rewards = deque(maxlen=100)

        self._load_data()

        logger.info(f"Self-Learning System initialized - Memory: {memory_size}, LR: {learning_rate}")

    def record_trade_experience(
        self,
        trade_id: str,
        stock_code: str,
        stock_name: str,
        entry_state: Dict[str, Any],
        action_params: Dict[str, Any],
        result: Dict[str, Any]
    ) -> float:
        """
        거래 경험 기록 및 학습

        Args:
            trade_id: 거래 ID
            stock_code: 종목 코드
            stock_name: 종목명
            entry_state: 진입 시 상태
            action_params: 행동 파라미터
            result: 거래 결과

        Returns:
            학습된 Q-값
        """
        # 보상 계산
        reward = self._calculate_reward(result)

        # 경험 생성
        experience = TradeExperience(
            trade_id=trade_id,
            timestamp=datetime.now(),
            stock_code=stock_code,
            stock_name=stock_name,
            state=entry_state,
            action=action_params,
            reward=reward,
            next_state=result.get('exit_state'),
            duration_hours=result.get('duration_hours', 0),
            max_drawdown=result.get('max_drawdown', 0),
            is_win=reward > 0
        )

        # 메모리에 저장
        self.memory.append(experience)

        # 통계 업데이트
        self._update_stats(experience)

        # Q-Learning 업데이트
        q_value = self._update_q_table(experience)

        # 패턴 학습
        self._learn_pattern(experience)

        # 주기적 저장 (100개마다)
        if len(self.memory) % 100 == 0:
            self._save_data()

        # Epsilon 감소 (탐험 → 활용)
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        logger.info(
            f"📚 Learned from trade {trade_id}: "
            f"Reward={reward:.3f}, Q-value={q_value:.3f}, "
            f"Win={experience.is_win}"
        )

        return q_value

    def suggest_action(
        self,
        current_state: Dict[str, Any],
        available_actions: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], float]:
        """
        현재 상태에서 최적 행동 추천

        Args:
            current_state: 현재 상태
            available_actions: 가능한 행동들

        Returns:
            (추천 행동, 예상 Q-값)
        """
        state_key = self._state_to_key(current_state)

        # Epsilon-Greedy 전략
        if np.random.random() < self.epsilon:
            # 탐험: 랜덤 선택
            action = np.random.choice(available_actions)
            q_value = self.q_table[state_key].get(self._action_to_key(action), 0.0)
            logger.debug(f"🔍 Exploration: Random action selected")
        else:
            # 활용: 최고 Q-값 행동 선택
            best_action = None
            best_q_value = -np.inf

            for action in available_actions:
                action_key = self._action_to_key(action)
                q_value = self.q_table[state_key].get(action_key, 0.0)

                if q_value > best_q_value:
                    best_q_value = q_value
                    best_action = action

            if best_action is None:
                best_action = available_actions[0] if available_actions else {}
                best_q_value = 0.0

            action = best_action
            q_value = best_q_value
            logger.debug(f"✨ Exploitation: Best action selected (Q={q_value:.3f})")

        return action, q_value

    def get_learned_insights(self) -> Dict[str, Any]:
        """학습된 인사이트 조회"""
        # 가장 성공적인 패턴
        top_patterns = sorted(
            self.successful_patterns,
            key=lambda p: p.get('avg_reward', 0),
            reverse=True
        )[:5]

        # 피해야 할 패턴
        worst_patterns = sorted(
            self.failed_patterns,
            key=lambda p: p.get('avg_reward', 0)
        )[:5]

        # 최근 성과
        recent_win_rate = (
            sum(1 for r in self.recent_rewards if r > 0) / len(self.recent_rewards)
            if self.recent_rewards else 0.5
        )

        # 가장 가치 있는 상태-행동
        top_q_values = []
        for state_key, actions in self.q_table.items():
            for action_key, q_value in actions.items():
                if q_value > 0.1:  # 의미 있는 값만
                    top_q_values.append({
                        'state': state_key,
                        'action': action_key,
                        'q_value': q_value,
                        'visit_count': self.visit_counts[state_key][action_key]
                    })

        top_q_values = sorted(top_q_values, key=lambda x: x['q_value'], reverse=True)[:10]

        insights = {
            'learning_stats': asdict(self.stats),
            'recent_win_rate': recent_win_rate,
            'avg_recent_reward': np.mean(self.recent_rewards) if self.recent_rewards else 0,
            'top_successful_patterns': top_patterns,
            'patterns_to_avoid': worst_patterns,
            'top_q_values': top_q_values,
            'exploration_rate': self.epsilon,
            'total_states_learned': len(self.q_table),
            'memory_usage': f"{len(self.memory)}/{self.memory.maxlen}"
        }

        return insights

    def get_adaptive_learning_rate(self) -> float:
        """적응형 학습률 계산"""
        # 최근 성과에 따라 학습률 조정
        if len(self.recent_rewards) < 10:
            return self.learning_rate

        recent_avg = np.mean(list(self.recent_rewards)[-20:])
        older_avg = np.mean(list(self.recent_rewards)[-40:-20]) if len(self.recent_rewards) >= 40 else recent_avg

        # 성과 개선 중이면 학습률 유지, 악화되면 증가
        if recent_avg > older_avg:
            # 개선 중: 현재 학습 유지
            return self.learning_rate * 0.95
        else:
            # 악화: 더 빠르게 학습
            return min(self.learning_rate * 1.1, 0.3)

    def batch_learn_from_memory(self, batch_size: int = 32) -> float:
        """
        메모리에서 배치 학습 (Experience Replay)

        Args:
            batch_size: 배치 크기

        Returns:
            평균 학습 오차
        """
        if len(self.memory) < batch_size:
            return 0.0

        # 랜덤 샘플링
        indices = np.random.choice(len(self.memory), batch_size, replace=False)
        batch = [self.memory[i] for i in indices]

        total_error = 0.0

        for experience in batch:
            # Q-Learning 업데이트
            error = self._update_q_table(experience)
            total_error += abs(error)

        avg_error = total_error / batch_size

        self.stats.learning_episodes += 1

        logger.info(f"📖 Batch learning completed: {batch_size} experiences, Avg error: {avg_error:.4f}")

        return avg_error

    def _calculate_reward(self, result: Dict[str, Any]) -> float:
        """
        보상 계산

        수익률, 리스크, 보유 기간 등을 고려한 종합 보상
        """
        profit_pct = result.get('profit_pct', 0.0)
        duration_hours = result.get('duration_hours', 24.0)
        max_drawdown = result.get('max_drawdown', 0.0)
        is_stopped = result.get('is_stopped', False)

        # 기본 보상: 수익률
        reward = profit_pct

        # 시간 가중 (빠른 수익 선호)
        if profit_pct > 0:
            time_bonus = max(0, 1.0 - (duration_hours / 168))  # 1주일 기준
            reward *= (1.0 + time_bonus * 0.5)

        # 낙폭 페널티
        if max_drawdown < 0:
            reward += max_drawdown * 0.5  # 낙폭의 절반만큼 감점

        # 손절 페널티 완화 (손절은 좋은 것)
        if is_stopped and profit_pct < 0:
            reward *= 0.7  # 손절 시 손실 30% 감소

        # 정규화 (-1 ~ 1 범위)
        reward = np.tanh(reward * 5)  # tanh로 범위 제한

        return reward

    def _update_q_table(self, experience: TradeExperience) -> float:
        """
        Q-테이블 업데이트 (Q-Learning)

        Q(s,a) = Q(s,a) + α * [R + γ * max(Q(s',a')) - Q(s,a)]
        """
        state_key = self._state_to_key(experience.state)
        action_key = self._action_to_key(experience.action)

        # 현재 Q-값
        current_q = self.q_table[state_key][action_key]

        # 다음 상태의 최대 Q-값
        if experience.next_state:
            next_state_key = self._state_to_key(experience.next_state)
            max_next_q = max(self.q_table[next_state_key].values()) if self.q_table[next_state_key] else 0.0
        else:
            max_next_q = 0.0

        # 적응형 학습률
        adaptive_lr = self.get_adaptive_learning_rate()

        # Q-Learning 업데이트
        td_target = experience.reward + self.discount_factor * max_next_q
        td_error = td_target - current_q
        new_q = current_q + adaptive_lr * td_error

        self.q_table[state_key][action_key] = new_q

        # 방문 횟수 증가
        self.visit_counts[state_key][action_key] += 1

        return td_error

    def _learn_pattern(self, experience: TradeExperience):
        """패턴 학습 (성공/실패 패턴 추출)"""
        pattern = {
            'state_features': self._extract_features(experience.state),
            'action_params': experience.action,
            'reward': experience.reward,
            'count': 1
        }

        if experience.is_win:
            # 성공 패턴
            self._add_to_patterns(pattern, self.successful_patterns)
        else:
            # 실패 패턴
            self._add_to_patterns(pattern, self.failed_patterns)

    def _add_to_patterns(self, new_pattern: Dict, pattern_list: List[Dict]):
        """패턴 목록에 추가 (유사 패턴 병합)"""
        # 유사 패턴 찾기
        for existing in pattern_list:
            if self._is_similar_pattern(new_pattern, existing):
                # 평균 업데이트
                total_count = existing['count'] + 1
                existing['avg_reward'] = (
                    existing.get('avg_reward', existing['reward']) * existing['count'] +
                    new_pattern['reward']
                ) / total_count
                existing['count'] = total_count
                return

        # 새 패턴 추가
        new_pattern['avg_reward'] = new_pattern['reward']
        pattern_list.append(new_pattern)

        # 최대 100개 유지 (Fix: pop(0) O(n) → 슬라이싱으로 변경)
        if len(pattern_list) > 100:
            del pattern_list[:-100]  # 오래된 항목 일괄 삭제

    def _is_similar_pattern(self, pattern1: Dict, pattern2: Dict) -> bool:
        """패턴 유사도 판단"""
        # 간단한 구현: 상태 특징 비교
        features1 = pattern1.get('state_features', {})
        features2 = pattern2.get('state_features', {})

        # 몇 개의 주요 특징만 비교
        key_features = ['volatility_level', 'trend', 'volume_level']
        matches = sum(1 for k in key_features if features1.get(k) == features2.get(k))

        return matches >= 2  # 3개 중 2개 이상 일치

    def _extract_features(self, state: Dict[str, Any]) -> Dict[str, str]:
        """상태에서 주요 특징 추출"""
        volatility = state.get('volatility', 0.02)
        trend = state.get('trend', 0.0)
        volume_ratio = state.get('volume_ratio', 1.0)

        return {
            'volatility_level': 'high' if volatility > 0.03 else 'medium' if volatility > 0.015 else 'low',
            'trend': 'up' if trend > 0.02 else 'down' if trend < -0.02 else 'neutral',
            'volume_level': 'high' if volume_ratio > 1.5 else 'normal' if volume_ratio > 0.8 else 'low'
        }

    def _state_to_key(self, state: Dict[str, Any]) -> str:
        """상태를 키로 변환 (이산화)"""
        features = self._extract_features(state)
        return f"{features['volatility_level']}_{features['trend']}_{features['volume_level']}"

    def _action_to_key(self, action: Dict[str, Any]) -> str:
        """행동을 키로 변환"""
        # 주요 파라미터만 사용
        position_size = action.get('position_size_pct', 0.1)
        stop_loss = action.get('stop_loss_pct', 0.05)

        pos_level = 'high' if position_size > 0.2 else 'medium' if position_size > 0.1 else 'low'
        sl_level = 'tight' if stop_loss < 0.04 else 'normal' if stop_loss < 0.08 else 'wide'

        return f"pos_{pos_level}_sl_{sl_level}"

    def _update_stats(self, experience: TradeExperience):
        """통계 업데이트"""
        self.stats.total_experiences += 1

        if experience.is_win:
            self.stats.total_wins += 1
        else:
            self.stats.total_losses += 1

        # 평균 보상 업데이트
        self.stats.avg_reward = (
            self.stats.avg_reward * (self.stats.total_experiences - 1) +
            experience.reward
        ) / self.stats.total_experiences

        # 최고/최악 보상
        self.stats.best_reward = max(self.stats.best_reward, experience.reward)
        self.stats.worst_reward = min(self.stats.worst_reward, experience.reward)

        self.stats.last_updated = datetime.now()

        # 최근 보상 추적
        self.recent_rewards.append(experience.reward)

    def _save_data(self):
        """학습 데이터 저장"""
        try:
            data = {
                'stats': asdict(self.stats),
                'q_table': {
                    state: dict(actions)
                    for state, actions in self.q_table.items()
                },
                'visit_counts': {
                    state: dict(actions)
                    for state, actions in self.visit_counts.items()
                },
                'successful_patterns': self.successful_patterns[:50],  # 상위 50개만
                'failed_patterns': self.failed_patterns[:50],
                'recent_rewards': list(self.recent_rewards),
                'epsilon': self.epsilon
            }

            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            logger.debug(f"Saved learning data: {len(self.q_table)} states")

        except Exception as e:
            logger.error(f"Failed to save learning data: {e}")

    def _load_data(self):
        """학습 데이터 로드"""
        try:
            if self.db_path.exists():
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 통계 복원
                stats_data = data.get('stats', {})
                if stats_data:
                    self.stats = LearningStats(**stats_data)

                # Q-테이블 복원
                q_table_data = data.get('q_table', {})
                for state, actions in q_table_data.items():
                    self.q_table[state] = defaultdict(float, actions)

                # 방문 횟수 복원
                visit_data = data.get('visit_counts', {})
                for state, actions in visit_data.items():
                    self.visit_counts[state] = defaultdict(int, actions)

                # 패턴 복원
                self.successful_patterns = data.get('successful_patterns', [])
                self.failed_patterns = data.get('failed_patterns', [])

                # 최근 보상 복원
                recent = data.get('recent_rewards', [])
                self.recent_rewards.extend(recent)

                # Epsilon 복원
                self.epsilon = data.get('epsilon', self.epsilon)

                logger.info(
                    f"Loaded learning data: {len(self.q_table)} states, "
                    f"{self.stats.total_experiences} experiences"
                )
        except Exception as e:
            logger.warning(f"Failed to load learning data: {e}")


# Singleton
_self_learning_system = None


def get_self_learning_system() -> SelfLearningSystem:
    """Get self-learning system singleton"""
    global _self_learning_system
    if _self_learning_system is None:
        _self_learning_system = SelfLearningSystem()
    return _self_learning_system


__all__ = ['SelfLearningSystem', 'get_self_learning_system', 'TradeExperience', 'LearningStats']
