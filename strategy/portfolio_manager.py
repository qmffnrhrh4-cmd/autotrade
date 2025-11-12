"""
strategy/portfolio_manager.py
포트폴리오 관리
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PortfolioManager:
    """
    포트폴리오 관리 클래스
    
    주요 기능:
    - 포트폴리오 구성 관리
    - 포지션 추적
    - 자산 배분
    - 성과 분석
    """
    
    def __init__(self, client, config: Dict[str, Any] = None):
        """
        PortfolioManager 초기화
        
        Args:
            client: KiwoomRESTClient 인스턴스
            config: 설정
                {
                    'max_positions': 5,           # 최대 포지션 수
                    'max_position_size': 0.30,    # 단일 포지션 최대 비중 30%
                    'cash_reserve_ratio': 0.10,   # 현금 보유 비율 10%
                    'rebalance_threshold': 0.05,  # 리밸런싱 임계값 5%
                }
        """
        self.client = client
        self.config = config or {}
        
        # 기본 설정
        self.max_positions = self.config.get('max_positions', 5)
        self.max_position_size = self.config.get('max_position_size', 0.30)
        self.cash_reserve_ratio = self.config.get('cash_reserve_ratio', 0.10)
        self.rebalance_threshold = self.config.get('rebalance_threshold', 0.05)
        
        # 포트폴리오 상태
        self.positions = {}  # {stock_code: position_info}
        self.target_weights = {}  # {stock_code: target_weight}
        self.total_assets = 0
        
        # 이력
        self.history = []
        
        logger.info("PortfolioManager 초기화 완료")
    
    # ==================== 포지션 관리 ====================
    
    def update_portfolio(self, holdings: List[Dict[str, Any]], cash: int):
        """
        포트폴리오 업데이트
        
        Args:
            holdings: 보유 종목 리스트
            cash: 보유 현금
        """
        self.positions.clear()
        
        # 총 자산 계산
        stocks_value = 0
        for holding in holdings:
            stock_code = holding.get('stock_code', '')
            evaluation = holding.get('evaluation_amount', 0)
            stocks_value += evaluation
            
            self.positions[stock_code] = {
                'stock_code': stock_code,
                'stock_name': holding.get('stock_name', ''),
                'quantity': holding.get('quantity', 0),
                'purchase_price': holding.get('purchase_price', 0),
                'current_price': holding.get('current_price', 0),
                'evaluation_amount': evaluation,
                'profit_loss': holding.get('profit_loss', 0),
                'profit_loss_rate': holding.get('profit_loss_rate', 0),
            }
        
        self.total_assets = cash + stocks_value
        
        # 비중 계산
        for stock_code, position in self.positions.items():
            if self.total_assets > 0:
                position['weight'] = position['evaluation_amount'] / self.total_assets
            else:
                position['weight'] = 0.0
        
        logger.info(f"포트폴리오 업데이트: 총 자산 {self.total_assets:,}원, 종목 수 {len(self.positions)}개")
    
    def add_position(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        purchase_price: float
    ):
        """
        포지션 추가
        
        Args:
            stock_code: 종목코드
            stock_name: 종목명
            quantity: 수량
            purchase_price: 매수가
        """
        evaluation_amount = quantity * purchase_price
        
        self.positions[stock_code] = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'quantity': quantity,
            'purchase_price': purchase_price,
            'current_price': purchase_price,
            'evaluation_amount': evaluation_amount,
            'profit_loss': 0,
            'profit_loss_rate': 0,
            'weight': 0.0,
            'added_time': datetime.now(),
        }
        
        logger.info(f"포지션 추가: {stock_name}({stock_code}) {quantity}주 @ {purchase_price:,.0f}원")
    
    def remove_position(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        포지션 제거
        
        Args:
            stock_code: 종목코드
        
        Returns:
            제거된 포지션 정보
        """
        if stock_code in self.positions:
            position = self.positions.pop(stock_code)
            logger.info(f"포지션 제거: {position['stock_name']}({stock_code})")
            return position
        return None
    
    def get_position(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        포지션 조회
        
        Args:
            stock_code: 종목코드
        
        Returns:
            포지션 정보
        """
        return self.positions.get(stock_code)
    
    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """모든 포지션 조회"""
        return self.positions.copy()

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """모든 포지션 반환 (get_all_positions 별칭, main.py 호환)"""
        return self.get_all_positions()

    def get_position_count(self) -> int:
        """포지션 개수"""
        return len(self.positions)
    
    def has_position(self, stock_code: str) -> bool:
        """
        포지션 보유 여부
        
        Args:
            stock_code: 종목코드
        
        Returns:
            보유 여부
        """
        return stock_code in self.positions
    
    # ==================== 포지션 크기 계산 ====================
    
    def calculate_position_size(
        self,
        stock_code: str,
        current_price: int,
        available_cash: int,
        target_weight: float = None
    ) -> int:
        """
        포지션 크기 계산
        
        Args:
            stock_code: 종목코드
            current_price: 현재가
            available_cash: 가용 현금
            target_weight: 목표 비중 (None이면 균등 배분)
        
        Returns:
            매수 수량
        """
        if current_price == 0:
            return 0
        
        # 포지션 수 확인
        if self.get_position_count() >= self.max_positions:
            logger.warning(f"최대 포지션 수 {self.max_positions}개 도달")
            return 0
        
        # 목표 비중 결정
        if target_weight is None:
            # 균등 배분
            remaining_positions = self.max_positions - self.get_position_count()
            target_weight = 1.0 / self.max_positions
        
        # 최대 포지션 크기 제한
        if target_weight > self.max_position_size:
            target_weight = self.max_position_size
        
        # 투자 금액 계산
        invest_amount = int(self.total_assets * target_weight)
        
        # 가용 현금 확인
        if invest_amount > available_cash:
            invest_amount = available_cash
        
        # 수수료 고려
        commission_rate = 0.00015
        quantity = int(invest_amount / (current_price * (1 + commission_rate)))
        
        logger.info(
            f"{stock_code} 포지션 크기 계산: "
            f"{quantity}주 (목표 비중: {target_weight*100:.1f}%, 투자금액: {invest_amount:,}원)"
        )
        
        return quantity
    
    def can_add_position(self) -> bool:
        """
        포지션 추가 가능 여부
        
        Returns:
            추가 가능 여부
        """
        return self.get_position_count() < self.max_positions
    
    def get_available_position_slots(self) -> int:
        """
        추가 가능한 포지션 슬롯 수
        
        Returns:
            슬롯 수
        """
        return max(0, self.max_positions - self.get_position_count())
    
    # ==================== 리밸런싱 ====================
    
    def set_target_weights(self, target_weights: Dict[str, float]):
        """
        목표 비중 설정
        
        Args:
            target_weights: {stock_code: weight}
        """
        total_weight = sum(target_weights.values())
        
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"목표 비중 합계가 1.0이 아닙니다: {total_weight:.4f}")
        
        self.target_weights = target_weights.copy()
        logger.info(f"목표 비중 설정 완료: {len(target_weights)}개 종목")
    
    def check_rebalance_needed(self) -> bool:
        """
        리밸런싱 필요 여부 확인
        
        Returns:
            리밸런싱 필요 여부
        """
        if not self.target_weights:
            return False
        
        for stock_code, target_weight in self.target_weights.items():
            position = self.get_position(stock_code)
            
            if position is None:
                # 포지션이 없는데 목표 비중이 있으면 리밸런싱 필요
                if target_weight > 0:
                    logger.info(f"리밸런싱 필요: {stock_code} 포지션 없음 (목표: {target_weight*100:.1f}%)")
                    return True
            else:
                current_weight = position.get('weight', 0)
                weight_diff = abs(current_weight - target_weight)
                
                # 비중 차이가 임계값을 초과하면 리밸런싱 필요
                if weight_diff > self.rebalance_threshold:
                    logger.info(
                        f"리밸런싱 필요: {stock_code} "
                        f"현재 {current_weight*100:.1f}% vs 목표 {target_weight*100:.1f}%"
                    )
                    return True
        
        return False
    
    def get_rebalance_orders(self) -> List[Dict[str, Any]]:
        """
        리밸런싱 주문 목록 생성
        
        Returns:
            주문 목록
            [
                {
                    'stock_code': '005930',
                    'action': 'buy' | 'sell',
                    'quantity': 10,
                    'reason': '목표 비중 조정'
                },
                ...
            ]
        """
        if not self.target_weights or self.total_assets == 0:
            return []
        
        orders = []
        
        for stock_code, target_weight in self.target_weights.items():
            position = self.get_position(stock_code)
            
            target_amount = self.total_assets * target_weight
            
            if position is None:
                # 신규 매수
                if target_weight > 0:
                    orders.append({
                        'stock_code': stock_code,
                        'action': 'buy',
                        'target_amount': target_amount,
                        'reason': f'목표 비중 {target_weight*100:.1f}% 달성'
                    })
            else:
                current_amount = position['evaluation_amount']
                diff_amount = target_amount - current_amount
                
                if abs(diff_amount) > self.total_assets * self.rebalance_threshold:
                    if diff_amount > 0:
                        # 추가 매수
                        orders.append({
                            'stock_code': stock_code,
                            'action': 'buy',
                            'target_amount': diff_amount,
                            'reason': f'비중 상향 조정 ({position["weight"]*100:.1f}% → {target_weight*100:.1f}%)'
                        })
                    else:
                        # 일부 매도
                        orders.append({
                            'stock_code': stock_code,
                            'action': 'sell',
                            'target_amount': abs(diff_amount),
                            'reason': f'비중 하향 조정 ({position["weight"]*100:.1f}% → {target_weight*100:.1f}%)'
                        })
        
        logger.info(f"리밸런싱 주문 {len(orders)}개 생성")
        return orders
    
    # ==================== 성과 분석 ====================
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        포트폴리오 요약
        
        Returns:
            요약 정보
        """
        total_evaluation = sum(p['evaluation_amount'] for p in self.positions.values())
        total_profit_loss = sum(p['profit_loss'] for p in self.positions.values())
        
        # 총 매수금액 계산
        total_purchase = sum(
            p['quantity'] * p['purchase_price']
            for p in self.positions.values()
        )
        
        # 수익률 계산
        if total_purchase > 0:
            total_profit_loss_rate = (total_profit_loss / total_purchase) * 100
        else:
            total_profit_loss_rate = 0.0
        
        # 현금 비중
        cash = self.total_assets - total_evaluation
        cash_ratio = (cash / self.total_assets * 100) if self.total_assets > 0 else 0
        
        return {
            'total_assets': self.total_assets,
            'cash': cash,
            'cash_ratio': round(cash_ratio, 2),
            'stocks_value': total_evaluation,
            'stocks_ratio': round((total_evaluation / self.total_assets * 100) if self.total_assets > 0 else 0, 2),
            'total_profit_loss': total_profit_loss,
            'total_profit_loss_rate': round(total_profit_loss_rate, 2),
            'position_count': len(self.positions),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_position_details(self) -> List[Dict[str, Any]]:
        """
        포지션 상세 정보
        
        Returns:
            포지션 리스트
        """
        positions = []
        
        for stock_code, position in self.positions.items():
            positions.append({
                'stock_code': stock_code,
                'stock_name': position['stock_name'],
                'quantity': position['quantity'],
                'purchase_price': position['purchase_price'],
                'current_price': position['current_price'],
                'evaluation_amount': position['evaluation_amount'],
                'profit_loss': position['profit_loss'],
                'profit_loss_rate': round(position['profit_loss_rate'], 2),
                'weight': round(position.get('weight', 0) * 100, 2),
            })
        
        # 수익률 순으로 정렬
        positions.sort(key=lambda x: x['profit_loss_rate'], reverse=True)
        
        return positions
    
    def get_top_performers(self, top_n: int = 3) -> List[Dict[str, Any]]:
        """
        상위 수익 종목
        
        Args:
            top_n: 조회 개수
        
        Returns:
            상위 종목 리스트
        """
        positions = list(self.positions.values())
        positions.sort(key=lambda x: x['profit_loss_rate'], reverse=True)
        return positions[:top_n]
    
    def get_worst_performers(self, top_n: int = 3) -> List[Dict[str, Any]]:
        """
        하위 수익 종목
        
        Args:
            top_n: 조회 개수
        
        Returns:
            하위 종목 리스트
        """
        positions = list(self.positions.values())
        positions.sort(key=lambda x: x['profit_loss_rate'])
        return positions[:top_n]
    
    # ==================== 리스크 지표 ====================
    
    def get_concentration_risk(self) -> Dict[str, Any]:
        """
        집중도 리스크 분석
        
        Returns:
            집중도 정보
        """
        if not self.positions:
            return {
                'max_position_weight': 0.0,
                'max_position_stock': None,
                'herfindahl_index': 0.0,
                'diversification_ratio': 0.0,
            }
        
        # 최대 비중 포지션
        max_position = max(self.positions.values(), key=lambda x: x.get('weight', 0))
        max_weight = max_position.get('weight', 0)
        
        # Herfindahl 지수 (집중도 측정)
        herfindahl = sum(p.get('weight', 0) ** 2 for p in self.positions.values())
        
        # 분산 비율
        n = len(self.positions)
        diversification_ratio = (1.0 / herfindahl) / n if n > 0 and herfindahl > 0 else 0
        
        return {
            'max_position_weight': round(max_weight * 100, 2),
            'max_position_stock': max_position.get('stock_name', ''),
            'herfindahl_index': round(herfindahl, 4),
            'diversification_ratio': round(diversification_ratio, 4),
            'is_concentrated': max_weight > self.max_position_size,
        }
    
    def save_snapshot(self):
        """포트폴리오 스냅샷 저장"""
        snapshot = {
            'timestamp': datetime.now(),
            'summary': self.get_portfolio_summary(),
            'positions': self.get_position_details(),
        }
        
        self.history.append(snapshot)
        
        # 최근 30개만 유지
        if len(self.history) > 30:
            self.history = self.history[-30:]
        
        logger.info("포트폴리오 스냅샷 저장 완료")
    
    def get_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        포트폴리오 이력 조회

        Args:
            days: 조회 일수

        Returns:
            이력 리스트
        """
        return self.history[-days:] if self.history else []

    def get_total_value(self) -> int:
        """
        총 포트폴리오 가치 조회

        Returns:
            총 자산 (현금 + 주식 평가액)
        """
        return int(self.total_assets)


__all__ = ['PortfolioManager']