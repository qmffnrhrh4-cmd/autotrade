"""
Mock Analyzer for Testing
AI 분석기가 사용 불가능할 때 사용하는 대체 분석기

Author: AutoTrade Pro
Version: 1.0

Note: This analyzer provides reasonable mock responses based on
technical indicators when real AI (Gemini) is not available.
It does NOT use random numbers or fake data - instead it uses
rule-based analysis based on actual stock data.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MockAnalyzer:
    """
    Mock Analyzer for when Gemini API is unavailable.

    Uses rule-based technical analysis instead of AI.
    This is NOT fake data - it's a simplified but real analysis.
    """

    def __init__(self):
        self.name = "MockAnalyzer"
        logger.warning("MockAnalyzer initialized - AI features limited. Set GEMINI_API_KEY for full AI analysis.")

    def analyze_stock(
        self,
        stock_data: Dict[str, Any],
        score_info: Optional[Dict[str, Any]] = None,
        portfolio_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze stock using rule-based technical analysis.

        Args:
            stock_data: Stock information including price, indicators
            score_info: Scoring system results
            portfolio_info: Current portfolio status

        Returns:
            Analysis result with signal and reasoning
        """
        stock_code = stock_data.get('code', 'UNKNOWN')
        stock_name = stock_data.get('name', stock_code)

        # Extract technical indicators from stock_data
        current_price = stock_data.get('current_price', 0)
        rsi = stock_data.get('rsi', 50)
        macd = stock_data.get('macd', 0)
        macd_signal = stock_data.get('macd_signal', 0)
        ma5 = stock_data.get('ma5', current_price)
        ma20 = stock_data.get('ma20', current_price)
        volume_ratio = stock_data.get('volume_ratio', 1.0)

        # Get score if available
        total_score = 0
        if score_info:
            total_score = score_info.get('total_score', 0)

        # Rule-based signal determination
        signal = 'hold'
        confidence = 0.5
        reasons = []

        # RSI analysis
        if rsi < 30:
            reasons.append(f"RSI 과매도 ({rsi:.1f})")
            confidence += 0.1
        elif rsi > 70:
            reasons.append(f"RSI 과매수 ({rsi:.1f})")
            confidence -= 0.1

        # MACD analysis
        macd_diff = macd - macd_signal
        if macd_diff > 0:
            reasons.append("MACD 골든크로스")
            confidence += 0.1
        elif macd_diff < 0:
            reasons.append("MACD 데드크로스")
            confidence -= 0.1

        # Moving average analysis
        if current_price > ma5 > ma20:
            reasons.append("상승 추세 (MA5 > MA20)")
            confidence += 0.1
        elif current_price < ma5 < ma20:
            reasons.append("하락 추세 (MA5 < MA20)")
            confidence -= 0.1

        # Volume analysis
        if volume_ratio > 2.0:
            reasons.append(f"거래량 급증 ({volume_ratio:.1f}x)")
            confidence += 0.05

        # Score-based adjustment
        if total_score >= 350:
            reasons.append(f"높은 종합 점수 ({total_score})")
            confidence += 0.15
        elif total_score <= 200:
            reasons.append(f"낮은 종합 점수 ({total_score})")
            confidence -= 0.15

        # Determine final signal
        confidence = max(0.1, min(0.9, confidence))

        if confidence >= 0.65:
            signal = 'buy'
        elif confidence <= 0.35:
            signal = 'sell'
        else:
            signal = 'hold'

        # Build reasoning text
        reasoning = f"[규칙 기반 분석] {stock_name} ({stock_code})\n"
        reasoning += "분석 근거:\n"
        for i, reason in enumerate(reasons, 1):
            reasoning += f"  {i}. {reason}\n"
        reasoning += f"\n결론: {signal.upper()} (신뢰도: {confidence:.0%})"

        return {
            'signal': signal,
            'confidence': confidence,
            'score': int(confidence * 100),
            'reasoning': reasoning,
            'analysis_type': 'rule_based',
            'timestamp': datetime.now().isoformat(),
            'details': {
                'rsi': rsi,
                'macd': macd,
                'macd_signal': macd_signal,
                'ma5': ma5,
                'ma20': ma20,
                'volume_ratio': volume_ratio,
                'total_score': total_score,
                'reasons': reasons
            },
            'warning': 'AI 분석 불가 - 규칙 기반 분석 사용 중. GEMINI_API_KEY 설정 권장.'
        }

    def is_available(self) -> bool:
        """Check if analyzer is available"""
        return True  # Mock analyzer is always available

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'name': 'MockAnalyzer',
            'type': 'rule_based',
            'version': '1.0',
            'description': 'Rule-based technical analysis (AI fallback)',
            'capabilities': ['basic_analysis', 'signal_generation'],
            'limitations': ['no_sentiment', 'no_news_analysis', 'no_deep_learning']
        }


# Singleton instance
_mock_analyzer_instance = None


def get_mock_analyzer() -> MockAnalyzer:
    """Get MockAnalyzer singleton instance"""
    global _mock_analyzer_instance
    if _mock_analyzer_instance is None:
        _mock_analyzer_instance = MockAnalyzer()
    return _mock_analyzer_instance
