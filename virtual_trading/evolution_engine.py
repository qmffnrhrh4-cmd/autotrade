"""
virtual_trading/evolution_engine.py
진화 알고리즘 기반 전략 최적화 엔진

YOLO처럼 계속 학습하고 진화하는 전략 시스템
- 유전 알고리즘 (Genetic Algorithm)
- 자연 선택 (Natural Selection)
- 돌연변이 (Mutation)
- 교배 (Crossover)
- 적합도 평가 (Fitness Function)
"""
import logging
import random
import copy
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class StrategyGene:
    """전략 유전자 (염색체)"""
    # 매수 조건
    rsi_min: float  # 30-50
    rsi_max: float  # 50-70
    volume_ratio_min: float  # 1.0-3.0
    bid_ask_ratio_min: float  # 1.0-2.0

    # 매도 조건
    take_profit_pct: float  # 5-20%
    stop_loss_pct: float  # 3-10%
    trailing_stop_pct: float  # 5-15%
    rsi_overbought_min: float  # 65-80
    rsi_overbought_max: float  # 80-95

    # 포지션 관리
    position_size_pct: float  # 5-30%
    max_positions: int  # 1-5

    # 시간 필터
    trade_start_hour: int  # 9-12
    trade_end_hour: int  # 14-20

    # 가격 범위
    price_min: int  # 1000-50000
    price_max: int  # 50000-500000

    # 분할 매수 설정
    split_buy_enabled: bool
    split_buy_count: int  # 2-5

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'rsi_min': self.rsi_min,
            'rsi_max': self.rsi_max,
            'volume_ratio_min': self.volume_ratio_min,
            'bid_ask_ratio_min': self.bid_ask_ratio_min,
            'take_profit_pct': self.take_profit_pct,
            'stop_loss_pct': self.stop_loss_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
            'rsi_overbought_min': self.rsi_overbought_min,
            'rsi_overbought_max': self.rsi_overbought_max,
            'position_size_pct': self.position_size_pct,
            'max_positions': self.max_positions,
            'trade_start_hour': self.trade_start_hour,
            'trade_end_hour': self.trade_end_hour,
            'price_min': self.price_min,
            'price_max': self.price_max,
            'split_buy_enabled': self.split_buy_enabled,
            'split_buy_count': self.split_buy_count
        }


@dataclass
class StrategyFitness:
    """전략 적합도 (성과 평가)"""
    strategy_id: int
    generation: int

    # 성과 지표
    return_rate: float  # 수익률
    sharpe_ratio: float  # 샤프 비율 (수익/위험)
    win_rate: float  # 승률
    max_drawdown: float  # 최대 낙폭 (MDD)
    profit_factor: float  # 손익비
    trade_count: int  # 거래 횟수

    # 적합도 점수 (0-100)
    fitness_score: float

    # 안전성 점수 (0-100)
    safety_score: float

    # 종합 점수 (fitness + safety)
    total_score: float


class StrategyEvolutionEngine:
    """
    전략 진화 엔진

    YOLO처럼 계속 학습하고 진화:
    1. 초기 모집단 생성 (20개 전략)
    2. 성과 평가 (적합도 함수)
    3. 선택 (상위 30%)
    4. 교배 (2개 조합 → 새 전략)
    5. 돌연변이 (10% 확률)
    6. 반복 (24시간)
    """

    def __init__(
        self,
        virtual_manager,
        data_fetcher,
        population_size: int = 20,
        elite_ratio: float = 0.3,
        mutation_rate: float = 0.1,
        initial_capital: float = 10000000
    ):
        """
        Args:
            virtual_manager: VirtualTradingManager
            data_fetcher: DataFetcher
            population_size: 모집단 크기 (동시 실행 전략 수)
            elite_ratio: 엘리트 비율 (상위 몇 %를 선택할지)
            mutation_rate: 돌연변이 확률
            initial_capital: 전략당 초기 자본
        """
        self.virtual_manager = virtual_manager
        self.data_fetcher = data_fetcher
        self.population_size = population_size
        self.elite_ratio = elite_ratio
        self.mutation_rate = mutation_rate
        self.initial_capital = initial_capital

        # 현재 세대
        self.generation = 0

        # 유전자 풀 (활성 전략)
        self.gene_pool: List[Tuple[int, StrategyGene]] = []  # [(strategy_id, gene), ...]

        # 적합도 히스토리
        self.fitness_history: List[StrategyFitness] = []

        # 최고 성과 전략
        self.best_strategy: Optional[Tuple[int, StrategyGene, StrategyFitness]] = None

        logger.info(f"진화 엔진 초기화: 모집단={population_size}, 엘리트={elite_ratio*100}%, 돌연변이={mutation_rate*100}%")

    def initialize_population(self) -> List[int]:
        """
        초기 모집단 생성

        Returns:
            생성된 전략 ID 리스트
        """
        logger.info(f"🧬 초기 모집단 생성 중 ({self.population_size}개)...")

        strategy_ids = []

        for i in range(self.population_size):
            # 랜덤 유전자 생성
            gene = self._generate_random_gene()

            # 전략 생성
            strategy_name = f"진화-G{self.generation:03d}-S{i:02d}"
            description = self._gene_to_description(gene)

            strategy_id = self.virtual_manager.create_strategy(
                name=strategy_name,
                description=description,
                initial_capital=self.initial_capital
            )

            # 유전자 풀에 추가
            self.gene_pool.append((strategy_id, gene))
            strategy_ids.append(strategy_id)

            logger.info(f"  [{i+1}/{self.population_size}] {strategy_name} 생성")

        logger.info(f"✅ 초기 모집단 생성 완료: {len(strategy_ids)}개")
        return strategy_ids

    def evaluate_fitness(self) -> List[StrategyFitness]:
        """
        현재 세대의 적합도 평가

        Returns:
            적합도 리스트 (점수 높은 순)
        """
        logger.info(f"📊 제{self.generation}세대 적합도 평가 중...")

        fitness_results = []

        for strategy_id, gene in self.gene_pool:
            # 성과 지표 계산
            metrics = self.virtual_manager.get_performance_metrics(strategy_id)

            return_rate = metrics.get('return_rate', 0)
            win_rate = metrics.get('win_rate', 0)
            max_drawdown = metrics.get('max_drawdown', 0)
            trade_count = metrics.get('trade_count', 0)

            # 샤프 비율 계산 (간단 버전)
            sharpe_ratio = self._calculate_sharpe_ratio(metrics)

            # 손익비 계산
            profit_factor = self._calculate_profit_factor(metrics)

            # 적합도 점수 계산 (수익성)
            fitness_score = self._calculate_fitness_score(
                return_rate, sharpe_ratio, win_rate, trade_count
            )

            # 안전성 점수 계산
            safety_score = self._calculate_safety_score(
                sharpe_ratio, max_drawdown, win_rate, profit_factor
            )

            # 종합 점수 (70% 수익성 + 30% 안전성)
            total_score = fitness_score * 0.7 + safety_score * 0.3

            fitness = StrategyFitness(
                strategy_id=strategy_id,
                generation=self.generation,
                return_rate=return_rate,
                sharpe_ratio=sharpe_ratio,
                win_rate=win_rate,
                max_drawdown=max_drawdown,
                profit_factor=profit_factor,
                trade_count=trade_count,
                fitness_score=fitness_score,
                safety_score=safety_score,
                total_score=total_score
            )

            fitness_results.append(fitness)
            self.fitness_history.append(fitness)

        # 점수 높은 순으로 정렬
        fitness_results.sort(key=lambda f: f.total_score, reverse=True)

        # 최고 성과 업데이트
        if fitness_results:
            best = fitness_results[0]
            if self.best_strategy is None or best.total_score > self.best_strategy[2].total_score:
                best_gene = next(gene for sid, gene in self.gene_pool if sid == best.strategy_id)
                self.best_strategy = (best.strategy_id, best_gene, best)
                logger.info(
                    f"🏆 새로운 최고 전략 발견! "
                    f"수익률={best.return_rate:.2f}%, "
                    f"샤프={best.sharpe_ratio:.2f}, "
                    f"승률={best.win_rate:.1f}%, "
                    f"점수={best.total_score:.1f}"
                )

        logger.info(f"✅ 적합도 평가 완료: 평균 점수 {sum(f.total_score for f in fitness_results) / len(fitness_results):.1f}")

        return fitness_results

    def evolve_generation(self) -> List[int]:
        """
        다음 세대로 진화

        Returns:
            새로운 전략 ID 리스트
        """
        logger.info(f"🧬 제{self.generation+1}세대로 진화 시작...")

        # 1. 적합도 평가
        fitness_results = self.evaluate_fitness()

        # 2. 엘리트 선택 (상위 30%)
        elite_count = max(1, int(len(fitness_results) * self.elite_ratio))
        elites = fitness_results[:elite_count]

        logger.info(f"⭐ 엘리트 {elite_count}개 선택:")
        for i, elite in enumerate(elites):
            logger.info(
                f"  [{i+1}] 전략#{elite.strategy_id}: "
                f"수익률={elite.return_rate:.2f}%, 점수={elite.total_score:.1f}"
            )

        # 3. 약한 전략 제거
        weak_strategies = fitness_results[elite_count:]
        for weak in weak_strategies:
            self.virtual_manager.delete_strategy(weak.strategy_id)
            # 유전자 풀에서 제거
            self.gene_pool = [(sid, gene) for sid, gene in self.gene_pool if sid != weak.strategy_id]

        logger.info(f"🗑️  약한 전략 {len(weak_strategies)}개 제거")

        # 4. 새로운 전략 생성 (교배 + 돌연변이)
        new_strategy_ids = []
        new_strategies_needed = self.population_size - elite_count

        for i in range(new_strategies_needed):
            # 랜덤으로 2개 엘리트 선택
            parent1 = random.choice(elites)
            parent2 = random.choice(elites)

            parent1_gene = next(gene for sid, gene in self.gene_pool if sid == parent1.strategy_id)
            parent2_gene = next(gene for sid, gene in self.gene_pool if sid == parent2.strategy_id)

            # 교배
            child_gene = self._crossover(parent1_gene, parent2_gene)

            # 돌연변이
            if random.random() < self.mutation_rate:
                child_gene = self._mutate(child_gene)
                logger.debug(f"  🧬 돌연변이 발생!")

            # 새 전략 생성
            strategy_name = f"진화-G{self.generation+1:03d}-S{elite_count+i:02d}"
            description = self._gene_to_description(child_gene)

            strategy_id = self.virtual_manager.create_strategy(
                name=strategy_name,
                description=description,
                initial_capital=self.initial_capital
            )

            self.gene_pool.append((strategy_id, child_gene))
            new_strategy_ids.append(strategy_id)

        logger.info(f"✅ 새로운 전략 {len(new_strategy_ids)}개 생성 (교배+돌연변이)")

        # 세대 증가
        self.generation += 1

        return new_strategy_ids

    def _generate_random_gene(self) -> StrategyGene:
        """랜덤 유전자 생성"""
        return StrategyGene(
            rsi_min=random.uniform(20, 40),
            rsi_max=random.uniform(50, 70),
            volume_ratio_min=random.uniform(1.2, 2.5),
            bid_ask_ratio_min=random.uniform(1.05, 1.5),
            take_profit_pct=random.uniform(5, 20),
            stop_loss_pct=random.uniform(3, 10),
            trailing_stop_pct=random.uniform(5, 15),
            rsi_overbought_min=random.uniform(65, 75),
            rsi_overbought_max=random.uniform(80, 95),
            position_size_pct=random.uniform(10, 25),
            max_positions=random.randint(2, 4),
            trade_start_hour=random.randint(9, 11),
            trade_end_hour=random.randint(14, 18),
            price_min=random.randint(5000, 30000),
            price_max=random.randint(100000, 400000),
            split_buy_enabled=random.choice([True, False]),
            split_buy_count=random.randint(2, 4)
        )

    def _crossover(self, parent1: StrategyGene, parent2: StrategyGene) -> StrategyGene:
        """교배 (2점 교차)"""
        # 각 유전자를 50% 확률로 선택
        return StrategyGene(
            rsi_min=random.choice([parent1.rsi_min, parent2.rsi_min]),
            rsi_max=random.choice([parent1.rsi_max, parent2.rsi_max]),
            volume_ratio_min=random.choice([parent1.volume_ratio_min, parent2.volume_ratio_min]),
            bid_ask_ratio_min=random.choice([parent1.bid_ask_ratio_min, parent2.bid_ask_ratio_min]),
            take_profit_pct=random.choice([parent1.take_profit_pct, parent2.take_profit_pct]),
            stop_loss_pct=random.choice([parent1.stop_loss_pct, parent2.stop_loss_pct]),
            trailing_stop_pct=random.choice([parent1.trailing_stop_pct, parent2.trailing_stop_pct]),
            rsi_overbought_min=random.choice([parent1.rsi_overbought_min, parent2.rsi_overbought_min]),
            rsi_overbought_max=random.choice([parent1.rsi_overbought_max, parent2.rsi_overbought_max]),
            position_size_pct=random.choice([parent1.position_size_pct, parent2.position_size_pct]),
            max_positions=random.choice([parent1.max_positions, parent2.max_positions]),
            trade_start_hour=random.choice([parent1.trade_start_hour, parent2.trade_start_hour]),
            trade_end_hour=random.choice([parent1.trade_end_hour, parent2.trade_end_hour]),
            price_min=random.choice([parent1.price_min, parent2.price_min]),
            price_max=random.choice([parent1.price_max, parent2.price_max]),
            split_buy_enabled=random.choice([parent1.split_buy_enabled, parent2.split_buy_enabled]),
            split_buy_count=random.choice([parent1.split_buy_count, parent2.split_buy_count])
        )

    def _mutate(self, gene: StrategyGene) -> StrategyGene:
        """돌연변이 (랜덤 필드 변경)"""
        mutated = copy.deepcopy(gene)

        # 랜덤으로 1-3개 필드 변경
        fields_to_mutate = random.sample([
            'rsi_min', 'rsi_max', 'volume_ratio_min', 'take_profit_pct',
            'stop_loss_pct', 'position_size_pct', 'max_positions'
        ], k=random.randint(1, 3))

        for field in fields_to_mutate:
            if field == 'rsi_min':
                mutated.rsi_min = random.uniform(20, 40)
            elif field == 'rsi_max':
                mutated.rsi_max = random.uniform(50, 70)
            elif field == 'volume_ratio_min':
                mutated.volume_ratio_min = random.uniform(1.2, 2.5)
            elif field == 'take_profit_pct':
                mutated.take_profit_pct = random.uniform(5, 20)
            elif field == 'stop_loss_pct':
                mutated.stop_loss_pct = random.uniform(3, 10)
            elif field == 'position_size_pct':
                mutated.position_size_pct = random.uniform(10, 25)
            elif field == 'max_positions':
                mutated.max_positions = random.randint(2, 4)

        return mutated

    def _calculate_sharpe_ratio(self, metrics: Dict[str, Any]) -> float:
        """샤프 비율 계산 (간단 버전)"""
        return_rate = metrics.get('return_rate', 0)
        max_drawdown = metrics.get('max_drawdown', 1)

        # 수익률 / 변동성
        if max_drawdown > 0:
            return return_rate / max_drawdown
        return 0

    def _calculate_profit_factor(self, metrics: Dict[str, Any]) -> float:
        """손익비 계산"""
        win_count = metrics.get('win_count', 0)
        loss_count = metrics.get('loss_count', 0)

        if loss_count > 0:
            return win_count / loss_count
        return win_count if win_count > 0 else 0

    def _calculate_fitness_score(
        self,
        return_rate: float,
        sharpe_ratio: float,
        win_rate: float,
        trade_count: int
    ) -> float:
        """적합도 점수 계산 (수익성 중심)"""
        score = 0

        # 수익률 (0-40점)
        if return_rate >= 30:
            score += 40
        elif return_rate >= 20:
            score += 35
        elif return_rate >= 10:
            score += 25
        elif return_rate >= 5:
            score += 15
        elif return_rate >= 0:
            score += 5

        # 샤프 비율 (0-30점)
        if sharpe_ratio >= 2.0:
            score += 30
        elif sharpe_ratio >= 1.5:
            score += 25
        elif sharpe_ratio >= 1.0:
            score += 20
        elif sharpe_ratio >= 0.5:
            score += 10

        # 승률 (0-20점)
        if win_rate >= 70:
            score += 20
        elif win_rate >= 60:
            score += 15
        elif win_rate >= 50:
            score += 10
        elif win_rate >= 40:
            score += 5

        # 거래 횟수 (0-10점)
        if trade_count >= 20:
            score += 10
        elif trade_count >= 10:
            score += 7
        elif trade_count >= 5:
            score += 4

        return min(score, 100)

    def _calculate_safety_score(
        self,
        sharpe_ratio: float,
        max_drawdown: float,
        win_rate: float,
        profit_factor: float
    ) -> float:
        """안전성 점수 계산"""
        score = 0

        # 샤프 비율 (0-30점)
        if sharpe_ratio >= 2.5:
            score += 30
        elif sharpe_ratio >= 2.0:
            score += 25
        elif sharpe_ratio >= 1.5:
            score += 20
        elif sharpe_ratio >= 1.0:
            score += 15

        # 최대 낙폭 (0-30점)
        if max_drawdown <= 5:
            score += 30
        elif max_drawdown <= 10:
            score += 25
        elif max_drawdown <= 15:
            score += 20
        elif max_drawdown <= 20:
            score += 10

        # 승률 (0-20점)
        if win_rate >= 70:
            score += 20
        elif win_rate >= 60:
            score += 15
        elif win_rate >= 50:
            score += 10

        # 손익비 (0-20점)
        if profit_factor >= 2.0:
            score += 20
        elif profit_factor >= 1.5:
            score += 15
        elif profit_factor >= 1.0:
            score += 10

        return min(score, 100)

    def _gene_to_description(self, gene: StrategyGene) -> str:
        """유전자를 설명 문자열로 변환"""
        return (
            f"진화 전략 📊\n"
            f"매수: RSI {gene.rsi_min:.1f}-{gene.rsi_max:.1f}, "
            f"거래량 {gene.volume_ratio_min:.2f}x 이상\n"
            f"매도: 익절 +{gene.take_profit_pct:.1f}%, "
            f"손절 -{gene.stop_loss_pct:.1f}%\n"
            f"포지션: {gene.position_size_pct:.1f}% (최대 {gene.max_positions}개)"
        )

    def get_best_strategy_info(self) -> Optional[Dict[str, Any]]:
        """최고 성과 전략 정보 반환"""
        if not self.best_strategy:
            return None

        strategy_id, gene, fitness = self.best_strategy

        return {
            'strategy_id': strategy_id,
            'generation': fitness.generation,
            'return_rate': fitness.return_rate,
            'sharpe_ratio': fitness.sharpe_ratio,
            'win_rate': fitness.win_rate,
            'max_drawdown': fitness.max_drawdown,
            'fitness_score': fitness.fitness_score,
            'safety_score': fitness.safety_score,
            'total_score': fitness.total_score,
            'gene': gene.to_dict()
        }


# Singleton
_evolution_engine = None


def get_evolution_engine(virtual_manager=None, data_fetcher=None) -> Optional[StrategyEvolutionEngine]:
    """진화 엔진 싱글톤 가져오기"""
    global _evolution_engine

    if _evolution_engine is None and virtual_manager and data_fetcher:
        _evolution_engine = StrategyEvolutionEngine(
            virtual_manager=virtual_manager,
            data_fetcher=data_fetcher,
            population_size=20,
            elite_ratio=0.3,
            mutation_rate=0.1,
            initial_capital=5000000  # 500만원씩
        )

    return _evolution_engine


__all__ = ['StrategyEvolutionEngine', 'get_evolution_engine', 'StrategyGene', 'StrategyFitness']
