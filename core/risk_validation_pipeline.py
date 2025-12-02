"""
core/risk_validation_pipeline.py
통합 리스크 검증 파이프라인

모든 주문이 실행되기 전에 반드시 거쳐야 하는 4단계 리스크 검증
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """리스크 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    BLOCKED = "blocked"


class ValidationResult(Enum):
    """검증 결과"""
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_APPROVAL = "requires_approval"
    REDUCED = "reduced"  # 수량 축소 승인


@dataclass
class RiskCheckResult:
    """리스크 체크 결과"""
    check_name: str
    passed: bool
    risk_level: RiskLevel
    message: str
    recommended_action: str = ""
    adjusted_quantity: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """검증 보고서"""
    order_id: str
    timestamp: str
    stock_code: str
    stock_name: str
    order_type: str  # buy/sell
    requested_quantity: int
    requested_price: float
    final_result: ValidationResult
    final_quantity: int
    checks: List[RiskCheckResult]
    overall_risk_level: RiskLevel
    rejection_reasons: List[str]
    warnings: List[str]


class RiskValidationPipeline:
    """
    4단계 리스크 검증 파이프라인

    Stage 1: 포지션 리스크 (단일 종목 집중도)
    Stage 2: 포트폴리오 리스크 (전체 노출도)
    Stage 3: 시장 리스크 (변동성, 유동성)
    Stage 4: 계정 리스크 (잔고, 일일 손실)
    """

    _instance = None
    _lock = Lock()

    # 기본 리스크 한도
    DEFAULT_LIMITS = {
        # 포지션 한도
        'max_position_pct': 0.15,           # 단일 종목 최대 15%
        'max_sector_pct': 0.40,             # 단일 섹터 최대 40%
        'min_position_value': 100000,       # 최소 포지션 10만원
        'max_position_value': 50000000,     # 최대 포지션 5천만원

        # 일일 한도
        'max_daily_loss_pct': 0.03,         # 일일 최대 손실 3%
        'max_daily_loss_amount': 1000000,   # 일일 최대 손실 100만원
        'max_daily_trades': 50,             # 일일 최대 거래 50회
        'max_daily_buy_amount': 100000000,  # 일일 최대 매수 1억원

        # 변동성 한도
        'max_volatility': 0.10,             # 최대 일일 변동성 10%
        'min_volume': 100000,               # 최소 거래량 10만주
        'min_trading_value': 1000000000,    # 최소 거래대금 10억원

        # 가격 한도
        'max_price_deviation': 0.05,        # 현재가 대비 최대 5% 이탈
        'max_spread_pct': 0.02,             # 최대 스프레드 2%
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
        self.limits = self.DEFAULT_LIMITS.copy()

        # 일일 추적
        self.daily_stats = {
            'date': datetime.now().date(),
            'total_loss': 0.0,
            'total_profit': 0.0,
            'trade_count': 0,
            'buy_amount': 0.0,
            'sell_amount': 0.0,
            'rejected_orders': 0
        }

        # 검증 히스토리
        self.validation_history: List[ValidationReport] = []

        # 긴급 정지 상태
        self.emergency_stop = False
        self.emergency_reason = ""

        logger.info("리스크 검증 파이프라인 초기화 완료")

    @classmethod
    def get_instance(cls) -> 'RiskValidationPipeline':
        return cls()

    def _reset_daily_stats_if_needed(self):
        """일일 통계 초기화 (날짜 변경 시)"""
        today = datetime.now().date()
        if self.daily_stats['date'] != today:
            self.daily_stats = {
                'date': today,
                'total_loss': 0.0,
                'total_profit': 0.0,
                'trade_count': 0,
                'buy_amount': 0.0,
                'sell_amount': 0.0,
                'rejected_orders': 0
            }
            logger.info(f"일일 통계 초기화: {today}")

    def validate_order(
        self,
        stock_code: str,
        stock_name: str,
        order_type: str,  # 'buy' or 'sell'
        quantity: int,
        price: float,
        portfolio_value: float,
        current_positions: List[Dict[str, Any]],
        market_data: Optional[Dict[str, Any]] = None
    ) -> ValidationReport:
        """
        주문 검증 메인 함수

        모든 주문은 이 함수를 거쳐야 함
        """
        self._reset_daily_stats_if_needed()

        order_id = f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        checks: List[RiskCheckResult] = []
        warnings: List[str] = []
        rejection_reasons: List[str] = []

        requested_quantity = quantity
        final_quantity = quantity

        # 긴급 정지 체크
        if self.emergency_stop:
            return ValidationReport(
                order_id=order_id,
                timestamp=datetime.now().isoformat(),
                stock_code=stock_code,
                stock_name=stock_name,
                order_type=order_type,
                requested_quantity=requested_quantity,
                requested_price=price,
                final_result=ValidationResult.REJECTED,
                final_quantity=0,
                checks=[RiskCheckResult(
                    check_name="emergency_stop",
                    passed=False,
                    risk_level=RiskLevel.BLOCKED,
                    message=f"긴급 정지 활성화: {self.emergency_reason}"
                )],
                overall_risk_level=RiskLevel.BLOCKED,
                rejection_reasons=[self.emergency_reason],
                warnings=[]
            )

        # Stage 1: 포지션 리스크
        stage1_result = self._check_position_risk(
            stock_code, order_type, quantity, price, portfolio_value, current_positions
        )
        checks.append(stage1_result)
        if not stage1_result.passed:
            rejection_reasons.append(stage1_result.message)
        elif stage1_result.adjusted_quantity:
            final_quantity = min(final_quantity, stage1_result.adjusted_quantity)
            warnings.append(f"포지션 한도로 수량 조정: {quantity} → {final_quantity}")

        # Stage 2: 포트폴리오 리스크
        stage2_result = self._check_portfolio_risk(
            stock_code, order_type, final_quantity, price, portfolio_value, current_positions
        )
        checks.append(stage2_result)
        if not stage2_result.passed:
            rejection_reasons.append(stage2_result.message)
        elif stage2_result.adjusted_quantity:
            final_quantity = min(final_quantity, stage2_result.adjusted_quantity)
            warnings.append(f"포트폴리오 한도로 수량 조정: {quantity} → {final_quantity}")

        # Stage 3: 시장 리스크
        stage3_result = self._check_market_risk(
            stock_code, order_type, final_quantity, price, market_data
        )
        checks.append(stage3_result)
        if not stage3_result.passed:
            rejection_reasons.append(stage3_result.message)

        # Stage 4: 계정 리스크
        stage4_result = self._check_account_risk(
            order_type, final_quantity, price, portfolio_value
        )
        checks.append(stage4_result)
        if not stage4_result.passed:
            rejection_reasons.append(stage4_result.message)
        elif stage4_result.adjusted_quantity:
            final_quantity = min(final_quantity, stage4_result.adjusted_quantity)
            warnings.append(f"일일 한도로 수량 조정: {quantity} → {final_quantity}")

        # 최종 결과 결정
        if rejection_reasons:
            final_result = ValidationResult.REJECTED
            final_quantity = 0
        elif final_quantity < requested_quantity:
            final_result = ValidationResult.REDUCED
        else:
            final_result = ValidationResult.APPROVED

        # 전체 리스크 수준 계산
        risk_levels = [c.risk_level for c in checks]
        if RiskLevel.BLOCKED in risk_levels:
            overall_risk = RiskLevel.BLOCKED
        elif RiskLevel.CRITICAL in risk_levels:
            overall_risk = RiskLevel.CRITICAL
        elif RiskLevel.HIGH in risk_levels:
            overall_risk = RiskLevel.HIGH
        elif RiskLevel.MEDIUM in risk_levels:
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW

        report = ValidationReport(
            order_id=order_id,
            timestamp=datetime.now().isoformat(),
            stock_code=stock_code,
            stock_name=stock_name,
            order_type=order_type,
            requested_quantity=requested_quantity,
            requested_price=price,
            final_result=final_result,
            final_quantity=final_quantity,
            checks=checks,
            overall_risk_level=overall_risk,
            rejection_reasons=rejection_reasons,
            warnings=warnings
        )

        # 히스토리 저장
        self.validation_history.append(report)
        if len(self.validation_history) > 1000:
            self.validation_history = self.validation_history[-500:]

        # 로그
        result_emoji = "✅" if final_result == ValidationResult.APPROVED else "⚠️" if final_result == ValidationResult.REDUCED else "❌"
        logger.info(f"{result_emoji} 리스크 검증 완료: {stock_name} {order_type} {requested_quantity}주 → {final_quantity}주 ({final_result.value})")

        if rejection_reasons:
            for reason in rejection_reasons:
                logger.warning(f"  거부 사유: {reason}")
        if warnings:
            for warning in warnings:
                logger.info(f"  경고: {warning}")

        # 통계 업데이트
        if final_result == ValidationResult.REJECTED:
            self.daily_stats['rejected_orders'] += 1

        return report

    def _check_position_risk(
        self,
        stock_code: str,
        order_type: str,
        quantity: int,
        price: float,
        portfolio_value: float,
        current_positions: List[Dict[str, Any]]
    ) -> RiskCheckResult:
        """Stage 1: 포지션 리스크 체크"""
        order_value = quantity * price

        # 현재 해당 종목 보유량
        current_holding = 0
        current_value = 0
        for pos in current_positions:
            if pos.get('stock_code') == stock_code:
                current_holding = pos.get('quantity', 0)
                current_value = pos.get('total_value', 0)
                break

        # 매수 후 예상 포지션
        if order_type == 'buy':
            new_value = current_value + order_value
        else:
            new_value = max(0, current_value - order_value)

        # 포지션 비중 체크
        position_pct = new_value / portfolio_value if portfolio_value > 0 else 0
        max_pct = self.limits['max_position_pct']

        if position_pct > max_pct:
            # 허용 가능한 최대 수량 계산
            max_value = portfolio_value * max_pct
            allowed_value = max(0, max_value - current_value)
            allowed_quantity = int(allowed_value / price) if price > 0 else 0

            if allowed_quantity <= 0:
                return RiskCheckResult(
                    check_name="position_concentration",
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    message=f"포지션 집중도 초과: {position_pct*100:.1f}% > {max_pct*100:.1f}%",
                    recommended_action="매수 불가 - 기존 포지션이 한도에 도달"
                )
            else:
                return RiskCheckResult(
                    check_name="position_concentration",
                    passed=True,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"포지션 집중도 조정 필요: {position_pct*100:.1f}% > {max_pct*100:.1f}%",
                    adjusted_quantity=allowed_quantity,
                    recommended_action=f"수량 {quantity} → {allowed_quantity}로 축소"
                )

        # 최소/최대 포지션 가치 체크
        if order_type == 'buy':
            if order_value < self.limits['min_position_value']:
                return RiskCheckResult(
                    check_name="position_size",
                    passed=False,
                    risk_level=RiskLevel.LOW,
                    message=f"최소 포지션 미달: {order_value:,}원 < {self.limits['min_position_value']:,}원"
                )

            if order_value > self.limits['max_position_value']:
                allowed_quantity = int(self.limits['max_position_value'] / price)
                return RiskCheckResult(
                    check_name="position_size",
                    passed=True,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"최대 포지션 초과: {order_value:,}원 > {self.limits['max_position_value']:,}원",
                    adjusted_quantity=allowed_quantity
                )

        return RiskCheckResult(
            check_name="position_risk",
            passed=True,
            risk_level=RiskLevel.LOW,
            message=f"포지션 리스크 정상: {position_pct*100:.1f}%"
        )

    def _check_portfolio_risk(
        self,
        stock_code: str,
        order_type: str,
        quantity: int,
        price: float,
        portfolio_value: float,
        current_positions: List[Dict[str, Any]]
    ) -> RiskCheckResult:
        """Stage 2: 포트폴리오 리스크 체크"""
        order_value = quantity * price

        # 현재 총 투자 금액
        total_invested = sum(pos.get('total_value', 0) for pos in current_positions)

        if order_type == 'buy':
            new_total = total_invested + order_value

            # 포트폴리오 총 노출도 체크 (80% 이상이면 경고)
            exposure_pct = new_total / portfolio_value if portfolio_value > 0 else 0

            if exposure_pct > 0.95:
                return RiskCheckResult(
                    check_name="portfolio_exposure",
                    passed=False,
                    risk_level=RiskLevel.CRITICAL,
                    message=f"포트폴리오 노출도 위험: {exposure_pct*100:.1f}% > 95%",
                    recommended_action="현금 비중 부족 - 매수 불가"
                )
            elif exposure_pct > 0.85:
                # 85% 이상이면 수량 축소
                max_allowed = portfolio_value * 0.85 - total_invested
                allowed_quantity = int(max_allowed / price) if price > 0 else 0

                if allowed_quantity <= 0:
                    return RiskCheckResult(
                        check_name="portfolio_exposure",
                        passed=False,
                        risk_level=RiskLevel.HIGH,
                        message=f"포트폴리오 노출도 초과: {exposure_pct*100:.1f}%"
                    )

                return RiskCheckResult(
                    check_name="portfolio_exposure",
                    passed=True,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"포트폴리오 노출도 조정 필요: {exposure_pct*100:.1f}%",
                    adjusted_quantity=allowed_quantity
                )

        return RiskCheckResult(
            check_name="portfolio_risk",
            passed=True,
            risk_level=RiskLevel.LOW,
            message="포트폴리오 리스크 정상"
        )

    def _check_market_risk(
        self,
        stock_code: str,
        order_type: str,
        quantity: int,
        price: float,
        market_data: Optional[Dict[str, Any]]
    ) -> RiskCheckResult:
        """Stage 3: 시장 리스크 체크"""
        if not market_data:
            return RiskCheckResult(
                check_name="market_risk",
                passed=True,
                risk_level=RiskLevel.MEDIUM,
                message="시장 데이터 없음 - 기본 체크만 수행"
            )

        # 변동성 체크
        volatility = market_data.get('volatility', 0)
        if volatility > self.limits['max_volatility']:
            return RiskCheckResult(
                check_name="volatility",
                passed=False,
                risk_level=RiskLevel.HIGH,
                message=f"변동성 초과: {volatility*100:.1f}% > {self.limits['max_volatility']*100:.1f}%",
                recommended_action="변동성이 높아 매매 위험"
            )

        # 거래량 체크
        volume = market_data.get('volume', 0)
        if volume < self.limits['min_volume']:
            return RiskCheckResult(
                check_name="liquidity",
                passed=False,
                risk_level=RiskLevel.HIGH,
                message=f"유동성 부족: 거래량 {volume:,} < {self.limits['min_volume']:,}",
                recommended_action="거래량이 적어 체결 위험"
            )

        # 호가 스프레드 체크
        spread_pct = market_data.get('spread_pct', 0)
        if spread_pct > self.limits['max_spread_pct']:
            return RiskCheckResult(
                check_name="spread",
                passed=True,  # 경고만
                risk_level=RiskLevel.MEDIUM,
                message=f"스프레드 주의: {spread_pct*100:.2f}% > {self.limits['max_spread_pct']*100:.2f}%"
            )

        return RiskCheckResult(
            check_name="market_risk",
            passed=True,
            risk_level=RiskLevel.LOW,
            message="시장 리스크 정상"
        )

    def _check_account_risk(
        self,
        order_type: str,
        quantity: int,
        price: float,
        portfolio_value: float
    ) -> RiskCheckResult:
        """Stage 4: 계정 리스크 체크"""
        order_value = quantity * price

        # 일일 손실 한도 체크
        daily_loss_pct = abs(self.daily_stats['total_loss']) / portfolio_value if portfolio_value > 0 else 0

        if daily_loss_pct > self.limits['max_daily_loss_pct']:
            self.trigger_emergency_stop(f"일일 손실 한도 초과: {daily_loss_pct*100:.2f}%")
            return RiskCheckResult(
                check_name="daily_loss",
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                message=f"일일 손실 한도 초과: {daily_loss_pct*100:.2f}% > {self.limits['max_daily_loss_pct']*100:.2f}%",
                recommended_action="오늘 거래 중지"
            )

        if abs(self.daily_stats['total_loss']) > self.limits['max_daily_loss_amount']:
            self.trigger_emergency_stop(f"일일 손실 금액 초과: {abs(self.daily_stats['total_loss']):,.0f}원")
            return RiskCheckResult(
                check_name="daily_loss_amount",
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                message=f"일일 손실 금액 초과: {abs(self.daily_stats['total_loss']):,.0f}원"
            )

        # 일일 거래 횟수 체크
        if self.daily_stats['trade_count'] >= self.limits['max_daily_trades']:
            return RiskCheckResult(
                check_name="daily_trades",
                passed=False,
                risk_level=RiskLevel.HIGH,
                message=f"일일 거래 횟수 초과: {self.daily_stats['trade_count']} >= {self.limits['max_daily_trades']}"
            )

        # 일일 매수 금액 한도 체크
        if order_type == 'buy':
            new_buy_amount = self.daily_stats['buy_amount'] + order_value
            if new_buy_amount > self.limits['max_daily_buy_amount']:
                # 가능한 금액 계산
                allowed_amount = self.limits['max_daily_buy_amount'] - self.daily_stats['buy_amount']
                allowed_quantity = int(allowed_amount / price) if price > 0 else 0

                if allowed_quantity <= 0:
                    return RiskCheckResult(
                        check_name="daily_buy_limit",
                        passed=False,
                        risk_level=RiskLevel.HIGH,
                        message=f"일일 매수 한도 초과: {new_buy_amount:,.0f}원"
                    )

                return RiskCheckResult(
                    check_name="daily_buy_limit",
                    passed=True,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"일일 매수 한도 조정 필요",
                    adjusted_quantity=allowed_quantity
                )

        return RiskCheckResult(
            check_name="account_risk",
            passed=True,
            risk_level=RiskLevel.LOW,
            message="계정 리스크 정상"
        )

    def trigger_emergency_stop(self, reason: str):
        """긴급 정지 활성화"""
        self.emergency_stop = True
        self.emergency_reason = reason
        logger.critical(f"🚨 긴급 정지 활성화: {reason}")

    def release_emergency_stop(self):
        """긴급 정지 해제"""
        self.emergency_stop = False
        self.emergency_reason = ""
        logger.info("✅ 긴급 정지 해제")

    def update_trade_result(self, profit_loss: float, order_type: str, amount: float):
        """거래 결과 업데이트"""
        self._reset_daily_stats_if_needed()

        self.daily_stats['trade_count'] += 1

        if profit_loss >= 0:
            self.daily_stats['total_profit'] += profit_loss
        else:
            self.daily_stats['total_loss'] += profit_loss

        if order_type == 'buy':
            self.daily_stats['buy_amount'] += amount
        else:
            self.daily_stats['sell_amount'] += amount

    def get_daily_stats(self) -> Dict[str, Any]:
        """일일 통계 반환"""
        self._reset_daily_stats_if_needed()
        return self.daily_stats.copy()

    def get_validation_summary(self) -> Dict[str, Any]:
        """검증 요약"""
        if not self.validation_history:
            return {'total': 0, 'approved': 0, 'rejected': 0, 'reduced': 0}

        return {
            'total': len(self.validation_history),
            'approved': len([v for v in self.validation_history if v.final_result == ValidationResult.APPROVED]),
            'rejected': len([v for v in self.validation_history if v.final_result == ValidationResult.REJECTED]),
            'reduced': len([v for v in self.validation_history if v.final_result == ValidationResult.REDUCED]),
            'emergency_stop': self.emergency_stop,
            'daily_stats': self.get_daily_stats()
        }


# 전역 접근 함수
def get_risk_pipeline() -> RiskValidationPipeline:
    return RiskValidationPipeline.get_instance()


def validate_order(
    stock_code: str,
    stock_name: str,
    order_type: str,
    quantity: int,
    price: float,
    portfolio_value: float,
    current_positions: List[Dict[str, Any]],
    market_data: Optional[Dict[str, Any]] = None
) -> ValidationReport:
    """주문 검증 편의 함수"""
    return get_risk_pipeline().validate_order(
        stock_code, stock_name, order_type, quantity, price,
        portfolio_value, current_positions, market_data
    )
