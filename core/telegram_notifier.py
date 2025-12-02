"""
core/telegram_notifier.py
텔레그램 알림 시스템

중요한 거래 이벤트를 텔레그램으로 실시간 알림
"""
import os
import json
import logging
import threading
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from queue import Queue, Empty

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """알림 수준"""
    INFO = "info"           # 정보성
    SUCCESS = "success"     # 성공
    WARNING = "warning"     # 경고
    ERROR = "error"         # 에러
    CRITICAL = "critical"   # 긴급


@dataclass
class TelegramMessage:
    """텔레그램 메시지"""
    text: str
    level: AlertLevel
    timestamp: str
    parse_mode: str = "HTML"


class TelegramNotifier:
    """
    텔레그램 알림 발송기 (싱글톤)

    설정:
    - TELEGRAM_BOT_TOKEN: 봇 토큰
    - TELEGRAM_CHAT_ID: 채팅 ID

    .env 파일 또는 환경변수에서 설정
    """

    _instance = None
    _lock = threading.Lock()

    # 알림 수준별 이모지
    LEVEL_EMOJI = {
        AlertLevel.INFO: "ℹ️",
        AlertLevel.SUCCESS: "✅",
        AlertLevel.WARNING: "⚠️",
        AlertLevel.ERROR: "❌",
        AlertLevel.CRITICAL: "🚨"
    }

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

        # 설정 로드
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

        # 설정 파일에서도 로드 시도
        if not self.bot_token or not self.chat_id:
            self._load_from_config()

        self.enabled = bool(self.bot_token and self.chat_id)

        # 메시지 큐
        self.message_queue: Queue = Queue()
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None

        # 속도 제한 (초당 1메시지)
        self.last_send_time = 0
        self.min_interval = 1.0

        # 통계
        self.stats = {
            'total_sent': 0,
            'total_failed': 0,
            'last_error': None
        }

        if self.enabled:
            self.start()
            logger.info("텔레그램 알림 시스템 활성화")
        else:
            logger.warning("텔레그램 설정 없음 - 알림 비활성화")

    def _load_from_config(self):
        """설정 파일에서 로드"""
        try:
            config_paths = [
                'config/credentials.json',
                'config/settings.json',
                '.env'
            ]

            for path in config_paths:
                if os.path.exists(path):
                    if path.endswith('.json'):
                        with open(path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            telegram = config.get('telegram', {})
                            self.bot_token = telegram.get('bot_token', self.bot_token)
                            self.chat_id = telegram.get('chat_id', self.chat_id)
                    elif path == '.env':
                        with open(path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if '=' in line:
                                    key, value = line.strip().split('=', 1)
                                    if key == 'TELEGRAM_BOT_TOKEN':
                                        self.bot_token = value.strip('"\'')
                                    elif key == 'TELEGRAM_CHAT_ID':
                                        self.chat_id = value.strip('"\'')
        except Exception as e:
            logger.debug(f"텔레그램 설정 로드 실패: {e}")

    @classmethod
    def get_instance(cls) -> 'TelegramNotifier':
        return cls()

    def start(self):
        """워커 시작"""
        if self.is_running:
            return

        self.is_running = True
        self.worker_thread = threading.Thread(target=self._send_worker, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """워커 중지"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2)

    def _send_worker(self):
        """메시지 발송 워커"""
        while self.is_running:
            try:
                message = self.message_queue.get(timeout=1)
                self._send_message(message)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"텔레그램 발송 오류: {e}")

    def _send_message(self, message: TelegramMessage):
        """실제 메시지 발송"""
        import time

        # 속도 제한
        elapsed = time.time() - self.last_send_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

            emoji = self.LEVEL_EMOJI.get(message.level, "📌")
            formatted_text = f"{emoji} {message.text}"

            payload = {
                'chat_id': self.chat_id,
                'text': formatted_text,
                'parse_mode': message.parse_mode
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                self.stats['total_sent'] += 1
                self.last_send_time = time.time()
                logger.debug(f"텔레그램 전송 성공: {message.text[:50]}...")
            else:
                self.stats['total_failed'] += 1
                self.stats['last_error'] = f"HTTP {response.status_code}"
                logger.warning(f"텔레그램 전송 실패: {response.text}")

        except Exception as e:
            self.stats['total_failed'] += 1
            self.stats['last_error'] = str(e)
            logger.error(f"텔레그램 전송 예외: {e}")

    def send(self, text: str, level: AlertLevel = AlertLevel.INFO):
        """메시지 발송 (큐에 추가)"""
        if not self.enabled:
            return

        message = TelegramMessage(
            text=text,
            level=level,
            timestamp=datetime.now().isoformat()
        )

        self.message_queue.put(message)

    def send_immediate(self, text: str, level: AlertLevel = AlertLevel.CRITICAL):
        """즉시 발송 (큐 우회)"""
        if not self.enabled:
            return

        message = TelegramMessage(
            text=text,
            level=level,
            timestamp=datetime.now().isoformat()
        )

        self._send_message(message)

    # === 편의 함수들 ===

    def notify_trade_executed(
        self,
        stock_name: str,
        trade_type: str,
        quantity: int,
        price: float,
        profit_loss: float = 0
    ):
        """거래 실행 알림"""
        if trade_type.lower() == 'buy':
            text = (
                f"<b>매수 체결</b>\n"
                f"종목: {stock_name}\n"
                f"수량: {quantity:,}주\n"
                f"가격: {price:,.0f}원\n"
                f"금액: {quantity * price:,.0f}원"
            )
            level = AlertLevel.SUCCESS
        else:
            pnl_emoji = "📈" if profit_loss >= 0 else "📉"
            text = (
                f"<b>매도 체결</b>\n"
                f"종목: {stock_name}\n"
                f"수량: {quantity:,}주\n"
                f"가격: {price:,.0f}원\n"
                f"손익: {pnl_emoji} {profit_loss:+,.0f}원"
            )
            level = AlertLevel.SUCCESS if profit_loss >= 0 else AlertLevel.WARNING

        self.send(text, level)

    def notify_risk_warning(self, message: str, risk_level: str):
        """리스크 경고 알림"""
        text = f"<b>리스크 경고</b>\n{message}\n수준: {risk_level}"
        self.send(text, AlertLevel.WARNING)

    def notify_emergency_stop(self, reason: str):
        """긴급 정지 알림"""
        text = f"<b>🚨 긴급 정지</b>\n사유: {reason}\n시간: {datetime.now().strftime('%H:%M:%S')}"
        self.send_immediate(text, AlertLevel.CRITICAL)

    def notify_daily_report(
        self,
        total_pnl: float,
        trade_count: int,
        win_rate: float,
        best_trade: str,
        worst_trade: str
    ):
        """일일 보고서 알림"""
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        text = (
            f"<b>📊 일일 보고서</b>\n\n"
            f"총 손익: {pnl_emoji} {total_pnl:+,.0f}원\n"
            f"거래 횟수: {trade_count}회\n"
            f"승률: {win_rate:.1f}%\n\n"
            f"최고 거래: {best_trade}\n"
            f"최악 거래: {worst_trade}"
        )
        self.send(text, AlertLevel.INFO)

    def notify_signal(self, stock_name: str, signal: str, confidence: float, reason: str):
        """시그널 알림"""
        signal_emoji = "🟢" if signal == 'buy' else "🔴" if signal == 'sell' else "⚪"
        text = (
            f"<b>{signal_emoji} 시그널 감지</b>\n"
            f"종목: {stock_name}\n"
            f"신호: {signal.upper()}\n"
            f"신뢰도: {confidence*100:.0f}%\n"
            f"사유: {reason}"
        )
        self.send(text, AlertLevel.INFO)

    def notify_evolution_result(self, generation: int, best_fitness: float, improvement: float):
        """진화 결과 알림"""
        text = (
            f"<b>🧬 진화 완료</b>\n"
            f"세대: {generation}\n"
            f"최고 적합도: {best_fitness:.2f}\n"
            f"개선율: {improvement:+.2f}%"
        )
        self.send(text, AlertLevel.INFO)

    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        return {
            'enabled': self.enabled,
            'queue_size': self.message_queue.qsize(),
            **self.stats
        }


# 전역 접근 함수
def get_telegram_notifier() -> TelegramNotifier:
    return TelegramNotifier.get_instance()


def send_telegram(text: str, level: AlertLevel = AlertLevel.INFO):
    """텔레그램 발송 편의 함수"""
    get_telegram_notifier().send(text, level)
