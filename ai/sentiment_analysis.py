"""
Sentiment Analysis System
News and social media sentiment analysis for trading

Author: AutoTrade Pro
Version: 4.2
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
from collections import Counter

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class NewsArticle:
    """News article"""
    title: str
    content: str
    source: str
    published_at: str
    url: str
    sentiment_score: float = 0.0
    keywords: List[str] = None


@dataclass
class SocialMediaPost:
    """Social media post"""
    platform: str  # 'twitter', 'reddit', etc.
    content: str
    author: str
    timestamp: str
    likes: int
    shares: int
    sentiment_score: float = 0.0


@dataclass
class SentimentReport:
    """Sentiment analysis report"""
    stock_code: str
    overall_sentiment: float  # -1 to 1
    sentiment_category: str  # 'very_negative', 'negative', 'neutral', 'positive', 'very_positive'
    news_sentiment: float
    social_sentiment: float
    confidence: float
    article_count: int
    post_count: int
    timestamp: str
    trending_keywords: List[str]
    sentiment_change_24h: float


# ============================================================================
# News Sentiment Analyzer
# ============================================================================

class NewsSentimentAnalyzer:
    """
    News sentiment analysis

    Features:
    - Keyword-based sentiment scoring
    - Financial news scraping
    - Trend detection
    """

    def __init__(self):
        # Positive keywords
        self.positive_keywords = {
            '상승', '증가', '호재', '성장', '긍정', '개선', '상향', '확대',
            '급등', '강세', '최고', '최대', '수익', '흑자', '이익', '실적',
            'surge', 'rally', 'gain', 'growth', 'positive', 'upgrade',
            'profit', 'beat', 'outperform', 'bullish'
        }

        # Negative keywords
        self.negative_keywords = {
            '하락', '감소', '악재', '약세', '부정', '악화', '하향', '축소',
            '급락', '최저', '손실', '적자', '위험', '우려', '불안', '실망',
            'plunge', 'drop', 'loss', 'negative', 'downgrade', 'risk',
            'concern', 'decline', 'bearish', 'underperform'
        }

        self.article_cache: Dict[str, List[NewsArticle]] = {}

    def analyze_news(self, stock_code: str, days_back: int = 7) -> Dict[str, Any]:
        """
        Analyze news sentiment

        Args:
            stock_code: Stock code
            days_back: Days to look back

        Returns:
            News sentiment analysis
        """
        articles = self._fetch_news(stock_code, days_back)

        if not articles:
            return {
                'sentiment_score': 0.0,
                'article_count': 0,
                'category': 'neutral'
            }

        # Analyze each article
        scores = []
        for article in articles:
            score = self._calculate_sentiment(article.title + " " + article.content)
            article.sentiment_score = score
            scores.append(score)

        avg_sentiment = sum(scores) / len(scores)

        return {
            'sentiment_score': avg_sentiment,
            'article_count': len(articles),
            'category': self._categorize_sentiment(avg_sentiment),
            'articles': articles[:10]  # Top 10
        }

    def _fetch_news(self, stock_code: str, days_back: int) -> List[NewsArticle]:
        """
        Fetch news articles for a stock.

        NOTE: This is a STUB implementation. For production use, integrate with:
        - Naver Finance API (https://openapi.naver.com)
        - Google News API
        - Financial news providers (Bloomberg, Reuters)

        Currently returns empty list to avoid misleading mock data.
        """
        # Try to fetch real news if available
        if REQUESTS_AVAILABLE:
            try:
                # Example: Naver Finance news scraping (requires proper API key)
                # This is a placeholder for real implementation
                pass
            except Exception as e:
                pass

        # Return empty list instead of fake data
        # This makes it clear that news analysis is not available
        return []

    def _calculate_sentiment(self, text: str) -> float:
        """Calculate sentiment score from text"""
        text_lower = text.lower()
        words = re.findall(r'\w+', text_lower)

        positive_count = sum(1 for word in words if word in self.positive_keywords)
        negative_count = sum(1 for word in words if word in self.negative_keywords)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        score = (positive_count - negative_count) / total
        return max(-1, min(1, score))

    def _categorize_sentiment(self, score: float) -> str:
        """Categorize sentiment score"""
        if score >= 0.5:
            return 'very_positive'
        elif score >= 0.1:
            return 'positive'
        elif score <= -0.5:
            return 'very_negative'
        elif score <= -0.1:
            return 'negative'
        else:
            return 'neutral'


# ============================================================================
# Social Media Sentiment Analyzer
# ============================================================================

class SocialMediaAnalyzer:
    """
    Social media sentiment analysis

    Features:
    - Twitter/Reddit sentiment
    - Viral post detection
    - Influencer impact analysis
    """

    def __init__(self):
        self.post_cache: Dict[str, List[SocialMediaPost]] = {}

    def analyze_social(self, stock_code: str, hours_back: int = 24) -> Dict[str, Any]:
        """
        Analyze social media sentiment

        Args:
            stock_code: Stock code
            hours_back: Hours to look back

        Returns:
            Social sentiment analysis
        """
        posts = self._fetch_posts(stock_code, hours_back)

        if not posts:
            return {
                'sentiment_score': 0.0,
                'post_count': 0,
                'category': 'neutral'
            }

        # Weighted sentiment (popular posts count more)
        total_weight = 0
        weighted_sentiment = 0

        for post in posts:
            weight = 1 + (post.likes + post.shares) / 100
            sentiment = self._calculate_post_sentiment(post.content)
            post.sentiment_score = sentiment

            weighted_sentiment += sentiment * weight
            total_weight += weight

        avg_sentiment = weighted_sentiment / total_weight if total_weight > 0 else 0

        return {
            'sentiment_score': avg_sentiment,
            'post_count': len(posts),
            'category': self._categorize_sentiment(avg_sentiment),
            'viral_posts': sorted(posts, key=lambda p: p.likes + p.shares, reverse=True)[:5]
        }

    def _fetch_posts(self, stock_code: str, hours_back: int) -> List[SocialMediaPost]:
        """
        Fetch social media posts about a stock.

        NOTE: This is a STUB implementation. For production use, integrate with:
        - Twitter/X API (requires developer account)
        - Reddit API (r/wallstreetbets, r/stocks)
        - StockTwits API

        Currently returns empty list to avoid misleading mock/random data.
        Social media sentiment analysis requires proper API integration.
        """
        # Return empty list instead of fake random data
        # This makes it clear that social sentiment is not available
        return []

    def _calculate_post_sentiment(self, text: str) -> float:
        """Calculate sentiment from post"""
        positive_emojis = {'🚀', '📈', '💰', '🔥', '💪', '👍', '✅'}
        negative_emojis = {'📉', '💩', '😢', '😭', '❌', '👎'}

        pos_count = sum(text.count(emoji) for emoji in positive_emojis)
        neg_count = sum(text.count(emoji) for emoji in negative_emojis)

        # Also check keywords
        text_lower = text.lower()
        if 'moon' in text_lower or 'bullish' in text_lower:
            pos_count += 1
        if 'dump' in text_lower or 'bearish' in text_lower:
            neg_count += 1

        total = pos_count + neg_count
        if total == 0:
            return 0.0

        return (pos_count - neg_count) / total

    def _categorize_sentiment(self, score: float) -> str:
        """Categorize sentiment"""
        if score >= 0.5:
            return 'very_positive'
        elif score >= 0.1:
            return 'positive'
        elif score <= -0.5:
            return 'very_negative'
        elif score <= -0.1:
            return 'negative'
        else:
            return 'neutral'


# ============================================================================
# Sentiment Analysis Manager
# ============================================================================

class SentimentAnalysisManager:
    """
    Unified sentiment analysis manager

    Features:
    - Combines news and social sentiment
    - Trend detection
    - Alert generation
    """

    def __init__(self):
        self.news_analyzer = NewsSentimentAnalyzer()
        self.social_analyzer = SocialMediaAnalyzer()
        self.sentiment_history: Dict[str, List[float]] = {}

    def analyze_complete(self, stock_code: str) -> SentimentReport:
        """
        Complete sentiment analysis

        Args:
            stock_code: Stock code

        Returns:
            Complete sentiment report
        """
        # Analyze news
        news_result = self.news_analyzer.analyze_news(stock_code)

        # Analyze social media
        social_result = self.social_analyzer.analyze_social(stock_code)

        # Combine sentiments (weighted average)
        overall_sentiment = (
            news_result['sentiment_score'] * 0.6 +
            social_result['sentiment_score'] * 0.4
        )

        # Store in history
        if stock_code not in self.sentiment_history:
            self.sentiment_history[stock_code] = []
        self.sentiment_history[stock_code].append(overall_sentiment)

        # Calculate 24h change
        hist = self.sentiment_history[stock_code]
        sentiment_change_24h = (
            overall_sentiment - hist[-2] if len(hist) > 1 else 0.0
        )

        # Extract trending keywords
        keywords = self._extract_keywords(stock_code)

        # Calculate confidence
        confidence = min(
            (news_result['article_count'] + social_result['post_count']) / 100,
            1.0
        )

        return SentimentReport(
            stock_code=stock_code,
            overall_sentiment=overall_sentiment,
            sentiment_category=self._categorize_overall(overall_sentiment),
            news_sentiment=news_result['sentiment_score'],
            social_sentiment=social_result['sentiment_score'],
            confidence=confidence,
            article_count=news_result['article_count'],
            post_count=social_result['post_count'],
            timestamp=datetime.now().isoformat(),
            trending_keywords=keywords,
            sentiment_change_24h=sentiment_change_24h
        )

    def _extract_keywords(self, stock_code: str) -> List[str]:
        """Extract trending keywords"""
        all_text = []

        # From news
        articles = self.news_analyzer.article_cache.get(stock_code, [])
        for article in articles:
            all_text.extend(re.findall(r'\w+', article.title.lower()))

        # From social
        posts = self.social_analyzer.post_cache.get(stock_code, [])
        for post in posts:
            all_text.extend(re.findall(r'\w+', post.content.lower()))

        # Count and return top keywords
        word_counts = Counter(all_text)
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were'}
        meaningful = {w: c for w, c in word_counts.items() if w not in stop_words and len(w) > 3}

        top_keywords = sorted(meaningful.items(), key=lambda x: x[1], reverse=True)[:10]
        return [word for word, count in top_keywords]

    def _categorize_overall(self, score: float) -> str:
        """Categorize overall sentiment"""
        if score >= 0.5:
            return 'very_positive'
        elif score >= 0.1:
            return 'positive'
        elif score <= -0.5:
            return 'very_negative'
        elif score <= -0.1:
            return 'negative'
        else:
            return 'neutral'

    def generate_alerts(self, report: SentimentReport) -> List[Dict[str, Any]]:
        """Generate sentiment alerts"""
        alerts = []

        # Extreme sentiment alert
        if abs(report.overall_sentiment) >= 0.7:
            alerts.append({
                'type': 'extreme_sentiment',
                'severity': 'high',
                'message': f"Extreme {report.sentiment_category} sentiment detected",
                'sentiment_score': report.overall_sentiment
            })

        # Rapid sentiment change
        if abs(report.sentiment_change_24h) >= 0.3:
            direction = 'improved' if report.sentiment_change_24h > 0 else 'deteriorated'
            alerts.append({
                'type': 'sentiment_shift',
                'severity': 'medium',
                'message': f"Sentiment has {direction} significantly in 24h",
                'change': report.sentiment_change_24h
            })

        # High confidence positive sentiment
        if report.overall_sentiment > 0.3 and report.confidence > 0.7:
            alerts.append({
                'type': 'high_confidence_positive',
                'severity': 'low',
                'message': f"Strong positive sentiment with high confidence",
                'sentiment': report.overall_sentiment,
                'confidence': report.confidence
            })

        return alerts


# Singleton instance
_sentiment_manager = None

def get_sentiment_manager() -> SentimentAnalysisManager:
    """Get sentiment analysis manager"""
    global _sentiment_manager
    if _sentiment_manager is None:
        _sentiment_manager = SentimentAnalysisManager()
    return _sentiment_manager


if __name__ == '__main__':
    print("📰 Sentiment Analysis Test")

    manager = get_sentiment_manager()
    report = manager.analyze_complete('005930')

    print(f"\nSentiment Report for {report.stock_code}:")
    print(f"Overall Sentiment: {report.overall_sentiment:.2f} ({report.sentiment_category})")
    print(f"News Sentiment: {report.news_sentiment:.2f}")
    print(f"Social Sentiment: {report.social_sentiment:.2f}")
    print(f"Confidence: {report.confidence:.1%}")
    print(f"Articles: {report.article_count}, Posts: {report.post_count}")
    print(f"Trending Keywords: {', '.join(report.trending_keywords[:5])}")

    alerts = manager.generate_alerts(report)
    print(f"\nAlerts: {len(alerts)}")
    for alert in alerts:
        print(f"  - [{alert['severity']}] {alert['message']}")

    print("\n✅ Sentiment analysis ready")
