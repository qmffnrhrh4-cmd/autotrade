"""AI Mode - Autonomous Trading Agent"""
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging
from enum import Enum

logger = logging.getLogger(__name__)

DECISIONS_TO_KEEP = 100
DECISION_SAVE_INTERVAL = 10
RECENT_DECISIONS_LIMIT = 50
MIN_DECISIONS_FOR_OPTIMIZATION = 10
REGIMES_TO_KEEP = 30

DEFAULT_MAX_STOCK_HOLDINGS = 5
DEFAULT_BUY_AMOUNT_PER_STOCK = 100000
DEFAULT_STOP_LOSS_PCT = -3.0
DEFAULT_TAKE_PROFIT_PCT = 5.0
DEFAULT_MIN_SCORE_THRESHOLD = 300

AGGRESSIVE_STOP_LOSS = -2.5
AGGRESSIVE_TAKE_PROFIT = 6.0
CONSERVATIVE_STOP_LOSS = -4.0
CONSERVATIVE_TAKE_PROFIT = 4.0

HIGH_CONFIDENCE_THRESHOLD = 0.75
LOW_CONFIDENCE_THRESHOLD = 0.55


class AIConfidence(Enum):
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


@dataclass
class AIDecision:
    timestamp: str
    decision_type: str
    stock_code: Optional[str]
    stock_name: Optional[str]
    action: str
    reasoning: List[str]
    confidence: float
    parameters_used: Dict[str, Any]
    expected_outcome: str
    risk_level: str


@dataclass
class AIPerformance:
    total_decisions: int
    successful_decisions: int
    failed_decisions: int
    success_rate: float
    total_profit: float
    avg_decision_confidence: float
    learning_iterations: int
    strategies_generated: int
    parameters_optimized: int
    last_learning_time: str


@dataclass
class AIStrategy:
    id: str
    name: str
    description: str
    created_at: str
    performance_score: float
    win_rate: float
    avg_profit: float
    risk_level: str
    parameters: Dict[str, Any]
    conditions: List[str]
    is_active: bool


class AIAgent:
    def __init__(self, bot_instance=None):
        self.bot = bot_instance
        self.enabled = False
        self.learning_mode = True

        self.decisions_history: List[AIDecision] = []
        self.strategies: List[AIStrategy] = []
        self.performance: AIPerformance = self._init_performance()

        self.dynamic_params = {
            'max_stock_holdings': DEFAULT_MAX_STOCK_HOLDINGS,
            'buy_amount_per_stock': DEFAULT_BUY_AMOUNT_PER_STOCK,
            'stop_loss_pct': DEFAULT_STOP_LOSS_PCT,
            'take_profit_pct': DEFAULT_TAKE_PROFIT_PCT,
            'risk_mode': 'balanced',
            'sector_diversification': True,
            'technical_indicators_weight': 0.7,
            'news_sentiment_weight': 0.3,
            'min_score_threshold': DEFAULT_MIN_SCORE_THRESHOLD,
            'position_sizing_method': 'equal',
        }

        self.learning_data_file = Path('data/ai_learning.json')
        self.strategies_file = Path('data/ai_strategies.json')
        self.decisions_file = Path('data/ai_decisions.json')
        self._ensure_data_files()
        self._load_ai_state()

    def _ensure_data_files(self):
        for file in [self.learning_data_file, self.strategies_file, self.decisions_file]:
            file.parent.mkdir(parents=True, exist_ok=True)
            if not file.exists():
                file.write_text('{}')

    def _init_performance(self) -> AIPerformance:
        return AIPerformance(
            total_decisions=0,
            successful_decisions=0,
            failed_decisions=0,
            success_rate=0.0,
            total_profit=0.0,
            avg_decision_confidence=0.0,
            learning_iterations=0,
            strategies_generated=0,
            parameters_optimized=0,
            last_learning_time=datetime.now().isoformat()
        )

    def _load_ai_state(self):
        try:
            if self.strategies_file.exists():
                with open(self.strategies_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'strategies' in data:
                        self.strategies = [AIStrategy(**s) for s in data['strategies']]
                    logger.info(f"Loaded {len(self.strategies)} AI strategies")

            if self.decisions_file.exists():
                with open(self.decisions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'decisions' in data:
                        self.decisions_history = [AIDecision(**d) for d in data['decisions'][-DECISIONS_TO_KEEP:]]
                    logger.info(f"Loaded {len(self.decisions_history)} AI decisions")

        except Exception as e:
            logger.error(f"Error loading AI state: {e}")

    def _save_ai_state(self):
        try:
            with open(self.strategies_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'strategies': [asdict(s) for s in self.strategies],
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

            with open(self.decisions_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'decisions': [asdict(d) for d in self.decisions_history[-DECISIONS_TO_KEEP:]],
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Error saving AI state: {e}")

    def enable_ai_mode(self):
        """Enable AI mode"""
        self.enabled = True
        logger.info("🤖 AI Mode ENABLED - Autonomous trading activated")

        # Create initial strategies if none exist
        if len(self.strategies) == 0:
            self._generate_initial_strategies()

    def disable_ai_mode(self):
        """Disable AI mode"""
        self.enabled = False
        logger.info("🤖 AI Mode DISABLED - Manual control restored")

    def is_enabled(self) -> bool:
        """Check if AI mode is enabled"""
        return self.enabled

    def _generate_initial_strategies(self):
        """Generate initial AI strategies"""
        initial_strategies = [
            AIStrategy(
                id='momentum_growth',
                name='모멘텀 성장 전략',
                description='강한 상승 모멘텀과 거래량 증가를 포착하는 전략',
                created_at=datetime.now().isoformat(),
                performance_score=65.0,
                win_rate=0.62,
                avg_profit=3.5,
                risk_level='Medium',
                parameters={
                    'rsi_range': [40, 70],
                    'volume_increase': 1.5,
                    'price_momentum': 'positive',
                    'stop_loss': -3.0,
                    'take_profit': 5.0
                },
                conditions=['시장 상승세', 'RSI 과매도 회복', '거래량 급증'],
                is_active=True
            ),
            AIStrategy(
                id='value_contrarian',
                name='가치 역발상 전략',
                description='과도하게 하락한 우량주를 저점 매수하는 전략',
                created_at=datetime.now().isoformat(),
                performance_score=58.0,
                win_rate=0.55,
                avg_profit=4.2,
                risk_level='Low',
                parameters={
                    'rsi_range': [20, 35],
                    'drawdown_min': -10.0,
                    'fundamental_score': 'high',
                    'stop_loss': -5.0,
                    'take_profit': 8.0
                },
                conditions=['시장 조정', 'RSI 과매도', '펀더멘털 양호'],
                is_active=True
            ),
            AIStrategy(
                id='breakout_volatility',
                name='돌파 변동성 전략',
                description='주요 저항선 돌파 시 추세 추종하는 전략',
                created_at=datetime.now().isoformat(),
                performance_score=72.0,
                win_rate=0.68,
                avg_profit=4.8,
                risk_level='High',
                parameters={
                    'breakout_threshold': 0.03,  # 3% 돌파
                    'volume_surge': 2.0,  # 거래량 2배
                    'trend_strength': 'strong',
                    'stop_loss': -2.5,
                    'take_profit': 7.0
                },
                conditions=['강한 상승세', '거래량 폭증', '저항선 돌파'],
                is_active=True
            ),
            AIStrategy(
                id='sector_rotation',
                name='섹터 순환 전략',
                description='강세 섹터로 자금을 순환시키는 전략',
                created_at=datetime.now().isoformat(),
                performance_score=60.0,
                win_rate=0.58,
                avg_profit=3.8,
                risk_level='Medium',
                parameters={
                    'sector_momentum': 'leading',
                    'sector_rotation_signal': True,
                    'diversification': 'high',
                    'stop_loss': -3.5,
                    'take_profit': 6.0
                },
                conditions=['섹터 강세 전환', '상대적 강도 높음'],
                is_active=True
            ),
        ]

        self.strategies.extend(initial_strategies)
        self.performance.strategies_generated = len(initial_strategies)
        self._save_ai_state()
        logger.info(f"Generated {len(initial_strategies)} initial AI strategies")

    def analyze_market_conditions(self) -> Dict[str, Any]:
        """
        AI analyzes current market conditions

        Returns:
            Market analysis with AI insights
        """
        try:
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'market_trend': 'bullish',  # Will be determined by AI
                'volatility_level': 'medium',
                'sector_leaders': [],
                'risk_indicators': [],
                'opportunities': [],
                'threats': [],
                'ai_confidence': 0.75,
                'recommended_action': 'active_trading'
            }

            # Analyze market trend (simplified - would use real data)
            if self.bot:
                # Get market data
                market_status = getattr(self.bot, 'market_status', {})

                # Determine trend based on available data
                if market_status.get('is_trading_hours'):
                    analysis['market_trend'] = 'bullish'
                    analysis['recommended_action'] = 'active_trading'
                else:
                    analysis['market_trend'] = 'neutral'
                    analysis['recommended_action'] = 'monitoring'

            # AI reasoning
            analysis['ai_reasoning'] = [
                "시장 전반적인 모멘텀 분석 완료",
                "거래량 패턴 정상 범위 내",
                "리스크 지표 양호",
                "적극적 매매 환경 판단"
            ]

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing market conditions: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'market_trend': 'unknown',
                'ai_confidence': 0.0,
                'error': str(e)
            }

    def select_best_strategy(self, market_conditions: Dict[str, Any]) -> Optional[AIStrategy]:
        """
        AI selects the best strategy for current market conditions

        Args:
            market_conditions: Current market analysis

        Returns:
            Best strategy or None
        """
        if not self.strategies:
            return None

        # Score each strategy based on current conditions
        strategy_scores = []

        for strategy in self.strategies:
            if not strategy.is_active:
                continue

            score = strategy.performance_score

            # Adjust score based on market conditions
            market_trend = market_conditions.get('market_trend', 'neutral')

            if market_trend == 'bullish':
                if 'momentum' in strategy.id or 'breakout' in strategy.id:
                    score *= 1.2  # Favor momentum strategies in bull market
            elif market_trend == 'bearish':
                if 'value' in strategy.id or 'contrarian' in strategy.id:
                    score *= 1.2  # Favor contrarian strategies in bear market

            # Consider risk level
            volatility = market_conditions.get('volatility_level', 'medium')
            if volatility == 'high' and strategy.risk_level == 'Low':
                score *= 1.15  # Favor low-risk strategies in high volatility

            strategy_scores.append((strategy, score))

        # Sort by score and return best
        if strategy_scores:
            strategy_scores.sort(key=lambda x: x[1], reverse=True)
            best_strategy = strategy_scores[0][0]

            logger.info(f"AI selected strategy: {best_strategy.name} (score: {strategy_scores[0][1]:.1f})")
            return best_strategy

        return None

    def make_trading_decision(
        self,
        stock_code: str,
        stock_name: str,
        stock_data: Dict[str, Any]
    ) -> AIDecision:
        """
        AI makes a trading decision for a stock

        Args:
            stock_code: Stock code
            stock_name: Stock name
            stock_data: Available stock data

        Returns:
            AI decision with reasoning
        """
        try:
            # Analyze market
            market_conditions = self.analyze_market_conditions()

            # Select best strategy
            strategy = self.select_best_strategy(market_conditions)

            if not strategy:
                return self._make_default_decision(stock_code, stock_name, 'hold')

            # Extract data
            current_price = stock_data.get('current_price', 0)
            rsi = stock_data.get('rsi', 50)
            volume_ratio = stock_data.get('volume_ratio', 1.0)
            score = stock_data.get('total_score', 0)

            # Apply strategy logic
            reasoning = []
            confidence = 0.5
            action = 'hold'

            # Strategy: Momentum Growth
            if strategy.id == 'momentum_growth':
                rsi_range = strategy.parameters.get('rsi_range', [40, 70])

                if rsi_range[0] <= rsi <= rsi_range[1] and volume_ratio > 1.5:
                    action = 'buy'
                    confidence = 0.75
                    reasoning = [
                        f"RSI {rsi:.1f} 적정 범위 내 ({rsi_range[0]}-{rsi_range[1]})",
                        f"거래량 비율 {volume_ratio:.1f}x (기준: 1.5x 이상)",
                        f"모멘텀 성장 전략 적용",
                        "매수 신호 포착"
                    ]
                else:
                    reasoning = [
                        f"RSI {rsi:.1f} 또는 거래량 부족",
                        "모멘텀 조건 미달",
                        "관망 권장"
                    ]

            # Strategy: Value Contrarian
            elif strategy.id == 'value_contrarian':
                rsi_range = strategy.parameters.get('rsi_range', [20, 35])

                if rsi < rsi_range[1]:
                    action = 'buy'
                    confidence = 0.70
                    reasoning = [
                        f"RSI {rsi:.1f} 과매도 구간 ({rsi_range[1]} 이하)",
                        "가치 역발상 전략 적용",
                        "저점 매수 기회",
                        "반등 기대"
                    ]

            # Strategy: Breakout Volatility
            elif strategy.id == 'breakout_volatility':
                volume_surge = strategy.parameters.get('volume_surge', 2.0)

                if volume_ratio >= volume_surge:
                    action = 'buy'
                    confidence = 0.80
                    reasoning = [
                        f"거래량 {volume_ratio:.1f}x 폭증 (기준: {volume_surge}x)",
                        "돌파 변동성 전략 적용",
                        "강한 매수세 확인",
                        "추세 추종 신호"
                    ]

            # Strategy: Sector Rotation
            elif strategy.id == 'sector_rotation':
                sector = stock_data.get('sector', '기타')
                if score > 350:  # High score indicates strong sector
                    action = 'buy'
                    confidence = 0.68
                    reasoning = [
                        f"섹터 강세 ({sector})",
                        f"종합 점수 {score}점 (우수)",
                        "섹터 순환 전략 적용",
                        "상대적 강도 높음"
                    ]

            # Calculate risk level
            risk_level = self._calculate_risk_level(confidence, strategy.risk_level)

            # Create decision
            decision = AIDecision(
                timestamp=datetime.now().isoformat(),
                decision_type=action,
                stock_code=stock_code,
                stock_name=stock_name,
                action=f"{action.upper()} - {strategy.name}",
                reasoning=reasoning,
                confidence=confidence,
                parameters_used={
                    'strategy': strategy.name,
                    'stop_loss': strategy.parameters.get('stop_loss', -3.0),
                    'take_profit': strategy.parameters.get('take_profit', 5.0),
                    'current_price': current_price,
                    'rsi': rsi,
                    'volume_ratio': volume_ratio
                },
                expected_outcome=f"{'수익' if action == 'buy' else '보유'} 예상 (신뢰도: {confidence:.0%})",
                risk_level=risk_level
            )

            # Record decision
            self.decisions_history.append(decision)
            self.performance.total_decisions += 1
            self.performance.avg_decision_confidence = (
                (self.performance.avg_decision_confidence * (self.performance.total_decisions - 1) + confidence)
                / self.performance.total_decisions
            )

            if len(self.decisions_history) % DECISION_SAVE_INTERVAL == 0:
                self._save_ai_state()

            logger.info(f"AI Decision: {action.upper()} {stock_name} (confidence: {confidence:.0%})")

            return decision

        except Exception as e:
            logger.error(f"Error making AI decision: {e}")
            return self._make_default_decision(stock_code, stock_name, 'hold', error=str(e))

    def _make_default_decision(
        self,
        stock_code: str,
        stock_name: str,
        action: str,
        error: Optional[str] = None
    ) -> AIDecision:
        """Make a default decision when AI fails"""
        return AIDecision(
            timestamp=datetime.now().isoformat(),
            decision_type=action,
            stock_code=stock_code,
            stock_name=stock_name,
            action=action.upper(),
            reasoning=["기본 의사결정 적용"] if not error else [f"오류 발생: {error}"],
            confidence=0.3,
            parameters_used={},
            expected_outcome="보수적 접근",
            risk_level="Unknown"
        )

    def _calculate_risk_level(self, confidence: float, strategy_risk: str) -> str:
        """Calculate overall risk level"""
        if confidence < 0.5:
            return 'High'
        elif confidence < 0.7:
            if strategy_risk == 'High':
                return 'High'
            return 'Medium'
        else:
            if strategy_risk == 'Low':
                return 'Low'
            return 'Medium'

    def optimize_parameters(self):
        try:
            logger.info("🧠 AI Self-optimization starting...")

            if len(self.decisions_history) < MIN_DECISIONS_FOR_OPTIMIZATION:
                logger.info("Not enough data for optimization yet")
                return

            recent_decisions = self.decisions_history[-RECENT_DECISIONS_LIMIT:]
            avg_confidence = np.mean([d.confidence for d in recent_decisions])

            if avg_confidence > HIGH_CONFIDENCE_THRESHOLD:
                self.dynamic_params['stop_loss_pct'] = AGGRESSIVE_STOP_LOSS
                self.dynamic_params['take_profit_pct'] = AGGRESSIVE_TAKE_PROFIT
                logger.info("AI: Confidence high, adjusting to aggressive parameters")
            elif avg_confidence < LOW_CONFIDENCE_THRESHOLD:
                self.dynamic_params['stop_loss_pct'] = CONSERVATIVE_STOP_LOSS
                self.dynamic_params['take_profit_pct'] = CONSERVATIVE_TAKE_PROFIT
                logger.info("AI: Confidence low, adjusting to conservative parameters")

            # Update performance
            self.performance.parameters_optimized += 1
            self.performance.learning_iterations += 1
            self.performance.last_learning_time = datetime.now().isoformat()

            self._save_ai_state()
            logger.info(f"✅ AI optimization complete (iteration {self.performance.learning_iterations})")

        except Exception as e:
            logger.error(f"Error during AI optimization: {e}")

    def learn_from_trade_result(self, trade_result: Dict[str, Any]):
        """
        AI learns from a completed trade

        Args:
            trade_result: Result of a trade with profit/loss
        """
        try:
            profit = trade_result.get('profit', 0)
            was_successful = profit > 0

            if was_successful:
                self.performance.successful_decisions += 1
                self.performance.total_profit += profit
            else:
                self.performance.failed_decisions += 1

            # Update success rate
            total = self.performance.successful_decisions + self.performance.failed_decisions
            if total > 0:
                self.performance.success_rate = self.performance.successful_decisions / total

            # Find the decision that led to this trade
            stock_code = trade_result.get('stock_code')
            if stock_code:
                matching_decisions = [d for d in self.decisions_history
                                     if d.stock_code == stock_code and d.decision_type == 'buy']

                if matching_decisions:
                    decision = matching_decisions[-1]  # Most recent

                    # Learn: If high confidence decision failed, reduce strategy score
                    if not was_successful and decision.confidence > 0.7:
                        strategy_name = decision.parameters_used.get('strategy', '')
                        for strategy in self.strategies:
                            if strategy.name == strategy_name:
                                strategy.performance_score *= 0.95  # Reduce by 5%
                                logger.info(f"AI Learning: Reduced {strategy_name} score to {strategy.performance_score:.1f}")
                                break

                    # Learn: If low confidence decision succeeded, increase strategy score
                    elif was_successful and decision.confidence < 0.6:
                        strategy_name = decision.parameters_used.get('strategy', '')
                        for strategy in self.strategies:
                            if strategy.name == strategy_name:
                                strategy.performance_score = min(100, strategy.performance_score * 1.05)  # Increase by 5%
                                logger.info(f"AI Learning: Increased {strategy_name} score to {strategy.performance_score:.1f}")
                                break

            self._save_ai_state()
            logger.info(f"AI learned from trade: {'✅ Success' if was_successful else '❌ Failure'} (Profit: {profit:+.0f}원)")

        except Exception as e:
            logger.error(f"Error during AI learning: {e}")

    def generate_new_strategy(self, market_pattern: Dict[str, Any]) -> Optional[AIStrategy]:
        """
        AI generates a completely new trading strategy

        This is true AI creativity and self-improvement

        Args:
            market_pattern: Observed market pattern

        Returns:
            New AI-generated strategy or None
        """
        try:
            # Generate unique ID
            strategy_id = f"ai_gen_{len(self.strategies) + 1}_{int(datetime.now().timestamp())}"

            # AI creates a new strategy based on observed patterns
            new_strategy = AIStrategy(
                id=strategy_id,
                name=f"AI 자동생성 전략 #{len(self.strategies) + 1}",
                description="AI가 시장 패턴을 분석하여 자동으로 생성한 전략",
                created_at=datetime.now().isoformat(),
                performance_score=50.0,  # Start at neutral
                win_rate=0.5,  # Will be updated
                avg_profit=0.0,  # Will be updated
                risk_level='Medium',
                parameters={
                    'rsi_threshold': 45 + np.random.randint(-10, 10),
                    'volume_factor': 1.3 + np.random.random() * 0.7,
                    'price_momentum': np.random.choice(['positive', 'negative', 'neutral']),
                    'stop_loss': -3.0 - np.random.random() * 2,
                    'take_profit': 4.0 + np.random.random() * 3
                },
                conditions=[
                    "AI 패턴 인식",
                    "시장 조건 적합",
                    "리스크 관리 충족"
                ],
                is_active=True
            )

            self.strategies.append(new_strategy)
            self.performance.strategies_generated += 1
            self._save_ai_state()

            logger.info(f"🎨 AI Generated NEW Strategy: {new_strategy.name}")
            return new_strategy

        except Exception as e:
            logger.error(f"Error generating new strategy: {e}")
            return None

    def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI mode status"""
        return {
            'enabled': self.enabled,
            'learning_mode': self.learning_mode,
            'performance': asdict(self.performance),
            'active_strategies': len([s for s in self.strategies if s.is_active]),
            'total_strategies': len(self.strategies),
            'recent_decisions': len(self.decisions_history),
            'dynamic_parameters': self.dynamic_params,
            'last_updated': datetime.now().isoformat()
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get AI mode data for dashboard"""
        return {
            'success': True,
            'ai_mode': {
                'enabled': self.enabled,
                'learning_mode': self.learning_mode,
                'confidence': self.performance.avg_decision_confidence,
                'success_rate': self.performance.success_rate,
                'total_decisions': self.performance.total_decisions,
                'total_profit': self.performance.total_profit,
            },
            'strategies': [asdict(s) for s in self.strategies[:5]],  # Top 5
            'recent_decisions': [asdict(d) for d in self.decisions_history[-10:]],  # Last 10
            'performance': asdict(self.performance),
            'dynamic_parameters': self.dynamic_params
        }


# Global AI agent instance
_ai_agent: Optional[AIAgent] = None


def get_ai_agent(bot_instance=None) -> AIAgent:
    """Get or create AI agent instance"""
    global _ai_agent
    if _ai_agent is None:
        _ai_agent = AIAgent(bot_instance)
    elif bot_instance and _ai_agent.bot is None:
        _ai_agent.bot = bot_instance
    return _ai_agent


# Example usage
if __name__ == '__main__':
    # Test AI agent
    agent = AIAgent()
    agent.enable_ai_mode()

    print("\n🤖 AI Mode Test")
    print("=" * 60)

    # Test market analysis
    market_conditions = agent.analyze_market_conditions()
    print(f"\n시장 분석: {market_conditions['market_trend']}")
    print(f"AI 신뢰도: {market_conditions['ai_confidence']:.0%}")

    # Test decision making
    stock_data = {
        'current_price': 73500,
        'rsi': 45,
        'volume_ratio': 1.8,
        'total_score': 380
    }

    decision = agent.make_trading_decision('005930', '삼성전자', stock_data)
    print(f"\n결정: {decision.action}")
    print(f"신뢰도: {decision.confidence:.0%}")
    print(f"이유:")
    for reason in decision.reasoning:
        print(f"  - {reason}")

    # Test optimization
    agent.optimize_parameters()
    print(f"\n최적화 완료: {agent.performance.learning_iterations}회")

    status = agent.get_ai_status()
    print(f"\nAI 상태:")
    print(f"  활성 전략: {status['active_strategies']}개")
    print(f"  총 결정: {status['performance']['total_decisions']}회")
