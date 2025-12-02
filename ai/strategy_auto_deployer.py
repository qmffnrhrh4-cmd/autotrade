"""
전략 자동 배포 시스템 (Strategy Auto-Deployment System)

최우수 전략을 자동으로 가상매매에 배포하고 성과를 모니터링합니다.
"""
import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from utils.logger_new import get_logger

logger = get_logger()


@dataclass
class DeployedStrategy:
    """배포된 전략 정보"""
    strategy_id: int  # evolved_strategies.id
    generation: int
    virtual_trading_id: int  # virtual trading strategy id
    fitness_score: float
    backtest_metrics: Dict[str, float]
    deployed_at: datetime
    last_check_at: Optional[datetime] = None
    trades_count: int = 0
    live_return_pct: float = 0.0
    status: str = "active"  # active, underperforming, replaced


class StrategyAutoDeployer:
    """전략 자동 배포 및 관리 (강화된 실시간 모니터링)"""

    def __init__(
        self,
        evolution_db_path: str = "data/strategy_evolution.db",
        virtual_trading_manager = None,
        performance_threshold: float = -0.30,  # 백테스팅 대비 -30% 이하 시 교체
        min_trades_before_replace: int = 10,    # 최소 10회 거래 후 교체 가능
        check_interval_seconds: int = 1800,     # 30분마다 체크 (더 빈번하게)
        alert_threshold: float = -0.15,         # -15% 이하 시 경고
        max_deployed_strategies: int = 3        # 최대 동시 배포 전략 수
    ):
        """초기화"""
        self.evolution_db_path = evolution_db_path
        self.vt_manager = virtual_trading_manager
        self.performance_threshold = performance_threshold
        self.alert_threshold = alert_threshold
        self.min_trades_before_replace = min_trades_before_replace
        self.check_interval = check_interval_seconds
        self.max_deployed_strategies = max_deployed_strategies

        # 배포된 전략 추적
        self.deployed_strategies: Dict[int, DeployedStrategy] = {}
        self.running = False

        # 성과 추적 히스토리
        self.performance_history: List[Dict[str, Any]] = []

        logger.info("전략 자동 배포 시스템 초기화 완료 (강화 버전)")
        logger.info(f"  - 성과 임계값: {performance_threshold * 100:.1f}%")
        logger.info(f"  - 경고 임계값: {alert_threshold * 100:.1f}%")
        logger.info(f"  - 최소 거래 횟수: {min_trades_before_replace}")
        logger.info(f"  - 체크 주기: {check_interval_seconds}초")
        logger.info(f"  - 최대 동시 배포: {max_deployed_strategies}개")

    def get_best_strategy(self, top_n: int = 1) -> List[Dict[str, Any]]:
        """
        최우수 전략 조회

        Args:
            top_n: 상위 N개 전략

        Returns:
            전략 정보 리스트 (genes, fitness_score, metrics 포함)
        """
        try:
            conn = sqlite3.connect(self.evolution_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    es.id, es.generation, es.genes,
                    fr.fitness_score, fr.total_return_pct, fr.sharpe_ratio,
                    fr.win_rate, fr.max_drawdown_pct, fr.profit_factor,
                    fr.total_trades
                FROM evolved_strategies es
                JOIN fitness_results fr ON es.id = fr.strategy_id
                ORDER BY fr.fitness_score DESC
                LIMIT ?
            """, (top_n,))

            strategies = []
            for row in cursor.fetchall():
                strategies.append({
                    'id': row['id'],
                    'generation': row['generation'],
                    'genes': json.loads(row['genes']),
                    'fitness_score': row['fitness_score'],
                    'metrics': {
                        'total_return_pct': row['total_return_pct'],
                        'sharpe_ratio': row['sharpe_ratio'],
                        'win_rate': row['win_rate'],
                        'max_drawdown_pct': row['max_drawdown_pct'],
                        'profit_factor': row['profit_factor'],
                        'total_trades': row['total_trades']
                    }
                })

            conn.close()
            return strategies

        except Exception as e:
            logger.error(f"최우수 전략 조회 실패: {e}")
            return []

    def deploy_strategy(self, strategy_info: Dict[str, Any]) -> Optional[int]:
        """
        전략을 가상매매에 배포

        Args:
            strategy_info: get_best_strategy()에서 반환된 전략 정보

        Returns:
            배포된 가상매매 전략 ID (실패시 None)
        """
        if not self.vt_manager:
            logger.warning("VirtualTradingManager가 없어 배포 불가")
            return None

        try:
            genes = strategy_info['genes']
            generation = strategy_info['generation']
            fitness = strategy_info['fitness_score']

            # 전략 이름 생성 (타임스탬프 포함으로 중복 방지)
            from datetime import datetime
            timestamp = datetime.now().strftime('%H%M%S')
            strategy_name = f"AI-진화-G{generation}-F{fitness:.1f}-{timestamp}"
            description = self._create_strategy_description(genes, strategy_info['metrics'])

            # 가상매매 전략 생성
            vt_strategy_id = self.vt_manager.create_strategy(
                name=strategy_name,
                description=description,
                initial_capital=10000000
            )

            # 배포 기록
            deployed = DeployedStrategy(
                strategy_id=strategy_info['id'],
                generation=generation,
                virtual_trading_id=vt_strategy_id,
                fitness_score=fitness,
                backtest_metrics=strategy_info['metrics'],
                deployed_at=datetime.now()
            )

            self.deployed_strategies[strategy_info['id']] = deployed

            logger.info(f"✅ 전략 배포 완료: {strategy_name} (VT ID: {vt_strategy_id})")
            logger.info(f"   백테스팅 성과: 수익률 {strategy_info['metrics']['total_return_pct']:.2f}%, "
                       f"승률 {strategy_info['metrics']['win_rate']:.2f}%")

            return vt_strategy_id

        except Exception as e:
            logger.error(f"전략 배포 실패: {e}")
            return None

    def _create_strategy_description(self, genes: Dict[str, Any], metrics: Dict[str, float]) -> str:
        """전략 설명 생성"""
        return f"""AI 진화 전략 (자동 배포)

📊 백테스팅 성과:
- 수익률: {metrics['total_return_pct']:.2f}%
- 샤프비율: {metrics['sharpe_ratio']:.2f}
- 승률: {metrics['win_rate']:.2f}%
- 최대낙폭: {metrics['max_drawdown_pct']:.2f}%
- 손익비: {metrics['profit_factor']:.2f}
- 거래횟수: {metrics['total_trades']}

📋 매수 조건:
- RSI: {genes['buy_rsi_min']:.1f} ~ {genes['buy_rsi_max']:.1f}
- 거래량비율: {genes['buy_volume_ratio_min']:.2f}x 이상
- 호가비율: {genes['buy_bid_ask_ratio_min']:.2f}x 이상
- 거래시간: {genes['trade_time_start']} ~ {genes['trade_time_end']}
- 가격범위: {genes['min_price']:,.0f}원 ~ {genes['max_price']:,.0f}원

📋 매도 조건:
- 익절: +{genes['sell_take_profit'] * 100:.1f}%
- 손절: {genes['sell_stop_loss'] * 100:.1f}%
- 추적손절: -{genes['sell_trailing_stop'] * 100:.1f}%
- RSI 과매수: {genes['sell_rsi_min']:.1f} ~ {genes['sell_rsi_max']:.1f}

💰 포지션 크기: 계좌의 {genes['position_size_pct'] * 100:.1f}%
"""

    def check_deployed_strategies_performance(self) -> List[Tuple[int, str]]:
        """
        배포된 전략들의 성과 체크 (강화 버전)

        Returns:
            [(strategy_id, status), ...] - 교체가 필요한 전략 목록
        """
        if not self.vt_manager:
            return []

        underperforming = []
        alerts = []

        logger.info("=" * 60)
        logger.info(f"📊 배포 전략 성과 체크 시작 ({len([d for d in self.deployed_strategies.values() if d.status == 'active'])}개 활성)")
        logger.info("=" * 60)

        for strategy_id, deployed in self.deployed_strategies.items():
            if deployed.status != "active":
                continue

            try:
                # 가상매매 전략 성과 조회
                vt_strategy = self._get_virtual_trading_performance(deployed.virtual_trading_id)

                if not vt_strategy:
                    logger.warning(f"전략 {strategy_id}: 성과 데이터 없음")
                    continue

                # 거래 횟수 체크
                trades_count = vt_strategy.get('total_trades', 0)
                win_rate = vt_strategy.get('win_rate', 0)

                if trades_count < self.min_trades_before_replace:
                    logger.info(f"전략 {strategy_id}: 거래 횟수 부족 ({trades_count}/{self.min_trades_before_replace}) - 대기 중")
                    continue

                # 성과 비교
                backtest_return = deployed.backtest_metrics['total_return_pct']
                live_return = vt_strategy.get('total_return_pct', 0)
                performance_ratio = (live_return - backtest_return) / abs(backtest_return) if backtest_return != 0 else 0

                deployed.trades_count = trades_count
                deployed.live_return_pct = live_return
                deployed.last_check_at = datetime.now()

                # 성과 히스토리 기록
                self.performance_history.append({
                    'strategy_id': strategy_id,
                    'timestamp': datetime.now().isoformat(),
                    'backtest_return': backtest_return,
                    'live_return': live_return,
                    'performance_ratio': performance_ratio,
                    'trades_count': trades_count,
                    'win_rate': win_rate
                })

                # 최근 100개만 유지
                if len(self.performance_history) > 100:
                    self.performance_history = self.performance_history[-100:]

                # 상세 로깅
                logger.info(f"전략 {strategy_id} (세대 {deployed.generation}, VT ID: {deployed.virtual_trading_id}):")
                logger.info(f"  백테스팅 수익률: {backtest_return:+.2f}%")
                logger.info(f"  실전 수익률:     {live_return:+.2f}%")
                logger.info(f"  성과비율:       {performance_ratio * 100:+.1f}%")
                logger.info(f"  거래횟수:       {trades_count}회 (승률: {win_rate:.1f}%)")

                # 경고 임계값 체크
                if self.alert_threshold <= performance_ratio < self.performance_threshold:
                    logger.warning(f"⚠️  경고: 전략 {strategy_id} 성과 저하 중 ({performance_ratio * 100:+.1f}%)")
                    alerts.append((strategy_id, "warning", performance_ratio))

                # 교체 임계값 체크
                if performance_ratio < self.performance_threshold:
                    logger.error(f"🚨 심각: 전략 {strategy_id} 성과 저하 심각! 교체 필요")
                    logger.error(f"   백테스팅 대비 {abs(performance_ratio) * 100:.1f}% 저조")
                    deployed.status = "underperforming"
                    underperforming.append((strategy_id, "underperforming"))
                elif performance_ratio > 0:
                    logger.info(f"✅ 양호: 백테스팅 대비 {performance_ratio * 100:+.1f}% 우수")

            except Exception as e:
                logger.error(f"전략 {strategy_id} 성과 체크 실패: {e}", exc_info=True)

        logger.info("=" * 60)
        logger.info(f"체크 완료: 경고 {len(alerts)}개, 교체 필요 {len(underperforming)}개")
        logger.info("=" * 60)

        return underperforming

    def _get_virtual_trading_performance(self, vt_strategy_id: int) -> Optional[Dict[str, Any]]:
        """가상매매 전략 성과 조회"""
        if not self.vt_manager:
            return None

        try:
            # VirtualTradingDB를 통해 성과 조회
            strategies = self.vt_manager.db.get_all_strategies()
            strategy = next((s for s in strategies if s['id'] == vt_strategy_id), None)

            if not strategy:
                return None

            # 포지션 조회
            positions = self.vt_manager.db.get_positions_by_strategy(vt_strategy_id)
            closed_positions = [p for p in positions if p['status'] == 'closed']

            # 성과 계산
            total_trades = len(closed_positions)
            winning_trades = len([p for p in closed_positions if p['profit_loss'] > 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            total_profit = sum(p['profit_loss'] for p in closed_positions)
            total_return_pct = (total_profit / strategy['initial_capital']) * 100

            return {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_return_pct': total_return_pct,
                'winning_trades': winning_trades,
                'total_profit': total_profit
            }

        except Exception as e:
            logger.error(f"가상매매 성과 조회 실패: {e}")
            return None

    def replace_underperforming_strategy(self, old_strategy_id: int) -> bool:
        """
        성과 저하 전략을 다음 순위 전략으로 교체

        Args:
            old_strategy_id: 교체할 전략 ID

        Returns:
            성공 여부
        """
        try:
            old_deployed = self.deployed_strategies.get(old_strategy_id)
            if not old_deployed:
                logger.error(f"전략 {old_strategy_id}를 찾을 수 없음")
                return False

            # 기존 전략 비활성화
            old_deployed.status = "replaced"
            logger.info(f"전략 {old_strategy_id} 비활성화 (가상매매 ID: {old_deployed.virtual_trading_id})")

            # 다음 순위 전략 조회 (현재 배포되지 않은 전략 중 최우수)
            all_strategies = self.get_best_strategy(top_n=20)
            deployed_ids = set(d.strategy_id for d in self.deployed_strategies.values() if d.status == "active")

            next_strategy = None
            for strategy in all_strategies:
                if strategy['id'] not in deployed_ids:
                    next_strategy = strategy
                    break

            if not next_strategy:
                logger.warning("교체할 다음 전략이 없음")
                return False

            # 새 전략 배포
            new_vt_id = self.deploy_strategy(next_strategy)
            if new_vt_id:
                logger.info(f"✅ 전략 교체 완료: {old_strategy_id} → {next_strategy['id']}")
                return True
            else:
                logger.error("새 전략 배포 실패")
                return False

        except Exception as e:
            logger.error(f"전략 교체 실패: {e}")
            return False

    def run_continuous_monitoring(self):
        """지속적 성과 모니터링 (별도 스레드에서 실행)"""
        self.running = True
        logger.info("🔍 지속적 성과 모니터링 시작")

        while self.running:
            try:
                # 배포된 전략 성과 체크
                underperforming = self.check_deployed_strategies_performance()

                # 성과 저하 전략 교체
                for strategy_id, status in underperforming:
                    if status == "underperforming":
                        self.replace_underperforming_strategy(strategy_id)

                # 대기
                logger.info(f"⏰ {self.check_interval}초 후 다음 체크...")
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"모니터링 중 오류: {e}")
                time.sleep(60)  # 오류 발생 시 1분 대기

        logger.info("🏁 지속적 성과 모니터링 종료")

    def stop(self):
        """모니터링 중지"""
        self.running = False

    def get_deployment_status(self) -> Dict[str, Any]:
        """배포 현황 조회"""
        active_count = sum(1 for d in self.deployed_strategies.values() if d.status == "active")
        replaced_count = sum(1 for d in self.deployed_strategies.values() if d.status == "replaced")

        active_strategies = []
        for strategy_id, deployed in self.deployed_strategies.items():
            if deployed.status == "active":
                active_strategies.append({
                    'strategy_id': strategy_id,
                    'generation': deployed.generation,
                    'vt_id': deployed.virtual_trading_id,
                    'fitness_score': deployed.fitness_score,
                    'backtest_return': deployed.backtest_metrics['total_return_pct'],
                    'live_return': deployed.live_return_pct,
                    'trades_count': deployed.trades_count,
                    'deployed_at': deployed.deployed_at.isoformat() if deployed.deployed_at else None,
                    'last_check': deployed.last_check_at.isoformat() if deployed.last_check_at else None
                })

        return {
            'total_deployed': len(self.deployed_strategies),
            'active': active_count,
            'replaced': replaced_count,
            'active_strategies': active_strategies
        }


__all__ = ['StrategyAutoDeployer', 'DeployedStrategy']
