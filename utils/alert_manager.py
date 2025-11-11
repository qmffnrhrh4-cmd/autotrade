"""
utils/alert_manager.py
실시간 알림 시스템

손익 임계값 도달 시 알림 발생
"""
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

from utils.base_manager import BaseManager

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """알림 레벨"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """알림 유형"""
    PROFIT_TARGET = "profit_target"  # 익절 목표 도달
    STOP_LOSS = "stop_loss"  # 손절 기준 도달
    BIG_PROFIT = "big_profit"  # 큰 수익 (예: 10% 이상)
    BIG_LOSS = "big_loss"  # 큰 손실 (예: -5% 이상)
    POSITION_OPENED = "position_opened"  # 신규 포지션
    POSITION_CLOSED = "position_closed"  # 포지션 청산


@dataclass
class Alert:
    """알림 데이터"""
    id: str
    timestamp: datetime
    level: AlertLevel
    alert_type: AlertType
    title: str
    message: str
    stock_code: str
    stock_name: str
    current_price: Optional[int] = None
    profit_loss_rate: Optional[float] = None
    profit_loss_amount: Optional[int] = None
    read: bool = False

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'alert_type': self.alert_type.value,
            'title': self.title,
            'message': self.message,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'current_price': self.current_price,
            'profit_loss_rate': self.profit_loss_rate,
            'profit_loss_amount': self.profit_loss_amount,
            'read': self.read
        }


class AlertManager(BaseManager):
    """알림 관리자"""

    def __init__(self):
        """초기화"""
        super().__init__(name="AlertManager")
        self.alerts: List[Alert] = []
        self.max_alerts = 100

        # 임계값 설정
        self.thresholds = {
            'profit_target': 10.0,
            'stop_loss': -5.0,
            'big_profit': 5.0,
            'big_loss': -3.0,
        }

        # 알림 발생 이력 (중복 방지)
        self._alert_history: Dict[str, datetime] = {}
        self._cooldown_seconds = 300

        self.initialized = True
        self.logger.info("🔔 알림 관리자 초기화 완료")

    def set_thresholds(self, profit_target: float = None, stop_loss: float = None,
                      big_profit: float = None, big_loss: float = None):
        """임계값 설정"""
        if profit_target is not None:
            self.thresholds['profit_target'] = profit_target
        if stop_loss is not None:
            self.thresholds['stop_loss'] = stop_loss
        if big_profit is not None:
            self.thresholds['big_profit'] = big_profit
        if big_loss is not None:
            self.thresholds['big_loss'] = big_loss

        logger.info(f"알림 임계값 설정: {self.thresholds}")

    def check_position_alerts(self, stock_code: str, stock_name: str,
                             current_price: int, buy_price: int,
                             profit_loss_rate: float, profit_loss_amount: int):
        """
        포지션 손익 체크하여 알림 발생

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            current_price: 현재가
            buy_price: 매수가
            profit_loss_rate: 손익률 (%)
            profit_loss_amount: 손익 금액 (원)
        """
        # 익절 목표 도달
        if profit_loss_rate >= self.thresholds['profit_target']:
            self._create_alert(
                alert_type=AlertType.PROFIT_TARGET,
                level=AlertLevel.CRITICAL,
                title=f"🎯 익절 목표 도달: {stock_name}",
                message=f"{profit_loss_rate:+.2f}% 수익 달성! 익절을 고려하세요.",
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                profit_loss_rate=profit_loss_rate,
                profit_loss_amount=profit_loss_amount
            )

        # 손절 기준 도달
        elif profit_loss_rate <= self.thresholds['stop_loss']:
            self._create_alert(
                alert_type=AlertType.STOP_LOSS,
                level=AlertLevel.CRITICAL,
                title=f"⚠️ 손절 기준 도달: {stock_name}",
                message=f"{profit_loss_rate:+.2f}% 손실 발생. 손절을 고려하세요.",
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                profit_loss_rate=profit_loss_rate,
                profit_loss_amount=profit_loss_amount
            )

        # 큰 수익 알림
        elif profit_loss_rate >= self.thresholds['big_profit']:
            self._create_alert(
                alert_type=AlertType.BIG_PROFIT,
                level=AlertLevel.WARNING,
                title=f"📈 큰 수익: {stock_name}",
                message=f"{profit_loss_rate:+.2f}% 수익 중입니다.",
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                profit_loss_rate=profit_loss_rate,
                profit_loss_amount=profit_loss_amount
            )

        # 큰 손실 알림
        elif profit_loss_rate <= self.thresholds['big_loss']:
            self._create_alert(
                alert_type=AlertType.BIG_LOSS,
                level=AlertLevel.WARNING,
                title=f"📉 손실 발생: {stock_name}",
                message=f"{profit_loss_rate:+.2f}% 손실 중입니다.",
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                profit_loss_rate=profit_loss_rate,
                profit_loss_amount=profit_loss_amount
            )

    def alert_position_opened(self, stock_code: str, stock_name: str,
                             buy_price: int, quantity: int):
        """신규 포지션 오픈 알림"""
        self._create_alert(
            alert_type=AlertType.POSITION_OPENED,
            level=AlertLevel.INFO,
            title=f"✅ 신규 매수: {stock_name}",
            message=f"{buy_price:,}원 × {quantity}주 매수 완료",
            stock_code=stock_code,
            stock_name=stock_name,
            current_price=buy_price
        )

    def alert_position_closed(self, stock_code: str, stock_name: str,
                             sell_price: int, profit_loss_rate: float,
                             profit_loss_amount: int, reason: str):
        """포지션 청산 알림"""
        level = AlertLevel.INFO if profit_loss_rate > 0 else AlertLevel.WARNING

        self._create_alert(
            alert_type=AlertType.POSITION_CLOSED,
            level=level,
            title=f"💰 매도 완료: {stock_name}",
            message=f"{sell_price:,}원 매도 ({profit_loss_rate:+.2f}%) - {reason}",
            stock_code=stock_code,
            stock_name=stock_name,
            current_price=sell_price,
            profit_loss_rate=profit_loss_rate,
            profit_loss_amount=profit_loss_amount
        )

    def _create_alert(self, alert_type: AlertType, level: AlertLevel,
                     title: str, message: str, stock_code: str, stock_name: str,
                     current_price: int = None, profit_loss_rate: float = None,
                     profit_loss_amount: int = None):
        """알림 생성 (중복 체크 포함)"""

        # 중복 체크 (쿨다운)
        alert_key = f"{stock_code}_{alert_type.value}"
        if alert_key in self._alert_history:
            last_time = self._alert_history[alert_key]
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < self._cooldown_seconds:
                return  # 쿨다운 중이면 알림 생성하지 않음

        # 알림 생성
        alert = Alert(
            id=f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}",
            timestamp=datetime.now(),
            level=level,
            alert_type=alert_type,
            title=title,
            message=message,
            stock_code=stock_code,
            stock_name=stock_name,
            current_price=current_price,
            profit_loss_rate=profit_loss_rate,
            profit_loss_amount=profit_loss_amount
        )

        self.alerts.insert(0, alert)  # 최신 알림이 앞에
        self._alert_history[alert_key] = datetime.now()

        # 최대 개수 초과 시 오래된 알림 제거
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[:self.max_alerts]

        # 로그 출력
        logger.info(f"🔔 [알림] {title}: {message}")
        print(f"\n🔔 [알림] {title}")
        print(f"   {message}")

    def get_alerts(self, unread_only: bool = False, limit: int = 50) -> List[Alert]:
        """
        알림 목록 조회

        Args:
            unread_only: 읽지 않은 알림만 조회
            limit: 조회 개수 제한

        Returns:
            알림 리스트
        """
        alerts = self.alerts if not unread_only else [a for a in self.alerts if not a.read]
        return alerts[:limit]

    def mark_as_read(self, alert_id: str):
        """알림 읽음 처리"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.read = True
                break

    def mark_all_as_read(self):
        """모든 알림 읽음 처리"""
        for alert in self.alerts:
            alert.read = False

    def get_unread_count(self) -> int:
        """읽지 않은 알림 개수"""
        return sum(1 for alert in self.alerts if not alert.read)

    def clear_old_alerts(self, days: int = 7):
        """오래된 알림 삭제"""
        cutoff_time = datetime.now()
        self.alerts = [
            alert for alert in self.alerts
            if (cutoff_time - alert.timestamp).days < days
        ]
        logger.info(f"오래된 알림 삭제 완료 (보존: {days}일)")

    def initialize(self) -> bool:
        """초기화"""
        self.initialized = True
        self.logger.info("알림 관리자 초기화 완료")
        return True

    def get_status(self) -> Dict[str, Any]:
        """상태 정보"""
        return {
            **super().get_stats(),
            'total_alerts': len(self.alerts),
            'unread_count': self.get_unread_count(),
            'max_alerts': self.max_alerts,
            'thresholds': self.thresholds,
            'cooldown_seconds': self._cooldown_seconds
        }


# 전역 인스턴스
_alert_manager = None


def get_alert_manager() -> AlertManager:
    """알림 관리자 인스턴스 반환 (싱글톤)"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
