"""
strategy/dynamic_risk_manager.py
동적 리스크 관리 모드 시스템
성과에 따라 자동으로 모드 전환
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from utils.logger_new import get_logger

from config.manager import get_config


logger = get_logger()


class RiskMode(Enum):
    """리스크 모드 열거형"""

    AGGRESSIVE = "aggressive"
    NORMAL = "normal"
    CONSERVATIVE = "conservative"
    VERY_CONSERVATIVE = "very_conservative"


@dataclass
class RiskModeConfig:
    """리스크 모드 설정"""

    mode: RiskMode
    max_open_positions: int
    risk_per_trade_ratio: float
    take_profit_ratio: float
    stop_loss_ratio: float
    ai_min_score: float

    trigger_return_min: Optional[float] = None
    trigger_return_max: Optional[float] = None


class DynamicRiskManager:
    """동적 리스크 관리자"""

    def __init__(self, initial_capital: float):
        """
        초기화

        Args:
            initial_capital: 초기 자본금
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # 설정 로드
        self.config = get_config()
        self.risk_config = self.config.risk_management

        # 현재 모드
        self.current_mode = RiskMode.NORMAL
        self.mode_changed_at = datetime.now()

        # 모드별 설정 로드
        self._load_mode_configs()

        logger.info(
            f"🛡️ 동적 리스크 관리자 초기화 완료 "
            f"(초기자본: {self.initial_capital:,}원, 모드: {self.current_mode.value})"
        )

    def _load_mode_configs(self):
        """모드별 설정 로드"""
        self.mode_configs = {}

        # Pydantic 모델과 dictionary 모두 지원하는 헬퍼 함수
        def get_risk_value(mode_name, key, default):
            try:
                if isinstance(self.risk_config, dict):
                    mode_config = self.risk_config.get(mode_name, {})
                    return mode_config.get(key, default) if isinstance(mode_config, dict) else getattr(mode_config, key, default)
                else:
                    mode_config = getattr(self.risk_config, mode_name, None)
                    if mode_config is None:
                        return default
                    return getattr(mode_config, key, default)
            except:
                return default

        # Aggressive 모드
        self.mode_configs[RiskMode.AGGRESSIVE] = RiskModeConfig(
            mode=RiskMode.AGGRESSIVE,
            max_open_positions=get_risk_value('aggressive', 'max_open_positions', 12),
            risk_per_trade_ratio=get_risk_value('aggressive', 'risk_per_trade_ratio', 0.25),
            take_profit_ratio=get_risk_value('aggressive', 'take_profit_ratio', 0.15),
            stop_loss_ratio=get_risk_value('aggressive', 'stop_loss_ratio', -0.07),
            ai_min_score=get_risk_value('aggressive', 'ai_min_score', 6.5),
            trigger_return_min=get_risk_value('aggressive', 'trigger_return', 0.05),
        )

        # Normal 모드
        self.mode_configs[RiskMode.NORMAL] = RiskModeConfig(
            mode=RiskMode.NORMAL,
            max_open_positions=get_risk_value('normal', 'max_open_positions', 10),
            risk_per_trade_ratio=get_risk_value('normal', 'risk_per_trade_ratio', 0.20),
            take_profit_ratio=get_risk_value('normal', 'take_profit_ratio', 0.10),
            stop_loss_ratio=get_risk_value('normal', 'stop_loss_ratio', -0.05),
            ai_min_score=get_risk_value('normal', 'ai_min_score', 7.0),
            trigger_return_min=get_risk_value('normal', 'trigger_return_min', -0.05),
            trigger_return_max=get_risk_value('normal', 'trigger_return_max', 0.05),
        )

        # Conservative 모드
        self.mode_configs[RiskMode.CONSERVATIVE] = RiskModeConfig(
            mode=RiskMode.CONSERVATIVE,
            max_open_positions=get_risk_value('conservative', 'max_open_positions', 7),
            risk_per_trade_ratio=get_risk_value('conservative', 'risk_per_trade_ratio', 0.15),
            take_profit_ratio=get_risk_value('conservative', 'take_profit_ratio', 0.08),
            stop_loss_ratio=get_risk_value('conservative', 'stop_loss_ratio', -0.04),
            ai_min_score=get_risk_value('conservative', 'ai_min_score', 7.5),
            trigger_return_min=get_risk_value('conservative', 'trigger_return_min', -0.10),
            trigger_return_max=get_risk_value('conservative', 'trigger_return_max', -0.05),
        )

        # Very Conservative 모드
        self.mode_configs[RiskMode.VERY_CONSERVATIVE] = RiskModeConfig(
            mode=RiskMode.VERY_CONSERVATIVE,
            max_open_positions=get_risk_value('very_conservative', 'max_open_positions', 5),
            risk_per_trade_ratio=get_risk_value('very_conservative', 'risk_per_trade_ratio', 0.10),
            take_profit_ratio=get_risk_value('very_conservative', 'take_profit_ratio', 0.05),
            stop_loss_ratio=get_risk_value('very_conservative', 'stop_loss_ratio', -0.03),
            ai_min_score=get_risk_value('very_conservative', 'ai_min_score', 8.0),
            trigger_return_max=get_risk_value('very_conservative', 'trigger_return', -0.10),
        )

    def update_capital(self, current_capital: float):
        """
        현재 자본금 업데이트 및 모드 재평가

        Args:
            current_capital: 현재 자본금
        """
        previous_capital = self.current_capital
        self.current_capital = current_capital

        # 수익률 계산
        return_rate = self.get_return_rate()

        logger.info(
            f"💰 자본금 업데이트: {previous_capital:,}원 → {current_capital:,}원 "
            f"(수익률: {return_rate*100:+.2f}%)"
        )

        # 모드 재평가
        self._evaluate_mode()

    def get_return_rate(self) -> float:
        """현재 수익률 계산"""
        if self.initial_capital == 0:
            return 0.0
        return (self.current_capital - self.initial_capital) / self.initial_capital

    def _evaluate_mode(self):
        """모드 재평가 및 전환"""
        return_rate = self.get_return_rate()
        new_mode = self._determine_mode(return_rate)

        if new_mode != self.current_mode:
            self._switch_mode(new_mode, return_rate)

    def _determine_mode(self, return_rate: float) -> RiskMode:
        """
        수익률에 따른 모드 결정

        Args:
            return_rate: 수익률

        Returns:
            RiskMode
        """
        # Aggressive: 수익률 +5% 이상
        if return_rate >= 0.05:
            return RiskMode.AGGRESSIVE

        # Very Conservative: 수익률 -10% 이하
        if return_rate <= -0.10:
            return RiskMode.VERY_CONSERVATIVE

        # Conservative: 수익률 -10% ~ -5%
        if -0.10 < return_rate <= -0.05:
            return RiskMode.CONSERVATIVE

        # Normal: 수익률 -5% ~ +5%
        return RiskMode.NORMAL

    def _switch_mode(self, new_mode: RiskMode, return_rate: float):
        """
        모드 전환

        Args:
            new_mode: 새로운 모드
            return_rate: 현재 수익률
        """
        old_mode = self.current_mode
        self.current_mode = new_mode
        self.mode_changed_at = datetime.now()

        logger.warning(
            f"🔄 리스크 모드 전환: {old_mode.value} → {new_mode.value} "
            f"(수익률: {return_rate*100:+.2f}%)"
        )

        # 모드별 설정 출력
        config = self.get_current_mode_config()
        logger.info(
            f"📋 새로운 리스크 설정:\n"
            f"  - 최대 포지션: {config.max_open_positions}개\n"
            f"  - 거래당 리스크: {config.risk_per_trade_ratio*100:.1f}%\n"
            f"  - 목표 수익률: {config.take_profit_ratio*100:.1f}%\n"
            f"  - 손절 비율: {config.stop_loss_ratio*100:.1f}%\n"
            f"  - AI 최소 점수: {config.ai_min_score:.1f}"
        )

    def get_current_mode_config(self) -> RiskModeConfig:
        """현재 모드 설정 반환"""
        return self.mode_configs[self.current_mode]

    def should_open_position(self, current_positions: int) -> bool:
        """
        포지션 진입 여부 판단

        Args:
            current_positions: 현재 보유 포지션 수

        Returns:
            진입 가능 여부
        """
        config = self.get_current_mode_config()
        return current_positions < config.max_open_positions

    def calculate_position_size(
        self,
        stock_price: int,
        available_cash: int
    ) -> int:
        """
        포지션 크기 계산

        Args:
            stock_price: 주가
            available_cash: 사용 가능 현금

        Returns:
            매수 수량
        """
        config = self.get_current_mode_config()

        # 거래당 리스크 금액
        risk_amount = self.current_capital * config.risk_per_trade_ratio

        # 사용 가능 금액과 리스크 금액 중 작은 값 사용
        position_value = min(risk_amount, available_cash)

        # 수량 계산
        quantity = int(position_value / stock_price)

        return quantity

    def get_exit_thresholds(self, entry_price: int) -> Dict[str, int]:
        """
        청산 임계값 계산

        Args:
            entry_price: 진입 가격

        Returns:
            {'take_profit': int, 'stop_loss': int}
        """
        config = self.get_current_mode_config()

        take_profit = int(entry_price * (1 + config.take_profit_ratio))
        stop_loss = int(entry_price * (1 + config.stop_loss_ratio))

        return {
            'take_profit': take_profit,
            'stop_loss': stop_loss,
        }

    def should_approve_ai_signal(self, ai_score: float, ai_confidence: str) -> bool:
        """
        AI 시그널 승인 여부

        Args:
            ai_score: AI 점수
            ai_confidence: AI 신뢰도

        Returns:
            승인 여부
        """
        config = self.get_current_mode_config()

        # 점수 체크
        if ai_score < config.ai_min_score:
            return False

        # 신뢰도 체크 (보수적 모드일수록 높은 신뢰도 요구)
        confidence_requirements = {
            RiskMode.AGGRESSIVE: 'Low',
            RiskMode.NORMAL: 'Medium',
            RiskMode.CONSERVATIVE: 'Medium',
            RiskMode.VERY_CONSERVATIVE: 'High',
        }

        required_confidence = confidence_requirements[self.current_mode]
        confidence_levels = {'Low': 1, 'Medium': 2, 'High': 3}

        return confidence_levels.get(ai_confidence, 0) >= confidence_levels.get(required_confidence, 2)

    def get_status_summary(self) -> Dict[str, Any]:
        """상태 요약"""
        config = self.get_current_mode_config()
        return_rate = self.get_return_rate()

        return {
            'mode': self.current_mode.value,
            'mode_changed_at': self.mode_changed_at.isoformat(),
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'return_rate': return_rate,
            'return_percentage': return_rate * 100,
            'profit_loss': self.current_capital - self.initial_capital,
            'config': {
                'max_open_positions': config.max_open_positions,
                'risk_per_trade_ratio': config.risk_per_trade_ratio,
                'take_profit_ratio': config.take_profit_ratio,
                'stop_loss_ratio': config.stop_loss_ratio,
                'ai_min_score': config.ai_min_score,
            },
        }

    def get_mode_description(self) -> str:
        """현재 모드 설명"""
        descriptions = {
            RiskMode.AGGRESSIVE: "🔥 공격적 모드 - 수익 확대 전략",
            RiskMode.NORMAL: "⚖️ 일반 모드 - 균형 잡힌 전략",
            RiskMode.CONSERVATIVE: "🛡️ 보수적 모드 - 손실 최소화 전략",
            RiskMode.VERY_CONSERVATIVE: "🔒 매우 보수적 모드 - 자본 보호 우선",
        }
        return descriptions.get(self.current_mode, "알 수 없는 모드")


__all__ = ['DynamicRiskManager', 'RiskMode', 'RiskModeConfig']
