"""
virtual_trading/diverse_strategies.py
12가지 다양한 실전 매매 전략 구현 (v5.7.5: 10개 → 12개 확장)

User Requirement:
"시중에 나온 다양한 매매 전략법을 완전 다른걸로 12개 해서 유리한 조합 테스트"
Not simple score variations - fundamentally different trading approaches.

v5.7.5 추가 전략:
11. 기관추종 (Institutional Following): 기관/외국인 순매수 추종
12. 거래량RSI (Volume & RSI Combined): 거래량 급증 + RSI 조합
"""
from typing import Dict, Optional
from datetime import datetime
from .virtual_account import VirtualAccount, VirtualPosition


class DiverseTradingStrategy:
    """다양한 실전 매매 전략의 베이스 클래스"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

        # 공통 설정
        self.max_positions = 5
        self.position_size_rate = 0.15
        self.min_price = 1000  # 최소 주가 (저가주 필터)

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        """매수 조건 확인 (전략별로 오버라이드)"""
        raise NotImplementedError

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        """매도 조건 확인 (전략별로 오버라이드)"""
        raise NotImplementedError

    def calculate_quantity(self, price: int, account: VirtualAccount) -> int:
        """매수 수량 계산"""
        available_cash = account.cash
        target_amount = int(available_cash * self.position_size_rate)
        quantity = target_amount // price
        return max(quantity, 1)


# ============================================================================
# 전략 1: 모멘텀 추세 전략 (Momentum Trend Following)
# ============================================================================
class MomentumStrategy(DiverseTradingStrategy):
    """
    강한 상승 추세를 따라가는 전략
    - 거래량 급증 + 주가 상승 종목에 진입
    - 추세 약화시 빠르게 청산
    """

    def __init__(self):
        super().__init__("모멘텀추세", "강한 상승세 포착 후 추세 추종")
        self.max_positions = 6
        self.position_size_rate = 0.18
        self.min_volume_ratio = 2.0  # 평균 거래량 대비 2배 이상
        self.min_price_change = 3.0  # 최소 3% 상승

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        # 거래량 급증 확인
        volume_ratio = stock_data.get('volume_ratio', 1.0)
        if volume_ratio < self.min_volume_ratio:
            return False

        # 주가 상승 확인
        price_change = stock_data.get('price_change_percent', 0)
        if price_change < self.min_price_change:
            return False

        # RSI 과열 방지 (70 이하)
        rsi = stock_data.get('rsi', 50)
        if rsi > 70:
            return False

        return True

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # 익절: 12% 이상
        if pnl_rate >= 12.0:
            return True, f"모멘텀 익절 {pnl_rate:.1f}%"

        # 손절: -6% 이하
        if pnl_rate <= -6.0:
            return True, f"모멘텀 손절 {pnl_rate:.1f}%"

        # 추세 약화 감지 (거래량 감소)
        volume_ratio = stock_data.get('volume_ratio', 1.0)
        if volume_ratio < 0.7 and pnl_rate < 3.0:
            return True, "거래량 감소로 청산"

        # 최대 보유 기간: 7일
        if days_held >= 7:
            return True, f"보유 {days_held}일 경과"

        return False, ""


# ============================================================================
# 전략 2: 평균회귀 전략 (Mean Reversion)
# ============================================================================
class MeanReversionStrategy(DiverseTradingStrategy):
    """
    과매도 구간에서 반등 포착 전략
    - RSI 30 이하 과매도 구간 진입
    - 단기 반등 노리고 빠른 익절
    """

    def __init__(self):
        super().__init__("평균회귀", "과매도 구간 반등 노림")
        self.max_positions = 4
        self.position_size_rate = 0.20
        self.max_rsi = 35  # RSI 35 이하
        self.min_days_down = 3  # 최소 3일 하락

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        rsi = stock_data.get('rsi', 50)
        if rsi > self.max_rsi:
            return False

        consecutive_down = stock_data.get('consecutive_down_days', 0)
        price_change = stock_data.get('price_change_percent', 0)

        if consecutive_down >= self.min_days_down:
            pass
        elif price_change < -3.0:
            pass
        else:
            return False

        if price_change < -10.0:
            return False

        return True

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # 빠른 익절: 5% 이상
        if pnl_rate >= 5.0:
            return True, f"평균회귀 익절 {pnl_rate:.1f}%"

        # 손절: -4% 이하
        if pnl_rate <= -4.0:
            return True, f"평균회귀 손절 {pnl_rate:.1f}%"

        # RSI 반등 확인 후 매도 (60 이상)
        rsi = stock_data.get('rsi', 50)
        if rsi >= 60 and pnl_rate > 2.0:
            return True, "RSI 회복으로 익절"

        # 최대 보유: 5일
        if days_held >= 5:
            return True, f"보유 {days_held}일 경과"

        return False, ""


# ============================================================================
# 전략 3: 돌파 매매 전략 (Breakout Trading)
# ============================================================================
class BreakoutStrategy(DiverseTradingStrategy):
    """
    저항선 돌파 시 진입 전략
    - 52주 신고가 돌파
    - 박스권 상단 돌파
    """

    def __init__(self):
        super().__init__("돌파매매", "저항선 돌파 포착")
        self.max_positions = 5
        self.position_size_rate = 0.16
        self.breakout_threshold = 0.98  # 52주 고가의 98% 이상

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        current_price = stock_data.get('current_price', 0)
        high_52w = stock_data.get('high_52week')

        if high_52w is not None and high_52w > 0:
            if current_price < high_52w * 0.95:
                return False
        else:
            price_change = stock_data.get('price_change_percent', 0)
            if price_change < 3.0:
                return False

        volume_ratio = stock_data.get('volume_ratio', 1.0)
        if volume_ratio < 1.2:
            return False

        price_change = stock_data.get('price_change_percent', 0)
        if price_change < 0.5:
            return False

        return True

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # 익절: 15% 이상 (큰 수익 추구)
        if pnl_rate >= 15.0:
            return True, f"돌파 익절 {pnl_rate:.1f}%"

        # 트레일링 스탑: 최고가 대비 -7% 하락시
        highest_rate = position.highest_price / position.average_price * 100 - 100
        if highest_rate > 8.0:
            current_rate = current_price / position.average_price * 100 - 100
            if current_rate < highest_rate - 7.0:
                return True, f"트레일링 스탑 (최고 {highest_rate:.1f}% → 현재 {current_rate:.1f}%)"

        # 손절: -5% 이하
        if pnl_rate <= -5.0:
            return True, f"돌파 실패 손절 {pnl_rate:.1f}%"

        # 최대 보유: 10일
        if days_held >= 10:
            return True, f"보유 {days_held}일 경과"

        return False, ""


# ============================================================================
# 전략 4: 가치투자 전략 (Value Investing)
# ============================================================================
class ValueInvestingStrategy(DiverseTradingStrategy):
    """
    저평가 우량주 장기 보유 전략
    - PER, PBR 낮은 종목
    - 배당 수익률 높은 종목
    """

    def __init__(self):
        super().__init__("가치투자", "저평가 우량주 장기 보유")
        self.max_positions = 3
        self.position_size_rate = 0.25
        self.max_per = 12.0  # PER 12 이하
        self.max_pbr = 1.2   # PBR 1.2 이하
        self.min_dividend = 2.0  # 배당수익률 2% 이상

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        # v5.9: 데이터 없을 때 조건 완화
        # PER 확인 (데이터 있을 때만)
        per = stock_data.get('per')
        if per is not None and per > 0:
            if per > self.max_per:
                return False

        # PBR 확인 (데이터 있을 때만)
        pbr = stock_data.get('pbr')
        if pbr is not None and pbr > 0:
            if pbr > self.max_pbr:
                return False

        # 배당수익률 확인 (데이터 있을 때만)
        dividend_yield = stock_data.get('dividend_yield')
        if dividend_yield is not None:
            if dividend_yield < self.min_dividend:
                return False

        # 데이터가 모두 없으면 기본 조건: 안정적 상승
        if per is None and pbr is None and dividend_yield is None:
            # 안정적인 상승 (2-5%)
            price_change = stock_data.get('price_change_percent', 0)
            if not (2.0 <= price_change <= 5.0):
                return False
            # 거래량도 적당히
            volume_ratio = stock_data.get('volume_ratio', 1.0)
            if volume_ratio < 1.0:
                return False
        else:
            # 안정적인 종목 선호 (급등/급락 제외)
            price_change = stock_data.get('price_change_percent', 0)
            if abs(price_change) > 5.0:
                return False

        return True

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # 목표 수익: 20% 이상 (장기 보유 목표)
        if pnl_rate >= 20.0:
            return True, f"가치투자 익절 {pnl_rate:.1f}%"

        # 손절: -8% 이하 (여유 있는 손절)
        if pnl_rate <= -8.0:
            return True, f"가치투자 손절 {pnl_rate:.1f}%"

        # 밸류에이션 악화 확인
        per = stock_data.get('per', 0)
        if per > 20.0 and pnl_rate > 10.0:
            return True, "밸류에이션 악화로 익절"

        # 최대 보유: 30일 (장기 보유)
        if days_held >= 30:
            return True, f"보유 {days_held}일 경과"

        return False, ""


# ============================================================================
# 전략 5: 스윙 트레이딩 전략 (Swing Trading)
# ============================================================================
class SwingTradingStrategy(DiverseTradingStrategy):
    """
    단기 변동성을 이용한 스윙 전략
    - 볼린저밴드 하단 매수, 상단 매도
    - 3-7일 단기 보유
    """

    def __init__(self):
        super().__init__("스윙매매", "단기 변동성 활용")
        self.max_positions = 7
        self.position_size_rate = 0.12
        self.bb_lower_threshold = 0.95  # 볼린저 하단 근처

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        # 볼린저밴드 하단 근처 확인
        bb_position = stock_data.get('bb_position', 0.5)  # 0: 하단, 1: 상단
        if bb_position > 0.3:
            return False

        # 변동성 확인 (ATR)
        volatility = stock_data.get('volatility', 0)
        if volatility < 2.0:  # 최소 2% 변동성
            return False

        # RSI 40 이하
        rsi = stock_data.get('rsi', 50)
        if rsi > 40:
            return False

        return True

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # 익절: 8% 이상
        if pnl_rate >= 8.0:
            return True, f"스윙 익절 {pnl_rate:.1f}%"

        # 손절: -4% 이하
        if pnl_rate <= -4.0:
            return True, f"스윙 손절 {pnl_rate:.1f}%"

        # 볼린저밴드 상단 도달시 익절
        bb_position = stock_data.get('bb_position', 0.5)
        if bb_position > 0.7 and pnl_rate > 3.0:
            return True, "볼린저 상단 도달 익절"

        # 최대 보유: 7일
        if days_held >= 7:
            return True, f"보유 {days_held}일 경과"

        return False, ""


# ============================================================================
# 전략 6: MACD 크로스오버 전략 (MACD Crossover)
# ============================================================================
class MACDStrategy(DiverseTradingStrategy):
    """
    MACD 지표 기반 전략
    - MACD 골든크로스 매수
    - MACD 데드크로스 매도
    """

    def __init__(self):
        super().__init__("MACD크로스", "MACD 시그널 추종")
        self.max_positions = 5
        self.position_size_rate = 0.17

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        macd = stock_data.get('macd')
        macd_signal = stock_data.get('macd_signal')

        if macd is not None and macd_signal is not None and macd != 0 and macd_signal != 0:
            if macd <= macd_signal:
                return False

            macd_hist = stock_data.get('macd_histogram', 0)
            if macd_hist <= 0:
                return False

            price = stock_data.get('current_price', 0)
            ma20 = stock_data.get('ma20', price)
            if price < ma20:
                return False
        else:
            price_change = stock_data.get('price_change_percent', 0)
            if price_change < 2.0:
                return False

            volume_ratio = stock_data.get('volume_ratio', 1.0)
            if volume_ratio < 1.3:
                return False

            rsi = stock_data.get('rsi', 50)
            if not (45 <= rsi <= 65):
                return False

        return True

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # MACD 데드크로스 감지
        macd = stock_data.get('macd', 0)
        macd_signal = stock_data.get('macd_signal', 0)
        if macd < macd_signal and pnl_rate > -3.0:
            return True, f"MACD 데드크로스 {pnl_rate:.1f}%"

        # 익절: 10% 이상
        if pnl_rate >= 10.0:
            return True, f"MACD 익절 {pnl_rate:.1f}%"

        # 손절: -5% 이하
        if pnl_rate <= -5.0:
            return True, f"MACD 손절 {pnl_rate:.1f}%"

        # 최대 보유: 15일
        if days_held >= 15:
            return True, f"보유 {days_held}일 경과"

        return False, ""


# ============================================================================
# 전략 7: 역발상 전략 (Contrarian Strategy)
# ============================================================================
class ContrarianStrategy(DiverseTradingStrategy):
    """
    시장 공포/탐욕 지수를 역으로 활용
    - 공포 극대화 시점에 매수
    - 탐욕 극대화 시점에 매도
    """

    def __init__(self):
        super().__init__("역발상", "시장 감정의 반대편 베팅")
        self.max_positions = 4
        self.position_size_rate = 0.22
        self.fear_threshold = 30  # 공포지수 30 이하
        self.greed_threshold = 70  # 탐욕지수 70 이상

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        score = 0
        required_score = 2

        fear_greed_index = market_data.get('fear_greed_index', 50)
        if fear_greed_index <= self.fear_threshold:
            score += 2

        price_change_3d = stock_data.get('price_change_3day', 0)
        if price_change_3d < -5.0:
            score += 2
        elif price_change_3d < -3.0:
            score += 1

        volume_ratio = stock_data.get('volume_ratio', 1.0)
        if volume_ratio >= 1.3:
            score += 1

        market_cap = stock_data.get('market_cap', 0)
        if market_cap >= 100_000_000_000:
            score += 1

        price_change = stock_data.get('price_change_percent', 0)
        if -4.0 <= price_change < -1.0:
            score += 1

        return score >= required_score

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # 시장 탐욕 극대화 확인
        market_data = stock_data.get('market_data', {})
        fear_greed_index = market_data.get('fear_greed_index', 50)
        if fear_greed_index > self.greed_threshold and pnl_rate > 5.0:
            return True, f"탐욕 극대화 익절 {pnl_rate:.1f}%"

        # 익절: 18% 이상
        if pnl_rate >= 18.0:
            return True, f"역발상 익절 {pnl_rate:.1f}%"

        # 손절: -7% 이하
        if pnl_rate <= -7.0:
            return True, f"역발상 손절 {pnl_rate:.1f}%"

        # 최대 보유: 20일
        if days_held >= 20:
            return True, f"보유 {days_held}일 경과"

        return False, ""


# ============================================================================
# 전략 8: 섹터 로테이션 전략 (Sector Rotation)
# ============================================================================
class SectorRotationStrategy(DiverseTradingStrategy):
    """
    경기 사이클에 따른 섹터 순환 전략
    - 경기 확장기: IT, 경기소비재
    - 경기 둔화기: 필수소비재, 유틸리티
    """

    def __init__(self):
        super().__init__("섹터순환", "경기 사이클별 섹터 선택")
        self.max_positions = 6
        self.position_size_rate = 0.15

        # 경기 사이클별 선호 섹터
        self.cycle_sectors = {
            'expansion': ['IT', '경기소비재', '산업재'],
            'peak': ['에너지', '금융'],
            'contraction': ['필수소비재', '헬스케어', '유틸리티'],
            'trough': ['경기소비재', 'IT']
        }

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        # 현재 경기 사이클 확인
        cycle_phase = market_data.get('economic_cycle', 'expansion')
        preferred_sectors = self.cycle_sectors.get(cycle_phase, [])

        # 종목의 섹터 확인
        sector = stock_data.get('sector', '')
        if sector not in preferred_sectors:
            return False

        # 섹터 강도 확인 (섹터 상대 강도 > 1.05)
        sector_strength = stock_data.get('sector_relative_strength', 1.0)
        if sector_strength < 1.05:
            return False

        # 종목 모멘텀 확인
        price_change = stock_data.get('price_change_percent', 0)
        if price_change < 2.0:
            return False

        return True

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # 섹터 강도 약화 확인
        sector_strength = stock_data.get('sector_relative_strength', 1.0)
        if sector_strength < 0.95 and pnl_rate > 0:
            return True, f"섹터 약화 익절 {pnl_rate:.1f}%"

        # 익절: 12% 이상
        if pnl_rate >= 12.0:
            return True, f"섹터 익절 {pnl_rate:.1f}%"

        # 손절: -5% 이하
        if pnl_rate <= -5.0:
            return True, f"섹터 손절 {pnl_rate:.1f}%"

        # 최대 보유: 14일
        if days_held >= 14:
            return True, f"보유 {days_held}일 경과"

        return False, ""


# ============================================================================
# 전략 9: 급등주 추격 전략 (Hot Stock Chasing)
# ============================================================================
class HotStockStrategy(DiverseTradingStrategy):
    """
    단기 급등주 추격 전략
    - 당일 급등 종목 진입
    - 빠른 익절/손절
    """

    def __init__(self):
        super().__init__("급등추격", "당일 급등주 단타")
        self.max_positions = 8
        self.position_size_rate = 0.10
        self.min_price_surge = 3.0  # 최소 3% 상승 (완화: 5% → 3%)
        self.max_price_surge = 30.0  # 최대 30% 상승 (완화: 20% → 30%)

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        # 당일 급등 확인 (완화: 3% 이상)
        price_change = stock_data.get('price_change_percent', 0)
        if not (self.min_price_surge <= price_change <= self.max_price_surge):
            return False

        # 거래량 폭증 확인 (완화: 3배 → 2배)
        volume_ratio = stock_data.get('volume_ratio', 1.0)
        if volume_ratio < 2.0:
            return False

        # 시가총액 필터 (완화: 500억 → 100억) - 중소형주도 포함
        market_cap = stock_data.get('market_cap', 0)
        if market_cap < 10_000_000_000:
            return False

        # 52주 신고가 근접 조건 제거 (너무 엄격하여 제거)
        # 모든 급등주에 기회 제공

        return True

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # 빠른 익절: 6% 이상
        if pnl_rate >= 6.0:
            return True, f"급등 익절 {pnl_rate:.1f}%"

        # 빠른 손절: -3% 이하
        if pnl_rate <= -3.0:
            return True, f"급등 손절 {pnl_rate:.1f}%"

        # 당일 마감 (익절/손절 안된 경우)
        if days_held >= 1:
            return True, f"당일 마감 {pnl_rate:.1f}%"

        return False, ""


# ============================================================================
# 전략 10: 배당 성장주 전략 (Dividend Growth)
# ============================================================================
class DividendGrowthStrategy(DiverseTradingStrategy):
    """
    배당 성장주 장기 보유 전략
    - 배당 성장률 높은 종목
    - 안정적인 현금 흐름
    """

    def __init__(self):
        super().__init__("배당성장", "배당 증가 우량주 장기 보유")
        self.max_positions = 4
        self.position_size_rate = 0.23
        self.min_dividend_yield = 2.5  # 최소 2.5% 배당수익률
        self.min_dividend_growth = 5.0  # 배당 연평균 5% 성장

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        dividend_yield = stock_data.get('dividend_yield')
        dividend_growth = stock_data.get('dividend_growth_rate')
        eps = stock_data.get('eps')
        dps = stock_data.get('dps')
        debt_ratio = stock_data.get('debt_ratio')

        has_dividend_data = (dividend_yield is not None and dividend_yield > 0 and
                            dividend_growth is not None)

        if has_dividend_data:
            if dividend_yield < self.min_dividend_yield:
                return False

            if dividend_growth < self.min_dividend_growth:
                return False

            if eps and dps and dps > 0:
                if eps / dps < 1.5:
                    return False

            if debt_ratio is not None and debt_ratio > 100:
                return False
        else:
            price_change = stock_data.get('price_change_percent', 0)
            if not (1.0 <= price_change <= 4.0):
                return False

            volume_ratio = stock_data.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                return False

            rsi = stock_data.get('rsi', 50)
            if rsi < 40 or rsi > 60:
                return False

            market_cap = stock_data.get('market_cap', 0)
            if market_cap < 100000000000:
                return False

        return True

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # 배당 감소 확인 (배당 보호)
        dividend_growth = stock_data.get('dividend_growth_rate', 0)
        if dividend_growth < 0 and pnl_rate > -5.0:
            return True, f"배당 감소로 청산 {pnl_rate:.1f}%"

        # 목표 수익: 25% 이상 (장기 보유 목표)
        if pnl_rate >= 25.0:
            return True, f"배당 성장주 익절 {pnl_rate:.1f}%"

        # 손절: -10% 이하 (여유 있는 손절)
        if pnl_rate <= -10.0:
            return True, f"배당 성장주 손절 {pnl_rate:.1f}%"

        # 최대 보유: 60일 (장기 보유)
        if days_held >= 60:
            return True, f"보유 {days_held}일 경과"

        return False, ""


# ============================================================================
# v5.7.5: 전략 11 - 기관 추종 전략 (Institutional Following)
# ============================================================================
class InstitutionalFollowingStrategy(DiverseTradingStrategy):
    """
    기관/외국인 순매수 추종 전략 (Smart Money Following)
    - 기관과 외국인의 순매수가 강한 종목에 진입
    - 스마트머니를 따라가는 전략
    """

    def __init__(self):
        super().__init__("기관추종", "기관/외국인 순매수 추종")
        self.max_positions = 5
        self.position_size_rate = 0.17
        self.min_institutional_buy = 10_000_000  # 최소 천만원 순매수
        self.min_foreign_buy = 5_000_000  # 최소 오백만원 순매수

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        # 기관 순매수 확인
        institutional_net_buy = stock_data.get('institutional_net_buy', 0)
        if institutional_net_buy < self.min_institutional_buy:
            return False

        # 외국인 순매수 확인 (선택적 - 둘 중 하나라도 강하면 OK)
        foreign_net_buy = stock_data.get('foreign_net_buy', 0)

        # 기관 + 외국인 모두 순매수 시 강력한 신호
        if foreign_net_buy >= self.min_foreign_buy:
            # 매수세 강함 - 더 공격적으로
            pass

        # 증권사 순매수 추가 확인
        broker_buy_count = stock_data.get('top_broker_buy_count', 0)
        if broker_buy_count >= 2:
            # 증권사도 매수 중이면 긍정적
            pass

        # 가격 상승 확인 (최소 1% 이상)
        price_change = stock_data.get('change_rate', 0)
        if price_change < 1.0:
            return False

        return True

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # 익절: 8% 이상
        if pnl_rate >= 8.0:
            return True, f"기관추종 익절 {pnl_rate:.1f}%"

        # 손절: -4% 이하
        if pnl_rate <= -4.0:
            return True, f"기관추종 손절 {pnl_rate:.1f}%"

        # 기관/외국인 순매도 전환 시 청산
        institutional_net_buy = stock_data.get('institutional_net_buy', 0)
        foreign_net_buy = stock_data.get('foreign_net_buy', 0)

        if institutional_net_buy < -5_000_000 or foreign_net_buy < -5_000_000:
            return True, f"기관/외국인 순매도로 청산 {pnl_rate:.1f}%"

        # 최대 보유: 10일
        if days_held >= 10:
            return True, f"보유 {days_held}일 경과"

        return False, ""


# ============================================================================
# v5.7.5: 전략 12 - 거래량 + RSI 복합 전략 (Volume & RSI Combined)
# ============================================================================
class VolumeRSIStrategy(DiverseTradingStrategy):
    """
    거래량 급증 + RSI 과매도/적정 조합 전략
    - 거래량이 급증하면서 RSI가 과매도 또는 적정 구간에 있을 때 진입
    - 단기 반등을 노리는 전략
    """

    def __init__(self):
        super().__init__("거래량RSI", "거래량 급증 + RSI 조합")
        self.max_positions = 6
        self.position_size_rate = 0.16
        self.min_volume_ratio = 2.5  # 평균 거래량 대비 2.5배 이상
        self.rsi_lower_bound = 25  # RSI 25 이상 (너무 과매도는 피함)
        self.rsi_upper_bound = 60  # RSI 60 이하 (과열 구간 피함)

    def should_buy(self, stock_data: Dict, market_data: Dict, account: VirtualAccount) -> bool:
        if len(account.positions) >= self.max_positions:
            return False

        # 거래량 급증 확인
        volume = stock_data.get('volume', 0)
        avg_volume = stock_data.get('avg_volume')

        if avg_volume and avg_volume > 0:
            volume_ratio = volume / avg_volume
            if volume_ratio < self.min_volume_ratio:
                return False
        else:
            # avg_volume이 없으면 절대값 기준
            if volume < 1_000_000:  # 최소 100만주
                return False

        # RSI 확인
        rsi = stock_data.get('rsi')
        if rsi is not None:
            if not (self.rsi_lower_bound <= rsi <= self.rsi_upper_bound):
                return False
        else:
            # RSI가 없으면 가격 상승률로 대체 (과열 아닌지 확인)
            price_change = stock_data.get('change_rate', 0)
            if price_change > 10.0:  # 10% 이상 급등은 위험
                return False

        # 체결강도 확인 (매수 우위)
        execution_intensity = stock_data.get('execution_intensity')
        if execution_intensity and execution_intensity < 80:
            return False

        # 가격 상승 중인지 확인 (최소 0.5% 이상)
        price_change = stock_data.get('change_rate', 0)
        if price_change < 0.5:
            return False

        return True

    def should_sell(self, position: VirtualPosition, current_price: int,
                    stock_data: Dict, days_held: int) -> tuple[bool, str]:
        position.update_price(current_price)
        pnl_rate = position.unrealized_pnl_rate

        # 익절: 7% 이상
        if pnl_rate >= 7.0:
            return True, f"거래량RSI 익절 {pnl_rate:.1f}%"

        # 손절: -3.5% 이하 (빠른 손절)
        if pnl_rate <= -3.5:
            return True, f"거래량RSI 손절 {pnl_rate:.1f}%"

        # RSI 과열 구간 진입 시 청산
        rsi = stock_data.get('rsi')
        if rsi and rsi > 75 and pnl_rate > 3.0:
            return True, f"RSI 과열 청산 {pnl_rate:.1f}%"

        # 거래량 급감 시 청산
        volume = stock_data.get('volume', 0)
        avg_volume = stock_data.get('avg_volume')
        if avg_volume and avg_volume > 0:
            volume_ratio = volume / avg_volume
            if volume_ratio < 0.8 and pnl_rate < 2.0:
                return True, f"거래량 급감 청산 {pnl_rate:.1f}%"

        # 최대 보유: 5일 (단기 전략)
        if days_held >= 5:
            return True, f"보유 {days_held}일 경과"

        return False, ""


# ============================================================================
# 전략 팩토리
# ============================================================================
def create_all_diverse_strategies() -> list:
    """v5.7.5: 12가지 다양한 전략 생성 (10개 → 12개 확장)"""
    return [
        MomentumStrategy(),
        MeanReversionStrategy(),
        BreakoutStrategy(),
        ValueInvestingStrategy(),
        SwingTradingStrategy(),
        MACDStrategy(),
        ContrarianStrategy(),
        SectorRotationStrategy(),
        HotStockStrategy(),
        DividendGrowthStrategy(),
        # v5.7.5: 2개 신규 전략 추가
        InstitutionalFollowingStrategy(),
        VolumeRSIStrategy()
    ]


def get_strategy_descriptions() -> Dict[str, str]:
    """전략별 상세 설명 (v5.7.5: 12개)"""
    return {
        "모멘텀추세": "강한 상승 추세를 따라가는 전략. 거래량 급증 + 주가 상승 시 진입.",
        "평균회귀": "과매도 구간 반등 포착. RSI 30 이하에서 진입.",
        "돌파매매": "52주 신고가 돌파 시 진입. 큰 수익 추구.",
        "가치투자": "저평가 우량주 장기 보유. PER/PBR 낮고 배당 높은 종목.",
        "스윙매매": "단기 변동성 활용. 볼린저밴드 하단 매수, 상단 매도.",
        "MACD크로스": "MACD 지표 기반. 골든크로스 매수, 데드크로스 매도.",
        "역발상": "시장 감정의 반대편 베팅. 공포 시 매수, 탐욕 시 매도.",
        "섹터순환": "경기 사이클에 따른 섹터 선택. 경기 확장기엔 IT, 둔화기엔 필수소비재.",
        "급등추격": "당일 급등주 단타. 빠른 익절/손절.",
        "배당성장": "배당 성장주 장기 보유. 안정적 현금 흐름.",
        # v5.7.5: 신규 전략 2개
        "기관추종": "기관/외국인 순매수 추종. 스마트머니 따라가기.",
        "거래량RSI": "거래량 급증 + RSI 과매도/적정 조합. 단기 반등 포착."
    }
