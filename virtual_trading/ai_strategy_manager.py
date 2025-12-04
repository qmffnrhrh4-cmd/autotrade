"""
virtual_trading/ai_strategy_manager.py
AI 기반 자동 전략 생성/검토/개선 시스템

5가지 전략을 자동으로 관리하고 성과에 따라 개선/교체
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


class AIStrategyManager:
    """AI 기반 전략 자동 관리 시스템"""

    def __init__(self, virtual_manager, data_fetcher):
        """
        Args:
            virtual_manager: VirtualTradingManager 인스턴스
            data_fetcher: DataFetcher 인스턴스
        """
        self.virtual_manager = virtual_manager
        self.data_fetcher = data_fetcher

        # 5가지 전략 템플릿 (다양한 투자 성향)
        self.strategy_templates = [
            {
                'name': 'AI-보수형',
                'description': 'AI 추천 보수적 장기투자 전략 (안정성 중시)',
                'risk_level': 'low',
                'stop_loss': 3.0,
                'take_profit': 8.0,
                'holding_period_target': 30,
                'characteristics': ['장기보유', '저변동성', '우량주']
            },
            {
                'name': 'AI-균형형',
                'description': 'AI 추천 균형잡힌 중기투자 전략',
                'risk_level': 'medium',
                'stop_loss': 5.0,
                'take_profit': 12.0,
                'holding_period_target': 15,
                'characteristics': ['중기보유', '중변동성', '성장주']
            },
            {
                'name': 'AI-공격형',
                'description': 'AI 추천 공격적 단기투자 전략 (수익성 중시)',
                'risk_level': 'high',
                'stop_loss': 7.0,
                'take_profit': 20.0,
                'holding_period_target': 5,
                'characteristics': ['단기매매', '고변동성', '모멘텀']
            },
            {
                'name': 'AI-가치형',
                'description': 'AI 추천 가치투자 전략 (저평가 발굴)',
                'risk_level': 'low',
                'stop_loss': 4.0,
                'take_profit': 15.0,
                'holding_period_target': 45,
                'characteristics': ['가치투자', '저PER', '안정배당']
            },
            {
                'name': 'AI-혁신형',
                'description': 'AI 추천 혁신성장 전략 (신기술/테마)',
                'risk_level': 'high',
                'stop_loss': 8.0,
                'take_profit': 25.0,
                'holding_period_target': 10,
                'characteristics': ['테마투자', '신기술', '고성장']
            }
        ]

        self.active_strategy_ids = []
        logger.info("AI 전략 관리자 초기화 완료")

    def initialize_strategies(self, initial_capital: int = 10000000) -> List[int]:
        """
        5가지 AI 전략 자동 생성

        Args:
            initial_capital: 각 전략의 초기 자본금

        Returns:
            생성된 전략 ID 리스트
        """
        logger.info("🤖 AI가 5가지 전략을 자동 생성합니다...")

        strategy_ids = []

        for template in self.strategy_templates:
            try:
                # create_strategy가 get-or-create 패턴이므로 직접 호출
                # 이미 존재하면 기존 ID 반환, 없으면 새로 생성
                strategy_id = self.virtual_manager.create_strategy(
                    name=template['name'],
                    description=template['description'],
                    initial_capital=initial_capital
                )

                strategy_ids.append(strategy_id)
                logger.info(f"✅ {template['name']} 준비 완료 (ID: {strategy_id})")

            except Exception as e:
                logger.error(f"❌ {template['name']} 처리 실패: {e}", exc_info=True)

        self.active_strategy_ids = strategy_ids
        logger.info(f"🎉 5가지 AI 전략 준비 완료: {strategy_ids}")

        return strategy_ids

    def review_strategies(self) -> Dict[str, Any]:
        """
        모든 전략의 성과를 AI가 자동 검토

        Returns:
            검토 결과 딕셔너리
        """
        logger.info("🔍 AI가 전략 성과를 검토합니다...")

        reviews = []

        for strategy_id in self.active_strategy_ids:
            try:
                # 전략 성과 지표 조회
                metrics = self.virtual_manager.get_performance_metrics(strategy_id)

                if not metrics:
                    continue

                # AI 평가
                evaluation = self._evaluate_strategy(metrics)

                reviews.append({
                    'strategy_id': strategy_id,
                    'name': metrics.get('name', 'Unknown'),
                    'metrics': metrics,
                    'evaluation': evaluation
                })

                logger.info(
                    f"📊 {metrics.get('name')}: "
                    f"수익률 {metrics.get('return_rate', 0):.2f}%, "  # Fix: 올바른 키 이름
                    f"승률 {metrics.get('win_rate', 0):.1f}%, "
                    f"평가 {evaluation['grade']}"
                )

            except Exception as e:
                logger.error(f"전략 {strategy_id} 검토 실패: {e}")

        # 종합 평가
        summary = self._generate_summary(reviews)

        return {
            'timestamp': datetime.now().isoformat(),
            'reviews': reviews,
            'summary': summary
        }

    def _evaluate_strategy(self, metrics: Dict) -> Dict[str, Any]:
        """
        AI가 전략 성과를 평가

        Args:
            metrics: 성과 지표

        Returns:
            평가 결과
        """
        total_return = metrics.get('return_rate', 0)  # Fix: 올바른 키 이름
        win_rate = metrics.get('win_rate', 0)
        trade_count = metrics.get('trade_count', 0)

        # 점수 계산 (0-100)
        score = 0

        # 수익률 점수 (0-50점)
        if total_return >= 20:
            score += 50
        elif total_return >= 10:
            score += 40
        elif total_return >= 5:
            score += 30
        elif total_return >= 0:
            score += 20
        else:
            score += max(0, 20 + total_return)  # 손실률에 따라 감점

        # 승률 점수 (0-30점)
        if win_rate >= 70:
            score += 30
        elif win_rate >= 60:
            score += 25
        elif win_rate >= 50:
            score += 20
        else:
            score += max(0, win_rate / 3)

        # 거래 횟수 점수 (0-20점)
        if trade_count >= 10:
            score += 20
        elif trade_count >= 5:
            score += 15
        elif trade_count >= 3:
            score += 10
        else:
            score += trade_count * 3

        # 등급 판정
        if score >= 80:
            grade = 'S'
            recommendation = '우수 - 실제 매매 적용 추천'
        elif score >= 70:
            grade = 'A'
            recommendation = '양호 - 현재 전략 유지'
        elif score >= 60:
            grade = 'B'
            recommendation = '보통 - 일부 개선 필요'
        elif score >= 50:
            grade = 'C'
            recommendation = '미흡 - 전략 개선 필요'
        else:
            grade = 'D'
            recommendation = '불량 - 전략 교체 권장'

        return {
            'score': score,
            'grade': grade,
            'recommendation': recommendation,
            'strengths': self._identify_strengths(metrics),
            'weaknesses': self._identify_weaknesses(metrics)
        }

    def _identify_strengths(self, metrics: Dict) -> List[str]:
        """전략의 강점 파악"""
        strengths = []

        if metrics.get('total_return_rate', 0) >= 10:
            strengths.append('높은 수익률')
        if metrics.get('win_rate', 0) >= 65:
            strengths.append('높은 승률')
        if metrics.get('max_gain_rate', 0) >= 15:
            strengths.append('큰 수익 포텐셜')
        if metrics.get('average_holding_days', 999) <= 5:
            strengths.append('빠른 회전율')

        return strengths if strengths else ['개선 가능성']

    def _identify_weaknesses(self, metrics: Dict) -> List[str]:
        """전략의 약점 파악"""
        weaknesses = []

        if metrics.get('total_return_rate', 0) < 0:
            weaknesses.append('마이너스 수익률')
        if metrics.get('win_rate', 0) < 45:
            weaknesses.append('낮은 승률')
        if metrics.get('max_loss_rate', 0) < -10:
            weaknesses.append('큰 손실 위험')
        if metrics.get('trade_count', 0) < 3:
            weaknesses.append('거래 횟수 부족')

        return weaknesses if weaknesses else ['없음']

    def _generate_summary(self, reviews: List[Dict]) -> Dict[str, Any]:
        """종합 평가 요약"""
        if not reviews:
            return {'message': '평가할 전략이 없습니다'}

        # 최고/최악 전략
        best_strategy = max(reviews, key=lambda x: x['evaluation']['score'])
        worst_strategy = min(reviews, key=lambda x: x['evaluation']['score'])

        # 평균 점수
        avg_score = sum(r['evaluation']['score'] for r in reviews) / len(reviews)

        return {
            'total_strategies': len(reviews),
            'average_score': avg_score,
            'best_strategy': {
                'name': best_strategy['name'],
                'score': best_strategy['evaluation']['score'],
                'grade': best_strategy['evaluation']['grade']
            },
            'worst_strategy': {
                'name': worst_strategy['name'],
                'score': worst_strategy['evaluation']['score'],
                'grade': worst_strategy['evaluation']['grade']
            }
        }

    def improve_strategies(self, backtest_period_days: int = 90) -> Dict[str, Any]:
        """
        AI가 자동으로 전략을 개선

        Args:
            backtest_period_days: 백테스팅 기간 (일)

        Returns:
            개선 결과
        """
        logger.info("🔧 AI가 전략을 자동 개선합니다...")

        improvements = []

        # 종목 풀 (코스피 대형주)
        test_stocks = ['005930', '000660', '035420', '051910', '006400']  # 삼성전자, SK하이닉스, NAVER, LG화학, 삼성SDI

        for strategy_id in self.active_strategy_ids:
            try:
                # 현재 성과 확인
                metrics = self.virtual_manager.get_performance_metrics(strategy_id)

                if not metrics:
                    continue

                current_return = metrics.get('total_return_rate', 0)

                # 성과가 나쁜 전략만 개선
                if current_return < 3.0:  # 수익률 3% 미만
                    logger.info(f"🔨 {metrics.get('name')} 개선 시작 (현재 수익률: {current_return:.2f}%)")

                    # 랜덤 종목으로 백테스팅
                    test_stock = random.choice(test_stocks)
                    end_date = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=backtest_period_days)).strftime('%Y%m%d')

                    from .backtest_adapter import BacktestAdapter
                    adapter = BacktestAdapter(self.virtual_manager, self.data_fetcher)

                    backtest_result = adapter.run_backtest(
                        strategy_id=strategy_id,
                        stock_code=test_stock,
                        start_date=start_date,
                        end_date=end_date
                    )

                    if 'error' not in backtest_result:
                        best = backtest_result['best_result']

                        improvements.append({
                            'strategy_id': strategy_id,
                            'name': metrics.get('name'),
                            'before_return': current_return,
                            'tested_stock': test_stock,
                            'optimal_conditions': {
                                'stop_loss': best['stop_loss_percent'],
                                'take_profit': best['take_profit_percent']
                            },
                            'expected_improvement': best['return_rate']
                        })

                        logger.info(
                            f"✨ {metrics.get('name')} 최적 조건 발견: "
                            f"손절 {best['stop_loss_percent']}%, "
                            f"익절 {best['take_profit_percent']}% "
                            f"(예상 수익률: {best['return_rate']:.2f}%)"
                        )

            except Exception as e:
                logger.error(f"전략 {strategy_id} 개선 실패: {e}")

        return {
            'timestamp': datetime.now().isoformat(),
            'improvements': improvements,
            'improved_count': len(improvements)
        }

    def get_best_strategy_for_real_trading(self) -> Optional[Dict[str, Any]]:
        """
        실제 매매에 적용할 최고 성과 전략 선택

        Returns:
            최고 성과 전략 정보
        """
        logger.info("🏆 실제 매매 적용 전략을 선택합니다...")

        best_strategy = None
        best_score = -999

        for strategy_id in self.active_strategy_ids:
            try:
                metrics = self.virtual_manager.get_performance_metrics(strategy_id)

                if not metrics:
                    continue

                evaluation = self._evaluate_strategy(metrics)

                if evaluation['score'] > best_score:
                    best_score = evaluation['score']
                    best_strategy = {
                        'strategy_id': strategy_id,
                        'name': metrics.get('name'),
                        'metrics': metrics,
                        'evaluation': evaluation
                    }

            except Exception as e:
                logger.error(f"전략 {strategy_id} 평가 실패: {e}")

        if best_strategy:
            logger.info(
                f"🎖️ 최고 성과 전략: {best_strategy['name']} "
                f"(점수: {best_score:.0f}, 등급: {best_strategy['evaluation']['grade']})"
            )

        return best_strategy

    def auto_manage_strategies(self) -> Dict[str, Any]:
        """
        AI가 전략을 자동으로 관리 (검토 → 개선 → 추천)

        Returns:
            관리 결과 종합
        """
        logger.info("🤖 AI 자동 전략 관리를 시작합니다...")

        # 1. 전략 검토
        review_result = self.review_strategies()

        # 2. 전략 개선
        improvement_result = self.improve_strategies()

        # 3. 최고 전략 선택
        best_strategy = self.get_best_strategy_for_real_trading()

        return {
            'timestamp': datetime.now().isoformat(),
            'review': review_result,
            'improvement': improvement_result,
            'recommended_for_real_trading': best_strategy
        }
