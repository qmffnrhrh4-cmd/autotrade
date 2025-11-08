"""
main_v2.py
AutoTrade Pro v2.0 - 통합된 자동매매 시스템
"""
import sys
import os
import time
import signal
import threading
import subprocess
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로
sys.path.insert(0, str(Path(__file__).parent))

from config.manager import get_config
try:
    from utils.logger_new import get_logger
except ImportError:
    import logging
    def get_logger():
        return logging.getLogger(__name__)
try:
    from database import get_db_session, Trade, Position, PortfolioSnapshot
except ImportError:
    def get_db_session():
        return None
    Trade = None
    Position = None
    PortfolioSnapshot = None

# 핵심 모듈
from core import KiwoomRESTClient
from core.websocket_client import WebSocketClient
from core.websocket_manager import WebSocketManager
from api import AccountAPI, MarketAPI, OrderAPI
from research import Screener, DataFetcher
from research.strategy_manager import StrategyManager
from strategy.scoring_system import ScoringSystem
from strategy.dynamic_risk_manager import DynamicRiskManager
from strategy import PortfolioManager
from ai.mock_analyzer import MockAnalyzer  # 테스트: Mock 직접 사용
from utils.activity_monitor import get_monitor
from utils.alert_manager import get_alert_manager  # v5.7.5: 알림 시스템

# 가상 매매 시스템
from virtual_trading import VirtualTrader, TradeLogger

# 로거
logger = get_logger()


class TradingBotV2:
    """
    AutoTrade Pro v2.0 메인 봇

    통합 기능:
    - 3단계 스캐닝 파이프라인 (Fast → Deep → AI)
    - 10가지 기준 스코어링 시스템 (440점 만점)
    - 동적 리스크 관리 (4단계 모드)
    - 데이터베이스 기록
    - YAML 설정 관리
    """

    def __init__(self):
        """봇 초기화"""
        logger.info("="*60)
        logger.info("🚀 AutoTrade Pro v2.0 초기화 시작")
        logger.info("="*60)

        # 설정 로드
        self.config = get_config()

        # 테스트 모드 확인 및 활성화
        self.test_mode_active = False
        self.test_date = None
        self._check_test_mode()

        # 상태
        self.is_running = False
        self.is_initialized = False
        self.market_status = {}  # 시장 상태 정보 (NXT 포함)
        self.start_time = datetime.now()  # 봇 시작 시간 기록

        # 제어 파일 (data 폴더로 이동)
        self.control_file = Path('data/control.json')
        self.state_file = Path('data/strategy_state.json')

        # 컴포넌트
        self.client = None  # REST API 클라이언트 (시세 조회용)
        self.openapi_client = None  # OpenAPI 클라이언트 (자동매매용)
        self.websocket_client = None  # 구 WebSocket 클라이언트 (비활성화)
        self.websocket_manager = None  # 신 WebSocketManager (ka10045 검증 완료)
        self.account_api = None
        self.market_api = None
        self.order_api = None
        self.data_fetcher = None  # 시장 데이터 조회용

        # 새로운 시스템
        self.strategy_manager = None
        self.scoring_system = None
        self.dynamic_risk_manager = None

        # 기존 시스템
        self.portfolio_manager = None
        self.analyzer = None

        # 가상 매매 시스템
        self.virtual_trader = None
        self.trade_logger = None

        # 활동 모니터
        self.monitor = get_monitor()

        # v5.7.5: 알림 관리자
        self.alert_manager = get_alert_manager()

        # 데이터베이스 세션
        self.db_session = None

        # AI 승인 매수 후보 리스트
        self.ai_approved_candidates = []

        # 스캔 진행 상황 추적
        self.scan_progress = {
            'current_strategy': '',  # 현재 스캔 전략
            'total_candidates': 0,   # 발견된 후보 수
            'top_candidates': [],    # 상위 후보 (이름, 점수)
            'reviewing': '',         # 현재 검토 중인 종목
            'rejected': [],          # 탈락 종목 (이름, 이유)
            'approved': [],          # 승인 종목 (이름, 가격, 전략)
        }

        # 초기화
        self._initialize_components()

        logger.info("✅ AutoTrade Pro v2.0 초기화 완료")

    def _check_test_mode(self):
        """테스트 모드 확인 및 활성화

        조건:
        - 휴일 (토요일, 일요일)
        - 평일 오후 8시(20:00) ~ 오전 8시(08:00)
        """
        try:
            from utils.trading_date import should_use_test_mode, get_last_trading_date

            # 테스트 모드 사용 여부 확인
            if should_use_test_mode():
                self.test_mode_active = True
                self.test_date = get_last_trading_date()

                now = datetime.now()
                weekday_kr = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
                current_weekday = weekday_kr[now.weekday()]

                logger.info("=" * 60)
                logger.info("🧪 테스트 모드 자동 활성화")
                logger.info(f"   현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')} ({current_weekday})")
                logger.info(f"   사용 데이터 날짜: {self.test_date}")

                if now.weekday() >= 5:
                    logger.info(f"   사유: 휴일 ({current_weekday})")
                else:
                    logger.info(f"   사유: 평일 비장시간 (20:00~08:00)")

                logger.info("   ⚠️  실제 주문은 발생하지 않습니다")
                logger.info("=" * 60)
            else:
                logger.info("⚡ 정규 장 시간 - 실시간 모드")
                self.test_mode_active = False

        except Exception as e:
            logger.warning(f"테스트 모드 확인 실패: {e}")
            self.test_mode_active = False

    def get_test_mode_info(self) -> dict:
        """테스트 모드 정보 반환"""
        return {
            "active": self.test_mode_active,
            "test_date": self.test_date,
            "current_time": datetime.now().isoformat(),
            "is_market_hours": not self.test_mode_active
        }

    def _initialize_components(self):
        """컴포넌트 초기화"""
        try:
            # 1. 데이터베이스 초기화
            logger.info("💾 데이터베이스 초기화 중...")
            self.db_session = get_db_session()
            logger.info("✓ 데이터베이스 초기화 완료")

            # 2. REST 클라이언트 (시세 조회용 - 64비트)
            logger.info("🌐 REST API 클라이언트 초기화 중...")
            self.client = KiwoomRESTClient()
            logger.info("✓ REST API 클라이언트 초기화 완료")

            # 2-0. OpenAPI 클라이언트 (자동매매용 - 32비트) - 선택적 사용
            logger.info("🔧 OpenAPI 클라이언트 초기화 시도 중...")
            logger.info("   (OpenAPI 서버 미사용 시 이 단계는 실패할 수 있습니다)")
            try:
                from core import get_openapi_client

                self.openapi_client = get_openapi_client(auto_connect=True)

                if self.openapi_client and self.openapi_client.is_connected:
                    logger.info("✅ OpenAPI 클라이언트 초기화 완료")
                    logger.info(f"   계좌 목록: {self.openapi_client.get_account_list()}")
                else:
                    logger.info("ℹ️  OpenAPI 연결 안됨 - REST API만 사용합니다")
                    logger.info("   시세 조회와 분석은 정상 작동합니다")
                    self.openapi_client = None
            except Exception as e:
                logger.info("ℹ️  OpenAPI 클라이언트 미사용")
                logger.info("   REST API로 모든 기능을 사용할 수 있습니다")
                logger.debug(f"   상세: {e}")
                self.openapi_client = None

            # 2-1. WebSocket 클라이언트 (실시간 데이터 수신)
            # NOTE: 구 WebSocket은 현재 비활성화 (서버가 주기적으로 연결 종료하여 불필요한 재연결 부하 발생)
            # 신 WebSocketManager로 대체
            logger.info("🔌 구 WebSocket: 비활성화")
            self.websocket_client = None

            # 2-2. 신 WebSocketManager 초기화 (LOGIN 패턴 검증 완료)
            try:
                logger.info("🔌 WebSocketManager 초기화 중...")
                if self.client.token:
                    self.websocket_manager = WebSocketManager(
                        access_token=self.client.token,
                        base_url=self.client.base_url
                    )

                    # 실시간 데이터 콜백 등록
                    async def on_price_update(data):
                        """실시간 체결 데이터 콜백"""
                        try:
                            stock_code = data.get('item', '')
                            values = data.get('values', {})
                            price = int(values.get('10', '0'))  # 현재가
                            logger.debug(f"📈 실시간 체결: {stock_code} = {price:,}원")
                        except Exception as e:
                            logger.error(f"체결 데이터 처리 오류: {e}")

                    async def on_orderbook_update(data):
                        """실시간 호가 데이터 콜백"""
                        try:
                            stock_code = data.get('item', '')
                            values = data.get('values', {})
                            sell_price = int(values.get('27', '0'))  # 매도호가
                            buy_price = int(values.get('28', '0'))   # 매수호가
                            logger.debug(f"📊 실시간 호가: {stock_code} 매도={sell_price:,}원 매수={buy_price:,}원")
                        except Exception as e:
                            logger.error(f"호가 데이터 처리 오류: {e}")

                    self.websocket_manager.register_callback('0B', on_price_update)      # 주식체결
                    self.websocket_manager.register_callback('0D', on_orderbook_update)  # 주식호가잔량

                    # WebSocket 자동 연결 시작 (백그라운드에서 실행)
                    import asyncio
                    import threading

                    def start_websocket():
                        """WebSocket 연결을 백그라운드에서 시작"""
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)

                            # 연결 시도
                            connected = loop.run_until_complete(self.websocket_manager.connect())
                            if connected:
                                logger.info("✅ WebSocket 자동 연결 성공")
                            else:
                                logger.warning("⚠️  WebSocket 자동 연결 실패")
                        except Exception as e:
                            logger.error(f"❌ WebSocket 연결 오류: {e}")

                    # 백그라운드 스레드에서 연결
                    ws_thread = threading.Thread(target=start_websocket, daemon=True)
                    ws_thread.start()

                    logger.info("✓ WebSocketManager 초기화 완료")
                    logger.info("   🔌 WebSocket 자동 연결 시작됨")
                    logger.info("   💡 장중(09:00-15:30)에만 실시간 데이터가 수신됩니다")
                else:
                    self.websocket_manager = None
                    logger.info("⚠️  토큰 없음 - WebSocketManager 비활성화")
            except Exception as e:
                logger.warning(f"⚠️  WebSocketManager 초기화 실패: {e}")
                self.websocket_manager = None

            # 3. API 모듈
            logger.info("📡 API 모듈 초기화 중...")
            self.account_api = AccountAPI(self.client)
            self.market_api = MarketAPI(self.client)
            self.order_api = OrderAPI(self.client)
            self.data_fetcher = DataFetcher(self.client)  # 시장 데이터 조회
            logger.info("✓ API 모듈 초기화 완료")

            # 4. AI 분석기 (Gemini API 키가 있으면 실제 사용, 없으면 Mock)
            logger.info("🤖 AI 분석기 초기화 중...")
            try:
                from config import GEMINI_API_KEY

                # Gemini API 키 확인
                if GEMINI_API_KEY and GEMINI_API_KEY.strip() and GEMINI_API_KEY != "your-gemini-api-key-here":
                    # 실제 Gemini 사용
                    from ai.gemini_analyzer import GeminiAnalyzer
                    self.analyzer = GeminiAnalyzer()
                    if self.analyzer.initialize():
                        logger.info("✅ Gemini AI 분석기 초기화 완료 (실제 AI 사용)")
                    else:
                        logger.warning("Gemini 초기화 실패 - Mock으로 대체")
                        from ai.mock_analyzer import MockAnalyzer
                        self.analyzer = MockAnalyzer()
                        self.analyzer.initialize()
                        logger.info("✓ Mock AI 분석기 초기화 완료 (대체)")
                else:
                    # Gemini API 키 없음 - Mock 사용
                    from ai.mock_analyzer import MockAnalyzer
                    self.analyzer = MockAnalyzer()
                    self.analyzer.initialize()
                    logger.info("✓ Mock AI 분석기 초기화 완료 (Gemini API 키 없음)")

            except Exception as e:
                logger.error(f"AI 분석기 초기화 실패: {e}")
                # 폴백: Mock 사용
                from ai.mock_analyzer import MockAnalyzer
                self.analyzer = MockAnalyzer()
                self.analyzer.initialize()
                logger.warning("✓ Mock AI 분석기로 폴백")

            # 5. 3가지 스캔 전략 매니저 (신규)
            logger.info("🎯 3가지 스캔 전략 매니저 초기화 중...")
            screener = Screener(self.client)
            self.strategy_manager = StrategyManager(
                market_api=self.market_api,
                screener=screener,
                ai_analyzer=self.analyzer,
                config=get_config().get('scan_strategies', {})
            )
            logger.info("✓ 3가지 스캔 전략 매니저 초기화 완료")

            # 6. 10가지 스코어링 시스템 (신규)
            logger.info("📊 10가지 스코어링 시스템 초기화 중...")
            self.scoring_system = ScoringSystem(market_api=self.market_api)
            logger.info("✓ 10가지 스코어링 시스템 초기화 완료")

            # 7. 동적 리스크 관리 (신규)
            logger.info("🛡️ 동적 리스크 관리자 초기화 중...")
            initial_capital = self._get_initial_capital()
            self.dynamic_risk_manager = DynamicRiskManager(initial_capital=initial_capital)
            logger.info("✓ 동적 리스크 관리자 초기화 완료")

            # 8. 포트폴리오 관리자
            logger.info("💼 포트폴리오 관리자 초기화 중...")
            self.portfolio_manager = PortfolioManager(self.client)
            logger.info("✓ 포트폴리오 관리자 초기화 완료")

            # 9. 가상 매매 시스템
            logger.info("📝 가상 매매 시스템 초기화 중...")
            try:
                # 가상 매매 초기 자본: 실제 계좌와 독립적으로 운영 (고정 1000만원)
                virtual_initial_cash = 10_000_000
                logger.info(f"   가상 매매 초기 자본: {virtual_initial_cash:,}원 (실제 계좌와 독립)")

                # VirtualTrader 초기화 (3가지 전략: 공격적, 보수적, 균형)
                self.virtual_trader = VirtualTrader(initial_cash=virtual_initial_cash)

                # TradeLogger 초기화
                self.trade_logger = TradeLogger()

                # 과거 7일 로그 불러오기
                loaded_count = self.trade_logger.load_historical_trades(days=7)
                if loaded_count > 0:
                    logger.info(f"✓ 과거 거래 로그 {loaded_count}건 불러옴")

                # 가상 계좌 상태 복원
                self.virtual_trader.load_all_states()

                logger.info("✅ 가상 매매 시스템 초기화 완료 (3가지 전략 운영)")
            except Exception as e:
                logger.warning(f"⚠️  가상 매매 시스템 초기화 실패: {e}")
                self.virtual_trader = None
                self.trade_logger = None

            # 10. 제어 파일
            self._initialize_control_file()

            # 11. 이전 상태 복원
            self._restore_state()

            self.is_initialized = True
            logger.info("✅ 모든 컴포넌트 초기화 완료")

            # 활동 모니터
            self.monitor.log_activity(
                'system',
                '🚀 AutoTrade Pro v2.0 시작',
                level='success'
            )

        except Exception as e:
            logger.error(f"컴포넌트 초기화 실패: {e}", exc_info=True)
            raise

    def _get_initial_capital(self) -> int:
        """초기 자본금 가져오기 (예수금 + 보유주식 평가금액) - kt00001 API 응답 필드 사용"""
        try:
            deposit = self.account_api.get_deposit()
            holdings = self.account_api.get_holdings()

            if deposit:
                # 예수금 (entr 필드 - kt00001 API 응답)
                deposit_total = int(str(deposit.get('entr', '0')).replace(',', ''))
                # 보유 주식 평가 금액
                holdings_value = sum(int(str(h.get('eval_amt', 0)).replace(',', '')) for h in holdings) if holdings else 0

                # 총 자본금 = 예수금 + 보유주식 평가금액
                capital = deposit_total + holdings_value if (deposit_total + holdings_value) > 0 else 10_000_000

                logger.info(f"💰 초기 자본금: {capital:,}원 (예수금: {deposit_total:,}, 보유주식: {holdings_value:,})")
                return capital
            return 10_000_000  # 기본값 1천만원
        except Exception as e:
            logger.warning(f"⚠️ 초기 자본금 조회 실패, 기본값 사용: {e}")
            return 10_000_000

    def _initialize_control_file(self):
        """제어 파일 초기화"""
        if not self.control_file.exists():
            default_state = {
                'run': True,
                'pause_buy': False,
                'pause_sell': False,
            }
            import json
            with open(self.control_file, 'w') as f:
                json.dump(default_state, f, indent=2)
            logger.info("제어 파일 생성 완료")

    def _restore_state(self):
        """이전 상태 복원"""
        try:
            if self.state_file.exists():
                import json
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"이전 상태 복원: {len(state.get('positions', {}))}개 포지션")
        except Exception as e:
            logger.warning(f"상태 복원 실패: {e}")

    def _test_samsung_trade(self):
        """삼성전자 테스트 매매 (연결 직후 1주 매수 → 10초 후 매도)"""
        try:
            logger.info("="*60)
            logger.info("🧪 삼성전자 테스트 매매 시작")
            logger.info("="*60)
            print("\n🧪 삼성전자 테스트 매매 시작")

            samsung_code = "005930"  # 삼성전자
            samsung_name = "삼성전자"

            # 현재 시간 확인 및 거래 유형 결정
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute

            market_type = ""
            order_type = "00"  # 기본값: 지정가

            # 시간대별 거래 유형 판단
            # ✅ 테스트 결과: NXT 거래소는 모든 시간대에 trde_tp=0 (보통 지정가) 사용
            exchange = "KRX"  # 기본값: 정규장
            if 8 <= current_hour < 9:
                market_type = "NXT 장시작전 시간외"
                order_type = "0"  # 보통 지정가 (NXT 거래소)
                exchange = "NXT"
                logger.info(f"⏰ 현재 시간: {now.strftime('%H:%M:%S')} - {market_type} (주문유형: 보통지정가)")
            elif 9 <= current_hour < 15 or (current_hour == 15 and current_minute < 30):
                market_type = "정규장"
                order_type = "0"  # 보통 지정가
                exchange = "KRX"
                logger.info(f"⏰ 현재 시간: {now.strftime('%H:%M:%S')} - {market_type} (주문유형: 지정가)")
            elif current_hour == 15 and 40 <= current_minute < 60:
                market_type = "NXT 장후 시간외"
                order_type = "0"  # 보통 지정가 (NXT 거래소)
                exchange = "NXT"
                logger.info(f"⏰ 현재 시간: {now.strftime('%H:%M:%S')} - {market_type} (주문유형: 보통지정가)")
            elif 16 <= current_hour < 20:
                market_type = "NXT 시간외 단일가"
                order_type = "0"  # 보통 지정가 (NXT 거래소) ✅ 테스트 검증됨!
                exchange = "NXT"
                logger.info(f"⏰ 현재 시간: {now.strftime('%H:%M:%S')} - {market_type} (주문유형: 보통지정가)")
            else:
                market_type = "장외시간"
                logger.warning(f"⏰ 현재 시간: {now.strftime('%H:%M:%S')} - {market_type} (주문 불가)")
                return  # 장외시간에는 주문하지 않음

            # 1. 삼성전자 현재가 조회
            logger.info(f"📊 {samsung_name} 현재가 조회 중...")
            current_price = None

            try:
                # get_stock_price()는 내부적으로 fallback 처리 (체결정보 → 호가 → 기본 호가)
                quote = self.market_api.get_stock_price(samsung_code)
                if quote and quote.get('current_price', 0) > 0:
                    current_price = int(quote.get('current_price', 0))
                    source = quote.get('source', 'unknown')
                    logger.info(f"✓ {samsung_name} 현재가: {current_price:,}원 (출처: {source})")
                else:
                    logger.error(f"❌ {samsung_name} 현재가 조회 실패 (모든 소스)")
                    return

            except Exception as e:
                logger.error(f"❌ 가격 조회 실패: {e}")
                import traceback
                traceback.print_exc()
                return

            if not current_price:
                logger.error(f"❌ 현재가를 가져올 수 없습니다 - 테스트 중단")
                return

            # 2. 매수 주문 실행
            quantity = 1  # 1주
            logger.info(f"📥 {samsung_name} 매수 주문 실행 중...")
            logger.info(f"   종목코드: {samsung_code}")
            logger.info(f"   수량: {quantity}주")
            logger.info(f"   가격: {current_price:,}원")
            logger.info(f"   총액: {current_price * quantity:,}원")
            logger.info(f"   거래유형: {market_type}")

            try:
                buy_result = self.order_api.buy(
                    stock_code=samsung_code,
                    quantity=quantity,
                    price=current_price,
                    order_type=order_type,
                    exchange=exchange  # ✅ 테스트 결과 반영: 시간외는 NXT
                )

                if buy_result:
                    order_no = buy_result.get('order_no', 'N/A')
                    logger.info(f"✅ {samsung_name} 매수 주문 성공!")
                    logger.info(f"   주문번호: {order_no}")

                    # 활동 로그
                    self.monitor.log_activity(
                        'test_buy',
                        f'🧪 테스트: {samsung_name} 매수 {quantity}주 @ {current_price:,}원',
                        level='success'
                    )
                else:
                    logger.error("매수 주문 실패")
                    return

            except Exception as e:
                logger.error(f"매수 주문 실패: {e}")
                return

            # 3. 10초 대기
            logger.info("⏳ 10초 대기 중...")
            for i in range(10, 0, -1):
                print(f"   {i}초 남음...", end='\r')
                time.sleep(1)
            print()

            # 4. 매도 주문 실행
            logger.info(f"📤 {samsung_name} 매도 주문 실행 중...")

            # 최신 현재가 재조회
            sell_price = current_price  # 기본값: 매수가 사용
            try:
                quote = self.market_api.get_stock_price(samsung_code)
                if quote and quote.get('current_price', 0) > 0:
                    sell_price = int(quote.get('current_price', 0))
                    source = quote.get('source', 'unknown')
                    logger.info(f"✓ {samsung_name} 현재가 (매도): {sell_price:,}원 (출처: {source})")
                else:
                    logger.warning(f"⚠️ 현재가 조회 실패 - 매수가 사용: {sell_price:,}원")

            except Exception as e:
                logger.warning(f"⚠️ 가격 재조회 실패: {e} - 매수가 사용: {sell_price:,}원")

            try:
                sell_result = self.order_api.sell(
                    stock_code=samsung_code,
                    quantity=quantity,
                    price=sell_price,
                    order_type=order_type,
                    exchange=exchange  # ✅ 테스트 결과 반영: 시간외는 NXT
                )

                if sell_result:
                    order_no = sell_result.get('order_no', 'N/A')
                    profit_loss = (sell_price - current_price) * quantity
                    logger.info(f"✅ {samsung_name} 매도 주문 성공!")
                    logger.info(f"   주문번호: {order_no}")
                    logger.info(f"   매수가: {current_price:,}원")
                    logger.info(f"   매도가: {sell_price:,}원")
                    logger.info(f"   손익: {profit_loss:+,}원")

                    # 활동 로그
                    self.monitor.log_activity(
                        'test_sell',
                        f'🧪 테스트: {samsung_name} 매도 {quantity}주 @ {sell_price:,}원 (손익: {profit_loss:+,}원)',
                        level='success' if profit_loss >= 0 else 'warning'
                    )
                else:
                    logger.error("매도 주문 실패")

            except Exception as e:
                logger.error(f"매도 주문 실패: {e}")

            logger.info("="*60)
            logger.info("✅ 삼성전자 테스트 매매 완료")
            logger.info("="*60)

        except Exception as e:
            logger.error(f"테스트 매매 중 오류: {e}", exc_info=True)
            print(f"❌ 테스트 매매 오류: {e}")
            import traceback
            traceback.print_exc()

    def start(self):
        """봇 시작"""
        if not self.is_initialized:
            logger.error("봇이 초기화되지 않았습니다")
            print("❌ 오류: 봇이 초기화되지 않았습니다")
            return

        print("\n" + "="*60)
        print("🚀 AutoTrade Pro v2.0 메인 루프 시작")
        print("="*60)
        logger.info("="*60)
        logger.info("🚀 AutoTrade Pro v2.0 실행 시작")
        logger.info("="*60)

        self.is_running = True

        try:
            # v5.7.5: 삼성전자 자동 매매 제거 (사용자 요청)
            # # 🧪 삼성전자 테스트 매매 실행
            # self._test_samsung_trade()

            # 메인 루프 시작
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("사용자에 의한 중단")
            print("\n사용자에 의한 중단")
        except Exception as e:
            logger.error(f"메인 루프 오류: {e}", exc_info=True)
            print(f"\n❌ 메인 루프 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()

    def stop(self):
        """봇 정지"""
        logger.info("AutoTrade Pro v2.0 종료 중...")
        self.is_running = False

        # 가상 매매 상태 저장
        if self.virtual_trader:
            try:
                logger.info("📝 가상 매매 상태 저장 중...")
                self.virtual_trader.save_all_states()
                logger.info("✓ 가상 매매 상태 저장 완료")
            except Exception as e:
                logger.warning(f"가상 매매 상태 저장 실패: {e}")

        # 가상 매매 로그 요약 출력
        if self.trade_logger:
            try:
                self.trade_logger.print_summary()
            except Exception as e:
                logger.warning(f"가상 매매 로그 요약 출력 실패: {e}")

        # WebSocketManager 종료
        if self.websocket_manager:
            try:
                import asyncio
                asyncio.run(self.websocket_manager.disconnect())
                logger.info("✓ WebSocketManager 연결 종료")
            except Exception as e:
                logger.warning(f"WebSocketManager 종료 실패: {e}")

        if self.db_session:
            self.db_session.close()

        if self.client:
            self.client.close()

        logger.info("✅ AutoTrade Pro v2.0 종료 완료")

    def _main_loop(self):
        """메인 루프"""
        cycle_count = 0
        # Backward compatibility: handle both Pydantic (object) and old config (dict)
        try:
            if hasattr(self.config.main_cycle, 'sleep_seconds'):
                sleep_seconds = self.config.main_cycle.sleep_seconds
            else:
                sleep_seconds = self.config.main_cycle.get('sleep_seconds', 60)
        except Exception as e:
            logger.warning(f"Config 로드 실패, 기본값 사용: {e}")
            sleep_seconds = 60

        while self.is_running:
            cycle_count += 1

            # 첫 사이클이 아니면 대기
            if cycle_count > 1:
                logger.info(f"⏳ {sleep_seconds}초 대기...\n")
                time.sleep(sleep_seconds)

            print(f"\n{'='*60}")
            print(f"🔄 사이클 #{cycle_count}")
            print(f"{'='*60}")

            try:
                self._read_control_file()
                if not self.is_running:
                    break

                trading_hours_ok = self._check_trading_hours()
                if not trading_hours_ok:
                    continue

                self._update_account_info()

                # 가상 매매 가격 업데이트 및 매도 검토
                if self.virtual_trader:
                    try:
                        # 가상 계좌의 모든 포지션 가격 업데이트
                        price_data = self._get_virtual_trading_prices()
                        if price_data:
                            self.virtual_trader.update_all_prices(price_data)

                        # 가상 매매 매도 조건 확인
                        self.virtual_trader.check_sell_conditions(price_data)
                    except Exception as e:
                        logger.warning(f"가상 매매 업데이트 실패: {e}")

                # 매도 검토
                if not self.pause_sell:
                    self._check_sell_signals()

                # 매수 검토
                if not self.pause_buy:
                    self._run_scanning_pipeline()

                self._save_portfolio_snapshot()
                self._print_statistics()

            except Exception as e:
                logger.error(f"메인 루프 오류: {e}", exc_info=True)
                print(f"❌ 메인 루프 오류: {e}")
                import traceback
                traceback.print_exc()

    def _read_control_file(self):
        """제어 파일 읽기"""
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
        """거래 시간 확인 (NXT 시장 포함)"""
        from research.analyzer import Analyzer
        analyzer = Analyzer(self.client)
        market_status = analyzer.get_market_status()

        # 시장 상태 저장 (다른 메서드에서 사용)
        self.market_status = market_status

        # 테스트 모드: 장 운영 시간이 아니어도 실제 API 호출로 탐색/분석/주문 실행
        if not market_status['is_trading_hours']:
            logger.info(f"⏸️  장 운영 시간 아님: {market_status['market_status']}")
            logger.info(f"🧪 테스트 모드 활성화 - 실제 API 호출 실행 (서버에서 주문 거절 예상)")
            # 테스트 모드로 강제 설정
            self.market_status['is_trading_hours'] = True
            self.market_status['is_test_mode'] = True
            self.market_status['market_type'] = '테스트 모드'
            # return False  # 주석 처리: 항상 실행

        # 시장 상태 로그
        if market_status.get('is_test_mode'):
            logger.info(f"🧪 테스트 모드: {market_status['market_status']}")
        elif market_status.get('can_cancel_only'):
            logger.info(f"⚠️  {market_status['market_type']}: {market_status['market_status']}")
        elif market_status.get('order_type_limit') == 'limit_only':
            logger.info(f"📊 {market_status['market_type']}: {market_status['market_status']}")
        else:
            logger.info(f"✅ {market_status['market_type']}: {market_status['market_status']}")

        return True

    def _update_account_info(self):
        """계좌 정보 업데이트 (kt00001 API 응답 필드 사용)"""
        try:
            deposit = self.account_api.get_deposit()
            holdings = self.account_api.get_holdings()

            # kt00001 API 응답 필드 사용 (동일한 필드: dashboard/app_apple.py:234-235)
            deposit_total = int(str(deposit.get('entr', '0')).replace(',', '')) if deposit else 0  # 예수금
            cash = int(str(deposit.get('100stk_ord_alow_amt', '0')).replace(',', '')) if deposit else 0  # 주문가능금액

            # 보유 주식 총 평가금액 계산
            stock_value = sum(int(str(h.get('eval_amt', 0)).replace(',', '')) for h in holdings) if holdings else 0

            # 포트폴리오 업데이트
            self.portfolio_manager.update_portfolio(holdings, cash)

            # 동적 리스크 관리자 업데이트 (총 자산 = 예수금 + 주식평가금액)
            total_capital = deposit_total + stock_value
            self.dynamic_risk_manager.update_capital(total_capital)

            logger.info(f"💰 계좌 정보: 예수금 {deposit_total:,}원, 주문가능금액 {cash:,}원, 주식평가 {stock_value:,}원, 총자산 {total_capital:,}원, 보유 {len(holdings)}개")

        except Exception as e:
            logger.error(f"계좌 정보 업데이트 실패: {e}")

    def _check_sell_signals(self):
        """매도 신호 검토"""
        logger.info("🔍 매도 신호 검토 중...")

        # 테스트 모드 표시
        if self.market_status.get('is_test_mode'):
            logger.info("🧪 테스트 모드: 실제 보유 종목으로 매도 로직 실행 (API 호출, 서버에서 거절 예상)")

        try:
            holdings = self.account_api.get_holdings()

            if not holdings:
                logger.info("보유 종목 없음")
                return

            for holding in holdings:
                # 키움증권 API 필드명 (kt00004)
                stock_code = holding.get('stk_cd', '')  # 종목코드

                # A 접두사 제거 (키움증권 API에서 A005930 형식으로 올 수 있음)
                if stock_code.startswith('A'):
                    stock_code = stock_code[1:]

                stock_name = holding.get('stk_nm')  # 종목명
                current_price = int(holding.get('cur_prc', 0))  # 현재가
                quantity = int(holding.get('rmnd_qty', 0))  # 보유수량
                buy_price = int(holding.get('avg_prc', 0))  # 평균단가

                logger.info(f"보유종목: {stock_name}({stock_code}) {quantity}주 @ {current_price:,}원")

                # 수익률 계산
                profit_loss = (current_price - buy_price) * quantity
                profit_loss_rate = ((current_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0

                # v5.7.5: 손익 알림 체크
                self.alert_manager.check_position_alerts(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    current_price=current_price,
                    buy_price=buy_price,
                    profit_loss_rate=profit_loss_rate,
                    profit_loss_amount=profit_loss
                )

                # 청산 임계값 가져오기
                thresholds = self.dynamic_risk_manager.get_exit_thresholds(buy_price)

                # 매도 조건 확인
                should_sell = False
                sell_reason = ""

                if current_price >= thresholds['take_profit']:
                    should_sell = True
                    sell_reason = f"목표가 도달 ({thresholds['take_profit']:,}원)"
                elif current_price <= thresholds['stop_loss']:
                    should_sell = True
                    sell_reason = f"손절가 도달 ({thresholds['stop_loss']:,}원)"

                if should_sell:
                    logger.info(f"📤 {stock_name} 매도 신호: {sell_reason}")
                    self._execute_sell(stock_code, stock_name, quantity, current_price, profit_loss, profit_loss_rate, sell_reason)

        except Exception as e:
            logger.error(f"매도 검토 실패: {e}")

    def _run_scanning_pipeline(self):
        """3단계 스캐닝 파이프라인 실행"""

        try:
            # 포지션 추가 가능 여부
            can_add = self.portfolio_manager.can_add_position()
            positions = self.portfolio_manager.get_positions()
            if not can_add:
                logger.info("⚠️  최대 포지션 수 도달")
                return

            # 동적 리스크 관리 확인
            current_positions = len(positions)
            should_open = self.dynamic_risk_manager.should_open_position(current_positions)

            if not should_open:
                logger.info("⚠️  리스크 관리: 포지션 진입 불가")
                return

            # 현재 전략 실행 (3가지 전략 순환)
            final_candidates = self.strategy_manager.run_current_strategy()

            # 스캔 진행 상황 업데이트
            strategy_name = self.strategy_manager.get_current_strategy_name() if hasattr(self.strategy_manager, 'get_current_strategy_name') else '시장 스캔'
            self.scan_progress['current_strategy'] = strategy_name
            self.scan_progress['total_candidates'] = len(final_candidates)
            self.scan_progress['rejected'] = []
            self.scan_progress['approved'] = []

            # v5.7.5: 전략명을 scan_type으로 매핑
            strategy_to_scan_type = {
                '거래량 순위': 'volume_based',
                '상승률 순위': 'price_change',
                'AI 매매 분석': 'ai_driven',
            }
            scan_type = strategy_to_scan_type.get(strategy_name, 'default')

            if not final_candidates:
                print("✅ 스캐닝 완료: 최종 후보 없음")
                logger.info("✅ 스캐닝 완료: 최종 후보 없음")
                return

            # 20개 모두 스코어링 시스템으로 점수 계산
            candidate_scores = {}
            for candidate in final_candidates:
                stock_data = {
                    # 기본 정보
                    'stock_code': candidate.code,
                    'stock_name': candidate.name,
                    'current_price': candidate.price,
                    'volume': candidate.volume,
                    'change_rate': candidate.rate,

                    # 투자자 매매 정보 (Deep Scan에서 수집됨)
                    'institutional_net_buy': candidate.institutional_net_buy,
                    'foreign_net_buy': candidate.foreign_net_buy,
                    'bid_ask_ratio': candidate.bid_ask_ratio,
                    'institutional_trend': getattr(candidate, 'institutional_trend', None),  # ka10045 기관매매추이 데이터

                    # 일봉 데이터에서 계산된 필드 (Deep Scan에서 수집됨)
                    'avg_volume': getattr(candidate, 'avg_volume', None),  # 평균 거래량 (20일)
                    'volatility': getattr(candidate, 'volatility', None),  # 변동성 (20일 표준편차)

                    # 증권사별 매매동향 (Deep Scan에서 수집됨, ka10078)
                    'top_broker_buy_count': getattr(candidate, 'top_broker_buy_count', 0),  # 주요 증권사 순매수 카운트
                    'top_broker_net_buy': getattr(candidate, 'top_broker_net_buy', 0),  # 주요 증권사 순매수 총액

                    # 체결강도 및 프로그램매매 (Deep Scan에서 수집됨, ka10047, ka90013)
                    'execution_intensity': getattr(candidate, 'execution_intensity', None),  # 체결 강도 (ka10047)
                    'program_net_buy': getattr(candidate, 'program_net_buy', None),         # 프로그램순매수 (ka90013)

                    # 미구현 필드 (API 없음)
                    'is_trending_theme': False,   # 테마 여부 (API 없음)
                    'has_positive_news': False,   # 긍정 뉴스 (API 없음)

                    # 기술적 지표는 없지만 가격/거래량 데이터로 추정 가능 (scoring_system에서 처리)
                }
                # v5.7.5: scan_type 전달하여 스캔별 차별화된 가중치 적용
                scoring_result = self.scoring_system.calculate_score(stock_data, scan_type=scan_type)
                candidate_scores[candidate.code] = scoring_result
                candidate.final_score = scoring_result.total_score

            # 점수 기준 재정렬
            final_candidates.sort(key=lambda x: x.final_score, reverse=True)

            # 상위 5개만 표시 및 AI 검토
            top5 = final_candidates[:5]
            print(f"\n📊 상위 5개 후보:")

            # scan_progress 업데이트 - 상위 후보
            self.scan_progress['top_candidates'] = []

            for rank, c in enumerate(top5, 1):
                score_result = candidate_scores[c.code]

                # 전체 점수 breakdown (0점 포함)
                breakdown_full = (
                    f"거래량:{score_result.volume_surge_score:.0f}/60, "
                    f"가격:{score_result.price_momentum_score:.0f}/60, "
                    f"기관:{score_result.institutional_buying_score:.0f}/60, "
                    f"호가:{score_result.bid_strength_score:.0f}/40, "
                    f"체결:{score_result.execution_intensity_score:.0f}/40, "
                    f"증권사:{score_result.broker_activity_score:.0f}/40, "
                    f"프로그램:{score_result.program_trading_score:.0f}/40, "
                    f"기술:{score_result.technical_indicators_score:.0f}/40, "
                    f"모멘텀:{score_result.theme_news_score:.0f}/40, "
                    f"변동성:{score_result.volatility_pattern_score:.0f}/20"
                )

                # 요약 (0점 초과만)
                breakdown_parts = []
                if score_result.volume_surge_score > 0:
                    breakdown_parts.append(f"거래량:{score_result.volume_surge_score:.0f}")
                if score_result.price_momentum_score > 0:
                    breakdown_parts.append(f"가격:{score_result.price_momentum_score:.0f}")
                if score_result.institutional_buying_score > 0:
                    breakdown_parts.append(f"기관:{score_result.institutional_buying_score:.0f}")
                if score_result.bid_strength_score > 0:
                    breakdown_parts.append(f"호가:{score_result.bid_strength_score:.0f}")
                if score_result.technical_indicators_score > 0:
                    breakdown_parts.append(f"기술:{score_result.technical_indicators_score:.0f}")
                breakdown_str = ", ".join(breakdown_parts) if breakdown_parts else "기타"

                percentage = (c.final_score / 440) * 100
                print(f"   {rank}. {c.name} - {c.final_score:.0f}점 ({percentage:.0f}%) [{breakdown_str}]")
                print(f"      상세: {breakdown_full}")

                # scan_progress에 추가
                self.scan_progress['top_candidates'].append({
                    'rank': rank,
                    'name': c.name,
                    'code': c.code,
                    'score': c.final_score,
                    'percentage': percentage,
                    'breakdown': breakdown_str
                })

            # 포트폴리오 정보
            portfolio_info = "No positions"

            # AI 매수 검토 (상위 3개)
            for idx, candidate in enumerate(top5[:3], 1):
                # scan_progress 업데이트 - 현재 검토 중
                self.scan_progress['reviewing'] = f"{candidate.name} ({idx}/3)"

                print(f"\n🤖 [{idx}/3] {candidate.name}")

                # 이미 계산된 점수 사용
                scoring_result = candidate_scores[candidate.code]

                # AI 분석 실행
                stock_data = {
                    'stock_code': candidate.code,
                    'stock_name': candidate.name,
                    'current_price': candidate.price,
                    'volume': candidate.volume,
                    'change_rate': candidate.rate,
                    'institutional_net_buy': candidate.institutional_net_buy,
                    'foreign_net_buy': candidate.foreign_net_buy,
                    'bid_ask_ratio': candidate.bid_ask_ratio,
                    'institutional_trend': getattr(candidate, 'institutional_trend', None),  # ka10045 기관매매추이 데이터
                }

                # 점수 breakdown 생성 (AI에게 전달)
                score_info = {
                    'score': scoring_result.total_score,
                    'max_score': 440,
                    'percentage': scoring_result.percentage,
                    'breakdown': {
                        '거래량 급증 (60점 만점)': scoring_result.volume_surge_score,
                        '가격 모멘텀 (60점 만점)': scoring_result.price_momentum_score,
                        '기관 매수세 (60점 만점)': scoring_result.institutional_buying_score,
                        '매수 호가 강도 (40점 만점)': scoring_result.bid_strength_score,
                        '체결 강도 (40점 만점)': scoring_result.execution_intensity_score,
                        '증권사 활동 (40점 만점)': scoring_result.broker_activity_score,
                        '프로그램 매매 (40점 만점)': scoring_result.program_trading_score,
                        '기술적 지표 (40점 만점)': scoring_result.technical_indicators_score,
                        '시장 모멘텀 (40점 만점)': scoring_result.theme_news_score,
                        '변동성 패턴 (20점 만점)': scoring_result.volatility_pattern_score,
                    },
                    '0점 항목 설명': {
                        '체결 강도': '기본값 100 < 최소값 120 (데이터 미수집)',
                        '증권사 활동': '미구현 (향후 ka10078 API 활용 예정)',
                        '프로그램 매매': '미구현 (향후 API 개발 필요)',
                        '테마/뉴스': '미구현 (향후 뉴스 분석 API 연동 예정)',
                        '변동성 패턴': '미구현 (향후 변동성 지표 계산 예정)',
                    }
                }

                # AI에게 매수 여부, 분할 매수 전략 질문
                ai_analysis = self.analyzer.analyze_stock(
                    stock_data,
                    score_info=score_info,
                    portfolio_info=portfolio_info
                )
                ai_signal = ai_analysis.get('signal', 'hold')
                split_strategy = ai_analysis.get('split_strategy', '')

                # AI 분석 결과 저장
                candidate.ai_signal = ai_signal
                candidate.ai_reasons = ai_analysis.get('reasons', [])

                # AI 원본 응답 전체 출력
                if ai_analysis.get('analysis_text'):
                    print(f"   [AI 원본 응답]")
                    for line in ai_analysis['analysis_text'].split('\n'):
                        if line.strip():
                            print(f"   {line}")

                # 결과 출력
                print(f"\n   ✅ AI 결정: {ai_signal.upper()}")

                if ai_signal == 'buy' and split_strategy:
                    print(f"   📊 분할매수 전략:")
                    for line in split_strategy.split('\n'):
                        if line.strip():
                            print(f"      {line}")

                if ai_analysis.get('reasons'):
                    print(f"   💡 사유: {ai_analysis['reasons'][0]}")

                if ai_analysis.get('risks') and ai_analysis['risks']:
                    print(f"   ⚠️  경고: {ai_analysis['risks'][0]}")

                # AI 승인 시 매수 후보 리스트에 추가
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
                    # 최대 10개까지만 유지
                    self.ai_approved_candidates.insert(0, buy_candidate)
                    self.ai_approved_candidates = self.ai_approved_candidates[:10]

                # 최종 승인 조건
                # 조건 1: AI=buy + 점수 250점 이상 (57%)
                # 조건 2: AI=hold + 점수 300점 이상 (68%)
                buy_approved = (
                    (ai_signal == 'buy' and scoring_result.total_score >= 250) or
                    (ai_signal == 'hold' and scoring_result.total_score >= 300)
                )

                if buy_approved:
                    print(f"✅ 매수 조건 충족 - 주문 실행")

                    # scan_progress 업데이트 - 승인
                    self.scan_progress['approved'].append({
                        'name': candidate.name,
                        'price': candidate.price,
                        'strategy': split_strategy,
                        'score': scoring_result.total_score
                    })

                    # 실제 매수 실행
                    self._execute_buy(candidate, scoring_result)

                    # 가상 매매 시스템에도 매수 신호 전달
                    if self.virtual_trader:
                        try:
                            # v5.7.5: Deep Scan 데이터 포함한 전체 필드 전달
                            volume = getattr(candidate, 'volume', 0)
                            avg_volume = getattr(candidate, 'avg_volume', None)

                            stock_data = {
                                # 기본 정보
                                'stock_code': candidate.code,
                                'stock_name': candidate.name,
                                'current_price': candidate.price,
                                'change_rate': candidate.rate,
                                'volume': volume,

                                # Deep Scan 데이터 (가상매매 전략들이 필요로 하는 필드)
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

                                # v5.7.5: 기술적 지표 (Technical Indicators)
                                'rsi': getattr(candidate, 'rsi', None),
                                'macd': getattr(candidate, 'macd', None),
                                'bollinger_bands': getattr(candidate, 'bollinger_bands', None),

                                # 전략들이 기대하는 추가 필드
                                'price_change_percent': candidate.rate,  # change_rate의 별칭
                                'volume_ratio': (volume / avg_volume) if avg_volume and avg_volume > 0 else 1.0,
                                'sector': getattr(candidate, 'sector', 'Unknown'),
                                'per': getattr(candidate, 'per', None),
                                'pbr': getattr(candidate, 'pbr', None),
                                'dividend_yield': getattr(candidate, 'dividend_yield', None),
                            }

                            # Market data 생성 (전략들이 필요로 하는 시장 정보)
                            market_data = {
                                'fear_greed_index': 50,  # 기본값 (중립)
                                'economic_cycle': 'expansion',  # 기본값
                                'market_trend': 'neutral',  # 기본값
                            }

                            ai_analysis_data = {
                                'signal': ai_signal,
                                'split_strategy': split_strategy,
                                'reasons': ai_analysis.get('reasons', []),
                                'score': scoring_result.total_score,
                            }
                            self.virtual_trader.process_buy_signal(stock_data, ai_analysis_data, market_data)
                            print(f"   📝 가상 매매: 12가지 전략으로 매수 시그널 처리 완료 (전체 데이터 전달)")
                        except Exception as e:
                            logger.warning(f"가상 매매 매수 처리 실패: {e}")

                    break  # 1회 사이클에 1개만
                else:
                    reason_text = f"AI={ai_signal}, 점수={scoring_result.total_score:.0f}"
                    print(f"❌ 매수 조건 미충족 ({reason_text})")

                    # scan_progress 업데이트 - 탈락
                    self.scan_progress['rejected'].append({
                        'name': candidate.name,
                        'reason': reason_text,
                        'score': scoring_result.total_score
                    })

            # 검토 완료
            self.scan_progress['reviewing'] = ''
            print("📍 스캔 전략 완료")

        except Exception as e:
            logger.error(f"스캔 전략 실패: {e}", exc_info=True)
            print(f"❌ 스캔 전략 오류: {e}")
            import traceback
            traceback.print_exc()

    def _execute_buy(self, candidate, scoring_result):
        """매수 실행 (NXT 시장 규칙 적용)"""
        try:
            # KRX 종가 결정 시간에는 신규 주문 불가
            if self.market_status.get('can_cancel_only'):
                logger.warning(f"⚠️  {self.market_status['market_type']}: 신규 매수 주문 불가")
                return

            stock_code = candidate.code
            stock_name = candidate.name
            current_price = candidate.price

            # 가용 현금 (kt00001 API 응답 필드 사용)
            deposit = self.account_api.get_deposit()
            holdings = self.account_api.get_holdings()

            # 100% 주문가능금액 = 실제 사용가능액 (동일한 필드 사용: dashboard/app_apple.py:235)
            available_cash = int(str(deposit.get('100stk_ord_alow_amt', '0')).replace(',', '')) if deposit else 0

            logger.debug(f"주문가능금액: {available_cash:,}원")

            # 포지션 크기 계산 (동적 리스크 관리)
            quantity = self.dynamic_risk_manager.calculate_position_size(
                stock_price=current_price,
                available_cash=available_cash
            )

            if quantity == 0:
                logger.warning("매수 가능 수량 0")
                return

            total_amount = current_price * quantity

            logger.info(
                f"💳 {stock_name} 매수 실행: {quantity}주 @ {current_price:,}원 "
                f"(총 {total_amount:,}원)"
            )

            # 주문 유형 결정 (시간대별 자동 선택)
            from utils.trading_date import is_nxt_hours
            from datetime import datetime

            if is_nxt_hours():
                # NXT 시간대
                now = datetime.now()
                if now.hour == 8:
                    # 프리마켓 (08:00-09:00)
                    order_type = '61'  # 장시작전시간외
                    logger.info("📌 프리마켓 주문: 장시작전시간외(61)")
                else:
                    # 애프터마켓 (15:30-20:00)
                    order_type = '81'  # 장마감후시간외
                    logger.info("📌 애프터마켓 주문: 장마감후시간외(81) - 종가로 체결")
            else:
                # 정규장 (09:00-15:30)
                order_type = '0'  # 보통(지정가)
                logger.info("📌 정규장 주문: 보통 지정가(0)")

            # 테스트 모드일 때 로그
            if self.market_status.get('is_test_mode'):
                logger.info(f"🧪 테스트 모드: AI 검토 완료 → 실제 매수 API 호출 (서버에서 거절 예상)")
                logger.info(f"   종목: {stock_name}, AI 점수: {candidate.ai_score}, 종합 점수: {scoring_result.total_score}")

            # 주문 실행
            order_result = self.order_api.buy(
                stock_code=stock_code,
                quantity=quantity,
                price=current_price,
                order_type=order_type
            )

            if order_result:
                order_no = order_result.get('order_no', '')

                # DB에 거래 기록
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

                logger.info(f"✅ {stock_name} 매수 성공 (주문번호: {order_no})")

                # v5.7.5: 매수 알림
                self.alert_manager.alert_position_opened(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    buy_price=current_price,
                    quantity=quantity
                )

                self.monitor.log_activity(
                    'buy',
                    f'✅ {stock_name} 매수: {quantity}주 @ {current_price:,}원',
                    level='success'
                )

        except Exception as e:
            logger.error(f"매수 실행 실패: {e}", exc_info=True)

    def _execute_sell(self, stock_code, stock_name, quantity, price, profit_loss, profit_loss_rate, reason):
        """매도 실행 (NXT 시장 규칙 적용)"""
        try:
            # KRX 종가 결정 시간에는 신규 주문 불가
            if self.market_status.get('can_cancel_only'):
                logger.warning(f"⚠️  {self.market_status['market_type']}: 신규 매도 주문 불가")
                return

            logger.info(
                f"💸 {stock_name} 매도 실행: {quantity}주 @ {price:,}원 "
                f"(손익: {profit_loss:+,}원, {profit_loss_rate:+.2f}%)"
            )

            # 주문 유형 결정 (시간대별 자동 선택)
            from utils.trading_date import is_nxt_hours
            from datetime import datetime

            if is_nxt_hours():
                # NXT 시간대
                now = datetime.now()
                if now.hour == 8:
                    # 프리마켓 (08:00-09:00)
                    order_type = '61'  # 장시작전시간외
                    logger.info("📌 프리마켓 매도: 장시작전시간외(61)")
                else:
                    # 애프터마켓 (15:30-20:00)
                    order_type = '81'  # 장마감후시간외
                    logger.info("📌 애프터마켓 매도: 장마감후시간외(81) - 종가로 체결")
            else:
                # 정규장 (09:00-15:30)
                order_type = '0'  # 보통(지정가)
                logger.info("📌 정규장 매도: 보통 지정가(0)")

            # 테스트 모드일 때 로그
            if self.market_status.get('is_test_mode'):
                logger.info(f"🧪 테스트 모드: 매도 조건 충족 → 실제 매도 API 호출 (서버에서 거절 예상)")
                logger.info(f"   종목: {stock_name}, 사유: {reason}, 손익: {profit_loss:+,}원 ({profit_loss_rate:+.2f}%)")

            # 주문 실행
            order_result = self.order_api.sell(
                stock_code=stock_code,
                quantity=quantity,
                price=price,
                order_type=order_type
            )

            if order_result:
                order_no = order_result.get('order_no', '')

                # DB에 거래 기록
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
                logger.info(f"✅ {stock_name} 매도 성공 (주문번호: {order_no})")

                # v5.7.5: 매도 알림
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
                    f'✅ {stock_name} 매도: {quantity}주 @ {price:,}원 (손익: {profit_loss:+,}원)',
                    level=log_level
                )

        except Exception as e:
            logger.error(f"매도 실행 실패: {e}", exc_info=True)

    def _save_portfolio_snapshot(self):
        """포트폴리오 스냅샷 저장"""
        try:
            summary = self.portfolio_manager.get_portfolio_summary()

            snapshot = PortfolioSnapshot(
                total_capital=summary['total_assets'],
                cash=summary['cash'],
                stock_value=summary['stocks_value'],  # Fixed: stocks_value -> stock_value
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
        """
        가상 매매용 현재 가격 조회
        ✅ v5.15: NXT 시간대(15:30~20:00) 실시간 현재가 정확 반영
        """
        try:
            if not self.virtual_trader:
                return {}

            # 모든 가상 계좌의 포지션에서 종목 코드 추출
            all_stock_codes = set()
            for account in self.virtual_trader.accounts.values():
                all_stock_codes.update(account.positions.keys())

            if not all_stock_codes:
                return {}

            # NXT 실시간 가격 관리자 사용
            from utils.nxt_realtime_price import get_nxt_price_manager
            nxt_manager = get_nxt_price_manager(self.market_api)

            # 각 종목의 현재가 조회 (NXT 시간대 자동 처리)
            price_data = {}
            for stock_code in all_stock_codes:
                try:
                    # ✅ NXT 시간대 실시간 현재가 조회 (종가 아님!)
                    price_info = nxt_manager.get_realtime_price(stock_code)
                    if price_info:
                        price_data[stock_code] = price_info['current_price']
                        if price_info.get('is_nxt_hours'):
                            logger.debug(f"NXT 실시간 가격: {stock_code} {price_info['current_price']:,}원")
                except Exception as e:
                    logger.warning(f"가격 조회 실패 ({stock_code}): {e}")
                    continue

            return price_data

        except Exception as e:
            logger.error(f"가상 매매 가격 조회 실패: {e}")
            return {}

    def _print_statistics(self):
        """통계 출력"""
        try:
            logger.info("\n" + "="*60)
            logger.info("📊 실시간 통계")
            logger.info("="*60)

            # 포트폴리오
            summary = self.portfolio_manager.get_portfolio_summary()
            logger.info(f"💰 총 자산: {summary['total_assets']:,}원")
            logger.info(f"💵 현금: {summary['cash']:,}원")
            logger.info(f"📈 수익률: {summary['total_profit_loss_rate']:+.2f}%")
            logger.info(f"📦 포지션: {summary['position_count']}개")

            # 리스크 모드
            risk_status = self.dynamic_risk_manager.get_status_summary()
            logger.info(f"🛡️  리스크 모드: {self.dynamic_risk_manager.get_mode_description()}")
            logger.info(f"📊 최대 포지션: {risk_status['config']['max_open_positions']}개")

            # 스캐닝 상태
            if self.strategy_manager:
                current_strategy = self.strategy_manager.get_current_strategy_name() if hasattr(self.strategy_manager, 'get_current_strategy_name') else '알 수 없음'
                logger.info(f"🔍 현재 전략: {current_strategy}")
                logger.info(f"📊 스캔 진행: {len(self.scan_progress.get('top_candidates', []))}개 후보 발견")
            else:
                logger.info(f"🔍 스캐닝 대기 중...")

            # 가상 매매 성과
            if self.virtual_trader:
                try:
                    logger.info("\n" + "-"*60)
                    logger.info("📝 가상 매매 성과 (3가지 전략)")
                    logger.info("-"*60)
                    self.virtual_trader.print_performance()
                except Exception as e:
                    logger.warning(f"가상 매매 성과 출력 실패: {e}")

            logger.info("="*60 + "\n")

        except Exception as e:
            logger.error(f"통계 출력 실패: {e}")

    # ==================== WebSocket 콜백 메서드 ====================

    def _on_ws_open(self, ws):
        """WebSocket 연결 성공 콜백"""
        logger.info("🔌 WebSocket 연결 성공 - 실시간 데이터 수신 시작")
        self.monitor.log_activity(
            'system',
            '🔌 WebSocket 연결 성공',
            level='success'
        )

        # 실시간 데이터 구독 시작
        try:
            # 보유 종목에 대한 실시간 가격 구독
            if self.portfolio_manager and hasattr(self.portfolio_manager, 'get_positions'):
                positions = self.portfolio_manager.get_positions()
                if not positions:
                    logger.info("보유 종목 없음 - 구독 생략")
                    return

                for position in positions:
                    # position이 딕셔너리인지 문자열인지 확인
                    if isinstance(position, dict):
                        stock_code = position.get('stock_code')
                    elif isinstance(position, str):
                        # position이 문자열이면 종목코드 그 자체
                        stock_code = position
                    else:
                        logger.warning(f"알 수 없는 position 타입: {type(position)}")
                        continue

                    if stock_code and self.websocket_client:
                        # TODO: Kiwoom API의 실제 구독 메시지 형식으로 교체 필요
                        # 현재는 테스트 형식 (실제 API 문서 확인 필요)
                        self.websocket_client.subscribe({
                            'type': 'price',
                            'stock_code': stock_code
                        })
                        logger.debug(f"실시간 가격 구독 요청: {stock_code}")

                logger.info("✓ 실시간 데이터 구독 완료")
            else:
                logger.info("보유 종목 없음 - 구독 생략")
        except Exception as e:
            logger.warning(f"실시간 데이터 구독 중 오류: {e}")
            import traceback
            traceback.print_exc()

    def _on_ws_message(self, data: dict):
        """WebSocket 메시지 수신 콜백"""
        try:
            # 실시간 데이터 처리
            msg_type = data.get('type')

            if msg_type == 'price':
                # 실시간 가격 업데이트
                stock_code = data.get('stock_code')
                price = data.get('price')
                logger.debug(f"실시간 가격: {stock_code} = {price:,}원")

            elif msg_type == 'order':
                # 주문 체결 알림
                logger.info(f"📥 주문 체결 알림: {data.get('message')}")
                self.monitor.log_activity(
                    'order',
                    data.get('message', '주문 체결'),
                    level='info'
                )

        except Exception as e:
            logger.error(f"WebSocket 메시지 처리 중 오류: {e}")

    def _on_ws_error(self, error):
        """WebSocket 에러 콜백"""
        # "Bye" 메시지는 정상 종료이므로 로그 억제
        error_str = str(error)
        if 'Bye' not in error_str:
            logger.error(f"🔌 WebSocket 오류: {error}")
            self.monitor.log_activity(
                'system',
                f'⚠️ WebSocket 오류: {error}',
                level='error'
            )

    def _on_ws_close(self, close_status_code, close_msg):
        """WebSocket 연결 종료 콜백"""
        # 정상 종료(1000)는 로그 억제
        if close_status_code and close_status_code != 1000:
            logger.warning(f"🔌 WebSocket 연결 종료 (코드: {close_status_code}, 메시지: {close_msg})")
            logger.info("🔄 자동 재연결 시도 중...")
            self.monitor.log_activity(
                'system',
                f'⚠️ WebSocket 연결 종료 - 재연결 시도 중',
                level='warning'
            )


def signal_handler(signum, frame):
    """시그널 핸들러"""
    logger.info("\n프로그램 종료 신호 수신")
    sys.exit(0)


def find_anaconda_path():
    """Anaconda 설치 경로 찾기"""
    possible_paths = [
        Path.home() / "anaconda3",
        Path.home() / "Anaconda3",
        Path("C:/ProgramData/Anaconda3"),
        Path("C:/ProgramData/anaconda3"),
    ]

    for path in possible_paths:
        if path.exists() and (path / "Scripts" / "activate.bat").exists():
            return path

    return None


def check_and_install_32bit_packages(conda_path):
    """
    32비트 환경에 필수 패키지가 설치되어 있는지 확인하고 없으면 설치 (최초 1회만)

    Returns:
        True if packages are ready, False otherwise
    """
    # 설치 완료 마커 파일
    marker_file = Path(__file__).parent / ".openapi_packages_installed"

    # 이미 설치 완료했으면 스킵
    if marker_file.exists():
        return True

    print("📦 OpenAPI 서버 패키지 확인 중...")

    # 패키지 체크
    check_cmd = f'"{conda_path / "Scripts" / "activate.bat"}" autotrade_32 && python -c "import flask; from koapy import KiwoomOpenApiPlusEntrypoint"'

    try:
        result = subprocess.run(
            check_cmd,
            shell=True,
            capture_output=True,
            timeout=10
        )

        if result.returncode == 0:
            # 패키지 있음 - 마커 생성
            marker_file.touch()
            print("✅ 패키지 확인 완료")
            return True

    except:
        pass

    # 패키지 없음 - 자동 설치
    print("⚠️  필수 패키지가 설치되지 않았습니다")
    print("📦 자동 설치 중... (최초 1회만, 1-2분 소요)")
    print()

    requirements_file = Path(__file__).parent / "requirements_32bit.txt"
    if not requirements_file.exists():
        print("❌ requirements_32bit.txt 파일을 찾을 수 없습니다")
        print("   수동 설치: install_32bit.bat 실행")
        return False

    install_cmd = f'"{conda_path / "Scripts" / "activate.bat"}" autotrade_32 && pip install -q -r "{requirements_file}"'

    try:
        print("   Installing: Flask, koapy, PyQt5...")
        result = subprocess.run(
            install_cmd,
            shell=True,
            capture_output=True,
            timeout=300  # 5분 타임아웃
        )

        if result.returncode == 0:
            marker_file.touch()
            print("✅ 패키지 설치 완료!")
            print()
            return True
        else:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            print(f"❌ 설치 실패")
            print(f"   수동 설치: install_32bit.bat 실행")
            return False

    except subprocess.TimeoutExpired:
        print("❌ 설치 시간 초과 (5분)")
        print("   수동 설치: install_32bit.bat 실행")
        return False
    except Exception as e:
        print(f"❌ 설치 실패: {e}")
        print("   수동 설치: install_32bit.bat 실행")
        return False


def start_openapi_server():
    """
    OpenAPI 서버를 정상 윈도우로 시작 (로그인 창이 보여야 함)

    Returns:
        subprocess.Popen object or None
    """
    print("🔧 OpenAPI 서버 시작 중 (32-bit)...")

    # Anaconda 경로 찾기
    conda_path = find_anaconda_path()
    if not conda_path:
        print("⚠️  Anaconda를 찾을 수 없습니다 - OpenAPI 기능 비활성화")
        print("   REST API 기능은 정상 작동합니다")
        return None

    # autotrade_32 환경 확인
    env_path = conda_path / "envs" / "autotrade_32"
    if not env_path.exists():
        print("⚠️  autotrade_32 환경을 찾을 수 없습니다 - OpenAPI 기능 비활성화")
        print("   환경 생성: INSTALL_ANACONDA_PROMPT.bat 실행")
        print("   REST API 기능은 정상 작동합니다")
        return None

    # 패키지 확인 및 설치 (최초 1회)
    if not check_and_install_32bit_packages(conda_path):
        print("⚠️  패키지 설치 실패 - OpenAPI 기능 비활성화")
        print("   REST API 기능은 정상 작동합니다")
        return None

    # openapi_server.py 경로
    server_script = Path(__file__).parent / "openapi_server.py"
    if not server_script.exists():
        print("⚠️  openapi_server.py를 찾을 수 없습니다")
        return None

    # 명령어 구성
    activate_script = conda_path / "Scripts" / "activate.bat"
    cmd = f'"{activate_script}" autotrade_32 && python "{server_script}"'

    try:
        # 로그 파일 경로
        log_file = Path(__file__).parent / "openapi_server.log"

        # Windows에서 새 콘솔 창으로 실행 (GUI 표시를 위해)
        if sys.platform == 'win32':
            # CREATE_NEW_CONSOLE: 새 콘솔 창 생성 (Qt GUI 표시에 필요)
            CREATE_NEW_CONSOLE = 0x00000010

            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    creationflags=CREATE_NEW_CONSOLE,
                    stdout=log,
                    stderr=subprocess.STDOUT
                )
        else:
            # Linux/Mac
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=log,
                    stderr=subprocess.STDOUT
                )

        print("✅ OpenAPI 서버 프로세스 시작됨")
        print("   - 서버 URL: http://localhost:5001")
        print("   - 환경: autotrade_32 (32-bit Python 3.10)")
        print("   - 서버 콘솔 창과 OpenAPI 로그인 창이 나타납니다")

        # 서버 초기화 대기 및 헬스체크
        print("   - 서버 초기화 중...", end='', flush=True)

        import requests
        max_retries = 15  # 15초 대기
        for i in range(max_retries):
            time.sleep(1)
            try:
                response = requests.get('http://127.0.0.1:5001/health', timeout=1)
                if response.status_code == 200:
                    print(f" 완료 ({i+1}초)")
                    print("   - 서버 상태: ✅ 정상")
                    return process
            except:
                pass

        print(" ⚠️ 타임아웃")
        print("   - 서버가 응답하지 않습니다 (15초 초과)")
        print("   - 프로세스는 실행 중이나 초기화 실패 가능성")
        print(f"   - 로그 확인: {Path(__file__).parent / 'openapi_server.log'}")
        print("   - REST API 기능은 정상 작동합니다")

        return process

    except Exception as e:
        print(f"⚠️  OpenAPI 서버 시작 실패: {e}")
        print("   REST API 기능은 정상 작동합니다")
        return None


def main():
    """메인 함수"""
    # 시그널 핸들러
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("\n" + "="*60)
    print("AutoTrade Pro v2.0".center(60))
    print("="*60 + "\n")

    # OpenAPI 서버 자동 시작 (백그라운드) - 선택적 사용
    # OpenAPI 서버는 32비트 환경과 koapy가 필요하므로 실패 시 REST API만 사용
    openapi_process = None
    try:
        logger.info("🔧 OpenAPI 서버 시작 시도 중... (실패 시 REST API만 사용)")
        openapi_process = start_openapi_server()
        if openapi_process:
            logger.info("✅ OpenAPI 서버 시작 성공")
        else:
            logger.warning("⚠️  OpenAPI 서버 시작 실패 - REST API만 사용합니다")
    except Exception as e:
        logger.warning(f"⚠️  OpenAPI 서버 시작 실패: {e}")
        logger.warning("   REST API로 계속 진행합니다")
        openapi_process = None
    print()  # 빈 줄

    bot = None
    try:
        # 봇 생성
        print("1. 트레이딩 봇 초기화 중...")
        bot = TradingBotV2()
        print("✓ 트레이딩 봇 초기화 완료\n")

        # 대시보드 시작
        print("2. 웹 대시보드 시작 중...")
        try:
            from dashboard import run_dashboard

            dashboard_thread = threading.Thread(
                target=run_dashboard,
                args=(bot,),
                kwargs={'host': '0.0.0.0', 'port': 5000, 'debug': False},
                daemon=True,
                name='DashboardThread'
            )
            dashboard_thread.start()
            time.sleep(1)

            print("✓ 웹 대시보드 시작 완료")
            print(f"  → http://localhost:5000\n")

        except Exception as e:
            print(f"⚠ 대시보드 시작 실패: {e}\n")

        # 봇 시작
        print("3. 자동매매 봇 시작...")
        print("="*60 + "\n")
        bot.start()

    except KeyboardInterrupt:
        print("\n사용자에 의한 중단")
        return 0
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        logger.error(f"오류: {e}", exc_info=True)
        return 1
    finally:
        # Cleanup: OpenAPI 서버 종료
        print("\n" + "="*60)
        print("Shutting down...")
        print("="*60)

        # 1. HTTP API로 서버에 종료 신호 보내기
        if bot and hasattr(bot, 'openapi_client') and bot.openapi_client:
            try:
                print("🛑 OpenAPI 서버에 종료 신호 전송 중...")
                bot.openapi_client.shutdown_server()
                time.sleep(1)
            except Exception as e:
                pass  # 이미 종료되었을 수 있음

        # 2. 프로세스 강제 종료 (응답 없으면)
        if openapi_process:
            try:
                print("🛑 OpenAPI 서버 프로세스 종료 중...")
                openapi_process.terminate()
                try:
                    openapi_process.wait(timeout=5)
                    print("✅ OpenAPI 서버 종료됨")
                except subprocess.TimeoutExpired:
                    print("⚠️  강제 종료 중...")
                    openapi_process.kill()
                    openapi_process.wait()
                    print("✅ OpenAPI 서버 강제 종료됨")
            except Exception as e:
                print(f"⚠️  프로세스 종료 실패: {e}")

        print("="*60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
