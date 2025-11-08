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
from config.constants import DELAYS, URLS
from utils.logger_new import get_logger
from database import get_db_session, Trade, Position, PortfolioSnapshot
from core import KiwoomRESTClient
from core.websocket_manager import WebSocketManager
from api import AccountAPI, MarketAPI, OrderAPI
from research import Screener, DataFetcher
from research.scanner_pipeline import ScannerPipeline
from strategy.scoring_system import ScoringSystem
from strategy.dynamic_risk_manager import DynamicRiskManager
from strategy import PortfolioManager
from utils.activity_monitor import get_monitor
from utils.alert_manager import get_alert_manager
from utils.data_cache import get_api_cache
from virtual_trading import VirtualTrader, TradeLogger

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
        logger.info("AutoTrade Pro - Advanced AI Trading System")
        logger.info("="*80)

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
        self.data_fetcher = None

        self.scanner = None
        self.scoring_system = None
        self.dynamic_risk_manager = None
        self.portfolio_manager = None
        self.analyzer = None

        self.virtual_trader = None
        self.trade_logger = None

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

        logger.info("AutoTrade Pro initialization complete")

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
                logger.info("Test Mode Activated")
                logger.info(f"Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')} ({current_weekday})")
                logger.info(f"Using Data From: {self.test_date}")
                logger.info("="*80)
            else:
                logger.info("Real-time Trading Mode")
                self.test_mode_active = False

        except Exception as e:
            logger.warning(f"Test mode check failed: {e}")
            self.test_mode_active = False

    def _initialize_components(self):
        try:
            logger.info("Initializing database...")
            self.db_session = get_db_session()
            logger.info("Database initialized")

            logger.info("Initializing REST API client...")
            self.client = KiwoomRESTClient()
            logger.info("REST API client initialized")

            logger.info("Initializing OpenAPI client...")
            try:
                from core.openapi_client import KiwoomOpenAPIClient
                self.openapi_client = KiwoomOpenAPIClient(auto_connect=False)

                if self.openapi_client.connect():
                    logger.info("OpenAPI client initialized")
                    accounts = self.openapi_client.get_account_list()
                    if accounts:
                        logger.info(f"Accounts: {accounts}")
                else:
                    logger.warning("OpenAPI server not running - attempting to start...")
                    server_started = self._start_openapi_server()
                    logger.info(f"Server start result: {server_started}")
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
                        connected = False

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
                                connected = True
                                break
                            else:
                                if retry < max_retries - 1:
                                    logger.info(f"   아직 준비되지 않음... {retry_delay}초 후 재시도")

                        if not connected:
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
                            logger.warning("  python openapi_server.py")
                            logger.warning("="*80)
                            logger.warning("")
                            self.openapi_client = None
                    else:
                        logger.warning("OpenAPI server start failed - using REST API only")
                        self.openapi_client = None
            except Exception as e:
                logger.warning(f"OpenAPI client not available: {e}")
                self.openapi_client = None

            logger.info("Initializing WebSocket...")
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
                            logger.debug(f"Real-time price: {stock_code} = {price:,}")
                        except Exception as e:
                            logger.error(f"Price data processing error: {e}")

                    self.websocket_manager.register_callback('0B', on_price_update)

                    def start_websocket():
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            connected = loop.run_until_complete(self.websocket_manager.connect())
                            if connected:
                                logger.info("WebSocket auto-connected")
                        except Exception as e:
                            logger.error(f"WebSocket connection error: {e}")

                    ws_thread = threading.Thread(target=start_websocket, daemon=True)
                    ws_thread.start()

                    logger.info("WebSocket initialized")
                else:
                    self.websocket_manager = None
                    logger.info("WebSocket disabled - no token")
            except Exception as e:
                logger.warning(f"WebSocket initialization failed: {e}")
                self.websocket_manager = None

            logger.info("Initializing API modules...")
            self.account_api = AccountAPI(self.client)
            self.market_api = MarketAPI(self.client)
            self.order_api = OrderAPI(self.client)
            self.data_fetcher = DataFetcher(self.client)
            logger.info("API modules initialized")

            logger.info("Initializing AI analyzer...")
            try:
                from config import GEMINI_API_KEY

                if GEMINI_API_KEY and GEMINI_API_KEY.strip() and GEMINI_API_KEY != "your-gemini-api-key-here":
                    from ai.gemini_analyzer import GeminiAnalyzer
                    self.analyzer = GeminiAnalyzer()
                    if self.analyzer.initialize():
                        logger.info("Gemini AI analyzer initialized")
                    else:
                        logger.warning("Gemini initialization failed - using Mock")
                        from ai.mock_analyzer import MockAnalyzer
                        self.analyzer = MockAnalyzer()
                        self.analyzer.initialize()
                else:
                    from ai.mock_analyzer import MockAnalyzer
                    self.analyzer = MockAnalyzer()
                    self.analyzer.initialize()
                    logger.info("Mock AI analyzer initialized")

            except Exception as e:
                logger.error(f"AI analyzer initialization failed: {e}")
                from ai.mock_analyzer import MockAnalyzer
                self.analyzer = MockAnalyzer()
                self.analyzer.initialize()
                logger.warning("Using Mock analyzer")

            logger.info("Initializing scanner pipeline...")
            screener = Screener(self.client)
            self.scanner = ScannerPipeline(
                market_api=self.market_api,
                screener=screener,
                ai_analyzer=self.analyzer
            )
            logger.info("Scanner pipeline initialized")

            logger.info("Initializing scoring system...")
            self.scoring_system = ScoringSystem(market_api=self.market_api)
            logger.info("Scoring system initialized")

            logger.info("Initializing risk manager...")
            initial_capital = self._get_initial_capital()
            self.dynamic_risk_manager = DynamicRiskManager(initial_capital=initial_capital)
            logger.info("Risk manager initialized")

            logger.info("Initializing portfolio manager...")
            self.portfolio_manager = PortfolioManager(self.client)
            logger.info("Portfolio manager initialized")

            logger.info("Initializing virtual trading system...")
            try:
                virtual_initial_cash = 10_000_000
                logger.info(f"Virtual trading initial capital: {virtual_initial_cash:,}")

                self.virtual_trader = VirtualTrader(initial_cash=virtual_initial_cash)
                self.trade_logger = TradeLogger()

                loaded_count = self.trade_logger.load_historical_trades(days=7)
                if loaded_count > 0:
                    logger.info(f"Loaded {loaded_count} historical trades")

                self.virtual_trader.load_all_states()

                logger.info("Virtual trading system initialized")
            except Exception as e:
                logger.warning(f"Virtual trading initialization failed: {e}")
                self.virtual_trader = None
                self.trade_logger = None

            self._initialize_control_file()
            self._restore_state()

            self.is_initialized = True
            logger.info("All components initialized successfully")

            self.monitor.log_activity('system', 'AutoTrade Pro started', level='success')

        except Exception as e:
            logger.error(f"Component initialization failed: {e}", exc_info=True)
            raise

    def _get_initial_capital(self) -> int:
        try:
            deposit = self.account_api.get_deposit()
            holdings = self.account_api.get_holdings()

            if deposit:
                deposit_total = int(str(deposit.get('entr', '0')).replace(',', ''))
                holdings_value = sum(int(str(h.get('eval_amt', 0)).replace(',', '')) for h in holdings) if holdings else 0
                capital = deposit_total + holdings_value if (deposit_total + holdings_value) > 0 else 10_000_000
                logger.info(f"Initial capital: {capital:,} (deposit: {deposit_total:,}, stocks: {holdings_value:,})")
                return capital
            return 10_000_000
        except Exception as e:
            logger.warning(f"Failed to get initial capital: {e}")
            return 10_000_000

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
            logger.info("Control file created")

    def _restore_state(self):
        try:
            if self.state_file.exists():
                import json
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"State restored: {len(state.get('positions', {}))} positions")
        except Exception as e:
            logger.warning(f"State restoration failed: {e}")

    def _start_openapi_server(self):
        """OpenAPI 서버 자동 시작 (Windows 32비트 Python 환경)"""
        try:
            import subprocess
            import platform
            import os

            if platform.system() != 'Windows':
                logger.warning("OpenAPI server auto-start only supported on Windows")
                logger.info("Please start manually: conda activate kiwoom32 && python openapi_server.py")
                return False

            logger.info("="*80)
            logger.info("OpenAPI 서버 시작 시도")
            logger.info("="*80)

            server_script = os.path.join(os.path.dirname(__file__), 'openapi_server.py')
            if not os.path.exists(server_script):
                logger.error(f"OpenAPI server script not found: {server_script}")
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
                    logger.info(f"✅ Found 32-bit Python: {path}")
                    break

            if not python_exe:
                logger.error("❌ 32-bit Python (kiwoom32) not found")
                logger.error(f"   Searched paths:")
                for path in conda_paths:
                    logger.error(f"   - {path}: {'EXISTS' if os.path.exists(path) else 'NOT FOUND'}")
                logger.info("")
                logger.info("수동으로 실행하세요:")
                logger.info("  1. 새 터미널을 엽니다")
                logger.info("  2. conda activate kiwoom32")
                logger.info("  3. python openapi_server.py")
                logger.info("")
                return False

            logger.info(f"🚀 Starting OpenAPI server...")
            logger.info(f"   Python: {python_exe}")
            logger.info(f"   Script: {server_script}")

            # 서버가 이미 실행 중인지 확인
            try:
                import requests
                response = requests.get('http://127.0.0.1:5001/health', timeout=1)
                if response.status_code == 200:
                    logger.info("✅ OpenAPI server already running!")
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

            logger.info(f"✅ OpenAPI server process started (PID: {process.pid})")
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
            logger.error(f"Failed to start OpenAPI server: {e}")
            import traceback
            traceback.print_exc()
            return False

    def start(self):
        if not self.is_initialized:
            logger.error("Bot not initialized")
            print("Error: Bot not initialized")
            return

        print("\n" + "="*80)
        print("AutoTrade Pro - Main Loop Started")
        print("="*80)
        logger.info("="*80)
        logger.info("AutoTrade Pro execution started")
        logger.info("="*80)

        self.is_running = True

        try:
            logger.info("Starting dashboard server...")
            from dashboard.app import run_dashboard
            import threading

            dashboard_thread = threading.Thread(
                target=lambda: run_dashboard(bot=self, host='0.0.0.0', port=5000, debug=False),
                daemon=True
            )
            dashboard_thread.start()
            logger.info("Dashboard server started on http://0.0.0.0:5000")
            print("📊 Dashboard: http://localhost:5000")

            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            print("\nInterrupted by user")
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
            print(f"\nMain loop error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()

    def stop(self):
        logger.info("Stopping AutoTrade Pro...")
        self.is_running = False

        if self.virtual_trader:
            try:
                logger.info("Saving virtual trading state...")
                self.virtual_trader.save_all_states()
                logger.info("Virtual trading state saved")
            except Exception as e:
                logger.warning(f"Failed to save virtual trading state: {e}")

        if self.trade_logger:
            try:
                self.trade_logger.print_summary()
            except Exception as e:
                logger.warning(f"Failed to print trade summary: {e}")

        if self.websocket_manager:
            try:
                asyncio.run(self.websocket_manager.disconnect())
                logger.info("WebSocket disconnected")
            except Exception as e:
                logger.warning(f"WebSocket disconnection failed: {e}")

        if self.db_session:
            self.db_session.close()

        if self.client:
            self.client.close()

        logger.info("AutoTrade Pro stopped")

    def _main_loop(self):
        cycle_count = 0
        try:
            if isinstance(self.config.main_cycle, dict):
                sleep_seconds = self.config.main_cycle.get('sleep_seconds', 60)
            else:
                sleep_seconds = getattr(self.config.main_cycle, 'sleep_seconds', 60)
        except Exception as e:
            logger.warning(f"Config load failed, using default: {e}")
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
                logger.error(f"Main loop error: {e}", exc_info=True)
                print(f"Main loop error: {e}")
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
            logger.warning(f"Control file read failed: {e}")

    def _check_trading_hours(self) -> bool:
        from research.analyzer import Analyzer
        analyzer = Analyzer(self.client)
        market_status = analyzer.get_market_status()

        self.market_status = market_status

        if not market_status['is_trading_hours']:
            logger.info(f"Not trading hours: {market_status['market_status']}")
            logger.info("Test mode activated - executing real API calls")
            self.market_status['is_trading_hours'] = True
            self.market_status['is_test_mode'] = True
            self.market_status['market_type'] = 'Test Mode'

        if market_status.get('is_test_mode'):
            logger.info(f"Test Mode: {market_status['market_status']}")
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

            logger.info(f"Account: deposit={deposit_total:,}, cash={cash:,}, stocks={stock_value:,}, total={total_capital:,}, positions={len(holdings)}")

        except Exception as e:
            logger.error(f"Account info update failed: {e}")

    def _check_sell_signals(self):
        logger.info("Checking sell signals...")

        if self.market_status.get('is_test_mode'):
            logger.info("Test mode: executing sell logic with actual holdings")

        try:
            holdings = self.account_api.get_holdings()

            if not holdings:
                logger.info("No holdings")
                return

            for holding in holdings:
                stock_code = holding.get('stk_cd', '')

                if stock_code.startswith('A'):
                    stock_code = stock_code[1:]

                stock_name = holding.get('stk_nm')
                current_price = int(holding.get('cur_prc', 0))
                quantity = int(holding.get('rmnd_qty', 0))
                buy_price = int(holding.get('avg_prc', 0))

                logger.info(f"Holding: {stock_name}({stock_code}) {quantity}@{current_price:,}")

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

                thresholds = self.dynamic_risk_manager.get_exit_thresholds(buy_price)

                should_sell = False
                sell_reason = ""

                if current_price >= thresholds['take_profit']:
                    should_sell = True
                    sell_reason = f"Take profit ({thresholds['take_profit']:,})"
                elif current_price <= thresholds['stop_loss']:
                    should_sell = True
                    sell_reason = f"Stop loss ({thresholds['stop_loss']:,})"

                if should_sell:
                    logger.info(f"Sell signal: {stock_name} - {sell_reason}")
                    self._execute_sell(stock_code, stock_name, quantity, current_price, profit_loss, profit_loss_rate, sell_reason)

        except Exception as e:
            logger.error(f"Sell check failed: {e}")

    def _run_scanning_pipeline(self):
        try:
            can_add = self.portfolio_manager.can_add_position()
            positions = self.portfolio_manager.get_positions()
            if not can_add:
                logger.info("Maximum positions reached")
                return

            current_positions = len(positions)
            should_open = self.dynamic_risk_manager.should_open_position(current_positions)

            if not should_open:
                logger.info("Risk manager: cannot open position")
                return

            logger.info("Starting market scan...")
            print("\n" + "="*80)
            print("Market Scanning Pipeline")
            print("="*80)

            candidates = self.scanner.scan_market()

            if not candidates:
                print("Scan complete: No candidates")
                logger.info("Scan complete: No candidates")
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
                print(f"   {rank}. {c.name} - {c.final_score:.0f} points ({percentage:.0f}%)")

            portfolio_info = "No positions"

            for idx, candidate in enumerate(top5[:3], 1):
                print(f"\n[{idx}/3] {candidate.name}")

                scoring_result = candidate_scores[candidate.code]

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

                ai_analysis = self.analyzer.analyze_stock(
                    stock_data,
                    score_info=score_info,
                    portfolio_info=portfolio_info
                )
                ai_signal = ai_analysis.get('signal', 'hold')
                split_strategy = ai_analysis.get('split_strategy', '')

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
                    (ai_signal == 'buy' and scoring_result.total_score >= 250) or
                    (ai_signal == 'hold' and scoring_result.total_score >= 300)
                )

                if buy_approved:
                    print(f"Buy criteria met - Executing order")

                    self._execute_buy(candidate, scoring_result)

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
                            logger.warning(f"Virtual trading failed: {e}")

                    break
                else:
                    reason_text = f"AI={ai_signal}, score={scoring_result.total_score:.0f}"
                    print(f"Buy criteria not met ({reason_text})")

            print("Scan strategy complete")

        except Exception as e:
            logger.error(f"Scan strategy failed: {e}", exc_info=True)
            print(f"Scan strategy error: {e}")
            import traceback
            traceback.print_exc()

    def _execute_buy(self, candidate, scoring_result):
        try:
            if self.market_status.get('can_cancel_only'):
                logger.warning(f"{self.market_status['market_type']}: Cannot place new buy order")
                return

            stock_code = candidate.code
            stock_name = candidate.name
            current_price = candidate.price

            deposit = self.account_api.get_deposit()
            holdings = self.account_api.get_holdings()

            available_cash = int(str(deposit.get('100stk_ord_alow_amt', '0')).replace(',', '')) if deposit else 0

            logger.debug(f"Available cash: {available_cash:,}")

            quantity = self.dynamic_risk_manager.calculate_position_size(
                stock_price=current_price,
                available_cash=available_cash
            )

            if quantity == 0:
                logger.warning("Buy quantity 0")
                return

            total_amount = current_price * quantity

            logger.info(
                f"{stock_name} buy order: {quantity}@{current_price:,} "
                f"(total {total_amount:,})"
            )

            from utils.trading_date import is_nxt_hours
            from datetime import datetime

            if is_nxt_hours():
                now = datetime.now()
                if now.hour == 8:
                    order_type = '61'
                    logger.info("Pre-market order: Type 61")
                else:
                    order_type = '81'
                    logger.info("After-market order: Type 81")
            else:
                order_type = '0'
                logger.info("Regular market order: Type 0")

            if self.market_status.get('is_test_mode'):
                logger.info(f"Test mode: AI review complete -> Real buy API call")
                logger.info(f"   Stock: {stock_name}, AI score: {candidate.ai_score}, Total score: {scoring_result.total_score}")

            order_result = self.order_api.buy(
                stock_code=stock_code,
                quantity=quantity,
                price=current_price,
                order_type=order_type
            )

            if order_result:
                order_no = order_result.get('order_no', '')

                trade = Trade(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    action='buy',
                    quantity=quantity,
                    price=current_price,
                    total_amount=total_amount,
                    risk_mode=self.dynamic_risk_manager.current_mode.value,
                    ai_score=candidate.ai_score,
                    ai_signal=candidate.ai_signal,
                    ai_confidence=candidate.ai_confidence,
                    scoring_total=scoring_result.total_score,
                    scoring_percentage=scoring_result.percentage
                )
                self.db_session.add(trade)
                self.db_session.commit()

                logger.info(f"{stock_name} buy success (order: {order_no})")

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

        except Exception as e:
            logger.error(f"Buy execution failed: {e}", exc_info=True)

    def _execute_sell(self, stock_code, stock_name, quantity, price, profit_loss, profit_loss_rate, reason):
        try:
            if self.market_status.get('can_cancel_only'):
                logger.warning(f"{self.market_status['market_type']}: Cannot place new sell order")
                return

            logger.info(
                f"{stock_name} sell order: {quantity}@{price:,} "
                f"(P/L: {profit_loss:+,}, {profit_loss_rate:+.2f}%)"
            )

            from utils.trading_date import is_nxt_hours
            from datetime import datetime

            if is_nxt_hours():
                now = datetime.now()
                if now.hour == 8:
                    order_type = '61'
                    logger.info("Pre-market sell: Type 61")
                else:
                    order_type = '81'
                    logger.info("After-market sell: Type 81")
            else:
                order_type = '0'
                logger.info("Regular market sell: Type 0")

            if self.market_status.get('is_test_mode'):
                logger.info(f"Test mode: Sell condition met -> Real sell API call")
                logger.info(f"   Stock: {stock_name}, Reason: {reason}, P/L: {profit_loss:+,} ({profit_loss_rate:+.2f}%)")

            order_result = self.order_api.sell(
                stock_code=stock_code,
                quantity=quantity,
                price=price,
                order_type=order_type
            )

            if order_result:
                order_no = order_result.get('order_no', '')

                trade = Trade(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    action='sell',
                    quantity=quantity,
                    price=price,
                    total_amount=price * quantity,
                    profit_loss=profit_loss,
                    profit_loss_ratio=profit_loss_rate / 100,
                    risk_mode=self.dynamic_risk_manager.current_mode.value,
                    notes=reason
                )
                self.db_session.add(trade)
                self.db_session.commit()

                log_level = 'success' if profit_loss >= 0 else 'warning'
                logger.info(f"{stock_name} sell success (order: {order_no})")

                self.alert_manager.alert_position_closed(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    sell_price=price,
                    profit_loss_rate=profit_loss_rate,
                    profit_loss_amount=profit_loss,
                    reason=reason
                )

                self.monitor.log_activity(
                    'sell',
                    f'{stock_name} sell: {quantity}@{price:,} (P/L: {profit_loss:+,})',
                    level=log_level
                )

        except Exception as e:
            logger.error(f"Sell execution failed: {e}", exc_info=True)

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
            logger.error(f"Portfolio snapshot save failed: {e}")

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
                    logger.warning(f"Price fetch failed ({stock_code}): {e}")
                    continue

            return price_data

        except Exception as e:
            logger.error(f"Virtual trading price fetch failed: {e}")
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
            logger.error(f"Statistics print failed: {e}")

    def run_self_test(self) -> bool:
        logger.info("="*80)
        logger.info("Running Self-Test")
        logger.info("="*80)

        tests_passed = 0
        tests_failed = 0

        try:
            logger.info("Test 1: REST API Connection")
            if self.client and self.client.token:
                logger.info("PASS: REST API connected")
                tests_passed += 1
            else:
                logger.error("FAIL: REST API not connected")
                tests_failed += 1
        except Exception as e:
            logger.error(f"FAIL: REST API test error: {e}")
            tests_failed += 1

        try:
            logger.info("Test 2: Account API")
            deposit = self.account_api.get_deposit()
            if deposit:
                logger.info("PASS: Account API functional")
                tests_passed += 1
            else:
                logger.error("FAIL: Account API not functional")
                tests_failed += 1
        except Exception as e:
            logger.error(f"FAIL: Account API test error: {e}")
            tests_failed += 1

        try:
            logger.info("Test 3: Market API")
            test_code = "005930"
            price_info = self.market_api.get_stock_price(test_code)
            if price_info and price_info.get('current_price', 0) > 0:
                logger.info(f"PASS: Market API functional (Samsung: {price_info['current_price']:,})")
                tests_passed += 1
            else:
                logger.error("FAIL: Market API not functional")
                tests_failed += 1
        except Exception as e:
            logger.error(f"FAIL: Market API test error: {e}")
            tests_failed += 1

        try:
            logger.info("Test 4: AI Analyzer")
            test_data = {
                'stock_code': '005930',
                'stock_name': 'Samsung Electronics',
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
                logger.info(f"PASS: AI Analyzer functional (signal: {result['signal']})")
                tests_passed += 1
            else:
                logger.error("FAIL: AI Analyzer not functional")
                tests_failed += 1
        except Exception as e:
            logger.error(f"FAIL: AI Analyzer test error: {e}")
            tests_failed += 1

        try:
            logger.info("Test 5: Scoring System")
            test_data = {
                'stock_code': '005930',
                'stock_name': 'Samsung Electronics',
                'current_price': 70000,
                'volume': 1000000,
                'change_rate': 2.0,
                'institutional_net_buy': 1000000,
                'foreign_net_buy': 500000,
                'bid_ask_ratio': 1.2,
            }
            score_result = self.scoring_system.calculate_score(test_data)
            if score_result and score_result.total_score >= 0:
                logger.info(f"PASS: Scoring System functional (score: {score_result.total_score:.0f}/440)")
                tests_passed += 1
            else:
                logger.error("FAIL: Scoring System not functional")
                tests_failed += 1
        except Exception as e:
            logger.error(f"FAIL: Scoring System test error: {e}")
            tests_failed += 1

        try:
            logger.info("Test 6: Database")
            if self.db_session:
                logger.info("PASS: Database connected")
                tests_passed += 1
            else:
                logger.error("FAIL: Database not connected")
                tests_failed += 1
        except Exception as e:
            logger.error(f"FAIL: Database test error: {e}")
            tests_failed += 1

        logger.info("="*80)
        logger.info(f"Self-Test Results: {tests_passed} passed, {tests_failed} failed")
        logger.info("="*80)

        return tests_failed == 0


def signal_handler(signum, frame):
    logger.info("Signal received - shutting down")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    bot = AutoTradingBot()

    # 셀프 테스트 건너뛰기 (시간 절약)
    print("\n" + "="*80)
    print("Starting Trading Bot (Self-Test Skipped)")
    print("="*80)

    bot.start()


if __name__ == "__main__":
    main()
