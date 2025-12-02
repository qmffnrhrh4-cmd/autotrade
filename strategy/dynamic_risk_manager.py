"""
strategy/dynamic_risk_manager.py
통합 동적 리스크 관리 시스템
성과에 따라 자동으로 모드 전환 + 정적 리스크 체크 통합
Q10. 적응형 전략 선택: 시장 상황에 따른 자동 모드 전환
"""
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from utils.logger_new import get_logger
from utils.base_manager import BaseManager
from config.manager import get_config


logger = get_logger()


# Q10. 시장 상황 열거형
class MarketCondition(Enum):
    """시장 상황"""
    STRONG_BULL = "strong_bull"    # 강세장 (KOSPI/KOSDAQ 2% 이상 상승)
    BULL = "bull"                  # 상승장 (1~2% 상승)
    NEUTRAL = "neutral"            # 보합세 (-0.5% ~ 0.5%)
    BEAR = "bear"                  # 하락장 (-2% ~ -0.5%)
    STRONG_BEAR = "strong_bear"    # 강세 하락 (-2% 이하)
    HIGH_VOLATILITY = "high_volatility"  # 변동성 장세


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


class DynamicRiskManager(BaseManager):
    """
    통합 동적 리스크 관리자

    Features:
    - 수익률 기반 동적 모드 전환 (Aggressive/Normal/Conservative/Very Conservative)
    - 포지션 크기 검증 및 계산
    - 손실 제한 관리 (일일/총 손실)
    - 손절/익절 임계값 관리
    - AI 시그널 승인
    - 리스크 레벨 평가
    - 거래 이력 추적
    """

    def __init__(self, initial_capital: float):
        """
        초기화

        Args:
            initial_capital: 초기 자본금
        """
        super().__init__(name="DynamicRiskManager")
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # 설정 로드
        self.config = get_config()
        self.risk_config = self.config.risk_management

        # 현재 모드
        self.current_mode = RiskMode.NORMAL
        self.mode_changed_at = datetime.now()

        # 손익 추적
        self.daily_profit_loss = 0.0
        self.total_profit_loss = 0.0
        self.consecutive_losses = 0
        self.daily_reset_time = datetime.now().date()

        # 거래 제어
        self.trading_enabled = True
        self.emergency_stop = False

        # 거래 이력
        self.trade_history: List[Dict[str, Any]] = []

        # Q10. 시장 상황 추적
        self.current_market_condition = MarketCondition.NEUTRAL
        self.market_condition_updated_at = datetime.now()
        self.market_api = None  # 시장 API (외부 주입)
        self.adaptive_mode_enabled = True  # Q10. 적응형 모드 활성화

        # 모드별 설정 로드
        self._load_mode_configs()
        self.initialized = True

        self.logger.info(
            f"🛡️ 통합 동적 리스크 관리자 초기화 완료 "
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

    def set_market_api(self, market_api):
        """Q10. 시장 API 설정 (외부 주입)"""
        self.market_api = market_api
        self.logger.info("📊 시장 API 연결됨 - 적응형 전략 선택 활성화")

    def _detect_market_condition(self) -> MarketCondition:
        """Q10. 시장 상황 감지"""
        if not self.market_api:
            return MarketCondition.NEUTRAL

        try:
            # KOSPI/KOSDAQ 지수 데이터 조회
            kospi_data = self.market_api.get_index_data('001')
            kosdaq_data = self.market_api.get_index_data('101')

            if not kospi_data or not kosdaq_data:
                return self.current_market_condition

            kospi_change = float(kospi_data.get('change_rate', 0))
            kosdaq_change = float(kosdaq_data.get('change_rate', 0))
            avg_change = (kospi_change + kosdaq_change) / 2

            # 변동성 체크 (KOSPI와 KOSDAQ 방향이 다르면 변동성 장세)
            if (kospi_change > 0.5 and kosdaq_change < -0.5) or (kospi_change < -0.5 and kosdaq_change > 0.5):
                return MarketCondition.HIGH_VOLATILITY

            # 시장 상황 판단
            if avg_change >= 2.0:
                return MarketCondition.STRONG_BULL
            elif avg_change >= 1.0:
                return MarketCondition.BULL
            elif avg_change > -0.5:
                return MarketCondition.NEUTRAL
            elif avg_change >= -2.0:
                return MarketCondition.BEAR
            else:
                return MarketCondition.STRONG_BEAR

        except Exception as e:
            self.logger.warning(f"시장 상황 감지 실패: {e}")
            return self.current_market_condition

    def _get_mode_for_market_condition(self, market_condition: MarketCondition) -> RiskMode:
        """Q10. 시장 상황에 따른 최적 모드 결정"""
        market_mode_map = {
            MarketCondition.STRONG_BULL: RiskMode.AGGRESSIVE,
            MarketCondition.BULL: RiskMode.NORMAL,
            MarketCondition.NEUTRAL: RiskMode.NORMAL,
            MarketCondition.BEAR: RiskMode.CONSERVATIVE,
            MarketCondition.STRONG_BEAR: RiskMode.VERY_CONSERVATIVE,
            MarketCondition.HIGH_VOLATILITY: RiskMode.CONSERVATIVE,  # 변동성 장세는 보수적으로
        }
        return market_mode_map.get(market_condition, RiskMode.NORMAL)

    def update_market_condition(self) -> MarketCondition:
        """Q10. 시장 상황 업데이트 및 모드 자동 전환"""
        if not self.adaptive_mode_enabled:
            return self.current_market_condition

        # 1분에 한 번만 업데이트
        if (datetime.now() - self.market_condition_updated_at).total_seconds() < 60:
            return self.current_market_condition

        new_condition = self._detect_market_condition()

        if new_condition != self.current_market_condition:
            self.logger.info(
                f"📊 시장 상황 변화: {self.current_market_condition.value} → {new_condition.value}"
            )
            self.current_market_condition = new_condition
            self.market_condition_updated_at = datetime.now()

            # 시장 상황에 따른 모드 자동 전환
            market_suggested_mode = self._get_mode_for_market_condition(new_condition)

            # 수익률 기반 모드와 시장 기반 모드 중 더 보수적인 것 선택
            return_rate = self.get_return_rate()
            return_based_mode = self._determine_mode(return_rate)

            # 모드 우선순위: VERY_CONSERVATIVE > CONSERVATIVE > NORMAL > AGGRESSIVE
            mode_priority = {
                RiskMode.VERY_CONSERVATIVE: 4,
                RiskMode.CONSERVATIVE: 3,
                RiskMode.NORMAL: 2,
                RiskMode.AGGRESSIVE: 1,
            }

            # 더 보수적인 모드 선택
            if mode_priority[market_suggested_mode] > mode_priority[return_based_mode]:
                final_mode = market_suggested_mode
                self.logger.info(f"🎯 시장 상황 기반 모드 적용: {final_mode.value}")
            else:
                final_mode = return_based_mode
                self.logger.info(f"🎯 수익률 기반 모드 유지: {final_mode.value}")

            if final_mode != self.current_mode:
                self._switch_mode(final_mode, return_rate)

        return self.current_market_condition

    def _evaluate_mode(self):
        """모드 재평가 및 전환"""
        # Q10. 시장 상황도 함께 고려
        self.update_market_condition()

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

    def validate_position_size(
        self,
        position_value: float,
        total_assets: float
    ) -> Tuple[bool, str]:
        """
        포지션 크기 검증

        Args:
            position_value: 포지션 가치
            total_assets: 총 자산

        Returns:
            (검증 통과 여부, 메시지)
        """
        if total_assets == 0:
            return False, "총 자산이 0입니다"

        config = self.get_current_mode_config()
        max_position_ratio = config.risk_per_trade_ratio
        position_ratio = position_value / total_assets

        if position_ratio > max_position_ratio:
            return False, f"포지션 크기 초과 ({position_ratio*100:.1f}% > {max_position_ratio*100:.1f}%)"

        return True, "포지션 크기 적정"

    def check_stop_loss(
        self,
        purchase_price: float,
        current_price: float
    ) -> Tuple[bool, str]:
        """
        손절 여부 확인

        Args:
            purchase_price: 매수가
            current_price: 현재가

        Returns:
            (손절 여부, 메시지)
        """
        if purchase_price == 0:
            return False, "매수가 정보 없음"

        config = self.get_current_mode_config()
        loss_rate = (current_price - purchase_price) / purchase_price

        if loss_rate <= config.stop_loss_ratio:
            return True, f"손절 조건 충족 ({loss_rate*100:.2f}% 손실)"

        return False, "손절 조건 미충족"

    def check_daily_loss_limit(self) -> Tuple[bool, str]:
        """
        일일 손실 한도 확인

        Returns:
            (거래 가능 여부, 메시지)
        """
        self._check_daily_reset()

        max_daily_loss_pct = 0.03
        max_daily_loss = self.current_capital * max_daily_loss_pct

        if abs(self.daily_profit_loss) >= max_daily_loss:
            return False, f"일일 손실 한도 도달 ({self.daily_profit_loss:+,.0f}원)"

        return True, "일일 손실 한도 내"

    def check_total_loss_limit(self) -> Tuple[bool, str]:
        """
        총 손실 한도 확인

        Returns:
            (거래 가능 여부, 메시지)
        """
        max_total_loss_pct = 0.10
        total_loss_rate = self.total_profit_loss / self.initial_capital

        if total_loss_rate <= -max_total_loss_pct:
            self.emergency_stop = True
            return False, f"총 손실 한도 초과 ({total_loss_rate*100:.2f}%) - 긴급 정지"

        return True, "총 손실 한도 내"

    def update_profit_loss(
        self,
        profit_loss: float,
        is_win: bool
    ):
        """
        손익 업데이트

        Args:
            profit_loss: 손익 금액
            is_win: 수익 여부
        """
        self.daily_profit_loss += profit_loss
        self.total_profit_loss += profit_loss

        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

            max_consecutive_losses = 3
            if self.consecutive_losses >= max_consecutive_losses:
                logger.warning(f"⚠️  연속 손실 {self.consecutive_losses}회 발생 - 거래 일시 정지 권고")

        logger.info(
            f"손익 업데이트: {profit_loss:+,.0f}원 "
            f"(일일: {self.daily_profit_loss:+,.0f}원, 총: {self.total_profit_loss:+,.0f}원)"
        )

    def _check_daily_reset(self):
        """일일 리셋 확인"""
        today = datetime.now().date()

        if today > self.daily_reset_time:
            logger.info(f"일일 손익 리셋 (이전: {self.daily_profit_loss:+,.0f}원)")
            self.daily_profit_loss = 0.0
            self.daily_reset_time = today

    def can_trade(self, reason: str = "") -> Tuple[bool, str]:
        """
        거래 가능 여부 확인

        Args:
            reason: 확인 사유

        Returns:
            (거래 가능 여부, 메시지)
        """
        if self.emergency_stop:
            return False, "긴급 정지 상태"

        if not self.trading_enabled:
            return False, "거래 비활성화됨"

        can_trade_daily, msg_daily = self.check_daily_loss_limit()
        if not can_trade_daily:
            return False, msg_daily

        max_consecutive_losses = 3
        if self.consecutive_losses >= max_consecutive_losses:
            return False, f"연속 손실 {self.consecutive_losses}회 도달"

        return True, "거래 가능"

    def record_trade(
        self,
        stock_code: str,
        action: str,
        quantity: int,
        price: float,
        profit_loss: float = 0.0
    ):
        """
        거래 기록

        Args:
            stock_code: 종목코드
            action: 'buy' | 'sell'
            quantity: 수량
            price: 가격
            profit_loss: 손익 (매도 시)
        """
        trade = {
            'timestamp': datetime.now().isoformat(),
            'stock_code': stock_code,
            'action': action,
            'quantity': quantity,
            'price': price,
            'profit_loss': profit_loss,
        }

        self.trade_history.append(trade)

        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]

    def assess_risk_level(
        self,
        portfolio_value: float,
        total_assets: float,
        position_count: int
    ) -> Dict[str, Any]:
        """
        리스크 수준 평가

        Args:
            portfolio_value: 포트폴리오 가치
            total_assets: 총 자산
            position_count: 포지션 수

        Returns:
            리스크 평가 결과
        """
        risk_score = 0
        risk_factors = []

        config = self.get_current_mode_config()

        if total_assets > 0:
            concentration = portfolio_value / total_assets
            if concentration > 0.8:
                risk_score += 3
                risk_factors.append("높은 주식 집중도")
            elif concentration > 0.6:
                risk_score += 2
                risk_factors.append("중간 주식 집중도")
            elif concentration > 0.4:
                risk_score += 1

        max_daily_loss = self.current_capital * 0.03
        if abs(self.daily_profit_loss) > max_daily_loss * 0.8:
            risk_score += 3
            risk_factors.append("높은 일일 손실")
        elif abs(self.daily_profit_loss) > max_daily_loss * 0.5:
            risk_score += 2
            risk_factors.append("중간 일일 손실")

        if self.consecutive_losses >= 2:
            risk_score += 2
            risk_factors.append(f"연속 손실 {self.consecutive_losses}회")
        elif self.consecutive_losses >= 1:
            risk_score += 1

        if position_count >= config.max_open_positions:
            risk_score += 2
            risk_factors.append("최대 포지션 수 도달")
        elif position_count >= config.max_open_positions * 0.8:
            risk_score += 1
            risk_factors.append("높은 포지션 수")

        if risk_score >= 7:
            risk_level = "Critical"
            recommendation = "즉시 포지션 축소 및 손실 제한 필요"
        elif risk_score >= 5:
            risk_level = "High"
            recommendation = "포지션 축소 및 신규 매수 자제"
        elif risk_score >= 3:
            risk_level = "Medium"
            recommendation = "주의 깊은 모니터링 필요"
        else:
            risk_level = "Low"
            recommendation = "정상 운영 가능"

        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'recommendation': recommendation,
            'can_trade': risk_score < 7,
            'daily_profit_loss': self.daily_profit_loss,
            'total_profit_loss': self.total_profit_loss,
            'consecutive_losses': self.consecutive_losses,
        }

    def enable_trading(self):
        """거래 활성화"""
        self.trading_enabled = True
        logger.info("거래 활성화")

    def disable_trading(self, reason: str = ""):
        """거래 비활성화"""
        self.trading_enabled = False
        logger.warning(f"거래 비활성화: {reason}")

    def reset_emergency_stop(self):
        """긴급 정지 해제"""
        self.emergency_stop = False
        logger.warning("긴급 정지 해제됨")

    def initialize(self) -> bool:
        """초기화"""
        self.initialized = True
        self.logger.info("동적 리스크 관리자 초기화 완료")
        return True

    def get_status(self) -> Dict[str, Any]:
        """상태 정보"""
        config = self.get_current_mode_config()
        return_rate = self.get_return_rate()

        return {
            **super().get_stats(),
            'mode': self.current_mode.value,
            'mode_changed_at': self.mode_changed_at.isoformat(),
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'return_rate': return_rate,
            'return_percentage': return_rate * 100,
            'profit_loss': self.current_capital - self.initial_capital,
            'daily_profit_loss': self.daily_profit_loss,
            'total_profit_loss': self.total_profit_loss,
            'consecutive_losses': self.consecutive_losses,
            'trading_enabled': self.trading_enabled,
            'emergency_stop': self.emergency_stop,
            'config': {
                'max_open_positions': config.max_open_positions,
                'risk_per_trade_ratio': config.risk_per_trade_ratio,
                'take_profit_ratio': config.take_profit_ratio,
                'stop_loss_ratio': config.stop_loss_ratio,
                'ai_min_score': config.ai_min_score,
            },
        }


__all__ = ['DynamicRiskManager', 'RiskMode', 'RiskModeConfig', 'MarketCondition']
