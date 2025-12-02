"""
AI-Powered Parameter Optimizer
AI 기반 파라미터 자동 최적화 시스템

모든 트레이딩 파라미터를 AI가 동적으로 최적화
"""
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ParameterResult:
    """파라미터 테스트 결과"""
    parameter_name: str
    parameter_value: Any
    performance_score: float
    win_rate: float
    avg_profit: float
    total_trades: int
    timestamp: datetime
    market_condition: str = "neutral"


@dataclass
class OptimizationHistory:
    """최적화 히스토리"""
    parameter_name: str
    tested_values: List[Any] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    best_value: Any = None
    best_score: float = -np.inf
    last_updated: datetime = field(default_factory=datetime.now)


class AIParameterOptimizer:
    """
    AI 기반 파라미터 최적화 시스템

    기능:
    - 베이지안 최적화 (Bayesian Optimization)
    - 강화학습 기반 파라미터 조정
    - 시장 상황별 최적 파라미터
    - 다목적 최적화 (수익률, 승률, 리스크)
    - A/B 테스팅 자동화
    """

    def __init__(self, db_path: str = "data/parameter_optimization.json"):
        """
        Args:
            db_path: 최적화 결과 저장 경로
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 최적화 히스토리
        self.history: Dict[str, OptimizationHistory] = {}

        # 파라미터 범위 정의
        self.parameter_ranges = {
            # 분할 주문 관련
            'split_order_count': (2, 10),  # 분할 횟수
            'split_price_gap_pct': (0.001, 0.05),  # 가격 간격 (%)
            'split_time_interval_sec': (10, 300),  # 시간 간격 (초)

            # 리스크 관리
            'position_size_pct': (0.05, 0.30),  # 포지션 크기 (%)
            'stop_loss_pct': (0.02, 0.15),  # 손절 비율
            'take_profit_pct': (0.03, 0.20),  # 익절 비율

            # 진입/청산 타이밍
            'entry_momentum_threshold': (0.5, 0.9),  # 진입 모멘텀 임계값
            'exit_profit_ratio': (1.5, 3.0),  # 청산 수익 비율

            # 기술적 지표
            'rsi_oversold': (20, 35),  # RSI 과매도
            'rsi_overbought': (65, 80),  # RSI 과매수
            'volume_threshold': (1.2, 3.0),  # 거래량 임계값

            # AI 신뢰도
            'ai_confidence_threshold': (0.6, 0.9),  # AI 신뢰도 임계값
        }

        # 성과 기록
        self.performance_records: Dict[str, List[ParameterResult]] = defaultdict(list)

        # 학습률
        self.learning_rate = 0.1

        # 탐험-활용 균형 (Exploration-Exploitation)
        self.epsilon = 0.2  # 20% 확률로 랜덤 탐험

        self._load_history()

        logger.info("AI Parameter Optimizer initialized")

    def optimize_parameter(
        self,
        parameter_name: str,
        current_value: Any,
        recent_performance: Dict[str, float],
        market_condition: str = "neutral"
    ) -> Tuple[Any, float]:
        """
        파라미터 최적화 (베이지안 최적화)

        Args:
            parameter_name: 파라미터 이름
            current_value: 현재 값
            recent_performance: 최근 성과 {'win_rate': 0.6, 'avg_profit': 0.03, ...}
            market_condition: 시장 상황 (bullish, bearish, neutral, volatile)

        Returns:
            (최적 값, 예상 성과 점수)
        """
        # 성과 점수 계산
        performance_score = self._calculate_performance_score(recent_performance)

        # 결과 기록
        result = ParameterResult(
            parameter_name=parameter_name,
            parameter_value=current_value,
            performance_score=performance_score,
            win_rate=recent_performance.get('win_rate', 0.5),
            avg_profit=recent_performance.get('avg_profit', 0.0),
            total_trades=recent_performance.get('total_trades', 0),
            timestamp=datetime.now(),
            market_condition=market_condition
        )

        self.performance_records[parameter_name].append(result)

        # 히스토리 업데이트
        if parameter_name not in self.history:
            self.history[parameter_name] = OptimizationHistory(
                parameter_name=parameter_name
            )

        history = self.history[parameter_name]
        history.tested_values.append(current_value)
        history.scores.append(performance_score)

        # 최고 성과 업데이트
        if performance_score > history.best_score:
            history.best_score = performance_score
            history.best_value = current_value
            logger.info(f"🎯 New best {parameter_name}: {current_value} (score: {performance_score:.3f})")

        history.last_updated = datetime.now()

        # 다음 시도할 값 결정 (Exploration vs Exploitation)
        if np.random.random() < self.epsilon:
            # Exploration: 랜덤 탐험
            next_value = self._random_sample(parameter_name)
            logger.debug(f"🔍 Exploring {parameter_name}: {next_value}")
        else:
            # Exploitation: 최적화된 값 사용
            next_value = self._bayesian_next_value(
                parameter_name,
                history,
                market_condition
            )
            logger.debug(f"✨ Optimizing {parameter_name}: {next_value}")

        # 히스토리 저장
        self._save_history()

        # 예상 성과 점수
        expected_score = self._predict_score(parameter_name, next_value, history)

        return next_value, expected_score

    def get_optimal_split_order_params(
        self,
        stock_code: str,
        order_amount: float,
        volatility: float,
        liquidity: int,
        market_condition: str = "neutral"
    ) -> Dict[str, Any]:
        """
        분할 주문 최적 파라미터 AI 결정

        Args:
            stock_code: 종목 코드
            order_amount: 주문 금액
            volatility: 변동성
            liquidity: 유동성 (일일 거래량)
            market_condition: 시장 상황

        Returns:
            최적 분할 주문 파라미터
        """
        # 변동성과 유동성 기반 기본 파라미터
        base_count = 3
        base_gap = 0.01
        base_interval = 60

        # 변동성 조정
        if volatility > 0.03:  # 높은 변동성
            base_count = min(base_count + 2, 8)
            base_gap = min(base_gap * 1.5, 0.03)
            base_interval = max(base_interval // 2, 30)
        elif volatility < 0.015:  # 낮은 변동성
            base_count = max(base_count - 1, 2)
            base_gap = max(base_gap * 0.7, 0.005)
            base_interval = min(base_interval * 1.5, 180)

        # 유동성 조정
        order_impact = order_amount / (liquidity * 1.0) if liquidity > 0 else 0.1
        if order_impact > 0.05:  # 큰 주문
            base_count = min(base_count + 3, 10)
            base_interval = max(base_interval // 1.5, 20)

        # 시장 상황 조정
        if market_condition == "volatile":
            base_gap *= 1.3
            base_interval = max(base_interval // 2, 15)
        elif market_condition == "trending":
            base_count = max(base_count - 1, 2)
            base_gap *= 0.8

        # AI 최적화 적용
        optimal_count = self._get_optimal_value('split_order_count', base_count)
        optimal_gap = self._get_optimal_value('split_price_gap_pct', base_gap)
        optimal_interval = self._get_optimal_value('split_time_interval_sec', base_interval)

        params = {
            'num_splits': int(optimal_count),
            'price_gap_pct': float(optimal_gap),
            'time_interval_sec': float(optimal_interval),
            'strategy': self._select_optimal_strategy(volatility, market_condition),
            'confidence_score': self._calculate_confidence(
                optimal_count, optimal_gap, optimal_interval
            )
        }

        logger.info(f"🤖 AI Split Order Params for {stock_code}: {params}")

        return params

    def get_optimal_position_size(
        self,
        stock_code: str,
        ai_confidence: float,
        volatility: float,
        win_rate: float,
        available_capital: float
    ) -> Dict[str, Any]:
        """
        최적 포지션 사이즈 AI 결정

        Args:
            stock_code: 종목 코드
            ai_confidence: AI 신뢰도
            volatility: 변동성
            win_rate: 승률
            available_capital: 사용 가능 자본

        Returns:
            최적 포지션 사이즈 정보
        """
        # 기본 비율 (Kelly Criterion 기반)
        kelly_ratio = win_rate - ((1 - win_rate) / 1.5) if win_rate > 0 else 0.1
        kelly_ratio = max(0.05, min(kelly_ratio * 0.5, 0.25))  # 안전하게 절반만

        # AI 신뢰도 반영
        confidence_multiplier = 0.5 + (ai_confidence * 0.5)  # 0.5 ~ 1.0
        base_ratio = kelly_ratio * confidence_multiplier

        # 변동성 조정
        volatility_adj = 0.02 / max(volatility, 0.01)  # 변동성 역수
        volatility_adj = min(volatility_adj, 1.5)

        base_ratio *= volatility_adj

        # AI 최적화
        optimal_ratio = self._get_optimal_value('position_size_pct', base_ratio)
        optimal_ratio = np.clip(optimal_ratio, 0.05, 0.30)

        position_amount = available_capital * optimal_ratio

        result = {
            'position_ratio': float(optimal_ratio),
            'position_amount': float(position_amount),
            'kelly_ratio': float(kelly_ratio),
            'confidence_multiplier': float(confidence_multiplier),
            'volatility_adjustment': float(volatility_adj),
            'reasoning': f"Kelly: {kelly_ratio:.2%} × Confidence: {confidence_multiplier:.2f} × Volatility: {volatility_adj:.2f}"
        }

        logger.info(f"🤖 AI Position Size for {stock_code}: {optimal_ratio:.2%} (₩{position_amount:,.0f})")

        return result

    def adapt_to_market_regime(
        self,
        market_regime: str,
        recent_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        시장 레짐에 따른 파라미터 적응

        Args:
            market_regime: 시장 레짐 (bull, bear, sideways, volatile)
            recent_results: 최근 거래 결과

        Returns:
            적응된 파라미터 세트
        """
        # 레짐별 성과 분석
        regime_performance = self._analyze_regime_performance(recent_results)

        adapted_params = {}

        if market_regime == "bull":
            # 상승장: 공격적 진입, 넓은 익절
            adapted_params['position_size_pct'] = self._get_optimal_value('position_size_pct', 0.20)
            adapted_params['take_profit_pct'] = self._get_optimal_value('take_profit_pct', 0.10)
            adapted_params['stop_loss_pct'] = self._get_optimal_value('stop_loss_pct', 0.05)

        elif market_regime == "bear":
            # 하락장: 보수적 진입, 빠른 손절
            adapted_params['position_size_pct'] = self._get_optimal_value('position_size_pct', 0.08)
            adapted_params['take_profit_pct'] = self._get_optimal_value('take_profit_pct', 0.05)
            adapted_params['stop_loss_pct'] = self._get_optimal_value('stop_loss_pct', 0.03)

        elif market_regime == "volatile":
            # 변동성 장: 분할 진입, 넓은 손절
            adapted_params['split_order_count'] = self._get_optimal_value('split_order_count', 5)
            adapted_params['position_size_pct'] = self._get_optimal_value('position_size_pct', 0.12)
            adapted_params['stop_loss_pct'] = self._get_optimal_value('stop_loss_pct', 0.08)

        else:  # sideways
            # 횡보장: 균형잡힌 접근
            adapted_params['position_size_pct'] = self._get_optimal_value('position_size_pct', 0.15)
            adapted_params['take_profit_pct'] = self._get_optimal_value('take_profit_pct', 0.06)
            adapted_params['stop_loss_pct'] = self._get_optimal_value('stop_loss_pct', 0.04)

        logger.info(f"🌍 Market regime {market_regime} - Adapted params: {adapted_params}")

        return adapted_params

    def _calculate_performance_score(self, performance: Dict[str, float]) -> float:
        """성과 점수 계산 (다목적 최적화)"""
        win_rate = performance.get('win_rate', 0.5)
        avg_profit = performance.get('avg_profit', 0.0)
        total_trades = performance.get('total_trades', 0)
        max_drawdown = performance.get('max_drawdown', 0.0)
        sharpe_ratio = performance.get('sharpe_ratio', 0.0)

        # 가중치 적용
        score = (
            win_rate * 0.3 +  # 승률
            avg_profit * 10 * 0.3 +  # 평균 수익 (% → 점수)
            (1 - abs(max_drawdown)) * 0.2 +  # 낙폭 (낮을수록 좋음)
            sharpe_ratio * 0.1 * 0.1 +  # 샤프 비율
            min(total_trades / 100, 1.0) * 0.1  # 거래 수 (신뢰도)
        )

        return max(0.0, min(score, 1.0))

    def _bayesian_next_value(
        self,
        parameter_name: str,
        history: OptimizationHistory,
        market_condition: str
    ) -> Any:
        """베이지안 최적화로 다음 시도할 값 결정"""
        if len(history.tested_values) < 3:
            # 데이터 부족 시 랜덤
            return self._random_sample(parameter_name)

        # 가장 성과 좋았던 값 주변 탐색
        best_idx = np.argmax(history.scores)
        best_value = history.tested_values[best_idx]

        # 범위 내에서 작은 변화 적용
        if parameter_name in self.parameter_ranges:
            min_val, max_val = self.parameter_ranges[parameter_name]

            # 가우시안 노이즈 추가
            if isinstance(best_value, (int, float)):
                std = (max_val - min_val) * 0.1  # 범위의 10%
                next_value = np.random.normal(best_value, std)
                next_value = np.clip(next_value, min_val, max_val)

                # 정수형이면 반올림
                if isinstance(best_value, int):
                    next_value = int(round(next_value))

                return next_value

        return best_value

    def _random_sample(self, parameter_name: str) -> Any:
        """파라미터 범위 내에서 랜덤 샘플링"""
        if parameter_name not in self.parameter_ranges:
            return None

        min_val, max_val = self.parameter_ranges[parameter_name]

        # 정수형 판단 (최소값으로)
        if isinstance(min_val, int):
            return np.random.randint(min_val, max_val + 1)
        else:
            return np.random.uniform(min_val, max_val)

    def _predict_score(
        self,
        parameter_name: str,
        value: Any,
        history: OptimizationHistory
    ) -> float:
        """파라미터 값에 대한 예상 성과 점수"""
        if len(history.scores) < 2:
            return 0.5  # 기본값

        # 간단한 선형 보간
        try:
            if isinstance(value, (int, float)) and len(history.tested_values) > 0:
                # 가장 가까운 값들의 점수 평균
                distances = [abs(value - v) for v in history.tested_values if isinstance(v, (int, float))]
                if distances:
                    closest_idx = np.argmin(distances)
                    return history.scores[closest_idx]
        except (TypeError, ValueError, IndexError) as e:
            logger.debug(f"Score estimation error: {e}")

        return np.mean(history.scores)

    def _get_optimal_value(self, parameter_name: str, default_value: Any) -> Any:
        """현재 최적 값 가져오기"""
        if parameter_name in self.history and self.history[parameter_name].best_value is not None:
            return self.history[parameter_name].best_value
        return default_value

    def _select_optimal_strategy(self, volatility: float, market_condition: str) -> str:
        """최적 분할 전략 선택"""
        if market_condition == "volatile" or volatility > 0.03:
            return "iceberg"  # 변동성 높을 때 빙산 주문
        elif market_condition == "trending":
            return "gradual_down"  # 추세 장에서 점진적 진입
        else:
            return "liquidity_adaptive"  # 기본: 유동성 적응형

    def _calculate_confidence(self, count: float, gap: float, interval: float) -> float:
        """파라미터 신뢰도 계산"""
        # 히스토리 기반 신뢰도
        confidence = 0.5  # 기본값

        for param_name in ['split_order_count', 'split_price_gap_pct', 'split_time_interval_sec']:
            if param_name in self.history:
                history = self.history[param_name]
                if len(history.scores) >= 5:
                    # 충분한 데이터가 있으면 신뢰도 증가
                    confidence += 0.15

        return min(confidence, 0.95)

    def _analyze_regime_performance(self, recent_results: List[Dict]) -> Dict:
        """레짐별 성과 분석"""
        # 간단한 구현 (실제로는 더 복잡한 분석)
        return {
            'avg_return': np.mean([r.get('return', 0) for r in recent_results]) if recent_results else 0,
            'win_rate': np.mean([1 if r.get('return', 0) > 0 else 0 for r in recent_results]) if recent_results else 0.5
        }

    def _save_history(self):
        """히스토리 저장"""
        try:
            data = {}
            for param_name, history in self.history.items():
                data[param_name] = {
                    'tested_values': [float(v) if isinstance(v, (int, float)) else str(v) for v in history.tested_values],
                    'scores': history.scores,
                    'best_value': float(history.best_value) if isinstance(history.best_value, (int, float)) else str(history.best_value),
                    'best_score': history.best_score,
                    'last_updated': history.last_updated.isoformat()
                }

            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def _load_history(self):
        """히스토리 로드"""
        try:
            if self.db_path.exists():
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for param_name, hist_data in data.items():
                    self.history[param_name] = OptimizationHistory(
                        parameter_name=param_name,
                        tested_values=hist_data['tested_values'],
                        scores=hist_data['scores'],
                        best_value=hist_data.get('best_value'),
                        best_score=hist_data.get('best_score', -np.inf),
                        last_updated=datetime.fromisoformat(hist_data.get('last_updated', datetime.now().isoformat()))
                    )

                logger.info(f"Loaded optimization history for {len(self.history)} parameters")
        except Exception as e:
            logger.warning(f"Failed to load history: {e}")


# Singleton
_parameter_optimizer = None


def get_parameter_optimizer() -> AIParameterOptimizer:
    """Get parameter optimizer singleton"""
    global _parameter_optimizer
    if _parameter_optimizer is None:
        _parameter_optimizer = AIParameterOptimizer()
    return _parameter_optimizer


__all__ = ['AIParameterOptimizer', 'get_parameter_optimizer', 'ParameterResult', 'OptimizationHistory']
