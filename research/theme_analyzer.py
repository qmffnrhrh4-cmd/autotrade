"""
research/theme_analyzer.py
테마 분석
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ThemeAnalyzer:
    """
    테마 분석 클래스
    
    주요 기능:
    - 상승 테마 발굴
    - 테마별 종목 분석
    - 테마 투자 전략
    """
    
    def __init__(self, theme_api):
        """
        Args:
            theme_api: ThemeAPI 인스턴스
        """
        self.theme_api = theme_api
        logger.info("ThemeAnalyzer 초기화")
    
    def find_hot_themes(
        self,
        limit: int = 10,
        min_profit_rate: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        핫 테마 발굴
        
        Args:
            limit: 조회 개수
            min_profit_rate: 최소 수익률 (%)
        
        Returns:
            핫 테마 리스트
        """
        try:
            # 상위 테마 조회
            themes = self.theme_api.get_top_themes(limit=limit * 2)
            
            # 필터링
            hot_themes = []
            for theme in themes:
                profit_rate = float(theme.get('dt_prft_rt', '0').replace('+', ''))
                
                if profit_rate >= min_profit_rate:
                    hot_themes.append({
                        'theme_code': theme.get('thema_grp_cd'),
                        'theme_name': theme.get('thema_nm'),
                        'profit_rate': profit_rate,
                        'change_rate': float(theme.get('flu_rt', '0').replace('+', '')),
                        'stock_count': int(float(theme.get('stk_num', 0)),
                        'rising_count': int(float(theme.get('rising_stk_num', 0)),
                        'main_stock': theme.get('main_stk', ''),
                    })
            
            # 수익률 순 정렬
            hot_themes.sort(key=lambda x: x['profit_rate'], reverse=True)
            
            logger.info(f"핫 테마 {len(hot_themes[:limit])}개 발굴")
            return hot_themes[:limit]
            
        except Exception as e:
            logger.error(f"핫 테마 발굴 실패: {e}")
            return []
    
    def analyze_theme_stocks(
        self,
        theme_code: str,
        theme_name: str = ''
    ) -> Dict[str, Any]:
        """
        테마 구성종목 분석
        
        Args:
            theme_code: 테마코드
            theme_name: 테마명
        
        Returns:
            분석 결과
        """
        try:
            # 테마 구성종목 조회
            theme_data = self.theme_api.get_theme_stocks(theme_code)
            stocks = theme_data.get('stocks', [])
            
            if not stocks:
                return {}
            
            # 상승 종목 필터링
            rising_stocks = [
                s for s in stocks
                if s.get('flu_sig') == '2' and float(s.get('flu_rt', '0')) > 0
            ]
            
            # 거래량 상위 종목
            stocks_sorted = sorted(
                stocks,
                key=lambda x: int(float(x.get('acc_trde_qty', 0)),
                reverse=True
            )
            
            result = {
                'theme_code': theme_code,
                'theme_name': theme_name,
                'total_stocks': len(stocks),
                'rising_stocks': len(rising_stocks),
                'theme_change_rate': float(theme_data.get('flu_rt', '0')),
                'theme_profit_rate': float(theme_data.get('dt_prft_rt', '0')),
                'top_volume_stocks': stocks_sorted[:5],
                'top_rising_stocks': sorted(
                    rising_stocks,
                    key=lambda x: float(x.get('flu_rt', '0')),
                    reverse=True
                )[:5]
            }
            
            logger.info(f"{theme_name} 테마 분석 완료")
            return result
            
        except Exception as e:
            logger.error(f"테마 분석 실패: {e}")
            return {}
    
    def get_theme_investment_candidates(
        self,
        min_theme_profit: float = 10.0,
        min_stock_change: float = 2.0,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        테마 기반 투자 후보 종목 추출
        
        Args:
            min_theme_profit: 최소 테마 수익률
            min_stock_change: 최소 종목 등락률
            limit: 종목 개수
        
        Returns:
            투자 후보 종목 리스트
        """
        candidates = []
        
        try:
            # 핫 테마 발굴
            hot_themes = self.find_hot_themes(limit=10, min_profit_rate=min_theme_profit)
            
            # 각 테마별 우량주 추출
            for theme in hot_themes:
                theme_code = theme['theme_code']
                theme_name = theme['theme_name']
                
                analysis = self.analyze_theme_stocks(theme_code, theme_name)
                
                if not analysis:
                    continue
                
                # 상승 종목 중 조건 충족 종목 추출
                for stock in analysis.get('top_rising_stocks', []):
                    change_rate = float(stock.get('flu_rt', '0'))
                    
                    if change_rate >= min_stock_change:
                        candidates.append({
                            'stock_code': stock.get('stk_cd', ''),
                            'stock_name': stock.get('stk_nm', ''),
                            'current_price': int(float(stock.get('cur_prc', 0)),
                            'change_rate': change_rate,
                            'volume': int(float(stock.get('acc_trde_qty', 0)),
                            'theme_name': theme_name,
                            'theme_profit_rate': theme['profit_rate'],
                        })
            
            # 등락률 순 정렬
            candidates.sort(key=lambda x: x['change_rate'], reverse=True)
            
            logger.info(f"투자 후보 종목 {len(candidates[:limit])}개 추출")
            return candidates[:limit]
            
        except Exception as e:
            logger.error(f"투자 후보 추출 실패: {e}")
            return []


__all__ = ['ThemeAnalyzer']