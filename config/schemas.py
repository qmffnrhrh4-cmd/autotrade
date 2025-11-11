"""
AutoTrade Pro - Unified Configuration Schema
Pydantic 기반 통합 설정 스키마 (v5.6+ Comprehensive)

COMPREHENSIVE 개선:
- 5개 설정 시스템 통합 → 단일 Pydantic 스키마
- unified_settings.py의 모든 설정 포함
- Type-safe configuration with validation
- Dot notation access: config.get('risk_management.max_position_size')
- Event listeners for dynamic settings
- JSON/YAML import/export
"""
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import yaml
import json


# ==================================================
# System Configuration
# ==================================================

class SystemConfig(BaseModel):
    """시스템 설정"""
    trading_enabled: bool = Field(default=True, description="트레이딩 활성화")
    test_mode: bool = Field(default=False, description="테스트 모드")
    auto_start: bool = Field(default=False, description="자동 시작")
    logging_level: str = Field(default="INFO", description="로깅 레벨")
    max_concurrent_analysis: int = Field(default=3, ge=1, le=10, description="최대 동시 분석 수")


# ==================================================
# Risk Management Configuration
# ==================================================

class RiskManagementConfig(BaseModel):
    """리스크 관리 설정 (Enhanced)"""

    # 기본 포지션 관리
    max_position_size: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="최대 포지션 비중 (총 자산 대비)"
    )
    position_limit: int = Field(
        default=5,
        ge=1,
        le=50,
        description="최대 동시 포지션 수"
    )

    # 손익 관리
    stop_loss_pct: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="기본 손절 비율"
    )
    take_profit_pct: float = Field(
        default=0.10,
        ge=0.0,
        le=2.0,
        description="기본 익절 비율"
    )
    emergency_stop_loss: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="긴급 손절 비율"
    )

    # 손실 한도
    max_daily_loss: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
        description="일일 최대 손실"
    )
    max_total_loss: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="총 최대 손실"
    )
    max_consecutive_losses: int = Field(
        default=3,
        ge=1,
        le=10,
        description="최대 연속 손실 횟수"
    )

    # Trailing Stop
    enable_trailing_stop: bool = Field(default=True, description="트레일링 스톱 활성화")
    trailing_stop_pct: float = Field(
        default=0.02,
        ge=0.0,
        le=0.5,
        description="트레일링 스톱 비율"
    )
    trailing_stop_atr_multiplier: float = Field(
        default=2.0,
        ge=0.5,
        le=5.0,
        description="ATR 승수"
    )
    trailing_stop_activation_pct: float = Field(
        default=0.03,
        ge=0.0,
        le=0.5,
        description="활성화 수익률"
    )

    # Kelly Criterion
    enable_kelly_criterion: bool = Field(default=False, description="켈리 배팅 활성화")
    kelly_fraction: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="켈리 공식 비율 (보수적)"
    )

    # Backward compatibility
    @property
    def daily_loss_limit(self) -> float:
        return self.max_daily_loss


# ==================================================
# Trading Configuration
# ==================================================

class TradingConfig(BaseModel):
    """트레이딩 설정"""
    min_price: int = Field(default=1000, ge=0, description="최소 주문 가격")
    max_price: int = Field(default=1000000, ge=0, description="최대 주문 가격")
    min_volume: int = Field(default=10000, ge=0, description="최소 거래량")
    commission_rate: float = Field(default=0.00015, ge=0.0, description="수수료율")
    slippage_pct: float = Field(default=0.0005, ge=0.0, description="슬리피지 비율")
    market_start_time: str = Field(default="09:00", description="장 시작 시간")
    market_end_time: str = Field(default="15:30", description="장 종료 시간")


# ==================================================
# Strategy Configurations
# ==================================================

class MomentumStrategyConfig(BaseModel):
    """모멘텀 전략 설정"""
    enabled: bool = Field(default=True, description="활성화")
    short_ma_period: int = Field(default=5, ge=1, le=50, description="단기 이평선")
    long_ma_period: int = Field(default=20, ge=5, le=200, description="장기 이평선")
    rsi_period: int = Field(default=14, ge=2, le=100, description="RSI 기간")
    rsi_overbought: int = Field(default=70, ge=50, le=100, description="RSI 과매수")
    rsi_oversold: int = Field(default=30, ge=0, le=50, description="RSI 과매도")


class VolatilityBreakoutConfig(BaseModel):
    """변동성 돌파 전략 설정"""
    enabled: bool = Field(default=True, description="활성화")
    k_value: float = Field(default=0.5, ge=0.0, le=2.0, description="변동폭 승수")
    entry_time: str = Field(default="09:05", description="진입 시각")
    exit_time: str = Field(default="15:15", description="청산 시각")
    use_volume_filter: bool = Field(default=True, description="거래량 필터 사용")


class PairsTradingConfig(BaseModel):
    """페어 트레이딩 전략 설정"""
    enabled: bool = Field(default=False, description="활성화")
    pairs: List[List[str]] = Field(
        default=[["005930", "000660"]],
        description="페어 목록 [삼성전자-SK하이닉스]"
    )
    spread_threshold: float = Field(default=2.0, ge=0.5, le=5.0, description="표준편차 임계값")
    lookback_period: int = Field(default=60, ge=20, le=250, description="롤백 기간 (일)")


class InstitutionalFollowingConfig(BaseModel):
    """수급 추종 전략 설정"""
    enabled: bool = Field(default=True, description="활성화")
    min_net_buy_volume: int = Field(
        default=1000000000,
        ge=0,
        description="최소 순매수 금액 (10억)"
    )
    consecutive_days: int = Field(default=3, ge=1, le=10, description="연속 매수 일수")


class StrategiesConfig(BaseModel):
    """전략 통합 설정"""
    momentum: MomentumStrategyConfig = Field(default_factory=MomentumStrategyConfig)
    volatility_breakout: VolatilityBreakoutConfig = Field(default_factory=VolatilityBreakoutConfig)
    pairs_trading: PairsTradingConfig = Field(default_factory=PairsTradingConfig)
    institutional_following: InstitutionalFollowingConfig = Field(default_factory=InstitutionalFollowingConfig)


# ==================================================
# AI Configuration
# ==================================================

class MarketRegimeConfig(BaseModel):
    """시장 레짐 분류 설정"""
    enabled: bool = Field(default=True, description="활성화")
    update_interval_hours: int = Field(default=4, ge=1, le=24, description="업데이트 간격 (시간)")
    regimes: Dict[str, str] = Field(
        default={"bull": "모멘텀", "bear": "방어적", "sideways": "역추세"},
        description="레짐별 전략 매핑"
    )


class AIConfig(BaseModel):
    """AI 설정 (Enhanced)"""
    enabled: bool = Field(default=True, description="AI 기능 활성화")
    default_analyzer: str = Field(
        default="gemini",
        description="기본 분석기 (gemini only)"
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="최소 신뢰도"
    )
    min_confidence_score: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="최소 신뢰도 점수 (Backward compat)"
    )
    timeout_seconds: int = Field(default=30, ge=5, le=120, description="타임아웃 (초)")
    analysis_interval: int = Field(default=300, ge=0, description="분석 주기 (초)")
    models: List[str] = Field(
        default=["gemini", "ensemble"],
        description="사용할 AI 모델 목록"
    )

    # 시장 레짐 분류
    market_regime_classification: MarketRegimeConfig = Field(
        default_factory=MarketRegimeConfig,
        description="시장 레짐 분류 설정"
    )

    # AI 스코어링 가중치
    scoring_weights: Dict[str, float] = Field(
        default={
            "technical_score": 0.30,
            "fundamental_score": 0.20,
            "ai_prediction_score": 0.25,
            "sentiment_score": 0.15,
            "volume_score": 0.10,
        },
        description="AI 스코어링 가중치"
    )


# ==================================================
# Advanced Automation Configuration
# ==================================================

class AutomationFeaturesConfig(BaseModel):
    """고급 자동화 기능 설정"""

    # 🆕 시장 분위기 자동 감지 및 대응
    market_sentiment_auto_response: bool = Field(
        default=False,
        description="시장 분위기 자동 감지 및 대응"
    )
    market_sentiment_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="시장 분위기 임계값"
    )

    # 🆕 계절성 및 패턴 기반 자동 매매
    seasonal_pattern_trading: bool = Field(
        default=False,
        description="계절성 및 패턴 기반 자동 매매"
    )
    seasonal_lookback_years: int = Field(
        default=3,
        ge=1,
        le=10,
        description="계절성 분석 기간 (년)"
    )

    # 🆕 스마트 자금 관리 시스템
    smart_money_management: bool = Field(
        default=True,
        description="스마트 자금 관리 시스템"
    )
    dynamic_position_sizing: bool = Field(
        default=True,
        description="동적 포지션 사이징"
    )

    # 🆕 다중 시간프레임 자동 분석
    multi_timeframe_analysis: bool = Field(
        default=True,
        description="다중 시간프레임 자동 분석"
    )
    timeframes: List[str] = Field(
        default=["1m", "5m", "15m", "1h", "1d"],
        description="분석할 시간프레임 목록"
    )

    # 🆕 유동성 기반 자동 주문 분할
    liquidity_based_order_split: bool = Field(
        default=True,
        description="유동성 기반 자동 주문 분할"
    )
    max_order_impact_pct: float = Field(
        default=0.05,
        ge=0.01,
        le=0.2,
        description="최대 주문 영향 비율 (%)"
    )

    # 🆕 자동 섹터 로테이션
    auto_sector_rotation: bool = Field(
        default=False,
        description="자동 섹터 로테이션"
    )
    sector_rotation_interval_days: int = Field(
        default=30,
        ge=7,
        le=365,
        description="섹터 로테이션 주기 (일)"
    )

    # 🆕 페어 트레이딩 자동화
    pairs_trading_automation: bool = Field(
        default=False,
        description="페어 트레이딩 자동화"
    )
    correlation_threshold: float = Field(
        default=0.8,
        ge=0.5,
        le=1.0,
        description="상관관계 임계값"
    )

    # 🆕 실시간 백테스팅 및 전략 검증
    realtime_backtest_validation: bool = Field(
        default=True,
        description="실시간 백테스팅 및 전략 검증"
    )
    validation_interval_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="검증 주기 (시간)"
    )

    # 🆕 비상 상황 자동 대응 시스템
    emergency_auto_response: bool = Field(
        default=True,
        description="비상 상황 자동 대응 시스템"
    )
    emergency_stop_loss_pct: float = Field(
        default=0.15,
        ge=0.05,
        le=0.5,
        description="비상 손절 비율 (%)"
    )
    circuit_breaker_enabled: bool = Field(
        default=True,
        description="서킷 브레이커 활성화"
    )


# ==================================================
# Backtesting Configuration
# ==================================================

class BacktestingConfig(BaseModel):
    """백테스팅 설정"""
    default_initial_capital: int = Field(default=10000000, ge=0, description="초기 자본 (1천만원)")
    commission_rate: float = Field(default=0.00015, ge=0.0, description="수수료율 (0.015%)")
    slippage_pct: float = Field(default=0.0005, ge=0.0, description="슬리피지 (0.05%)")
    generate_report: bool = Field(default=True, description="리포트 생성")
    report_format: str = Field(default="html", description="리포트 형식 (html/pdf)")
    report_includes: Dict[str, bool] = Field(
        default={
            "equity_curve": True,
            "drawdown_chart": True,
            "monthly_returns": True,
            "trade_list": True,
            "correlation_matrix": True,
        },
        description="리포트 포함 항목"
    )


# ==================================================
# Optimization Configuration
# ==================================================

class OptimizationConfig(BaseModel):
    """파라미터 최적화 설정"""
    method: str = Field(
        default="bayesian",
        description="최적화 방법 (grid/random/bayesian)"
    )
    n_trials: int = Field(default=50, ge=10, le=500, description="시행 횟수")
    n_jobs: int = Field(default=-1, description="병렬 처리 (-1=모든 CPU)")
    timeout_minutes: int = Field(default=60, ge=10, le=600, description="타임아웃 (분)")
    objective_metric: str = Field(
        default="sharpe_ratio",
        description="최적화 목표 (sharpe_ratio/total_return/max_drawdown)"
    )


# ==================================================
# Rebalancing Configuration
# ==================================================

class RebalancingConfig(BaseModel):
    """자동 리밸런싱 설정"""
    enabled: bool = Field(default=False, description="활성화")
    method: str = Field(
        default="time_based",
        description="방법 (time_based/threshold_based)"
    )
    frequency_days: int = Field(default=30, ge=1, le=365, description="시간 기반 주기 (일)")
    threshold_pct: float = Field(default=0.05, ge=0.01, le=0.5, description="임계값 기반 (5% 이탈)")
    use_risk_parity: bool = Field(default=False, description="리스크 패리티 사용")
    target_volatility: float = Field(default=0.15, ge=0.05, le=0.5, description="목표 변동성 (15%)")


# ==================================================
# Screening Configuration
# ==================================================

class QuantFactorValueConfig(BaseModel):
    """퀀트 팩터 - Value"""
    enabled: bool = Field(default=True, description="활성화")
    per_max: int = Field(default=15, ge=0, le=100, description="최대 PER")
    pbr_max: float = Field(default=1.5, ge=0.0, le=10.0, description="최대 PBR")


class QuantFactorQualityConfig(BaseModel):
    """퀀트 팩터 - Quality"""
    enabled: bool = Field(default=True, description="활성화")
    roe_min: int = Field(default=10, ge=0, le=100, description="최소 ROE (%)")
    debt_ratio_max: int = Field(default=100, ge=0, le=500, description="최대 부채비율 (%)")


class QuantFactorMomentumConfig(BaseModel):
    """퀀트 팩터 - Momentum"""
    enabled: bool = Field(default=True, description="활성화")
    return_1m_min: float = Field(default=0.05, ge=-1.0, le=1.0, description="최소 1개월 수익률")
    return_3m_min: float = Field(default=0.10, ge=-1.0, le=1.0, description="최소 3개월 수익률")


class ScreeningConfig(BaseModel):
    """스크리닝 및 스코어링 설정"""
    max_candidates: int = Field(default=50, ge=10, le=200, description="최대 후보 수")
    min_market_cap: int = Field(default=100000000000, ge=0, description="최소 시가총액 (1000억)")
    min_volume: int = Field(default=100000, ge=0, description="최소 거래량")
    min_price: int = Field(default=1000, ge=0, description="최소 주가")

    # 퀀트 팩터 스크리닝
    quant_factors: Dict[str, Any] = Field(
        default={
            "value": {"enabled": True, "per_max": 15, "pbr_max": 1.5},
            "quality": {"enabled": True, "roe_min": 10, "debt_ratio_max": 100},
            "momentum": {"enabled": True, "return_1m_min": 0.05, "return_3m_min": 0.10},
        },
        description="퀀트 팩터 설정"
    )


# ==================================================
# Notification Configuration
# ==================================================

class NotificationConfig(BaseModel):
    """알림 설정 (Enhanced)"""
    enabled: bool = Field(default=True, description="알림 활성화")

    # 채널
    telegram_enabled: bool = Field(default=False, description="텔레그램 알림")
    telegram_bot_token: Optional[str] = Field(default=None, description="텔레그램 봇 토큰")
    telegram_chat_id: Optional[str] = Field(default=None, description="텔레그램 채팅 ID")
    email_enabled: bool = Field(default=False, description="이메일 알림")
    email_to: Optional[str] = Field(default=None, description="수신 이메일")
    sms: bool = Field(default=False, description="SMS 알림")
    web_push: bool = Field(default=True, description="웹 푸시 알림")

    # 이벤트
    events: Dict[str, bool] = Field(
        default={
            "order_executed": True,
            "ai_signal": True,
            "stop_loss_triggered": True,
            "daily_report": True,
            "system_error": True,
        },
        description="알림 이벤트"
    )


# ==================================================
# UI Configuration
# ==================================================

class UIConfig(BaseModel):
    """UI 설정"""
    theme: str = Field(default="light", description="테마 (light/dark)")
    language: str = Field(default="ko", description="언어 (ko/en)")
    refresh_interval_seconds: int = Field(default=5, ge=1, le=60, description="새로고침 간격 (초)")
    show_guide_tour: bool = Field(default=True, description="가이드 투어 표시")
    dashboard_widgets: List[Dict[str, Any]] = Field(
        default=[
            {"id": "account_summary", "enabled": True, "position": {"x": 0, "y": 0, "w": 6, "h": 4}},
            {"id": "holdings", "enabled": True, "position": {"x": 6, "y": 0, "w": 6, "h": 4}},
            {"id": "ai_analysis", "enabled": True, "position": {"x": 0, "y": 4, "w": 12, "h": 6}},
            {"id": "chart", "enabled": True, "position": {"x": 0, "y": 10, "w": 8, "h": 8}},
            {"id": "order_book", "enabled": True, "position": {"x": 8, "y": 10, "w": 4, "h": 8}},
        ],
        description="대시보드 위젯 설정"
    )


# ==================================================
# Advanced Orders Configuration
# ==================================================

class AdvancedOrdersConfig(BaseModel):
    """고급 주문 설정"""
    enable_stop_orders: bool = Field(default=True, description="스톱 주문 활성화")
    enable_ioc_orders: bool = Field(default=True, description="IOC 주문 활성화 (Immediate Or Cancel)")
    enable_fok_orders: bool = Field(default=True, description="FOK 주문 활성화 (Fill Or Kill)")
    default_order_type: str = Field(default="limit", description="기본 주문 유형 (market/limit/stop)")


# ==================================================
# Anomaly Detection Configuration
# ==================================================

class AnomalyDetectionConfig(BaseModel):
    """시스템 이상 감지 설정"""
    enabled: bool = Field(default=True, description="활성화")
    check_interval_minutes: int = Field(default=5, ge=1, le=60, description="체크 간격 (분)")
    alert_threshold: float = Field(default=0.8, ge=0.5, le=1.0, description="이상 확률 임계값")
    monitor_items: Dict[str, bool] = Field(
        default={
            "api_response_time": True,
            "order_failure_rate": True,
            "account_balance_change": True,
            "system_cpu_usage": True,
            "system_memory_usage": True,
        },
        description="모니터링 대상"
    )


# ==================================================
# Logging Configuration
# ==================================================

class LoggingConfig(BaseModel):
    """로깅 설정"""
    level: str = Field(default="INFO", description="로그 레벨")
    console_level: str = Field(default="WARNING", description="콘솔 로그 레벨")
    file_path: str = Field(default="logs/bot.log", description="로그 파일 경로")
    max_file_size: int = Field(default=10485760, description="최대 파일 크기 (bytes)")
    backup_count: int = Field(default=30, description="백업 파일 수")
    rotation: str = Field(default="00:00", description="로그 로테이션 시간")
    format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        description="로그 포맷"
    )
    console_output: bool = Field(default=True, description="콘솔 출력 여부")
    colored_output: bool = Field(default=True, description="컬러 출력 여부")


# ==================================================
# Main Cycle Configuration
# ==================================================

class MainCycleConfig(BaseModel):
    """메인 사이클 설정"""
    sleep_seconds: int = Field(default=60, ge=1, description="메인 루프 대기 시간 (초)")
    health_check_interval: int = Field(default=300, ge=60, description="헬스 체크 간격 (초)")

    # Backward compatibility
    @property
    def SLEEP_SECONDS(self) -> int:
        """별칭: sleep_seconds"""
        return self.sleep_seconds

    @property
    def HEALTH_CHECK_INTERVAL(self) -> int:
        """별칭: health_check_interval"""
        return self.health_check_interval


# ==================================================
# Root Configuration
# ==================================================

class AutoTradeConfig(BaseModel):
    """통합 설정 (루트) - Comprehensive"""

    # 시스템
    system: SystemConfig = Field(default_factory=SystemConfig)

    # 리스크 관리
    risk_management: RiskManagementConfig = Field(default_factory=RiskManagementConfig)

    # 트레이딩
    trading: TradingConfig = Field(default_factory=TradingConfig)

    # 전략
    strategies: StrategiesConfig = Field(default_factory=StrategiesConfig)

    # AI
    ai_analysis: AIConfig = Field(default_factory=AIConfig)
    ai: AIConfig = Field(default_factory=AIConfig)  # Backward compatibility

    # 백테스팅
    backtesting: BacktestingConfig = Field(default_factory=BacktestingConfig)

    # 최적화
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)

    # 리밸런싱
    rebalancing: RebalancingConfig = Field(default_factory=RebalancingConfig)

    # 스크리닝
    screening: ScreeningConfig = Field(default_factory=ScreeningConfig)

    # 알림
    notification: NotificationConfig = Field(default_factory=NotificationConfig)

    # UI
    ui: UIConfig = Field(default_factory=UIConfig)

    # 고급 주문
    advanced_orders: AdvancedOrdersConfig = Field(default_factory=AdvancedOrdersConfig)

    # 이상 감지
    anomaly_detection: AnomalyDetectionConfig = Field(default_factory=AnomalyDetectionConfig)

    # 로깅
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # 메인 사이클
    main_cycle: MainCycleConfig = Field(default_factory=MainCycleConfig)

    # 고급 자동화 기능 (v6.1 NEW)
    automation_features: AutomationFeaturesConfig = Field(default_factory=AutomationFeaturesConfig)

    # 전역 설정
    environment: str = Field(default="production", description="환경 (production/development/test)")
    debug_mode: bool = Field(default=False, description="디버그 모드")
    initial_capital: float = Field(default=10000000, ge=0, description="초기 자본")

    # Backward compatibility properties
    @property
    def position(self) -> Dict[str, Any]:
        """Legacy: position 카테고리 (risk_management로 매핑)"""
        return {
            "max_open_positions": self.risk_management.position_limit,
            "risk_per_trade_ratio": self.risk_management.max_position_size,
            "max_position_size": self.risk_management.max_position_size,
        }

    @property
    def profit_loss(self) -> Dict[str, Any]:
        """Legacy: profit_loss 카테고리 (risk_management로 매핑)"""
        return {
            "take_profit_ratio": self.risk_management.take_profit_pct,
            "stop_loss_ratio": self.risk_management.stop_loss_pct,
            "trailing_stop_enabled": self.risk_management.enable_trailing_stop,
            "trailing_stop_ratio": self.risk_management.trailing_stop_pct,
        }

    @property
    def scanning(self) -> Dict[str, Any]:
        """Legacy: scanning 카테고리 (screening으로 매핑)"""
        return {
            "max_candidates": self.screening.max_candidates,
            "min_price": self.screening.min_price,
            "min_volume": self.screening.min_volume,
        }

    @property
    def scoring(self) -> Dict[str, Any]:
        """Legacy: scoring 카테고리 (ai.scoring_weights로 매핑)"""
        return self.ai.scoring_weights

    @property
    def dashboard(self) -> Dict[str, Any]:
        """Legacy: dashboard 카테고리 (ui로 매핑)"""
        return {
            "theme": self.ui.theme,
            "language": self.ui.language,
            "refresh_interval_seconds": self.ui.refresh_interval_seconds,
        }

    @property
    def development(self) -> Dict[str, Any]:
        """Legacy: development 카테고리"""
        return {
            "debug_mode": self.debug_mode,
            "environment": self.environment,
        }

    @property
    def api(self) -> Dict[str, Any]:
        """Legacy: api 카테고리"""
        return {
            "timeout": self.ai.timeout_seconds,
            "commission_rate": self.trading.commission_rate,
        }

    @property
    def database(self) -> Dict[str, Any]:
        """Legacy: database 카테고리"""
        return {
            "path": "data/autotrade.db",
        }

    @classmethod
    def from_yaml(cls, path: str) -> 'AutoTradeConfig':
        """YAML 파일에서 설정 로드"""
        yaml_path = Path(path)
        if not yaml_path.exists():
            # 기본 설정 반환
            return cls()

        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def save_yaml(self, path: str):
        """설정을 YAML 파일로 저장"""
        yaml_path = Path(path)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                self.model_dump(exclude={"ai"}),  # ai는 ai_analysis와 중복이므로 제외
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )

    @classmethod
    def from_json(cls, path: str) -> 'AutoTradeConfig':
        """JSON 파일에서 설정 로드"""
        json_path = Path(path)
        if not json_path.exists():
            return cls()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return cls(**data)

    def save_json(self, path: str):
        """설정을 JSON 파일로 저장"""
        json_path = Path(path)
        json_path.parent.mkdir(parents=True, exist_ok=True)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(
                self.model_dump(exclude={"ai"}),
                f,
                ensure_ascii=False,
                indent=2
            )

    def get(self, path: str, default=None):
        """
        Dot notation으로 설정 값 가져오기

        Example:
            config.get('risk_management.max_position_size')
            config.get('ai_analysis.confidence_threshold', 0.5)
        """
        keys = path.split('.')
        value = self

        for key in keys:
            if hasattr(value, key):
                value = getattr(value, key)
            else:
                return default

        return value

    def set(self, path: str, value: Any):
        """
        Dot notation으로 설정 값 변경

        Example:
            config.set('risk_management.max_position_size', 0.25)
        """
        keys = path.split('.')
        obj = self

        # Navigate to the parent object
        for key in keys[:-1]:
            if hasattr(obj, key):
                obj = getattr(obj, key)
            else:
                raise KeyError(f"Invalid config path: {path}")

        # Set the final key
        if hasattr(obj, keys[-1]):
            setattr(obj, keys[-1], value)
        else:
            raise KeyError(f"Invalid config key: {keys[-1]}")

    class Config:
        json_schema_extra = {
            "title": "AutoTrade Pro Configuration",
            "description": "Comprehensive unified configuration schema for AutoTrade Pro v5.6+"
        }


# Export
__all__ = [
    'AutoTradeConfig',
    'SystemConfig',
    'RiskManagementConfig',
    'TradingConfig',
    'StrategiesConfig',
    'MomentumStrategyConfig',
    'VolatilityBreakoutConfig',
    'PairsTradingConfig',
    'InstitutionalFollowingConfig',
    'AIConfig',
    'MarketRegimeConfig',
    'AutomationFeaturesConfig',
    'BacktestingConfig',
    'OptimizationConfig',
    'RebalancingConfig',
    'ScreeningConfig',
    'NotificationConfig',
    'UIConfig',
    'AdvancedOrdersConfig',
    'AnomalyDetectionConfig',
    'LoggingConfig',
    'MainCycleConfig',
]
