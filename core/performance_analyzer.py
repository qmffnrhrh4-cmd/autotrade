"""
core/performance_analyzer.py
성능 분석 및 트레이딩 저널

거래별 분석, 귀인 분석, 월간 보고서, 통계적 유의성 검증
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date
from threading import Lock
from collections import defaultdict
from pathlib import Path
import statistics

logger = logging.getLogger(__name__)


@dataclass
class TradeAnalysis:
    """거래 분석"""
    trade_id: str
    timestamp: str
    stock_code: str
    stock_name: str
    trade_type: str          # buy/sell
    quantity: int
    entry_price: float
    exit_price: float = 0.0
    profit_loss: float = 0.0
    profit_loss_pct: float = 0.0
    holding_period_hours: float = 0.0
    strategy_name: str = ""
    ai_signal: str = ""
    ai_confidence: float = 0.0
    market_condition: str = ""
    entry_reason: str = ""
    exit_reason: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class DailyPerformance:
    """일일 성과"""
    date: str
    starting_capital: float
    ending_capital: float
    daily_pnl: float
    daily_return_pct: float
    trade_count: int
    win_count: int
    loss_count: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    best_trade: Optional[TradeAnalysis] = None
    worst_trade: Optional[TradeAnalysis] = None


@dataclass
class MonthlyReport:
    """월간 보고서"""
    year: int
    month: int
    starting_capital: float
    ending_capital: float
    total_pnl: float
    return_pct: float
    trade_count: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    best_day: str
    worst_day: str
    top_performers: List[Dict]
    worst_performers: List[Dict]
    strategy_performance: Dict[str, Dict]


class PerformanceAnalyzer:
    """
    성능 분석기

    기능:
    - 거래별 상세 분석
    - 일일/주간/월간 보고서
    - 전략별 성과 비교
    - 통계적 유의성 검증
    - 귀인 분석 (무엇이 수익에 기여했나)
    """

    _instance = None
    _lock = Lock()

    # 저장 경로
    ANALYSIS_DIR = Path("logs/performance")

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True

        # 데이터 저장소
        self.trades: List[TradeAnalysis] = []
        self.daily_performance: Dict[str, DailyPerformance] = {}
        self.equity_curve: List[Tuple[str, float]] = []

        # 전략별 통계
        self.strategy_stats: Dict[str, Dict] = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'losses': 0,
            'total_pnl': 0, 'total_profit': 0, 'total_loss': 0
        })

        # 종목별 통계
        self.stock_stats: Dict[str, Dict] = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'pnl': 0
        })

        # 초기 자본 (설정에서 로드)
        self.initial_capital = 10000000  # 1천만원 기본값

        # 디렉토리 생성
        self.ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

        # 이전 데이터 로드
        self._load_history()

        logger.info("성능 분석기 초기화 완료")

    @classmethod
    def get_instance(cls) -> 'PerformanceAnalyzer':
        return cls()

    def _load_history(self):
        """이전 데이터 로드"""
        try:
            history_file = self.ANALYSIS_DIR / "trade_history.json"
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # trades 복원은 복잡하므로 생략
                    self.initial_capital = data.get('initial_capital', self.initial_capital)
        except Exception as e:
            logger.debug(f"히스토리 로드 실패: {e}")

    def _save_history(self):
        """데이터 저장"""
        try:
            history_file = self.ANALYSIS_DIR / "trade_history.json"
            data = {
                'initial_capital': self.initial_capital,
                'total_trades': len(self.trades),
                'last_updated': datetime.now().isoformat()
            }
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"히스토리 저장 실패: {e}")

    def record_trade(
        self,
        stock_code: str,
        stock_name: str,
        trade_type: str,
        quantity: int,
        price: float,
        profit_loss: float = 0,
        strategy_name: str = "",
        ai_signal: str = "",
        ai_confidence: float = 0,
        reason: str = "",
        tags: List[str] = None
    ) -> TradeAnalysis:
        """거래 기록"""
        trade = TradeAnalysis(
            trade_id=f"T_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            timestamp=datetime.now().isoformat(),
            stock_code=stock_code,
            stock_name=stock_name,
            trade_type=trade_type,
            quantity=quantity,
            entry_price=price if trade_type == 'buy' else 0,
            exit_price=price if trade_type == 'sell' else 0,
            profit_loss=profit_loss,
            profit_loss_pct=(profit_loss / (price * quantity) * 100) if (price * quantity) > 0 else 0,
            strategy_name=strategy_name,
            ai_signal=ai_signal,
            ai_confidence=ai_confidence,
            entry_reason=reason if trade_type == 'buy' else "",
            exit_reason=reason if trade_type == 'sell' else "",
            tags=tags or []
        )

        self.trades.append(trade)

        # 전략별 통계 업데이트
        if strategy_name:
            stats = self.strategy_stats[strategy_name]
            stats['trades'] += 1
            if trade_type == 'sell':
                stats['total_pnl'] += profit_loss
                if profit_loss >= 0:
                    stats['wins'] += 1
                    stats['total_profit'] += profit_loss
                else:
                    stats['losses'] += 1
                    stats['total_loss'] += abs(profit_loss)

        # 종목별 통계 업데이트
        stock_stat = self.stock_stats[stock_code]
        stock_stat['trades'] += 1
        if trade_type == 'sell':
            stock_stat['pnl'] += profit_loss
            if profit_loss >= 0:
                stock_stat['wins'] += 1

        self._save_history()

        return trade

    def calculate_daily_performance(
        self,
        date_str: str,
        starting_capital: float,
        ending_capital: float
    ) -> DailyPerformance:
        """일일 성과 계산"""
        # 해당 날짜의 거래 필터링
        day_trades = [
            t for t in self.trades
            if t.timestamp.startswith(date_str) and t.trade_type == 'sell'
        ]

        daily_pnl = ending_capital - starting_capital
        daily_return = (daily_pnl / starting_capital * 100) if starting_capital > 0 else 0

        wins = [t for t in day_trades if t.profit_loss >= 0]
        losses = [t for t in day_trades if t.profit_loss < 0]

        total_profit = sum(t.profit_loss for t in wins)
        total_loss = abs(sum(t.profit_loss for t in losses))

        win_rate = (len(wins) / len(day_trades) * 100) if day_trades else 0
        avg_win = (total_profit / len(wins)) if wins else 0
        avg_loss = (total_loss / len(losses)) if losses else 0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')

        best_trade = max(day_trades, key=lambda t: t.profit_loss) if day_trades else None
        worst_trade = min(day_trades, key=lambda t: t.profit_loss) if day_trades else None

        perf = DailyPerformance(
            date=date_str,
            starting_capital=starting_capital,
            ending_capital=ending_capital,
            daily_pnl=daily_pnl,
            daily_return_pct=daily_return,
            trade_count=len(day_trades),
            win_count=len(wins),
            loss_count=len(losses),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=0,  # TODO: 실시간 계산
            best_trade=best_trade,
            worst_trade=worst_trade
        )

        self.daily_performance[date_str] = perf
        self.equity_curve.append((date_str, ending_capital))

        return perf

    def get_strategy_comparison(self) -> Dict[str, Dict]:
        """전략별 성과 비교"""
        comparison = {}

        for strategy, stats in self.strategy_stats.items():
            trades = stats['trades']
            wins = stats['wins']
            losses = stats['losses']
            total_pnl = stats['total_pnl']
            total_profit = stats['total_profit']
            total_loss = stats['total_loss']

            win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
            profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
            avg_pnl = (total_pnl / trades) if trades > 0 else 0

            comparison[strategy] = {
                'trades': trades,
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 0),
                'avg_pnl': round(avg_pnl, 0),
                'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 'INF'
            }

        return comparison

    def get_stock_ranking(self, top_n: int = 10) -> Tuple[List, List]:
        """종목별 순위 (최고/최악)"""
        stocks = []

        for code, stats in self.stock_stats.items():
            if stats['trades'] > 0:
                win_rate = (stats['wins'] / stats['trades'] * 100)
                stocks.append({
                    'stock_code': code,
                    'trades': stats['trades'],
                    'pnl': stats['pnl'],
                    'win_rate': win_rate
                })

        # PNL 기준 정렬
        sorted_by_pnl = sorted(stocks, key=lambda x: x['pnl'], reverse=True)

        top_performers = sorted_by_pnl[:top_n]
        worst_performers = sorted_by_pnl[-top_n:][::-1]

        return top_performers, worst_performers

    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.035) -> float:
        """샤프 비율 계산"""
        if len(returns) < 2:
            return 0

        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)

        if std_return == 0:
            return 0

        # 연율화 (일일 수익률 가정)
        annualized_return = avg_return * 252
        annualized_std = std_return * (252 ** 0.5)

        sharpe = (annualized_return - risk_free_rate) / annualized_std

        return round(sharpe, 2)

    def calculate_max_drawdown(self) -> Tuple[float, str, str]:
        """최대 낙폭 계산"""
        if len(self.equity_curve) < 2:
            return 0, "", ""

        peak = self.equity_curve[0][1]
        max_dd = 0
        peak_date = self.equity_curve[0][0]
        trough_date = ""

        for date_str, value in self.equity_curve:
            if value > peak:
                peak = value
                peak_date = date_str

            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
                trough_date = date_str

        return round(max_dd * 100, 2), peak_date, trough_date

    def generate_monthly_report(self, year: int, month: int) -> MonthlyReport:
        """월간 보고서 생성"""
        month_str = f"{year}-{month:02d}"

        # 해당 월의 일일 성과 필터링
        month_perfs = [
            perf for date_str, perf in self.daily_performance.items()
            if date_str.startswith(month_str)
        ]

        if not month_perfs:
            return None

        # 집계
        starting_capital = month_perfs[0].starting_capital if month_perfs else self.initial_capital
        ending_capital = month_perfs[-1].ending_capital if month_perfs else starting_capital
        total_pnl = sum(p.daily_pnl for p in month_perfs)
        return_pct = (total_pnl / starting_capital * 100) if starting_capital > 0 else 0

        trade_count = sum(p.trade_count for p in month_perfs)
        win_count = sum(p.win_count for p in month_perfs)
        loss_count = sum(p.loss_count for p in month_perfs)
        win_rate = (win_count / (win_count + loss_count) * 100) if (win_count + loss_count) > 0 else 0

        # 수익/손실 합계
        total_profit = sum(p.daily_pnl for p in month_perfs if p.daily_pnl >= 0)
        total_loss = abs(sum(p.daily_pnl for p in month_perfs if p.daily_pnl < 0))
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')

        # 샤프 비율
        daily_returns = [p.daily_return_pct / 100 for p in month_perfs]
        sharpe = self.calculate_sharpe_ratio(daily_returns)

        # 최고/최악 날
        best_day = max(month_perfs, key=lambda p: p.daily_pnl)
        worst_day = min(month_perfs, key=lambda p: p.daily_pnl)

        # 종목별 순위
        top_performers, worst_performers = self.get_stock_ranking(5)

        report = MonthlyReport(
            year=year,
            month=month,
            starting_capital=starting_capital,
            ending_capital=ending_capital,
            total_pnl=total_pnl,
            return_pct=round(return_pct, 2),
            trade_count=trade_count,
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2) if profit_factor != float('inf') else 999,
            sharpe_ratio=sharpe,
            max_drawdown=self.calculate_max_drawdown()[0],
            best_day=best_day.date,
            worst_day=worst_day.date,
            top_performers=top_performers,
            worst_performers=worst_performers,
            strategy_performance=self.get_strategy_comparison()
        )

        # 보고서 저장
        report_file = self.ANALYSIS_DIR / f"monthly_{year}_{month:02d}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2, default=str)

        return report

    def get_attribution_analysis(self) -> Dict[str, Any]:
        """귀인 분석 - 수익의 원천 분석"""
        analysis = {
            'by_strategy': {},
            'by_market_condition': defaultdict(lambda: {'pnl': 0, 'trades': 0}),
            'by_ai_signal': defaultdict(lambda: {'pnl': 0, 'trades': 0}),
            'by_holding_period': defaultdict(lambda: {'pnl': 0, 'trades': 0}),
            'by_day_of_week': defaultdict(lambda: {'pnl': 0, 'trades': 0}),
        }

        for trade in self.trades:
            if trade.trade_type != 'sell':
                continue

            pnl = trade.profit_loss

            # 전략별
            if trade.strategy_name:
                if trade.strategy_name not in analysis['by_strategy']:
                    analysis['by_strategy'][trade.strategy_name] = {'pnl': 0, 'trades': 0}
                analysis['by_strategy'][trade.strategy_name]['pnl'] += pnl
                analysis['by_strategy'][trade.strategy_name]['trades'] += 1

            # AI 시그널별
            if trade.ai_signal:
                analysis['by_ai_signal'][trade.ai_signal]['pnl'] += pnl
                analysis['by_ai_signal'][trade.ai_signal]['trades'] += 1

            # 보유 기간별
            if trade.holding_period_hours > 0:
                if trade.holding_period_hours < 1:
                    period = 'scalping'
                elif trade.holding_period_hours < 24:
                    period = 'day_trade'
                elif trade.holding_period_hours < 168:
                    period = 'swing'
                else:
                    period = 'position'
                analysis['by_holding_period'][period]['pnl'] += pnl
                analysis['by_holding_period'][period]['trades'] += 1

            # 요일별
            try:
                dt = datetime.fromisoformat(trade.timestamp.replace('Z', '+00:00'))
                day = dt.strftime('%A')
                analysis['by_day_of_week'][day]['pnl'] += pnl
                analysis['by_day_of_week'][day]['trades'] += 1
            except Exception:
                pass

        return analysis

    def get_summary(self) -> Dict[str, Any]:
        """전체 요약"""
        sell_trades = [t for t in self.trades if t.trade_type == 'sell']

        if not sell_trades:
            return {'message': '거래 데이터 없음'}

        total_pnl = sum(t.profit_loss for t in sell_trades)
        wins = [t for t in sell_trades if t.profit_loss >= 0]
        losses = [t for t in sell_trades if t.profit_loss < 0]

        total_profit = sum(t.profit_loss for t in wins)
        total_loss = abs(sum(t.profit_loss for t in losses))

        return {
            'total_trades': len(sell_trades),
            'total_pnl': round(total_pnl, 0),
            'win_count': len(wins),
            'loss_count': len(losses),
            'win_rate': round(len(wins) / len(sell_trades) * 100, 2) if sell_trades else 0,
            'avg_win': round(total_profit / len(wins), 0) if wins else 0,
            'avg_loss': round(total_loss / len(losses), 0) if losses else 0,
            'profit_factor': round(total_profit / total_loss, 2) if total_loss > 0 else 'INF',
            'max_drawdown': self.calculate_max_drawdown()[0],
            'strategy_count': len(self.strategy_stats),
            'stock_count': len(self.stock_stats)
        }


# 전역 접근 함수
def get_performance_analyzer() -> PerformanceAnalyzer:
    return PerformanceAnalyzer.get_instance()


def record_trade(**kwargs) -> TradeAnalysis:
    """거래 기록 편의 함수"""
    return get_performance_analyzer().record_trade(**kwargs)
