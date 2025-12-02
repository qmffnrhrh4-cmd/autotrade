"""
core/portfolio_risk_manager.py
포트폴리오 수준 리스크 관리

VaR 계산, 상관관계 분석, 동적 포지션 사이징, 섹터 노출도 관리
"""
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class RiskMetric(Enum):
    """리스크 지표"""
    VAR_95 = "var_95"           # 95% VaR
    VAR_99 = "var_99"           # 99% VaR
    CVAR = "cvar"               # Conditional VaR
    SHARPE = "sharpe"           # 샤프 비율
    SORTINO = "sortino"         # 소르티노 비율
    MAX_DRAWDOWN = "max_dd"     # 최대 낙폭
    BETA = "beta"               # 베타
    VOLATILITY = "volatility"   # 변동성


@dataclass
class PositionRisk:
    """포지션 리스크"""
    stock_code: str
    stock_name: str
    quantity: int
    current_value: float
    weight: float                   # 포트폴리오 비중
    daily_volatility: float         # 일일 변동성
    var_95: float                   # 개별 VaR (95%)
    sector: str = "기타"
    correlation_to_market: float = 1.0
    contribution_to_risk: float = 0.0  # 포트폴리오 리스크 기여도


@dataclass
class PortfolioRiskReport:
    """포트폴리오 리스크 보고서"""
    timestamp: str
    total_value: float
    cash: float
    invested: float

    # 전체 리스크 지표
    portfolio_var_95: float         # 포트폴리오 VaR (95%)
    portfolio_var_99: float         # 포트폴리오 VaR (99%)
    portfolio_volatility: float     # 포트폴리오 변동성
    max_drawdown: float             # 최대 낙폭
    sharpe_ratio: float             # 샤프 비율

    # 섹터 노출도
    sector_exposure: Dict[str, float]
    max_sector_weight: float

    # 개별 포지션
    positions: List[PositionRisk]

    # 경고/권장
    warnings: List[str]
    recommendations: List[str]


class PortfolioRiskManager:
    """
    포트폴리오 리스크 매니저

    기능:
    - VaR 계산 (파라메트릭, 히스토리컬)
    - 상관관계 분석
    - 동적 포지션 사이징
    - 섹터 노출도 관리
    - 리스크 예산 배분
    """

    _instance = None
    _lock = Lock()

    # 기본 설정
    DEFAULT_CONFIG = {
        'var_confidence_95': 1.645,      # 95% 신뢰수준 z-score
        'var_confidence_99': 2.326,      # 99% 신뢰수준 z-score
        'max_portfolio_var_pct': 0.05,   # 최대 포트폴리오 VaR 5%
        'max_sector_weight': 0.40,       # 최대 섹터 비중 40%
        'max_single_position': 0.15,     # 최대 단일 종목 15%
        'min_sharpe_ratio': 0.5,         # 최소 샤프 비율
        'risk_free_rate': 0.035,         # 무위험 이자율 3.5%
        'lookback_days': 60,             # 변동성 계산 기간
    }

    # 섹터 분류 (예시 - 실제로는 API에서 가져와야 함)
    SECTOR_MAP = {
        '005930': '전자', '000660': '전자', '035420': 'IT',
        '005380': '자동차', '051910': '화학', '006400': '전자',
        '068270': 'IT', '035720': 'IT', '028260': '엔터',
        '105560': '금융', '055550': '금융', '086790': '금융',
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
        self.config = self.DEFAULT_CONFIG.copy()

        # 가격 히스토리 캐시
        self.price_history: Dict[str, List[float]] = defaultdict(list)
        self.return_history: Dict[str, List[float]] = defaultdict(list)

        # 시장 수익률 (KOSPI)
        self.market_returns: List[float] = []

        # 보고서 히스토리
        self.report_history: List[PortfolioRiskReport] = []

        logger.info("포트폴리오 리스크 매니저 초기화 완료")

    @classmethod
    def get_instance(cls) -> 'PortfolioRiskManager':
        return cls()

    def update_price(self, stock_code: str, price: float):
        """가격 업데이트 및 수익률 계산"""
        history = self.price_history[stock_code]
        history.append(price)

        # 최대 120일 유지
        if len(history) > 120:
            self.price_history[stock_code] = history[-120:]

        # 수익률 계산
        if len(history) >= 2:
            daily_return = (history[-1] / history[-2]) - 1
            self.return_history[stock_code].append(daily_return)

            if len(self.return_history[stock_code]) > 120:
                self.return_history[stock_code] = self.return_history[stock_code][-120:]

    def update_market_return(self, market_return: float):
        """시장 수익률 업데이트"""
        self.market_returns.append(market_return)
        if len(self.market_returns) > 120:
            self.market_returns = self.market_returns[-120:]

    def calculate_volatility(self, stock_code: str) -> float:
        """일일 변동성 계산"""
        returns = self.return_history.get(stock_code, [])
        if len(returns) < 5:
            return 0.02  # 기본 2%

        return float(np.std(returns))

    def calculate_var(
        self,
        value: float,
        volatility: float,
        confidence: float = 1.645,  # 95%
        holding_period: int = 1
    ) -> float:
        """
        VaR 계산 (파라메트릭 방식)

        VaR = Value × Volatility × Z-score × √(Holding Period)
        """
        return value * volatility * confidence * np.sqrt(holding_period)

    def calculate_position_risk(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        current_price: float,
        portfolio_value: float
    ) -> PositionRisk:
        """개별 포지션 리스크 계산"""
        current_value = quantity * current_price
        weight = current_value / portfolio_value if portfolio_value > 0 else 0
        volatility = self.calculate_volatility(stock_code)
        var_95 = self.calculate_var(current_value, volatility)

        # 시장 상관계수 계산
        correlation = self._calculate_correlation_to_market(stock_code)

        # 섹터 분류
        sector = self.SECTOR_MAP.get(stock_code, '기타')

        return PositionRisk(
            stock_code=stock_code,
            stock_name=stock_name,
            quantity=quantity,
            current_value=current_value,
            weight=weight,
            daily_volatility=volatility,
            var_95=var_95,
            sector=sector,
            correlation_to_market=correlation
        )

    def _calculate_correlation_to_market(self, stock_code: str) -> float:
        """시장과의 상관계수 계산"""
        stock_returns = self.return_history.get(stock_code, [])

        if len(stock_returns) < 10 or len(self.market_returns) < 10:
            return 1.0  # 기본값

        # 같은 기간의 수익률만 사용
        min_len = min(len(stock_returns), len(self.market_returns))
        stock_arr = np.array(stock_returns[-min_len:])
        market_arr = np.array(self.market_returns[-min_len:])

        try:
            correlation = np.corrcoef(stock_arr, market_arr)[0, 1]
            return float(correlation) if not np.isnan(correlation) else 1.0
        except Exception:
            return 1.0

    def calculate_portfolio_var(
        self,
        positions: List[PositionRisk],
        portfolio_value: float
    ) -> Tuple[float, float]:
        """
        포트폴리오 VaR 계산 (분산-공분산 방식)

        Returns:
            (var_95, var_99)
        """
        if not positions:
            return 0, 0

        n = len(positions)
        weights = np.array([p.weight for p in positions])
        volatilities = np.array([p.daily_volatility for p in positions])

        # 단순화: 동일 상관계수 가정 (0.5)
        # 실제로는 상관관계 행렬을 구해야 함
        avg_correlation = 0.5

        # 포트폴리오 분산 계산
        # σ²_p = Σ w²_i σ²_i + 2 Σ Σ w_i w_j ρ_ij σ_i σ_j
        variance = 0

        # 개별 분산 합
        for i in range(n):
            variance += (weights[i] ** 2) * (volatilities[i] ** 2)

        # 공분산 합 (단순화)
        for i in range(n):
            for j in range(i + 1, n):
                variance += 2 * weights[i] * weights[j] * avg_correlation * volatilities[i] * volatilities[j]

        portfolio_volatility = np.sqrt(variance)

        var_95 = portfolio_value * portfolio_volatility * self.config['var_confidence_95']
        var_99 = portfolio_value * portfolio_volatility * self.config['var_confidence_99']

        return var_95, var_99

    def calculate_sector_exposure(self, positions: List[PositionRisk]) -> Dict[str, float]:
        """섹터별 노출도 계산"""
        sector_values: Dict[str, float] = defaultdict(float)
        total_value = sum(p.current_value for p in positions)

        for pos in positions:
            sector_values[pos.sector] += pos.current_value

        if total_value <= 0:
            return {}

        return {sector: value / total_value for sector, value in sector_values.items()}

    def calculate_optimal_position_size(
        self,
        stock_code: str,
        stock_name: str,
        current_price: float,
        portfolio_value: float,
        current_positions: List[Dict],
        target_risk_contribution: float = 0.02  # 목표 리스크 기여도 2%
    ) -> int:
        """
        최적 포지션 크기 계산

        Kelly Criterion 변형 + 리스크 예산 기반
        """
        volatility = self.calculate_volatility(stock_code)

        if volatility <= 0:
            volatility = 0.02  # 기본 2%

        # 리스크 예산 기반 포지션 크기
        # Position Size = (Target Risk Contribution × Portfolio Value) / (Volatility × Price)
        risk_budget = target_risk_contribution * portfolio_value
        optimal_value = risk_budget / volatility

        # 최대 포지션 제한 적용
        max_position_value = portfolio_value * self.config['max_single_position']
        optimal_value = min(optimal_value, max_position_value)

        # 수량 계산
        quantity = int(optimal_value / current_price) if current_price > 0 else 0

        logger.debug(
            f"최적 포지션 계산: {stock_name} - "
            f"변동성={volatility:.2%}, 리스크예산={risk_budget:,.0f}, "
            f"최적가치={optimal_value:,.0f}, 수량={quantity}"
        )

        return max(0, quantity)

    def generate_risk_report(
        self,
        portfolio_value: float,
        cash: float,
        positions: List[Dict[str, Any]]
    ) -> PortfolioRiskReport:
        """포트폴리오 리스크 보고서 생성"""
        warnings = []
        recommendations = []

        # 포지션 리스크 계산
        position_risks = []
        for pos in positions:
            pr = self.calculate_position_risk(
                stock_code=pos.get('stock_code', ''),
                stock_name=pos.get('stock_name', ''),
                quantity=pos.get('quantity', 0),
                current_price=pos.get('current_price', 0),
                portfolio_value=portfolio_value
            )
            position_risks.append(pr)

        invested = sum(pr.current_value for pr in position_risks)

        # 포트폴리오 VaR
        var_95, var_99 = self.calculate_portfolio_var(position_risks, invested)

        # 포트폴리오 변동성
        if position_risks:
            avg_vol = np.mean([pr.daily_volatility for pr in position_risks])
        else:
            avg_vol = 0

        # 섹터 노출도
        sector_exposure = self.calculate_sector_exposure(position_risks)
        max_sector_weight = max(sector_exposure.values()) if sector_exposure else 0

        # 경고 생성
        var_pct = var_95 / portfolio_value if portfolio_value > 0 else 0
        if var_pct > self.config['max_portfolio_var_pct']:
            warnings.append(
                f"포트폴리오 VaR가 한도 초과: {var_pct:.1%} > {self.config['max_portfolio_var_pct']:.1%}"
            )
            recommendations.append("포지션 축소 또는 헤지 고려")

        if max_sector_weight > self.config['max_sector_weight']:
            max_sector = max(sector_exposure, key=sector_exposure.get)
            warnings.append(
                f"섹터 집중도 초과: {max_sector} {max_sector_weight:.1%} > {self.config['max_sector_weight']:.1%}"
            )
            recommendations.append(f"{max_sector} 섹터 비중 축소 권장")

        # 개별 종목 집중도 체크
        for pr in position_risks:
            if pr.weight > self.config['max_single_position']:
                warnings.append(
                    f"단일 종목 집중: {pr.stock_name} {pr.weight:.1%} > {self.config['max_single_position']:.1%}"
                )

        # 리스크 기여도 계산
        total_var = var_95
        for pr in position_risks:
            if total_var > 0:
                pr.contribution_to_risk = pr.var_95 / total_var

        # 샤프 비율 (단순화)
        if avg_vol > 0:
            # 예상 수익률 = 무위험이자율 + 프리미엄 (단순화)
            expected_return = self.config['risk_free_rate'] + avg_vol * 0.5
            sharpe = (expected_return - self.config['risk_free_rate']) / avg_vol
        else:
            sharpe = 0

        report = PortfolioRiskReport(
            timestamp=datetime.now().isoformat(),
            total_value=portfolio_value,
            cash=cash,
            invested=invested,
            portfolio_var_95=var_95,
            portfolio_var_99=var_99,
            portfolio_volatility=avg_vol,
            max_drawdown=0,  # TODO: 히스토리 기반 계산
            sharpe_ratio=sharpe,
            sector_exposure=sector_exposure,
            max_sector_weight=max_sector_weight,
            positions=position_risks,
            warnings=warnings,
            recommendations=recommendations
        )

        # 히스토리 저장
        self.report_history.append(report)
        if len(self.report_history) > 100:
            self.report_history = self.report_history[-50:]

        return report

    def should_reduce_position(
        self,
        stock_code: str,
        current_positions: List[PositionRisk],
        portfolio_value: float
    ) -> Tuple[bool, str]:
        """포지션 축소 필요 여부 판단"""
        for pos in current_positions:
            if pos.stock_code == stock_code:
                # 비중 초과
                if pos.weight > self.config['max_single_position']:
                    return True, f"비중 초과: {pos.weight:.1%}"

                # VaR 기여도 초과 (30% 이상)
                if pos.contribution_to_risk > 0.30:
                    return True, f"리스크 기여도 과다: {pos.contribution_to_risk:.1%}"

        return False, ""

    def get_rebalancing_suggestions(
        self,
        current_positions: List[PositionRisk],
        portfolio_value: float
    ) -> List[Dict[str, Any]]:
        """리밸런싱 제안"""
        suggestions = []

        # 섹터 노출도 체크
        sector_exposure = self.calculate_sector_exposure(current_positions)

        for sector, weight in sector_exposure.items():
            if weight > self.config['max_sector_weight']:
                excess = weight - self.config['max_sector_weight']
                excess_value = excess * portfolio_value

                sector_positions = [p for p in current_positions if p.sector == sector]
                sector_positions.sort(key=lambda x: x.contribution_to_risk, reverse=True)

                if sector_positions:
                    suggestions.append({
                        'type': 'reduce_sector',
                        'sector': sector,
                        'current_weight': weight,
                        'target_weight': self.config['max_sector_weight'],
                        'reduce_amount': excess_value,
                        'candidates': [p.stock_name for p in sector_positions[:3]]
                    })

        # 개별 종목 집중도 체크
        for pos in current_positions:
            if pos.weight > self.config['max_single_position']:
                excess = pos.weight - self.config['max_single_position']
                suggestions.append({
                    'type': 'reduce_position',
                    'stock_code': pos.stock_code,
                    'stock_name': pos.stock_name,
                    'current_weight': pos.weight,
                    'target_weight': self.config['max_single_position'],
                    'reduce_quantity': int(pos.quantity * excess / pos.weight)
                })

        return suggestions


# 전역 접근 함수
def get_portfolio_risk_manager() -> PortfolioRiskManager:
    return PortfolioRiskManager.get_instance()
