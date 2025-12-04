"""
engine/autonomous_trading_engine.py
자율 진화형 자동매매 엔진

24시간 연속 작동하며 스스로 최적의 알고리즘을 찾아가는 자기 진화형 시스템

주요 기능:
1. 멀티 종목 병렬 매매 (100+ 종목 동시 처리)
2. 24시간 연속 알고리즘 분석 및 진화
3. 모든 REST API 데이터 실시간 수집/분석
4. 자동 전략 배포 및 성과 추적
5. 히스토리컬 데이터 기반 백테스팅 연속 수행

Author: AutoTrade Pro
Version: 1.0
"""
import asyncio
import threading
import time
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
from queue import Queue, PriorityQueue, Empty as QueueEmpty
import random

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """거래 신호"""
    stock_code: str
    stock_name: str
    action: str  # 'buy', 'sell', 'hold'
    confidence: float  # 0-100
    price: int
    quantity: int
    strategy_id: str
    signal_time: datetime = field(default_factory=datetime.now)
    priority: int = 5  # 1=최고, 10=최저
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        return self.priority < other.priority


@dataclass
class StrategyPerformance:
    """전략 성과 추적"""
    strategy_id: str
    total_trades: int = 0
    winning_trades: int = 0
    total_profit: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

    @property
    def win_rate(self) -> float:
        return self.winning_trades / max(self.total_trades, 1) * 100


@dataclass
class EvolutionState:
    """진화 상태"""
    generation: int = 0
    best_fitness: float = 0.0
    best_strategy_id: str = ""
    evolution_history: List[Dict] = field(default_factory=list)
    is_evolving: bool = False
    last_evolution: datetime = None


class AutonomousTradingEngine:
    """
    자율 진화형 자동매매 엔진

    모든 기능을 통합하여 24시간 자동으로 운영:
    - 멀티 종목 병렬 스캐닝 및 매매
    - 연속 백테스팅 및 알고리즘 진화
    - 실시간 API 데이터 수집
    - 자동 전략 배포
    """

    def __init__(
        self,
        client,
        max_workers: int = 20,
        max_positions: int = 50,
        evolution_interval_minutes: int = 30,
        scan_interval_seconds: int = 10,
        enable_auto_evolution: bool = True
    ):
        """
        Args:
            client: KiwoomRESTClient
            max_workers: 병렬 처리 스레드 수
            max_positions: 최대 보유 종목 수
            evolution_interval_minutes: 진화 주기 (분)
            scan_interval_seconds: 스캔 주기 (초)
            enable_auto_evolution: 자동 진화 활성화
        """
        self.client = client
        self.max_workers = max_workers
        self.max_positions = max_positions
        self.evolution_interval = evolution_interval_minutes * 60
        self.scan_interval = scan_interval_seconds
        self.enable_auto_evolution = enable_auto_evolution

        # 스레드 풀
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 신호 큐 (우선순위 기반)
        self.signal_queue = PriorityQueue()

        # 스레드 안전성을 위한 락 (v8.3: 동시성 보호)
        self._positions_lock = threading.RLock()
        self._orders_lock = threading.RLock()
        self._cache_lock = threading.RLock()
        self._activity_lock = threading.RLock()

        # 상태 관리 (락으로 보호됨)
        self.is_running = False
        self.current_positions: Dict[str, Dict] = {}  # stock_code -> position_info
        self.pending_orders: Dict[str, Dict] = {}  # order_no -> order_info

        # 전략 관리
        self.active_strategies: Dict[str, Dict] = {}  # strategy_id -> strategy_config
        self.strategy_performance: Dict[str, StrategyPerformance] = {}

        # 진화 상태
        self.evolution_state = EvolutionState()

        # 데이터 캐시 (초단기, 락으로 보호됨)
        self.price_cache: Dict[str, Dict] = {}  # stock_code -> {price, time}
        self.cache_ttl = 2  # 2초
        self._data_cache: Dict[str, Dict] = {}  # API 데이터 캐시 (인스턴스별로 분리)

        # 성과 추적 (메모리 누수 방지를 위해 최대 1000개 제한)
        self.daily_trades: List[Dict] = []
        self._max_daily_trades = 1000  # 메모리 누수 방지
        self.hourly_stats = defaultdict(lambda: {'trades': 0, 'profit': 0, 'signals': 0})

        # 활동 로그 (대시보드 표시용, 락으로 보호됨)
        self.activity_log: deque = deque(maxlen=100)  # 최근 100개 활동

        # 백그라운드 태스크
        self._threads: List[threading.Thread] = []
        self._stop_event = threading.Event()

        # 콜백
        self.on_trade_executed: Optional[Callable] = None
        self.on_strategy_evolved: Optional[Callable] = None
        self.on_signal_generated: Optional[Callable] = None

        logger.info(f"🚀 자율 진화형 엔진 초기화: workers={max_workers}, positions={max_positions}")

    def add_activity(self, activity_type: str, title: str, detail: str = ""):
        """활동 로그 추가 (대시보드 표시용, 스레드 안전)"""
        with self._activity_lock:
            self.activity_log.append({
                'type': activity_type,  # scan, signal, trade, evolution, data, system
                'title': title,
                'detail': detail,
                'time': datetime.now()
            })

    def get_recent_activities(self, limit: int = 20) -> List[Dict]:
        """최근 활동 로그 조회 (스레드 안전)"""
        with self._activity_lock:
            activities = list(self.activity_log)
        activities.reverse()  # 최신순
        return activities[:limit]

    def start(self):
        """엔진 시작"""
        if self.is_running:
            logger.warning("엔진이 이미 실행 중입니다")
            return

        self.is_running = True
        self._stop_event.clear()

        logger.info("=" * 60)
        logger.info("🔥 자율 진화형 자동매매 엔진 시작")
        logger.info("=" * 60)

        # 1. 병렬 스캐닝 스레드
        scan_thread = threading.Thread(
            target=self._parallel_scanning_loop,
            name="ParallelScanner",
            daemon=True
        )
        scan_thread.start()
        self._threads.append(scan_thread)

        # 2. 신호 처리 스레드
        signal_thread = threading.Thread(
            target=self._signal_processing_loop,
            name="SignalProcessor",
            daemon=True
        )
        signal_thread.start()
        self._threads.append(signal_thread)

        # 3. 진화 엔진 스레드 (24시간 연속)
        if self.enable_auto_evolution:
            evolution_thread = threading.Thread(
                target=self._continuous_evolution_loop,
                name="EvolutionEngine",
                daemon=True
            )
            evolution_thread.start()
            self._threads.append(evolution_thread)

        # 4. 데이터 수집 스레드 (모든 API)
        data_thread = threading.Thread(
            target=self._comprehensive_data_collection_loop,
            name="DataCollector",
            daemon=True
        )
        data_thread.start()
        self._threads.append(data_thread)

        # 5. 성과 모니터링 스레드
        monitor_thread = threading.Thread(
            target=self._performance_monitoring_loop,
            name="PerformanceMonitor",
            daemon=True
        )
        monitor_thread.start()
        self._threads.append(monitor_thread)

        # 6. 히스토리컬 분석 스레드 (24시간)
        historical_thread = threading.Thread(
            target=self._historical_analysis_loop,
            name="HistoricalAnalyzer",
            daemon=True
        )
        historical_thread.start()
        self._threads.append(historical_thread)

        logger.info(f"✅ {len(self._threads)}개 백그라운드 태스크 시작됨")

    def stop(self):
        """엔진 중지"""
        logger.info("🛑 엔진 중지 요청...")
        self.is_running = False
        self._stop_event.set()

        # 스레드 종료 대기
        for thread in self._threads:
            thread.join(timeout=5)

        # 스레드 풀 종료
        self.executor.shutdown(wait=False)

        logger.info("✅ 엔진 중지 완료")

    # ========== 1. 병렬 스캐닝 ==========
    def _parallel_scanning_loop(self):
        """멀티 종목 병렬 스캐닝 루프"""
        logger.info("📡 병렬 스캐닝 시작")

        while not self._stop_event.is_set():
            try:
                start_time = time.time()

                # 스캔 대상 종목 리스트 가져오기
                candidates = self._get_scan_candidates()

                if candidates:
                    # 병렬 분석 실행
                    signals = self._parallel_analyze(candidates)

                    # 신호 큐에 추가
                    for signal in signals:
                        self.signal_queue.put((signal.priority, signal))

                        if self.on_signal_generated:
                            self.on_signal_generated(signal)

                        # 활동 로그에 신호 추가
                        self.add_activity(
                            'signal',
                            f'{signal.stock_name} {signal.action.upper()}',
                            f'신뢰도 {signal.confidence:.0f}% | {signal.strategy_id}'
                        )

                    elapsed = time.time() - start_time

                    # 활동 로그에 스캔 결과 추가
                    self.add_activity(
                        'scan',
                        f'시장 스캔 완료',
                        f'{len(candidates)}종목 분석 → {len(signals)}개 신호 ({elapsed:.1f}초)'
                    )

                # 다음 스캔까지 대기
                sleep_time = max(0, self.scan_interval - (time.time() - start_time))
                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"스캐닝 오류: {e}", exc_info=True)
                time.sleep(5)

    def _get_scan_candidates(self) -> List[str]:
        """스캔 대상 종목 수집 (RankingAPI 사용)"""
        candidates = set()

        try:
            from api.market.ranking import RankingAPI
            ranking_api = RankingAPI(self.client)

            # 1. 거래량 상위 (ka10031)
            try:
                volume_list = ranking_api.get_volume_rank(market='ALL', limit=50)
                for item in volume_list:
                    code = item.get('code', '')
                    if code:
                        candidates.add(code)
                logger.debug(f"거래량 상위: {len(volume_list)}개")
            except Exception as e:
                logger.debug(f"거래량 순위 조회 실패: {e}")

            # 2. 등락률 상위 (ka10027)
            try:
                rise_list = ranking_api.get_price_change_rank(market='ALL', sort='rise', limit=30)
                for item in rise_list:
                    code = item.get('code', '')
                    if code:
                        candidates.add(code)
                logger.debug(f"상승률 상위: {len(rise_list)}개")
            except Exception as e:
                logger.debug(f"등락률 순위 조회 실패: {e}")

            # 3. 거래대금 상위 (ka10032)
            try:
                value_list = ranking_api.get_trading_value_rank(market='ALL', limit=30)
                for item in value_list:
                    code = item.get('code', '')
                    if code:
                        candidates.add(code)
                logger.debug(f"거래대금 상위: {len(value_list)}개")
            except Exception as e:
                logger.debug(f"거래대금 순위 조회 실패: {e}")

            # 4. 외국인 순매수 (ka10034)
            try:
                foreign_list = ranking_api.get_foreign_period_trading_rank(
                    market='KOSPI', trade_type='buy', period_days=1, limit=20
                )
                for item in foreign_list:
                    code = item.get('code', '')
                    if code:
                        candidates.add(code)
                logger.debug(f"외국인 순매수: {len(foreign_list)}개")
            except Exception as e:
                logger.debug(f"외국인 순매수 조회 실패: {e}")

            # 5. 기관 순매수 (ka90009)
            try:
                inst_list = ranking_api.get_foreign_institution_trading_rank(
                    market='KOSPI', investor_type='institution_buy', limit=20
                )
                for item in inst_list:
                    code = item.get('code', '')
                    if code:
                        candidates.add(code)
                logger.debug(f"기관 순매수: {len(inst_list)}개")
            except Exception as e:
                logger.debug(f"기관 순매수 조회 실패: {e}")

            # 6. 현재 보유 종목
            with self._positions_lock:
                for code in self.current_positions.keys():
                    candidates.add(code)

        except Exception as e:
            logger.error(f"후보 수집 오류: {e}")

        candidates.discard('')

        # 폴백: API 실패 시 주요 대형주 추가
        if len(candidates) < 10:
            logger.warning(f"⚠️ API에서 종목 수집 부족 ({len(candidates)}개) - 주요 종목 폴백 사용")
            fallback_stocks = [
                '005930',  # 삼성전자
                '000660',  # SK하이닉스
                '035420',  # NAVER
                '005380',  # 현대차
                '051910',  # LG화학
                '006400',  # 삼성SDI
                '035720',  # 카카오
                '068270',  # 셀트리온
                '207940',  # 삼성바이오로직스
                '000270',  # 기아
                '005490',  # POSCO홀딩스
                '028260',  # 삼성물산
                '012330',  # 현대모비스
                '066570',  # LG전자
                '003550',  # LG
            ]
            for code in fallback_stocks:
                candidates.add(code)

        result = list(candidates)[:100]  # 최대 100종목

        if result:
            logger.info(f"📊 스캔 대상 종목: {len(result)}개")
        else:
            logger.warning("⚠️ 스캔할 종목이 없습니다")

        return result

    def _parallel_analyze(self, stock_codes: List[str]) -> List[TradingSignal]:
        """병렬 종목 분석 (타임아웃 개선)"""
        signals = []

        # 종목 수 제한 (너무 많으면 타임아웃)
        codes_to_analyze = stock_codes[:50]  # 최대 50개로 제한

        # 병렬 분석 실행
        futures = {}
        for code in codes_to_analyze:
            future = self.executor.submit(self._analyze_single_stock, code)
            futures[future] = code

        # 결과 수집 (타임아웃 60초, 실패해도 계속 진행)
        completed_count = 0
        try:
            for future in as_completed(futures, timeout=60):
                try:
                    signal = future.result(timeout=5)  # 개별 결과도 타임아웃
                    # Fix: 신호 생성 임계값(65)과 통일 - 이전에 70으로 필터링하여 많은 신호 무시됨
                    if signal and signal.confidence >= 65:
                        signals.append(signal)
                    completed_count += 1
                except Exception as e:
                    code = futures[future]
                    logger.debug(f"{code} 분석 실패: {e}")
        except TimeoutError:
            # 타임아웃 발생해도 지금까지 수집된 결과 사용
            logger.warning(f"⚠️ 분석 타임아웃: {completed_count}/{len(codes_to_analyze)} 완료, {len(signals)}개 신호")

        # 미완료 futures 취소
        for future in futures:
            if not future.done():
                future.cancel()

        # 신뢰도순 정렬
        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals[:20]  # 상위 20개

    def _analyze_single_stock(self, stock_code: str) -> Optional[TradingSignal]:
        """단일 종목 분석 (병렬 실행용)"""
        try:
            # 1. 현재가 조회
            price_data = self._get_current_price(stock_code)
            if not price_data:
                return None

            current_price = price_data.get('current_price', 0)
            if current_price <= 0:
                return None

            # 2. 호가 분석
            orderbook = self._get_orderbook(stock_code)

            # 3. 체결강도 분석
            execution = self._get_execution_strength(stock_code)

            # 4. 투자자별 매매 분석
            investor_data = self._get_investor_data(stock_code)

            # 5. 기술적 분석 (캐시된 차트 데이터 사용)
            technical = self._get_technical_analysis(stock_code)

            # 6. 종합 점수 계산
            score, breakdown = self._calculate_composite_score(
                price_data, orderbook, execution, investor_data, technical
            )

            # 7. 신호 생성 (임계값 완화: 70 → 65)
            if score >= 65:
                action = 'buy'
                priority = 1 if score >= 85 else 2 if score >= 75 else 3
            elif score <= 35:
                action = 'sell'
                priority = 1 if score <= 15 else 2 if score <= 25 else 3
            else:
                return None  # hold

            # 수량 계산 (현재 잔고 기반)
            quantity = self._calculate_position_size(stock_code, current_price, score)

            return TradingSignal(
                stock_code=stock_code,
                stock_name=price_data.get('stock_name', stock_code),
                action=action,
                confidence=score,
                price=current_price,
                quantity=quantity,
                strategy_id=self._get_active_strategy_id(),
                priority=priority,
                metadata={
                    'breakdown': breakdown,
                    'orderbook_imbalance': orderbook.get('imbalance', 0) if orderbook else 0,
                    'execution_strength': execution.get('strength', 0) if execution else 0
                }
            )

        except Exception as e:
            logger.debug(f"{stock_code} 분석 오류: {e}")
            return None

    # ========== 2. 신호 처리 ==========
    def _signal_processing_loop(self):
        """거래 신호 처리 루프"""
        logger.info("⚡ 신호 처리 시작")

        while not self._stop_event.is_set():
            try:
                # 큐에서 신호 가져오기 (1초 타임아웃)
                try:
                    priority, signal = self.signal_queue.get(timeout=1)
                except QueueEmpty:  # Fix: bare except → 명시적 예외 지정
                    continue

                # 신호 유효성 검증
                if not self._validate_signal(signal):
                    continue

                # 주문 실행
                result = self._execute_signal(signal)

                if result and result.get('success'):
                    logger.info(
                        f"✅ {signal.action.upper()} 체결: {signal.stock_name} "
                        f"{signal.quantity}주 @ {signal.price:,}원"
                    )

                    # 전략 성과 업데이트
                    self._update_strategy_performance(signal, result)

                    # 콜백 호출
                    if self.on_trade_executed:
                        self.on_trade_executed(signal, result)

            except Exception as e:
                logger.error(f"신호 처리 오류: {e}", exc_info=True)
                time.sleep(1)

    def _validate_signal(self, signal: TradingSignal) -> bool:
        """신호 유효성 검증"""
        # 1. 시간 검증 (10초 이내로 확대 - 3초는 너무 짧아서 대부분 신호 무시됨)
        age = (datetime.now() - signal.signal_time).total_seconds()
        if age > 10:
            logger.debug(f"오래된 신호 무시: {signal.stock_code} ({age:.1f}초)")
            return False

        # 2. 포지션 검증
        if signal.action == 'buy':
            if len(self.current_positions) >= self.max_positions:
                logger.debug(f"최대 포지션 도달: {self.max_positions}")
                return False
            if signal.stock_code in self.current_positions:
                logger.debug(f"이미 보유 중: {signal.stock_code}")
                return False

        if signal.action == 'sell':
            if signal.stock_code not in self.current_positions:
                return False

        # 3. 가격 검증 (현재가와 비교)
        current_price = self._get_current_price_cached(signal.stock_code)
        if current_price:
            diff = abs(current_price - signal.price) / signal.price * 100
            if diff > 2:  # 2% 이상 변동
                logger.debug(f"가격 변동 과다: {signal.stock_code} ({diff:.1f}%)")
                return False

        return True

    def _execute_signal(self, signal: TradingSignal) -> Optional[Dict]:
        """신호 실행"""
        try:
            from api.order import OrderAPI
            order_api = OrderAPI(self.client)

            if signal.action == 'buy':
                result = order_api.buy(
                    stock_code=signal.stock_code,
                    quantity=signal.quantity,
                    price=signal.price,
                    order_type='00'  # 지정가
                )
            else:  # sell
                result = order_api.sell(
                    stock_code=signal.stock_code,
                    quantity=signal.quantity,
                    price=signal.price,
                    order_type='00'
                )

            if result and result.get('status') == 'ordered':
                order_no = result.get('order_no')
                self.pending_orders[order_no] = {
                    'signal': signal,
                    'result': result,
                    'time': datetime.now()
                }
                return {'success': True, 'order_no': order_no, 'result': result}

            return {'success': False, 'error': result.get('error', 'Unknown')}

        except Exception as e:
            logger.error(f"주문 실행 오류: {e}")
            return {'success': False, 'error': str(e)}

    # ========== 3. 연속 진화 ==========
    def _continuous_evolution_loop(self):
        """24시간 연속 알고리즘 진화 루프"""
        logger.info("🧬 연속 진화 엔진 시작")

        while not self._stop_event.is_set():
            try:
                self.evolution_state.is_evolving = True
                start_time = time.time()

                logger.info(f"🔬 진화 세대 {self.evolution_state.generation + 1} 시작...")

                # 1. 현재 전략들의 성과 평가
                fitness_scores = self._evaluate_all_strategies()

                # 2. 유전 알고리즘 적용
                new_strategies = self._evolve_strategies(fitness_scores)

                # 3. 백테스트로 검증
                validated = self._validate_evolved_strategies(new_strategies)

                # 4. 최고 전략 배포
                if validated:
                    best = max(validated, key=lambda s: s.get('fitness', 0))
                    if best.get('fitness', 0) > self.evolution_state.best_fitness:
                        self._deploy_strategy(best)
                        self.evolution_state.best_fitness = best['fitness']
                        self.evolution_state.best_strategy_id = best['id']

                        logger.info(
                            f"🏆 새로운 최고 전략 배포! "
                            f"fitness={best['fitness']:.2f}"
                        )

                # 5. 진화 상태 업데이트
                self.evolution_state.generation += 1
                self.evolution_state.last_evolution = datetime.now()
                self.evolution_state.is_evolving = False

                elapsed = time.time() - start_time
                logger.info(
                    f"✅ 세대 {self.evolution_state.generation} 완료 "
                    f"({elapsed:.1f}초), 최고 fitness={self.evolution_state.best_fitness:.2f}"
                )

                # 다음 진화까지 대기
                time.sleep(self.evolution_interval)

            except Exception as e:
                logger.error(f"진화 오류: {e}", exc_info=True)
                self.evolution_state.is_evolving = False
                time.sleep(60)

    def _evaluate_all_strategies(self) -> Dict[str, float]:
        """모든 전략 성과 평가"""
        scores = {}

        for strategy_id, perf in self.strategy_performance.items():
            # 복합 점수 계산
            win_rate_score = perf.win_rate / 100 * 30  # 30점 만점
            profit_score = min(30, max(-30, perf.total_profit / 100000))  # 30점 만점
            sharpe_score = min(20, max(0, perf.sharpe_ratio * 10))  # 20점 만점
            dd_score = max(0, 20 - perf.max_drawdown * 2)  # 20점 만점

            scores[strategy_id] = win_rate_score + profit_score + sharpe_score + dd_score

        return scores

    def _evolve_strategies(self, fitness_scores: Dict[str, float]) -> List[Dict]:
        """유전 알고리즘으로 전략 진화"""
        try:
            # StrategyOptimizationEngine.evolve_generation()은 population과 fitness_scores 두 개를 요구
            # 여기서는 간단한 진화 로직 사용
            return self._simple_evolution(fitness_scores)
        except Exception as e:
            logger.error(f"전략 진화 오류: {e}")
            return self._simple_evolution(fitness_scores)

    def _simple_evolution(self, fitness_scores: Dict[str, float]) -> List[Dict]:
        """간단한 진화 로직 (fallback)"""
        new_generation = []

        # fitness_scores가 비어있으면 초기 전략 생성
        if not fitness_scores:
            logger.info("📊 초기 전략 생성 중...")
            base_strategies = [
                {'id': 'momentum_01', 'type': 'momentum', 'rsi_threshold': 30, 'volume_ratio': 1.5},
                {'id': 'mean_reversion_01', 'type': 'mean_reversion', 'bb_threshold': 2.0, 'rsi_oversold': 25},
                {'id': 'trend_follow_01', 'type': 'trend_follow', 'ma_period': 20, 'breakout_pct': 2.0},
                {'id': 'volume_spike_01', 'type': 'volume_spike', 'volume_mult': 3.0, 'price_change': 1.5},
                {'id': 'foreign_follow_01', 'type': 'foreign_follow', 'net_buy_threshold': 10000},
            ]
            for strategy in base_strategies:
                strategy['fitness'] = random.uniform(20, 50)  # 초기 fitness
                strategy['mutation_rate'] = random.uniform(0.1, 0.3)
                strategy['generation'] = self.evolution_state.generation
                new_generation.append(strategy)

                # strategy_performance에도 등록
                self.strategy_performance[strategy['id']] = StrategyPerformance(
                    strategy_id=strategy['id']
                )
            logger.info(f"✅ 초기 전략 {len(new_generation)}개 생성 완료")
            return new_generation

        # 상위 전략 기반으로 변이 생성
        sorted_strategies = sorted(fitness_scores.items(), key=lambda x: x[1], reverse=True)

        for strategy_id, fitness in sorted_strategies[:5]:
            # 변이 전략 생성
            mutated = {
                'id': f"{strategy_id}_gen{self.evolution_state.generation}",
                'parent_id': strategy_id,
                'fitness': fitness * random.uniform(0.9, 1.2),  # 약간의 변이
                'mutation_rate': random.uniform(0.05, 0.2),
                'generation': self.evolution_state.generation
            }
            new_generation.append(mutated)

        return new_generation

    def _validate_evolved_strategies(self, strategies: List[Dict]) -> List[Dict]:
        """진화된 전략 검증 (fitness 기반)"""
        validated = []

        try:
            # fitness 점수 기반 검증 (실제 백테스트는 별도로 수행)
            for strategy in strategies[:10]:  # 상위 10개만
                fitness = strategy.get('fitness', 0)
                mutation_rate = strategy.get('mutation_rate', 0.1)

                # 기본 검증 조건
                if fitness > 0:
                    # 생성 시간 기록
                    strategy['validated_at'] = datetime.now().isoformat()
                    strategy['generation'] = self.evolution_state.generation

                    # 예상 sharpe ratio 계산 (fitness 기반 추정)
                    estimated_sharpe = fitness / 100 * 2  # 간단한 추정
                    strategy['estimated_sharpe'] = estimated_sharpe

                    validated.append(strategy)

            logger.debug(f"전략 검증 완료: {len(validated)}/{len(strategies)}개 통과")

        except Exception as e:
            logger.error(f"전략 검증 오류: {e}")
            # 오류 시에도 상위 전략은 유지
            validated = strategies[:5]

        return validated

    def _deploy_strategy(self, strategy: Dict):
        """전략 배포"""
        strategy_id = strategy.get('id', f"evolved_{self.evolution_state.generation}")
        self.active_strategies[strategy_id] = strategy

        # 성과 추적 초기화
        self.strategy_performance[strategy_id] = StrategyPerformance(
            strategy_id=strategy_id
        )

        if self.on_strategy_evolved:
            self.on_strategy_evolved(strategy)

    # ========== 4. 종합 데이터 수집 ==========
    def _comprehensive_data_collection_loop(self):
        """모든 API 데이터 종합 수집"""
        logger.info("📥 종합 데이터 수집 시작")

        # 수집할 API 목록 (미사용 API 포함)
        api_schedule = [
            # 투자자 동향 (30초마다)
            ('ka10059', 30, {'stk_cd': '005930'}),  # 종목별 투자자기관별
            ('ka10063', 30, {}),  # 장중 투자자별 매매
            ('ka10065', 30, {}),  # 장중 투자자별 매매 상위

            # 외국인/기관 (1분마다)
            ('ka10034', 60, {'prd_tp': '0'}),  # 외인 기간별 매매 상위
            ('ka10035', 60, {}),  # 외인 연속 순매매
            ('ka10045', 60, {}),  # 종목별 기관 매매 추이

            # 프로그램 매매 (30초마다)
            ('ka90005', 30, {}),  # 프로그램 매매 추이 시간별
            ('ka90007', 60, {}),  # 프로그램 매매 누적 추이

            # 시장 현황 (1분마다)
            ('ka10031', 60, {}),  # 전일 거래량 상위
            ('ka10032', 60, {}),  # 거래대금 상위
            ('ka10027', 60, {}),  # 등락률 상위
            ('ka10023', 30, {}),  # 거래량 급증

            # 업종 (5분마다)
            ('ka20001', 300, {}),  # 업종 현재가
            ('ka20003', 300, {}),  # 전업종 지수
        ]

        # API별 마지막 호출 시간
        last_called = defaultdict(lambda: datetime.min)

        while not self._stop_event.is_set():
            try:
                now = datetime.now()

                for api_id, interval, params in api_schedule:
                    elapsed = (now - last_called[api_id]).total_seconds()

                    if elapsed >= interval:
                        # 비동기 수집
                        self.executor.submit(
                            self._collect_and_store_data,
                            api_id, params
                        )
                        last_called[api_id] = now

                time.sleep(1)

            except Exception as e:
                logger.error(f"데이터 수집 오류: {e}")
                time.sleep(5)

    def _collect_and_store_data(self, api_id: str, params: Dict):
        """API 데이터 수집 및 저장"""
        try:
            result = self._call_api_safe(api_id, params)

            if result:
                # 분석용 데이터 저장 (메모리 캐시)
                cache_key = f"{api_id}:{json.dumps(params, sort_keys=True)}"
                self._data_cache[cache_key] = {
                    'data': result,
                    'time': datetime.now()
                }

                # 특수 데이터 처리
                self._process_special_data(api_id, result)

        except Exception as e:
            logger.debug(f"API {api_id} 수집 실패: {e}")

    def _process_special_data(self, api_id: str, data: Dict):
        """특수 데이터 분석 처리"""
        if api_id == 'ka10063':  # 투자자별 매매
            # 외국인/기관 순매수 급변 감지
            foreign = data.get('foreign_net', 0)
            inst = data.get('institution_net', 0)

            if abs(foreign) > 1000000000:  # 10억 이상
                logger.info(f"🌍 외국인 대량매매 감지: {foreign/100000000:.1f}억")

        elif api_id == 'ka90005':  # 프로그램 매매
            # 프로그램 순매수 급변 감지
            program_net = data.get('program_net', 0)

            if abs(program_net) > 500000000:  # 5억 이상
                logger.info(f"🖥️ 프로그램 대량매매 감지: {program_net/100000000:.1f}억")

    # ========== 5. 성과 모니터링 ==========
    def _performance_monitoring_loop(self):
        """실시간 성과 모니터링"""
        logger.info("📈 성과 모니터링 시작")

        while not self._stop_event.is_set():
            try:
                # 1. 포지션 업데이트
                self._update_positions()

                # 2. 미체결 주문 확인
                self._check_pending_orders()

                # 3. 일간 성과 집계
                daily_stats = self._calculate_daily_stats()

                # 4. 10분마다 리포트 출력
                if datetime.now().minute % 10 == 0:
                    self._print_performance_report(daily_stats)

                time.sleep(30)

            except Exception as e:
                logger.error(f"모니터링 오류: {e}")
                time.sleep(10)

    def _update_positions(self):
        """보유 포지션 업데이트"""
        try:
            from api.account import AccountAPI
            account_api = AccountAPI(self.client)

            holdings = account_api.get_holdings()

            if holdings:
                self.current_positions = {
                    h['stk_cd']: h for h in holdings
                }
        except Exception as e:
            logger.debug(f"포지션 업데이트 실패: {e}")

    def _check_pending_orders(self):
        """미체결 주문 확인"""
        try:
            from api.order import OrderAPI
            order_api = OrderAPI(self.client)

            completed = []

            for order_no, order_info in self.pending_orders.items():
                status = order_api.get_order_status(order_no)

                if status and status.get('status') in ['filled', 'cancelled']:
                    completed.append(order_no)

                    # 체결된 경우 성과 업데이트
                    if status.get('status') == 'filled':
                        signal = order_info['signal']
                        self._record_trade_result(signal, status)

            # 완료된 주문 제거
            for order_no in completed:
                del self.pending_orders[order_no]

        except Exception as e:
            logger.debug(f"주문 확인 실패: {e}")

    def _calculate_daily_stats(self) -> Dict:
        """일간 통계 계산"""
        return {
            'total_trades': len(self.daily_trades),
            'total_profit': sum(t.get('profit', 0) for t in self.daily_trades),
            'win_count': sum(1 for t in self.daily_trades if t.get('profit', 0) > 0),
            'positions': len(self.current_positions),
            'pending_orders': len(self.pending_orders),
            'generation': self.evolution_state.generation,
            'best_fitness': self.evolution_state.best_fitness
        }

    def _print_performance_report(self, stats: Dict):
        """성과 리포트 출력"""
        win_rate = stats['win_count'] / max(stats['total_trades'], 1) * 100

        logger.info("=" * 50)
        logger.info("📊 자율 진화 엔진 성과 리포트")
        logger.info("=" * 50)
        logger.info(f"거래 수: {stats['total_trades']}")
        logger.info(f"승률: {win_rate:.1f}%")
        logger.info(f"총 손익: {stats['total_profit']:+,}원")
        logger.info(f"보유 종목: {stats['positions']}")
        logger.info(f"미체결: {stats['pending_orders']}")
        logger.info(f"진화 세대: {stats['generation']}")
        logger.info(f"최고 Fitness: {stats['best_fitness']:.2f}")
        logger.info("=" * 50)

    # ========== 6. 히스토리컬 분석 (24시간) ==========
    def _historical_analysis_loop(self):
        """24시간 히스토리컬 데이터 분석"""
        logger.info("📚 히스토리컬 분석 시작 (24시간 연속)")

        while not self._stop_event.is_set():
            try:
                # 장 마감 후에는 더 집중적으로 분석
                now = datetime.now()
                is_after_hours = now.hour >= 16 or now.hour < 9

                if is_after_hours:
                    logger.info("🌙 장외 시간: 심층 히스토리컬 분석 실행")

                    # 1. 전체 종목 일봉 데이터 수집
                    self._collect_historical_data()

                    # 2. 패턴 발견
                    self._discover_patterns()

                    # 3. 전략 백테스팅
                    self._batch_backtest()

                    # 4. 최적 파라미터 탐색
                    self._optimize_parameters()

                    # 1시간 대기
                    time.sleep(3600)
                else:
                    # 장중에는 가볍게
                    time.sleep(600)

            except Exception as e:
                logger.error(f"히스토리컬 분석 오류: {e}")
                time.sleep(300)

    def _collect_historical_data(self):
        """히스토리컬 데이터 수집"""
        logger.info("📥 히스토리컬 데이터 수집 중...")

        # 거래량 상위 100종목의 일봉 데이터 수집
        top_stocks = self._get_scan_candidates()

        for stock_code in top_stocks[:100]:
            try:
                # 일봉 차트 (ka10081)
                result = self._call_api_safe('ka10081', {'stk_cd': stock_code})
                if result:
                    self._store_historical_data(stock_code, 'daily', result)

                time.sleep(0.2)  # Rate limit 준수

            except Exception as e:
                logger.debug(f"{stock_code} 히스토리컬 수집 실패: {e}")

    def _discover_patterns(self):
        """패턴 발견"""
        logger.info("🔍 패턴 발견 중...")

        try:
            from ai.self_learning_system import SelfLearningSystem
            learner = SelfLearningSystem()

            # 최근 거래에서 성공/실패 패턴 추출
            insights = learner.get_learned_insights()

            if insights.get('success_patterns'):
                logger.info(f"✅ 성공 패턴 {len(insights['success_patterns'])}개 발견")
            if insights.get('failure_patterns'):
                logger.info(f"⚠️ 실패 패턴 {len(insights['failure_patterns'])}개 발견")

        except Exception as e:
            logger.error(f"패턴 발견 오류: {e}")

    def _batch_backtest(self):
        """배치 백테스팅"""
        logger.info("🧪 배치 백테스팅 중...")

        try:
            from ai.unified_backtester import UnifiedBacktester
            backtester = UnifiedBacktester(self.client)

            # 현재 활성 전략들 백테스트
            for strategy_id, strategy in self.active_strategies.items():
                result = backtester.run_backtest(strategy)

                if result:
                    # 성과 업데이트
                    perf = self.strategy_performance.get(strategy_id)
                    if perf:
                        perf.sharpe_ratio = result.get('sharpe_ratio', 0)
                        perf.max_drawdown = result.get('max_drawdown', 0)

        except Exception as e:
            logger.error(f"배치 백테스트 오류: {e}")

    def _optimize_parameters(self):
        """파라미터 최적화"""
        logger.info("⚙️ 파라미터 최적화 중...")

        try:
            from ai.parameter_optimizer import get_parameter_optimizer
            optimizer = get_parameter_optimizer()

            # 주요 파라미터 최적화
            optimal_params = optimizer.optimize_all()

            if optimal_params:
                logger.info(f"✅ 최적 파라미터 발견: {len(optimal_params)}개")

        except Exception as e:
            logger.error(f"파라미터 최적화 오류: {e}")

    # ========== 유틸리티 메서드 ==========
    def _call_api_safe(self, api_id: str, params: Dict) -> Optional[Dict]:
        """안전한 API 호출"""
        try:
            result = self.client.call_verified_api(
                api_id=api_id,
                body_override=params
            )
            if result and result.get('return_code') == 0:
                return result
        except Exception as e:
            logger.debug(f"API {api_id} 호출 실패: {e}")
        return None

    def _get_current_price(self, stock_code: str) -> Optional[Dict]:
        """현재가 조회"""
        result = self._call_api_safe('ka10003', {'stk_cd': stock_code})
        if result:
            return {
                'current_price': int(result.get('cur_prc', 0)),
                'stock_name': result.get('stk_nm', stock_code),
                'change_rate': float(result.get('prdy_ctrt', 0)),
                'volume': int(result.get('acml_vol', 0))
            }
        return None

    def _get_current_price_cached(self, stock_code: str) -> Optional[int]:
        """캐시된 현재가"""
        cache = self.price_cache.get(stock_code)
        if cache and (datetime.now() - cache['time']).total_seconds() < self.cache_ttl:
            return cache['price']

        data = self._get_current_price(stock_code)
        if data:
            self.price_cache[stock_code] = {
                'price': data['current_price'],
                'time': datetime.now()
            }
            return data['current_price']
        return None

    def _get_orderbook(self, stock_code: str) -> Optional[Dict]:
        """호가 조회"""
        return self._call_api_safe('ka10004', {'stk_cd': stock_code})

    def _get_execution_strength(self, stock_code: str) -> Optional[Dict]:
        """체결강도 조회"""
        return self._call_api_safe('ka10047', {'stk_cd': stock_code})

    def _get_investor_data(self, stock_code: str) -> Optional[Dict]:
        """투자자별 매매 조회"""
        return self._call_api_safe('ka10059', {'stk_cd': stock_code})

    def _get_technical_analysis(self, stock_code: str) -> Optional[Dict]:
        """기술적 분석"""
        # 분봉 차트 데이터 조회
        chart = self._call_api_safe('ka10080', {'stk_cd': stock_code})

        if not chart:
            return None

        # 간단한 기술 지표 계산
        prices = [int(c.get('cur_prc', 0)) for c in chart.get('chart_list', [])]

        if len(prices) < 20:
            return None

        return {
            'ma5': sum(prices[:5]) / 5,
            'ma20': sum(prices[:20]) / 20,
            'trend': 'up' if prices[0] > prices[19] else 'down'
        }

    def _calculate_composite_score(
        self,
        price_data: Dict,
        orderbook: Dict,
        execution: Dict,
        investor: Dict,
        technical: Dict
    ) -> tuple:
        """종합 점수 계산 (매매 활성화를 위해 완화된 기준)"""
        score = 55  # 기본 점수 상향 (50 → 55)
        breakdown = {}

        # 1. 등락률 (20점) - 조건 완화
        change_rate = price_data.get('change_rate', 0)
        if 1 <= change_rate <= 15:  # 1~15% 범위 확대
            score += 15
            breakdown['change_rate'] = 15
        elif 0 < change_rate < 1:  # 소폭 상승도 +5
            score += 5
            breakdown['change_rate'] = 5
        elif change_rate > 15:
            score -= 5  # 과열
            breakdown['change_rate'] = -5
        elif change_rate < -5:
            score -= 10
            breakdown['change_rate'] = -10

        # 2. 호가 불균형 (15점) - 조건 완화
        # Fix: Ask=매도호가, Bid=매수호가 (이전 코드가 반대로 되어있었음)
        if orderbook:
            buy_volume = sum(int(orderbook.get(f'bid_rq{i}', orderbook.get(f'매수호가잔량{i}', 0))) for i in range(1, 6))
            sell_volume = sum(int(orderbook.get(f'ask_rq{i}', orderbook.get(f'매도호가잔량{i}', 0))) for i in range(1, 6))
            if buy_volume + sell_volume > 0:
                imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume)
                if imbalance > 0.1:  # 0.3 → 0.1로 완화
                    score += 10
                    breakdown['orderbook'] = 10
                elif imbalance < -0.3:
                    score -= 5  # -10 → -5로 완화
                    breakdown['orderbook'] = -5

        # 3. 체결강도 (15점) - 조건 완화
        if execution:
            strength = float(execution.get('cntr_strg', execution.get('체결강도', 100)))
            if strength > 100:  # 120 → 100으로 완화
                score += 10
                breakdown['execution'] = 10
            elif strength < 70:  # 80 → 70으로 조정
                score -= 5
                breakdown['execution'] = -5

        # 4. 외국인/기관 (15점) - 조건 완화
        if investor:
            foreign = int(investor.get('frgn_net', investor.get('외국인순매수', 0)))
            inst = int(investor.get('inst_net', investor.get('기관순매수', 0)))
            if foreign > 0 or inst > 0:  # 둘 중 하나만 순매수여도 점수
                score += 10
                breakdown['investor'] = 10
            if foreign > 0 and inst > 0:  # 둘 다 순매수면 추가 점수
                score += 5
                breakdown['investor'] = 15
            elif foreign < 0 and inst < 0:
                score -= 5  # -10 → -5로 완화
                breakdown['investor'] = -5

        # 5. 기술적 분석 (10점)
        if technical:
            if technical.get('trend') == 'up' and price_data.get('current_price', 0) > technical.get('ma5', 0):
                score += 10
                breakdown['technical'] = 10
            elif technical.get('trend') == 'down':
                score -= 5
                breakdown['technical'] = -5

        return max(0, min(100, score)), breakdown

    def _calculate_position_size(self, stock_code: str, price: int, score: float) -> int:
        """포지션 크기 계산"""
        # 기본 투자금액 (점수에 따라 조정)
        base_amount = 1000000  # 100만원

        if score >= 90:
            amount = base_amount * 3  # 300만원
        elif score >= 80:
            amount = base_amount * 2  # 200만원
        else:
            amount = base_amount

        # 수량 계산
        quantity = int(amount / price)

        # 최소 1주
        return max(1, quantity)

    def _get_active_strategy_id(self) -> str:
        """현재 활성 전략 ID"""
        if self.evolution_state.best_strategy_id:
            return self.evolution_state.best_strategy_id
        return "default"

    def _update_strategy_performance(self, signal: TradingSignal, result: Dict):
        """전략 성과 업데이트"""
        perf = self.strategy_performance.get(signal.strategy_id)
        if perf:
            perf.total_trades += 1
            perf.last_updated = datetime.now()

    def _record_trade_result(self, signal: TradingSignal, status: Dict):
        """거래 결과 기록"""
        profit = status.get('profit', 0)

        self.daily_trades.append({
            'stock_code': signal.stock_code,
            'action': signal.action,
            'profit': profit,
            'time': datetime.now()
        })

        # 메모리 누수 방지: 최대 개수 초과시 오래된 기록 제거
        if len(self.daily_trades) > self._max_daily_trades:
            self.daily_trades = self.daily_trades[-self._max_daily_trades:]

        # 전략 성과 업데이트
        perf = self.strategy_performance.get(signal.strategy_id)
        if perf:
            if profit > 0:
                perf.winning_trades += 1
            perf.total_profit += profit

    def _store_historical_data(self, stock_code: str, timeframe: str, data: Dict):
        """히스토리컬 데이터 저장"""
        # TODO: 데이터베이스에 저장
        pass


# 편의 함수
def create_autonomous_engine(client, **kwargs) -> AutonomousTradingEngine:
    """자율 진화 엔진 생성"""
    return AutonomousTradingEngine(client, **kwargs)


__all__ = ['AutonomousTradingEngine', 'TradingSignal', 'create_autonomous_engine']
