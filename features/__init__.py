"""
AutoTrade Pro - 고급 기능 모듈
실시간 호가창, 수익 추적, 포트폴리오 최적화, 뉴스 피드, 리스크 분석,
AI 자율 모드, 가상매매, 거래 일지, 알림 시스템 등
"""

# 테스트 모드 매니저 (의존성 없음, 항상 사용 가능)
from .test_mode_manager import TestModeManager, run_test_mode

# 선택적 import (numpy 등 의존성 필요)
try:
    from .order_book import OrderBookService, OrderBook
    from .profit_tracker import ProfitTracker, PerformanceMetrics, TradeRecord
    from .portfolio_optimizer import PortfolioOptimizer, PortfolioOptimization
    from .news_feed import NewsFeedService, NewsArticle, NewsSummary, SentimentAnalyzer
    from .risk_analyzer import RiskAnalyzer, RiskAnalysis, StockRisk, PortfolioRisk
    from .ai_mode import AIAgent, AIDecision, AIStrategy, AIPerformance, get_ai_agent
    from .ai_learning import AILearningEngine, TradingPattern as AITradingPattern, MarketRegime, LearningInsight
    from .paper_trading import PaperTradingEngine, VirtualAccount, VirtualPosition, StrategyConfig, get_paper_trading_engine
    from .trading_journal import TradingJournal, JournalEntry, JournalInsight, get_trading_journal
    from .notification import NotificationManager, Notification, NotificationPriority, get_notification_manager
    # v4.0 Advanced Features
    from .replay_simulator import ReplaySimulator, MarketSnapshot
    from .auto_rebalancer import AutoRebalancer, RebalanceStrategy, RebalanceAction, get_auto_rebalancer
except ImportError as e:
    import warnings
    warnings.warn(f"Some features modules could not be imported: {e}. Install required dependencies (numpy, pandas, etc.)")
    # 임포트 실패한 모듈들을 None으로 설정
    OrderBookService = OrderBook = None
    ProfitTracker = PerformanceMetrics = TradeRecord = None
    PortfolioOptimizer = PortfolioOptimization = None
    NewsFeedService = NewsArticle = NewsSummary = SentimentAnalyzer = None
    RiskAnalyzer = RiskAnalysis = StockRisk = PortfolioRisk = None
    AIAgent = AIDecision = AIStrategy = AIPerformance = get_ai_agent = None
    AILearningEngine = AITradingPattern = MarketRegime = LearningInsight = None
    PaperTradingEngine = VirtualAccount = VirtualPosition = StrategyConfig = get_paper_trading_engine = None
    TradingJournal = JournalEntry = JournalInsight = get_trading_journal = None
    NotificationManager = Notification = NotificationPriority = get_notification_manager = None
    # v4.0 Advanced Features
    ReplaySimulator = MarketSnapshot = None
    AutoRebalancer = RebalanceStrategy = RebalanceAction = get_auto_rebalancer = None

__all__ = [
    # Test Mode Manager (no dependencies)
    'TestModeManager',
    'run_test_mode',
    # Order Book
    'OrderBookService',
    'OrderBook',
    # Profit Tracking
    'ProfitTracker',
    'PerformanceMetrics',
    'TradeRecord',
    # Portfolio Optimization
    'PortfolioOptimizer',
    'PortfolioOptimization',
    # News Feed
    'NewsFeedService',
    'NewsArticle',
    'NewsSummary',
    'SentimentAnalyzer',
    # Risk Analysis
    'RiskAnalyzer',
    'RiskAnalysis',
    'StockRisk',
    'PortfolioRisk',
    # AI Mode (v3.6)
    'AIAgent',
    'AIDecision',
    'AIStrategy',
    'AIPerformance',
    'get_ai_agent',
    # AI Learning
    'AILearningEngine',
    'AITradingPattern',
    'MarketRegime',
    'LearningInsight',
    # Paper Trading (v3.7)
    'PaperTradingEngine',
    'VirtualAccount',
    'VirtualPosition',
    'StrategyConfig',
    'get_paper_trading_engine',
    # Trading Journal (v3.7)
    'TradingJournal',
    'JournalEntry',
    'JournalInsight',
    'get_trading_journal',
    # Notifications (v3.7)
    'NotificationManager',
    'Notification',
    'NotificationPriority',
    'get_notification_manager',
    # v4.0 Advanced Features
    'ReplaySimulator',
    'MarketSnapshot',
    'AutoRebalancer',
    'RebalanceStrategy',
    'RebalanceAction',
    'get_auto_rebalancer',
]
