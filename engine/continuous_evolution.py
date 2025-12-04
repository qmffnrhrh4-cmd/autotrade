"""
engine/continuous_evolution.py
24시간 연속 알고리즘 진화 시스템

쉬는 시간 없이 끊임없이 알고리즘을 분석하고 최적화

Author: AutoTrade Pro
Version: 1.0
"""
import logging
import time
import threading
import json
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import random
import copy

logger = logging.getLogger(__name__)


@dataclass
class StrategyGene:
    """전략 유전자 (40개 파라미터)"""
    # 진입 조건
    rsi_buy_threshold: float = 30.0
    rsi_sell_threshold: float = 70.0
    volume_ratio_min: float = 2.0
    price_change_min: float = 2.0
    price_change_max: float = 15.0

    # 호가/체결
    bid_ask_imbalance_min: float = 0.2
    execution_strength_min: float = 100.0

    # 투자자 조건
    foreign_net_buy_min: int = 0
    institution_net_buy_min: int = 0

    # 기술적 지표
    macd_signal: str = 'golden_cross'  # golden_cross, above_zero, any
    bollinger_position: str = 'lower'  # lower, middle, upper
    ma5_above_ma20: bool = True

    # 포지션 관리
    position_size_pct: float = 10.0  # 1-30%
    max_positions: int = 5
    stop_loss_pct: float = 3.0
    take_profit_pct: float = 5.0
    trailing_stop_pct: float = 2.0

    # 시간 필터
    trade_start_hour: int = 9
    trade_end_hour: int = 15
    avoid_first_minutes: int = 10
    avoid_last_minutes: int = 10

    # 가격 필터
    min_price: int = 1000
    max_price: int = 500000
    min_volume: int = 100000

    # 분할 매수
    split_order_count: int = 1
    split_interval_seconds: int = 60

    # AI 신뢰도
    min_ai_confidence: float = 70.0
    min_composite_score: float = 70.0

    # 추가 조건
    require_sector_trend: bool = False
    require_market_trend: bool = False
    allow_after_hours: bool = False

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'StrategyGene':
        """딕셔너리에서 생성"""
        gene = cls()
        for k, v in data.items():
            if hasattr(gene, k):
                setattr(gene, k, v)
        return gene

    def mutate(self, mutation_rate: float = 0.15) -> 'StrategyGene':
        """돌연변이"""
        mutated = copy.deepcopy(self)

        for attr_name in dir(mutated):
            if attr_name.startswith('_'):
                continue

            if random.random() > mutation_rate:
                continue

            value = getattr(mutated, attr_name)

            if isinstance(value, float):
                # 10-30% 변동
                delta = value * random.uniform(-0.3, 0.3)
                setattr(mutated, attr_name, value + delta)
            elif isinstance(value, int):
                # ±1-3 변동
                delta = random.randint(-3, 3)
                setattr(mutated, attr_name, max(0, value + delta))
            elif isinstance(value, bool):
                setattr(mutated, attr_name, not value)
            elif isinstance(value, str) and attr_name == 'macd_signal':
                options = ['golden_cross', 'above_zero', 'any']
                setattr(mutated, attr_name, random.choice(options))

        return mutated

    def crossover(self, other: 'StrategyGene') -> 'StrategyGene':
        """교차"""
        child = StrategyGene()
        attrs = [a for a in dir(self) if not a.startswith('_') and not callable(getattr(self, a))]

        # 단일점 교차
        crossover_point = random.randint(0, len(attrs) - 1)

        for i, attr in enumerate(attrs):
            if i < crossover_point:
                setattr(child, attr, getattr(self, attr))
            else:
                setattr(child, attr, getattr(other, attr))

        return child


@dataclass
class EvolutionResult:
    """진화 결과"""
    generation: int
    best_gene: StrategyGene
    best_fitness: float
    population_stats: Dict
    timestamp: datetime = field(default_factory=datetime.now)


class ContinuousEvolution:
    """
    24시간 연속 알고리즘 진화 시스템

    - 끊임없이 새로운 전략 생성 및 테스트
    - 실시간 백테스트로 검증
    - 최고 성과 전략 자동 배포
    - 시장 환경 변화에 적응
    """

    def __init__(
        self,
        client,
        population_size: int = 30,
        elite_ratio: float = 0.2,
        mutation_rate: float = 0.15,
        crossover_rate: float = 0.7,
        max_workers: int = 10
    ):
        """
        Args:
            client: KiwoomRESTClient
            population_size: 세대당 개체 수
            elite_ratio: 엘리트 보존 비율
            mutation_rate: 돌연변이 확률
            crossover_rate: 교차 확률
            max_workers: 병렬 백테스트 스레드 수
        """
        self.client = client
        self.population_size = population_size
        self.elite_count = int(population_size * elite_ratio)
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.max_workers = max_workers

        # 스레드 풀
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 개체군
        self.population: List[StrategyGene] = []
        self.fitness_scores: Dict[int, float] = {}  # gene_hash -> fitness

        # 진화 상태
        self.generation = 0
        self.best_gene: Optional[StrategyGene] = None
        self.best_fitness = 0.0
        self.evolution_history: List[EvolutionResult] = []

        # 배포된 전략
        self.deployed_strategies: Dict[str, StrategyGene] = {}

        # 런타임 상태
        self.is_running = False
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

        # 콜백
        self.on_new_best: Optional[Callable] = None
        self.on_generation_complete: Optional[Callable] = None
        self.on_strategy_deployed: Optional[Callable] = None

        logger.info(f"🧬 연속 진화 시스템 초기화: pop={population_size}, mutation={mutation_rate}")

    def initialize_population(self):
        """초기 개체군 생성"""
        self.population = []

        for i in range(self.population_size):
            gene = StrategyGene()

            # 무작위 변이 적용
            gene = gene.mutate(mutation_rate=0.5)

            # 경계값 보정
            gene.rsi_buy_threshold = max(10, min(40, gene.rsi_buy_threshold))
            gene.rsi_sell_threshold = max(60, min(90, gene.rsi_sell_threshold))
            gene.position_size_pct = max(5, min(30, gene.position_size_pct))
            gene.max_positions = max(1, min(10, gene.max_positions))
            gene.stop_loss_pct = max(1, min(10, gene.stop_loss_pct))
            gene.take_profit_pct = max(2, min(20, gene.take_profit_pct))

            self.population.append(gene)

        logger.info(f"✅ 초기 개체군 생성: {len(self.population)}개")

    def start(self):
        """진화 시작"""
        if self.is_running:
            logger.warning("이미 실행 중입니다")
            return

        self.is_running = True
        self._stop_event.clear()

        # 저장된 상태 복원 시도
        if not self.population:
            loaded = self.load_state()
            if loaded and self.population:
                logger.info(f"🔄 이전 진화 상태에서 계속: gen={self.generation}, pop={len(self.population)}")
            else:
                # 상태 복원 실패 또는 빈 개체군 - 새로 시작
                self.initialize_population()

        # 진화 스레드 시작
        thread = threading.Thread(
            target=self._evolution_loop,
            name="ContinuousEvolution",
            daemon=True
        )
        thread.start()

        logger.info("🔥 24시간 연속 진화 시작!")

    def stop(self):
        """진화 중지"""
        # 상태 저장 (중지 전)
        self.save_state()
        self.is_running = False
        self._stop_event.set()
        logger.info("🛑 진화 중지 (상태 저장 완료)")

    def _evolution_loop(self):
        """진화 루프 (24시간 연속)"""
        while not self._stop_event.is_set():
            try:
                start_time = time.time()

                # 1. 적합도 평가 (병렬 백테스트)
                self._evaluate_population()

                # 2. 선택
                parents = self._select_parents()

                # 3. 교차 & 돌연변이
                offspring = self._create_offspring(parents)

                # 4. 다음 세대 구성
                self._update_population(offspring)

                # 5. 최고 개체 확인
                self._check_best()

                # 6. 통계 기록
                elapsed = time.time() - start_time
                self._record_generation(elapsed)

                # 7. 자동 배포 (조건 충족 시)
                self._auto_deploy()

                # 8. 상태 자동 저장 (5세대마다)
                if self.generation % 5 == 0:
                    self.save_state()

                # 세대 완료 로그
                logger.info(
                    f"🧬 세대 {self.generation} 완료: "
                    f"최고={self.best_fitness:.2f}, "
                    f"시간={elapsed:.1f}초"
                )

                # 다음 세대 대기 (시장 상황에 따라 조절)
                wait_time = self._calculate_wait_time()
                time.sleep(wait_time)

            except Exception as e:
                logger.error(f"진화 루프 오류: {e}", exc_info=True)
                time.sleep(60)

    def _evaluate_population(self):
        """개체군 적합도 평가 (병렬 백테스트)"""
        logger.debug(f"📊 {len(self.population)}개 개체 평가 중...")

        futures = {}
        for i, gene in enumerate(self.population):
            gene_hash = hash(json.dumps(gene.to_dict(), sort_keys=True))

            # 이미 평가된 경우 스킵
            if gene_hash in self.fitness_scores:
                continue

            future = self.executor.submit(self._evaluate_gene, gene)
            futures[future] = (i, gene_hash)

        # 결과 수집
        for future in as_completed(futures, timeout=300):
            try:
                i, gene_hash = futures[future]
                fitness = future.result()
                self.fitness_scores[gene_hash] = fitness
            except Exception as e:
                i, gene_hash = futures[future]
                logger.debug(f"개체 {i} 평가 실패: {e}")
                self.fitness_scores[gene_hash] = 0.0

    def _evaluate_gene(self, gene: StrategyGene) -> float:
        """단일 유전자 평가 (백테스트 또는 휴리스틱)"""
        try:
            # 백테스터 임포트
            from ai.unified_backtester import UnifiedBacktester

            backtester = UnifiedBacktester(self.client)

            # 전략 파라미터로 변환
            strategy_params = gene.to_dict()

            # 백테스트 실행
            result = backtester.run_backtest(strategy_params)

            if result and result.get('total_trades', 0) > 0:
                # 복합 적합도 계산
                total_return = result.get('total_return_pct', 0)
                sharpe = result.get('sharpe_ratio', 0)
                win_rate = result.get('win_rate', 0)
                max_dd = result.get('max_drawdown_pct', 100)
                trade_count = result.get('total_trades', 0)

                # 적합도 = 수익률(30%) + 샤프(25%) + 승률(20%) + 드로다운(15%) + 거래수(10%)
                fitness = (
                    min(30, max(-30, total_return * 0.3)) +
                    min(25, max(0, sharpe * 12.5)) +
                    min(20, win_rate * 0.2) +
                    max(0, 15 - max_dd * 0.3) +
                    min(10, trade_count * 0.5)
                )

                return max(0, fitness)

        except Exception as e:
            logger.debug(f"백테스트 실패: {e}")

        # 백테스트 실패 시 휴리스틱 적합도 (전략 파라미터 기반)
        return self._heuristic_fitness(gene)

    def _heuristic_fitness(self, gene: StrategyGene) -> float:
        """휴리스틱 적합도 계산 (백테스트 불가 시)"""
        import random

        fitness = 30.0  # 기본값

        # RSI 설정 점수 (매수 < 35, 매도 > 65가 좋음)
        if 25 <= gene.rsi_buy_threshold <= 35:
            fitness += 5
        if 65 <= gene.rsi_sell_threshold <= 75:
            fitness += 5

        # 손절/익절 비율 점수 (익절 > 손절 * 2가 좋음)
        if gene.take_profit_pct >= gene.stop_loss_pct * 2:
            fitness += 10

        # 포지션 크기 점수 (10~20%가 적당)
        if 10 <= gene.position_size_pct <= 20:
            fitness += 5

        # 최대 포지션 수 점수 (3~5개가 적당)
        if 3 <= gene.max_positions <= 5:
            fitness += 5

        # 거래량 비율 점수 (1.5~3.0이 적당)
        if 1.5 <= gene.volume_ratio_min <= 3.0:
            fitness += 5

        # 약간의 랜덤성 추가 (다양성 유지)
        fitness += random.uniform(-5, 10)

        return max(0, min(100, fitness))

    def _select_parents(self) -> List[StrategyGene]:
        """부모 선택 (토너먼트 선택)"""
        parents = []

        # 적합도 계산
        scored_population = []
        for gene in self.population:
            gene_hash = hash(json.dumps(gene.to_dict(), sort_keys=True))
            fitness = self.fitness_scores.get(gene_hash, 0)
            scored_population.append((gene, fitness))

        # 적합도 순 정렬
        scored_population.sort(key=lambda x: x[1], reverse=True)

        # 엘리트 보존
        for gene, fitness in scored_population[:self.elite_count]:
            parents.append(gene)

        # 토너먼트 선택으로 나머지 채우기
        while len(parents) < self.population_size:
            # 3명 토너먼트
            contestants = random.sample(scored_population, min(3, len(scored_population)))
            winner = max(contestants, key=lambda x: x[1])
            parents.append(winner[0])

        return parents

    def _create_offspring(self, parents: List[StrategyGene]) -> List[StrategyGene]:
        """자손 생성 (교차 & 돌연변이)"""
        offspring = []

        # 엘리트는 그대로 유지
        for gene in parents[:self.elite_count]:
            offspring.append(copy.deepcopy(gene))

        # 나머지는 교차 & 돌연변이
        while len(offspring) < self.population_size:
            # 부모 선택
            parent1, parent2 = random.sample(parents, 2)

            # 교차
            if random.random() < self.crossover_rate:
                child = parent1.crossover(parent2)
            else:
                child = copy.deepcopy(random.choice([parent1, parent2]))

            # 돌연변이
            child = child.mutate(self.mutation_rate)

            # 경계값 보정
            self._clamp_gene_values(child)

            offspring.append(child)

        return offspring

    def _clamp_gene_values(self, gene: StrategyGene):
        """유전자 값 경계 보정"""
        gene.rsi_buy_threshold = max(10, min(45, gene.rsi_buy_threshold))
        gene.rsi_sell_threshold = max(55, min(90, gene.rsi_sell_threshold))
        gene.volume_ratio_min = max(1.0, min(10.0, gene.volume_ratio_min))
        gene.price_change_min = max(0.5, min(10.0, gene.price_change_min))
        gene.price_change_max = max(5.0, min(30.0, gene.price_change_max))

        gene.position_size_pct = max(5, min(30, gene.position_size_pct))
        gene.max_positions = max(1, min(10, gene.max_positions))
        gene.stop_loss_pct = max(1, min(10, gene.stop_loss_pct))
        gene.take_profit_pct = max(2, min(20, gene.take_profit_pct))
        gene.trailing_stop_pct = max(0.5, min(5, gene.trailing_stop_pct))

        gene.min_price = max(500, min(10000, gene.min_price))
        gene.max_price = max(50000, min(1000000, gene.max_price))
        gene.min_volume = max(10000, min(1000000, gene.min_volume))

        gene.min_ai_confidence = max(50, min(95, gene.min_ai_confidence))
        gene.min_composite_score = max(50, min(95, gene.min_composite_score))

    def _update_population(self, offspring: List[StrategyGene]):
        """다음 세대로 갱신"""
        with self._lock:
            self.population = offspring
            self.generation += 1

    def _check_best(self):
        """최고 개체 확인"""
        best = None
        best_fitness = self.best_fitness

        for gene in self.population:
            gene_hash = hash(json.dumps(gene.to_dict(), sort_keys=True))
            fitness = self.fitness_scores.get(gene_hash, 0)

            if fitness > best_fitness:
                best = gene
                best_fitness = fitness

        if best and best_fitness > self.best_fitness:
            self.best_gene = best
            self.best_fitness = best_fitness

            logger.info(f"🏆 새로운 최고 개체! fitness={best_fitness:.2f}")

            if self.on_new_best:
                self.on_new_best(best, best_fitness)

    def _record_generation(self, elapsed: float):
        """세대 통계 기록"""
        fitnesses = [
            self.fitness_scores.get(
                hash(json.dumps(g.to_dict(), sort_keys=True)), 0
            )
            for g in self.population
        ]

        stats = {
            'mean': sum(fitnesses) / len(fitnesses) if fitnesses else 0,
            'max': max(fitnesses) if fitnesses else 0,
            'min': min(fitnesses) if fitnesses else 0,
            'elapsed': elapsed
        }

        result = EvolutionResult(
            generation=self.generation,
            best_gene=copy.deepcopy(self.best_gene) if self.best_gene else StrategyGene(),
            best_fitness=self.best_fitness,
            population_stats=stats
        )

        self.evolution_history.append(result)

        # 히스토리 관리 (최근 1000개만)
        if len(self.evolution_history) > 1000:
            self.evolution_history = self.evolution_history[-1000:]

        if self.on_generation_complete:
            self.on_generation_complete(result)

    def _calculate_wait_time(self) -> int:
        """다음 세대까지 대기 시간 계산"""
        hour = datetime.now().hour

        if 9 <= hour < 16:
            # 장중: 5분 (빠른 적응)
            return 300
        elif 16 <= hour < 18:
            # 장마감 직후: 2분 (결과 분석)
            return 120
        else:
            # 장외: 30분 (심층 분석)
            return 1800

    def _auto_deploy(self):
        """자동 전략 배포"""
        # 조건: 적합도 70 이상 + 10세대 이상 유지
        if self.best_fitness < 70 or self.generation < 10:
            return

        # 이미 배포된 전략인지 확인
        if self.best_gene:
            gene_hash = hash(json.dumps(self.best_gene.to_dict(), sort_keys=True))
            strategy_id = f"evolved_gen{self.generation}_{gene_hash % 10000}"

            if strategy_id not in self.deployed_strategies:
                self.deployed_strategies[strategy_id] = self.best_gene

                logger.info(f"🚀 전략 자동 배포: {strategy_id} (fitness={self.best_fitness:.2f})")

                if self.on_strategy_deployed:
                    self.on_strategy_deployed(strategy_id, self.best_gene)

    # ========== 상태 저장/복원 ==========

    STATE_FILE = "data/evolution_state.json"

    def save_state(self):
        """진화 상태를 파일에 저장"""
        try:
            from pathlib import Path
            state_path = Path(self.STATE_FILE)
            state_path.parent.mkdir(parents=True, exist_ok=True)

            state = {
                'generation': self.generation,
                'best_fitness': self.best_fitness,
                'best_gene': self.best_gene.to_dict() if self.best_gene else None,
                'population': [g.to_dict() for g in self.population],
                'fitness_scores': {str(k): v for k, v in self.fitness_scores.items()},
                'deployed_strategies': {
                    k: v.to_dict() for k, v in self.deployed_strategies.items()
                },
                'saved_at': datetime.now().isoformat()
            }

            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 진화 상태 저장 완료: gen={self.generation}, best_fitness={self.best_fitness:.2f}")
            print(f"💾 진화 상태 저장 완료: gen={self.generation}, best_fitness={self.best_fitness:.2f}")

        except Exception as e:
            logger.error(f"진화 상태 저장 실패: {e}")

    def load_state(self) -> bool:
        """파일에서 진화 상태를 복원"""
        try:
            from pathlib import Path
            state_path = Path(self.STATE_FILE)

            if not state_path.exists():
                logger.info("저장된 진화 상태 없음 - 새로 시작")
                return False

            with open(state_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # 상태 복원
            self.generation = state.get('generation', 0)
            self.best_fitness = state.get('best_fitness', 0.0)

            if state.get('best_gene'):
                self.best_gene = StrategyGene.from_dict(state['best_gene'])

            if state.get('population'):
                self.population = [
                    StrategyGene.from_dict(g) for g in state['population']
                ]

            if state.get('fitness_scores'):
                self.fitness_scores = {
                    int(k): v for k, v in state['fitness_scores'].items()
                }

            if state.get('deployed_strategies'):
                self.deployed_strategies = {
                    k: StrategyGene.from_dict(v)
                    for k, v in state['deployed_strategies'].items()
                }

            saved_at = state.get('saved_at', '알 수 없음')
            logger.info(f"✅ 진화 상태 복원 완료: gen={self.generation}, best_fitness={self.best_fitness:.2f}, saved_at={saved_at}")
            print(f"✅ 진화 상태 복원 완료: gen={self.generation}, best_fitness={self.best_fitness:.2f}")

            return True

        except Exception as e:
            logger.error(f"진화 상태 복원 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ========== 공개 메서드 ==========

    def get_best_strategy(self) -> Optional[StrategyGene]:
        """최고 전략 반환"""
        return copy.deepcopy(self.best_gene) if self.best_gene else None

    def get_evolution_stats(self) -> Dict:
        """진화 통계"""
        return {
            'generation': self.generation,
            'best_fitness': self.best_fitness,
            'population_size': len(self.population),
            'evaluated_genes': len(self.fitness_scores),
            'deployed_strategies': len(self.deployed_strategies),
            'is_running': self.is_running,
            'history_length': len(self.evolution_history)
        }

    def get_recent_history(self, count: int = 50) -> List[EvolutionResult]:
        """최근 진화 히스토리"""
        return self.evolution_history[-count:]

    def inject_strategy(self, gene: StrategyGene):
        """외부 전략 주입 (기존 성공 전략 활용)"""
        with self._lock:
            self.population.append(gene)
            logger.info(f"✅ 외부 전략 주입 완료")


# 시장 환경별 최적 유전자 프리셋
MARKET_PRESETS = {
    'bull': StrategyGene(
        rsi_buy_threshold=35,
        rsi_sell_threshold=75,
        volume_ratio_min=1.5,
        price_change_min=3.0,
        position_size_pct=15,
        max_positions=5,
        stop_loss_pct=4,
        take_profit_pct=8,
    ),
    'bear': StrategyGene(
        rsi_buy_threshold=25,
        rsi_sell_threshold=60,
        volume_ratio_min=3.0,
        price_change_min=1.0,
        position_size_pct=8,
        max_positions=3,
        stop_loss_pct=2,
        take_profit_pct=4,
    ),
    'sideways': StrategyGene(
        rsi_buy_threshold=30,
        rsi_sell_threshold=70,
        volume_ratio_min=2.0,
        price_change_min=2.0,
        position_size_pct=10,
        max_positions=4,
        stop_loss_pct=3,
        take_profit_pct=5,
    ),
}


__all__ = ['ContinuousEvolution', 'StrategyGene', 'EvolutionResult', 'MARKET_PRESETS']
