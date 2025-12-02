"""
알림 시스템
다채널 거래 알림 시스템

기능:
- 소리 알림
- 데스크탑 알림
- 텔레그램 봇 연동
- 우선순위 기반 알림
- 알림 기록 관리

Author: AutoTrade Pro
Version: 5.1
"""
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """알림 우선순위"""
    LOW = 1       # 낮음
    MEDIUM = 2    # 보통
    HIGH = 3      # 높음
    CRITICAL = 4  # 긴급


class NotificationChannel(Enum):
    """알림 채널"""
    SOUND = 'sound'        # 소리
    DESKTOP = 'desktop'    # 데스크탑
    TELEGRAM = 'telegram'  # 텔레그램
    EMAIL = 'email'        # 이메일


@dataclass
class Notification:
    """단일 알림"""
    id: str
    timestamp: str
    priority: str  # 'low', 'medium', 'high', 'critical'
    category: str  # 'trade', 'ai', 'alert', 'system'
    title: str
    message: str
    channels: List[str]  # 사용할 채널
    data: Dict[str, Any] = None  # 추가 데이터
    delivered: bool = False  # 전달 완료
    read: bool = False  # 읽음 여부


class NotificationManager:
    """
    다채널 알림 관리자

    소리, 데스크탑, 텔레그램 알림 처리
    """

    def __init__(self):
        """알림 관리자 초기화"""
        self.enabled = True
        self.sound_enabled = True
        self.desktop_enabled = True
        self.telegram_enabled = False

        # 텔레그램 설정 - credentials.py에서 초기값 로드
        try:
            from config import get_credentials
            creds = get_credentials()
            telegram_config = creds.get_telegram_config()
            self.telegram_bot_token: Optional[str] = telegram_config.get('bot_token')
            self.telegram_chat_id: Optional[str] = telegram_config.get('chat_id')

            # 텔레그램 설정이 있으면 자동 활성화
            if self.telegram_bot_token and self.telegram_chat_id:
                self.telegram_enabled = True
                logger.info("✓ 텔레그램 설정 로드 완료")
        except Exception as e:
            logger.warning(f"텔레그램 설정 로드 실패: {e}")
            self.telegram_bot_token: Optional[str] = None
            self.telegram_chat_id: Optional[str] = None

        # 알림 기록
        self.notifications: List[Notification] = []

        # 소리 파일 디렉토리
        self.sounds_dir = Path('dashboard/static/sounds')
        self.sounds_dir.mkdir(parents=True, exist_ok=True)

        # 설정 파일
        self.config_file = Path('config/notifications.json')
        self.history_file = Path('data/notifications.json')

        self._load_config()
        self._load_history()

    def _load_config(self):
        """알림 설정 로드"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.enabled = config.get('enabled', True)
                    self.sound_enabled = config.get('sound_enabled', True)
                    self.desktop_enabled = config.get('desktop_enabled', True)
                    self.telegram_enabled = config.get('telegram_enabled', False)
                    self.telegram_bot_token = config.get('telegram_bot_token')
                    self.telegram_chat_id = config.get('telegram_chat_id')
        except Exception as e:
            logger.error(f"알림 설정 로드 오류: {e}")

    def _save_config(self):
        """알림 설정 저장"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'enabled': self.enabled,
                    'sound_enabled': self.sound_enabled,
                    'desktop_enabled': self.desktop_enabled,
                    'telegram_enabled': self.telegram_enabled,
                    'telegram_bot_token': self.telegram_bot_token,
                    'telegram_chat_id': self.telegram_chat_id
                }, f, indent=2)
        except Exception as e:
            logger.error(f"알림 설정 저장 오류: {e}")

    def _load_history(self):
        """알림 기록 로드"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notifications = [Notification(**n) for n in data.get('notifications', [])][-100:]  # 최근 100개 유지
        except Exception as e:
            logger.error(f"알림 기록 로드 오류: {e}")

    def _save_history(self):
        """알림 기록 저장"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'notifications': [asdict(n) for n in self.notifications[-100:]],
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"알림 기록 저장 오류: {e}")

    def send(
        self,
        title: str,
        message: str,
        priority: str = 'medium',
        category: str = 'system',
        channels: List[str] = None,
        data: Dict[str, Any] = None
    ) -> Notification:
        """
        알림 발송

        Args:
            title: 알림 제목
            message: 알림 내용
            priority: 우선순위 (low/medium/high/critical)
            category: 카테고리 (trade/ai/alert/system)
            channels: 사용할 채널 목록 (None = 우선순위에 따라 자동 선택)
            data: 추가 데이터

        Returns:
            알림 객체
        """
        if not self.enabled:
            return None

        # 우선순위에 따라 채널 자동 선택
        if channels is None:
            channels = self._auto_select_channels(priority)

        # 알림 생성
        notification = Notification(
            id=f"notif_{int(datetime.now().timestamp())}",
            timestamp=datetime.now().isoformat(),
            priority=priority,
            category=category,
            title=title,
            message=message,
            channels=channels,
            data=data,
            delivered=False,
            read=False
        )

        # 각 채널로 전달
        for channel in channels:
            try:
                if channel == 'sound' and self.sound_enabled:
                    self._send_sound(notification)
                elif channel == 'desktop' and self.desktop_enabled:
                    self._send_desktop(notification)
                elif channel == 'telegram' and self.telegram_enabled:
                    self._send_telegram(notification)
            except Exception as e:
                logger.error(f"{channel} 채널 알림 발송 오류: {e}")

        notification.delivered = True
        self.notifications.append(notification)
        self._save_history()

        logger.info(f"알림 발송: [{priority}] {title}")

        return notification

    def _auto_select_channels(self, priority: str) -> List[str]:
        """우선순위에 따라 채널 자동 선택"""
        if priority == 'critical':
            return ['sound', 'desktop', 'telegram']
        elif priority == 'high':
            return ['sound', 'desktop']
        elif priority == 'medium':
            return ['desktop']
        else:
            return []

    def _send_sound(self, notification: Notification):
        """소리 알림 재생"""
        try:
            # 우선순위에 따른 소리 파일 선택
            sound_map = {
                'critical': 'critical_alert.wav',
                'high': 'high_alert.wav',
                'medium': 'notification.wav',
                'low': 'soft_ping.wav'
            }

            sound_file = sound_map.get(notification.priority, 'notification.wav')
            sound_path = self.sounds_dir / sound_file

            # 소리 파일이 없으면 로그만 출력
            if not sound_path.exists():
                logger.debug(f"소리 파일 없음: {sound_file}")
                return

            # 플랫폼별 소리 재생
            # Windows: winsound.PlaySound(str(sound_path), winsound.SND_FILENAME)
            # Mac: os.system(f"afplay {sound_path}")
            # Linux: os.system(f"aplay {sound_path}")

            logger.info(f"🔊 소리 알림: {sound_file}")

        except Exception as e:
            logger.error(f"소리 재생 오류: {e}")

    def _send_desktop(self, notification: Notification):
        """데스크탑 알림 발송"""
        try:
            # plyer 라이브러리로 크로스플랫폼 알림
            try:
                from plyer import notification as plyer_notif
                plyer_notif.notify(
                    title=notification.title,
                    message=notification.message,
                    app_name='AutoTrade Pro',
                    timeout=10
                )
                logger.info(f"📢 데스크탑 알림 발송: {notification.title}")
            except ImportError:
                # 대체: 로그 출력
                logger.info(f"📢 [데스크탑] {notification.title}: {notification.message}")

        except Exception as e:
            logger.error(f"데스크탑 알림 오류: {e}")

    def _send_telegram(self, notification: Notification):
        """텔레그램 알림 발송"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("텔레그램이 설정되지 않았습니다")
            return

        try:
            import requests

            # 우선순위별 이모지
            priority_emoji = {
                'critical': '🚨',
                'high': '⚠️',
                'medium': 'ℹ️',
                'low': '💬'
            }

            emoji = priority_emoji.get(notification.priority, 'ℹ️')

            telegram_message = f"{emoji} **{notification.title}**\n\n{notification.message}"

            # 텔레그램 Bot API로 발송
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': telegram_message,
                'parse_mode': 'Markdown'
            }

            response = requests.post(url, json=payload, timeout=5)

            if response.status_code == 200:
                logger.info(f"📱 텔레그램 알림 발송: {notification.title}")
            else:
                logger.error(f"텔레그램 API 오류: {response.status_code}")

        except Exception as e:
            logger.error(f"텔레그램 알림 오류: {e}")

    # ==================== 편의 메서드 ====================

    def notify_trade(
        self,
        action: str,
        stock_name: str,
        quantity: int,
        price: float,
        reason: str
    ):
        """거래 알림"""
        title = f"{'🟢 매수' if action == 'buy' else '🔴 매도'}: {stock_name}"
        message = f"""
수량: {quantity}주
가격: {price:,}원
총액: {price * quantity:,}원
이유: {reason}
        """.strip()

        self.send(
            title=title,
            message=message,
            priority='high',
            category='trade',
            data={
                'action': action,
                'stock_name': stock_name,
                'quantity': quantity,
                'price': price
            }
        )

    def notify_ai_decision(
        self,
        decision_type: str,
        stock_name: str,
        confidence: float,
        reasoning: List[str]
    ):
        """AI 결정 알림"""
        action_ko = {'buy': '매수', 'sell': '매도', 'hold': '보유'}.get(decision_type.lower(), decision_type)
        title = f"🤖 AI 결정: {action_ko} - {stock_name}"
        message = f"""
신뢰도: {confidence:.0%}
분석 근거:
{chr(10).join(f"  • {r}" for r in reasoning)}
        """.strip()

        priority = 'high' if confidence > 0.8 else 'medium'

        self.send(
            title=title,
            message=message,
            priority=priority,
            category='ai',
            data={
                'decision_type': decision_type,
                'stock_name': stock_name,
                'confidence': confidence
            }
        )

    def notify_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        priority: str = 'medium'
    ):
        """일반 경고 알림"""
        self.send(
            title=f"⚠️ {title}",
            message=message,
            priority=priority,
            category='alert'
        )

    def notify_paper_trading_result(
        self,
        strategy_name: str,
        action: str,
        stock_name: str,
        profit_pct: float
    ):
        """가상 매매 결과 알림"""
        emoji = '📈' if profit_pct > 0 else '📉'
        title = f"{emoji} 가상매매: {strategy_name}"
        message = f"""
{action}: {stock_name}
수익률: {profit_pct:+.1f}%
        """.strip()

        self.send(
            title=title,
            message=message,
            priority='low',
            category='paper_trading'
        )

    def configure_telegram(self, bot_token: str, chat_id: str):
        """텔레그램 설정"""
        self.telegram_bot_token = bot_token
        self.telegram_chat_id = chat_id
        self.telegram_enabled = True
        self._save_config()
        logger.info("✓ 텔레그램 설정 완료")

    def get_unread_count(self) -> int:
        """읽지 않은 알림 개수"""
        return sum(1 for n in self.notifications if not n.read)

    def mark_as_read(self, notification_id: str):
        """알림 읽음 처리"""
        for notification in self.notifications:
            if notification.id == notification_id:
                notification.read = True
                self._save_history()
                break

    def mark_all_as_read(self):
        """모든 알림 읽음 처리"""
        for notification in self.notifications:
            notification.read = True
        self._save_history()

    def get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드용 데이터"""
        return {
            'success': True,
            'enabled': self.enabled,
            'channels': {
                'sound': self.sound_enabled,
                'desktop': self.desktop_enabled,
                'telegram': self.telegram_enabled
            },
            'unread_count': self.get_unread_count(),
            'recent_notifications': [asdict(n) for n in self.notifications[-20:]],
            'last_updated': datetime.now().isoformat()
        }


# 전역 인스턴스
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """알림 관리자 싱글톤 인스턴스 반환"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


# 테스트 코드
if __name__ == '__main__':
    manager = NotificationManager()

    print("\n📢 알림 시스템 테스트")
    print("=" * 60)

    # 거래 알림 테스트
    manager.notify_trade(
        action='buy',
        stock_name='삼성전자',
        quantity=100,
        price=73500,
        reason='AI 신뢰도 85%로 강력 매수'
    )

    # AI 결정 알림 테스트
    manager.notify_ai_decision(
        decision_type='buy',
        stock_name='SK하이닉스',
        confidence=0.78,
        reasoning=[
            '거래량 1.8배 폭증',
            'RSI 45로 적정 수준',
            '돌파 변동성 전략 신호'
        ]
    )

    # 경고 알림 테스트
    manager.notify_alert(
        alert_type='system',
        title='AI 모드 활성화',
        message='AI 자율 트레이딩 모드가 활성화되었습니다.',
        priority='high'
    )

    print(f"\n총 알림: {len(manager.notifications)}개")
    print(f"읽지 않은 알림: {manager.get_unread_count()}개")
