"""
utils/trade_logger.py
거래 실행 기록 및 확인 시스템

모든 매수/매도 거래를 기록하고, 실패/성공 상태를 추적합니다.
Claude Code가 향후 세션에서 거래 이력을 분석할 수 있습니다.
"""
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class TradeType(Enum):
    """거래 유형"""
    BUY = "buy"
    SELL = "sell"
    PARTIAL_BUY = "partial_buy"
    PARTIAL_SELL = "partial_sell"


class TradeStatus(Enum):
    """거래 상태"""
    PENDING = "pending"          # 대기 중
    SUBMITTED = "submitted"      # 주문 제출됨
    PARTIAL_FILLED = "partial"   # 부분 체결
    FILLED = "filled"            # 완전 체결
    REJECTED = "rejected"        # 거부됨
    CANCELLED = "cancelled"      # 취소됨
    FAILED = "failed"            # 실패


@dataclass
class TradeRecord:
    """거래 기록"""
    trade_id: str
    timestamp: str
    trade_type: str
    status: str
    stock_code: str
    stock_name: str
    quantity: int
    price: float
    total_amount: float
    strategy_name: str = ""
    order_number: str = ""
    execution_price: float = 0.0
    execution_quantity: int = 0
    commission: float = 0.0
    profit_loss: float = 0.0
    profit_loss_percent: float = 0.0
    reason: str = ""
    ai_signal: str = ""
    score: float = 0.0
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class TradeLogger:
    """
    거래 실행 로거 (싱글톤)

    모든 거래를 기록하고 상태를 추적합니다.
    """

    _instance: Optional['TradeLogger'] = None
    _lock = threading.Lock()

    # 저장 경로
    TRADE_LOG_FILE = Path("logs/trades.json")
    TRADE_HISTORY_FILE = Path("logs/trade_history.json")

    # 최대 기록 수
    MAX_RECENT_TRADES = 500
    MAX_HISTORY_TRADES = 5000

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True

        # 거래 기록
        self.recent_trades: List[TradeRecord] = []
        self.pending_trades: Dict[str, TradeRecord] = {}

        # 통계
        self.stats = {
            'total_buys': 0,
            'total_sells': 0,
            'successful_buys': 0,
            'successful_sells': 0,
            'failed_trades': 0,
            'total_profit_loss': 0.0,
            'win_count': 0,
            'loss_count': 0
        }

        # 세션 시작 시간
        self.session_start = datetime.now().isoformat()

        # 로그 디렉토리 생성
        self.TRADE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 이전 기록 로드
        self._load_history()

    @classmethod
    def get_instance(cls) -> 'TradeLogger':
        """싱글톤 인스턴스 반환"""
        return cls()

    def _load_history(self):
        """이전 거래 기록 로드"""
        try:
            if self.TRADE_HISTORY_FILE.exists():
                with open(self.TRADE_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.stats = data.get('stats', self.stats)
        except Exception:
            pass

    def _generate_trade_id(self) -> str:
        """거래 ID 생성"""
        import uuid
        return f"TRD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    def log_buy_attempt(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: float,
        strategy_name: str = "",
        ai_signal: str = "",
        score: float = 0.0,
        reason: str = ""
    ) -> str:
        """
        매수 시도 기록

        Returns:
            trade_id: 거래 ID
        """
        trade_id = self._generate_trade_id()

        record = TradeRecord(
            trade_id=trade_id,
            timestamp=datetime.now().isoformat(),
            trade_type=TradeType.BUY.value,
            status=TradeStatus.PENDING.value,
            stock_code=stock_code,
            stock_name=stock_name,
            quantity=quantity,
            price=price,
            total_amount=quantity * price,
            strategy_name=strategy_name,
            ai_signal=ai_signal,
            score=score,
            reason=reason
        )

        with self._lock:
            self.pending_trades[trade_id] = record
            self.stats['total_buys'] += 1

        self._save()

        print(f"📝 [거래기록] 매수 시도: {stock_name} ({stock_code}) {quantity}주 @ {price:,}원")
        return trade_id

    def log_sell_attempt(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: float,
        strategy_name: str = "",
        reason: str = "",
        buy_price: float = 0.0
    ) -> str:
        """
        매도 시도 기록

        Returns:
            trade_id: 거래 ID
        """
        trade_id = self._generate_trade_id()

        # 손익 계산
        profit_loss = (price - buy_price) * quantity if buy_price > 0 else 0
        profit_loss_percent = ((price / buy_price) - 1) * 100 if buy_price > 0 else 0

        record = TradeRecord(
            trade_id=trade_id,
            timestamp=datetime.now().isoformat(),
            trade_type=TradeType.SELL.value,
            status=TradeStatus.PENDING.value,
            stock_code=stock_code,
            stock_name=stock_name,
            quantity=quantity,
            price=price,
            total_amount=quantity * price,
            strategy_name=strategy_name,
            reason=reason,
            profit_loss=profit_loss,
            profit_loss_percent=profit_loss_percent
        )

        with self._lock:
            self.pending_trades[trade_id] = record
            self.stats['total_sells'] += 1

        self._save()

        profit_emoji = "📈" if profit_loss >= 0 else "📉"
        print(f"📝 [거래기록] 매도 시도: {stock_name} ({stock_code}) {quantity}주 @ {price:,}원 {profit_emoji} {profit_loss:+,.0f}원 ({profit_loss_percent:+.2f}%)")
        return trade_id

    def update_trade_status(
        self,
        trade_id: str,
        status: TradeStatus,
        order_number: str = "",
        execution_price: float = 0.0,
        execution_quantity: int = 0,
        error_message: str = ""
    ):
        """거래 상태 업데이트"""
        with self._lock:
            if trade_id in self.pending_trades:
                record = self.pending_trades[trade_id]

                # 상태 업데이트
                record = TradeRecord(
                    **{**asdict(record),
                       'status': status.value,
                       'order_number': order_number or record.order_number,
                       'execution_price': execution_price or record.execution_price,
                       'execution_quantity': execution_quantity or record.execution_quantity,
                       'error_message': error_message}
                )

                # 완료된 거래는 recent_trades로 이동
                if status in [TradeStatus.FILLED, TradeStatus.REJECTED, TradeStatus.CANCELLED, TradeStatus.FAILED]:
                    self.recent_trades.append(record)
                    del self.pending_trades[trade_id]

                    # 통계 업데이트
                    if status == TradeStatus.FILLED:
                        if record.trade_type == TradeType.BUY.value:
                            self.stats['successful_buys'] += 1
                        elif record.trade_type == TradeType.SELL.value:
                            self.stats['successful_sells'] += 1

                            # 손익 통계
                            self.stats['total_profit_loss'] += record.profit_loss
                            if record.profit_loss >= 0:
                                self.stats['win_count'] += 1
                            else:
                                self.stats['loss_count'] += 1

                    elif status in [TradeStatus.REJECTED, TradeStatus.FAILED]:
                        self.stats['failed_trades'] += 1

                    # 최대 기록 수 유지
                    if len(self.recent_trades) > self.MAX_RECENT_TRADES:
                        self.recent_trades = self.recent_trades[-self.MAX_RECENT_TRADES:]

                else:
                    self.pending_trades[trade_id] = record

        self._save()

        # 상태 변경 알림
        status_emoji = {
            TradeStatus.SUBMITTED: "📤",
            TradeStatus.FILLED: "✅",
            TradeStatus.PARTIAL_FILLED: "🔄",
            TradeStatus.REJECTED: "❌",
            TradeStatus.CANCELLED: "🚫",
            TradeStatus.FAILED: "⚠️"
        }.get(status, "📋")

        print(f"{status_emoji} [거래상태] {trade_id}: {status.value}")

    def log_trade_success(
        self,
        trade_id: str,
        order_number: str,
        execution_price: float,
        execution_quantity: int
    ):
        """거래 성공 기록"""
        self.update_trade_status(
            trade_id=trade_id,
            status=TradeStatus.FILLED,
            order_number=order_number,
            execution_price=execution_price,
            execution_quantity=execution_quantity
        )

    def log_trade_failure(
        self,
        trade_id: str,
        error_message: str
    ):
        """거래 실패 기록"""
        self.update_trade_status(
            trade_id=trade_id,
            status=TradeStatus.FAILED,
            error_message=error_message
        )

    def get_pending_trades(self) -> List[Dict[str, Any]]:
        """대기 중인 거래 목록"""
        return [asdict(t) for t in self.pending_trades.values()]

    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """최근 거래 목록"""
        return [asdict(t) for t in self.recent_trades[-limit:]]

    def get_trade_stats(self) -> Dict[str, Any]:
        """거래 통계"""
        win_rate = (
            self.stats['win_count'] / (self.stats['win_count'] + self.stats['loss_count']) * 100
            if (self.stats['win_count'] + self.stats['loss_count']) > 0 else 0
        )

        buy_success_rate = (
            self.stats['successful_buys'] / self.stats['total_buys'] * 100
            if self.stats['total_buys'] > 0 else 0
        )

        sell_success_rate = (
            self.stats['successful_sells'] / self.stats['total_sells'] * 100
            if self.stats['total_sells'] > 0 else 0
        )

        return {
            **self.stats,
            'win_rate': round(win_rate, 2),
            'buy_success_rate': round(buy_success_rate, 2),
            'sell_success_rate': round(sell_success_rate, 2),
            'pending_count': len(self.pending_trades),
            'session_start': self.session_start
        }

    def generate_trade_report(self) -> Dict[str, Any]:
        """거래 보고서 생성"""
        stats = self.get_trade_stats()

        # 오늘 거래 필터링
        today = datetime.now().date().isoformat()
        today_trades = [
            t for t in self.recent_trades
            if t.timestamp.startswith(today)
        ]

        # 오늘 손익
        today_profit_loss = sum(t.profit_loss for t in today_trades if t.trade_type == TradeType.SELL.value)

        report = {
            'report_generated': datetime.now().isoformat(),
            'session_start': self.session_start,
            'stats': stats,
            'today_summary': {
                'trades_count': len(today_trades),
                'buys': len([t for t in today_trades if t.trade_type == TradeType.BUY.value]),
                'sells': len([t for t in today_trades if t.trade_type == TradeType.SELL.value]),
                'profit_loss': round(today_profit_loss, 0)
            },
            'pending_trades': self.get_pending_trades(),
            'recent_trades': self.get_recent_trades(20)
        }

        return report

    def _save(self):
        """저장"""
        try:
            report = self.generate_trade_report()

            with open(self.TRADE_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        except Exception:
            pass

    def save_history(self):
        """전체 히스토리 저장 (세션 종료 시)"""
        try:
            history = {
                'last_updated': datetime.now().isoformat(),
                'stats': self.stats,
                'trades': [asdict(t) for t in self.recent_trades[-self.MAX_HISTORY_TRADES:]]
            }

            with open(self.TRADE_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

        except Exception:
            pass


# 전역 인스턴스 접근 함수
def get_trade_logger() -> TradeLogger:
    """거래 로거 인스턴스 반환"""
    return TradeLogger.get_instance()


def log_buy(stock_code: str, stock_name: str, quantity: int, price: float, **kwargs) -> str:
    """매수 기록 (편의 함수)"""
    return get_trade_logger().log_buy_attempt(stock_code, stock_name, quantity, price, **kwargs)


def log_sell(stock_code: str, stock_name: str, quantity: int, price: float, **kwargs) -> str:
    """매도 기록 (편의 함수)"""
    return get_trade_logger().log_sell_attempt(stock_code, stock_name, quantity, price, **kwargs)


def log_success(trade_id: str, order_number: str, execution_price: float, execution_quantity: int):
    """거래 성공 기록 (편의 함수)"""
    get_trade_logger().log_trade_success(trade_id, order_number, execution_price, execution_quantity)


def log_failure(trade_id: str, error_message: str):
    """거래 실패 기록 (편의 함수)"""
    get_trade_logger().log_trade_failure(trade_id, error_message)


__all__ = [
    'TradeLogger',
    'TradeType',
    'TradeStatus',
    'TradeRecord',
    'get_trade_logger',
    'log_buy',
    'log_sell',
    'log_success',
    'log_failure'
]
