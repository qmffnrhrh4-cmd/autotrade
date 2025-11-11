"""
전략 최적화 엔진 (Strategy Optimization Engine)

24/7 백테스팅과 가상매매를 통한 자기진화 시스템
"""
import logging
import time
import random
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import json

from utils.logger_new import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyGene:
    """전략 유전자"""
    # 매수 조건
    buy_rsi_min: float = 20.0
    buy_rsi_max: float = 40.0
    buy_volume_ratio_min: float = 1.2
    buy_volume_ratio_max: float = 3.0
    buy_bid_ask_ratio_min: float = 1.1

    # 매도 조건
    sell_rsi_min: float = 60.0
    sell_rsi_max: float = 80.0
    sell_take_profit: float = 0.10  # 10%
    sell_stop_loss: float = -0.05  # -5%
    sell_trailing_stop: float = 0.03  # 3%

    # 포지션 크기
    position_size_pct: float = 0.10  # 계좌의 10%

    # 시간 필터
    trade_time_start: str = "09:30"
    trade_time_end: str = "15:00"

    # 종목 필터
    min_price: float = 10000
    max_price: float = 200000
    min_volume: float = 100000

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyGene':
        """딕셔너리에서 생성"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class StrategyOptimizationEngine:
    """전략 최적화 엔진"""

    def __init__(
        self,
        db_path: str = "data/strategy_evolution.db",
        population_size: int = 20,
        mutation_rate: float = 0.15,
        crossover_rate: float = 0.7,
        elite_ratio: float = 0.2
    ):
        """초기화"""
        self.db_path = db_path
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_count = max(1, int(population_size * elite_ratio))
        self.current_generation = 0
        self.running = False
        self.backtester = None

        self._init_database()

        logger.info(f"전략 최적화 엔진 초기화 완료")
        logger.info(f"  - 세대당 전략 수: {population_size}")
        logger.info(f"  - 변이 확률: {mutation_rate * 100}%")

    def _init_database(self):
        """데이터베이스 초기화"""
        import os
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else '.', exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolved_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generation INTEGER NOT NULL,
                genes TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fitness_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                generation INTEGER NOT NULL,
                total_return_pct REAL,
                sharpe_ratio REAL,
                win_rate REAL,
                max_drawdown_pct REAL,
                profit_factor REAL,
                total_trades INTEGER,
                fitness_score REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_id) REFERENCES evolved_strategies(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generation_stats (
                generation INTEGER PRIMARY KEY,
                best_fitness REAL NOT NULL,
                avg_fitness REAL NOT NULL,
                worst_fitness REAL NOT NULL,
                best_strategy_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"데이터베이스 초기화 완료: {self.db_path}")

    def initialize_population(self) -> List[StrategyGene]:
        """초기 세대 생성"""
        logger.info(f"초기 세대 생성 중... (크기: {self.population_size})")
        population = []
        for i in range(self.population_size):
            gene = StrategyGene(
                buy_rsi_min=random.uniform(15, 35),
                buy_rsi_max=random.uniform(35, 50),
                buy_volume_ratio_min=random.uniform(1.1, 2.0),
                sell_take_profit=random.uniform(0.05, 0.25),
                sell_stop_loss=random.uniform(-0.15, -0.03),
                position_size_pct=random.uniform(0.05, 0.20)
            )
            population.append(gene)
        logger.info(f"✅ 초기 세대 {self.population_size}개 생성 완료")
        return population

    def evaluate_fitness(self, gene: StrategyGene, stock_codes: List[str] = None) -> float:
        """적합도 평가 (백테스팅)"""
        # 임시: 랜덤 점수 (나중에 실제 백테스팅 연결)
        total_return = random.uniform(-10, 30)
        sharpe_ratio = random.uniform(0, 2)
        win_rate = random.uniform(40, 70)
        max_drawdown = random.uniform(-20, -3)
        profit_factor = random.uniform(0.5, 2.5)

        return self._calculate_fitness(total_return, sharpe_ratio, win_rate, max_drawdown, profit_factor)

    def _calculate_fitness(self, total_return_pct, sharpe_ratio, win_rate, max_drawdown_pct, profit_factor) -> float:
        """적합도 계산"""
        weights = {'total_return': 0.30, 'sharpe_ratio': 0.25, 'win_rate': 0.15, 'max_drawdown': 0.15, 'profit_factor': 0.15}
        normalized = {
            'total_return': self._normalize(total_return_pct, -20, 50),
            'sharpe_ratio': self._normalize(sharpe_ratio, -1, 3),
            'win_rate': self._normalize(win_rate, 30, 80),
            'max_drawdown': 1 - self._normalize(abs(max_drawdown_pct), 0, 30),
            'profit_factor': self._normalize(profit_factor, 0, 3),
        }
        return sum(weights[k] * normalized[k] for k in weights.keys()) * 100

    def _normalize(self, value: float, min_val: float, max_val: float) -> float:
        """0-1 정규화"""
        if max_val == min_val:
            return 0.5
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

    def mutate(self, gene: StrategyGene) -> StrategyGene:
        """변이"""
        mutated = StrategyGene(**gene.to_dict())
        if random.random() < self.mutation_rate:
            mutated.buy_rsi_min = max(10, min(40, mutated.buy_rsi_min + random.uniform(-5, 5)))
        if random.random() < self.mutation_rate:
            mutated.sell_take_profit = max(0.03, min(0.30, mutated.sell_take_profit + random.uniform(-0.05, 0.05)))
        return mutated

    def crossover(self, parent1: StrategyGene, parent2: StrategyGene) -> StrategyGene:
        """교차"""
        genes1, genes2 = parent1.to_dict(), parent2.to_dict()
        child_genes = {k: genes1[k] if random.random() < 0.5 else genes2[k] for k in genes1.keys()}
        return StrategyGene.from_dict(child_genes)

    def select_parents(self, population: List[StrategyGene], fitness_scores: List[float]) -> Tuple[StrategyGene, StrategyGene]:
        """토너먼트 선택"""
        def tournament():
            indices = random.sample(range(len(population)), 3)
            return population[max(indices, key=lambda i: fitness_scores[i])]
        return tournament(), tournament()

    def evolve_generation(self, population: List[StrategyGene], fitness_scores: List[float]) -> List[StrategyGene]:
        """세대 진화"""
        logger.info(f"세대 진화 중... (현재 세대: {self.current_generation})")
        elite_indices = sorted(range(len(fitness_scores)), key=lambda i: fitness_scores[i], reverse=True)[:self.elite_count]
        next_generation = [population[i] for i in elite_indices]

        while len(next_generation) < self.population_size:
            parent1, parent2 = self.select_parents(population, fitness_scores)
            child = self.crossover(parent1, parent2) if random.random() < self.crossover_rate else parent1
            next_generation.append(self.mutate(child))

        logger.info(f"✅ 다음 세대 생성 완료: {len(next_generation)}개")
        return next_generation

    def save_generation(self, population: List[StrategyGene], fitness_scores: List[float]):
        """세대 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            for gene, fitness in zip(population, fitness_scores):
                cursor.execute("INSERT INTO evolved_strategies (generation, genes) VALUES (?, ?)",
                             (self.current_generation, json.dumps(gene.to_dict())))
                strategy_id = cursor.lastrowid
                cursor.execute("""INSERT INTO fitness_results (strategy_id, generation, fitness_score, total_return_pct, sharpe_ratio, win_rate, max_drawdown_pct, profit_factor, total_trades)
                                VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0)""", (strategy_id, self.current_generation, fitness))

            cursor.execute("""INSERT INTO generation_stats (generation, best_fitness, avg_fitness, worst_fitness, best_strategy_id)
                            VALUES (?, ?, ?, ?, ?)""",
                         (self.current_generation, max(fitness_scores), sum(fitness_scores)/len(fitness_scores), min(fitness_scores), 1))
            conn.commit()
            logger.info(f"세대 {self.current_generation} DB 저장 완료")
        except Exception as e:
            logger.error(f"DB 저장 실패: {e}")
            conn.rollback()
        finally:
            conn.close()

    def run_continuous_optimization(self, stock_codes: List[str] = None, max_generations: int = None, interval_seconds: int = 600):
        """지속적 최적화 실행"""
        logger.info("🚀 지속적 전략 최적화 시작")
        self.running = True
        population = self.initialize_population()
        generation_count = 0

        while self.running and (not max_generations or generation_count < max_generations):
            logger.info(f"📊 세대 {self.current_generation} 평가 중...")
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(self.evaluate_fitness, gene, stock_codes): i for i, gene in enumerate(population)}
                fitness_scores = [0.0] * len(population)
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        fitness_scores[idx] = future.result()
                    except Exception as e:
                        logger.error(f"전략 {idx} 평가 실패: {e}")

            logger.info(f"✅ 세대 {self.current_generation} 완료 ({time.time() - start_time:.1f}초) - 최고: {max(fitness_scores):.2f}")
            self.save_generation(population, fitness_scores)
            population = self.evolve_generation(population, fitness_scores)
            self.current_generation += 1
            generation_count += 1

            if self.running and (not max_generations or generation_count < max_generations):
                time.sleep(interval_seconds)

        logger.info(f"🏁 전략 최적화 종료 (총 {generation_count}세대)")

    def stop(self):
        """중지"""
        self.running = False


if __name__ == "__main__":
    engine = StrategyOptimizationEngine(population_size=10)
    engine.run_continuous_optimization(max_generations=3, interval_seconds=5)
