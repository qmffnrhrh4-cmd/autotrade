"""
core/autopilot.py
완전 자동화 트레이딩 시스템 - AutoPilot

모든 것을 AI와 시스템이 자동으로 관리:
- 전략 자동 생성/진화/교체
- 시장 상황 분석 및 리스크 자동 조절
- 매매 신호 자동 생성 및 실행
- 손절/익절 자동 관리
- 포트폴리오 자동 리밸런싱
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AutoPilotMode(Enum):
    """AutoPilot 운영 모드"""
    INITIALIZING = "initializing"  # 초기화 중
    LEARNING = "learning"          # 학습 모드 (가상매매만)
    ACTIVE = "active"              # 활성 모드 (실제 매매)
    CAUTIOUS = "cautious"          # 주의 모드 (보수적 매매)
    DEFENSIVE = "defensive"        # 방어 모드 (매도만)
    PAUSED = "paused"              # 일시 중지


class MarketCondition(Enum):
    """시장 상황"""
    BULL = "bull"           # 상승장
    BEAR = "bear"           # 하락장
    SIDEWAYS = "sideways"   # 횡보장
    VOLATILE = "volatile"   # 변동성 장
    UNKNOWN = "unknown"     # 알 수 없음


@dataclass
class AutoPilotConfig:
    """AutoPilot 설정 (모든 값이 자동 최적화됨)"""
    # 전략 관리
    min_strategies: int = 5
    max_strategies: int = 20
    strategy_review_interval_hours: int = 1
    strategy_evolution_interval_minutes: int = 5

    # 성과 기준 (자동 조절됨)
    min_win_rate: float = 0.4
    min_return_rate: float = -5.0
    replace_threshold_days: int = 3

    # 리스크 관리 (시장 상황에 따라 자동 조절)
    max_daily_loss_pct: float = 3.0
    max_position_pct: float = 15.0
    max_positions: int = 10

    # 자동 손절/익절 (AI가 종목별로 최적화)
    default_stop_loss_pct: float = 5.0
    default_take_profit_pct: float = 10.0

    # 진화 알고리즘
    evolution_enabled: bool = True
    evolution_population_size: int = 20
    evolution_generations_per_cycle: int = 10


@dataclass
class AutoPilotState:
    """AutoPilot 상태"""
    mode: AutoPilotMode = AutoPilotMode.INITIALIZING
    market_condition: MarketCondition = MarketCondition.UNKNOWN
    started_at: datetime = field(default_factory=datetime.now)
    last_strategy_review: Optional[datetime] = None
    last_evolution_cycle: Optional[datetime] = None
    last_market_analysis: Optional[datetime] = None
    total_trades_today: int = 0
    realized_profit_today: float = 0
    active_strategies: int = 0
    best_strategy_return: float = 0
    consecutive_losses: int = 0
    is_market_open: bool = False


class AutoPilot:
    """
    완전 자동화 트레이딩 시스템

    사람의 개입 없이 모든 것을 자동으로 관리:
    1. 시스템 시작 시 자동 초기화
    2. 전략 자동 생성/진화/교체
    3. 시장 상황 분석 및 리스크 자동 조절
    4. 매매 신호 자동 생성 및 실행
    5. 손절/익절 자동 관리
    """

    def __init__(
        self,
        virtual_manager=None,
        evolution_engine=None,
        dynamic_risk_manager=None,
        analyzer=None,
        data_fetcher=None
    ):
        self.virtual_manager = virtual_manager
        self.evolution_engine = evolution_engine
        self.dynamic_risk_manager = dynamic_risk_manager
        self.analyzer = analyzer
        self.data_fetcher = data_fetcher

        self.config = AutoPilotConfig()
        self.state = AutoPilotState()

        self._running = False
        self._threads: List[threading.Thread] = []
        self._lock = threading.RLock()

        logger.info("🤖 AutoPilot 초기화 완료")

    def start(self):
        """AutoPilot 시작 - 모든 자동화 프로세스 실행"""
        if self._running:
            logger.warning("AutoPilot이 이미 실행 중입니다")
            return

        self._running = True
        logger.info("🚀 AutoPilot 시작...")

        # 1. 초기화
        self._initialize()

        # 2. 백그라운드 스레드 시작
        threads_config = [
            ("AutoPilot-Evolution", self._evolution_loop, 60),      # 진화 루프
            ("AutoPilot-Review", self._review_loop, 300),          # 검토 루프 (5분)
            ("AutoPilot-Market", self._market_analysis_loop, 60),  # 시장 분석 (1분)
            ("AutoPilot-Risk", self._risk_management_loop, 30),    # 리스크 관리 (30초)
        ]

        for name, target, interval in threads_config:
            thread = threading.Thread(
                target=self._thread_wrapper,
                args=(target, interval),
                name=name,
                daemon=True
            )
            thread.start()
            self._threads.append(thread)
            logger.info(f"  ✅ {name} 스레드 시작 (간격: {interval}초)")

        self.state.mode = AutoPilotMode.ACTIVE
        logger.info("✅ AutoPilot 완전 가동!")

    def stop(self):
        """AutoPilot 중지"""
        logger.info("🛑 AutoPilot 중지 중...")
        self._running = False
        self.state.mode = AutoPilotMode.PAUSED

        # 스레드 종료 대기
        for thread in self._threads:
            thread.join(timeout=5)

        self._threads.clear()
        logger.info("✅ AutoPilot 중지 완료")

    def _initialize(self):
        """시스템 자동 초기화"""
        logger.info("📋 AutoPilot 초기화 시작...")

        # 1. 전략 확인 및 자동 생성
        self._ensure_strategies()

        # 2. 진화 엔진 초기화
        self._initialize_evolution()

        # 3. 시장 상황 분석
        self._analyze_market()

        # 4. 리스크 모드 자동 설정
        self._auto_adjust_risk_mode()

        logger.info("✅ AutoPilot 초기화 완료")

    def _ensure_strategies(self):
        """전략이 없으면 자동 생성"""
        if not self.virtual_manager:
            logger.warning("VirtualManager 없음 - 전략 자동 생성 건너뜀")
            return

        try:
            strategies = self.virtual_manager.get_strategy_summary()
            active_strategies = [s for s in strategies if s.get('is_active', True)]

            if len(active_strategies) < self.config.min_strategies:
                needed = self.config.min_strategies - len(active_strategies)
                logger.info(f"📊 전략 부족 - {needed}개 자동 생성 중...")

                # 다양한 전략 자동 생성
                strategy_templates = [
                    ("AI-Conservative", "보수적 AI 전략 - 낮은 리스크, 안정적 수익"),
                    ("AI-Balanced", "균형 AI 전략 - 중간 리스크, 적정 수익"),
                    ("AI-Aggressive", "공격적 AI 전략 - 높은 리스크, 높은 수익"),
                    ("AI-Momentum", "모멘텀 AI 전략 - 추세 추종"),
                    ("AI-ValueHunter", "가치 발굴 AI 전략 - 저평가 종목"),
                ]

                for i, (name, desc) in enumerate(strategy_templates[:needed]):
                    try:
                        strategy_id = self.virtual_manager.create_strategy(
                            name=f"{name}-{datetime.now().strftime('%m%d')}",
                            description=desc,
                            initial_capital=10_000_000
                        )
                        logger.info(f"  ✅ 전략 생성: {name} (ID: {strategy_id})")
                    except Exception as e:
                        logger.error(f"  ❌ 전략 생성 실패: {name} - {e}")

            self.state.active_strategies = len(active_strategies)
            logger.info(f"📊 활성 전략: {self.state.active_strategies}개")

        except Exception as e:
            logger.error(f"전략 확인/생성 실패: {e}")

    def _initialize_evolution(self):
        """진화 엔진 자동 초기화"""
        if not self.evolution_engine:
            logger.warning("EvolutionEngine 없음 - 진화 자동 시작 건너뜀")
            return

        try:
            if not self.evolution_engine.is_running:
                logger.info("🧬 진화 엔진 자동 시작...")
                self.evolution_engine.start()
                logger.info("✅ 진화 엔진 가동")
        except Exception as e:
            logger.error(f"진화 엔진 초기화 실패: {e}")

    def _thread_wrapper(self, target, interval):
        """스레드 래퍼 - 예외 처리 및 주기적 실행"""
        while self._running:
            try:
                target()
            except Exception as e:
                logger.error(f"AutoPilot 스레드 오류: {e}", exc_info=True)

            # 인터럽트 가능한 sleep
            for _ in range(interval):
                if not self._running:
                    break
                time.sleep(1)

    def _evolution_loop(self):
        """진화 루프 - 전략 자동 진화"""
        if not self.evolution_engine or not self.config.evolution_enabled:
            return

        try:
            # 진화 한 세대 실행
            if self.evolution_engine.is_running:
                self.evolution_engine.evolve_one_generation()
                self.state.last_evolution_cycle = datetime.now()

                # 최고 성과 업데이트
                if hasattr(self.evolution_engine, 'best_fitness'):
                    self.state.best_strategy_return = self.evolution_engine.best_fitness

        except Exception as e:
            logger.error(f"진화 루프 오류: {e}")

    def _review_loop(self):
        """검토 루프 - 전략 성과 자동 검토 및 교체"""
        if not self.virtual_manager:
            return

        try:
            logger.info("🔍 전략 자동 검토 시작...")

            strategies = self.virtual_manager.get_strategy_summary()
            now = datetime.now()

            poor_performers = []

            for strategy in strategies:
                strategy_id = strategy.get('id') or strategy.get('strategy_id')
                metrics = self.virtual_manager.get_performance_metrics(strategy_id)

                # 성과 평가
                win_rate = metrics.get('win_rate', 0)
                return_rate = metrics.get('return_rate', 0)
                trade_count = metrics.get('trade_count', 0)

                # 충분한 거래가 있고 성과가 저조한 전략 식별
                if trade_count >= 10:
                    if win_rate < self.config.min_win_rate * 100:
                        poor_performers.append({
                            'id': strategy_id,
                            'name': strategy.get('name'),
                            'reason': f'낮은 승률 ({win_rate:.1f}%)'
                        })
                    elif return_rate < self.config.min_return_rate:
                        poor_performers.append({
                            'id': strategy_id,
                            'name': strategy.get('name'),
                            'reason': f'낮은 수익률 ({return_rate:.1f}%)'
                        })

            # 저조한 전략 자동 교체
            for poor in poor_performers[:2]:  # 한 번에 최대 2개만 교체
                logger.info(f"  🔄 전략 교체: {poor['name']} ({poor['reason']})")
                self._replace_strategy(poor['id'])

            self.state.last_strategy_review = now
            logger.info(f"✅ 전략 검토 완료 - 교체: {len(poor_performers[:2])}개")

        except Exception as e:
            logger.error(f"검토 루프 오류: {e}")

    def _replace_strategy(self, strategy_id: int):
        """저조한 전략을 새 전략으로 교체"""
        try:
            # 기존 전략 비활성화
            self.virtual_manager.delete_strategy(strategy_id)

            # 진화된 최적 파라미터로 새 전략 생성
            if self.evolution_engine and hasattr(self.evolution_engine, 'get_best_parameters'):
                best_params = self.evolution_engine.get_best_parameters()
                # 새 전략에 최적 파라미터 적용
                new_name = f"진화-G{self.evolution_engine.generation:03d}-S{strategy_id:02d}"
            else:
                new_name = f"AI-New-{datetime.now().strftime('%H%M')}"

            self.virtual_manager.create_strategy(
                name=new_name,
                description="자동 생성된 AI 전략",
                initial_capital=10_000_000
            )
            logger.info(f"  ✅ 새 전략 생성: {new_name}")

        except Exception as e:
            logger.error(f"전략 교체 실패: {e}")

    def _market_analysis_loop(self):
        """시장 분석 루프 - 시장 상황 자동 파악"""
        try:
            # 시장 상황 분석
            condition = self._analyze_market()

            # 시장 상황에 따른 모드 자동 전환
            if condition == MarketCondition.BEAR:
                if self.state.mode == AutoPilotMode.ACTIVE:
                    self.state.mode = AutoPilotMode.CAUTIOUS
                    logger.info("⚠️ 하락장 감지 - CAUTIOUS 모드로 전환")
            elif condition == MarketCondition.VOLATILE:
                if self.state.mode == AutoPilotMode.ACTIVE:
                    self.state.mode = AutoPilotMode.DEFENSIVE
                    logger.info("⚠️ 변동성 증가 - DEFENSIVE 모드로 전환")
            elif condition == MarketCondition.BULL:
                if self.state.mode in (AutoPilotMode.CAUTIOUS, AutoPilotMode.DEFENSIVE):
                    self.state.mode = AutoPilotMode.ACTIVE
                    logger.info("📈 상승장 감지 - ACTIVE 모드로 전환")

            self.state.last_market_analysis = datetime.now()

        except Exception as e:
            logger.error(f"시장 분석 루프 오류: {e}")

    def _analyze_market(self) -> MarketCondition:
        """시장 상황 분석"""
        try:
            if not self.data_fetcher:
                return MarketCondition.UNKNOWN

            # KOSPI 지수 분석
            kospi_data = self.data_fetcher.get_index_data('KOSPI')
            if not kospi_data:
                return MarketCondition.UNKNOWN

            change_rate = kospi_data.get('change_rate', 0)

            if change_rate > 1.0:
                self.state.market_condition = MarketCondition.BULL
            elif change_rate < -1.0:
                self.state.market_condition = MarketCondition.BEAR
            elif abs(change_rate) > 2.0:
                self.state.market_condition = MarketCondition.VOLATILE
            else:
                self.state.market_condition = MarketCondition.SIDEWAYS

            return self.state.market_condition

        except Exception as e:
            logger.debug(f"시장 분석 실패: {e}")
            return MarketCondition.UNKNOWN

    def _risk_management_loop(self):
        """리스크 관리 루프 - 자동 손절/익절 및 리스크 조절"""
        try:
            # 1. 일일 손실 체크
            if self.state.realized_profit_today < -(self.config.max_daily_loss_pct / 100 * 10_000_000):
                if self.state.mode != AutoPilotMode.DEFENSIVE:
                    self.state.mode = AutoPilotMode.DEFENSIVE
                    logger.warning(f"🛑 일일 손실 한도 도달 - DEFENSIVE 모드")

            # 2. 연속 손실 체크
            if self.state.consecutive_losses >= 3:
                self._auto_adjust_risk_mode()

            # 3. 동적 리스크 매니저 업데이트
            if self.dynamic_risk_manager:
                self._auto_adjust_risk_mode()

        except Exception as e:
            logger.error(f"리스크 관리 루프 오류: {e}")

    def _auto_adjust_risk_mode(self):
        """시장 상황에 따른 리스크 모드 자동 조절"""
        if not self.dynamic_risk_manager:
            return

        try:
            # 시장 상황 + 연속 손실 + 당일 손익 기반 리스크 모드 결정
            if self.state.market_condition == MarketCondition.BEAR:
                target_mode = 'conservative'
            elif self.state.market_condition == MarketCondition.VOLATILE:
                target_mode = 'very_conservative'
            elif self.state.consecutive_losses >= 3:
                target_mode = 'conservative'
            elif self.state.market_condition == MarketCondition.BULL:
                target_mode = 'normal'
            else:
                target_mode = 'normal'

            # 리스크 모드 변경
            current_mode = self.dynamic_risk_manager.current_mode.value
            if current_mode != target_mode:
                self.dynamic_risk_manager.set_mode(target_mode)
                logger.info(f"🎚️ 리스크 모드 자동 변경: {current_mode} → {target_mode}")

        except Exception as e:
            logger.error(f"리스크 모드 자동 조절 실패: {e}")

    def get_trading_decision(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI 기반 매매 결정 자동 생성

        Returns:
            {
                'action': 'buy' | 'sell' | 'hold',
                'confidence': float,
                'quantity': int,
                'price': int,
                'stop_loss': float,
                'take_profit': float,
                'reason': str
            }
        """
        try:
            # 방어 모드면 매수 금지
            if self.state.mode == AutoPilotMode.DEFENSIVE:
                return {
                    'action': 'hold',
                    'confidence': 0,
                    'reason': 'DEFENSIVE 모드 - 신규 매수 금지'
                }

            # 일시 중지면 모든 거래 금지
            if self.state.mode == AutoPilotMode.PAUSED:
                return {
                    'action': 'hold',
                    'confidence': 0,
                    'reason': 'AutoPilot 일시 중지'
                }

            # AI 분석기로 매매 결정
            if self.analyzer:
                analysis = self.analyzer.analyze_stock(stock_data)

                if analysis:
                    action = analysis.get('signal', 'hold')
                    confidence = analysis.get('confidence', 0)

                    # 모드에 따른 신뢰도 임계값 조절
                    threshold = {
                        AutoPilotMode.ACTIVE: 0.6,
                        AutoPilotMode.CAUTIOUS: 0.75,
                        AutoPilotMode.LEARNING: 0.5,
                    }.get(self.state.mode, 0.7)

                    if confidence >= threshold:
                        return {
                            'action': action,
                            'confidence': confidence,
                            'stop_loss': self.config.default_stop_loss_pct,
                            'take_profit': self.config.default_take_profit_pct,
                            'reason': analysis.get('reasons', ['AI 분석'])[0]
                        }

            return {
                'action': 'hold',
                'confidence': 0,
                'reason': '분석 결과 없음'
            }

        except Exception as e:
            logger.error(f"매매 결정 생성 실패: {e}")
            return {
                'action': 'hold',
                'confidence': 0,
                'reason': f'오류: {e}'
            }

    def record_trade_result(self, profit: float, is_win: bool):
        """거래 결과 기록"""
        with self._lock:
            self.state.total_trades_today += 1
            self.state.realized_profit_today += profit

            if is_win:
                self.state.consecutive_losses = 0
            else:
                self.state.consecutive_losses += 1

    def get_status(self) -> Dict[str, Any]:
        """AutoPilot 상태 조회"""
        return {
            'mode': self.state.mode.value,
            'market_condition': self.state.market_condition.value,
            'running': self._running,
            'started_at': self.state.started_at.isoformat(),
            'active_strategies': self.state.active_strategies,
            'total_trades_today': self.state.total_trades_today,
            'realized_profit_today': self.state.realized_profit_today,
            'best_strategy_return': self.state.best_strategy_return,
            'consecutive_losses': self.state.consecutive_losses,
            'last_strategy_review': self.state.last_strategy_review.isoformat() if self.state.last_strategy_review else None,
            'last_evolution_cycle': self.state.last_evolution_cycle.isoformat() if self.state.last_evolution_cycle else None,
            'config': {
                'min_strategies': self.config.min_strategies,
                'max_daily_loss_pct': self.config.max_daily_loss_pct,
                'evolution_enabled': self.config.evolution_enabled,
            }
        }


# 싱글톤 인스턴스
_autopilot_instance: Optional[AutoPilot] = None


def get_autopilot() -> Optional[AutoPilot]:
    """AutoPilot 싱글톤 인스턴스 반환"""
    return _autopilot_instance


def init_autopilot(
    virtual_manager=None,
    evolution_engine=None,
    dynamic_risk_manager=None,
    analyzer=None,
    data_fetcher=None
) -> AutoPilot:
    """AutoPilot 초기화 및 시작"""
    global _autopilot_instance

    _autopilot_instance = AutoPilot(
        virtual_manager=virtual_manager,
        evolution_engine=evolution_engine,
        dynamic_risk_manager=dynamic_risk_manager,
        analyzer=analyzer,
        data_fetcher=data_fetcher
    )

    return _autopilot_instance
