"""
Emergency Auto-Response System
비상 상황 자동 대응 시스템

시장 급락, 급등, 시스템 이상 등에 자동 대응
"""
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import threading
import time

from utils.trading_date import is_nxt_hours

logger = logging.getLogger(__name__)


class EmergencyLevel(Enum):
    """비상 레벨"""
    NORMAL = "normal"          # 정상
    WARNING = "warning"        # 경고 (주의 필요)
    CRITICAL = "critical"      # 위험 (즉시 조치 필요)
    EMERGENCY = "emergency"    # 비상 (전량 청산 고려)


class EmergencyType(Enum):
    """비상 상황 유형"""
    MARKET_CRASH = "market_crash"          # 시장 급락
    PORTFOLIO_LOSS = "portfolio_loss"      # 포트폴리오 손실
    POSITION_LOSS = "position_loss"        # 개별 포지션 손실
    SYSTEM_ERROR = "system_error"          # 시스템 에러
    API_FAILURE = "api_failure"            # API 실패
    CIRCUIT_BREAKER = "circuit_breaker"    # 서킷 브레이커 발동


@dataclass
class EmergencyEvent:
    """비상 상황 이벤트"""
    event_type: EmergencyType
    level: EmergencyLevel
    timestamp: datetime
    description: str
    data: Dict
    action_taken: Optional[str] = None


class EmergencyManager:
    """
    비상 상황 자동 대응 시스템

    기능:
    - 시장 급락/급등 감지
    - 포트폴리오 손실 모니터링
    - 서킷 브레이커
    - 자동 손절/전량 청산
    - 비상 알림
    """

    def __init__(self, config=None, order_api=None, data_fetcher=None):
        """
        Args:
            config: automation_features 설정
            order_api: OrderAPI 인스턴스
            data_fetcher: DataFetcher 인스턴스
        """
        self.config = config or {}
        self.order_api = order_api
        self.data_fetcher = data_fetcher

        # 설정 로드
        self.enabled = self.config.get('emergency_auto_response', True)
        self.emergency_stop_loss_pct = self.config.get('emergency_stop_loss_pct', 0.15)  # 15%
        self.circuit_breaker_enabled = self.config.get('circuit_breaker_enabled', True)

        # 상태
        self.is_monitoring = False
        self.circuit_breaker_active = False
        self.emergency_events: List[EmergencyEvent] = []

        # 임계값
        self.market_crash_threshold = -0.03  # 3% 하락
        self.portfolio_loss_threshold = -0.10  # 10% 손실
        self.position_emergency_threshold = -0.15  # 15% 손실

        # 콜백
        self.emergency_callbacks: List[Callable] = []

        logger.info(f"EmergencyManager initialized - Enabled: {self.enabled}, Circuit Breaker: {self.circuit_breaker_enabled}")

    def start_monitoring(self, bot_instance):
        """
        모니터링 시작

        Args:
            bot_instance: TradingBot 인스턴스
        """
        if not self.enabled:
            logger.info("Emergency monitoring disabled")
            return

        if self.is_monitoring:
            logger.warning("Emergency monitoring already running")
            return

        self.is_monitoring = True

        # 백그라운드 스레드로 모니터링
        monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(bot_instance,),
            daemon=True
        )
        monitor_thread.start()

        logger.info("✅ Emergency monitoring started")

    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_monitoring = False
        logger.info("Emergency monitoring stopped")

    def check_emergency_conditions(
        self,
        portfolio_value: float,
        initial_capital: float,
        positions: List[Dict],
        market_data: Optional[Dict] = None
    ) -> Optional[EmergencyEvent]:
        """
        비상 상황 체크

        Args:
            portfolio_value: 현재 포트폴리오 가치
            initial_capital: 초기 자본
            positions: 포지션 리스트
            market_data: 시장 데이터

        Returns:
            비상 이벤트 (없으면 None)
        """
        # 1. 포트폴리오 손실 체크
        # Fix v6.1.3: 초기 상태(portfolio_value=0 또는 매우 작은 값) 또는 initial_capital이 0인 경우 무시
        if portfolio_value == 0 or portfolio_value < 100000 or initial_capital == 0:
            logger.debug(f"포트폴리오 체크 건너뜀: value={portfolio_value:,}, capital={initial_capital:,}")
            return None

        # Fix v6.1.3: portfolio_value가 initial_capital보다 매우 작으면 데이터 오류로 간주
        if portfolio_value < initial_capital * 0.05:  # 초기 자본의 5% 미만이면 데이터 오류
            logger.warning(f"⚠️ 포트폴리오 데이터 오류 의심: value={portfolio_value:,}, capital={initial_capital:,} (체크 건너뜀)")
            return None

        # Fix v6.1.6: 보유 종목이 없으면 포트폴리오 손실 체크 건너뜀 (청산할 것이 없으므로)
        if not positions or len(positions) == 0:
            logger.debug(f"보유 종목 없음 - 포트폴리오 손실 체크 건너뜀 (value={portfolio_value:,}, capital={initial_capital:,})")
            return None

        # Fix v6.1.7: 포트폴리오 전체 손실 대신 현재 보유 종목의 총 손익률로 체크
        # 과거 누적 손실이 아닌, 현재 활성 포지션의 손익만 고려
        total_purchase_value = 0
        total_current_value = 0

        for position in positions:
            purchase_price = position.get('purchase_price', 0)
            current_price = position.get('current_price', 0)
            quantity = position.get('quantity', 0)

            if purchase_price > 0 and current_price > 0 and quantity > 0:
                total_purchase_value += purchase_price * quantity
                total_current_value += current_price * quantity

        # 보유 종목의 총 손익률 계산
        if total_purchase_value > 0:
            positions_loss_pct = (total_current_value - total_purchase_value) / total_purchase_value

            # 현재 보유 종목이 10% 이상 손실인 경우만 비상 청산
            if positions_loss_pct <= self.portfolio_loss_threshold:
                level = EmergencyLevel.CRITICAL
                if positions_loss_pct <= self.emergency_stop_loss_pct:
                    level = EmergencyLevel.EMERGENCY

                event = EmergencyEvent(
                    event_type=EmergencyType.PORTFOLIO_LOSS,
                    level=level,
                    timestamp=datetime.now(),
                    description=f"보유 종목 손실 {positions_loss_pct*100:.1f}% 발생",
                    data={
                        'total_purchase_value': total_purchase_value,
                        'total_current_value': total_current_value,
                        'loss_pct': positions_loss_pct
                    }
                )
                return event
            else:
                logger.debug(f"보유 종목 손익: {positions_loss_pct*100:+.2f}% (비상 청산 임계값: {self.portfolio_loss_threshold*100:.1f}% 이하)")
        else:
            logger.debug("유효한 보유 종목 가치 없음 - 비상 청산 건너뜀")

        # 2. 개별 포지션 체크
        for position in positions:
            # Fix v6.1.5: 빈 stock_code 필터링
            stock_code = position.get('stock_code', '')
            if not stock_code or stock_code.strip() == '':
                logger.debug("Empty stock_code in position, skipping emergency check")
                continue

            # Fix: 현재가 유효성 체크 (0이거나 None이면 스킵)
            current_price = position.get('current_price', 0)
            purchase_price = position.get('purchase_price', 0)

            if current_price <= 0 or purchase_price <= 0:
                logger.debug(f"Invalid price data for {stock_code} (현재가: {current_price}, 매입가: {purchase_price}) - 긴급청산 스킵")
                continue

            profit_loss_rate = position.get('profit_loss_rate', 0)

            if profit_loss_rate <= -self.position_emergency_threshold:
                # 개별 포지션 15% 이상 손실
                event = EmergencyEvent(
                    event_type=EmergencyType.POSITION_LOSS,
                    level=EmergencyLevel.CRITICAL,
                    timestamp=datetime.now(),
                    description=f"{position.get('stock_name')} 포지션 손실 {profit_loss_rate:.1f}% 발생",
                    data={
                        'stock_code': stock_code,
                        'stock_name': position.get('stock_name'),
                        'loss_rate': profit_loss_rate,
                        'quantity': position.get('quantity')
                    }
                )
                return event

        # 3. 시장 급락 체크 (KOSPI/KOSDAQ)
        if market_data:
            kospi_change = market_data.get('kospi_change_pct', 0)
            kosdaq_change = market_data.get('kosdaq_change_pct', 0)

            if kospi_change <= self.market_crash_threshold or kosdaq_change <= self.market_crash_threshold:
                event = EmergencyEvent(
                    event_type=EmergencyType.MARKET_CRASH,
                    level=EmergencyLevel.WARNING,
                    timestamp=datetime.now(),
                    description=f"시장 급락 감지 - KOSPI: {kospi_change:.2f}%, KOSDAQ: {kosdaq_change:.2f}%",
                    data={
                        'kospi_change': kospi_change,
                        'kosdaq_change': kosdaq_change
                    }
                )
                return event

        return None

    def handle_emergency(self, event: EmergencyEvent, bot_instance) -> bool:
        """
        비상 상황 처리

        Args:
            event: 비상 이벤트
            bot_instance: TradingBot 인스턴스

        Returns:
            처리 성공 여부
        """
        logger.warning(f"🚨 EMERGENCY: {event.description}")

        # 이벤트 기록
        self.emergency_events.append(event)

        # 레벨에 따른 처리
        if event.level == EmergencyLevel.EMERGENCY:
            # EMERGENCY: 전량 청산
            action = self._execute_emergency_liquidation(bot_instance)
            event.action_taken = action

        elif event.level == EmergencyLevel.CRITICAL:
            # CRITICAL: 손실 포지션 청산
            if event.event_type == EmergencyType.POSITION_LOSS:
                action = self._liquidate_position(
                    event.data.get('stock_code'),
                    bot_instance
                )
                event.action_taken = action
            else:
                # 포트폴리오 손실 - 일부 청산
                action = self._partial_liquidation(bot_instance, ratio=0.5)
                event.action_taken = action

        elif event.level == EmergencyLevel.WARNING:
            # WARNING: 서킷 브레이커 활성화
            if self.circuit_breaker_enabled:
                action = self._activate_circuit_breaker()
                event.action_taken = action

        # 콜백 실행
        self._trigger_callbacks(event)

        return True

    def activate_circuit_breaker(self, duration_minutes: int = 30):
        """
        서킷 브레이커 활성화

        Args:
            duration_minutes: 활성화 기간 (분)
        """
        if not self.circuit_breaker_enabled:
            logger.info("Circuit breaker is disabled")
            return

        self.circuit_breaker_active = True
        logger.warning(f"🔴 서킷 브레이커 활성화 - {duration_minutes}분간 모든 매매 중단")

        # 일정 시간 후 자동 해제
        def deactivate():
            time.sleep(duration_minutes * 60)
            self.circuit_breaker_active = False
            logger.info("✅ 서킷 브레이커 해제")

        thread = threading.Thread(target=deactivate, daemon=True)
        thread.start()

    def is_circuit_breaker_active(self) -> bool:
        """서킷 브레이커 활성 여부"""
        return self.circuit_breaker_active

    def register_callback(self, callback: Callable):
        """
        비상 상황 콜백 등록

        Args:
            callback: 콜백 함수 (event: EmergencyEvent)
        """
        self.emergency_callbacks.append(callback)

    def get_recent_events(self, hours: int = 24) -> List[EmergencyEvent]:
        """최근 비상 이벤트 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            event for event in self.emergency_events
            if event.timestamp >= cutoff_time
        ]

    def _monitoring_loop(self, bot_instance):
        """모니터링 루프 (백그라운드)"""
        logger.info("Emergency monitoring loop started")

        while self.is_monitoring:
            try:
                # 포트폴리오 상태 조회
                if hasattr(bot_instance, 'portfolio_manager'):
                    portfolio_value = bot_instance.portfolio_manager.get_total_value()

                    # Fix v6.1.3: dynamic_risk_manager에서 initial_capital 가져오기
                    if hasattr(bot_instance, 'dynamic_risk_manager'):
                        initial_capital = bot_instance.dynamic_risk_manager.initial_capital
                    else:
                        initial_capital = 10000000  # 폴백

                    positions = bot_instance.portfolio_manager.get_positions()

                    # positions가 Dict인 경우 List로 변환
                    if isinstance(positions, dict):
                        positions = list(positions.values())

                    # 비상 상황 체크
                    event = self.check_emergency_conditions(
                        portfolio_value=portfolio_value,
                        initial_capital=initial_capital,
                        positions=positions
                    )

                    if event:
                        self.handle_emergency(event, bot_instance)

            except Exception as e:
                logger.error(f"Emergency monitoring error: {e}", exc_info=True)

            # 30초마다 체크
            time.sleep(30)

    def _execute_emergency_liquidation(self, bot_instance) -> str:
        """전량 청산 실행"""
        logger.critical("🚨🚨 비상 전량 청산 실행 🚨🚨")

        if not self.order_api:
            return "OrderAPI not available"

        try:
            # Fix: NXT 시간대 체크
            is_nxt = is_nxt_hours()
            exchange = 'NXT' if is_nxt else 'KRX'
            logger.info(f"거래소 선택: {exchange} (NXT 시간대: {is_nxt})")

            # Fix v6.1.3: account_api에서 직접 holdings 조회
            if hasattr(bot_instance, 'account_api'):
                holdings = bot_instance.account_api.get_holdings()

                if not holdings:
                    logger.warning("보유 종목 없음 - 청산 불필요")
                    return "No positions to liquidate"

                logger.info(f"청산 대상: {len(holdings)}개 종목")

                for holding in holdings:
                    stock_code = holding.get('stk_cd', '')
                    if stock_code.startswith('A'):
                        stock_code = stock_code[1:]

                    stock_name = holding.get('stk_nm', '')
                    quantity = int(holding.get('rmnd_qty', 0))

                    if not stock_code or quantity == 0:
                        logger.warning(f"잘못된 포지션 데이터: code={stock_code}, qty={quantity}")
                        continue

                    logger.info(f"  청산 시도: {stock_name}({stock_code}) {quantity}주")

                    # 시장가 매도
                    result = self.order_api.sell(
                        stock_code=stock_code,
                        quantity=quantity,
                        price=0,
                        order_type='01',  # 시장가
                        exchange=exchange  # Fix: NXT/KRX 거래소 선택
                    )

                    if result and result.get('success'):
                        logger.info(f"  ✅ {stock_name} {quantity}주 긴급 청산 완료")
                    else:
                        logger.error(f"  ❌ {stock_name} 청산 실패: {result}")

            return f"Emergency liquidation executed for {len(holdings)} positions"

        except Exception as e:
            logger.error(f"Emergency liquidation error: {e}", exc_info=True)
            return f"Liquidation failed: {e}"

    def _liquidate_position(self, stock_code: str, bot_instance) -> str:
        """특정 포지션 청산"""
        # Fix v6.1.3: stock_code 유효성 검사
        if not stock_code or stock_code == '':
            logger.warning("⚠️ 긴급 청산: stock_code가 비어있음 - 청산 불가")
            return "Invalid stock_code"

        # Fix: 장 시간 체크 (장 시작 전/후에는 긴급청산 불가)
        from datetime import datetime
        now = datetime.now()
        # 장 시작 전 (09:00 이전) 또는 장 마감 후 (15:30 이후)
        if now.hour < 9 or (now.hour == 15 and now.minute >= 30) or now.hour > 15:
            logger.warning(f"⚠️ 장 시간 외 긴급청산 시도 차단: {stock_code} (현재 {now.strftime('%H:%M')})")
            return "Market closed - emergency sell blocked"

        logger.warning(f"🔴 긴급 청산: {stock_code}")

        if not self.order_api:
            return "OrderAPI not available"

        try:
            # Fix: NXT 시간대 체크
            is_nxt = is_nxt_hours()
            exchange = 'NXT' if is_nxt else 'KRX'

            # 포지션 조회
            if hasattr(bot_instance, 'portfolio_manager'):
                position = bot_instance.portfolio_manager.get_position(stock_code)

                if position:
                    quantity = position.get('quantity')

                    # 시장가 매도
                    result = self.order_api.sell(
                        stock_code=stock_code,
                        quantity=quantity,
                        price=0,
                        order_type='01',
                        exchange=exchange  # Fix: NXT/KRX 거래소 선택
                    )

                    if result and result.get('success'):
                        return f"Position {stock_code} liquidated"
                    else:
                        return f"Liquidation failed for {stock_code}"

        except Exception as e:
            logger.error(f"Position liquidation error: {e}", exc_info=True)
            return f"Error: {e}"

        return "Position not found"

    def _partial_liquidation(self, bot_instance, ratio: float = 0.5) -> str:
        """부분 청산 (비율만큼)"""
        logger.warning(f"⚠️ 부분 청산 실행: {ratio*100:.0f}%")

        if not self.order_api:
            return "OrderAPI not available"

        liquidated_count = 0

        try:
            # Fix: NXT 시간대 체크
            is_nxt = is_nxt_hours()
            exchange = 'NXT' if is_nxt else 'KRX'

            if hasattr(bot_instance, 'portfolio_manager'):
                positions = bot_instance.portfolio_manager.get_positions()

                for position in positions:
                    stock_code = position.get('stock_code')
                    total_quantity = position.get('quantity')
                    liquidate_quantity = int(total_quantity * ratio)

                    if liquidate_quantity > 0:
                        result = self.order_api.sell(
                            stock_code=stock_code,
                            quantity=liquidate_quantity,
                            price=0,
                            order_type='01',
                            exchange=exchange  # Fix: NXT/KRX 거래소 선택
                        )

                        if result and result.get('success'):
                            liquidated_count += 1

            return f"Partial liquidation: {liquidated_count} positions"

        except Exception as e:
            logger.error(f"Partial liquidation error: {e}", exc_info=True)
            return f"Error: {e}"

    def _activate_circuit_breaker(self) -> str:
        """서킷 브레이커 활성화"""
        self.activate_circuit_breaker(duration_minutes=30)
        return "Circuit breaker activated for 30 minutes"

    def _trigger_callbacks(self, event: EmergencyEvent):
        """콜백 실행"""
        for callback in self.emergency_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")


# Singleton instance
_emergency_manager = None


def get_emergency_manager(config=None, order_api=None, data_fetcher=None):
    """Get emergency manager singleton"""
    global _emergency_manager
    if _emergency_manager is None:
        _emergency_manager = EmergencyManager(config, order_api, data_fetcher)
    return _emergency_manager


__all__ = [
    'EmergencyManager',
    'EmergencyLevel',
    'EmergencyType',
    'EmergencyEvent',
    'get_emergency_manager'
]
