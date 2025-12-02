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
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class StrategyGene:
    """전략 유전자 (염색체) - 33개 지표"""
    # === 기본 매수 조건 (4개) ===
    rsi_min: float  # 30-50
    rsi_max: float  # 50-70
    volume_ratio_min: float  # 1.0-3.0
    bid_ask_ratio_min: float  # 1.0-2.0

    # === 매도 조건 (5개) ===
    take_profit_pct: float  # 5-20%
    stop_loss_pct: float  # 3-10%
    trailing_stop_pct: float  # 5-15%
    rsi_overbought_min: float  # 65-80
    rsi_overbought_max: float  # 80-95

    # === 포지션 관리 (2개) ===
    position_size_pct: float  # 5-30%
    max_positions: int  # 1-5

    # === 시간 필터 (2개) ===
    trade_start_hour: int  # 9-12
    trade_end_hour: int  # 14-20

    # === 가격 범위 (2개) ===
    price_min: int  # 1000-50000
    price_max: int  # 50000-500000

    # === 분할 매수 (2개) ===
    split_buy_enabled: bool
    split_buy_count: int  # 2-5

    # === MACD 지표 (3개) ===
    macd_signal_cross: bool  # MACD 골든/데드 크로스 사용
    macd_histogram_threshold: float  # Histogram 임계값 (-5.0 ~ 5.0)
    macd_divergence_enabled: bool  # 다이버전스 체크

    # === 볼린저 밴드 (3개) ===
    bb_upper_touch: bool  # 상단 터치 시 매도 신호
    bb_lower_touch: bool  # 하단 터치 시 매수 신호
    bb_width_threshold: float  # 밴드 폭 임계값 (0.5-3.0)

    # === 이동평균선 (4개) ===
    ma5_cross: bool  # 5일선 골든크로스 사용
    ma20_cross: bool  # 20일선 골든크로스 사용
    ma60_above: bool  # 60일선 위에서만 매수
    ma_arrangement: str  # 정배열/역배열/무관 ("bull"/"bear"/"any")

    # === 외국인/기관 (4개) ===
    foreign_buy_min: float  # 외국인 최소 순매수 (백만원, 0-1000)
    foreign_ratio_min: float  # 외국인 보유 비율 최소 (%, 0-30)
    institution_buy_min: float  # 기관 최소 순매수 (백만원, 0-1000)
    institution_ratio_min: float  # 기관 보유 비율 최소 (%, 0-30)

    # === 거래량/호가/체결 (3개) ===
    trading_value_min: float  # 최소 거래대금 (억원, 10-1000)
    execution_power_min: float  # 최소 체결강도 (50-150)
    bid_ask_imbalance_min: float  # 호가 불균형 최소값 (1.0-2.0)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            # 기본 매수 조건
            'rsi_min': self.rsi_min,
            'rsi_max': self.rsi_max,
            'volume_ratio_min': self.volume_ratio_min,
            'bid_ask_ratio_min': self.bid_ask_ratio_min,
            # 매도 조건
            'take_profit_pct': self.take_profit_pct,
            'stop_loss_pct': self.stop_loss_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
            'rsi_overbought_min': self.rsi_overbought_min,
            'rsi_overbought_max': self.rsi_overbought_max,
            # 포지션 관리
            'position_size_pct': self.position_size_pct,
            'max_positions': self.max_positions,
            # 시간 필터
            'trade_start_hour': self.trade_start_hour,
            'trade_end_hour': self.trade_end_hour,
            # 가격 범위
            'price_min': self.price_min,
            'price_max': self.price_max,
            # 분할 매수
            'split_buy_enabled': self.split_buy_enabled,
            'split_buy_count': self.split_buy_count,
            # MACD
            'macd_signal_cross': self.macd_signal_cross,
            'macd_histogram_threshold': self.macd_histogram_threshold,
            'macd_divergence_enabled': self.macd_divergence_enabled,
            # 볼린저 밴드
            'bb_upper_touch': self.bb_upper_touch,
            'bb_lower_touch': self.bb_lower_touch,
            'bb_width_threshold': self.bb_width_threshold,
            # 이동평균선
            'ma5_cross': self.ma5_cross,
            'ma20_cross': self.ma20_cross,
            'ma60_above': self.ma60_above,
            'ma_arrangement': self.ma_arrangement,
            # 외국인/기관
            'foreign_buy_min': self.foreign_buy_min,
            'foreign_ratio_min': self.foreign_ratio_min,
            'institution_buy_min': self.institution_buy_min,
            'institution_ratio_min': self.institution_ratio_min,
            # 거래량/호가/체결
            'trading_value_min': self.trading_value_min,
            'execution_power_min': self.execution_power_min,
            'bid_ask_imbalance_min': self.bid_ask_imbalance_min
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

        # 현재 세대 (기존 전략에서 최대 세대 번호를 계승)
        self.generation = self._get_max_generation()

        # 유전자 풀 (활성 전략)
        self.gene_pool: List[Tuple[int, StrategyGene]] = []  # [(strategy_id, gene), ...]

        self.fitness_history: deque = deque(maxlen=500)

        # 최고 성과 전략
        self.best_strategy: Optional[Tuple[int, StrategyGene, StrategyFitness]] = None

        # CRITICAL: HistoricalDataCollector 초기화
        from .historical_data_collector import get_historical_data_collector
        self.historical_collector = get_historical_data_collector(data_fetcher)

        if not self.historical_collector:
            logger.warning("⚠️ HistoricalDataCollector 초기화 실패 - 실제 데이터 백테스팅 불가")
        else:
            logger.info("✅ HistoricalDataCollector 초기화 완료 - OPEN API 데이터 사용 가능")

        logger.info(f"진화 엔진 초기화: 모집단={population_size}, 엘리트={elite_ratio*100}%, 돌연변이={mutation_rate*100}%")

    def initialize_population(self) -> List[int]:
        """
        초기 모집단 생성

        Returns:
            생성된 전략 ID 리스트
        """
        logger.info(f"🧬 초기 모집단 생성 중 ({self.population_size}개)...")

        strategy_ids = []

        # 현재 타임스탬프 (동일 세대 내 중복 방지)
        timestamp = datetime.now().strftime('%H%M%S')

        for i in range(self.population_size):
            # 랜덤 유전자 생성
            gene = self._generate_random_gene()

            # 전략 생성 (타임스탬프 포함으로 중복 방지)
            strategy_name = f"진화-G{self.generation:03d}-S{i:02d}-{timestamp}"
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

        # 현재 타임스탬프 (동일 세대 내 중복 방지)
        timestamp = datetime.now().strftime('%H%M%S')

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

            # 새 전략 생성 (타임스탬프 포함으로 중복 방지)
            strategy_name = f"진화-G{self.generation+1:03d}-S{elite_count+i:02d}-{timestamp}"
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

    def _get_max_generation(self) -> int:
        """기존 전략에서 최대 세대 번호 조회"""
        try:
            import re
            strategies = self.virtual_manager.db.get_all_strategies()
            max_gen = 0
            for strategy in strategies:
                name = strategy.get('name', '')
                # "진화-G{세대:03d}-S{번호:02d}" 또는 "진화-G{세대:03d}-S{번호:02d}-{timestamp}" 형식에서 세대 번호 추출
                match = re.search(r'진화-G(\d+)-S\d+', name)
                if match:
                    gen = int(match.group(1))
                    max_gen = max(max_gen, gen)
            if max_gen > 0:
                logger.info(f"📊 기존 진화 전략 발견: 최대 세대 {max_gen}, 다음 세대 {max_gen + 1}부터 시작")
                return max_gen + 1
            return 0
        except Exception as e:
            logger.warning(f"세대 번호 조회 실패: {e}")
            return 0

    def _generate_random_gene(self) -> StrategyGene:
        """랜덤 유전자 생성 (33개 지표)"""
        return StrategyGene(
            # 기본 매수 조건
            rsi_min=random.uniform(20, 40),
            rsi_max=random.uniform(50, 70),
            volume_ratio_min=random.uniform(1.2, 2.5),
            bid_ask_ratio_min=random.uniform(1.05, 1.5),
            # 매도 조건
            take_profit_pct=random.uniform(5, 20),
            stop_loss_pct=random.uniform(3, 10),
            trailing_stop_pct=random.uniform(5, 15),
            rsi_overbought_min=random.uniform(65, 75),
            rsi_overbought_max=random.uniform(80, 95),
            # 포지션 관리
            position_size_pct=random.uniform(10, 25),
            max_positions=random.randint(2, 4),
            # 시간 필터
            trade_start_hour=random.randint(9, 11),
            trade_end_hour=random.randint(14, 18),
            # 가격 범위
            price_min=random.randint(5000, 30000),
            price_max=random.randint(100000, 400000),
            # 분할 매수
            split_buy_enabled=random.choice([True, False]),
            split_buy_count=random.randint(2, 4),
            # MACD
            macd_signal_cross=random.choice([True, False]),
            macd_histogram_threshold=random.uniform(-5.0, 5.0),
            macd_divergence_enabled=random.choice([True, False]),
            # 볼린저 밴드
            bb_upper_touch=random.choice([True, False]),
            bb_lower_touch=random.choice([True, False]),
            bb_width_threshold=random.uniform(0.5, 3.0),
            # 이동평균선
            ma5_cross=random.choice([True, False]),
            ma20_cross=random.choice([True, False]),
            ma60_above=random.choice([True, False]),
            ma_arrangement=random.choice(['bull', 'bear', 'any']),
            # 외국인/기관
            foreign_buy_min=random.uniform(0, 1000),
            foreign_ratio_min=random.uniform(0, 30),
            institution_buy_min=random.uniform(0, 1000),
            institution_ratio_min=random.uniform(0, 30),
            # 거래량/호가/체결
            trading_value_min=random.uniform(10, 1000),
            execution_power_min=random.uniform(50, 150),
            bid_ask_imbalance_min=random.uniform(1.0, 2.0)
        )

    def _crossover(self, parent1: StrategyGene, parent2: StrategyGene) -> StrategyGene:
        """교배 (2점 교차) - 각 유전자를 50% 확률로 부모에서 선택"""
        return StrategyGene(
            # 기본 매수 조건
            rsi_min=random.choice([parent1.rsi_min, parent2.rsi_min]),
            rsi_max=random.choice([parent1.rsi_max, parent2.rsi_max]),
            volume_ratio_min=random.choice([parent1.volume_ratio_min, parent2.volume_ratio_min]),
            bid_ask_ratio_min=random.choice([parent1.bid_ask_ratio_min, parent2.bid_ask_ratio_min]),
            # 매도 조건
            take_profit_pct=random.choice([parent1.take_profit_pct, parent2.take_profit_pct]),
            stop_loss_pct=random.choice([parent1.stop_loss_pct, parent2.stop_loss_pct]),
            trailing_stop_pct=random.choice([parent1.trailing_stop_pct, parent2.trailing_stop_pct]),
            rsi_overbought_min=random.choice([parent1.rsi_overbought_min, parent2.rsi_overbought_min]),
            rsi_overbought_max=random.choice([parent1.rsi_overbought_max, parent2.rsi_overbought_max]),
            # 포지션 관리
            position_size_pct=random.choice([parent1.position_size_pct, parent2.position_size_pct]),
            max_positions=random.choice([parent1.max_positions, parent2.max_positions]),
            # 시간 필터
            trade_start_hour=random.choice([parent1.trade_start_hour, parent2.trade_start_hour]),
            trade_end_hour=random.choice([parent1.trade_end_hour, parent2.trade_end_hour]),
            # 가격 범위
            price_min=random.choice([parent1.price_min, parent2.price_min]),
            price_max=random.choice([parent1.price_max, parent2.price_max]),
            # 분할 매수
            split_buy_enabled=random.choice([parent1.split_buy_enabled, parent2.split_buy_enabled]),
            split_buy_count=random.choice([parent1.split_buy_count, parent2.split_buy_count]),
            # MACD
            macd_signal_cross=random.choice([parent1.macd_signal_cross, parent2.macd_signal_cross]),
            macd_histogram_threshold=random.choice([parent1.macd_histogram_threshold, parent2.macd_histogram_threshold]),
            macd_divergence_enabled=random.choice([parent1.macd_divergence_enabled, parent2.macd_divergence_enabled]),
            # 볼린저 밴드
            bb_upper_touch=random.choice([parent1.bb_upper_touch, parent2.bb_upper_touch]),
            bb_lower_touch=random.choice([parent1.bb_lower_touch, parent2.bb_lower_touch]),
            bb_width_threshold=random.choice([parent1.bb_width_threshold, parent2.bb_width_threshold]),
            # 이동평균선
            ma5_cross=random.choice([parent1.ma5_cross, parent2.ma5_cross]),
            ma20_cross=random.choice([parent1.ma20_cross, parent2.ma20_cross]),
            ma60_above=random.choice([parent1.ma60_above, parent2.ma60_above]),
            ma_arrangement=random.choice([parent1.ma_arrangement, parent2.ma_arrangement]),
            # 외국인/기관
            foreign_buy_min=random.choice([parent1.foreign_buy_min, parent2.foreign_buy_min]),
            foreign_ratio_min=random.choice([parent1.foreign_ratio_min, parent2.foreign_ratio_min]),
            institution_buy_min=random.choice([parent1.institution_buy_min, parent2.institution_buy_min]),
            institution_ratio_min=random.choice([parent1.institution_ratio_min, parent2.institution_ratio_min]),
            # 거래량/호가/체결
            trading_value_min=random.choice([parent1.trading_value_min, parent2.trading_value_min]),
            execution_power_min=random.choice([parent1.execution_power_min, parent2.execution_power_min]),
            bid_ask_imbalance_min=random.choice([parent1.bid_ask_imbalance_min, parent2.bid_ask_imbalance_min])
        )

    def _mutate(self, gene: StrategyGene) -> StrategyGene:
        """돌연변이 (랜덤 필드 변경) - 1-5개 필드 랜덤 변경"""
        mutated = copy.deepcopy(gene)

        # 모든 가능한 필드 목록
        all_fields = [
            'rsi_min', 'rsi_max', 'volume_ratio_min', 'take_profit_pct',
            'stop_loss_pct', 'position_size_pct', 'max_positions',
            'macd_signal_cross', 'macd_histogram_threshold', 'bb_width_threshold',
            'ma5_cross', 'ma20_cross', 'ma60_above', 'ma_arrangement',
            'foreign_buy_min', 'institution_buy_min', 'trading_value_min',
            'execution_power_min', 'bid_ask_imbalance_min'
        ]

        # 랜덤으로 1-5개 필드 변경
        fields_to_mutate = random.sample(all_fields, k=random.randint(1, 5))

        for field in fields_to_mutate:
            # 기본 매수 조건
            if field == 'rsi_min':
                mutated.rsi_min = random.uniform(20, 40)
            elif field == 'rsi_max':
                mutated.rsi_max = random.uniform(50, 70)
            elif field == 'volume_ratio_min':
                mutated.volume_ratio_min = random.uniform(1.2, 2.5)
            # 매도 조건
            elif field == 'take_profit_pct':
                mutated.take_profit_pct = random.uniform(5, 20)
            elif field == 'stop_loss_pct':
                mutated.stop_loss_pct = random.uniform(3, 10)
            # 포지션 관리
            elif field == 'position_size_pct':
                mutated.position_size_pct = random.uniform(10, 25)
            elif field == 'max_positions':
                mutated.max_positions = random.randint(2, 4)
            # MACD
            elif field == 'macd_signal_cross':
                mutated.macd_signal_cross = random.choice([True, False])
            elif field == 'macd_histogram_threshold':
                mutated.macd_histogram_threshold = random.uniform(-5.0, 5.0)
            # 볼린저 밴드
            elif field == 'bb_width_threshold':
                mutated.bb_width_threshold = random.uniform(0.5, 3.0)
            # 이동평균선
            elif field == 'ma5_cross':
                mutated.ma5_cross = random.choice([True, False])
            elif field == 'ma20_cross':
                mutated.ma20_cross = random.choice([True, False])
            elif field == 'ma60_above':
                mutated.ma60_above = random.choice([True, False])
            elif field == 'ma_arrangement':
                mutated.ma_arrangement = random.choice(['bull', 'bear', 'any'])
            # 외국인/기관
            elif field == 'foreign_buy_min':
                mutated.foreign_buy_min = random.uniform(0, 1000)
            elif field == 'institution_buy_min':
                mutated.institution_buy_min = random.uniform(0, 1000)
            # 거래량/호가/체결
            elif field == 'trading_value_min':
                mutated.trading_value_min = random.uniform(10, 1000)
            elif field == 'execution_power_min':
                mutated.execution_power_min = random.uniform(50, 150)
            elif field == 'bid_ask_imbalance_min':
                mutated.bid_ask_imbalance_min = random.uniform(1.0, 2.0)

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
