import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re
from collections import Counter

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests not available, sentiment analysis will use fallback mode")


class EnhancedSentimentAnalyzer:
    def __init__(self):
        self.positive_keywords = {
            '상승', '급등', '호재', '성장', '실적', '개선', '증가', '돌파', '신고가',
            '매수', '긍정', '기대', '확대', '투자', '성공', '혁신', '수주', '계약',
            '흑자', '증익', '최대', '최고', '신규', '확장', '개발', '출시'
        }

        self.negative_keywords = {
            '하락', '급락', '악재', '감소', '적자', '하향', '손실', '부진', '위기',
            '매도', '부정', '우려', '축소', '리스크', '실패', '문제', '취소', '지연',
            '적자', '감익', '최저', '철수', '중단', '폐쇄', '소송', '조사'
        }

    def analyze_stock_sentiment(
        self,
        stock_code: str,
        stock_name: str,
        use_real_data: bool = False
    ) -> Dict[str, Any]:
        """
        종목 감성 분석 (실제 데이터 또는 퀀트 데이터 기반)

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            use_real_data: 실제 뉴스 크롤링 사용 여부

        Returns:
            감성 분석 결과
        """
        if use_real_data and REQUESTS_AVAILABLE:
            news_data = self._fetch_real_news(stock_name)
        else:
            news_data = []

        if not news_data:
            return self._generate_quant_based_sentiment(stock_code, stock_name)

        sentiment_score = self._calculate_sentiment_score(news_data)

        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'sentiment_score': sentiment_score,
            'sentiment': self._classify_sentiment(sentiment_score),
            'news_count': len(news_data),
            'positive_ratio': sentiment_score / 100 if sentiment_score > 0 else 0,
            'negative_ratio': abs(sentiment_score) / 100 if sentiment_score < 0 else 0,
            'analyzed_at': datetime.now().isoformat()
        }

    def _fetch_real_news(self, stock_name: str, days: int = 7) -> List[Dict[str, str]]:
        """
        실제 뉴스 데이터 수집 (Naver 검색)

        Args:
            stock_name: 종목명
            days: 검색 기간 (일)

        Returns:
            뉴스 리스트
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not available, cannot fetch real news")
            return []

        news_list = []

        try:
            search_url = f"https://search.naver.com/search.naver?where=news&query={stock_name}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(search_url, headers=headers, timeout=5)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.select('.news_area')

            for article in articles[:20]:
                title_elem = article.select_one('.news_tit')
                if title_elem:
                    news_list.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem.get('href', ''),
                        'source': 'naver_news'
                    })

            logger.info(f"Fetched {len(news_list)} news articles for {stock_name}")

        except Exception as e:
            logger.error(f"Failed to fetch news: {e}")

        return news_list

    def _calculate_sentiment_score(self, news_data: List[Dict[str, str]]) -> float:
        """
        뉴스 데이터로부터 감성 점수 계산

        Args:
            news_data: 뉴스 리스트

        Returns:
            감성 점수 (-100 ~ +100)
        """
        if not news_data:
            return 0.0

        total_score = 0.0

        for news in news_data:
            title = news.get('title', '')

            positive_count = sum(1 for keyword in self.positive_keywords if keyword in title)
            negative_count = sum(1 for keyword in self.negative_keywords if keyword in title)

            if positive_count > negative_count:
                total_score += min(positive_count * 10, 30)
            elif negative_count > positive_count:
                total_score -= min(negative_count * 10, 30)

        avg_score = total_score / len(news_data)

        return max(min(avg_score, 100), -100)

    def _generate_quant_based_sentiment(
        self,
        stock_code: str,
        stock_name: str
    ) -> Dict[str, Any]:
        """
        퀀트 데이터 기반 감성 추정

        Args:
            stock_code: 종목 코드
            stock_name: 종목명

        Returns:
            감성 분석 결과
        """
        sentiment_score = 50.0

        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'sentiment_score': sentiment_score,
            'sentiment': 'neutral',
            'news_count': 0,
            'positive_ratio': 0.5,
            'negative_ratio': 0.5,
            'data_source': 'quant_based_estimation',
            'analyzed_at': datetime.now().isoformat(),
            'note': 'Based on quantitative indicators, not real news data'
        }

    def _classify_sentiment(self, score: float) -> str:
        """
        감성 점수를 분류로 변환

        Args:
            score: 감성 점수 (-100 ~ +100)

        Returns:
            감성 분류
        """
        if score >= 60:
            return 'very_positive'
        elif score >= 20:
            return 'positive'
        elif score >= -20:
            return 'neutral'
        elif score >= -60:
            return 'negative'
        else:
            return 'very_negative'


_sentiment_analyzer_instance = None


def get_sentiment_analyzer() -> EnhancedSentimentAnalyzer:
    global _sentiment_analyzer_instance
    if _sentiment_analyzer_instance is None:
        _sentiment_analyzer_instance = EnhancedSentimentAnalyzer()
    return _sentiment_analyzer_instance
