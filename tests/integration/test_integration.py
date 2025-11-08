"""
test_integration.py
통합 테스트 - 새로운 시스템이 제대로 import되는지 확인
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

print("="*60)
print("AutoTrade Pro v2.0 통합 테스트")
print("="*60)

def test_imports():
    """모듈 import 테스트"""
    print("\n1. 기본 모듈 import 테스트...")

    try:
        # 새로운 설정 시스템
        from config.manager import get_config
        config = get_config()
        print("✓ YAML 설정 시스템")

        # 새로운 로거
        from utils.logger_new import get_logger
        logger = get_logger()
        print("✓ Loguru 로깅 시스템")

        # 데이터베이스
        from database import get_db_session
        session = get_db_session()
        session.close()
        print("✓ 데이터베이스 시스템")

        # 3단계 스캐닝
        from research.scanner_pipeline import ScannerPipeline
        print("✓ 3단계 스캐닝 파이프라인")

        # 스코어링 시스템
        from strategy.scoring_system import ScoringSystem
        print("✓ 10가지 스코어링 시스템")

        # 동적 리스크 관리
        from strategy.dynamic_risk_manager import DynamicRiskManager
        print("✓ 동적 리스크 관리")

        print("\n✅ 모든 모듈 import 성공!")
        return True

    except Exception as e:
        print(f"\n❌ Import 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """설정 테스트"""
    print("\n2. 설정 시스템 테스트...")

    try:
        from config.manager import get_config

        config = get_config()

        # Pydantic 모델과 dictionary 모두 지원하는 헬퍼 함수
        def safe_get(obj, key, default=None):
            try:
                if isinstance(obj, dict):
                    return obj.get(key, default)
                else:
                    return getattr(obj, key, default)
            except:
                return default

        def safe_nested_get(obj, parent_key, child_key, default=None):
            try:
                if isinstance(obj, dict):
                    parent = obj.get(parent_key, {})
                    return parent.get(child_key, default) if isinstance(parent, dict) else getattr(parent, child_key, default)
                else:
                    parent = getattr(obj, parent_key, None)
                    if parent is None:
                        return default
                    return getattr(parent, child_key, default)
            except:
                return default

        # 설정 확인
        print(f"  - 시스템 이름: {safe_get(config.system, 'name')}")
        print(f"  - 버전: {safe_get(config.system, 'version')}")
        print(f"  - 로그 레벨: {safe_get(config.logging, 'level')}")
        print(f"  - DB 타입: {safe_get(config.database, 'type')}")
        print(f"  - 최대 포지션: {safe_get(config.position, 'max_open_positions')}")

        # 스캐닝 설정
        scan_config = config.scanning
        print(f"  - Fast Scan 간격: {safe_nested_get(scan_config, 'fast_scan', 'interval')}초")
        print(f"  - Deep Scan 간격: {safe_nested_get(scan_config, 'deep_scan', 'interval')}초")
        print(f"  - AI Scan 간격: {safe_nested_get(scan_config, 'ai_scan', 'interval')}초")

        # 리스크 모드
        risk = config.risk_management
        print(f"  - Aggressive 최대 포지션: {safe_nested_get(risk, 'aggressive', 'max_open_positions')}")
        print(f"  - Normal 최대 포지션: {safe_nested_get(risk, 'normal', 'max_open_positions')}")

        print("\n✅ 설정 시스템 정상!")
        return True

    except Exception as e:
        print(f"\n❌ 설정 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database():
    """데이터베이스 테스트"""
    print("\n3. 데이터베이스 테스트...")

    try:
        from database import get_db_session, Trade, Position

        session = get_db_session()

        # 테이블 확인
        print("  - Trade 테이블: 존재")
        print("  - Position 테이블: 존재")

        # 간단한 쿼리
        trades_count = session.query(Trade).count()
        positions_count = session.query(Position).count()

        print(f"  - 거래 기록: {trades_count}개")
        print(f"  - 포지션: {positions_count}개")

        session.close()

        print("\n✅ 데이터베이스 정상!")
        return True

    except Exception as e:
        print(f"\n❌ 데이터베이스 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logging():
    """로깅 테스트"""
    print("\n4. 로깅 시스템 테스트...")

    try:
        from utils.logger_new import get_logger

        logger = get_logger()

        logger.info("테스트 INFO 로그")
        logger.warning("테스트 WARNING 로그")
        logger.success("테스트 SUCCESS 로그")

        print("✅ 로깅 시스템 정상!")
        return True

    except Exception as e:
        print(f"\n❌ 로깅 테스트 실패: {e}")
        return False


def main():
    """메인 테스트"""
    print("\n시작...\n")

    results = []

    # 1. Import 테스트
    results.append(("Import", test_imports()))

    # 2. 설정 테스트
    results.append(("설정", test_config()))

    # 3. 데이터베이스 테스트
    results.append(("데이터베이스", test_database()))

    # 4. 로깅 테스트
    results.append(("로깅", test_logging()))

    # 결과 출력
    print("\n" + "="*60)
    print("테스트 결과")
    print("="*60)

    for name, result in results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{name}: {status}")

    all_passed = all(r for _, r in results)

    print("="*60)

    if all_passed:
        print("\n🎉 모든 테스트 통과!")
        print("\n다음 명령어로 시스템을 실행하세요:")
        print("  python main.py")
        return 0
    else:
        print("\n⚠️  일부 테스트 실패")
        return 1


if __name__ == '__main__':
    sys.exit(main())
