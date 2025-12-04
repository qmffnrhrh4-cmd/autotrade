"""
News Sentiment Analysis Module v6.0
실시간 뉴스 크롤링 및 AI 감정 분석
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup
import json


class NewsAggregator:
    """뉴스 수집기"""

    def __init__(self):
        self.sources = {
            'naver_finance': 'https://finance.naver.com',
            'daum_finance': 'https://finance.daum.net',
        }

    async def fetch_stock_news(self, stock_code: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        종목 관련 뉴스 수집

        Args:
            stock_code: 종목 코드
            limit: 최대 뉴스 개수

        Returns:
            뉴스 리스트
        """

        news_list = []

        # Naver Finance 뉴스
        naver_news = await self._fetch_naver_news(stock_code, limit)
        news_list.extend(naver_news)

        # Daum Finance 뉴스
        daum_news = await self._fetch_daum_news(stock_code, limit)
        news_list.extend(daum_news)

        # 중복 제거 (제목 기준)
        unique_news = {}
        for news in news_list:
            title = news['title']
            if title not in unique_news:
                unique_news[title] = news

        # 최신순 정렬
        sorted_news = sorted(
            unique_news.values(),
            key=lambda x: x['published'],
            reverse=True
        )

        return sorted_news[:limit]

    async def _fetch_naver_news(self, stock_code: str, limit: int) -> List[Dict[str, Any]]:
        """Naver Finance 뉴스 크롤링"""

        try:
            url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}&page=1"

            response = await asyncio.to_thread(requests.get, url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            news_list = []
            news_items = soup.select('.newsList .articleSubject')

            for item in news_items[:limit]:
                link = item.find('a')
                if link:
                    title = link.get('title', '').strip()
                    href = 'https://finance.naver.com' + link.get('href', '')

                    news_list.append({
                        'title': title,
                        'link': href,
                        'source': 'naver',
                        'published': datetime.now().isoformat()
                    })

            return news_list

        except Exception as e:
            print(f"Naver 뉴스 크롤링 실패: {e}")
            return []

    async def _fetch_daum_news(self, stock_code: str, limit: int) -> List[Dict[str, Any]]:
        """Daum Finance 뉴스 크롤링"""

        try:
            # Daum은 종목 코드 형식이 다를 수 있음 (A005930)
            if not stock_code.startswith('A'):
                stock_code = 'A' + stock_code

            url = f"https://finance.daum.net/quotes/{stock_code}#news"

            response = await asyncio.to_thread(requests.get, url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            news_list = []
            news_items = soup.select('.newsList .tit')

            for item in news_items[:limit]:
                link = item.find('a')
                if link:
                    title = link.text.strip()
                    href = link.get('href', '')

                    news_list.append({
                        'title': title,
                        'link': href,
                        'source': 'daum',
                        'published': datetime.now().isoformat()
                    })

            return news_list

        except Exception as e:
            print(f"Daum 뉴스 크롤링 실패: {e}")
            return []


class SentimentAnalyzer:
    """감정 분석기"""

    def __init__(self, ai_analyzer=None):
        """
        초기화

        Args:
            ai_analyzer: UnifiedAnalyzer 인스턴스
        """
        self.ai_analyzer = ai_analyzer

        # 감정 키워드 사전 (간단한 규칙 기반)
        self.positive_keywords = [
            '상승', '급등', '호재', '투자', '확대', '성장', '증가',
            '개선', '긍정', '매수', '강세', '실적', '호조', '수주'
        ]

        self.negative_keywords = [
            '하락', '급락', '악재', '위기', '감소', '축소', '부진',
            '하향', '부정', '매도', '약세', '적자', '손실', '리스크'
        ]

    async def analyze_news_sentiment(
        self,
        news_list: List[Dict[str, Any]],
        use_ai: bool = True
    ) -> Dict[str, Any]:
        """
        뉴스 감정 분석

        Args:
            news_list: 뉴스 리스트
            use_ai: AI 분석 사용 여부

        Returns:
            감정 분석 결과
        """

        if not news_list:
            return {
                'positive': 0,
                'neutral': 100,
                'negative': 0,
                'keywords': [],
                'summary': '뉴스 없음'
            }

        if use_ai and self.ai_analyzer:
            # AI 기반 감정 분석
            return await self._ai_sentiment_analysis(news_list)
        else:
            # 규칙 기반 감정 분석
            return self._rule_based_sentiment_analysis(news_list)

    async def _ai_sentiment_analysis(self, news_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """AI 기반 감정 분석"""

        titles = [news['title'] for news in news_list[:10]]  # 최대 10개

        prompt = f"""
다음 뉴스 제목들을 분석하여 전체적인 감정(sentiment)을 평가하세요:

{json.dumps(titles, ensure_ascii=False, indent=2)}

다음 형식으로 답변하세요:

```json
{{
  "positive": 긍정 뉴스 비율 (0-100),
  "neutral": 중립 뉴스 비율 (0-100),
  "negative": 부정 뉴스 비율 (0-100),
  "keywords": ["주요", "키워드", "리스트"],
  "summary": "한 줄 요약"
}}
```

JSON만 출력하세요.
"""

        try:
            # AI Provider가 있으면 사용
            if hasattr(self.ai_analyzer, 'providers') and self.ai_analyzer.providers:
                provider_name = self.ai_analyzer.default_provider
                provider = self.ai_analyzer.providers[provider_name]

                response_text = await provider.analyze(prompt)

                # JSON 파싱
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                    return result

            # AI 없으면 규칙 기반으로 폴백
            return self._rule_based_sentiment_analysis(news_list)

        except Exception as e:
            print(f"AI 감정 분석 실패: {e}")
            return self._rule_based_sentiment_analysis(news_list)

    def _rule_based_sentiment_analysis(self, news_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """규칙 기반 감정 분석"""

        positive_count = 0
        negative_count = 0
        neutral_count = 0

        keywords = {}

        for news in news_list:
            title = news['title']

            # 긍정 키워드 카운트
            positive_score = sum(1 for keyword in self.positive_keywords if keyword in title)

            # 부정 키워드 카운트
            negative_score = sum(1 for keyword in self.negative_keywords if keyword in title)

            # 분류
            if positive_score > negative_score:
                positive_count += 1
            elif negative_score > positive_score:
                negative_count += 1
            else:
                neutral_count += 1

            # 키워드 추출
            for keyword in self.positive_keywords + self.negative_keywords:
                if keyword in title:
                    keywords[keyword] = keywords.get(keyword, 0) + 1

        total = len(news_list)

        positive_pct = (positive_count / total) * 100 if total > 0 else 0
        neutral_pct = (neutral_count / total) * 100 if total > 0 else 0
        negative_pct = (negative_count / total) * 100 if total > 0 else 0

        # 상위 키워드
        top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5]
        top_keywords = [kw[0] for kw in top_keywords]

        # 요약
        if positive_pct > 60:
            summary = "매우 긍정적인 뉴스 흐름"
        elif positive_pct > 40:
            summary = "긍정적인 뉴스 흐름"
        elif negative_pct > 60:
            summary = "매우 부정적인 뉴스 흐름"
        elif negative_pct > 40:
            summary = "부정적인 뉴스 흐름"
        else:
            summary = "중립적인 뉴스 흐름"

        return {
            'positive': round(positive_pct, 1),
            'neutral': round(neutral_pct, 1),
            'negative': round(negative_pct, 1),
            'keywords': top_keywords,
            'summary': summary,
            'total_news': total
        }


class NewsMonitor:
    """뉴스 모니터 (실시간 스트리밍)"""

    def __init__(self, ai_analyzer=None):
        """
        초기화

        Args:
            ai_analyzer: UnifiedAnalyzer 인스턴스
        """
        self.aggregator = NewsAggregator()
        self.analyzer = SentimentAnalyzer(ai_analyzer)
        self.cache = {}  # 종목별 뉴스 캐시
        self.cache_ttl = 300  # 5분 캐시

    async def get_stock_news_with_sentiment(
        self,
        stock_code: str,
        limit: int = 10,
        use_ai: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        종목 뉴스 + 감정 분석

        Args:
            stock_code: 종목 코드
            limit: 최대 뉴스 개수
            use_ai: AI 분석 사용 여부
            use_cache: 캐시 사용 여부

        Returns:
            뉴스 + 감정 분석 결과
        """

        # 캐시 확인
        if use_cache and stock_code in self.cache:
            cached_data, cached_time = self.cache[stock_code]
            # Fix: .seconds → total_seconds()
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                return cached_data

        # 뉴스 수집
        news_list = await self.aggregator.fetch_stock_news(stock_code, limit)

        # 감정 분석
        sentiment = await self.analyzer.analyze_news_sentiment(news_list, use_ai)

        result = {
            'stock_code': stock_code,
            'news': news_list,
            'sentiment': sentiment,
            'timestamp': datetime.now().isoformat()
        }

        # 캐시 저장
        if use_cache:
            self.cache[stock_code] = (result, datetime.now())

        return result


# 싱글톤 인스턴스
_news_monitor_instance = None


def get_news_monitor(ai_analyzer=None):
    """NewsMonitor 싱글톤 인스턴스 반환"""
    global _news_monitor_instance
    if _news_monitor_instance is None:
        _news_monitor_instance = NewsMonitor(ai_analyzer)
    return _news_monitor_instance
