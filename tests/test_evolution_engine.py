"""
테스트: 진화 알고리즘 엔진 및 24시간 스케줄러

모든 기능이 제대로 작동하는지 검증
"""
import sys
import os
import time
import logging
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# 직접 import (패키지 초기화 피하기)
import importlib.util

# evolution_engine 직접 로드
spec = importlib.util.spec_from_file_location(
    "evolution_engine",
    Path(__file__).parent.parent / "virtual_trading" / "evolution_engine.py"
)
evolution_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evolution_module)

StrategyEvolutionEngine = evolution_module.StrategyEvolutionEngine
StrategyGene = evolution_module.StrategyGene

# manager 직접 로드
spec = importlib.util.spec_from_file_location(
    "manager",
    Path(__file__).parent.parent / "virtual_trading" / "manager.py"
)
manager_module = importlib.util.module_from_spec(spec)
sys.modules['virtual_trading.models'] = type('MockModule', (), {
    'VirtualTradingDB': type('VirtualTradingDB', (), {
        '__init__': lambda self, db_path: None,
        'create_strategy': lambda self, name, desc, capital: 1,
        'get_all_strategies': lambda self: [],
        'get_open_positions': lambda self: [],
        'open_position': lambda self, **kwargs: 1,
        'close_position': lambda self, **kwargs: 0,
        'get_strategy_summary': lambda self, sid=None: []
    })
})()
spec.loader.exec_module(manager_module)

VirtualTradingManager = manager_module.VirtualTradingManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockDataFetcher:
    """테스트용 Mock DataFetcher"""

    def get_current_price(self, stock_code):
        """테스트용 가격 반환"""
        return {
            'current_price': 50000,
            'volume': 1000000,
            'change_rate': 2.5
        }

    def get_comprehensive_data(self, stock_code):
        """테스트용 종합 데이터"""
        return {
            'current_price': 50000,
            'volume': 1000000,
            'avg_volume': 800000,
            'change_rate': 2.5,
            'rsi': 55,
            'macd': 150,
            'macd_signal': 120,
            'volatility': 0.025
        }


def test_strategy_gene_creation():
    """테스트 1: 전략 유전자 생성"""
    logger.info("=" * 60)
    logger.info("테스트 1: 전략 유전자 생성")
    logger.info("=" * 60)

    gene = StrategyGene(
        rsi_min=30.0,
        rsi_max=60.0,
        volume_ratio_min=1.5,
        bid_ask_ratio_min=1.1,
        take_profit_pct=10.0,
        stop_loss_pct=5.0,
        trailing_stop_pct=7.0,
        rsi_overbought_min=70.0,
        rsi_overbought_max=85.0,
        position_size_pct=15.0,
        max_positions=3,
        trade_start_hour=9,
        trade_end_hour=15,
        price_min=10000,
        price_max=200000,
        split_buy_enabled=True,
        split_buy_count=3
    )

    logger.info(f"✅ 유전자 생성 완료")
    logger.info(f"   RSI: {gene.rsi_min}-{gene.rsi_max}")
    logger.info(f"   거래량 비율: {gene.volume_ratio_min}x 이상")
    logger.info(f"   익절: +{gene.take_profit_pct}%, 손절: -{gene.stop_loss_pct}%")
    logger.info(f"   포지션 크기: {gene.position_size_pct}% (최대 {gene.max_positions}개)")

    return True


def test_evolution_engine_init():
    """테스트 2: 진화 엔진 초기화"""
    logger.info("\n" + "=" * 60)
    logger.info("테스트 2: 진화 엔진 초기화")
    logger.info("=" * 60)

    # DB 경로 설정
    test_db_path = "/tmp/test_virtual_trading.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    # VirtualTradingManager 생성
    virtual_manager = VirtualTradingManager(db_path=test_db_path)
    data_fetcher = MockDataFetcher()

    # 진화 엔진 생성
    evolution_engine = StrategyEvolutionEngine(
        virtual_manager=virtual_manager,
        data_fetcher=data_fetcher,
        population_size=5,  # 테스트용으로 작게
        elite_ratio=0.4,
        mutation_rate=0.2,
        initial_capital=1000000
    )

    logger.info(f"✅ 진화 엔진 초기화 완료")
    logger.info(f"   모집단 크기: {evolution_engine.population_size}")
    logger.info(f"   엘리트 비율: {evolution_engine.elite_ratio * 100}%")
    logger.info(f"   돌연변이 확률: {evolution_engine.mutation_rate * 100}%")

    return evolution_engine, virtual_manager, data_fetcher


def test_population_initialization(evolution_engine):
    """테스트 3: 초기 모집단 생성"""
    logger.info("\n" + "=" * 60)
    logger.info("테스트 3: 초기 모집단 생성")
    logger.info("=" * 60)

    strategy_ids = evolution_engine.initialize_population()

    logger.info(f"✅ 초기 모집단 생성 완료: {len(strategy_ids)}개")
    logger.info(f"   전략 ID: {strategy_ids}")
    logger.info(f"   유전자 풀 크기: {len(evolution_engine.gene_pool)}")

    # 각 전략의 유전자 확인
    for i, (strategy_id, gene) in enumerate(evolution_engine.gene_pool[:3]):
        logger.info(f"   전략 #{strategy_id}: RSI {gene.rsi_min:.1f}-{gene.rsi_max:.1f}, "
                   f"익절 {gene.take_profit_pct:.1f}%")

    return len(strategy_ids) == evolution_engine.population_size


def test_fitness_evaluation(evolution_engine, virtual_manager):
    """테스트 4: 적합도 평가"""
    logger.info("\n" + "=" * 60)
    logger.info("테스트 4: 적합도 평가")
    logger.info("=" * 60)

    # 테스트용으로 일부 전략에 거래 내역 추가
    for strategy_id, gene in evolution_engine.gene_pool[:2]:
        # 테스트 매수
        virtual_manager.execute_buy(
            strategy_id=strategy_id,
            stock_code="005930",
            stock_name="삼성전자",
            quantity=10,
            price=50000,
            stop_loss_percent=5.0,
            take_profit_percent=10.0,
            use_split=False
        )

        # 가격 업데이트 (수익 발생)
        virtual_manager.update_prices({"005930": 55000})

    # 적합도 평가
    fitness_results = evolution_engine.evaluate_fitness()

    logger.info(f"✅ 적합도 평가 완료: {len(fitness_results)}개")

    for i, fitness in enumerate(fitness_results[:3]):
        logger.info(
            f"   [{i+1}] 전략#{fitness.strategy_id}: "
            f"수익률={fitness.return_rate:.2f}%, "
            f"샤프={fitness.sharpe_ratio:.2f}, "
            f"승률={fitness.win_rate:.1f}%, "
            f"점수={fitness.total_score:.1f} "
            f"(수익성={fitness.fitness_score:.1f}, 안전성={fitness.safety_score:.1f})"
        )

    return len(fitness_results) > 0


def test_evolution_cycle(evolution_engine):
    """테스트 5: 진화 사이클 (선택, 교배, 돌연변이)"""
    logger.info("\n" + "=" * 60)
    logger.info("테스트 5: 진화 사이클")
    logger.info("=" * 60)

    initial_generation = evolution_engine.generation
    initial_gene_pool_size = len(evolution_engine.gene_pool)

    logger.info(f"   현재 세대: {initial_generation}")
    logger.info(f"   현재 모집단: {initial_gene_pool_size}개")

    # 진화 실행
    new_strategy_ids = evolution_engine.evolve_generation()

    logger.info(f"✅ 진화 완료")
    logger.info(f"   새로운 세대: {evolution_engine.generation}")
    logger.info(f"   새로운 전략: {len(new_strategy_ids)}개 생성")
    logger.info(f"   현재 모집단: {len(evolution_engine.gene_pool)}개")

    # 최고 전략 확인
    best_info = evolution_engine.get_best_strategy_info()
    if best_info:
        logger.info(f"   🏆 최고 전략: 전략#{best_info['strategy_id']}")
        logger.info(f"      수익률={best_info['return_rate']:.2f}%, "
                   f"점수={best_info['total_score']:.1f}")

    return evolution_engine.generation == initial_generation + 1


def test_scheduler_24_7():
    """테스트 6: 24시간 스케줄러 (장 시간 체크 제거 확인)"""
    logger.info("\n" + "=" * 60)
    logger.info("테스트 6: 24시간 스케줄러")
    logger.info("=" * 60)

    # 스케줄러 코드 확인
    scheduler_code_path = Path(__file__).parent.parent / "virtual_trading" / "scheduler.py"

    with open(scheduler_code_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # 장 시간 체크가 제거되었는지 확인
    has_trading_hours_block = "if not is_any_trading_hours():" in code and "return" in code.split("if not is_any_trading_hours():")[1].split('\n')[0:3]

    if has_trading_hours_block:
        logger.error("❌ 장 시간 체크가 아직 있습니다!")
        logger.error("   _execute_virtual_trading()에서 'if not is_any_trading_hours(): return' 제거 필요")
        return False

    # 24시간 실행 로그 확인
    has_24_7_log = "💤 장외 시간 - 과거 데이터로 가상매매 계속 실행" in code
    has_trading_log = "🕐 장중 시간 - 실시간 데이터로 가상매매 실행" in code

    if has_24_7_log and has_trading_log:
        logger.info("✅ 24시간 스케줄러 확인 완료")
        logger.info("   - 장외 시간에도 계속 실행")
        logger.info("   - 과거 데이터 사용 로그 있음")
        return True
    else:
        logger.error("❌ 24시간 로그가 없습니다")
        return False


def test_thread_count():
    """테스트 7: 5개 스레드 확인"""
    logger.info("\n" + "=" * 60)
    logger.info("테스트 7: 백그라운드 스레드 개수 확인")
    logger.info("=" * 60)

    scheduler_code_path = Path(__file__).parent.parent / "virtual_trading" / "scheduler.py"

    with open(scheduler_code_path, 'r', encoding='utf-8') as f:
        code = f.read()

    threads = {
        'update_thread': 'self.update_thread = threading.Thread' in code,
        'check_thread': 'self.check_thread = threading.Thread' in code,
        'trading_thread': 'self.trading_thread = threading.Thread' in code,
        'ai_management_thread': 'self.ai_management_thread = threading.Thread' in code,
        'evolution_thread': 'self.evolution_thread = threading.Thread' in code
    }

    logger.info(f"   스레드 확인:")
    for thread_name, exists in threads.items():
        status = "✅" if exists else "❌"
        logger.info(f"   {status} {thread_name}: {'있음' if exists else '없음'}")

    all_exists = all(threads.values())

    if all_exists:
        logger.info(f"✅ 5개 스레드 모두 확인 완료")
    else:
        logger.error(f"❌ 일부 스레드가 없습니다")

    return all_exists


def test_evolution_engine_indicators():
    """테스트 8: 진화 엔진이 보는 지표 확인"""
    logger.info("\n" + "=" * 60)
    logger.info("테스트 8: 진화 엔진 지표 확인")
    logger.info("=" * 60)

    # StrategyGene의 모든 필드 확인
    from dataclasses import fields

    gene_fields = fields(StrategyGene)

    logger.info(f"   현재 보는 지표 ({len(gene_fields)}개):")

    field_categories = {
        '매수 조건': ['rsi_min', 'rsi_max', 'volume_ratio_min', 'bid_ask_ratio_min'],
        '매도 조건': ['take_profit_pct', 'stop_loss_pct', 'trailing_stop_pct',
                    'rsi_overbought_min', 'rsi_overbought_max'],
        '포지션 관리': ['position_size_pct', 'max_positions'],
        '시간/가격': ['trade_start_hour', 'trade_end_hour', 'price_min', 'price_max'],
        '분할 매수': ['split_buy_enabled', 'split_buy_count']
    }

    for category, field_names in field_categories.items():
        logger.info(f"\n   [{category}]")
        for field_name in field_names:
            field = next((f for f in gene_fields if f.name == field_name), None)
            if field:
                logger.info(f"      ✅ {field.name}: {field.type}")
            else:
                logger.info(f"      ❌ {field_name}: 없음")

    # 추가해야 할 지표
    logger.info(f"\n   추가 필요한 지표:")
    missing_indicators = [
        "MACD (signal, histogram)",
        "볼린저 밴드 (상단, 하단)",
        "이동평균선 (5일, 20일, 60일)",
        "스토캐스틱 (K, D)",
        "외국인/기관 순매수",
        "체결강도",
        "호가창 불균형",
        "프로그램 매매 순매수"
    ]

    for indicator in missing_indicators:
        logger.info(f"      ⚠️  {indicator}")

    return True


def run_all_tests():
    """모든 테스트 실행"""
    logger.info("\n" + "🧪" * 30)
    logger.info("진화 알고리즘 엔진 종합 테스트")
    logger.info("🧪" * 30 + "\n")

    results = []

    # 테스트 1: 유전자 생성
    try:
        result = test_strategy_gene_creation()
        results.append(("유전자 생성", result))
    except Exception as e:
        logger.error(f"❌ 테스트 1 실패: {e}", exc_info=True)
        results.append(("유전자 생성", False))

    # 테스트 2-5: 진화 엔진
    try:
        evolution_engine, virtual_manager, data_fetcher = test_evolution_engine_init()
        results.append(("진화 엔진 초기화", True))

        result = test_population_initialization(evolution_engine)
        results.append(("초기 모집단 생성", result))

        result = test_fitness_evaluation(evolution_engine, virtual_manager)
        results.append(("적합도 평가", result))

        result = test_evolution_cycle(evolution_engine)
        results.append(("진화 사이클", result))

    except Exception as e:
        logger.error(f"❌ 진화 엔진 테스트 실패: {e}", exc_info=True)
        results.append(("진화 엔진", False))

    # 테스트 6-7: 스케줄러
    try:
        result = test_scheduler_24_7()
        results.append(("24시간 스케줄러", result))

        result = test_thread_count()
        results.append(("5개 스레드", result))

    except Exception as e:
        logger.error(f"❌ 스케줄러 테스트 실패: {e}", exc_info=True)
        results.append(("스케줄러", False))

    # 테스트 8: 지표 확인
    try:
        result = test_evolution_engine_indicators()
        results.append(("지표 확인", result))
    except Exception as e:
        logger.error(f"❌ 지표 테스트 실패: {e}", exc_info=True)
        results.append(("지표 확인", False))

    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("테스트 결과 요약")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {status}: {test_name}")

    logger.info(f"\n총 {passed}/{total} 테스트 통과 ({passed/total*100:.1f}%)")

    if passed == total:
        logger.info("🎉 모든 테스트 통과!")
    else:
        logger.warning(f"⚠️  {total - passed}개 테스트 실패")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
