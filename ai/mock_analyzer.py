"""
ai/mock_analyzer.py
Mock AI 분석기 (테스트/개발용)
"""
import logging
import random
import time
from typing import Dict, Any
from .base_analyzer import BaseAnalyzer

logger = logging.getLogger(__name__)


class MockAnalyzer(BaseAnalyzer):
    """
    Mock AI 분석기
    
    실제 AI API 없이 테스트/개발용으로 사용
    랜덤하지만 그럴듯한 분석 결과 생성
    """
    
    def __init__(self, delay: float = 0.5):
        """
        Mock 분석기 초기화
        
        Args:
            delay: 응답 지연 시간 (초)
        """
        super().__init__("MockAnalyzer")
        self.delay = delay
        logger.info(f"MockAnalyzer 초기화 (지연: {delay}초)")
    
    def initialize(self) -> bool:
        """
        Mock 분석기 초기화
        
        Returns:
            항상 True
        """
        time.sleep(0.1)
        self.is_initialized = True
        logger.info("Mock 분석기 초기화 성공")
        return True
    
    def analyze_stock(
        self,
        stock_data: Dict[str, Any],
        analysis_type: str = 'comprehensive',
        **kwargs
    ) -> Dict[str, Any]:
        """
        종목 분석 (Mock)

        Args:
            stock_data: 종목 데이터
            analysis_type: 분석 유형
            **kwargs: 추가 파라미터 (score_info 등)

        Returns:
            Mock 분석 결과
        """
        # 초기화 확인
        if not self.is_initialized:
            self.initialize()
        
        # 데이터 검증
        is_valid, msg = self.validate_stock_data(stock_data)
        if not is_valid:
            return self._get_error_result(msg)
        
        # 지연 시뮬레이션
        time.sleep(self.delay)
        
        # 통계 업데이트
        self.update_statistics(True, self.delay)
        
        # Mock 결과 생성
        stock_code = stock_data.get('stock_code', '')
        stock_name = stock_data.get('stock_name', '')
        current_price = stock_data.get('current_price', 0)
        change_rate = stock_data.get('change_rate', 0)
        
        # 등락률에 따른 기본 점수
        base_score = 5.0
        if change_rate > 5:
            base_score = 8.0
        elif change_rate > 3:
            base_score = 7.0
        elif change_rate > 1:
            base_score = 6.0
        elif change_rate < -3:
            base_score = 3.0
        elif change_rate < -1:
            base_score = 4.0
        
        # 랜덤 변동 추가
        score = base_score + random.uniform(-1, 1)
        score = max(0, min(10, score))
        
        # 신호 결정
        if score >= 7.5:
            signal = 'buy'
            confidence = 'High'
        elif score >= 6.5:
            signal = 'buy'
            confidence = 'Medium'
        elif score >= 4.5:
            signal = 'hold'
            confidence = 'Medium'
        else:
            signal = 'sell'
            confidence = 'Low'
        
        # 이유 생성
        reasons = self._generate_reasons(signal, stock_data)
        
        # 리스크 생성
        risks = self._generate_risks(stock_data)
        
        result = {
            'score': round(score, 2),
            'signal': signal,
            'confidence': confidence,
            'recommendation': self._get_recommendation(signal, stock_name),
            'reasons': reasons,
            'risks': risks,
            'target_price': int(current_price * (1 + random.uniform(0.05, 0.15))),
            'stop_loss_price': int(current_price * (1 - random.uniform(0.03, 0.07))),
            'analysis_text': f"Mock 분석 결과 (점수: {score:.2f})",
            'is_mock': True,
        }
        
        logger.info(
            f"Mock 분석 완료: {stock_code} "
            f"(점수: {score:.2f}, 신호: {signal}, 신뢰도: {confidence})"
        )
        
        return result
    
    def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        시장 분석 (Mock)
        
        Args:
            market_data: 시장 데이터
        
        Returns:
            Mock 시장 분석 결과
        """
        if not self.is_initialized:
            self.initialize()
        
        time.sleep(self.delay)
        self.update_statistics(True, self.delay)
        
        # 랜덤 시장 심리
        sentiments = ['bullish', 'bearish', 'neutral']
        sentiment = random.choice(sentiments)
        
        # 심리에 따른 점수
        if sentiment == 'bullish':
            score = random.uniform(6.5, 8.5)
        elif sentiment == 'bearish':
            score = random.uniform(2.0, 4.5)
        else:
            score = random.uniform(4.5, 6.5)
        
        result = {
            'market_sentiment': sentiment,
            'market_score': round(score, 2),
            'analysis': f"Mock 시장 분석: {sentiment} 시장",
            'recommendations': [
                "Mock 추천 사항 1",
                "Mock 추천 사항 2",
                "Mock 추천 사항 3",
            ],
            'is_mock': True,
        }
        
        logger.info(f"Mock 시장 분석 완료 (심리: {sentiment}, 점수: {score:.2f})")
        
        return result
    
    def analyze_portfolio(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        포트폴리오 분석 (Mock)
        
        Args:
            portfolio_data: 포트폴리오 데이터
        
        Returns:
            Mock 포트폴리오 분석 결과
        """
        if not self.is_initialized:
            self.initialize()
        
        time.sleep(self.delay)
        self.update_statistics(True, self.delay)
        
        result = {
            'analysis': "Mock 포트폴리오 분석 결과",
            'strengths': [
                "분산 투자가 잘 되어 있습니다",
                "수익률이 양호합니다",
            ],
            'weaknesses': [
                "현금 비중이 낮습니다",
                "일부 종목 비중이 높습니다",
            ],
            'recommendations': [
                "현금 비중을 늘리세요",
                "손실 종목을 정리하세요",
                "리밸런싱을 고려하세요",
            ],
            'is_mock': True,
        }
        
        logger.info("Mock 포트폴리오 분석 완료")
        
        return result
    
    # ==================== Mock 데이터 생성 ====================
    
    def _generate_reasons(
        self,
        signal: str,
        stock_data: Dict[str, Any]
    ) -> list:
        """매수/매도 이유 생성"""
        change_rate = stock_data.get('change_rate', 0)
        volume = stock_data.get('volume', 0)
        
        if signal == 'buy':
            reasons = [
                f"강한 상승 모멘텀 ({change_rate:+.2f}%)",
                f"높은 거래량 ({volume:,}주)",
                "기술적 지표 긍정적",
            ]
        elif signal == 'sell':
            reasons = [
                f"약한 하락 추세 ({change_rate:+.2f}%)",
                "거래량 감소 추세",
                "리스크 관리 필요",
            ]
        else:
            reasons = [
                "횡보 구간 진입",
                "관망 필요",
                "추가 신호 대기",
            ]
        
        return reasons
    
    def _generate_risks(self, stock_data: Dict[str, Any]) -> list:
        """리스크 생성"""
        risks = [
            "시장 변동성 위험",
            "단기 급등/급락 가능성",
        ]
        
        change_rate = stock_data.get('change_rate', 0)
        
        if abs(change_rate) > 10:
            risks.append("높은 변동성 주의")
        
        return risks
    
    def _get_recommendation(self, signal: str, stock_name: str) -> str:
        """추천 문구 생성"""
        if signal == 'buy':
            return f"{stock_name} 매수 추천"
        elif signal == 'sell':
            return f"{stock_name} 매도 고려"
        else:
            return f"{stock_name} 보유 또는 관망"
    
    def _get_error_result(self, error_msg: str) -> Dict[str, Any]:
        """에러 결과 반환"""
        return {
            'error': True,
            'error_message': error_msg,
            'score': 5.0,
            'signal': 'hold',
            'confidence': 'Low',
            'recommendation': 'Mock 분석 실패',
            'reasons': [error_msg],
            'risks': [],
            'is_mock': True,
        }


__all__ = ['MockAnalyzer']