"""
virtual_trading/backtest_adapter.py
백테스팅 결과를 가상매매 시스템에 연동

과거 데이터로 전략 검증 및 최적 조건 탐색
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BacktestAdapter:
    """백테스팅 결과를 가상매매에 연동하는 어댑터"""

    def __init__(self, virtual_manager, data_fetcher):
        """
        Args:
            virtual_manager: VirtualTradingManager 인스턴스
            data_fetcher: DataFetcher 인스턴스 (과거 데이터 조회)
        """
        self.virtual_manager = virtual_manager
        self.data_fetcher = data_fetcher
        logger.info("백테스팅 어댑터 초기화")

    def run_backtest(
        self,
        strategy_id: int,
        stock_code: str,
        start_date: str,
        end_date: str,
        stop_loss_percents: List[float] = [3.0, 5.0, 7.0],
        take_profit_percents: List[float] = [5.0, 10.0, 15.0]
    ) -> Dict[str, Any]:
        """
        과거 데이터로 백테스팅 실행

        Args:
            strategy_id: 가상매매 전략 ID
            stock_code: 종목코드
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            stop_loss_percents: 테스트할 손절 비율 리스트
            take_profit_percents: 테스트할 익절 비율 리스트

        Returns:
            백테스팅 결과 딕셔너리
        """
        logger.info(f"백테스팅 시작: {stock_code} ({start_date} ~ {end_date})")

        # 과거 일봉 데이터 조회
        try:
            daily_data = self.data_fetcher.get_daily_price(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date
            )

            if not daily_data:
                logger.error(f"과거 데이터 조회 실패: {stock_code}")
                return {'error': '과거 데이터 없음'}

            logger.info(f"과거 데이터 조회 완료: {len(daily_data)}일")

        except Exception as e:
            logger.error(f"과거 데이터 조회 실패: {e}")
            return {'error': str(e)}

        # 모든 손절/익절 조합 테스트
        results = []

        for stop_loss in stop_loss_percents:
            for take_profit in take_profit_percents:
                result = self._simulate_trades(
                    stock_code=stock_code,
                    daily_data=daily_data,
                    stop_loss_percent=stop_loss,
                    take_profit_percent=take_profit
                )

                result['stop_loss_percent'] = stop_loss
                result['take_profit_percent'] = take_profit
                results.append(result)

        # 최적 조건 찾기 (수익률 기준)
        best_result = max(results, key=lambda x: x['return_rate'])

        logger.info(
            f"백테스팅 완료: 최적 조건 = "
            f"손절 {best_result['stop_loss_percent']}%, "
            f"익절 {best_result['take_profit_percent']}% "
            f"(수익률: {best_result['return_rate']:.2f}%)"
        )

        return {
            'stock_code': stock_code,
            'period': f"{start_date} ~ {end_date}",
            'total_days': len(daily_data),
            'all_results': results,
            'best_result': best_result,
            'recommendation': {
                'stop_loss_percent': best_result['stop_loss_percent'],
                'take_profit_percent': best_result['take_profit_percent'],
                'expected_return': best_result['return_rate'],
                'expected_win_rate': best_result['win_rate']
            }
        }

    def _simulate_trades(
        self,
        stock_code: str,
        daily_data: List[Dict],
        stop_loss_percent: float,
        take_profit_percent: float
    ) -> Dict[str, Any]:
        """
        특정 손절/익절 조건으로 거래 시뮬레이션

        Args:
            stock_code: 종목코드
            daily_data: 일봉 데이터
            stop_loss_percent: 손절 비율
            take_profit_percent: 익절 비율

        Returns:
            시뮬레이션 결과
        """
        initial_capital = 1000000  # 100만원
        capital = initial_capital
        position = None
        trades = []

        for i, day in enumerate(daily_data):
            date = day.get('date', day.get('stck_bsop_date', ''))
            # Support both formats: 'open'/'open_price', 'high'/'high_price', etc.
            open_price = day.get('open', day.get('open_price', day.get('stck_oprc', 0)))
            high_price = day.get('high', day.get('high_price', day.get('stck_hgpr', 0)))
            low_price = day.get('low', day.get('low_price', day.get('stck_lwpr', 0)))
            close_price = day.get('close', day.get('close_price', day.get('stck_clpr', 0)))

            # 포지션이 없으면 매수 (단순화: 매일 매수 시도)
            if position is None and open_price > 0:
                quantity = int(capital / open_price)
                if quantity > 0:
                    position = {
                        'buy_date': date,
                        'buy_price': open_price,
                        'quantity': quantity,
                        'stop_loss_price': open_price * (1 - stop_loss_percent / 100),
                        'take_profit_price': open_price * (1 + take_profit_percent / 100)
                    }
                    capital -= quantity * open_price

            # 포지션이 있으면 손절/익절 체크
            elif position is not None:
                sell_price = None
                sell_reason = None

                # 손절 체크 (저가가 손절가 이하)
                if low_price <= position['stop_loss_price']:
                    sell_price = position['stop_loss_price']
                    sell_reason = 'stop_loss'

                # 익절 체크 (고가가 익절가 이상)
                elif high_price >= position['take_profit_price']:
                    sell_price = position['take_profit_price']
                    sell_reason = 'take_profit'

                # 마지막 날이면 종가로 청산
                elif i == len(daily_data) - 1:
                    sell_price = close_price
                    sell_reason = 'final_close'

                # 매도 실행
                if sell_price:
                    sell_amount = position['quantity'] * sell_price
                    capital += sell_amount

                    profit = sell_amount - (position['quantity'] * position['buy_price'])
                    profit_percent = (profit / (position['quantity'] * position['buy_price'])) * 100

                    trades.append({
                        'buy_date': position['buy_date'],
                        'buy_price': position['buy_price'],
                        'sell_date': date,
                        'sell_price': sell_price,
                        'quantity': position['quantity'],
                        'profit': profit,
                        'profit_percent': profit_percent,
                        'reason': sell_reason
                    })

                    position = None

        # 결과 계산
        total_profit = capital - initial_capital
        return_rate = (total_profit / initial_capital) * 100
        win_trades = [t for t in trades if t['profit'] > 0]
        win_rate = (len(win_trades) / len(trades) * 100) if trades else 0

        return {
            'initial_capital': initial_capital,
            'final_capital': capital,
            'total_profit': total_profit,
            'return_rate': return_rate,
            'trade_count': len(trades),
            'win_count': len(win_trades),
            'loss_count': len(trades) - len(win_trades),
            'win_rate': win_rate,
            'trades': trades
        }

    def apply_best_conditions(
        self,
        strategy_id: int,
        backtest_result: Dict[str, Any]
    ) -> bool:
        """
        백테스팅 최적 조건을 전략에 적용

        Args:
            strategy_id: 가상매매 전략 ID
            backtest_result: 백테스팅 결과

        Returns:
            적용 성공 여부
        """
        try:
            recommendation = backtest_result.get('recommendation', {})

            if not recommendation:
                logger.error("백테스팅 추천 조건 없음")
                return False

            stop_loss_percent = recommendation.get('stop_loss_percent')
            take_profit_percent = recommendation.get('take_profit_percent')

            logger.info(
                f"전략 {strategy_id}에 최적 조건 적용: "
                f"손절 {stop_loss_percent}%, 익절 {take_profit_percent}%"
            )

            # 여기서 전략에 기본 손절/익절 조건을 저장할 수 있음
            # (현재는 포지션별로 설정하므로 참고용으로 로깅만)

            return True

        except Exception as e:
            logger.error(f"최적 조건 적용 실패: {e}")
            return False

    def run_multi_stock_backtest(
        self,
        strategy_id: int,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        stop_loss_percent: float = 5.0,
        take_profit_percent: float = 10.0
    ) -> Dict[str, Any]:
        """
        여러 종목에 대해 백테스팅 실행

        Args:
            strategy_id: 가상매매 전략 ID
            stock_codes: 종목코드 리스트
            start_date: 시작일
            end_date: 종료일
            stop_loss_percent: 손절 비율
            take_profit_percent: 익절 비율

        Returns:
            종합 백테스팅 결과
        """
        logger.info(f"복수 종목 백테스팅 시작: {len(stock_codes)}개 종목")

        results = {}
        total_profit = 0
        total_trades = 0
        total_wins = 0

        for stock_code in stock_codes:
            try:
                daily_data = self.data_fetcher.get_daily_price(
                    stock_code=stock_code,
                    start_date=start_date,
                    end_date=end_date
                )

                if not daily_data:
                    logger.warning(f"{stock_code}: 데이터 없음")
                    continue

                result = self._simulate_trades(
                    stock_code=stock_code,
                    daily_data=daily_data,
                    stop_loss_percent=stop_loss_percent,
                    take_profit_percent=take_profit_percent
                )

                results[stock_code] = result
                total_profit += result['total_profit']
                total_trades += result['trade_count']
                total_wins += result['win_count']

            except Exception as e:
                logger.error(f"{stock_code} 백테스팅 실패: {e}")

        overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

        logger.info(
            f"복수 종목 백테스팅 완료: "
            f"총 수익 {total_profit:,.0f}원, "
            f"승률 {overall_win_rate:.1f}%"
        )

        return {
            'stock_count': len(results),
            'total_profit': total_profit,
            'total_trades': total_trades,
            'total_wins': total_wins,
            'overall_win_rate': overall_win_rate,
            'results': results
        }
