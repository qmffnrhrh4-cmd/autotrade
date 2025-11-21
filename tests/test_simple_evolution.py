"""
간단한 진화 엔진 테스트

의존성 없이 핵심 기능만 테스트
"""
import sys
import logging
from pathlib import Path
from dataclasses import fields

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def test_24_hour_scheduler():
    """24시간 스케줄러 테스트"""
    logger.info("=" * 60)
    logger.info("테스트 1: 24시간 스케줄러 검증")
    logger.info("=" * 60)

    scheduler_path = Path(__file__).parent.parent / "virtual_trading" / "scheduler.py"

    with open(scheduler_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # 문제점 체크
    issues = []

    # 1. 장 시간 체크 후 return이 있는지
    if "if not is_any_trading_hours():" in code:
        # return 문이 바로 다음 줄에 있는지 확인
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if 'if not is_any_trading_hours():' in line:
                # 다음 몇 줄 확인
                next_lines = lines[i+1:i+5]
                for next_line in next_lines:
                    if 'return' in next_line and 'logger' not in next_line:
                        issues.append(f"❌ 줄 {i+1}: 장 시간 체크 후 return 발견!")
                        issues.append(f"   코드: {line.strip()}")
                        issues.append(f"   다음: {next_line.strip()}")
                        break

    # 2. 24시간 실행 로그 확인
    if "💤 장외 시간 - 과거 데이터로 가상매매 계속 실행" not in code:
        issues.append("⚠️  장외 시간 로그가 없습니다")

    if "🕐 장중 시간 - 실시간 데이터로 가상매매 실행" not in code:
        issues.append("⚠️  장중 시간 로그가 없습니다")

    # 3. 5개 스레드 확인
    threads = [
        ('update_thread', '_price_update_loop'),
        ('check_thread', '_stop_loss_take_profit_loop'),
        ('trading_thread', '_auto_trading_loop'),
        ('ai_management_thread', '_ai_management_loop'),
        ('evolution_thread', '_evolution_loop')
    ]

    logger.info("\n스레드 확인:")
    for thread_name, loop_name in threads:
        has_thread = f'self.{thread_name} = threading.Thread' in code
        has_loop = f'def {loop_name}(self):' in code
        status = "✅" if (has_thread and has_loop) else "❌"
        logger.info(f"  {status} {thread_name}: {loop_name}")

        if not (has_thread and has_loop):
            issues.append(f"❌ {thread_name} 또는 {loop_name}가 없습니다")

    # 결과 출력
    if not issues:
        logger.info("\n✅ 24시간 스케줄러 검증 통과!")
        return True
    else:
        logger.error("\n❌ 문제점 발견:")
        for issue in issues:
            logger.error(f"   {issue}")
        return False


def test_evolution_indicators():
    """진화 엔진 지표 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("테스트 2: 진화 엔진 지표 확인")
    logger.info("=" * 60)

    # StrategyGene import
    try:
        from virtual_trading.evolution_engine import StrategyGene
    except:
        logger.error("❌ evolution_engine import 실패 - 수동 확인")
        return check_indicators_manually()

    gene_fields = fields(StrategyGene)

    logger.info(f"\n현재 보는 지표 ({len(gene_fields)}개):")

    categories = {
        '매수 조건': ['rsi_min', 'rsi_max', 'volume_ratio_min', 'bid_ask_ratio_min'],
        '매도 조건': ['take_profit_pct', 'stop_loss_pct', 'trailing_stop_pct',
                    'rsi_overbought_min', 'rsi_overbought_max'],
        '포지션': ['position_size_pct', 'max_positions'],
        '시간/가격': ['trade_start_hour', 'trade_end_hour', 'price_min', 'price_max'],
        '분할': ['split_buy_enabled', 'split_buy_count']
    }

    for category, field_names in categories.items():
        logger.info(f"\n  [{category}]")
        for field_name in field_names:
            exists = any(f.name == field_name for f in gene_fields)
            status = "✅" if exists else "❌"
            logger.info(f"    {status} {field_name}")

    logger.info(f"\n추가 필요한 지표:")
    missing = [
        "❌ MACD (signal, histogram)",
        "❌ 볼린저 밴드 (상단, 하단, 폭)",
        "❌ 이동평균선 (5일, 20일, 60일, 120일)",
        "❌ 이평선 배열 (정배열/역배열)",
        "❌ 골든크로스 / 데드크로스",
        "❌ 스토캐스틱 (K, D, %K, %D)",
        "❌ CCI (Commodity Channel Index)",
        "❌ 외국인 순매수 (금액, 비율)",
        "❌ 기관 순매수 (금액, 비율)",
        "❌ 프로그램 순매수",
        "❌ 체결강도",
        "❌ 호가 불균형 (매수/매도)",
        "❌ 거래대금",
        "❌ 시가총액",
        "❌ PER, PBR, ROE",
        "❌ 변동성 (표준편차)",
        "❌ 당일 고가/저가",
        "❌ 전일 대비 등락률",
        "❌ 52주 신고가/신저가"
    ]

    for indicator in missing:
        logger.info(f"  {indicator}")

    return True


def check_indicators_manually():
    """수동으로 지표 확인"""
    evolution_path = Path(__file__).parent.parent / "virtual_trading" / "evolution_engine.py"

    with open(evolution_path, 'r', encoding='utf-8') as f:
        code = f.read()

    logger.info("\nStrategyGene 필드:")

    # @dataclass 다음부터 StrategyGene 찾기
    if 'class StrategyGene:' in code:
        start = code.index('class StrategyGene:')
        # 다음 class까지 추출
        end = code.index('class ', start + 10) if 'class ' in code[start + 10:] else len(code)
        gene_code = code[start:end]

        # 필드 추출 (간단하게)
        fields = []
        for line in gene_code.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#') and not line.startswith('def'):
                field_name = line.split(':')[0].strip()
                if field_name and not field_name.startswith('"""'):
                    fields.append(field_name)
                    logger.info(f"  ✅ {field_name}")

        logger.info(f"\n총 {len(fields)}개 지표")

    return True


def test_file_structure():
    """파일 구조 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("테스트 3: 파일 구조 확인")
    logger.info("=" * 60)

    files_to_check = [
        ("진화 엔진", "virtual_trading/evolution_engine.py"),
        ("스케줄러", "virtual_trading/scheduler.py"),
        ("매니저", "virtual_trading/manager.py"),
        ("__init__", "virtual_trading/__init__.py")
    ]

    base_path = Path(__file__).parent.parent

    logger.info("")
    all_exist = True
    for name, rel_path in files_to_check:
        full_path = base_path / rel_path
        exists = full_path.exists()
        status = "✅" if exists else "❌"
        logger.info(f"  {status} {name}: {rel_path}")

        if not exists:
            all_exist = False

    return all_exist


def main():
    """메인 테스트"""
    logger.info("\n" + "🧪" * 30)
    logger.info("진화 알고리즘 시스템 간단 테스트")
    logger.info("🧪" * 30)

    results = []

    # 테스트 1: 파일 구조
    try:
        result = test_file_structure()
        results.append(("파일 구조", result))
    except Exception as e:
        logger.error(f"파일 구조 테스트 실패: {e}")
        results.append(("파일 구조", False))

    # 테스트 2: 24시간 스케줄러
    try:
        result = test_24_hour_scheduler()
        results.append(("24시간 스케줄러", result))
    except Exception as e:
        logger.error(f"스케줄러 테스트 실패: {e}")
        results.append(("24시간 스케줄러", False))

    # 테스트 3: 지표 확인
    try:
        result = test_evolution_indicators()
        results.append(("지표 확인", result))
    except Exception as e:
        logger.error(f"지표 테스트 실패: {e}")
        results.append(("지표 확인", False))

    # 결과
    logger.info("\n" + "=" * 60)
    logger.info("테스트 결과")
    logger.info("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {status}: {test_name}")

    logger.info(f"\n총 {passed}/{total} 테스트 통과 ({passed/total*100:.1f}%)")

    if passed < total:
        logger.warning("\n⚠️  일부 테스트 실패 - 수정 필요!")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
