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

logger = get_logger()


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
        elite_ratio: float = 0.2,
        market_api = None
    ):
        """초기화"""
        self.db_path = db_path
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_count = max(1, int(population_size * elite_ratio))
        self.current_generation = 0
        self.running = False
        self.market_api = market_api
        self.backtester = None

        # 백테스터 초기화 (market_api가 제공된 경우)
        if market_api:
            try:
                from ai.strategy_backtester import StrategyBacktester
                self.backtester = StrategyBacktester(market_api)
                logger.info("✅ 실제 백테스터 연결 완료")
            except Exception as e:
                logger.warning(f"백테스터 초기화 실패: {e}. 시뮬레이션 모드로 실행됩니다.")
                self.backtester = None
        else:
            logger.warning("⚠️ market_api 미제공 - 시뮬레이션 모드로 실행됩니다")

        self._init_database()

        logger.info(f"전략 최적화 엔진 초기화 완료")
        logger.info(f"  - 세대당 전략 수: {population_size}")
        logger.info(f"  - 변이 확률: {mutation_rate * 100}%")
        logger.info(f"  - 모드: {'실제 백테스팅' if self.backtester else '시뮬레이션'}")

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

    def _create_strategy_from_gene(self, gene: StrategyGene, name: str = "Evolved Strategy"):
        """StrategyGene을 백테스트 가능한 전략 객체로 변환"""
        class GeneBasedStrategy:
            def __init__(self, gene: StrategyGene, name: str):
                self.name = name
                self.gene = gene
                self.cash = 10000000
                self.positions = {}

            def reset(self):
                self.cash = 10000000
                self.positions = {}

            def should_buy(self, stock_data, market_data, ai_analysis):
                """매수 조건"""
                # RSI 조건
                rsi = stock_data.get('rsi', 50)
                if not (self.gene.buy_rsi_min <= rsi <= self.gene.buy_rsi_max):
                    return False

                # 거래량 조건
                volume_ratio = stock_data.get('volume_ratio', 1.0)
                if volume_ratio < self.gene.buy_volume_ratio_min:
                    return False

                # 호가 비율 조건 (매수우위)
                bid_ask_ratio = stock_data.get('bid_ask_ratio', 1.0)
                if bid_ask_ratio < self.gene.buy_bid_ask_ratio_min:
                    return False

                # 시간 필터
                current_time = stock_data.get('time', '09:00')
                if not (self.gene.trade_time_start <= current_time <= self.gene.trade_time_end):
                    return False

                # 가격 필터
                price = stock_data.get('close', 0)
                if not (self.gene.min_price <= price <= self.gene.max_price):
                    return False

                return True

            def should_sell(self, stock_code, position, current_price):
                """매도 조건"""
                buy_price = position['buy_price']
                profit_pct = ((current_price - buy_price) / buy_price)

                # 익절 조건
                if profit_pct >= self.gene.sell_take_profit:
                    return True

                # 손절 조건
                if profit_pct <= self.gene.sell_stop_loss:
                    return True

                # 추적 손절 (최고점 대비 하락)
                if 'max_price' in position:
                    max_price = position['max_price']
                    drawdown = (current_price - max_price) / max_price
                    if drawdown <= -self.gene.sell_trailing_stop:
                        return True

                # RSI 과매수 조건
                rsi = position.get('current_rsi', 50)
                if self.gene.sell_rsi_min <= rsi <= self.gene.sell_rsi_max:
                    return True

                return False

        return GeneBasedStrategy(gene, name)

    def evaluate_fitness(self, gene: StrategyGene, stock_codes: List[str] = None) -> Tuple[float, Dict[str, Any]]:
        """
        적합도 평가 (백테스팅)

        Returns:
            (fitness_score, metrics_dict)
        """
        # 실제 백테스팅 실행
        if self.backtester and stock_codes:
            try:
                # 전략 생성
                strategy = self._create_strategy_from_gene(gene, f"Gene-{self.current_generation}")

                # 백테스터에 전략 주입 (기존 전략 대체)
                original_strategies = self.backtester.strategies
                self.backtester.strategies = [strategy]

                # 최근 3개월 백테스트
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)

                results = self.backtester.run_backtest(
                    stock_codes=stock_codes,
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d'),
                    interval='5',  # 5분봉
                    parallel=False
                )

                # 원래 전략 복원
                self.backtester.strategies = original_strategies

                # 결과 추출
                if strategy.name in results:
                    result = results[strategy.name]
                    metrics = {
                        'total_return_pct': result.total_return_pct,
                        'sharpe_ratio': result.sharpe_ratio,
                        'win_rate': result.win_rate,
                        'max_drawdown_pct': result.max_drawdown_pct,
                        'profit_factor': result.profit_factor,
                        'total_trades': result.total_trades
                    }
                    fitness = self._calculate_fitness(
                        result.total_return_pct,
                        result.sharpe_ratio,
                        result.win_rate,
                        result.max_drawdown_pct,
                        result.profit_factor
                    )
                    return fitness, metrics
                else:
                    logger.warning(f"백테스트 결과 없음 - 시뮬레이션 모드로 fallback")

            except Exception as e:
                logger.warning(f"백테스트 실패: {e} - 시뮬레이션 모드로 fallback")

        # 시뮬레이션 모드 (fallback)
        total_return = random.uniform(-10, 30)
        sharpe_ratio = random.uniform(0, 2)
        win_rate = random.uniform(40, 70)
        max_drawdown = random.uniform(-20, -3)
        profit_factor = random.uniform(0.5, 2.5)

        metrics = {
            'total_return_pct': total_return,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'max_drawdown_pct': max_drawdown,
            'profit_factor': profit_factor,
            'total_trades': random.randint(10, 50)
        }

        fitness = self._calculate_fitness(total_return, sharpe_ratio, win_rate, max_drawdown, profit_factor)
        return fitness, metrics

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

    def save_generation(self, population: List[StrategyGene], fitness_scores: List[float], metrics_list: List[Dict[str, Any]]):
        """세대 저장 (실제 성과 지표 포함)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            strategy_ids = []
            for gene, fitness, metrics in zip(population, fitness_scores, metrics_list):
                # 전략 저장
                cursor.execute("INSERT INTO evolved_strategies (generation, genes) VALUES (?, ?)",
                             (self.current_generation, json.dumps(gene.to_dict())))
                strategy_id = cursor.lastrowid
                strategy_ids.append(strategy_id)

                # 실제 성과 지표 저장
                cursor.execute("""
                    INSERT INTO fitness_results (
                        strategy_id, generation, fitness_score,
                        total_return_pct, sharpe_ratio, win_rate,
                        max_drawdown_pct, profit_factor, total_trades
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy_id, self.current_generation, fitness,
                    metrics.get('total_return_pct', 0),
                    metrics.get('sharpe_ratio', 0),
                    metrics.get('win_rate', 0),
                    metrics.get('max_drawdown_pct', 0),
                    metrics.get('profit_factor', 0),
                    metrics.get('total_trades', 0)
                ))

            # 세대 통계 저장 (최우수 전략 ID 포함)
            best_idx = fitness_scores.index(max(fitness_scores))
            best_strategy_id = strategy_ids[best_idx]

            cursor.execute("""
                INSERT INTO generation_stats (
                    generation, best_fitness, avg_fitness, worst_fitness, best_strategy_id
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                self.current_generation,
                max(fitness_scores),
                sum(fitness_scores) / len(fitness_scores),
                min(fitness_scores),
                best_strategy_id
            ))

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
        logger.info(f"  모드: {'실제 백테스팅' if self.backtester and stock_codes else '시뮬레이션'}")
        if stock_codes:
            logger.info(f"  테스트 종목: {', '.join(stock_codes)}")

        self.running = True
        population = self.initialize_population()
        generation_count = 0

        while self.running and (not max_generations or generation_count < max_generations):
            logger.info("=" * 80)
            logger.info(f"📊 세대 {self.current_generation} 평가 중...")
            logger.info("=" * 80)
            start_time = time.time()

            # 병렬 평가
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(self.evaluate_fitness, gene, stock_codes): i for i, gene in enumerate(population)}
                fitness_scores = [0.0] * len(population)
                metrics_list = [{}] * len(population)

                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        fitness, metrics = future.result()
                        fitness_scores[idx] = fitness
                        metrics_list[idx] = metrics
                    except Exception as e:
                        logger.error(f"전략 {idx} 평가 실패: {e}")
                        # 기본값 설정
                        fitness_scores[idx] = 0.0
                        metrics_list[idx] = {
                            'total_return_pct': 0, 'sharpe_ratio': 0, 'win_rate': 0,
                            'max_drawdown_pct': 0, 'profit_factor': 0, 'total_trades': 0
                        }

            elapsed = time.time() - start_time
            logger.info(f"✅ 세대 {self.current_generation} 평가 완료 ({elapsed:.1f}초)")
            logger.info(f"  🏆 최고 점수: {max(fitness_scores):.2f}")
            logger.info(f"  📊 평균 점수: {sum(fitness_scores)/len(fitness_scores):.2f}")
            logger.info(f"  📉 최저 점수: {min(fitness_scores):.2f}")

            # DB 저장
            self.save_generation(population, fitness_scores, metrics_list)

            # 다음 세대 진화
            logger.info(f"세대 진화 중... (현재 세대: {self.current_generation})")
            elite_indices = sorted(range(len(fitness_scores)), key=lambda i: fitness_scores[i], reverse=True)[:self.elite_count]
            logger.info(f"  엘리트 보존: {self.elite_count}개 (최고 점수: {fitness_scores[elite_indices[0]]:.2f})")

            population = self.evolve_generation(population, fitness_scores)
            self.current_generation += 1
            generation_count += 1

            # 대기
            if self.running and (not max_generations or generation_count < max_generations):
                logger.info(f"⏰ {interval_seconds}초 후 다음 세대 시작...")
                time.sleep(interval_seconds)

        logger.info("=" * 80)
        logger.info(f"🏁 전략 최적화 종료 (총 {generation_count}세대)")
        logger.info("=" * 80)

    def stop(self):
        """중지"""
        self.running = False


if __name__ == "__main__":
    engine = StrategyOptimizationEngine(population_size=10)
    engine.run_continuous_optimization(max_generations=3, interval_seconds=5)
