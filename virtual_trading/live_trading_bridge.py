"""
실전 투자 전환 브릿지 (Live Trading Bridge)

가상매매에서 검증된 전략을 실전 투자로 전환합니다.
- 가상매매 성과 검증
- 리스크 체크
- 실전 주문 실행
- 안전 장치 (일일 손실 제한, 최대 투자 금액 등)
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LiveTradingConfig:
    """실전 투자 설정"""
    # 검증 조건
    min_win_rate: float = 60.0  # 최소 승률 (%)
    min_trades: int = 50  # 최소 거래 횟수
    min_return_rate: float = 10.0  # 최소 수익률 (%)
    max_drawdown: float = 15.0  # 최대 낙폭 (%)

    # 리스크 관리
    max_daily_loss_pct: float = 5.0  # 일일 최대 손실 (%)
    max_position_size_pct: float = 20.0  # 최대 포지션 크기 (%)
    max_total_investment_pct: float = 80.0  # 최대 총 투자 비율 (%)

    # 실전 투자 금액
    initial_live_capital: float = 10000000  # 초기 실전 투자 금액 (1천만원)
    position_sizing_method: str = "kelly"  # kelly, fixed, proportional

    # 안전 장치
    enable_stop_loss: bool = True
    enable_take_profit: bool = True
    enable_trailing_stop: bool = True
    emergency_stop_on_loss: bool = True


class LiveTradingBridge:
    """가상매매 → 실전 투자 전환 브릿지"""

    def __init__(
        self,
        virtual_manager,
        trading_api,
        config: LiveTradingConfig = None
    ):
        """
        Args:
            virtual_manager: VirtualTradingManager 인스턴스
            trading_api: 실전 거래 API
            config: 실전 투자 설정
        """
        self.virtual_manager = virtual_manager
        self.trading_api = trading_api
        self.config = config or LiveTradingConfig()

        self.live_mode_enabled = False
        self.live_positions: Dict[str, Dict] = {}  # 실전 포지션
        self.daily_pnl = 0.0  # 일일 손익
        self.daily_reset_date = datetime.now().date()

        logger.info("실전 투자 브릿지 초기화 완료")

    def validate_strategy(self, strategy_id: int) -> Dict[str, Any]:
        """
        전략 검증 (실전 투자 가능 여부 확인)

        Args:
            strategy_id: 가상매매 전략 ID

        Returns:
            검증 결과 딕셔너리
        """
        try:
            logger.info(f"전략 {strategy_id} 검증 시작...")

            # 전략 성과 조회
            metrics = self.virtual_manager.db.get_strategy_summary(strategy_id=strategy_id)

            if not metrics:
                return {
                    'validated': False,
                    'reason': '전략 성과 데이터 없음',
                    'checks': {}
                }

            metric = metrics[0]

            # 검증 체크리스트
            checks = {
                'win_rate': {
                    'value': metric.get('win_rate', 0),
                    'threshold': self.config.min_win_rate,
                    'passed': metric.get('win_rate', 0) >= self.config.min_win_rate
                },
                'trade_count': {
                    'value': metric.get('total_trades', 0),
                    'threshold': self.config.min_trades,
                    'passed': metric.get('total_trades', 0) >= self.config.min_trades
                },
                'return_rate': {
                    'value': metric.get('total_return', 0),
                    'threshold': self.config.min_return_rate,
                    'passed': metric.get('total_return', 0) >= self.config.min_return_rate
                }
            }

            # 낙폭 계산
            positions = self.virtual_manager.db.get_closed_positions(
                strategy_id=strategy_id,
                limit=1000
            )
            max_drawdown = self._calculate_max_drawdown(positions)

            checks['max_drawdown'] = {
                'value': max_drawdown,
                'threshold': self.config.max_drawdown,
                'passed': max_drawdown <= self.config.max_drawdown
            }

            # 모든 체크 통과 여부
            all_passed = all(check['passed'] for check in checks.values())

            result = {
                'validated': all_passed,
                'reason': '검증 통과' if all_passed else '검증 조건 미달',
                'checks': checks,
                'metrics': metric
            }

            if all_passed:
                logger.info(f"✅ 전략 {strategy_id} 검증 통과!")
            else:
                logger.warning(f"⚠️ 전략 {strategy_id} 검증 실패")
                for check_name, check_data in checks.items():
                    if not check_data['passed']:
                        logger.warning(
                            f"  - {check_name}: {check_data['value']:.2f} "
                            f"(기준: {check_data['threshold']:.2f})"
                        )

            return result

        except Exception as e:
            logger.error(f"전략 검증 실패: {e}", exc_info=True)
            return {
                'validated': False,
                'reason': f'검증 오류: {str(e)}',
                'checks': {}
            }

    def enable_live_trading(self, strategy_id: int) -> Dict[str, Any]:
        """
        실전 투자 활성화

        Args:
            strategy_id: 가상매매 전략 ID

        Returns:
            활성화 결과
        """
        try:
            # 전략 검증
            validation = self.validate_strategy(strategy_id)

            if not validation['validated']:
                return {
                    'success': False,
                    'message': f"검증 실패: {validation['reason']}",
                    'validation': validation
                }

            # 실전 투자 활성화
            self.live_mode_enabled = True
            self.active_strategy_id = strategy_id

            logger.info(f"🚀 실전 투자 활성화: 전략 {strategy_id}")

            return {
                'success': True,
                'message': '실전 투자 활성화 완료',
                'strategy_id': strategy_id,
                'validation': validation,
                'config': {
                    'max_daily_loss_pct': self.config.max_daily_loss_pct,
                    'max_position_size_pct': self.config.max_position_size_pct,
                    'initial_capital': self.config.initial_live_capital
                }
            }

        except Exception as e:
            logger.error(f"실전 투자 활성화 실패: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'오류 발생: {str(e)}'
            }

    def disable_live_trading(self) -> Dict[str, Any]:
        """실전 투자 비활성화"""
        try:
            self.live_mode_enabled = False
            logger.info("실전 투자 비활성화")

            return {
                'success': True,
                'message': '실전 투자 비활성화 완료'
            }

        except Exception as e:
            logger.error(f"실전 투자 비활성화 실패: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'오류 발생: {str(e)}'
            }

    def execute_live_trade(
        self,
        action: str,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: float,
        strategy_id: int
    ) -> Dict[str, Any]:
        """
        실전 주문 실행

        Args:
            action: 'buy' 또는 'sell'
            stock_code: 종목코드
            stock_name: 종목명
            quantity: 수량
            price: 가격
            strategy_id: 전략 ID

        Returns:
            주문 결과
        """
        try:
            if not self.live_mode_enabled:
                return {
                    'success': False,
                    'message': '실전 투자가 비활성화되어 있습니다'
                }

            # 일일 손실 체크
            if self._check_daily_loss_limit():
                logger.warning("⚠️ 일일 손실 한도 초과 - 주문 차단")
                return {
                    'success': False,
                    'message': '일일 손실 한도 초과',
                    'daily_pnl': self.daily_pnl
                }

            # 포지션 크기 체크
            if action == 'buy' and not self._check_position_size(quantity, price):
                logger.warning("⚠️ 포지션 크기 초과 - 주문 차단")
                return {
                    'success': False,
                    'message': '포지션 크기 한도 초과'
                }

            # CRITICAL FIX: 매도 시 비정상 가격 검증
            if action == 'sell':
                # 현재가 조회하여 비정상 가격 필터링
                try:
                    from research import DataFetcher
                    if hasattr(self.trading_api, 'client'):
                        data_fetcher = DataFetcher(self.trading_api.client)
                        current_price_data = data_fetcher.get_current_price(stock_code)
                        current_price = current_price_data.get('current_price', 0)

                        if current_price > 0 and price > current_price * 1.3:
                            logger.warning(f"⚠️ 비정상 매도가 감지: {price:,}원 (현재가: {current_price:,}원)")
                            logger.warning(f"   현재가 대비 {((price/current_price - 1) * 100):.1f}% 높음 → 현재가 +2%로 조정")
                            price = int(current_price * 1.02)  # 현재가 +2%로 조정
                            logger.info(f"✅ 조정된 매도가: {price:,}원")
                except Exception as e:
                    logger.warning(f"현재가 조회 실패, 원본 가격 사용: {e}")

            # 실전 주문 실행
            if action == 'buy':
                result = self.trading_api.buy_stock(
                    stock_code=stock_code,
                    quantity=quantity,
                    price=price,
                    order_type="00"  # 지정가
                )
            else:
                result = self.trading_api.sell_stock(
                    stock_code=stock_code,
                    quantity=quantity,
                    price=price,
                    order_type="00"  # 지정가
                )

            if result and result.get('success'):
                logger.info(
                    f"✅ 실전 주문 완료: {action.upper()} "
                    f"{stock_name}({stock_code}) {quantity}주 @ {price:,}원"
                )

                # 포지션 추적
                if action == 'buy':
                    self.live_positions[stock_code] = {
                        'stock_name': stock_name,
                        'quantity': quantity,
                        'avg_price': price,
                        'open_time': datetime.now().isoformat(),
                        'strategy_id': strategy_id
                    }
                elif action == 'sell' and stock_code in self.live_positions:
                    # 손익 계산
                    position = self.live_positions[stock_code]
                    profit = (price - position['avg_price']) * quantity
                    self.daily_pnl += profit

                    # 포지션 제거
                    del self.live_positions[stock_code]

                return {
                    'success': True,
                    'message': f'{action.upper()} 주문 완료',
                    'order_id': result.get('order_id'),
                    'result': result
                }
            else:
                return {
                    'success': False,
                    'message': result.get('error', '주문 실패') if result else '주문 응답 없음'
                }

        except Exception as e:
            logger.error(f"실전 주문 실행 실패: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'오류 발생: {str(e)}'
            }

    def get_live_status(self) -> Dict[str, Any]:
        """실전 투자 현황 조회"""
        try:
            return {
                'live_mode_enabled': self.live_mode_enabled,
                'active_strategy_id': getattr(self, 'active_strategy_id', None),
                'daily_pnl': self.daily_pnl,
                'daily_pnl_pct': (self.daily_pnl / self.config.initial_live_capital) * 100,
                'position_count': len(self.live_positions),
                'positions': list(self.live_positions.values()),
                'config': {
                    'max_daily_loss_pct': self.config.max_daily_loss_pct,
                    'max_position_size_pct': self.config.max_position_size_pct,
                    'initial_capital': self.config.initial_live_capital
                }
            }

        except Exception as e:
            logger.error(f"실전 투자 현황 조회 실패: {e}", exc_info=True)
            return {
                'live_mode_enabled': False,
                'error': str(e)
            }

    def _check_daily_loss_limit(self) -> bool:
        """일일 손실 한도 체크"""
        # 날짜가 바뀌면 리셋
        current_date = datetime.now().date()
        if current_date != self.daily_reset_date:
            self.daily_pnl = 0.0
            self.daily_reset_date = current_date

        daily_loss_pct = abs(self.daily_pnl / self.config.initial_live_capital) * 100

        if self.daily_pnl < 0 and daily_loss_pct >= self.config.max_daily_loss_pct:
            return True

        return False

    def _check_position_size(self, quantity: int, price: float) -> bool:
        """포지션 크기 체크"""
        position_value = quantity * price
        max_position_value = self.config.initial_live_capital * (self.config.max_position_size_pct / 100)

        return position_value <= max_position_value

    def _calculate_max_drawdown(self, positions: List[Dict]) -> float:
        """최대 낙폭 계산"""
        if not positions:
            return 0

        equity = 0
        max_equity = 0
        max_drawdown = 0

        for pos in sorted(positions, key=lambda x: x.get('close_time', '')):
            profit = pos.get('profit_loss', 0)
            equity += profit

            if equity > max_equity:
                max_equity = equity

            if max_equity > 0:
                drawdown = (max_equity - equity) / max_equity * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        return max_drawdown


# 싱글톤 인스턴스
_live_trading_bridge = None


def get_live_trading_bridge(
    virtual_manager=None,
    trading_api=None,
    config: LiveTradingConfig = None
) -> LiveTradingBridge:
    """실전 투자 브릿지 싱글톤 가져오기"""
    global _live_trading_bridge

    if _live_trading_bridge is None and virtual_manager and trading_api:
        _live_trading_bridge = LiveTradingBridge(
            virtual_manager=virtual_manager,
            trading_api=trading_api,
            config=config
        )

    return _live_trading_bridge
