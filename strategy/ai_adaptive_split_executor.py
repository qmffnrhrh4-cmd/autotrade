"""
AI 기반 적응형 분할 매도 시스템
AI-Powered Adaptive Split Order Executor

1차 체결 → Gemini AI 시장 분석 → 2차 가격 재계산 → 체결 → 반복...
"""
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AIAdaptiveSplitExecutor:
    """
    AI 기반 적응형 분할 매도 실행기

    특징:
    - 실시간 체결 모니터링
    - Gemini AI를 통한 시장 상황 분석
    - 동적 가격 재계산
    - 단계별 실행 (한 번에 하나씩)
    """

    def __init__(self, order_api, data_fetcher, account_api, ai_analyzer=None):
        """
        Args:
            order_api: 주문 API
            data_fetcher: 데이터 조회 API
            account_api: 계좌 API (체결 확인용)
            ai_analyzer: AI 분석기 (Gemini)
        """
        self.order_api = order_api
        self.data_fetcher = data_fetcher
        self.account_api = account_api
        self.ai_analyzer = ai_analyzer

    def execute_adaptive_split_buy(
        self,
        stock_code: str,
        stock_name: str,
        total_quantity: int,
        target_budget: float,
        num_splits: int = 3,
        max_wait_seconds: int = 30,
        account_number: str = None,
        exchange: str = 'KRX'
    ) -> Dict[str, Any]:
        """
        AI 기반 적응형 분할 매수 실행

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            total_quantity: 총 매수 수량
            target_budget: 목표 매수 금액
            num_splits: 분할 횟수 (기본 3회)
            max_wait_seconds: 체결 대기 최대 시간 (초, 기본 30초)
            account_number: 계좌번호
            exchange: 거래소 (KRX/NXT)

        Returns:
            실행 결과 딕셔너리
        """
        logger.info(f"")
        logger.info(f"=" * 80)
        logger.info(f"🤖 AI 기반 적응형 분할 매수 시작 (**순차 실행 모드**)")
        logger.info(f"=" * 80)
        logger.info(f"   종목: {stock_name}({stock_code})")
        logger.info(f"   ⚠️  주의: 1차 체결 완료 후 2차 실행됩니다!")
        logger.info(f"   수량: {total_quantity}주 → {num_splits}회 분할")
        logger.info(f"   목표 금액: {target_budget:,.0f}원")
        logger.info(f"")

        # 수량 분할
        base_qty = total_quantity // num_splits
        remainder = total_quantity % num_splits
        quantities = [base_qty + (1 if i < remainder else 0) for i in range(num_splits)]

        results = []
        last_filled_price = None
        remaining_qty = total_quantity

        for split_idx in range(num_splits):
            qty = quantities[split_idx]
            if qty <= 0:
                continue

            logger.info(f"")
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"📍 [{split_idx + 1}/{num_splits}차] 매수 시작")
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            # 1️⃣ 현재 시장 상황 조회
            current_price = self._get_current_price(stock_code)
            if not current_price:
                logger.error(f"❌ 현재가 조회 실패")
                break

            logger.info(f"📊 현재가: {current_price:,.0f}원")

            # 2️⃣ AI 분석으로 목표 매수가 결정
            target_price = self._calculate_buy_target_price_with_ai(
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                split_index=split_idx,
                total_splits=num_splits,
                last_filled_price=last_filled_price,
                remaining_quantity=remaining_qty
            )

            if not target_price:
                logger.warning(f"⚠️ 목표가 계산 실패, 현재가 -1%로 설정")
                target_price = current_price * 0.99

            logger.info(f"🎯 [{split_idx + 1}차] 목표 매수가: {target_price:,.0f}원")

            # 3️⃣ 주문 실행
            order_result = self._place_buy_order(
                stock_code=stock_code,
                quantity=qty,
                price=int(target_price),
                account_number=account_number,
                exchange=exchange
            )

            if not order_result or not order_result.get('success'):
                logger.error(f"❌ [{split_idx + 1}차] 주문 실패")
                results.append({
                    'split': split_idx + 1,
                    'quantity': qty,
                    'target_price': target_price,
                    'success': False,
                    'error': order_result.get('error') if order_result else 'No response'
                })
                continue

            order_number = order_result.get('order_no', order_result.get('order_number', ''))
            logger.info(f"✅ [{split_idx + 1}차] 주문 성공: {order_number}")

            # 4️⃣ 체결 모니터링 (마지막 주문 제외)
            if split_idx < num_splits - 1:
                logger.info(f"")
                logger.info(f"⏳ 체결 대기 중... (최대 {max_wait_seconds}초)")

                filled_info = self._wait_for_fill(
                    stock_code=stock_code,
                    order_number=order_number,
                    expected_quantity=qty,
                    max_wait_seconds=max_wait_seconds
                )

                if filled_info and filled_info.get('filled'):
                    filled_price = filled_info.get('filled_price', target_price)
                    filled_qty = filled_info.get('filled_quantity', qty)

                    logger.info(f"")
                    logger.info(f"✅ [{split_idx + 1}차] 체결 완료!")
                    logger.info(f"   체결가: {filled_price:,.0f}원")
                    logger.info(f"   체결량: {filled_qty}주")

                    last_filled_price = filled_price
                    remaining_qty -= filled_qty

                    results.append({
                        'split': split_idx + 1,
                        'quantity': filled_qty,
                        'target_price': target_price,
                        'filled_price': filled_price,
                        'success': True,
                        'filled': True
                    })

                    # 다음 주문 전 시장 변화 관찰
                    logger.info(f"")
                    logger.info(f"🔍 시장 변화 관찰 중... (2초 대기)")
                    time.sleep(2)
                else:
                    # CRITICAL: 체결 안 되면 다음 주문 실행하지 않음!
                    logger.error(f"")
                    logger.error(f"❌ [{split_idx + 1}차] 체결 실패 - 분할 매수 중단")
                    logger.error(f"   {max_wait_seconds}초 동안 체결되지 않았습니다")
                    logger.error(f"   주문은 유효 상태로 남아있습니다 (주문번호: {order_number})")
                    logger.error(f"   미체결 목록에서 확인하거나 취소할 수 있습니다")

                    results.append({
                        'split': split_idx + 1,
                        'quantity': qty,
                        'target_price': target_price,
                        'success': False,
                        'filled': False,
                        'note': f'체결 대기 시간 초과 ({max_wait_seconds}초) - 중단',
                        'order_number': order_number
                    })

                    # 다음 주문 실행하지 않고 종료!
                    break
            else:
                # 마지막 주문은 체결 대기 안 함
                logger.info(f"📝 [{split_idx + 1}차] 마지막 주문 - 체결 대기 생략")
                results.append({
                    'split': split_idx + 1,
                    'quantity': qty,
                    'target_price': target_price,
                    'success': True,
                    'filled': False,
                    'note': '마지막 주문'
                })

        logger.info(f"")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"✅ AI 기반 적응형 분할 매수 완료")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return {
            'success': True,
            'total_splits': num_splits,
            'results': results,
            'completed_at': datetime.now().isoformat()
        }

    def execute_adaptive_split_sell(
        self,
        stock_code: str,
        stock_name: str,
        total_quantity: int,
        entry_price: float,
        num_splits: int = 3,
        max_wait_seconds: int = 30,
        account_number: str = None,
        exchange: str = 'KRX'
    ) -> Dict[str, Any]:
        """
        AI 기반 적응형 분할 매도 실행

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            total_quantity: 총 매도 수량
            entry_price: 평균 매수가
            num_splits: 분할 횟수 (기본 3회)
            max_wait_seconds: 체결 대기 최대 시간 (초)
            account_number: 계좌번호
            exchange: 거래소 (KRX/NXT)

        Returns:
            실행 결과 딕셔너리
        """
        logger.info(f"")
        logger.info(f"=" * 80)
        logger.info(f"🤖 AI 기반 적응형 분할 매도 시작 (**순차 실행 모드**)")
        logger.info(f"=" * 80)
        logger.info(f"   종목: {stock_name}({stock_code})")
        logger.info(f"   ⚠️  주의: 1차 체결 완료 후 2차 실행됩니다!")
        logger.info(f"   수량: {total_quantity}주 → {num_splits}회 분할")
        logger.info(f"   평균 매수가: {entry_price:,.0f}원")
        logger.info(f"")

        # 수량 분할
        base_qty = total_quantity // num_splits
        remainder = total_quantity % num_splits
        quantities = [base_qty + (1 if i < remainder else 0) for i in range(num_splits)]

        results = []
        last_filled_price = None
        remaining_qty = total_quantity

        for split_idx in range(num_splits):
            qty = quantities[split_idx]
            if qty <= 0:
                continue

            logger.info(f"")
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"📍 [{split_idx + 1}/{num_splits}차] 매도 시작")
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            # 1️⃣ 현재 시장 상황 조회
            current_price = self._get_current_price(stock_code)
            if not current_price:
                logger.error(f"❌ 현재가 조회 실패")
                break

            logger.info(f"📊 현재가: {current_price:,.0f}원")
            logger.info(f"   평균 매수가: {entry_price:,.0f}원")

            profit_loss_rate = ((current_price - entry_price) / entry_price) * 100
            logger.info(f"   손익률: {profit_loss_rate:+.2f}%")

            # 2️⃣ AI 분석으로 목표가 결정
            target_price = self._calculate_target_price_with_ai(
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                entry_price=entry_price,
                split_index=split_idx,
                total_splits=num_splits,
                last_filled_price=last_filled_price,
                remaining_quantity=remaining_qty
            )

            if not target_price:
                logger.warning(f"⚠️ 목표가 계산 실패, 현재가 +1%로 설정")
                target_price = current_price * 1.01

            logger.info(f"🎯 [{split_idx + 1}차] 목표 매도가: {target_price:,.0f}원")

            # 3️⃣ 주문 실행
            order_result = self._place_sell_order(
                stock_code=stock_code,
                quantity=qty,
                price=int(target_price),
                account_number=account_number,
                exchange=exchange
            )

            if not order_result or not order_result.get('success'):
                logger.error(f"❌ [{split_idx + 1}차] 주문 실패")
                results.append({
                    'split': split_idx + 1,
                    'quantity': qty,
                    'target_price': target_price,
                    'success': False,
                    'error': order_result.get('error') if order_result else 'No response'
                })
                continue

            order_number = order_result.get('order_no', order_result.get('order_number', ''))
            logger.info(f"✅ [{split_idx + 1}차] 주문 성공: {order_number}")

            # 4️⃣ 체결 모니터링 (마지막 주문 제외)
            if split_idx < num_splits - 1:
                logger.info(f"")
                logger.info(f"⏳ 체결 대기 중... (최대 {max_wait_seconds}초)")

                filled_info = self._wait_for_fill(
                    stock_code=stock_code,
                    order_number=order_number,
                    expected_quantity=qty,
                    max_wait_seconds=max_wait_seconds
                )

                if filled_info and filled_info.get('filled'):
                    filled_price = filled_info.get('filled_price', target_price)
                    filled_qty = filled_info.get('filled_quantity', qty)

                    logger.info(f"")
                    logger.info(f"✅ [{split_idx + 1}차] 체결 완료!")
                    logger.info(f"   체결가: {filled_price:,.0f}원")
                    logger.info(f"   체결량: {filled_qty}주")

                    last_filled_price = filled_price
                    remaining_qty -= filled_qty

                    results.append({
                        'split': split_idx + 1,
                        'quantity': filled_qty,
                        'target_price': target_price,
                        'filled_price': filled_price,
                        'success': True,
                        'filled': True
                    })

                    # 다음 주문 전 시장 변화 관찰
                    logger.info(f"")
                    logger.info(f"🔍 시장 변화 관찰 중... (3초 대기)")
                    time.sleep(3)
                else:
                    # CRITICAL: 체결 안 되면 다음 주문 실행하지 않음!
                    logger.error(f"")
                    logger.error(f"❌ [{split_idx + 1}차] 체결 실패 - 분할 매도 중단")
                    logger.error(f"   {max_wait_seconds}초 동안 체결되지 않았습니다")
                    logger.error(f"   주문은 유효 상태로 남아있습니다")
                    logger.error(f"   미체결 목록에서 확인하거나 취소할 수 있습니다")

                    results.append({
                        'split': split_idx + 1,
                        'quantity': qty,
                        'target_price': target_price,
                        'success': False,
                        'filled': False,
                        'note': f'체결 대기 시간 초과 ({max_wait_seconds}초) - 중단',
                        'order_number': order_number
                    })

                    # 다음 주문 실행하지 않고 종료!
                    break
            else:
                # 마지막 주문은 체결 대기 안 함
                logger.info(f"📝 [{split_idx + 1}차] 마지막 주문 - 체결 대기 생략")
                results.append({
                    'split': split_idx + 1,
                    'quantity': qty,
                    'target_price': target_price,
                    'success': True,
                    'filled': False,
                    'note': '마지막 주문'
                })

        logger.info(f"")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"✅ AI 기반 적응형 분할 매도 완료")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return {
            'success': True,
            'total_splits': num_splits,
            'results': results,
            'completed_at': datetime.now().isoformat()
        }

    def _calculate_buy_target_price_with_ai(
        self,
        stock_code: str,
        stock_name: str,
        current_price: float,
        split_index: int,
        total_splits: int,
        last_filled_price: Optional[float],
        remaining_quantity: int
    ) -> Optional[float]:
        """
        AI를 활용한 목표 매수가 계산

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            current_price: 현재가
            split_index: 현재 분할 인덱스 (0, 1, 2...)
            total_splits: 총 분할 횟수
            last_filled_price: 이전 체결가 (None이면 첫 주문)
            remaining_quantity: 남은 수량

        Returns:
            목표 매수가
        """
        try:
            # 1차 주문: 단순 로직
            if split_index == 0:
                # 매수는 현재가보다 낮게 주문
                target = current_price * 0.995  # -0.5%
                logger.info(f"   💡 1차 전략: 보수적 매수 (현재가 -0.5%)")
                return target

            # 2차, 3차 주문: AI 분석 활용
            if self.ai_analyzer and last_filled_price:
                logger.info(f"   🤖 AI 시장 분석 중...")

                # 이전 체결 이후 가격 변화
                price_change_since_fill = ((current_price - last_filled_price) / last_filled_price) * 100

                logger.info(f"   📈 이전 체결가 대비: {price_change_since_fill:+.2f}%")

                # AI에게 질문
                ai_prompt = f"""
당신은 한국 주식 시장 전문 트레이더입니다.

## 현재 상황
- 종목: {stock_name}({stock_code})
- 현재가: {current_price:,.0f}원
- 이전 체결가: {last_filled_price:,.0f}원
- 이전 체결 후 변화: {price_change_since_fill:+.2f}%
- 진행 상황: {split_index + 1}/{total_splits}차 매수
- 남은 수량: {remaining_quantity}주

## 질문
다음 매수 주문의 적정 가격을 추천해주세요.
(매수이므로 현재가보다 낮은 가격 또는 현재가 근처)

## 응답 형식 (JSON)
{{
  "recommended_price": 추천_매수가_숫자만,
  "reasoning": "추천 이유 (1-2문장)",
  "market_condition": "상승중/하락중/횡보중"
}}

응답은 반드시 JSON 형식으로만 작성하세요. 다른 설명은 불필요합니다.
"""

                try:
                    # AI 분석 요청
                    ai_response = self._call_ai_for_price_recommendation(ai_prompt)

                    if ai_response and 'recommended_price' in ai_response:
                        ai_price = float(ai_response['recommended_price'])
                        reasoning = ai_response.get('reasoning', '')
                        market_condition = ai_response.get('market_condition', '')

                        logger.info(f"   ✅ AI 추천가: {ai_price:,.0f}원")
                        logger.info(f"   📝 시장 상황: {market_condition}")
                        logger.info(f"   💬 판단 근거: {reasoning}")

                        # 안전 범위 검증 (현재가의 -3% ~ +2% 이내)
                        min_price = current_price * 0.97
                        max_price = current_price * 1.02

                        if min_price <= ai_price <= max_price:
                            return ai_price
                        else:
                            logger.warning(f"   ⚠️ AI 추천가가 범위 벗어남, 조정 적용")
                            return max(min_price, min(ai_price, max_price))

                except Exception as e:
                    logger.warning(f"   ⚠️ AI 분석 실패: {e}")

            # Fallback: AI 없이 간단한 로직
            logger.info(f"   📊 기본 전략 사용 (AI 분석 불가)")

            if last_filled_price:
                # 이전 체결가 기준
                price_change_since_fill = ((current_price - last_filled_price) / last_filled_price) * 100

                if price_change_since_fill > 1:  # 1% 이상 상승
                    target = current_price * 0.997  # 현재가 -0.3% (빠른 매수)
                    logger.info(f"   💡 전략: 상승장 - 빠른 매수")
                elif price_change_since_fill < -1:  # 1% 이상 하락
                    target = current_price * 0.985  # 현재가 -1.5% (낮게 매수)
                    logger.info(f"   💡 전략: 하락장 - 더 낮게 매수")
                else:  # 횡보
                    target = current_price * 0.992  # 현재가 -0.8%
                    logger.info(f"   💡 전략: 횡보장 - 중간 가격")
            else:
                # 첫 주문처럼 처리
                target = current_price * 0.995

            return target

        except Exception as e:
            logger.error(f"목표가 계산 오류: {e}", exc_info=True)
            return None

    def _calculate_target_price_with_ai(
        self,
        stock_code: str,
        stock_name: str,
        current_price: float,
        entry_price: float,
        split_index: int,
        total_splits: int,
        last_filled_price: Optional[float],
        remaining_quantity: int
    ) -> Optional[float]:
        """
        AI를 활용한 목표 매도가 계산

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            current_price: 현재가
            entry_price: 평균 매수가
            split_index: 현재 분할 인덱스 (0, 1, 2...)
            total_splits: 총 분할 횟수
            last_filled_price: 이전 체결가 (None이면 첫 주문)
            remaining_quantity: 남은 수량

        Returns:
            목표 매도가
        """
        try:
            # 손익률 계산
            profit_loss_rate = ((current_price - entry_price) / entry_price) * 100

            # 1차 주문: 단순 로직
            if split_index == 0:
                if profit_loss_rate < -5:  # 5% 이상 손실
                    # 빠른 탈출: 현재가 +0.5%
                    target = current_price * 1.005
                    logger.info(f"   💡 1차 전략: 손실 빠른 탈출 (현재가 +0.5%)")
                elif profit_loss_rate < 2:  # 2% 미만 수익
                    # 조금 기다림: 현재가 +1%
                    target = current_price * 1.01
                    logger.info(f"   💡 1차 전략: 소폭 익절 (현재가 +1%)")
                else:  # 2% 이상 수익
                    # 더 기다림: 현재가 +2%
                    target = current_price * 1.02
                    logger.info(f"   💡 1차 전략: 익절 확대 (현재가 +2%)")

                return target

            # 2차, 3차 주문: AI 분석 활용
            if self.ai_analyzer and last_filled_price:
                logger.info(f"   🤖 AI 시장 분석 중...")

                # 이전 체결 이후 가격 변화
                price_change_since_fill = ((current_price - last_filled_price) / last_filled_price) * 100

                logger.info(f"   📈 이전 체결가 대비: {price_change_since_fill:+.2f}%")

                # AI에게 질문
                ai_prompt = f"""
당신은 한국 주식 시장 전문 트레이더입니다.

## 현재 상황
- 종목: {stock_name}({stock_code})
- 현재가: {current_price:,.0f}원
- 평균 매수가: {entry_price:,.0f}원
- 현재 손익률: {profit_loss_rate:+.2f}%
- 이전 체결가: {last_filled_price:,.0f}원
- 이전 체결 후 변화: {price_change_since_fill:+.2f}%
- 진행 상황: {split_index + 1}/{total_splits}차 매도
- 남은 수량: {remaining_quantity}주

## 질문
다음 매도 주문의 적정 가격을 추천해주세요.

## 응답 형식 (JSON)
{{
  "recommended_price": 추천_매도가_숫자만,
  "reasoning": "추천 이유 (1-2문장)",
  "market_condition": "상승중/하락중/횡보중"
}}

응답은 반드시 JSON 형식으로만 작성하세요. 다른 설명은 불필요합니다.
"""

                try:
                    # AI 분석 요청 (간단한 버전 - 실제로는 Gemini API 호출)
                    ai_response = self._call_ai_for_price_recommendation(ai_prompt)

                    if ai_response and 'recommended_price' in ai_response:
                        ai_price = float(ai_response['recommended_price'])
                        reasoning = ai_response.get('reasoning', '')
                        market_condition = ai_response.get('market_condition', '')

                        logger.info(f"   ✅ AI 추천가: {ai_price:,.0f}원")
                        logger.info(f"   📝 시장 상황: {market_condition}")
                        logger.info(f"   💬 판단 근거: {reasoning}")

                        # 안전 범위 검증 (현재가의 ±5% 이내)
                        min_price = current_price * 0.95
                        max_price = current_price * 1.05

                        if min_price <= ai_price <= max_price:
                            return ai_price
                        else:
                            logger.warning(f"   ⚠️ AI 추천가가 범위 벗어남, 조정 적용")
                            return max(min_price, min(ai_price, max_price))

                except Exception as e:
                    logger.warning(f"   ⚠️ AI 분석 실패: {e}")

            # Fallback: AI 없이 간단한 로직
            logger.info(f"   📊 기본 전략 사용 (AI 분석 불가)")

            if last_filled_price:
                # 이전 체결가 기준
                if price_change_since_fill > 1:  # 1% 이상 상승
                    target = current_price * 1.015  # 현재가 +1.5%
                    logger.info(f"   💡 전략: 상승장 추세 - 높게 설정")
                elif price_change_since_fill < -1:  # 1% 이상 하락
                    target = current_price * 1.003  # 현재가 +0.3%
                    logger.info(f"   💡 전략: 하락장 - 빠른 처분")
                else:  # 횡보
                    target = current_price * 1.008  # 현재가 +0.8%
                    logger.info(f"   💡 전략: 횡보장 - 중간 가격")
            else:
                # 첫 주문처럼 처리
                target = current_price * 1.01

            return target

        except Exception as e:
            logger.error(f"목표가 계산 오류: {e}", exc_info=True)
            return None

    def _call_ai_for_price_recommendation(self, prompt: str) -> Optional[Dict]:
        """
        AI에게 가격 추천 요청

        Args:
            prompt: AI 프롬프트

        Returns:
            AI 응답 (JSON)
        """
        try:
            if not self.ai_analyzer:
                return None

            # Gemini API 호출
            if not hasattr(self.ai_analyzer, 'model') or not self.ai_analyzer.model:
                # analyzer가 초기화되지 않았으면 초기화 시도
                if not self.ai_analyzer.initialize():
                    logger.warning("AI analyzer 초기화 실패")
                    return None

            # Gemini에게 직접 질문
            response = self.ai_analyzer.model.generate_content(
                prompt,
                request_options={'timeout': 30}
            )

            if not response or not response.text:
                logger.warning("AI 응답 없음")
                return None

            # JSON 파싱
            response_text = response.text.strip()

            # 코드 블록 제거 (```json ... ``` 형식)
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                # 첫 줄과 마지막 줄 제거
                if len(lines) > 2:
                    response_text = '\n'.join(lines[1:-1])

            # JSON 파싱
            import json
            result = json.loads(response_text)

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"AI 응답 JSON 파싱 실패: {e}")
            logger.debug(f"응답 내용: {response_text[:200]}")
            return None
        except Exception as e:
            logger.error(f"AI 호출 오류: {e}")
            return None

    def _place_buy_order(
        self,
        stock_code: str,
        quantity: int,
        price: int,
        account_number: str,
        exchange: str
    ) -> Optional[Dict]:
        """매수 주문 실행"""
        try:
            result = self.order_api.buy(
                stock_code=stock_code,
                quantity=quantity,
                price=price,
                order_type='02',  # 지정가
                account_number=account_number,
                exchange=exchange
            )
            return result
        except Exception as e:
            logger.error(f"매수 주문 실행 오류: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _place_sell_order(
        self,
        stock_code: str,
        quantity: int,
        price: int,
        account_number: str,
        exchange: str
    ) -> Optional[Dict]:
        """매도 주문 실행"""
        try:
            result = self.order_api.sell(
                stock_code=stock_code,
                quantity=quantity,
                price=price,
                order_type='02',  # 지정가
                account_number=account_number,
                exchange=exchange
            )
            return result
        except Exception as e:
            logger.error(f"매도 주문 실행 오류: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _wait_for_fill(
        self,
        stock_code: str,
        order_number: str,
        expected_quantity: int,
        max_wait_seconds: int
    ) -> Optional[Dict]:
        """
        체결 대기 및 확인 (REAL - 실제 API 확인)

        Args:
            stock_code: 종목코드
            order_number: 주문번호
            expected_quantity: 예상 체결 수량
            max_wait_seconds: 최대 대기 시간 (초)

        Returns:
            체결 정보 딕셔너리
        """
        try:
            start_time = datetime.now()
            check_interval = 2  # 2초마다 체크
            order_seen_in_pending = False  # CRITICAL FIX: 주문이 미체결 목록에 한 번이라도 나타났는지 추적

            logger.info(f"   🔍 체결 확인 시작: 주문번호={order_number}")

            while (datetime.now() - start_time).seconds < max_wait_seconds:
                try:
                    # CRITICAL: 실제 API로 미체결 주문 조회
                    pending_orders = self.account_api.get_pending_orders(stock_code=stock_code)

                    # 미체결 목록에서 해당 주문 찾기
                    found_order = None
                    if pending_orders:
                        for order in pending_orders:
                            if order.get('order_no') == order_number or order.get('odno') == order_number:
                                found_order = order
                                break

                    if found_order:
                        # 주문이 미체결 목록에 있음
                        order_seen_in_pending = True

                        # 미체결 상태 확인
                        remaining_qty = int(found_order.get('psbl_qty') or found_order.get('remaining_quantity', expected_quantity))
                        filled_qty = expected_quantity - remaining_qty

                        if filled_qty > 0 and filled_qty < expected_quantity:
                            # 부분 체결
                            logger.info(f"   📊 부분 체결: {filled_qty}/{expected_quantity}주")
                        else:
                            # 아직 미체결
                            elapsed = (datetime.now() - start_time).seconds
                            logger.debug(f"   ⏳ 미체결 ({elapsed}/{max_wait_seconds}초)")

                    elif order_seen_in_pending:
                        # CRITICAL FIX: 주문이 이전에 미체결 목록에 있었는데 지금은 없음 = 체결됨!
                        logger.info(f"   ✅ 체결 완료 (미체결 목록에서 사라짐)")

                        # 체결 내역에서 실제 체결가 조회
                        try:
                            executed_orders = self.account_api.get_executed_orders(stock_code=stock_code)
                            if executed_orders:
                                for order in executed_orders:
                                    if order.get('order_no') == order_number or order.get('odno') == order_number:
                                        filled_price = float(order.get('avg_prc') or order.get('executed_price', 0))
                                        filled_qty = int(order.get('tot_ccld_qty') or order.get('executed_quantity', expected_quantity))

                                        logger.info(f"   💰 체결가: {filled_price:,.0f}원")
                                        logger.info(f"   📦 체결량: {filled_qty}주")

                                        return {
                                            'filled': True,
                                            'filled_quantity': filled_qty,
                                            'filled_price': filled_price
                                        }
                        except Exception as e:
                            logger.warning(f"   체결 내역 조회 실패: {e}")

                        # 체결 내역 조회 실패해도 미체결에서 사라졌으면 체결된 것
                        return {
                            'filled': True,
                            'filled_quantity': expected_quantity,
                            'filled_price': None  # 가격은 모름
                        }
                    else:
                        # 아직 주문이 미체결 목록에 나타나지 않음 (시스템 등록 대기)
                        elapsed = (datetime.now() - start_time).seconds
                        logger.debug(f"   ⏳ 주문 등록 대기 중... ({elapsed}/{max_wait_seconds}초)")

                except Exception as e:
                    logger.warning(f"   체결 확인 오류: {e}")

                # 대기
                time.sleep(check_interval)

            # 시간 초과
            logger.warning(f"   ⚠️ 체결 대기 시간 초과 ({max_wait_seconds}초)")
            return {
                'filled': False,
                'note': '체결 대기 시간 초과'
            }

        except Exception as e:
            logger.error(f"체결 확인 오류: {e}", exc_info=True)
            return None

    def _get_current_price(self, stock_code: str) -> Optional[float]:
        """현재가 조회"""
        try:
            if not self.data_fetcher:
                return None

            price_info = self.data_fetcher.get_current_price(stock_code)
            if price_info:
                # 응답 형식에 따라 키가 다를 수 있음
                price = price_info.get('current_price') or price_info.get('stck_prpr')
                if price:
                    return float(price)

            return None

        except Exception as e:
            logger.error(f"현재가 조회 오류: {e}")
            return None


__all__ = ['AIAdaptiveSplitExecutor']
