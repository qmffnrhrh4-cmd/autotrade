"""
ai/base_analyzer.py
AI 분석기 기본 인터페이스
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """
    AI 분석기 기본 추상 클래스
    
    모든 AI 분석기는 이 인터페이스를 구현해야 함
    """
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        """
        분석기 초기화
        
        Args:
            name: 분석기 이름
            config: 설정
        """
        self.name = name
        self.config = config or {}
        self.is_initialized = False
        
        # 통계
        self.stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'avg_response_time': 0.0,
        }
        
        logger.info(f"{self.name} 분석기 초기화")
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        분석기 초기화 (추상 메서드)
        
        Returns:
            초기화 성공 여부
        """
        pass
    
    @abstractmethod
    def analyze_stock(
        self,
        stock_data: Dict[str, Any],
        analysis_type: str = 'comprehensive',
        **kwargs
    ) -> Dict[str, Any]:
        """
        종목 분석 (추상 메서드)

        Args:
            stock_data: 종목 데이터
            analysis_type: 분석 유형 ('comprehensive', 'quick', 'technical', 'fundamental')
            **kwargs: 추가 파라미터 (score_info, portfolio_info 등)

        Returns:
            분석 결과
            {
                'score': 7.5,                    # 투자 점수 (0~10)
                'signal': 'buy' | 'sell' | 'hold',
                'confidence': 'Low' | 'Medium' | 'High',
                'recommendation': '매수 추천',
                'reasons': ['이유1', '이유2', ...],
                'risks': ['리스크1', '리스크2', ...],
                'target_price': 75000,
                'stop_loss_price': 65000,
            }
        """
        pass
    
    @abstractmethod
    def analyze_market(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        시장 분석 (추상 메서드)
        
        Args:
            market_data: 시장 데이터
        
        Returns:
            시장 분석 결과
            {
                'market_sentiment': 'bullish' | 'bearish' | 'neutral',
                'market_score': 6.5,
                'analysis': '시장 분석 내용',
                'recommendations': ['추천 사항'],
            }
        """
        pass
    
    @abstractmethod
    def analyze_portfolio(
        self,
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        포트폴리오 분석 (추상 메서드)
        
        Args:
            portfolio_data: 포트폴리오 데이터
        
        Returns:
            포트폴리오 분석 결과
        """
        pass
    
    # ==================== 공통 메서드 ====================
    
    def is_ready(self) -> bool:
        """
        분석기 준비 상태 확인
        
        Returns:
            준비 상태
        """
        return self.is_initialized
    
    def validate_stock_data(self, stock_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        종목 데이터 검증
        
        Args:
            stock_data: 종목 데이터
        
        Returns:
            (검증 통과 여부, 메시지)
        """
        required_fields = ['stock_code', 'current_price', 'change_rate']
        
        for field in required_fields:
            if field not in stock_data:
                return False, f"필수 필드 누락: {field}"
        
        if stock_data.get('current_price', 0) <= 0:
            return False, "유효하지 않은 현재가"
        
        return True, "검증 통과"
    
    def update_statistics(self, success: bool, response_time: float = 0.0):
        """
        통계 업데이트
        
        Args:
            success: 분석 성공 여부
            response_time: 응답 시간 (초)
        """
        self.stats['total_analyses'] += 1
        
        if success:
            self.stats['successful_analyses'] += 1
        else:
            self.stats['failed_analyses'] += 1
        
        # 평균 응답 시간 계산
        total = self.stats['total_analyses']
        current_avg = self.stats['avg_response_time']
        self.stats['avg_response_time'] = ((current_avg * (total - 1)) + response_time) / total
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        분석기 통계 조회
        
        Returns:
            통계 정보
        """
        total = self.stats['total_analyses']
        success_rate = (self.stats['successful_analyses'] / total * 100) if total > 0 else 0
        
        return {
            'name': self.name,
            'total_analyses': total,
            'successful_analyses': self.stats['successful_analyses'],
            'failed_analyses': self.stats['failed_analyses'],
            'success_rate': round(success_rate, 2),
            'avg_response_time': round(self.stats['avg_response_time'], 2),
        }
    
    def reset_statistics(self):
        """통계 초기화"""
        self.stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'avg_response_time': 0.0,
        }
        logger.info(f"{self.name} 통계 초기화")
    
    def get_config(self, key: str, default=None):
        """설정 값 조회"""
        return self.config.get(key, default)
    
    def update_config(self, key: str, value: Any):
        """설정 값 업데이트"""
        self.config[key] = value
        logger.info(f"{self.name} 설정 업데이트: {key} = {value}")
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}', initialized={self.is_initialized})>"


__all__ = ['BaseAnalyzer']