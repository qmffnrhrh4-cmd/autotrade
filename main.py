import sys
import os
import time
import signal
import threading
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).parent))

from config.manager import get_config
from config.constants import DELAYS, URLS, HOST, PORTS, BUY_SCORE_THRESHOLDS
from utils.logger_new import get_logger
from database import get_db_session, Trade, Position, PortfolioSnapshot
from core import KiwoomRESTClient, init_autopilot, get_autopilot
from core.websocket_manager import WebSocketManager
from api import AccountAPI, MarketAPI, OrderAPI, ExecutionAPI, OrderTracker, OrderStatus
from research import Screener, DataFetcher
from research.scanner_pipeline import ScannerPipeline
from strategy.scoring_system import ScoringSystem
from strategy.dynamic_risk_manager import DynamicRiskManager
from strategy import PortfolioManager
from utils.activity_monitor import get_monitor
from utils.alert_manager import get_alert_manager
from utils.data_cache import get_api_cache
from utils.trading_date import is_any_trading_hours
from virtual_trading import VirtualTrader, TradeLogger, VirtualTradingManager, VirtualTradingScheduler

# v8.0: 통합 리스크 관리 모듈
try:
    from core.risk_validation_pipeline import get_risk_pipeline, ValidationResult
    from core.event_bus import get_event_bus, EventType
    from core.emergency_controller import get_emergency_controller, is_trading_allowed
    from core.performance_analyzer import get_performance_analyzer
    _risk_modules_available = True
except ImportError as e:
    _risk_modules_available = False
    get_risk_pipeline = lambda: None
    get_event_bus = lambda: None
    get_emergency_controller = lambda: None
    is_trading_allowed = lambda: True
    get_performance_analyzer = lambda: None

# v8.2: 고급 자동화 및 안정성 모듈
try:
    from core.circuit_breaker import get_circuit_breaker, CircuitBreaker, CircuitOpenError
    from core.intelligent_data_manager import get_data_manager
    from core.self_healing_engine import get_healing_engine, ComponentType
    from core.autonomous_optimizer import get_optimizer, MarketCondition
    from core.trade_coordinator import get_trade_coordinator
    _v82_modules_available = True
except ImportError as e:
    _v82_modules_available = False
    get_circuit_breaker = lambda name, **kwargs: None
    get_data_manager = lambda: None
    get_healing_engine = lambda: None
    get_optimizer = lambda: None
    get_trade_coordinator = lambda: None

# 거래 실행 로거 (진단용)
try:
    from utils.trade_logger import get_trade_logger, log_buy, log_sell, log_success, log_failure
    _trade_logger = get_trade_logger()
except ImportError:
    _trade_logger = None
    def log_buy(*args, **kwargs):
        return ""
    def log_sell(*args, **kwargs):
        return ""
    def log_success(*args, **kwargs):
        pass
    def log_failure(*args, **kwargs):
        pass

logger = get_logger()


@dataclass
class MarketData:
    stock_code: str
    stock_name: str
    current_price: int
    volume: int
    change_rate: float
    institutional_net_buy: int = 0
    foreign_net_buy: int = 0
    bid_ask_ratio: float = 1.0
    institutional_trend: Optional[Dict] = None
    avg_volume: Optional[int] = None
    volatility: Optional[float] = None
    execution_intensity: Optional[float] = None
    program_net_buy: Optional[int] = None
    top_broker_buy_count: int = 0
    top_broker_net_buy: int = 0


class AutoTradingBot:

    def __init__(self):
        logger.info("="*80)
        logger.info("오토트레이드 프로 v8.2 - 고급 AI 트레이딩 시스템")
        logger.info("v8.2: 서킷 브레이커, 자가 치유, 자율 최적화, 지능형 캐싱")
        logger.info("="*80)

        # Fix v6.1.3: 시스템 자가 진단 실행
        try:
            from utils.system_diagnostics import run_diagnostics
            diagnostics_summary = run_diagnostics(save_to_file=True)

            # 치명적 오류가 있으면 경고
            if diagnostics_summary['failed'] > 0:
                logger.warning("")
                logger.warning("⚠️" * 40)
                logger.warning(f"⚠️  시스템 진단에서 {diagnostics_summary['failed']}개의 문제가 발견되었습니다!")
                logger.warning("⚠️  logs/diagnostics_report.txt 파일을 확인하세요")
                logger.warning("⚠️" * 40)
                logger.warning("")
        except Exception as e:
            logger.warning(f"시스템 진단 실패 (무시하고 계속): {e}")

        self.config = get_config()
        self.is_running = False
        self.is_initialized = False
        self.market_status = {}
        self.start_time = datetime.now()

        self.control_file = Path('data/control.json')
        self.state_file = Path('data/strategy_state.json')

        self.client = None
        self.openapi_client = None
        self.websocket_manager = None
        self.account_api = None
        self.market_api = None
        self.order_api = None
        self.execution_api = None
        self.order_tracker = None
        self.data_fetcher = None

        self.scanner = None
        self.scoring_system = None
        self.dynamic_risk_manager = None
        self.portfolio_manager = None
        self.analyzer = None

        self.split_order_executor = None
        self.ai_adaptive_split_executor = None  # AI 기반 적응형 분할 매도
        self.smart_money_manager = None
        self.emergency_manager = None
        self.liquidity_splitter = None
        self.cache_manager = None
        self.trailing_stop_manager = None  # Fix: 트레일링 스탑 관리자 추가

        self.split_order_ai = None
        self.parameter_optimizer = None
        self.self_learning_system = None
        self.strategy_loader = None  # v6.1.3: 진화된 전략 로더

        self.virtual_trader = None
        self.trade_logger = None
        self.virtual_trading_manager = None
        self.virtual_trading_scheduler = None
        self.autopilot = None  # v6.3 AutoPilot (완전 자동화)

        # v8.0: 통합 리스크 관리 모듈
        self.risk_pipeline = None
        self.event_bus = None
        self.emergency_controller = None
        self.performance_analyzer = None

        # v8.2: 고급 자동화 및 안정성 모듈
        self.circuit_breaker_api = None      # API 호출용 서킷 브레이커
        self.intelligent_data_manager = None  # 5단계 캐싱 데이터 관리자
        self.self_healing_engine = None       # 자가 치유 엔진
        self.autonomous_optimizer = None      # 자율 최적화 엔진
        self.trade_coordinator = None         # 통합 거래 코디네이터

        self.monitor = get_monitor()
        self.alert_manager = get_alert_manager()
        self.cache = get_api_cache()

        self.db_session = None

        self.ai_approved_candidates = []
        self.scan_progress = {
            'current_strategy': '',
            'total_candidates': 0,
            'top_candidates': [],
            'reviewing': '',
            'rejected': [],
            'approved': [],
        }

        self._check_test_mode()
        self._initialize_components()

        logger.info("오토트레이드 프로 초기화 완료")

    def _check_test_mode(self):
        try:
            from utils.trading_date import should_use_test_mode, get_last_trading_date

            if should_use_test_mode():
                self.test_mode_active = True
                self.test_date = get_last_trading_date()

                now = datetime.now()
                weekday_kr = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
                current_weekday = weekday_kr[now.weekday()]

                logger.info("="*80)
                logger.info("테스트 모드 활성화됨")
                logger.info(f"현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')} ({current_weekday})")
                logger.info(f"사용 데이터: {self.test_date}")
                logger.info("="*80)
            else:
                logger.info("실시간 매매 모드")
                self.test_mode_active = False

        except Exception as e:
            logger.warning(f"테스트 모드 확인 실패: {e}")
            self.test_mode_active = False

    def _initialize_components(self):
        try:
            logger.info("데이터베이스 초기화 중...")
            self.db_session = get_db_session()
            logger.info("데이터베이스 초기화 완료")

            logger.info("REST API 클라이언트 초기화 중...")
            self.client = KiwoomRESTClient()
            logger.info("REST API 클라이언트 초기화 완료")

            logger.info("OpenAPI 클라이언트 초기화 중...")
            try:
                from core.openapi_client import KiwoomOpenAPIClient

                # 먼저 OpenAPI 서버가 이미 실행 중인지 확인
                import requests
                server_already_running = False
                try:
                    response = requests.get(URLS['openapi_health'], timeout=2)
                    if response.status_code == 200:
                        server_already_running = True
                        logger.info("✅ OpenAPI 서버 이미 실행 중 (외부에서 시작됨)")
                except:
                    pass

                self.openapi_client = KiwoomOpenAPIClient(auto_connect=False)

                # OpenAPI 연결 시도 (최대 3번 재시도, 각 5초 간격)
                connected = False
                max_connection_retries = 3

                for retry in range(max_connection_retries):
                    if retry > 0:
                        logger.info(f"⏳ OpenAPI 연결 재시도 {retry}/{max_connection_retries}... (5초 대기)")
                        import time
                        time.sleep(5)

                    if self.openapi_client.connect():
                        logger.info("OpenAPI 클라이언트 초기화 완료")
                        accounts = self.openapi_client.get_account_list()
                        if accounts:
                            logger.info(f"계좌 목록: {accounts}")
                        connected = True
                        break

                if not connected:
                    if server_already_running:
                        logger.warning("OpenAPI 서버 실행 중이지만 재시도 후에도 연결 불가")
                        logger.warning("서버가 초기화 중이거나 로그인 대기 중일 수 있습니다")
                        logger.warning("OpenAPI 서버 창을 확인하세요 (작업 표시줄에 최소화됨)")
                        logger.warning("REST API만으로 계속 진행합니다...")
                        self.openapi_client = None
                    else:
                        logger.warning("OpenAPI 서버 미실행 - 시작 시도 중...")
                        server_started = self._start_openapi_server()
                        logger.info(f"서버 시작 결과: {server_started}")
                        if server_started:
                            logger.info("")
                            logger.info("="*80)
                            logger.info("⚠️  키움증권 로그인이 필요합니다!")
                            logger.info("="*80)
                            logger.info("1. 새 콘솔 창이 열렸습니다 (OpenAPI 서버)")
                            logger.info("2. 해당 창에서 키움증권 로그인 창이 나타납니다")
                            logger.info("3. 로그인 정보와 인증서 비밀번호를 입력하세요")
                            logger.info("4. 로그인 완료까지 최대 60초 대기합니다...")
                            logger.info("="*80)
                            logger.info("")

                            # 서버 시작 대기 및 재시도 (최대 60초)
                            max_retries = 20
                            retry_delay = 3
                            retry_connected = False

                            for retry in range(max_retries):
                                logger.info(f"⏳ 연결 시도 {retry + 1}/{max_retries} (남은 시간: {(max_retries - retry) * retry_delay}초)")
                                time.sleep(retry_delay)

                                if self.openapi_client.connect():
                                    logger.info("")
                                    logger.info("="*80)
                                    logger.info("✅ OpenAPI 로그인 성공!")
                                    logger.info("="*80)
                                    accounts = self.openapi_client.get_account_list()
                                    if accounts:
                                        logger.info(f"📋 계좌 목록: {accounts}")
                                    retry_connected = True
                                    break
                                else:
                                    if retry < max_retries - 1:
                                        logger.info(f"   준비 중... {retry_delay}초 후 재시도")

                            if not retry_connected:
                                logger.warning("")
                                logger.warning("="*80)
                                logger.warning("⚠️  OpenAPI 연결 실패")
                                logger.warning("="*80)
                                logger.warning("60초 대기 후에도 연결되지 않았습니다.")
                                logger.warning("가능한 원인:")
                                logger.warning("  - 로그인 창에서 로그인하지 않음")
                                logger.warning("  - 인증서 비밀번호 오류")
                                logger.warning("  - OpenAPI 서버 시작 실패")
                                logger.warning("")
                                logger.warning("REST API로 계속 진행합니다.")
                                logger.warning("OpenAPI 기능을 사용하려면 수동으로 시작하세요:")
                                logger.warning("  conda activate kiwoom32")
                                logger.warning("  python openapi_server_v2.py")
                                logger.warning("="*80)
                                logger.warning("")
                                self.openapi_client = None
                        else:
                            logger.warning("OpenAPI 서버 시작 실패 - REST API만 사용합니다")
                            self.openapi_client = None
            except Exception as e:
                logger.warning(f"OpenAPI 클라이언트 사용 불가: {e}")
                self.openapi_client = None

            logger.info("WebSocket 초기화 중...")
            try:
                if self.client.token:
                    self.websocket_manager = WebSocketManager(
                        access_token=self.client.token,
                        base_url=self.client.base_url
                    )

                    async def on_price_update(data):
                        try:
                            stock_code = data.get('item', '')
                            values = data.get('values', {})
                            price = int(values.get('10', '0'))
                            logger.debug(f"실시간 가격: {stock_code} = {price:,}")
                        except Exception as e:
                            logger.error(f"가격 데이터 처리 오류: {e}")

                    self.websocket_manager.register_callback('0B', on_price_update)

                    def start_websocket():
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            connected = loop.run_until_complete(self.websocket_manager.connect())
                            if connected:
                                logger.info("WebSocket 자동 연결 완료")
                        except Exception as e:
                            logger.error(f"WebSocket 연결 오류: {e}")

                    ws_thread = threading.Thread(target=start_websocket, daemon=True)
                    ws_thread.start()

                    logger.info("WebSocket 초기화 완료")
                else:
                    self.websocket_manager = None
                    logger.info("WebSocket 비활성화 - 토큰 없음")
            except Exception as e:
                logger.warning(f"WebSocket 초기화 실패: {e}")
                self.websocket_manager = None

            logger.info("API 모듈 초기화 중...")
            self.account_api = AccountAPI(self.client)
            self.market_api = MarketAPI(self.client)
            self.order_api = OrderAPI(self.client)
            self.execution_api = ExecutionAPI(self.client)
            self.order_tracker = OrderTracker(self.execution_api)
            self.data_fetcher = DataFetcher(self.client)
            logger.info("API 모듈 초기화 완료")

            logger.info("AI 분석기 초기화 중...")
            try:
                from config import GEMINI_API_KEY
                from ai.enhanced_sentiment_analyzer import get_sentiment_analyzer

                if GEMINI_API_KEY and GEMINI_API_KEY.strip() and GEMINI_API_KEY != "your-gemini-api-key-here":
                    from ai.gemini_analyzer import GeminiAnalyzer
                    self.analyzer = GeminiAnalyzer()
                    if self.analyzer.initialize():
                        logger.info("Gemini AI 분석기 초기화 완료")
                    else:
                        logger.warning("Gemini 초기화 실패 - Mock 분석기 사용 중")
                        from ai.mock_analyzer import MockAnalyzer
                        self.analyzer = MockAnalyzer()
                        self.analyzer.initialize()
                else:
                    from ai.mock_analyzer import MockAnalyzer
                    self.analyzer = MockAnalyzer()
                    self.analyzer.initialize()
                    logger.info("Mock AI 분석기 초기화 완료")

                self.sentiment_analyzer = get_sentiment_analyzer()
                logger.info("감성 분석기 초기화 완료")

            except Exception as e:
                logger.error(f"AI 분석기 초기화 실패: {e}")
                from ai.mock_analyzer import MockAnalyzer
                self.analyzer = MockAnalyzer()
                self.analyzer.initialize()
                self.sentiment_analyzer = None
                logger.warning("Mock 분석기 사용 중")

            logger.info("스캐닝 파이프라인 초기화 중...")
            screener = Screener(self.client)
            self.scanner = ScannerPipeline(
                market_api=self.market_api,
                screener=screener,
                ai_analyzer=self.analyzer
            )
            logger.info("스캐닝 파이프라인 초기화 완료")

            logger.info("점수 계산 시스템 초기화 중...")
            self.scoring_system = ScoringSystem(market_api=self.market_api)
            logger.info("점수 계산 시스템 초기화 완료")

            logger.info("리스크 관리자 초기화 중...")
            initial_capital = self._get_initial_capital()
            self.dynamic_risk_manager = DynamicRiskManager(initial_capital=initial_capital)
            logger.info("리스크 관리자 초기화 완료")

            logger.info("포트폴리오 관리자 초기화 중...")
            self.portfolio_manager = PortfolioManager(self.client)
            logger.info("포트폴리오 관리자 초기화 완료")

            logger.info("자동화 시스템 초기화 중...")
            try:
                from strategy.split_order_executor import SplitOrderExecutor
                from strategy.ai_adaptive_split_executor import AIAdaptiveSplitExecutor
                from strategy.smart_money_manager import get_smart_money_manager
                from strategy.emergency_manager import get_emergency_manager
                from strategy.liquidity_splitter import get_liquidity_splitter
                from utils.cache_manager import get_cache_manager
                from strategy.trailing_stop_manager import TrailingStopManager

                # Split order executor
                self.split_order_executor = SplitOrderExecutor(
                    order_api=self.order_api,
                    data_fetcher=self.data_fetcher
                )
                logger.info("  ✅ Split order executor")

                # AI 기반 적응형 분할 매도 실행기
                self.ai_adaptive_split_executor = AIAdaptiveSplitExecutor(
                    order_api=self.order_api,
                    data_fetcher=self.data_fetcher,
                    account_api=self.account_api,
                    ai_analyzer=self.analyzer if hasattr(self, 'analyzer') else None
                )
                logger.info("  ✅ AI 적응형 분할 매도 시스템")

                # Smart money manager
                # Fix: Pydantic BaseModel을 dict로 변환
                if hasattr(self.config, 'automation_features'):
                    automation_config = self.config.automation_features.model_dump() if hasattr(self.config.automation_features, 'model_dump') else {}
                else:
                    automation_config = {}
                self.smart_money_manager = get_smart_money_manager(automation_config)
                logger.info("  ✅ Smart money manager")

                # Emergency manager
                self.emergency_manager = get_emergency_manager(
                    config=automation_config,
                    order_api=self.order_api,
                    data_fetcher=self.data_fetcher
                )
                logger.info("  ✅ Emergency manager")

                # Liquidity splitter
                self.liquidity_splitter = get_liquidity_splitter(automation_config)
                logger.info("  ✅ Liquidity splitter")

                # Cache manager
                self.cache_manager = get_cache_manager()
                logger.info("  ✅ Cache manager")

                # Trailing stop manager
                trailing_settings = {
                    'atr_multiplier': 2.0,           # ATR 승수
                    'activation_pct': 0.03,          # 3% 수익에서 활성화
                    'min_profit_lock_pct': 0.50      # 최소 50% 수익 보호
                }
                self.trailing_stop_manager = TrailingStopManager(settings=trailing_settings)
                logger.info("  ✅ Trailing stop manager (ATR 기반 동적 손절/익절)")

                logger.info("자동화 시스템 초기화 완료")

            except Exception as e:
                logger.warning(f"자동화 시스템 초기화 실패: {e}")
                logger.warning("자동화 기능은 제한적으로 작동합니다")

            logger.info("AI 학습 시스템 초기화 중...")
            try:
                from ai.split_order_ai import get_split_order_ai
                from ai.parameter_optimizer import get_parameter_optimizer
                from ai.self_learning_system import get_self_learning_system

                # Split order AI
                self.split_order_ai = get_split_order_ai()
                logger.info("  ✅ Split order AI")

                # Parameter optimizer
                self.parameter_optimizer = get_parameter_optimizer()
                logger.info("  ✅ Parameter optimizer")

                # Self-learning system
                self.self_learning_system = get_self_learning_system()
                logger.info("  ✅ Self-learning system")

                logger.info("AI 학습 시스템 초기화 완료")
                logger.info(f"  📚 학습된 경험: {self.self_learning_system.stats.total_experiences}개")
                logger.info(f"  🎯 학습된 상태: {len(self.self_learning_system.q_table)}개")

            except Exception as e:
                logger.warning(f"AI 학습 시스템 초기화 실패: {e}")
                logger.warning("AI 학습 기능은 제한적으로 작동합니다")

            logger.info("진화된 전략 로더 초기화 중...")
            try:
                from ai.strategy_loader import get_strategy_loader

                # 전략 로더 초기화
                self.strategy_loader = get_strategy_loader()

                # 최우수 전략 로드
                evolved_strategy = self.strategy_loader.load_best_strategy()

                if evolved_strategy:
                    logger.info("  ✅ 진화된 전략 로드 완료")
                    logger.info(f"  📊 세대: {evolved_strategy.generation}, 적합도: {evolved_strategy.fitness_score:.2f}")
                    logger.info(f"  🎯 백테스팅 수익률: {evolved_strategy.backtest_return_pct:+.2f}%")
                    logger.info(f"  💰 익절: +{evolved_strategy.sell_take_profit * 100:.1f}%, 손절: {evolved_strategy.sell_stop_loss * 100:.1f}%")
                else:
                    logger.info("  ℹ️  진화된 전략 없음 - 기본 전략 사용")
                    logger.info("  💡 전략 진화를 시작하려면: python run_strategy_optimizer.py")

            except Exception as e:
                logger.error(f"❌ 진화된 전략 로더 초기화 실패: {e}", exc_info=True)
                logger.warning("기본 전략으로 계속 진행합니다")
                self.strategy_loader = None

            logger.info("가상매매 시스템 초기화 중...")
            try:
                virtual_initial_cash = 10_000_000
                logger.info(f"가상매매 초기 자본금: {virtual_initial_cash:,}원")

                self.virtual_trader = VirtualTrader(initial_cash=virtual_initial_cash)
                self.trade_logger = TradeLogger()

                loaded_count = self.trade_logger.load_historical_trades(days=7)
                if loaded_count > 0:
                    logger.info(f"{loaded_count}건의 과거 거래 기록 로드됨")

                self.virtual_trader.load_all_states()

                # 가상매매 매니저 초기화 (DB 기반)
                self.virtual_trading_manager = VirtualTradingManager()
                logger.info("가상매매 매니저 초기화 완료")

                # 가상매매 슬롯 자동 생성 (10개)
                self._auto_initialize_virtual_trading_slots()

                # 가상매매 스케줄러 초기화 및 시작
                if self.data_fetcher and self.virtual_trading_manager:
                    self.virtual_trading_scheduler = VirtualTradingScheduler(
                        virtual_manager=self.virtual_trading_manager,
                        data_fetcher=self.data_fetcher,
                        bot_instance=self  # Fix v6.1.4: bot_instance 전달하여 독립적인 매매 가능
                    )
                    self.virtual_trading_scheduler.start()
                    logger.info("가상매매 스케줄러 시작 완료 (실시간 업데이트, 자동 손절/익절, 독립 매매)")

                logger.info("가상매매 시스템 초기화 완료")

                # v6.3 AutoPilot 초기화 (완전 자동화)
                # 환경 변수로 비활성화 여부 확인
                autopilot_disabled = os.environ.get('AUTOPILOT_DISABLED', '0') == '1'

                if autopilot_disabled:
                    logger.info("⚠️  AutoPilot 비활성화됨 (--no-autopilot 플래그)")
                    self.autopilot = None
                else:
                    try:
                        from virtual_trading.evolution_engine import get_evolution_engine
                        evolution_engine = get_evolution_engine()

                        self.autopilot = init_autopilot(
                            virtual_manager=self.virtual_trading_manager,
                            evolution_engine=evolution_engine,
                            dynamic_risk_manager=self.dynamic_risk_manager,
                            analyzer=getattr(self, 'analyzer', None),
                            data_fetcher=self.data_fetcher
                        )
                        self.autopilot.start()
                        logger.info("🤖 AutoPilot 완전 자동화 모드 시작!")
                    except Exception as e:
                        logger.warning(f"AutoPilot 초기화 실패 (수동 모드로 계속): {e}")
                        self.autopilot = None

            except Exception as e:
                logger.warning(f"가상매매 시스템 초기화 실패: {e}")
                self.virtual_trader = None
                self.trade_logger = None
                self.virtual_trading_manager = None
                self.virtual_trading_scheduler = None
                self.autopilot = None

            # v8.0: 통합 리스크 관리 모듈 초기화
            logger.info("통합 리스크 관리 시스템 초기화 중...")
            try:
                if _risk_modules_available:
                    # 리스크 검증 파이프라인
                    self.risk_pipeline = get_risk_pipeline()
                    logger.info("  ✅ 4단계 리스크 검증 파이프라인")

                    # 이벤트 버스
                    self.event_bus = get_event_bus()
                    logger.info("  ✅ 실시간 이벤트 버스")

                    # 긴급 정지 컨트롤러
                    self.emergency_controller = get_emergency_controller()
                    logger.info(f"  ✅ 긴급 정지 컨트롤러 (현재 수준: {self.emergency_controller.current_level.value})")

                    # 성능 분석기
                    self.performance_analyzer = get_performance_analyzer()
                    logger.info("  ✅ 성능 분석기")

                    logger.info("통합 리스크 관리 시스템 초기화 완료")
                else:
                    logger.warning("리스크 관리 모듈 사용 불가 - 기본 모드로 실행")
            except Exception as e:
                logger.warning(f"리스크 관리 시스템 초기화 실패: {e}")

            # v8.2: 고급 자동화 및 안정성 시스템 초기화
            logger.info("v8.2 고급 자동화 시스템 초기화 중...")
            try:
                if _v82_modules_available:
                    # 1. 서킷 브레이커 (API 안정성)
                    self.circuit_breaker_api = get_circuit_breaker(
                        "kiwoom_api",
                        failure_threshold=5,
                        recovery_timeout=60.0,
                        failure_rate_threshold=0.5
                    )
                    logger.info("  ✅ 서킷 브레이커 (API 장애 격리)")

                    # 2. 지능형 데이터 매니저 (5단계 캐싱)
                    self.intelligent_data_manager = get_data_manager()
                    if self.client:
                        self.intelligent_data_manager.set_api_client(self.client)
                    logger.info("  ✅ 지능형 데이터 매니저 (5단계 캐싱)")

                    # 3. 자가 치유 엔진
                    self.self_healing_engine = get_healing_engine()

                    # 컴포넌트 건강 체크 등록
                    def check_api_health():
                        try:
                            deposit = self.account_api.get_deposit() if self.account_api else None
                            return deposit is not None
                        except:
                            return False

                    def check_db_health():
                        try:
                            if self.db_session:
                                self.db_session.execute("SELECT 1")
                                return True
                            return False
                        except:
                            return False

                    def check_websocket_health():
                        return self.websocket_manager is not None and self.websocket_manager.is_connected

                    self.self_healing_engine.register_component(
                        name="kiwoom_api",
                        component_type=ComponentType.API,
                        check_func=check_api_health,
                        interval=60.0,
                        failure_threshold=3
                    )
                    self.self_healing_engine.register_component(
                        name="database",
                        component_type=ComponentType.DATABASE,
                        check_func=check_db_health,
                        interval=120.0,
                        failure_threshold=2
                    )
                    self.self_healing_engine.register_component(
                        name="websocket",
                        component_type=ComponentType.WEBSOCKET,
                        check_func=check_websocket_health,
                        interval=30.0,
                        failure_threshold=5
                    )
                    self.self_healing_engine.start()
                    logger.info("  ✅ 자가 치유 엔진 (자동 복구)")

                    # 4. 자율 최적화 엔진
                    self.autonomous_optimizer = get_optimizer()
                    if self.dynamic_risk_manager:
                        self.autonomous_optimizer.set_risk_manager(self.dynamic_risk_manager)
                    self.autonomous_optimizer.start()
                    logger.info("  ✅ 자율 최적화 엔진 (자동 튜닝)")

                    # 5. 통합 거래 코디네이터
                    self.trade_coordinator = get_trade_coordinator()
                    if self.order_api:
                        self.trade_coordinator.set_order_api(self.order_api)
                    logger.info("  ✅ 통합 거래 코디네이터 (분할 주문/부분 청산)")

                    logger.info("v8.2 고급 자동화 시스템 초기화 완료")
                else:
                    logger.warning("v8.2 모듈 사용 불가 - 기본 모드로 실행")
            except Exception as e:
                logger.warning(f"v8.2 시스템 초기화 실패 (무시하고 계속): {e}")

            self._initialize_control_file()
            self._restore_state()

            self.is_initialized = True
            logger.info("모든 컴포넌트 초기화 성공")

            self.monitor.log_activity('system', 'AutoTrade Pro started', level='success')

        except Exception as e:
            logger.error(f"컴포넌트 초기화 실패: {e}", exc_info=True)
            raise

    def _get_initial_capital(self) -> int:
        try:
            deposit = self.account_api.get_deposit()
            holdings = self.account_api.get_holdings()

            if deposit:
                deposit_total = int(str(deposit.get('entr', '0')).replace(',', ''))
                holdings_value = sum(int(str(h.get('eval_amt', 0)).replace(',', '')) for h in holdings) if holdings else 0
                capital = deposit_total + holdings_value if (deposit_total + holdings_value) > 0 else 10_000_000
                logger.info(f"초기 자본금: {capital:,}원 (예수금: {deposit_total:,}원, 주식: {holdings_value:,}원)")
                return capital
            return 10_000_000
        except Exception as e:
            logger.warning(f"초기 자본금 조회 실패: {e}")
            return 10_000_000

    def _auto_initialize_virtual_trading_slots(self):
        """가상매매 슬롯 자동 초기화 (10개)"""
        if not self.virtual_trading_manager:
            return

        try:
            # 기존 슬롯 확인
            existing_strategies = self.virtual_trading_manager.db.get_all_strategies()
            existing_count = len(existing_strategies)

            if existing_count >= 10:
                logger.info(f"가상매매 슬롯 {existing_count}개 이미 존재 - 자동 생성 스킵")
                return

            # 부족한 슬롯 생성
            slots_to_create = 10 - existing_count
            logger.info(f"가상매매 슬롯 {slots_to_create}개 자동 생성 중...")

            for i in range(existing_count, 10):
                slot_name = f"슬롯 {i}"
                try:
                    strategy_id = self.virtual_trading_manager.create_strategy(
                        name=slot_name,
                        description=f"자동 생성된 가상매매 슬롯 #{i}",
                        initial_capital=10_000_000  # 1천만원 초기 자본
                    )
                    logger.info(f"  ✅ {slot_name} 생성 완료 (ID: {strategy_id})")
                except Exception as e:
                    # 이미 존재하는 경우 스킵
                    if "UNIQUE constraint failed" in str(e):
                        logger.debug(f"  ⏭️  {slot_name} 이미 존재")
                    else:
                        logger.warning(f"  ⚠️  {slot_name} 생성 실패: {e}")

            logger.info(f"✅ 가상매매 슬롯 자동 생성 완료 (총 10개)")

        except Exception as e:
            logger.error(f"가상매매 슬롯 자동 초기화 실패: {e}")

    def _initialize_control_file(self):
        if not self.control_file.exists():
            default_state = {
                'run': True,
                'pause_buy': False,
                'pause_sell': False,
            }
            import json
            with open(self.control_file, 'w') as f:
                json.dump(default_state, f, indent=2)
            logger.info("제어 파일 생성됨")

    def _restore_state(self):
        try:
            if self.state_file.exists():
                import json
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"상태 복원됨: {len(state.get('positions', {}))}개 포지션")
        except Exception as e:
            logger.warning(f"상태 복원 실패: {e}")

    def _start_openapi_server(self):
        """OpenAPI 서버 자동 시작 (Windows 32비트 Python 환경)"""
        try:
            import subprocess
            import platform
            import os

            if platform.system() != 'Windows':
                logger.warning("OpenAPI 서버 자동 시작은 Windows에서만 지원됩니다")
                logger.info("수동으로 시작하세요: conda activate kiwoom32 && python openapi_server_v2.py")
                return False

            logger.info("="*80)
            logger.info("OpenAPI 서버 시작 시도")
            logger.info("="*80)

            server_script = os.path.join(os.path.dirname(__file__), 'openapi_server_v2.py')
            if not os.path.exists(server_script):
                logger.error(f"OpenAPI 서버 스크립트를 찾을 수 없습니다: {server_script}")
                return False

            # 32비트 Python 환경 검색
            conda_paths = [
                r"C:\Users\USER\anaconda3\envs\kiwoom32\python.exe",
                r"C:\ProgramData\Anaconda3\envs\kiwoom32\python.exe",
                r"C:\Anaconda3\envs\kiwoom32\python.exe",
            ]

            python_exe = None
            for path in conda_paths:
                if os.path.exists(path):
                    python_exe = path
                    logger.info(f"✅ 32비트 Python 발견: {path}")
                    break

            if not python_exe:
                logger.error("❌ 32비트 Python (kiwoom32)을 찾을 수 없습니다")
                logger.error(f"   검색 경로:")
                for path in conda_paths:
                    logger.error(f"   - {path}: {'존재함' if os.path.exists(path) else '없음'}")
                logger.info("")
                logger.info("수동으로 실행하세요:")
                logger.info("  1. 새 터미널을 엽니다")
                logger.info("  2. conda activate kiwoom32")
                logger.info("  3. python openapi_server_v2.py")
                logger.info("")
                return False

            logger.info(f"🚀 OpenAPI 서버 시작 중...")
            logger.info(f"   Python: {python_exe}")
            logger.info(f"   스크립트: {server_script}")

            # 서버가 이미 실행 중인지 확인
            try:
                import requests
                response = requests.get(URLS['openapi_health'], timeout=1)
                if response.status_code == 200:
                    logger.info("✅ OpenAPI 서버가 이미 실행 중입니다!")
                    return True
            except:
                pass

            # 서버 시작 (로그인 창이 보이도록 새 콘솔 창에서 실행)
            if platform.system() == 'Windows':
                # CREATE_NEW_CONSOLE: 새 콘솔 창에서 실행하여 로그인 창이 확실히 표시됨
                process = subprocess.Popen(
                    [python_exe, server_script],
                    cwd=os.path.dirname(__file__),
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                process = subprocess.Popen(
                    [python_exe, server_script],
                    cwd=os.path.dirname(__file__),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            logger.info(f"✅ OpenAPI 서버 프로세스 시작됨 (PID: {process.pid})")
            logger.info("")
            logger.info("⚠️  중요 안내:")
            logger.info("   - 새로운 콘솔 창이 열렸습니다 (OpenAPI 서버)")
            logger.info("   - 해당 창에서 키움증권 로그인 창이 나타납니다")
            logger.info("   - 키움증권 계정으로 로그인하세요")
            logger.info("   - 로그인 완료까지 약 10-30초 소요됩니다")
            logger.info("")
            logger.info("="*80)

            return True

        except Exception as e:
            logger.error(f"OpenAPI 서버 시작 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def start(self):
        if not self.is_initialized:
            logger.error("봇이 초기화되지 않았습니다")
            print("오류: 봇이 초기화되지 않았습니다")
            return

        print("\n" + "="*80)
        print("오토트레이드 프로 v8.2 - 메인 루프 시작됨")
        print("="*80)
        logger.info("="*80)
        logger.info("오토트레이드 프로 실행 시작")
        logger.info("="*80)

        self.is_running = True

        try:
            logger.info("대시보드 서버 시작 중...")
            from dashboard.app import run_dashboard
            import threading

            dashboard_thread = threading.Thread(
                target=lambda: run_dashboard(bot=self, host=HOST, port=PORTS['dashboard'], debug=False),
                daemon=True
            )
            dashboard_thread.start()
            logger.info(f"대시보드 서버 시작됨: http://{HOST}:{PORTS['dashboard']}")
            print(f"📊 Dashboard: {URLS['dashboard']}")

            # 대시보드 자동 열기
            try:
                import webbrowser
                import time
                time.sleep(2)  # 서버 시작 대기
                webbrowser.open(URLS['dashboard'])
                logger.info("브라우저에서 대시보드 열기 완료")
            except Exception as e:
                logger.warning(f"브라우저 열기 실패: {e}")

            if self.emergency_manager:
                try:
                    logger.info("비상 모니터링 시스템 시작 중...")
                    self.emergency_manager.start_monitoring(self)
                    logger.info("비상 모니터링 시스템 시작 완료")
                    print("🚨 Emergency monitoring: Active")
                except Exception as e:
                    logger.warning(f"비상 모니터링 시작 실패: {e}")

            self._main_loop()
        except KeyboardInterrupt:
            logger.info("사용자가 중단함")
            print("\n사용자가 중단함")
        except Exception as e:
            logger.error(f"메인 루프 오류: {e}", exc_info=True)
            print(f"\n메인 루프 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()

    def stop(self):
        logger.info("오토트레이드 프로 중단 중...")
        self.is_running = False

        # v8.2: 자동화 시스템 정지
        if self.self_healing_engine:
            try:
                logger.info("자가 치유 엔진 중지 중...")
                self.self_healing_engine.stop()
                logger.info("자가 치유 엔진 중지 완료")
            except Exception as e:
                logger.warning(f"자가 치유 엔진 중지 실패: {e}")

        if self.autonomous_optimizer:
            try:
                logger.info("자율 최적화 엔진 중지 중...")
                self.autonomous_optimizer.stop()
                logger.info("자율 최적화 엔진 중지 완료")
            except Exception as e:
                logger.warning(f"자율 최적화 엔진 중지 실패: {e}")

        if self.intelligent_data_manager:
            try:
                logger.info("데이터 매니저 캐시 통계...")
                stats = self.intelligent_data_manager.get_cache_stats()
                logger.info(f"  캐시 적중률: {stats.get('hit_rate', 0):.1f}%")
            except Exception as e:
                logger.warning(f"데이터 매니저 통계 조회 실패: {e}")

        if self.emergency_manager:
            try:
                logger.info("비상 모니터링 중지 중...")
                self.emergency_manager.stop_monitoring()
                logger.info("비상 모니터링 중지 완료")
            except Exception as e:
                logger.warning(f"비상 모니터링 중지 실패: {e}")

        if self.virtual_trader:
            try:
                logger.info("가상매매 상태 저장 중...")
                self.virtual_trader.save_all_states()
                logger.info("가상매매 상태 저장 완료")
            except Exception as e:
                logger.warning(f"가상매매 상태 저장 실패: {e}")

        if self.trade_logger:
            try:
                self.trade_logger.print_summary()
            except Exception as e:
                logger.warning(f"거래 요약 출력 실패: {e}")

        if self.websocket_manager:
            try:
                asyncio.run(self.websocket_manager.disconnect())
                logger.info("WebSocket 연결 해제됨")
            except Exception as e:
                logger.warning(f"WebSocket 연결 해제 실패: {e}")

        if self.db_session:
            self.db_session.close()

        if self.client:
            self.client.close()

        logger.info("오토트레이드 프로 중단 완료")

    def _main_loop(self):
        cycle_count = 0
        try:
            if isinstance(self.config.main_cycle, dict):
                sleep_seconds = self.config.main_cycle.get('sleep_seconds', 60)
            else:
                sleep_seconds = getattr(self.config.main_cycle, 'sleep_seconds', 60)
        except Exception as e:
            logger.warning(f"설정 로드 실패, 기본값 사용: {e}")
            sleep_seconds = 60

        while self.is_running:
            cycle_count += 1

            if cycle_count > 1:
                logger.info(f"Waiting {sleep_seconds} seconds...\n")
                time.sleep(sleep_seconds)

            print(f"\n{'='*80}")
            print(f"Cycle #{cycle_count}")
            print(f"{'='*80}")

            try:
                self._read_control_file()
                if not self.is_running:
                    break

                trading_hours_ok = self._check_trading_hours()
                if not trading_hours_ok:
                    continue

                self._update_account_info()

                if self.virtual_trader:
                    try:
                        price_data = self._get_virtual_trading_prices()
                        if price_data:
                            self.virtual_trader.update_all_prices(price_data)
                        self.virtual_trader.check_sell_conditions(price_data)
                    except Exception as e:
                        logger.warning(f"Virtual trading update failed: {e}")

                if not self.pause_sell:
                    self._check_sell_signals()

                if not self.pause_buy:
                    self._run_scanning_pipeline()

                self._save_portfolio_snapshot()
                self._print_statistics()

            except Exception as e:
                logger.error(f"메인 루프 오류: {e}", exc_info=True)
                print(f"메인 루프 오류: {e}")
                import traceback
                traceback.print_exc()

    def _read_control_file(self):
        try:
            import json
            if self.control_file.exists():
                with open(self.control_file, 'r') as f:
                    control = json.load(f)
                self.is_running = control.get('run', True)
                self.pause_buy = control.get('pause_buy', False)
                self.pause_sell = control.get('pause_sell', False)
        except Exception as e:
            logger.warning(f"제어 파일 읽기 실패: {e}")

    def _check_trading_hours(self) -> bool:
        from research.analyzer import Analyzer
        analyzer = Analyzer(self.client)
        market_status = analyzer.get_market_status()

        self.market_status = market_status

        if not market_status['is_trading_hours']:
            logger.info(f"거래 시간 외: {market_status['market_status']}")
            logger.info("테스트 모드 활성화 - 실제 API 호출 실행")
            self.market_status['is_trading_hours'] = True
            self.market_status['is_test_mode'] = True
            self.market_status['market_type'] = '테스트 모드'

        if market_status.get('is_test_mode'):
            logger.info(f"테스트 모드: {market_status['market_status']}")
        elif market_status.get('can_cancel_only'):
            logger.info(f"{market_status['market_type']}: {market_status['market_status']}")
        elif market_status.get('order_type_limit') == 'limit_only':
            logger.info(f"{market_status['market_type']}: {market_status['market_status']}")
        else:
            logger.info(f"{market_status['market_type']}: {market_status['market_status']}")

        return True

    def _update_account_info(self):
        try:
            deposit = self.account_api.get_deposit()
            holdings = self.account_api.get_holdings()

            deposit_total = int(str(deposit.get('entr', '0')).replace(',', '')) if deposit else 0
            cash = int(str(deposit.get('100stk_ord_alow_amt', '0')).replace(',', '')) if deposit else 0
            stock_value = sum(int(str(h.get('eval_amt', 0)).replace(',', '')) for h in holdings) if holdings else 0

            self.portfolio_manager.update_portfolio(holdings, cash)

            total_capital = deposit_total + stock_value
            self.dynamic_risk_manager.update_capital(total_capital)

            logger.info(f"계좌: 예수금={deposit_total:,}원, 현금={cash:,}원, 주식={stock_value:,}원, 합계={total_capital:,}원, 포지션={len(holdings)}개")

        except Exception as e:
            logger.error(f"계좌 정보 업데이트 실패: {e}")

    def _check_sell_signals(self):
        logger.info("매도 신호 확인 중...")

        if self.market_status.get('is_test_mode'):
            logger.info("테스트 모드: 실제 보유 종목으로 매도 로직 실행")

        try:
            holdings = self.account_api.get_holdings()

            if not holdings:
                logger.info("보유 종목 없음")
                return

            for holding in holdings:
                stock_code = holding.get('stk_cd', '')

                if stock_code.startswith('A'):
                    stock_code = stock_code[1:]

                stock_name = holding.get('stk_nm')
                quantity = int(holding.get('rmnd_qty', 0))
                buy_price = int(holding.get('avg_prc', 0))

                # FIX: 계좌 API의 cur_prc는 부정확할 수 있음. 실시간 현재가 조회
                try:
                    current_price_data = self.data_fetcher.get_current_price(stock_code)
                    current_price = int(current_price_data.get('current_price', 0))
                    logger.debug(f"실시간 현재가 조회: {stock_name} = {current_price:,}원")
                except Exception as e:
                    # 실시간 조회 실패 시 계좌 API 값 사용 (fallback)
                    current_price = int(holding.get('cur_prc', 0))
                    logger.warning(f"실시간 현재가 조회 실패, 계좌 값 사용: {stock_name} = {current_price:,}원")

                logger.info(f"보유: {stock_name}({stock_code}) {quantity}주@{current_price:,}원 (매수가:{buy_price:,}원)")

                profit_loss = (current_price - buy_price) * quantity
                profit_loss_rate = ((current_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0

                self.alert_manager.check_position_alerts(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    current_price=current_price,
                    buy_price=buy_price,
                    profit_loss_rate=profit_loss_rate,
                    profit_loss_amount=profit_loss
                )

                # v6.1.3: 진화된 전략의 손익 비율 사용 (없으면 기본값)
                if self.strategy_loader and self.strategy_loader.current_strategy:
                    evolved_strategy = self.strategy_loader.current_strategy
                    take_profit_pct = evolved_strategy.sell_take_profit  # 예: 0.10 = 10%
                    stop_loss_pct = evolved_strategy.sell_stop_loss      # 예: -0.05 = -5%

                    logger.info(f"🔍 [VALIDATION CHECK] {stock_name}: 원본 익절={take_profit_pct*100:.1f}%, 손절={stop_loss_pct*100:.1f}%")

                    # CRITICAL FIX: 비정상적인 값 필터링 (정상 범위: 익절 2~30%, 손절 -15~-2%)
                    if not (0.02 <= take_profit_pct <= 0.30):
                        logger.warning(f"⚠️ 비정상적인 익절 비율 감지: {take_profit_pct*100:.1f}% → 기본값 15% 사용")
                        take_profit_pct = 0.15  # 기본 15%

                    if not (-0.15 <= stop_loss_pct <= -0.02):
                        logger.warning(f"⚠️ 비정상적인 손절 비율 감지: {stop_loss_pct*100:.1f}% → 기본값 -5% 사용")
                        stop_loss_pct = -0.05  # 기본 -5%

                    take_profit_price = int(buy_price * (1 + take_profit_pct))
                    stop_loss_price = int(buy_price * (1 + stop_loss_pct))

                    logger.info(f"✅ [VALIDATION RESULT] {stock_name}: 적용 익절={take_profit_pct*100:.1f}% ({take_profit_price:,}원), 손절={stop_loss_pct*100:.1f}% ({stop_loss_price:,}원)")

                    logger.debug(f"진화된 전략 사용: 익절 {take_profit_pct*100:+.1f}% ({take_profit_price:,}원), "
                               f"손절 {stop_loss_pct*100:.1f}% ({stop_loss_price:,}원)")
                else:
                    # 기본 전략 사용 (DynamicRiskManager)
                    thresholds = self.dynamic_risk_manager.get_exit_thresholds(buy_price)
                    take_profit_price = thresholds['take_profit']
                    stop_loss_price = thresholds['stop_loss']

                should_sell = False
                sell_reason = ""

                # Fix: 트레일링 스탑 체크 (우선순위 1)
                if self.trailing_stop_manager and stock_code in self.trailing_stop_manager.states:
                    try:
                        should_sell_ts, reason_ts = self.trailing_stop_manager.update(stock_code, current_price)
                        if should_sell_ts:
                            should_sell = True
                            sell_reason = f"트레일링스탑 {reason_ts}"
                            logger.info(f"🎯 트레일링 스탑 발동: {stock_name} - {reason_ts}")
                    except Exception as e:
                        logger.warning(f"트레일링 스탑 체크 실패: {e}")

                # 기본 손익 체크 (트레일링 스탑이 없거나 발동 안된 경우)
                if not should_sell:
                    if current_price >= take_profit_price:
                        should_sell = True
                        sell_reason = f"익절 ({take_profit_price:,}원)"
                    elif current_price <= stop_loss_price:
                        should_sell = True
                        sell_reason = f"손절 ({stop_loss_price:,}원)"

                if should_sell:
                    logger.info(f"매도 신호: {stock_name} - {sell_reason}")
                    self._execute_sell(stock_code, stock_name, quantity, current_price, profit_loss, profit_loss_rate, sell_reason)

                    # 매도 후 트레일링 스탑 상태 제거
                    if self.trailing_stop_manager and stock_code in self.trailing_stop_manager.states:
                        del self.trailing_stop_manager.states[stock_code]
                        logger.debug(f"트레일링 스탑 제거: {stock_code}")

        except Exception as e:
            logger.error(f"매도 신호 확인 실패: {e}")

    def _run_scanning_pipeline(self):
        try:
            can_add = self.portfolio_manager.can_add_position()
            positions = self.portfolio_manager.get_positions()
            if not can_add:
                logger.info("최대 포지션 도달")
                return

            current_positions = len(positions)
            should_open = self.dynamic_risk_manager.should_open_position(current_positions)

            if not should_open:
                logger.info("리스크 관리자: 포지션 진입 불가")
                return

            logger.info("시장 스캔 시작...")
            print("\n" + "="*80)
            print("시장 스캔 파이프라인")
            print("="*80)

            candidates = self.scanner.scan_market()

            if not candidates:
                print("스캔 완료: 후보 종목 없음")
                logger.info("스캔 완료: 후보 종목 없음")
                return

            candidate_scores = {}
            for candidate in candidates:
                stock_data = {
                    'stock_code': candidate.code,
                    'stock_name': candidate.name,
                    'current_price': candidate.price,
                    'volume': candidate.volume,
                    'change_rate': candidate.rate,
                    'institutional_net_buy': candidate.institutional_net_buy,
                    'foreign_net_buy': candidate.foreign_net_buy,
                    'bid_ask_ratio': candidate.bid_ask_ratio,
                    'institutional_trend': getattr(candidate, 'institutional_trend', None),
                    'avg_volume': getattr(candidate, 'avg_volume', None),
                    'volatility': getattr(candidate, 'volatility', None),
                    'top_broker_buy_count': getattr(candidate, 'top_broker_buy_count', 0),
                    'top_broker_net_buy': getattr(candidate, 'top_broker_net_buy', 0),
                    'execution_intensity': getattr(candidate, 'execution_intensity', None),
                    'program_net_buy': getattr(candidate, 'program_net_buy', None),
                }

                scoring_result = self.scoring_system.calculate_score(stock_data, scan_type='default')
                candidate_scores[candidate.code] = scoring_result
                candidate.final_score = scoring_result.total_score

            candidates.sort(key=lambda x: x.final_score, reverse=True)

            top5 = candidates[:5]
            print(f"\nTop 5 Candidates:")

            for rank, c in enumerate(top5, 1):
                score_result = candidate_scores[c.code]
                percentage = (c.final_score / 440) * 100
                print(f"   {rank}. {c.name} - {c.final_score:.0f}점 ({percentage:.0f}%)")

            portfolio_info = "No positions"

            if self.order_tracker:
                self.order_tracker.sync_with_api()
                self.order_tracker.cleanup_expired()

            top10 = candidates[:10]
            analysis_candidates = [
                c for c in top10
                if not self.portfolio_manager.has_position(c.code)
                and not (self.order_tracker and self.order_tracker.has_pending_order(c.code))
            ][:5]

            if not analysis_candidates:
                print("⚠️  분석할 새 종목 없음 (상위 10개 모두 보유/주문 중)")
                return

            bought_count = 0
            max_buys_per_scan = BUY_SCORE_THRESHOLDS['max_buys_per_scan']

            for idx, candidate in enumerate(analysis_candidates, 1):
                print(f"\n[{idx}/{len(analysis_candidates)}] {candidate.name} ({candidate.code})")

                scoring_result = candidate_scores[candidate.code]

                # OpenAPI 종합 데이터 조회
                openapi_features = {}
                if self.openapi_client and self.openapi_client.is_connected:
                    try:
                        print(f"   📊 OpenAPI 데이터 조회 중...")
                        comprehensive_data = self.openapi_client.get_comprehensive_data(candidate.code)
                        if comprehensive_data:
                            openapi_features = self.openapi_client.extract_openapi_features(comprehensive_data)
                            success_count = comprehensive_data.get('success_count', 0)
                            total_count = comprehensive_data.get('total_count', 0)
                            print(f"   ✅ OpenAPI 데이터: {success_count}/{total_count} 수집")
                        else:
                            print(f"   ⚠️  OpenAPI 데이터 조회 실패")
                    except Exception as e:
                        logger.warning(f"OpenAPI 데이터 조회 실패 ({candidate.code}): {e}")
                        print(f"   ⚠️  OpenAPI 데이터 조회 오류: {e}")

                stock_data = {
                    'stock_code': candidate.code,
                    'stock_name': candidate.name,
                    'current_price': candidate.price,
                    'volume': candidate.volume,
                    'change_rate': candidate.rate,
                    'institutional_net_buy': candidate.institutional_net_buy,
                    'foreign_net_buy': candidate.foreign_net_buy,
                    'bid_ask_ratio': candidate.bid_ask_ratio,
                    'institutional_trend': getattr(candidate, 'institutional_trend', None),
                    **openapi_features  # OpenAPI 데이터 병합
                }

                score_info = {
                    'score': scoring_result.total_score,
                    'max_score': 440,
                    'percentage': scoring_result.percentage,
                    'breakdown': {
                        'Volume Surge (60 max)': scoring_result.volume_surge_score,
                        'Price Momentum (60 max)': scoring_result.price_momentum_score,
                        'Institutional Buying (60 max)': scoring_result.institutional_buying_score,
                        'Bid Strength (40 max)': scoring_result.bid_strength_score,
                        'Execution Intensity (40 max)': scoring_result.execution_intensity_score,
                        'Broker Activity (40 max)': scoring_result.broker_activity_score,
                        'Program Trading (40 max)': scoring_result.program_trading_score,
                        'Technical Indicators (40 max)': scoring_result.technical_indicators_score,
                        'Market Momentum (40 max)': scoring_result.theme_news_score,
                        'Volatility Pattern (20 max)': scoring_result.volatility_pattern_score,
                    }
                }

                # Fix: AI 분석 디버깅 강화
                try:
                    print(f"\n   🤖 AI 분석 시작...")
                    logger.info(f"AI 분석 시작: {candidate.name} (점수: {scoring_result.total_score})")

                    ai_analysis = self.analyzer.analyze_stock(
                        stock_data,
                        score_info=score_info,
                        portfolio_info=portfolio_info
                    )

                    if not ai_analysis:
                        logger.error(f"AI 분석 결과 없음: {candidate.name}")
                        print(f"   ❌ AI 분석 실패 - 결과 없음")
                        continue

                    ai_signal = ai_analysis.get('signal', 'hold')
                    split_strategy = ai_analysis.get('split_strategy', '')

                    logger.info(f"AI 분석 완료: {candidate.name} → {ai_signal} (전략: {split_strategy})")

                except Exception as e:
                    logger.error(f"AI 분석 예외 발생: {candidate.name} - {e}", exc_info=True)
                    print(f"   ❌ AI 분석 오류: {e}")
                    continue

                candidate.ai_signal = ai_signal
                candidate.ai_reasons = ai_analysis.get('reasons', [])

                print(f"\n   AI Decision: {ai_signal.upper()}")

                if ai_signal == 'buy' and split_strategy:
                    print(f"   Split Strategy: {split_strategy}")

                if ai_analysis.get('reasons'):
                    print(f"   Reason: {ai_analysis['reasons'][0]}")

                if ai_analysis.get('risks') and ai_analysis['risks']:
                    print(f"   Warning: {ai_analysis['risks'][0]}")

                if ai_signal == 'buy':
                    buy_candidate = {
                        'stock_code': candidate.code,
                        'stock_name': candidate.name,
                        'current_price': candidate.price,
                        'change_rate': candidate.rate,
                        'score': scoring_result.total_score,
                        'split_strategy': split_strategy,
                        'ai_reason': ai_analysis.get('reasons', [''])[0] if ai_analysis.get('reasons') else '',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    self.ai_approved_candidates.insert(0, buy_candidate)
                    self.ai_approved_candidates = self.ai_approved_candidates[:10]

                buy_approved = (
                    (ai_signal == 'buy' and scoring_result.total_score >= BUY_SCORE_THRESHOLDS['ai_buy']) or
                    (ai_signal == 'hold' and scoring_result.total_score >= BUY_SCORE_THRESHOLDS['ai_hold'])
                )

                # 매수 조건 평가 로깅
                logger.info(f"매수 조건 평가: {candidate.name} - AI={ai_signal}, 점수={scoring_result.total_score}, 승인={buy_approved}")
                print(f"   📊 매수 평가: AI={ai_signal}, 점수={scoring_result.total_score:.0f}, 승인={'✅' if buy_approved else '❌'}")

                if buy_approved:
                    # 중복 매수 방지: 이미 보유한 종목인지 확인
                    if self.portfolio_manager.has_position(candidate.code):
                        logger.info(f"⚠️  {candidate.name}({candidate.code}) 이미 보유 중 - 중복 매수 방지")
                        print(f"⚠️  이미 보유 중인 종목 - 매수 건너뜀")
                        continue

                    # 최대 포지션 수 확인
                    if not self.portfolio_manager.can_add_position():
                        logger.warning(f"최대 포지션 수({self.portfolio_manager.max_positions}) 도달 - 매수 불가")
                        print(f"최대 포지션 수 도달 - 매수 건너뜀")
                        break

                    # 이번 스캔에서 이미 최대 매수 개수에 도달했는지 확인
                    if bought_count >= max_buys_per_scan:
                        logger.info(f"한 스캔당 최대 매수 개수({max_buys_per_scan}) 도달 - 더 이상 매수 안 함")
                        print(f"✋ 한 스캔당 최대 매수 개수 도달 - 나머지 후보 분석만 진행")
                        continue

                    print(f"매수 조건 충족 - 주문 실행 중")

                    self._execute_buy(candidate, scoring_result)
                    bought_count += 1

                    if self.virtual_trader:
                        try:
                            volume = getattr(candidate, 'volume', 0)
                            avg_volume = getattr(candidate, 'avg_volume', None)

                            stock_data = {
                                'stock_code': candidate.code,
                                'stock_name': candidate.name,
                                'current_price': candidate.price,
                                'change_rate': candidate.rate,
                                'volume': volume,
                                'institutional_net_buy': getattr(candidate, 'institutional_net_buy', 0),
                                'foreign_net_buy': getattr(candidate, 'foreign_net_buy', 0),
                                'bid_ask_ratio': getattr(candidate, 'bid_ask_ratio', 0),
                                'institutional_trend': getattr(candidate, 'institutional_trend', None),
                                'avg_volume': avg_volume,
                                'volatility': getattr(candidate, 'volatility', None),
                                'top_broker_buy_count': getattr(candidate, 'top_broker_buy_count', 0),
                                'top_broker_net_buy': getattr(candidate, 'top_broker_net_buy', 0),
                                'execution_intensity': getattr(candidate, 'execution_intensity', None),
                                'program_net_buy': getattr(candidate, 'program_net_buy', None),
                                'price_change_percent': candidate.rate,
                                'volume_ratio': (volume / avg_volume) if avg_volume and avg_volume > 0 else 1.0,
                            }

                            market_data = {
                                'fear_greed_index': 50,
                                'economic_cycle': 'expansion',
                                'market_trend': 'neutral',
                            }

                            ai_analysis_data = {
                                'signal': ai_signal,
                                'split_strategy': split_strategy,
                                'reasons': ai_analysis.get('reasons', []),
                                'score': scoring_result.total_score,
                            }
                            self.virtual_trader.process_buy_signal(stock_data, ai_analysis_data, market_data)
                            print(f"   Virtual trading: Signal processed")
                        except Exception as e:
                            logger.warning(f"가상매매 실패: {e}")

                    # break 제거: 모든 후보 분석을 위해 계속 진행
                    # 매수 개수는 위에서 bought_count로 제어됨
                else:
                    reason_text = f"AI={ai_signal}, 점수={scoring_result.total_score:.0f}"
                    print(f"매수 조건 미충족 ({reason_text})")

            print("스캔 전략 완료")

        except Exception as e:
            logger.error(f"스캔 전략 실패: {e}", exc_info=True)
            print(f"스캔 전략 오류: {e}")
            import traceback
            traceback.print_exc()

    def _get_optimal_buy_price(self, stock_code, current_price):
        """
        호가 분석 기반 최적 매수 가격 계산
        매수호가 중에서 유리한 가격 선택 (낮은 가격)
        """
        try:
            orderbook = self.data_fetcher.get_orderbook(stock_code)
            if not orderbook or 'bids' not in orderbook:
                logger.warning(f"{stock_code} 호가 정보 없음, 현재가 사용")
                return current_price

            bids = orderbook['bids'][:5]  # 상위 5개 매수호가
            if not bids:
                return current_price

            # 매수호가 중 가장 높은 가격 (1호가) 사용
            # 체결 확률을 높이면서도 시장가보다 낮은 가격
            best_bid = bids[0]['price']

            # 현재가보다 높으면 현재가 사용
            if best_bid > current_price:
                optimal_price = current_price
            else:
                # 1호가와 2호가 사이 가격 사용
                if len(bids) >= 2:
                    second_bid = bids[1]['price']
                    optimal_price = best_bid  # 1호가 사용 (체결 우선)
                else:
                    optimal_price = best_bid

            logger.info(f"매수 가격 최적화: {current_price:,}원 → {optimal_price:,}원 (호가 분석)")
            return optimal_price

        except Exception as e:
            logger.warning(f"최적 매수 가격 계산 실패: {e}")
            return current_price

    def _get_optimal_sell_price(self, stock_code, current_price):
        """
        호가 분석 기반 최적 매도 가격 계산
        현재가보다 약간 높게 설정하여 매도 체결 확률 향상
        """
        try:
            orderbook = self.data_fetcher.get_orderbook(stock_code)
            if not orderbook or 'asks' not in orderbook or 'bids' not in orderbook:
                # 호가 정보 없으면 현재가의 101% 사용 (약간 높게)
                optimal_price = int(current_price * 1.01)
                logger.warning(f"{stock_code} 호가 정보 없음, 현재가의 101% 사용: {optimal_price:,}원")
                return optimal_price

            asks = orderbook['asks'][:5]  # 상위 5개 매도호가
            bids = orderbook['bids'][:5]  # 상위 5개 매수호가

            if not asks or not bids:
                # 현재가의 101% 사용
                optimal_price = int(current_price * 1.01)
                logger.info(f"매도 가격 최적화: {current_price:,}원 → {optimal_price:,}원 (현재가 +1%)")
                return optimal_price

            # 매수 1호가 (가장 높은 매수 호가)
            best_bid = bids[0]['price']

            # 매도 1호가 (가장 낮은 매도 호가)
            best_ask = asks[0]['price']

            # 전략: 매수 1호가보다 약간 높게, 하지만 매도 1호가보다는 낮게
            # 체결 확률을 높이면서도 유리한 가격 확보
            if best_bid > 0:
                # 매수 1호가의 101% ~ 102% 사이
                optimal_price = int(best_bid * 1.015)  # 1.5% 높게

                # 현재가보다 낮아지면 안됨
                if optimal_price < current_price:
                    optimal_price = int(current_price * 1.01)

                # 매도 1호가보다 높아지면 안됨 (체결 확률 낮아짐)
                if optimal_price > best_ask:
                    optimal_price = best_ask
            else:
                # 매수호가가 없으면 현재가의 101% 사용
                optimal_price = int(current_price * 1.01)

            logger.info(f"매도 가격 최적화: {current_price:,}원 → {optimal_price:,}원 (호가 분석, 매수1호가 {best_bid:,}원 기준 +1.5%)")
            return optimal_price

        except Exception as e:
            logger.warning(f"최적 매도 가격 계산 실패: {e}")
            # 실패 시 현재가의 101% 사용
            return int(current_price * 1.01)

    def _execute_buy(self, candidate, scoring_result):
        try:
            if self.market_status.get('can_cancel_only'):
                logger.warning(f"{self.market_status['market_type']}: 신규 매수 주문 불가")
                return

            # v8.0: 긴급 정지 확인
            if self.emergency_controller and not self.emergency_controller.is_new_buy_allowed():
                logger.warning(f"🚨 긴급 정지 활성화 - 신규 매수 차단 (수준: {self.emergency_controller.current_level.value})")
                return

            stock_code = candidate.code
            stock_name = candidate.name
            current_price = candidate.price

            # Fix: 매수 직전 중복 방지 재확인
            # 1. 보유 종목 확인 (최신 API 데이터)
            if self.portfolio_manager.has_position(stock_code):
                logger.warning(f"⚠️ 중복 매수 방지: {stock_name}({stock_code}) 이미 보유 중")
                return

            # 2. 미체결 주문 확인 (강제 동기화)
            if self.order_tracker:
                self.order_tracker.sync_with_api(force=True)  # 강제 동기화
                if self.order_tracker.has_pending_order(stock_code):
                    logger.warning(f"⚠️ 중복 매수 방지: {stock_name}({stock_code}) 미체결 주문 존재")
                    return

            # 3. 실시간 보유 종목 재확인 (API 직접 호출)
            try:
                holdings = self.account_api.get_holdings()
                if holdings:
                    for holding in holdings:
                        holding_code = holding.get('stk_cd') or holding.get('pdno', '')
                        if holding_code == stock_code:
                            logger.warning(f"⚠️ 중복 매수 방지: {stock_name}({stock_code}) 실시간 보유 확인")
                            return
            except Exception as e:
                logger.debug(f"보유 종목 재확인 중 오류 (무시): {e}")

            # 호가 분석 기반 최적 매수 가격 계산
            optimal_price = self._get_optimal_buy_price(stock_code, current_price)

            deposit = self.account_api.get_deposit()
            holdings = self.account_api.get_holdings()

            # Fix v6.1.5: 100% 주문가능금액 사용 (ord_alow_amt → 100stk_ord_alow_amt)
            available_cash = int(str(deposit.get('100stk_ord_alow_amt', '0')).replace(',', '')) if deposit else 0

            logger.info(f"💰 사용 가능 현금: {available_cash:,}원, 현재가: {optimal_price:,}원")

            # v6.1.3: 진화된 전략의 포지션 크기 사용 (없으면 기본값)
            if self.strategy_loader and self.strategy_loader.current_strategy:
                evolved_strategy = self.strategy_loader.current_strategy
                position_size_pct = evolved_strategy.position_size_pct  # 예: 0.10 = 10%
                target_amount = int(available_cash * position_size_pct)
                quantity = target_amount // optimal_price

                logger.info(f"📊 진화된 전략 사용: 포지션 크기 {position_size_pct*100:.1f}% = {target_amount:,}원 → {quantity}주")
            else:
                # 기본 전략 사용 (DynamicRiskManager)
                quantity = self.dynamic_risk_manager.calculate_position_size(
                    stock_price=optimal_price,
                    available_cash=available_cash
                )
                logger.info(f"📊 기본 전략 사용: {quantity}주")

            if quantity == 0:
                logger.warning(f"⚠️ 매수 수량 0 (현금: {available_cash:,}원, 가격: {optimal_price:,}원)")
                return

            total_amount = optimal_price * quantity

            # v8.0: 4단계 리스크 검증 파이프라인
            if self.risk_pipeline:
                try:
                    # 포트폴리오 정보 수집
                    portfolio_value = self.portfolio_manager.get_total_value() if self.portfolio_manager else available_cash
                    current_positions = len(self.portfolio_manager.positions) if self.portfolio_manager else 0

                    validation_result = self.risk_pipeline.validate_order(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        order_type='buy',
                        quantity=quantity,
                        price=optimal_price,
                        portfolio_value=portfolio_value,
                        current_positions=current_positions
                    )

                    if not validation_result.passed:
                        logger.warning(f"🛡️ 리스크 검증 실패: {stock_name}")
                        for msg in validation_result.messages:
                            logger.warning(f"   - {msg}")
                        if self.event_bus:
                            self.event_bus.emit_risk_warning(
                                f"매수 차단: {stock_name}",
                                validation_result.risk_level,
                                {'reason': validation_result.messages}
                            )
                        return

                    logger.info(f"✅ 리스크 검증 통과: {stock_name} (수준: {validation_result.risk_level})")
                except Exception as e:
                    logger.warning(f"리스크 검증 오류 (무시하고 진행): {e}")

            strategy_note = "진화된 전략" if (self.strategy_loader and self.strategy_loader.current_strategy) else "기본 전략"
            logger.info(
                f"{stock_name} 매수 주문: {quantity}주 @ {optimal_price:,}원 "
                f"(합계 {total_amount:,}원, {strategy_note})"
            )

            from utils.trading_date import is_nxt_hours
            from datetime import datetime

            if is_nxt_hours():
                now = datetime.now()
                if now.hour == 8:
                    order_type = '61'
                    logger.info("장 시작 전 시간외: Type 61")
                else:
                    order_type = '81'
                    logger.info("장 마감 후 시간외: Type 81")
            else:
                order_type = '0'
                logger.info("일반 지정가 주문: Type 0")

            if self.market_status.get('is_test_mode'):
                logger.info(f"테스트 모드: AI 검토 완료 -> 실제 매수 API 호출")
                logger.info(f"   Stock: {stock_name}, AI score: {candidate.ai_score}, Total score: {scoring_result.total_score}")

            # Fix: 매수 시작 전 임시 주문 등록 (중복 방지)
            temp_order_no = f"pending_{stock_code}_{datetime.now().strftime('%H%M%S%f')}"
            if self.order_tracker:
                self.order_tracker.register_order(temp_order_no, stock_code, 'buy', quantity, optimal_price)
                logger.info(f"📝 임시 주문 등록: {temp_order_no}")

            # 거래 로거에 매수 시도 기록
            trade_log_id = log_buy(
                stock_code=stock_code,
                stock_name=stock_name,
                quantity=quantity,
                price=optimal_price,
                strategy_name=strategy_note,
                ai_signal=getattr(candidate, 'ai_signal', ''),
                score=scoring_result.total_score if scoring_result else 0,
                reason=f"AI Score: {getattr(candidate, 'ai_score', 0)}"
            )

            # Fix v6.1.3: AI 기반 적응형 분할 매수 사용
            if self.ai_adaptive_split_executor:
                logger.info(f"🤖 AI 기반 적응형 분할 매수 실행: {stock_name} {quantity}주 @ {optimal_price:,}원")

                # Fix: NXT 시간대 체크
                exchange = 'NXT' if is_nxt_hours() else 'KRX'

                order_result = self.ai_adaptive_split_executor.execute_adaptive_split_buy(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    total_quantity=quantity,
                    target_budget=optimal_price * quantity,
                    num_splits=3,
                    max_wait_seconds=30,  # 30초 대기 (빠른 진행)
                    account_number=None,
                    exchange=exchange
                )
            elif self.split_order_executor:
                # Fallback: 기존 분할 매수
                logger.info(f"🔀 분할 매수 실행: {stock_name} {quantity}주 @ {optimal_price:,}원 (주문유형: {order_type})")
                # Fix v6.1.5: order_type 전달 (장 종료 후 시간외 주문 지원)
                order_result = self.split_order_executor.execute_split_buy(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    total_quantity=quantity,
                    entry_strategy="gradual_down",  # 점진적 하락 시 분할 매수
                    num_splits=3,                    # 3회 분할
                    order_type=order_type            # 계산된 주문 유형 전달
                )
            else:
                # Fallback: 일반 매수
                order_result = self.order_api.buy(
                    stock_code=stock_code,
                    quantity=quantity,
                    price=optimal_price,
                    order_type=order_type
                )

            # Fix v6.1.3: 가상매매도 동시 실행
            if self.virtual_trading_manager and order_result:
                try:
                    # 활성 전략 중 첫 번째에 가상매매 실행
                    strategies = self.virtual_trading_manager.db.get_all_strategies()
                    if not strategies:
                        logger.warning("⚠️ 가상매매 전략이 없습니다 - 슬롯을 생성해주세요")
                    else:
                        first_strategy = strategies[0]
                        logger.info(f"🎯 가상매매 실행 시도: {stock_name} (전략: {first_strategy['name']})")

                        result = self.virtual_trading_manager.execute_buy(
                            strategy_id=first_strategy['id'],
                            stock_code=stock_code,
                            stock_name=stock_name,
                            quantity=quantity,
                            price=float(optimal_price),
                            stop_loss_percent=5.0,  # 5% 손절
                            take_profit_percent=10.0,  # 10% 익절
                            use_split=True  # 가상매매도 분할 매수
                        )

                        if result:
                            logger.info(f"✅ 가상매매 동시 실행 성공: {stock_name} ({first_strategy['name']})")
                        else:
                            logger.warning(f"⚠️ 가상매매 실행 실패 (결과 None): {stock_name}")
                except Exception as e:
                    logger.error(f"❌ 가상매매 실행 실패: {e}", exc_info=True)

            if order_result:
                from strategy.split_order_manager import SplitOrderGroup
                if isinstance(order_result, SplitOrderGroup):
                    order_no = order_result.group_id
                    if order_result.entries and len(order_result.entries) > 0:
                        first_entry = order_result.entries[0]
                        if hasattr(first_entry, 'order_number') and first_entry.order_number:
                            order_no = first_entry.order_number
                    logger.info(f"분할 매수 완료: {len(order_result.entries)}개 주문")
                else:
                    order_no = order_result.get('order_no', '') if isinstance(order_result, dict) else ''

                # Fix: 임시 주문을 실제 주문으로 교체
                # CRITICAL: 실제 주문을 먼저 등록한 후 임시 주문 제거 (중복 매수 방지)
                if self.order_tracker:
                    # 실제 주문번호로 먼저 등록 (pending_stocks에서 제거되지 않도록)
                    if order_no:
                        self.order_tracker.register_order(order_no, stock_code, 'buy', quantity, optimal_price)
                        logger.info(f"✅ 실제 주문 등록: {order_no}")
                    # 임시 주문 제거 (이제 실제 주문이 있으므로 안전)
                    self.order_tracker.update_status(temp_order_no, OrderStatus.FILLED)
                trade = Trade(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    action='buy',
                    quantity=quantity,
                    price=optimal_price,
                    total_amount=total_amount,
                    risk_mode=self.dynamic_risk_manager.current_mode.value,
                    ai_score=candidate.ai_score,
                    ai_signal=candidate.ai_signal,
                    ai_confidence=candidate.ai_confidence,
                    scoring_total=scoring_result.total_score,
                    scoring_percentage=scoring_result.percentage,
                    is_virtual=False  # v6.1.1: Mark as real trade
                )
                self.db_session.add(trade)
                self.db_session.commit()

                logger.info(f"{stock_name} 매수 성공 (주문번호: {order_no})")

                # 거래 로거에 성공 기록
                if trade_log_id:
                    log_success(trade_log_id, order_no, optimal_price, quantity)

                # v8.0: 이벤트 버스 알림
                if self.event_bus:
                    self.event_bus.emit_order_filled(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        order_type='buy',
                        quantity=quantity,
                        price=optimal_price,
                        order_no=order_no
                    )

                # v8.0: 성능 분석기 기록
                if self.performance_analyzer:
                    self.performance_analyzer.record_trade(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        trade_type='buy',
                        quantity=quantity,
                        price=optimal_price,
                        strategy_name=strategy_note,
                        ai_score=getattr(candidate, 'ai_score', 0)
                    )

                # Fix: 트레일링 스탑 추가 (ATR 기반 동적 손절/익절)
                if self.trailing_stop_manager:
                    try:
                        # ATR 값 추정 (가격의 2% 또는 변동성 기반)
                        volatility = getattr(candidate, 'volatility', None)
                        if volatility and volatility > 0:
                            atr_value = optimal_price * volatility * 0.5  # 변동성의 50%
                        else:
                            atr_value = optimal_price * 0.02  # 기본 2%

                        self.trailing_stop_manager.add_position(
                            stock_code=stock_code,
                            entry_price=optimal_price,
                            atr_value=atr_value,
                            initial_stop_loss_pct=0.05,  # 5% 손절
                            initial_take_profit_pct=0.10  # 10% 익절
                        )
                        logger.info(f"🎯 트레일링 스탑 설정: {stock_name} (ATR: {atr_value:,.0f}원)")
                    except Exception as e:
                        logger.warning(f"트레일링 스탑 설정 실패: {e}")

                self.alert_manager.alert_position_opened(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    buy_price=current_price,
                    quantity=quantity
                )

                self.monitor.log_activity(
                    'buy',
                    f'{stock_name} buy: {quantity}@{current_price:,}',
                    level='success'
                )
            else:
                # 주문 실패 시 임시 주문 취소 처리
                if self.order_tracker:
                    self.order_tracker.update_status(temp_order_no, OrderStatus.CANCELLED)
                    logger.warning(f"❌ 주문 실패 - 임시 주문 취소: {temp_order_no}")

                # 거래 로거에 실패 기록
                if trade_log_id:
                    log_failure(trade_log_id, "주문 실행 실패 (order_result None)")

        except Exception as e:
            logger.error(f"매수 실행 실패: {e}", exc_info=True)
            # 거래 로거에 예외 기록
            if 'trade_log_id' in locals() and trade_log_id:
                log_failure(trade_log_id, str(e))

    def _execute_sell(self, stock_code, stock_name, quantity, price, profit_loss, profit_loss_rate, reason):
        try:
            if self.market_status.get('can_cancel_only'):
                logger.warning(f"{self.market_status['market_type']}: 신규 매도 주문 불가")
                return

            # v8.0: 긴급 정지 시에도 매도는 허용 (손절을 위해)
            if self.emergency_controller and not self.emergency_controller.can_sell():
                logger.warning(f"🚨 시스템 종료 상태 - 매도도 차단됨 (수준: {self.emergency_controller.current_level.value})")
                return

            # 호가 분석 기반 최적 매도 가격 계산
            optimal_price = self._get_optimal_sell_price(stock_code, price)

            # 손익 재계산 (최적화된 가격 기준)
            if optimal_price != price:
                holdings = self.account_api.get_holdings()
                for h in holdings:
                    if h.get('stk_cd', '').replace('A', '').replace('_NX', '') == stock_code:
                        avg_price = int(float(str(h.get('avg_prc', 0)).replace(',', '')))
                        profit_loss = (optimal_price - avg_price) * quantity
                        profit_loss_rate = ((optimal_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
                        break

            logger.info(
                f"{stock_name} 매도 주문: {quantity}주 @ {optimal_price:,}원 "
                f"(손익: {profit_loss:+,}원, {profit_loss_rate:+.2f}%, 호가 분석 최적화)"
            )

            # 매수 시 평균가 조회 (손익 계산용)
            buy_price = 0
            try:
                holdings = self.account_api.get_holdings()
                for h in holdings:
                    if h.get('stk_cd', '').replace('A', '').replace('_NX', '') == stock_code:
                        buy_price = int(float(str(h.get('avg_prc', 0)).replace(',', '')))
                        break
            except Exception:
                pass

            # 거래 로거에 매도 시도 기록
            sell_trade_log_id = log_sell(
                stock_code=stock_code,
                stock_name=stock_name,
                quantity=quantity,
                price=optimal_price,
                reason=reason,
                buy_price=buy_price
            )

            from utils.trading_date import is_nxt_hours
            from datetime import datetime

            if is_nxt_hours():
                now = datetime.now()
                if now.hour == 8:
                    order_type = '61'
                    logger.info("장 시작 전 시간외 매도: Type 61")
                else:
                    order_type = '81'
                    logger.info("장 마감 후 시간외 매도: Type 81")
            else:
                order_type = '0'
                logger.info("일반 시장 매도: Type 0")

            if self.market_status.get('is_test_mode'):
                logger.info(f"테스트 모드: 매도 조건 충족 -> 실제 매도 API 호출")
                logger.info(f"   Stock: {stock_name}, Reason: {reason}, P/L: {profit_loss:+,} ({profit_loss_rate:+.2f}%)")

            # Fix v6.1.3: AI 기반 적응형 분할 매도 사용
            if self.ai_adaptive_split_executor:
                logger.info(f"🤖 AI 기반 적응형 분할 매도 실행: {stock_name} {quantity}주")

                # 평균 매수가 조회
                avg_price = 0
                holdings = self.account_api.get_holdings()
                for h in holdings:
                    if h.get('stk_cd', '').replace('A', '').replace('_NX', '') == stock_code:
                        avg_price = int(float(str(h.get('avg_prc', 0)).replace(',', '')))
                        break

                if avg_price == 0:
                    logger.warning(f"평균 매수가를 찾을 수 없음, 현재가를 진입가로 사용: {optimal_price}")
                    avg_price = optimal_price

                # Fix: NXT 시간대 체크
                exchange = 'NXT' if is_nxt_hours() else 'KRX'

                order_result = self.ai_adaptive_split_executor.execute_adaptive_split_sell(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    total_quantity=quantity,
                    entry_price=avg_price,
                    num_splits=3,
                    max_wait_seconds=30,  # 30초 대기 (빠른 진행)
                    account_number=None,
                    exchange=exchange
                )
            elif self.split_order_executor:
                # Fallback: 기존 분할 매도
                logger.info(f"🔀 분할 매도 실행: {stock_name} {quantity}주")

                # 평균 매수가 조회
                avg_price = 0
                holdings = self.account_api.get_holdings()
                for h in holdings:
                    if h.get('stk_cd', '').replace('A', '').replace('_NX', '') == stock_code:
                        avg_price = int(float(str(h.get('avg_prc', 0)).replace(',', '')))
                        break

                if avg_price == 0:
                    logger.warning(f"평균 매수가를 찾을 수 없음, 현재가를 진입가로 사용: {optimal_price}")
                    avg_price = optimal_price

                order_result = self.split_order_executor.execute_split_sell(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    total_quantity=quantity,
                    entry_price=avg_price,  # Fix: target_price → entry_price (평균 매수가)
                    account_number=None
                )
            else:
                # Fallback: 일반 매도
                # Fix: NXT 시간대면 exchange 파라미터 전달
                exchange = 'NXT' if is_nxt_hours() else 'KRX'
                order_result = self.order_api.sell(
                    stock_code=stock_code,
                    quantity=quantity,
                    price=optimal_price,
                    order_type=order_type,
                    exchange=exchange
                )

            # Fix v6.1.3: 가상매매 포지션 찾아서 동시 매도
            if self.virtual_trading_manager and order_result:
                try:
                    positions = self.virtual_trading_manager.get_positions()
                    # 같은 종목 포지션 찾기
                    found_position = False
                    for pos in positions:
                        if pos['stock_code'] == stock_code:
                            found_position = True
                            logger.info(f"🎯 가상매매 매도 시도: {stock_name} (포지션 ID: {pos['id']})")

                            result = self.virtual_trading_manager.execute_sell(
                                position_id=pos['id'],
                                sell_price=float(optimal_price),
                                reason=reason,
                                use_split=True  # 가상매매도 분할 매도
                            )

                            if result:
                                logger.info(f"✅ 가상매매 동시 매도 성공: {stock_name} (포지션 ID: {pos['id']})")
                            else:
                                logger.warning(f"⚠️ 가상매매 매도 실패 (결과 None): {stock_name}")
                            break

                    if not found_position:
                        logger.debug(f"가상매매 포지션 없음: {stock_name} - 실제 매도만 실행")
                except Exception as e:
                    logger.error(f"❌ 가상매매 매도 실패: {e}", exc_info=True)

            if order_result:
                # Fix: SplitOrderGroup vs 딕셔너리 구분
                from strategy.split_order_manager import SplitOrderGroup
                if isinstance(order_result, SplitOrderGroup):
                    # 분할 주문의 경우 group_id 또는 첫 번째 entry의 order_number 사용
                    order_no = order_result.group_id
                    if order_result.entries and len(order_result.entries) > 0:
                        first_entry = order_result.entries[0]
                        if hasattr(first_entry, 'order_number') and first_entry.order_number:
                            order_no = first_entry.order_number
                    logger.info(f"분할 매도 완료: {len(order_result.entries)}개 주문 생성 (그룹 ID: {order_result.group_id})")
                else:
                    # 일반 주문의 경우
                    order_no = order_result.get('order_no', '') if isinstance(order_result, dict) else ''

                trade = Trade(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    action='sell',
                    quantity=quantity,
                    price=optimal_price,
                    total_amount=optimal_price * quantity,
                    profit_loss=profit_loss,
                    profit_loss_ratio=profit_loss_rate / 100,
                    risk_mode=self.dynamic_risk_manager.current_mode.value,
                    notes=reason,
                    is_virtual=False  # v6.1.1: Mark as real trade
                )
                self.db_session.add(trade)
                self.db_session.commit()

                log_level = 'success' if profit_loss >= 0 else 'warning'
                logger.info(f"{stock_name} 매도 성공 (주문번호: {order_no})")

                # 거래 로거에 성공 기록
                if sell_trade_log_id:
                    log_success(sell_trade_log_id, order_no, optimal_price, quantity)

                # v8.0: 이벤트 버스 알림
                if self.event_bus:
                    self.event_bus.emit_order_filled(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        order_type='sell',
                        quantity=quantity,
                        price=optimal_price,
                        order_no=order_no
                    )

                # v8.0: 성능 분석기 기록
                if self.performance_analyzer:
                    self.performance_analyzer.record_trade(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        trade_type='sell',
                        quantity=quantity,
                        price=optimal_price,
                        profit_loss=profit_loss,
                        profit_loss_pct=profit_loss_rate,
                        strategy_name=reason
                    )

                # v8.0: 긴급 정지 컨트롤러에 일일 손실 체크
                if self.emergency_controller and profit_loss < 0:
                    portfolio_value = self.portfolio_manager.get_total_value() if self.portfolio_manager else 10000000
                    self.emergency_controller.check_daily_loss(profit_loss, portfolio_value)

                self.alert_manager.alert_position_closed(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    sell_price=optimal_price,
                    profit_loss_rate=profit_loss_rate,
                    profit_loss_amount=profit_loss,
                    reason=reason
                )

                self.monitor.log_activity(
                    'sell',
                    f'{stock_name} sell: {quantity}@{optimal_price:,} (P/L: {profit_loss:+,})',
                    level=log_level
                )

        except Exception as e:
            logger.error(f"매도 실행 실패: {e}", exc_info=True)
            # 거래 로거에 예외 기록
            if 'sell_trade_log_id' in locals() and sell_trade_log_id:
                log_failure(sell_trade_log_id, str(e))

    def _save_portfolio_snapshot(self):
        try:
            summary = self.portfolio_manager.get_portfolio_summary()

            snapshot = PortfolioSnapshot(
                total_capital=summary['total_assets'],
                cash=summary['cash'],
                stock_value=summary['stocks_value'],
                total_profit_loss=summary['total_profit_loss'],
                total_profit_loss_ratio=summary['total_profit_loss_rate'] / 100,
                open_positions=summary['position_count'],
                risk_mode=self.dynamic_risk_manager.current_mode.value
            )

            self.db_session.add(snapshot)
            self.db_session.commit()

        except Exception as e:
            logger.error(f"포트폴리오 스냅샷 저장 실패: {e}")

    def _get_virtual_trading_prices(self) -> dict:
        try:
            if not self.virtual_trader:
                return {}

            all_stock_codes = set()
            for account in self.virtual_trader.accounts.values():
                all_stock_codes.update(account.positions.keys())

            if not all_stock_codes:
                return {}

            from utils.nxt_realtime_price import get_nxt_price_manager
            nxt_manager = get_nxt_price_manager(self.market_api)

            price_data = {}
            for stock_code in all_stock_codes:
                try:
                    price_info = nxt_manager.get_realtime_price(stock_code)
                    if price_info:
                        price_data[stock_code] = price_info['current_price']
                        if price_info.get('is_nxt_hours'):
                            logger.debug(f"NXT real-time price: {stock_code} {price_info['current_price']:,}")
                except Exception as e:
                    logger.warning(f"가격 조회 실패 ({stock_code}): {e}")
                    continue

            return price_data

        except Exception as e:
            logger.error(f"가상매매 가격 조회 실패: {e}")
            return {}

    def _print_statistics(self):
        try:
            summary = self.portfolio_manager.get_portfolio_summary()

            print(f"\n{'='*80}")
            print(f"Portfolio Summary")
            print(f"{'='*80}")
            print(f"Total Assets: {summary['total_assets']:,}")
            print(f"Cash: {summary['cash']:,}")
            print(f"Stock Value: {summary['stocks_value']:,}")
            print(f"Total P/L: {summary['total_profit_loss']:+,} ({summary['total_profit_loss_rate']:+.2f}%)")
            print(f"Open Positions: {summary['position_count']}")
            print(f"{'='*80}\n")

        except Exception as e:
            logger.error(f"통계 출력 실패: {e}")

    def run_self_test(self) -> bool:
        logger.info("="*80)
        logger.info("자체 테스트 실행 중")
        logger.info("="*80)

        tests_passed = 0
        tests_failed = 0

        try:
            logger.info("테스트 1: REST API 연결")
            if self.client and self.client.token:
                logger.info("통과: REST API 연결됨")
                tests_passed += 1
            else:
                logger.error("실패: REST API 미연결")
                tests_failed += 1
        except Exception as e:
            logger.error(f"실패: REST API 테스트 오류: {e}")
            tests_failed += 1

        try:
            logger.info("테스트 2: 계좌 API")
            deposit = self.account_api.get_deposit()
            if deposit:
                logger.info("통과: 계좌 API 작동")
                tests_passed += 1
            else:
                logger.error("실패: 계좌 API 미작동")
                tests_failed += 1
        except Exception as e:
            logger.error(f"실패: 계좌 API 테스트 오류: {e}")
            tests_failed += 1

        try:
            logger.info("테스트 3: 시장 API")
            # 장이 열려있지 않으면 테스트 스킵
            if not is_any_trading_hours():
                logger.warning("⚠️ 장이 열려있지 않아 시장 API 테스트를 스킵합니다")
                logger.info("   (정규장: 09:00-15:30, NXT: 08:00-09:00, 15:30-20:00)")
                tests_passed += 1  # 스킵된 테스트는 통과로 처리
            else:
                test_code = "005930"
                price_info = self.market_api.get_stock_price(test_code)
                if price_info and price_info.get('current_price', 0) > 0:
                    logger.info(f"통과: 시장 API 작동 (삼성: {price_info['current_price']:,}원)")
                    tests_passed += 1
                else:
                    logger.error("실패: 시장 API 미작동")
                    tests_failed += 1
        except Exception as e:
            logger.error(f"실패: 시장 API 테스트 오류: {e}")
            tests_failed += 1

        try:
            logger.info("테스트 4: AI 분석기")
            test_data = {
                'stock_code': '005930',
                'stock_name': '삼성전자',
                'current_price': 70000,
                'volume': 1000000,
                'change_rate': 2.0,
            }
            test_score_info = {
                'score': 300,
                'percentage': 68,
                'breakdown': {}
            }
            result = self.analyzer.analyze_stock(test_data, score_info=test_score_info)
            if result and result.get('signal'):
                logger.info(f"통과: AI 분석기 작동 (신호: {result['signal']})")
                tests_passed += 1
            else:
                logger.error("실패: AI 분석기 미작동")
                tests_failed += 1
        except Exception as e:
            logger.error(f"실패: AI 분석기 테스트 오류: {e}")
            tests_failed += 1

        try:
            logger.info("테스트 5: 점수 계산 시스템")
            test_data = {
                'stock_code': '005930',
                'stock_name': '삼성전자',
                'current_price': 70000,
                'volume': 1000000,
                'change_rate': 2.0,
                'institutional_net_buy': 1000000,
                'foreign_net_buy': 500000,
                'bid_ask_ratio': 1.2,
            }
            score_result = self.scoring_system.calculate_score(test_data)
            if score_result and score_result.total_score >= 0:
                logger.info(f"통과: 점수 계산 시스템 작동 (점수: {score_result.total_score:.0f}/440)")
                tests_passed += 1
            else:
                logger.error("실패: 점수 계산 시스템 미작동")
                tests_failed += 1
        except Exception as e:
            logger.error(f"실패: 점수 계산 시스템 테스트 오류: {e}")
            tests_failed += 1

        try:
            logger.info("테스트 6: 데이터베이스")
            if self.db_session:
                logger.info("통과: 데이터베이스 연결됨")
                tests_passed += 1
            else:
                logger.error("실패: 데이터베이스 미연결")
                tests_failed += 1
        except Exception as e:
            logger.error(f"실패: 데이터베이스 테스트 오류: {e}")
            tests_failed += 1

        logger.info("="*80)
        logger.info(f"자체 테스트 결과: {tests_passed}개 통과, {tests_failed}개 실패")
        logger.info("="*80)

        return tests_failed == 0


def signal_handler(signum, frame):
    logger.info("신호 수신 - 종료 중")
    sys.exit(0)


def main():
    import argparse

    # Command line arguments
    parser = argparse.ArgumentParser(description='AutoTrade Pro - AI Trading Bot')
    parser.add_argument('--virtual-trading', action='store_true',
                       help='가상매매 모드로 시작 (실제 거래 안 함)')
    parser.add_argument('--auto-start', action='store_true',
                       help='가상매매 전략 자동 시작')
    parser.add_argument('--skip-test', action='store_true',
                       help='자체 테스트 건너뛰기')
    parser.add_argument('--no-autopilot', action='store_true',
                       help='AutoPilot 비활성화 (수동 모드)')
    parser.add_argument('--no-autonomous', action='store_true',
                       help='자율 진화 모드 비활성화 (기본: 활성화)')
    parser.add_argument('--max-positions', type=int, default=50,
                       help='최대 보유 종목 수 (기본: 50)')
    parser.add_argument('--parallel-workers', type=int, default=20,
                       help='병렬 처리 스레드 수 (기본: 20)')
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # AutoPilot 제어 (환경 변수로 전달)
    if args.no_autopilot:
        os.environ['AUTOPILOT_DISABLED'] = '1'
        logger.info("⚠️  AutoPilot 비활성화됨 (수동 모드)")
    else:
        os.environ['AUTOPILOT_DISABLED'] = '0'

    bot = AutoTradingBot()

    # Fix: 자체 테스트 실행 (시스템 검증)
    print("\n" + "="*80)
    if args.virtual_trading:
        print("매매 봇 시작 (가상매매 모드)")
    else:
        print("매매 봇 시작 (자체 테스트 실행)")
    print("="*80)

    # 자체 테스트 실행 (건너뛰기 옵션이 없으면)
    if not args.skip_test:
        test_passed = bot.run_self_test()
        if not test_passed:
            logger.error("❌ 자체 테스트 실패 - 봇 시작을 중단합니다")
            print("\n자체 테스트 실패. 로그를 확인하세요.")
            return

        logger.info("✅ 자체 테스트 통과 - 봇을 시작합니다")

    # 가상매매 모드 활성화
    if args.virtual_trading:
        logger.info("="*80)
        logger.info("🎮 가상매매 모드 활성화")
        logger.info("="*80)

        try:
            # Virtual Trading Manager 초기화
            if bot.virtual_trading_manager is None:
                from virtual_trading import VirtualTradingManager
                bot.virtual_trading_manager = VirtualTradingManager(db_path="data/virtual_trading.db")
                logger.info("✅ 가상매매 매니저 초기화 완료")

            # 자동 시작 옵션이 활성화되어 있으면
            if args.auto_start:
                strategies = bot.virtual_trading_manager.get_strategy_summary()
                logger.info(f"📊 전략 개수: {len(strategies)}개")

                # 전략이 없으면 자동 생성
                if len(strategies) == 0:
                    logger.info("⚠️  전략이 없습니다. 자동 생성 중...")
                    from virtual_trading.diverse_strategies import create_all_diverse_strategies

                    diverse_strategies = create_all_diverse_strategies()
                    for strategy in diverse_strategies:
                        strategy_id = bot.virtual_trading_manager.create_strategy(
                            name=strategy.name,
                            description=strategy.description,
                            initial_capital=10_000_000
                        )
                        logger.info(f"   ✅ {strategy.name} (ID: {strategy_id})")

                    logger.info(f"✅ {len(diverse_strategies)}개 전략 생성 완료")

                logger.info("🚀 모든 가상매매 전략을 활성화합니다...")

                # Virtual Trader 시작
                if bot.virtual_trader is None:
                    from virtual_trading import VirtualTrader
                    bot.virtual_trader = VirtualTrader(
                        manager=bot.virtual_trading_manager,
                        data_fetcher=bot.data_fetcher
                    )
                    logger.info("✅ 가상 트레이더 시작")

        except Exception as e:
            logger.error(f"❌ 가상매매 초기화 실패: {e}", exc_info=True)

    # 자율 진화 모드 활성화 (기본값: 활성화)
    if not args.no_autonomous:
        logger.info("=" * 80)
        logger.info("🔥 자율 진화 모드 활성화")
        logger.info("=" * 80)
        logger.info("  • 24시간 연속 자동매매")
        logger.info("  • 멀티 종목 병렬 처리")
        logger.info("  • 실시간 알고리즘 진화")
        logger.info("  • 전체 API 데이터 수집")
        logger.info("=" * 80)

        try:
            from engine import (
                AutonomousTradingEngine,
                APIDataAggregator,
                ContinuousEvolution
            )

            # 1. API 데이터 수집기 시작
            logger.info("📊 API 데이터 수집기 초기화...")
            api_aggregator = APIDataAggregator(
                client=bot.client,
                max_workers=10,
                enable_all_apis=True
            )
            api_aggregator.start()
            logger.info("✅ API 수집기 시작 (50+ APIs)")

            # 2. 연속 진화 엔진 시작
            logger.info("🧬 연속 진화 엔진 초기화...")
            evolution_engine = ContinuousEvolution(
                client=bot.client,
                population_size=30,
                mutation_rate=0.15,
                max_workers=10
            )
            evolution_engine.start()
            logger.info("✅ 진화 엔진 시작 (24시간 연속)")

            # 3. 자율 매매 엔진 시작
            logger.info("🚀 자율 매매 엔진 초기화...")
            autonomous_engine = AutonomousTradingEngine(
                client=bot.client,
                max_workers=args.parallel_workers,
                max_positions=args.max_positions,
                evolution_interval_minutes=30,
                scan_interval_seconds=10,
                enable_auto_evolution=True
            )

            # 콜백 설정
            def on_trade_executed(signal, result):
                logger.info(f"💰 거래 체결: {signal.stock_name} {signal.action} {signal.quantity}주")

            def on_strategy_evolved(strategy):
                logger.info(f"🧬 새 전략 진화: fitness={strategy.get('fitness', 0):.2f}")

            autonomous_engine.on_trade_executed = on_trade_executed
            autonomous_engine.on_strategy_evolved = on_strategy_evolved

            autonomous_engine.start()
            logger.info("✅ 자율 매매 엔진 시작")

            logger.info("=" * 80)
            logger.info("🎯 자율 진화 시스템 완전 가동!")
            logger.info(f"   • 최대 보유: {args.max_positions}종목")
            logger.info(f"   • 병렬 처리: {args.parallel_workers}스레드")
            logger.info("=" * 80)

            # 엔진 참조 저장 (종료 시 정리용)
            bot._autonomous_engine = autonomous_engine
            bot._api_aggregator = api_aggregator
            bot._evolution_engine = evolution_engine

        except Exception as e:
            logger.error(f"❌ 자율 진화 모드 초기화 실패: {e}", exc_info=True)
            logger.info("⚠️ 일반 모드로 계속합니다...")

    bot.start()


if __name__ == "__main__":
    main()
