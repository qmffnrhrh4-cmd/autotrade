"""
사용자 피드백 시스템 v1.0
실제 트레이더를 위한 명확한 알림 및 가이드 제공

Author: AutoTrade Pro
Version: 1.0

기능:
- 매수/매도 성공/실패 시 명확한 피드백
- 에러 발생 시 한국어 가이드
- 긴급 상황 경고
- 진행 상황 표시
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """알림 레벨"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertCategory(Enum):
    """알림 카테고리"""
    TRADE = "trade"  # 매매 관련
    SYSTEM = "system"  # 시스템 관련
    RISK = "risk"  # 위험 관련
    ACCOUNT = "account"  # 계좌 관련
    NETWORK = "network"  # 네트워크 관련


# 에러 코드별 사용자 친화적 메시지
ERROR_MESSAGES = {
    # API 에러
    "-102": {
        "message": "네트워크 연결 시간이 초과되었습니다",
        "actions": [
            "인터넷 연결 상태를 확인하세요",
            "방화벽 설정을 확인하세요",
            "잠시 후 다시 시도하세요"
        ]
    },
    "401": {
        "message": "인증에 실패했습니다",
        "actions": [
            "API 키가 올바른지 확인하세요",
            "credentials.json 파일을 확인하세요",
            "키움 HTS에서 API 사용 설정을 확인하세요"
        ]
    },
    "429": {
        "message": "API 호출 한도를 초과했습니다",
        "actions": [
            "잠시 후 다시 시도하세요 (약 1분)",
            "호출 빈도를 줄여보세요"
        ]
    },

    # 주문 에러
    "잔고부족": {
        "message": "계좌 잔고가 부족합니다",
        "actions": [
            "계좌에 입금하거나",
            "주문 수량을 줄이세요",
            "현재 잔고: 대시보드에서 확인"
        ]
    },
    "주문가능시간아님": {
        "message": "현재 주문 가능 시간이 아닙니다",
        "actions": [
            "정규장: 09:00~15:30",
            "시간외: 08:00~09:00, 15:40~18:00",
            "야간: 18:00~20:00 (일부 종목)"
        ]
    },
    "호가단위오류": {
        "message": "주문 가격이 호가 단위에 맞지 않습니다",
        "actions": [
            "가격을 호가 단위에 맞게 조정하세요",
            "예: 5만원 이상은 100원 단위"
        ]
    },
    "주문수량오류": {
        "message": "주문 수량이 올바르지 않습니다",
        "actions": [
            "최소 1주 이상 주문하세요",
            "보유 수량 이하로 매도하세요"
        ]
    },

    # 시스템 에러
    "connection_error": {
        "message": "서버에 연결할 수 없습니다",
        "actions": [
            "OpenAPI 서버가 실행 중인지 확인하세요",
            "openapi_server_v2.py를 재시작하세요",
            "키움 HTS가 로그인되어 있는지 확인하세요"
        ]
    },
    "websocket_closed": {
        "message": "실시간 연결이 끊어졌습니다",
        "actions": [
            "자동 재연결을 시도합니다",
            "문제가 지속되면 프로그램을 재시작하세요"
        ]
    }
}

# 리스크 설정 프리셋
RISK_PRESETS = {
    "초보자": {
        "name": "초보자 (안전 우선)",
        "description": "안전하고 보수적인 설정. 처음 시작하는 분께 권장합니다.",
        "settings": {
            "risk_mode": "very_conservative",
            "max_open_positions": 3,
            "risk_per_trade_ratio": 0.05,
            "take_profit_ratio": 0.08,
            "stop_loss_ratio": -0.03,
            "ai_min_score": 8.0,
            "max_daily_loss": -0.05
        },
        "expected_return": "월 2~5% 목표",
        "risk_level": "낮음"
    },
    "중급자": {
        "name": "중급자 (균형)",
        "description": "위험과 수익의 균형. 어느 정도 경험이 있는 분께 권장합니다.",
        "settings": {
            "risk_mode": "normal",
            "max_open_positions": 8,
            "risk_per_trade_ratio": 0.10,
            "take_profit_ratio": 0.12,
            "stop_loss_ratio": -0.05,
            "ai_min_score": 7.0,
            "max_daily_loss": -0.08
        },
        "expected_return": "월 5~10% 목표",
        "risk_level": "중간"
    },
    "고급자": {
        "name": "고급자 (공격적)",
        "description": "높은 수익 추구. 경험 많은 투자자에게만 권장합니다.",
        "settings": {
            "risk_mode": "aggressive",
            "max_open_positions": 12,
            "risk_per_trade_ratio": 0.15,
            "take_profit_ratio": 0.20,
            "stop_loss_ratio": -0.07,
            "ai_min_score": 6.5,
            "max_daily_loss": -0.12
        },
        "expected_return": "월 10~20% 목표 (손실 위험도 높음)",
        "risk_level": "높음"
    }
}


class UserFeedback:
    """사용자 피드백 관리자"""

    def __init__(self, notification_manager=None):
        """
        초기화

        Args:
            notification_manager: 알림 관리자 (Telegram, Desktop 등)
        """
        self.notification_manager = notification_manager
        self.last_portfolio_pl_rate = 0.0
        self.trade_history_today = []

    def show_buy_success(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: int,
        order_no: str
    ):
        """매수 성공 피드백"""
        total_amount = price * quantity

        print("\n" + "=" * 70)
        print("🎉 매수 주문이 접수되었습니다!")
        print("=" * 70)
        print(f"📋 주문 정보:")
        print(f"  • 종목: {stock_name} ({stock_code})")
        print(f"  • 주문번호: {order_no}")
        print(f"  • 수량: {quantity:,}주")
        print(f"  • 가격: {price:,}원")
        print(f"  • 총액: {total_amount:,}원")
        print(f"  • 시간: {datetime.now().strftime('%H:%M:%S')}")
        print(f"\n⏰ 체결 확인:")
        print(f"  체결 여부는 약 1~5초 후 확인됩니다.")
        print(f"  대시보드: http://localhost:5000/trading")
        print("=" * 70 + "\n")

        # 알림 발송
        self._send_notification(
            title="🟢 매수 주문 접수",
            message=f"{stock_name}\n{quantity:,}주 × {price:,}원\n총액: {total_amount:,}원",
            level=AlertLevel.SUCCESS,
            category=AlertCategory.TRADE
        )

        # 거래 기록
        self.trade_history_today.append({
            "time": datetime.now().isoformat(),
            "type": "buy",
            "stock": stock_name,
            "quantity": quantity,
            "price": price,
            "status": "success"
        })

    def show_buy_failure(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: int,
        error_code: str,
        error_msg: str
    ):
        """매수 실패 피드백"""
        error_info = self._get_error_info(error_code, error_msg)

        print("\n" + "=" * 70)
        print("❌ 매수 주문이 실패했습니다")
        print("=" * 70)
        print(f"📋 주문 정보:")
        print(f"  • 종목: {stock_name} ({stock_code})")
        print(f"  • 수량: {quantity:,}주")
        print(f"  • 가격: {price:,}원")
        print(f"\n🚨 실패 원인:")
        print(f"  {error_info['message']}")
        print(f"\n💡 해결 방법:")
        for i, action in enumerate(error_info['actions'], 1):
            print(f"  {i}. {action}")
        print("=" * 70 + "\n")

        # 알림 발송
        self._send_notification(
            title="🔴 매수 실패",
            message=f"{stock_name}\n{error_info['message']}",
            level=AlertLevel.ERROR,
            category=AlertCategory.TRADE
        )

    def show_sell_success(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: int,
        profit_loss: int,
        profit_loss_rate: float,
        order_no: str
    ):
        """매도 성공 피드백"""
        total_amount = price * quantity
        pl_emoji = "📈" if profit_loss >= 0 else "📉"

        print("\n" + "=" * 70)
        print("💰 매도 주문이 접수되었습니다!")
        print("=" * 70)
        print(f"📋 주문 정보:")
        print(f"  • 종목: {stock_name} ({stock_code})")
        print(f"  • 주문번호: {order_no}")
        print(f"  • 수량: {quantity:,}주")
        print(f"  • 가격: {price:,}원")
        print(f"  • 총액: {total_amount:,}원")
        print(f"\n{pl_emoji} 예상 손익:")
        print(f"  • 금액: {profit_loss:+,}원")
        print(f"  • 수익률: {profit_loss_rate:+.2f}%")
        print(f"\n⏰ 시간: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 70 + "\n")

        # 알림 발송
        self._send_notification(
            title="💰 매도 주문 접수",
            message=f"{stock_name}\n{quantity:,}주\n손익: {profit_loss:+,}원 ({profit_loss_rate:+.2f}%)",
            level=AlertLevel.SUCCESS,
            category=AlertCategory.TRADE
        )

    def show_error(self, error_code: str, error_msg: str, context: str = ""):
        """에러 피드백"""
        error_info = self._get_error_info(error_code, error_msg)

        print("\n" + "🚨" * 35)
        print(f"❌ 오류가 발생했습니다")
        if context:
            print(f"   위치: {context}")
        print("🚨" * 35)
        print(f"\n📋 오류 내용:")
        print(f"  {error_info['message']}")
        print(f"\n💡 해결 방법:")
        for i, action in enumerate(error_info['actions'], 1):
            print(f"  {i}. {action}")
        print("\n" + "🚨" * 35 + "\n")

    def show_emergency_warning(
        self,
        title: str,
        message: str,
        current_value: Any = None,
        threshold: Any = None,
        actions: List[str] = None
    ):
        """긴급 경고 표시"""
        print("\n" + "⚠️" * 35)
        print(f"🚨🚨🚨 긴급 경고: {title} 🚨🚨🚨")
        print("⚠️" * 35)
        print(f"\n{message}")

        if current_value is not None:
            print(f"\n📊 현재 상태:")
            print(f"  현재값: {current_value}")
            if threshold is not None:
                print(f"  기준값: {threshold}")

        if actions:
            print(f"\n⚡ 권장 조치:")
            for i, action in enumerate(actions, 1):
                print(f"  {i}. {action}")

        print("\n" + "⚠️" * 35 + "\n")

        # 긴급 알림 발송
        self._send_notification(
            title=f"🚨 긴급: {title}",
            message=message,
            level=AlertLevel.CRITICAL,
            category=AlertCategory.RISK,
            channels=["telegram", "desktop", "sound"]
        )

    def show_portfolio_change(self, old_pl_rate: float, new_pl_rate: float):
        """포트폴리오 변동 알림 (1% 이상 변동시)"""
        change = new_pl_rate - old_pl_rate

        if abs(change) >= 1.0:
            if change > 0:
                print(f"\n📈 포트폴리오 수익률 상승: {old_pl_rate:+.2f}% → {new_pl_rate:+.2f}% (+{change:.2f}%)")
            else:
                print(f"\n📉 포트폴리오 수익률 하락: {old_pl_rate:+.2f}% → {new_pl_rate:+.2f}% ({change:.2f}%)")

            self.last_portfolio_pl_rate = new_pl_rate

    def show_progress(self, step: int, total: int, description: str):
        """진행 상황 표시"""
        progress = (step / total) * 100
        bar_length = 30
        filled = int(bar_length * step / total)
        bar = "█" * filled + "░" * (bar_length - filled)

        print(f"\r  [{bar}] {progress:.0f}% - {description}", end="", flush=True)

        if step == total:
            print(" ✅")

    def show_daily_summary(self, stats: Dict[str, Any]):
        """일일 거래 요약"""
        print("\n" + "=" * 70)
        print("📋 오늘의 거래 요약")
        print("=" * 70)
        print(f"  거래일: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"\n📊 거래 통계:")
        print(f"  • 총 매수: {stats.get('buy_count', 0)}건")
        print(f"  • 총 매도: {stats.get('sell_count', 0)}건")
        print(f"  • 실현 손익: {stats.get('realized_pl', 0):+,}원")
        print(f"  • 평가 손익: {stats.get('unrealized_pl', 0):+,}원")
        print(f"  • 총 손익률: {stats.get('total_pl_rate', 0):+.2f}%")
        print(f"\n💰 계좌 현황:")
        print(f"  • 총 자산: {stats.get('total_assets', 0):,}원")
        print(f"  • 현금: {stats.get('cash', 0):,}원")
        print(f"  • 보유 종목: {stats.get('position_count', 0)}개")
        print("=" * 70 + "\n")

    def show_risk_preset_guide(self):
        """리스크 프리셋 가이드 표시"""
        print("\n" + "=" * 70)
        print("📊 리스크 설정 가이드")
        print("=" * 70)

        for preset_name, preset in RISK_PRESETS.items():
            print(f"\n🔹 {preset['name']}")
            print(f"   {preset['description']}")
            print(f"   예상 수익: {preset['expected_return']}")
            print(f"   위험 수준: {preset['risk_level']}")
            print(f"   주요 설정:")
            print(f"     - 최대 보유 종목: {preset['settings']['max_open_positions']}개")
            print(f"     - 익절 기준: +{preset['settings']['take_profit_ratio']*100:.0f}%")
            print(f"     - 손절 기준: {preset['settings']['stop_loss_ratio']*100:.0f}%")

        print("\n" + "=" * 70)
        print("💡 설정 변경: 대시보드 > 설정 > 리스크 관리")
        print("=" * 70 + "\n")

    def apply_risk_preset(self, preset_name: str) -> bool:
        """
        리스크 프리셋 적용

        Args:
            preset_name: '초보자', '중급자', '고급자' 중 하나

        Returns:
            성공 여부
        """
        if preset_name not in RISK_PRESETS:
            print(f"\n❌ 알 수 없는 프리셋: {preset_name}")
            print(f"   사용 가능한 프리셋: 초보자, 중급자, 고급자")
            return False

        preset = RISK_PRESETS[preset_name]
        settings = preset['settings']

        print("\n" + "=" * 70)
        print(f"🔧 리스크 프리셋 적용: {preset['name']}")
        print("=" * 70)

        try:
            # config.manager를 사용하여 설정 적용
            from config.manager import set_setting

            # 각 설정 적용
            set_setting('risk_management.risk_mode', settings['risk_mode'])
            set_setting('portfolio.max_open_positions', settings['max_open_positions'])
            set_setting('risk_management.risk_per_trade_ratio', settings['risk_per_trade_ratio'])
            set_setting('ai_trading.profit_ratio', settings['take_profit_ratio'])
            set_setting('ai_trading.loss_ratio', settings['stop_loss_ratio'])
            set_setting('ai_trading.ai_min_score', settings['ai_min_score'])
            set_setting('risk_management.max_daily_loss', settings['max_daily_loss'])

            print(f"\n✅ 프리셋 적용 완료!")
            print(f"\n📋 적용된 설정:")
            print(f"  • 리스크 모드: {settings['risk_mode']}")
            print(f"  • 최대 보유 종목: {settings['max_open_positions']}개")
            print(f"  • 종목당 투자 비중: {settings['risk_per_trade_ratio']*100:.0f}%")
            print(f"  • 익절 기준: +{settings['take_profit_ratio']*100:.0f}%")
            print(f"  • 손절 기준: {settings['stop_loss_ratio']*100:.0f}%")
            print(f"  • AI 최소 점수: {settings['ai_min_score']}")
            print(f"  • 일일 최대 손실: {settings['max_daily_loss']*100:.0f}%")
            print(f"\n⚠️ 예상 수익: {preset['expected_return']}")
            print(f"⚠️ 위험 수준: {preset['risk_level']}")
            print("=" * 70 + "\n")

            return True

        except ImportError:
            logger.warning("config.manager를 불러올 수 없습니다")
            print(f"\n⚠️ 설정 시스템을 불러올 수 없습니다.")
            print(f"   대시보드에서 수동으로 설정하세요.")
            return False
        except Exception as e:
            logger.error(f"프리셋 적용 실패: {e}")
            print(f"\n❌ 프리셋 적용 실패: {e}")
            return False

    def show_connection_status(
        self,
        api_connected: bool,
        websocket_connected: bool,
        openapi_connected: bool
    ):
        """연결 상태 표시"""
        print("\n" + "=" * 70)
        print("🔌 연결 상태")
        print("=" * 70)
        print(f"  REST API:    {'✅ 연결됨' if api_connected else '❌ 연결 끊김'}")
        print(f"  WebSocket:   {'✅ 연결됨' if websocket_connected else '❌ 연결 끊김'}")
        print(f"  OpenAPI:     {'✅ 연결됨' if openapi_connected else '❌ 연결 끊김'}")

        if not all([api_connected, websocket_connected, openapi_connected]):
            print(f"\n⚠️ 일부 연결에 문제가 있습니다.")
            print(f"   1. 인터넷 연결 확인")
            print(f"   2. openapi_server_v2.py 실행 여부 확인")
            print(f"   3. 키움 HTS 로그인 상태 확인")
        print("=" * 70 + "\n")

    def show_startup_summary(
        self,
        version: str,
        mode: str,
        account_balance: int,
        positions_count: int,
        ai_enabled: bool
    ):
        """시작 시 요약 정보 표시"""
        print("\n" + "=" * 70)
        print(f"🚀 AutoTrade Pro {version} 시작")
        print("=" * 70)
        print(f"\n📊 현재 상태:")
        print(f"  • 모드: {mode}")
        print(f"  • 계좌 잔고: {account_balance:,}원")
        print(f"  • 보유 종목: {positions_count}개")
        print(f"  • AI 분석: {'활성화' if ai_enabled else '비활성화'}")
        print(f"\n⏰ 거래 시간:")
        print(f"  • 정규장: 09:00 ~ 15:30")
        print(f"  • 시간외: 08:00~09:00, 15:40~18:00")
        print(f"\n💡 도움말:")
        print(f"  • 대시보드: http://localhost:5000")
        print(f"  • 로그 확인: logs/bot.log")
        print("=" * 70 + "\n")

    def _get_error_info(self, error_code: str, error_msg: str) -> Dict[str, Any]:
        """에러 정보 조회"""
        # 에러 코드로 먼저 검색
        if error_code in ERROR_MESSAGES:
            return ERROR_MESSAGES[error_code]

        # 에러 메시지 키워드로 검색
        for key, info in ERROR_MESSAGES.items():
            if key in str(error_msg):
                return info

        # 기본 메시지
        return {
            "message": error_msg or "알 수 없는 오류가 발생했습니다",
            "actions": [
                "프로그램을 재시작해 보세요",
                "문제가 지속되면 로그를 확인하세요",
                "logs/bot.log 파일 참조"
            ]
        }

    def _send_notification(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        category: AlertCategory,
        channels: List[str] = None
    ):
        """알림 발송"""
        if self.notification_manager:
            try:
                self.notification_manager.send(
                    title=title,
                    message=message,
                    priority=level.value,
                    category=category.value,
                    channels=channels
                )
            except Exception as e:
                logger.warning(f"알림 발송 실패: {e}")


# 싱글톤 인스턴스
_user_feedback_instance = None


def get_user_feedback(notification_manager=None) -> UserFeedback:
    """UserFeedback 싱글톤 인스턴스 반환"""
    global _user_feedback_instance
    if _user_feedback_instance is None:
        _user_feedback_instance = UserFeedback(notification_manager)
    elif notification_manager and _user_feedback_instance.notification_manager is None:
        _user_feedback_instance.notification_manager = notification_manager
    return _user_feedback_instance
