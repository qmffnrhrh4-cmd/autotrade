"""
virtual_trading/scheduler.py
가상매매 백그라운드 스케줄러

실시간 가격 업데이트, 자동 손절/익절 체크, 독립적인 자동 매매
"""
import time
import logging
import threading
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class VirtualTradingScheduler:
    """가상매매 백그라운드 스케줄러"""

    def __init__(self, virtual_manager, data_fetcher=None, bot_instance=None):
        """
        Args:
            virtual_manager: VirtualTradingManager 인스턴스
            data_fetcher: DataFetcher 인스턴스 (가격 조회용)
            bot_instance: AutoTradingBot 인스턴스 (독립 매매용)
        """
        self.virtual_manager = virtual_manager
        self.data_fetcher = data_fetcher
        self.bot_instance = bot_instance  # Fix v6.1.4: 독립적인 매매를 위한 bot 참조
        self.is_running = False
        self.update_thread = None
        self.check_thread = None
        self.trading_thread = None  # Fix v6.1.4: 자동 매매 스레드
        self.ai_management_thread = None  # Fix v6.3: AI 전략 자동 관리 스레드
        self.evolution_thread = None  # Fix v6.4: 진화 알고리즘 스레드 (YOLO-style)
        self.cleanup_thread = None  # 전략 정리 스레드 (매일 자정)

        # 진화 엔진
        self.evolution_engine = None

        logger.info("가상매매 스케줄러 초기화")

    def start(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return

        self.is_running = True

        # 가격 업데이트 스레드 (5초마다)
        self.update_thread = threading.Thread(
            target=self._price_update_loop,
            daemon=True
        )
        self.update_thread.start()

        # 손절/익절 체크 스레드 (5초마다)
        self.check_thread = threading.Thread(
            target=self._stop_loss_take_profit_loop,
            daemon=True
        )
        self.check_thread.start()

        # Fix v6.1.4: 독립적인 자동 매매 스레드 (60초마다)
        if self.bot_instance:
            self.trading_thread = threading.Thread(
                target=self._auto_trading_loop,
                daemon=True
            )
            self.trading_thread.start()
            logger.info("✅ 가상매매 독립 매매 스레드 시작")

        # Fix v6.3: AI 전략 자동 관리 스레드 (1시간마다)
        if self.data_fetcher:
            self.ai_management_thread = threading.Thread(
                target=self._ai_management_loop,
                daemon=True
            )
            self.ai_management_thread.start()
            logger.info("✅ AI 전략 자동 관리 스레드 시작")

        # Fix v6.4: 진화 알고리즘 스레드 (10분마다) - YOLO-style 계속 학습
        if self.data_fetcher:
            self.evolution_thread = threading.Thread(
                target=self._evolution_loop,
                daemon=True
            )
            self.evolution_thread.start()
            logger.info("✅ 진화 알고리즘 스레드 시작 (YOLO-style 연속 학습)")

        # 전략 정리 스레드 (1시간마다)
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True
        )
        self.cleanup_thread.start()
        logger.info("✅ 전략 자동 정리 스레드 시작 (1시간마다)")

        # 즉시 전략 정리 실행 (시작 시) - 동기적으로 실행하여 완료 보장
        logger.info("🧹 시작 시 전략 정리 즉시 실행...")
        try:
            self._execute_cleanup()
            logger.info("✅ 시작 시 전략 정리 완료")
        except Exception as e:
            logger.error(f"❌ 시작 시 전략 정리 실패: {e}", exc_info=True)

        logger.info("가상매매 스케줄러 시작 (24시간 실행, 6개 스레드)")

    def stop(self):
        """스케줄러 중지"""
        self.is_running = False

        if self.update_thread:
            self.update_thread.join(timeout=2)

        if self.check_thread:
            self.check_thread.join(timeout=2)

        if self.trading_thread:
            self.trading_thread.join(timeout=2)

        if self.ai_management_thread:
            self.ai_management_thread.join(timeout=2)

        if self.evolution_thread:
            self.evolution_thread.join(timeout=2)

        logger.info("가상매매 스케줄러 중지")

    def _price_update_loop(self):
        """가격 업데이트 루프 (5초마다)"""
        logger.info("가격 업데이트 스레드 시작")

        while self.is_running:
            try:
                self._update_prices()
            except Exception as e:
                logger.error(f"가격 업데이트 실패: {e}")

            # 5초 대기
            time.sleep(5)

    def _stop_loss_take_profit_loop(self):
        """손절/익절 체크 루프 (5초마다)"""
        logger.info("손절/익절 체크 스레드 시작")

        while self.is_running:
            try:
                self._check_stop_loss_take_profit()
            except Exception as e:
                logger.error(f"손절/익절 체크 실패: {e}")

            # 5초 대기
            time.sleep(5)

    def _auto_trading_loop(self):
        """
        독립적인 자동 매매 루프 (60초마다)
        Fix v6.1.4: 실제 매매 없이도 가상매매가 독립적으로 실행
        Fix v6.3: 24시간 실행 (장 시간 체크 제거)
        """
        logger.info("🤖 가상매매 독립 매매 스레드 시작 (24시간 실행)")

        # 첫 실행은 30초 후 (초기화 완료 대기)
        time.sleep(30)

        while self.is_running:
            try:
                self._execute_virtual_trading()
            except Exception as e:
                logger.error(f"가상매매 자동 실행 실패: {e}", exc_info=True)

            # 60초 대기
            time.sleep(60)

    def _ai_management_loop(self):
        """
        AI 전략 자동 관리 루프 (1시간마다)
        Fix v6.3: 24시간 실행 - 전략 검토, 개선, 추천
        """
        logger.info("🤖 AI 전략 자동 관리 스레드 시작 (24시간 실행)")

        # 첫 실행은 5분 후 (초기 데이터 수집 대기)
        time.sleep(300)

        while self.is_running:
            try:
                self._execute_ai_management()
            except Exception as e:
                logger.error(f"AI 전략 관리 실패: {e}", exc_info=True)

            # 1시간 대기
            time.sleep(3600)

    def _evolution_loop(self):
        """
        진화 알고리즘 루프 (10분마다)
        Fix v6.4: YOLO처럼 계속 학습하고 진화
        """
        logger.info("🧬 진화 알고리즘 스레드 시작 (YOLO-style 연속 학습)")

        # 첫 실행은 1분 후 (초기 데이터 수집 대기)
        time.sleep(60)

        # 초기 모집단 생성
        try:
            from virtual_trading.evolution_engine import get_evolution_engine

            self.evolution_engine = get_evolution_engine(
                virtual_manager=self.virtual_manager,
                data_fetcher=self.data_fetcher
            )

            if self.evolution_engine:
                logger.info("🧬 초기 모집단 생성 중...")
                self.evolution_engine.initialize_population()
                logger.info("✅ 초기 모집단 생성 완료")
            else:
                logger.error("❌ 진화 엔진 초기화 실패")
                return

        except Exception as e:
            logger.error(f"진화 엔진 초기화 실패: {e}", exc_info=True)
            return

        # 10분마다 진화
        while self.is_running:
            try:
                logger.info("🧬 진화 알고리즘 실행 중...")
                self._execute_evolution()
            except Exception as e:
                logger.error(f"진화 실행 실패: {e}", exc_info=True)

            # 10분 대기
            time.sleep(600)

    def _execute_evolution(self):
        """
        진화 알고리즘 실행
        Fix v6.4: YOLO처럼 계속 학습 - 적합도 평가 → 선택 → 교배 → 돌연변이
        """
        if not self.evolution_engine:
            return

        try:
            # DB와 gene_pool 동기화 (cleanup으로 인한 불일치 방지)
            self.evolution_engine.sync_with_database()

            # gene_pool이 비어있으면 초기화
            if len(self.evolution_engine.gene_pool) == 0:
                logger.warning("⚠️ gene_pool이 비어있음 - 재초기화 필요")
                self.evolution_engine.initialize_population()
                return  # 다음 주기에 진화 실행

            # 다음 세대로 진화
            new_strategy_ids = self.evolution_engine.evolve_generation()

            # 최고 전략 정보
            best_info = self.evolution_engine.get_best_strategy_info()

            if best_info:
                logger.info(
                    f"🏆 현재 최고 전략 (제{best_info['generation']}세대): "
                    f"수익률={best_info['return_rate']:.2f}%, "
                    f"샤프={best_info['sharpe_ratio']:.2f}, "
                    f"승률={best_info['win_rate']:.1f}%, "
                    f"점수={best_info['total_score']:.1f}"
                )

                # 점수가 80점 이상이면 실매매 추천
                if best_info['total_score'] >= 80:
                    logger.info(
                        f"⭐⭐⭐ 실매매 적용 추천! "
                        f"전략#{best_info['strategy_id']} - "
                        f"높은 수익성({best_info['fitness_score']:.1f}) + "
                        f"높은 안전성({best_info['safety_score']:.1f})"
                    )

            logger.info(f"✅ 제{self.evolution_engine.generation}세대 진화 완료")

        except Exception as e:
            logger.error(f"진화 실행 중 오류: {e}", exc_info=True)

    def _execute_virtual_trading(self):
        """
        가상매매 실행: 시장 스캔 → 분석 → 매수/매도 결정

        Fix v6.3: 가상매매는 과거 데이터를 사용하므로 24시간 실행
        장 시간에 관계없이 OpenAPI로 데이터를 받아와서 계속 매매
        """
        # Fix v6.3: 장 시간 체크 제거 - 가상매매는 24시간 실행
        from utils.trading_date import is_any_trading_hours
        is_trading_hours = is_any_trading_hours()

        if not is_trading_hours:
            logger.info("💤 장외 시간 - 과거 데이터로 가상매매 계속 실행")
        else:
            logger.info("🕐 장중 시간 - 실시간 데이터로 가상매매 실행")

        # bot_instance가 없으면 실행 불가
        if not self.bot_instance:
            return

        # screener와 scoring_system이 없으면 실행 불가
        if not hasattr(self.bot_instance, 'screener') or not self.bot_instance.screener:
            logger.debug("Screener 없음 - 가상매매 건너뛰기")
            return

        if not hasattr(self.bot_instance, 'scoring_system') or not self.bot_instance.scoring_system:
            logger.debug("Scoring system 없음 - 가상매매 건너뛰기")
            return

        logger.info("🔍 가상매매: 시장 스캔 시작")

        try:
            # 1. 시장 스캔 (후보 종목 찾기)
            candidates = self._scan_market()

            if not candidates:
                logger.info("가상매매: 매수 후보 없음")
                return

            logger.info(f"가상매매: {len(candidates)}개 매수 후보 발견")

            # 2. 각 전략별로 매수 실행
            strategies = self.virtual_manager.db.get_all_strategies()

            if not strategies:
                logger.warning("가상매매: 전략 없음")
                return

            for strategy in strategies:
                self._try_buy_for_strategy(strategy, candidates)

        except Exception as e:
            logger.error(f"가상매매 실행 중 오류: {e}", exc_info=True)

    def _scan_market(self) -> List[Dict[str, Any]]:
        """
        시장 스캔하여 매수 후보 종목 찾기
        진화 알고리즘을 위해 항상 충분한 데이터 확보
        """
        try:
            # ScannerPipeline을 사용하여 후보 종목 찾기
            scanner = self.bot_instance.scanner
            scoring_system = self.bot_instance.scoring_system

            if not scanner:
                logger.warning("Scanner 없음")
                return []

            # 시장 스캔 실행
            candidates = scanner.scan_market()

            # 후보가 부족하면 (10개 미만) Fast Scan만 실행하여 기본 데이터 확보
            if not candidates or len(candidates) < 10:
                logger.info(f"가상매매: 스캔 결과 부족 ({len(candidates) if candidates else 0}개) - Fast Scan 시도")
                try:
                    fast_candidates = scanner.run_fast_scan()
                    if fast_candidates:
                        candidates = fast_candidates
                        logger.info(f"가상매매: Fast Scan으로 {len(candidates)}개 확보")
                except Exception as e:
                    logger.warning(f"Fast Scan 실패: {e}")

            if not candidates:
                logger.debug("가상매매: 스캔 결과 없음")
                return []

            logger.debug(f"가상매매: 스캔 결과 {len(candidates)}개")

            # 스코어링 (더 많은 종목 분석)
            scored_candidates = []
            for candidate in candidates[:50]:  # 20 → 50개로 확대
                try:
                    # StockCandidate 객체를 딕셔너리로 변환
                    stock_data = {
                        'stock_code': candidate.code,
                        'stock_name': candidate.name,
                        'current_price': candidate.price,
                        'volume': candidate.volume,
                        'change_rate': candidate.rate,
                        'institutional_net_buy': getattr(candidate, 'institutional_net_buy', 0),
                        'foreign_net_buy': getattr(candidate, 'foreign_net_buy', 0),
                        'bid_ask_ratio': getattr(candidate, 'bid_ask_ratio', 1.0),
                        'institutional_trend': getattr(candidate, 'institutional_trend', None),
                        'avg_volume': getattr(candidate, 'avg_volume', None),
                        'volatility': getattr(candidate, 'volatility', None),
                        'execution_intensity': getattr(candidate, 'execution_intensity', None),
                        'program_net_buy': getattr(candidate, 'program_net_buy', None),
                    }

                    # 기본 데이터 보강 (전략에서 사용)
                    stock_data['volume_ratio'] = stock_data.get('volume', 0) / max(stock_data.get('avg_volume', 1), 1) if stock_data.get('avg_volume') else 1.0
                    stock_data['price_change_percent'] = stock_data.get('change_rate', 0)
                    stock_data['rsi'] = 50  # 기본값 (실제로는 계산 필요)

                    # 스코어 계산 (올바른 시그니처)
                    scoring_result = scoring_system.calculate_score(stock_data, scan_type='default')
                    score = scoring_result.total_score

                    # 가상매매는 더 적극적으로 매수 (진화 알고리즘을 위한 데이터 확보)
                    if score >= 40:  # 70 → 40점으로 완화 (더 많은 거래로 다양성 확보)
                        scored_candidates.append({
                            'stock_code': candidate.code,
                            'stock_name': candidate.name,
                            'current_price': candidate.price,
                            'volume': candidate.volume,
                            'change_rate': candidate.rate,
                            'score': score,
                            'volume_ratio': stock_data['volume_ratio'],
                            'price_change_percent': stock_data['price_change_percent'],
                            'rsi': stock_data['rsi']
                        })
                except Exception as e:
                    logger.debug(f"스코어링 실패 ({getattr(candidate, 'code', 'Unknown')}): {e}")

            # 점수 높은 순으로 정렬
            scored_candidates.sort(key=lambda x: x['score'], reverse=True)

            logger.debug(f"가상매매: 스코어링 결과 {len(scored_candidates)}개 (70점 이상)")

            return scored_candidates[:15]  # 상위 15개 (다양성 확보)

        except Exception as e:
            logger.error(f"시장 스캔 실패: {e}", exc_info=True)
            return []

    def _try_buy_for_strategy(self, strategy: Dict[str, Any], candidates: List[Dict[str, Any]]):
        """
        특정 전략으로 매수 시도
        """
        strategy_id = strategy['id']
        strategy_name = strategy['name']

        try:
            # 해당 전략의 활성 포지션 확인
            positions = [p for p in self.virtual_manager.get_positions()
                        if p.get('strategy_id') == strategy_id]

            # 포지션 제한 없음 (무제한 매수로 승률 극대화)
            # 잔고만 확인

            # 전략의 잔고 확인
            strategy_info = self.virtual_manager.get_performance_metrics(strategy_id)
            available_cash = strategy_info.get('current_capital', 0) - strategy_info.get('total_investment', 0)

            if available_cash < 100000:  # 10만원 미만
                logger.debug(f"가상매매 ({strategy_name}): 잔고 부족 ({available_cash:,}원)")
                return

            # 이미 보유한 종목은 제외
            held_codes = {p['stock_code'] for p in positions}
            available_candidates = [c for c in candidates if c['stock_code'] not in held_codes]

            if not available_candidates:
                logger.debug(f"가상매매 ({strategy_name}): 매수 가능한 종목 없음")
                return

            # 한 번에 최대 5개까지 매수 (더 많이 분산 투자)
            max_buys_per_cycle = min(5, len(available_candidates))
            buy_count = 0

            for candidate in available_candidates[:max_buys_per_cycle]:
                stock_code = candidate['stock_code']
                stock_name = candidate.get('stock_name', stock_code)
                current_price = candidate.get('current_price', 0)

                if current_price <= 0:
                    # 현재가 조회
                    if self.data_fetcher:
                        price_info = self.data_fetcher.get_current_price(stock_code)
                        if price_info:
                            current_price = price_info.get('current_price', 0)

                if current_price <= 0:
                    logger.warning(f"가상매매: 현재가 조회 실패 ({stock_code})")
                    continue  # return → continue로 변경 (다음 종목 시도)

                # 매수 수량 계산 (자본의 10% - 더 많은 종목 분산 투자)
                target_amount = min(available_cash / max_buys_per_cycle, strategy_info.get('current_capital', 1000000) * 0.10)
                quantity = int(target_amount // current_price)

                if quantity < 1:
                    logger.debug(f"가상매매 ({strategy_name}): 수량 부족 (금액: {target_amount:,}원, 가격: {current_price:,}원)")
                    continue

                # 가상 매수 실행
                logger.info(f"🎯 가상매매 ({strategy_name}): {stock_name} {quantity}주 매수 시도 @ {current_price:,}원 ({buy_count+1}/{max_buys_per_cycle}) [현재 {len(positions)}개 보유]")

                # Fix v6.2: AI 기반 분할 매수 활성화
                # 시장 데이터 준비 (AI 분석용)
                market_data = {
                    'current_price': current_price,
                    'volume': candidate.get('volume', 0),
                    'volume_ratio': candidate.get('volume_ratio', 1.0),
                    'price_change_pct': candidate.get('change_rate', 0) / 100,
                    'volatility': 0.02,  # 기본값 (실제로는 계산 필요)
                    'avg_volume': candidate.get('volume', 0) / max(candidate.get('volume_ratio', 1), 0.1),
                    'rsi': candidate.get('rsi', 50),
                    'kospi_change_pct': 0.0,  # TODO: 실제 코스피 등락률
                    'kosdaq_change_pct': 0.0  # TODO: 실제 코스닥 등락률
                }

                result = self.virtual_manager.execute_buy(
                    strategy_id=strategy_id,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    quantity=quantity,
                    price=float(current_price),
                    stop_loss_percent=5.0,
                    take_profit_percent=10.0,
                    use_split=True,  # 분할 매수 활성화
                    use_ai_split=True,  # AI 기반 분할 전략 사용
                    market_data=market_data  # 시장 데이터 전달
                )

                if result:
                    logger.info(f"✅ 가상매매 ({strategy_name}): {stock_name} 매수 성공!")
                    buy_count += 1
                    available_cash -= target_amount  # 잔고 차감
                else:
                    logger.warning(f"⚠️ 가상매매 ({strategy_name}): {stock_name} 매수 실패")

            if buy_count > 0:
                logger.info(f"📊 가상매매 ({strategy_name}): 총 {buy_count}개 종목 매수 완료")

        except Exception as e:
            logger.error(f"가상매매 ({strategy_name}) 매수 시도 실패: {e}", exc_info=True)

    def _update_prices(self):
        """활성 포지션의 현재가 업데이트"""
        try:
            # 모든 활성 포지션 조회
            positions = self.virtual_manager.get_positions()

            if not positions:
                return

            # 종목별 현재가 수집
            price_updates = {}

            for position in positions:
                stock_code = position['stock_code']

                # 이미 조회한 종목은 스킵
                if stock_code in price_updates:
                    continue

                # 현재가 조회
                if self.data_fetcher:
                    try:
                        price_info = self.data_fetcher.get_current_price(stock_code)
                        if price_info and 'current_price' in price_info:
                            price_updates[stock_code] = price_info['current_price']
                    except Exception as e:
                        logger.debug(f"{stock_code} 가격 조회 실패: {e}")

            # 가격 업데이트
            if price_updates:
                self.virtual_manager.update_prices(price_updates)
                logger.debug(f"가격 업데이트: {len(price_updates)}개 종목")

        except Exception as e:
            logger.error(f"가격 업데이트 중 오류: {e}", exc_info=True)

    def _check_stop_loss_take_profit(self):
        """자동 손절/익절 조건 체크 및 실행"""
        try:
            executed_orders = self.virtual_manager.check_stop_loss_take_profit()

            if executed_orders:
                logger.info(f"자동 매도 실행: {len(executed_orders)}건")

                for order in executed_orders:
                    order_type = order['type']
                    stock_name = order['stock_name']
                    profit = order['profit']

                    type_text = '손절' if order_type == 'stop_loss' else '익절'
                    logger.info(
                        f"  [{type_text}] {stock_name}: "
                        f"{profit:+,.0f}원 @ {order['sell_price']:,}원"
                    )

        except Exception as e:
            logger.error(f"손절/익절 체크 중 오류: {e}", exc_info=True)

    def _execute_ai_management(self):
        """
        AI 전략 자동 관리 실행
        Fix v6.3: 24시간 실행 - 전략 검토, 개선, 추천

        1시간마다:
        - 모든 전략 성과 검토
        - 저성과 전략 자동 개선 (백테스팅)
        - S등급 전략 실매매 추천
        """
        logger.info("🤖 AI 전략 자동 관리 시작")

        try:
            # AIStrategyManager 임포트
            from virtual_trading import AIStrategyManager

            if not self.data_fetcher:
                logger.warning("DataFetcher 없음 - AI 관리 건너뛰기")
                return

            # AIStrategyManager 생성
            ai_manager = AIStrategyManager(
                virtual_manager=self.virtual_manager,
                data_fetcher=self.data_fetcher
            )

            # 모든 전략 가져오기
            strategies = self.virtual_manager.get_strategy_summary()
            if not strategies:
                logger.info("AI 관리: 전략 없음")
                return

            ai_manager.active_strategy_ids = [s.get('strategy_id') or s.get('id') for s in strategies]
            logger.info(f"AI 관리: {len(strategies)}개 전략 검토")

            # 1. 전략 성과 검토
            logger.info("📊 전략 성과 검토 중...")
            review_result = ai_manager.review_strategies()

            # 검토 결과 로그
            if review_result and 'grades' in review_result:
                for strategy_id, grade_info in review_result['grades'].items():
                    grade = grade_info.get('grade', '?')
                    score = grade_info.get('score', 0)
                    name = grade_info.get('name', f'전략{strategy_id}')
                    logger.info(f"  - {name}: {grade}등급 ({score}점)")

            # 2. C/D등급 전략 자동 개선 (백테스팅)
            poor_performers = [
                sid for sid, info in review_result.get('grades', {}).items()
                if info.get('grade') in ['C', 'D']
            ]

            if poor_performers:
                logger.info(f"🔧 {len(poor_performers)}개 저성과 전략 개선 중...")
                improvement_result = ai_manager.improve_strategies(backtest_period_days=30)

                if improvement_result:
                    logger.info(f"✅ 전략 개선 완료: {improvement_result.get('improved_count', 0)}개")
            else:
                logger.info("✅ 모든 전략이 양호한 성과 (B등급 이상)")

            # 3. S등급 전략 실매매 추천
            top_performers = [
                (sid, info) for sid, info in review_result.get('grades', {}).items()
                if info.get('grade') == 'S'
            ]

            if top_performers:
                logger.info(f"⭐ {len(top_performers)}개 S등급 전략 발견!")
                for strategy_id, info in top_performers:
                    name = info.get('name', f'전략{strategy_id}')
                    score = info.get('score', 0)
                    logger.info(f"   🏆 {name}: {score}점 - 실매매 적용 추천!")

            logger.info("🤖 AI 전략 자동 관리 완료")

        except Exception as e:
            logger.error(f"AI 전략 관리 실행 중 오류: {e}", exc_info=True)

    def get_status(self) -> Dict[str, Any]:
        """스케줄러 상태 조회"""
        status = {
            'is_running': self.is_running,
            'update_thread_alive': self.update_thread.is_alive() if self.update_thread else False,
            'check_thread_alive': self.check_thread.is_alive() if self.check_thread else False,
            'trading_thread_alive': self.trading_thread.is_alive() if self.trading_thread else False,
            'ai_management_thread_alive': self.ai_management_thread.is_alive() if self.ai_management_thread else False,
            'evolution_thread_alive': self.evolution_thread.is_alive() if self.evolution_thread else False,
            'positions_count': len(self.virtual_manager.get_positions()) if self.virtual_manager else 0
        }

        # 진화 엔진 상태 추가
        if self.evolution_engine:
            status['evolution_generation'] = self.evolution_engine.generation
            status['evolution_population_size'] = len(self.evolution_engine.gene_pool)

            best_info = self.evolution_engine.get_best_strategy_info()
            if best_info:
                status['best_strategy'] = {
                    'strategy_id': best_info['strategy_id'],
                    'generation': best_info['generation'],
                    'return_rate': best_info['return_rate'],
                    'total_score': best_info['total_score']
                }

        return status

    def _execute_cleanup(self):
        """전략 정리 실행 (단독 실행용)"""
        from datetime import datetime, timedelta

        # evolution_engine의 population_size보다 약간 높게 설정
        MAX_ACTIVE_STRATEGIES = 25  # evolution population_size(20) + 여유분(5)
        MIN_DAYS_TO_KEEP = 7
        PERFORMANCE_THRESHOLD = -20.0

        try:
            now = datetime.now()

            logger.info("=" * 60)
            logger.info("🧹 전략 자동 정리 시작")
            logger.info("=" * 60)

            all_strategies = self.virtual_manager.db.get_all_strategies()
            active_strategies = [s for s in all_strategies if s.get('is_active', 1) == 1]

            logger.info(f"현재 활성 전략: {len(active_strategies)}개 (목표: {MAX_ACTIVE_STRATEGIES}개)")

            if len(active_strategies) > MAX_ACTIVE_STRATEGIES:
                cleanup_count = 0

                # 모든 전략의 성과 계산
                strategy_scores = []
                for strategy in active_strategies:
                    strategy_id = strategy['id']
                    name = strategy['name']
                    current_capital = strategy.get('current_capital', 0)
                    initial_capital = strategy.get('initial_capital', 1)
                    created_at = strategy.get('created_at')

                    # 수익률 계산
                    profit_rate = ((current_capital - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0

                    # 생성일 체크
                    try:
                        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        days_old = (now - created_date).days
                    except:
                        days_old = 0

                    # 우선순위 점수 계산 (낮을수록 제거 우선)
                    # 1. 수익률이 낮을수록 점수 낮음
                    # 2. 오래될수록 점수 낮음 (단, 최근 3일은 보호)
                    priority_score = profit_rate
                    if days_old >= 3:
                        priority_score -= (days_old - 3) * 0.5  # 3일 이후부터 하루당 -0.5점

                    strategy_scores.append({
                        'id': strategy_id,
                        'name': name,
                        'profit_rate': profit_rate,
                        'days_old': days_old,
                        'priority_score': priority_score
                    })

                # 우선순위 점수 낮은 순으로 정렬 (성과 나쁜 것부터)
                strategy_scores.sort(key=lambda x: x['priority_score'])

                # 목표 개수만큼 제거 (무조건 하위 전략 제거)
                max_to_remove = len(active_strategies) - MAX_ACTIVE_STRATEGIES
                strategies_to_remove = strategy_scores[:max_to_remove]

                logger.info(f"제거 대상: {len(strategies_to_remove)}개")

                for strategy in strategies_to_remove[:10]:  # 처음 10개만 로그
                    logger.info(f"  - {strategy['name']}: 수익률 {strategy['profit_rate']:.1f}%, {strategy['days_old']}일 경과, 점수 {strategy['priority_score']:.1f}")

                if len(strategies_to_remove) > 10:
                    logger.info(f"  ... 외 {len(strategies_to_remove) - 10}개")

                cursor = self.virtual_manager.db.conn.cursor()
                for strategy in strategies_to_remove:
                    try:
                        cursor.execute(
                            "UPDATE virtual_strategies SET is_active = 0, updated_at = ? WHERE id = ?",
                            (now.isoformat(), strategy['id'])
                        )
                        cleanup_count += 1
                    except Exception as e:
                        logger.error(f"  ✗ {strategy['name']} 실패: {e}")

                self.virtual_manager.db.conn.commit()

                logger.info(f"✅ 정리 완료: {cleanup_count}개 비활성화")

                # evolution_engine에게 gene_pool 동기화 알림
                if self.evolution_engine and cleanup_count > 0:
                    self.evolution_engine.sync_with_database()
                    logger.info(f"🔄 진화 엔진 gene_pool 동기화 완료")
            else:
                logger.info("✅ 정리 불필요 (활성 전략 수 적정)")

            # 오래된 포지션 정리 (30일 이상) - 스킵 (virtual_positions에 status 컬럼 없음)
            # 대신 is_closed=0인 오래된 포지션 정리
            old_position_cutoff = (now - timedelta(days=30)).isoformat()
            try:
                cursor = self.virtual_manager.db.conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM virtual_positions
                    WHERE is_closed = 0
                    AND created_at < ?
                    """,
                    (old_position_cutoff,)
                )
                old_positions = cursor.fetchall()

                if old_positions:
                    logger.info(f"오래된 포지션 정리: {len(old_positions)}개")
                    for pos in old_positions[:20]:  # 최대 20개
                        try:
                            cursor.execute(
                                """
                                UPDATE virtual_positions
                                SET is_closed = 1,
                                    updated_at = ?
                                WHERE id = ?
                                """,
                                (now.isoformat(), pos['id'])
                            )
                        except Exception as e:
                            logger.error(f"포지션 정리 실패: {e}")

                    self.virtual_manager.db.conn.commit()
                    logger.info(f"✅ 오래된 포지션 정리 완료")
            except Exception as e:
                logger.warning(f"포지션 정리 스킵: {e}")

            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"전략 정리 중 오류: {e}", exc_info=True)

    def _cleanup_loop(self):
        """전략 자동 정리 루프 (1시간마다)"""
        logger.info("전략 자동 정리 루프 시작 (1시간마다)")

        while self.is_running:
            try:
                # 1시간 대기
                time.sleep(3600)

                # 정리 실행
                self._execute_cleanup()

            except Exception as e:
                logger.error(f"전략 정리 루프 오류: {e}", exc_info=True)
                time.sleep(3600)
