"""
전체 트레이딩 시스템 통합 테스트

모든 시스템을 순차적으로 테스트합니다.
"""
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 다른 테스트 임포트 (tests 디렉토리에서 직접 임포트)
import test_strategy_evolution
import test_virtual_trading
import test_evolution_to_virtual


def main():
    """통합 테스트 실행"""
    print("\n" + "="*80)
    print("[전체 트레이딩 시스템 통합 테스트]")
    print("="*80)
    print("\n[1] 전략 진화 시스템")
    print("[2] 가상매매 시스템")
    print("[3] 전략 진화 -> 가상매매 연동")
    print("\n" + "="*80 + "\n")

    results = []

    # 1. 전략 진화 테스트
    print("\n[1/3] 전략 진화 시스템 테스트 중...")
    print("="*80)
    try:
        exit_code = test_strategy_evolution.main()
        results.append(("전략 진화 시스템", exit_code == 0))
    except Exception as e:
        print(f"[X] 전략 진화 테스트 실패: {e}")
        results.append(("전략 진화 시스템", False))

    # 2. 가상매매 테스트
    print("\n\n[2/3] 가상매매 시스템 테스트 중...")
    print("="*80)
    try:
        exit_code = test_virtual_trading.main()
        results.append(("가상매매 시스템", exit_code == 0))
    except Exception as e:
        print(f"[X] 가상매매 테스트 실패: {e}")
        results.append(("가상매매 시스템", False))

    # 3. 연동 테스트
    print("\n\n[3/3] 전략 진화 -> 가상매매 연동 테스트 중...")
    print("="*80)
    try:
        exit_code = test_evolution_to_virtual.main()
        results.append(("연동 시스템", exit_code == 0))
    except Exception as e:
        print(f"[X] 연동 테스트 실패: {e}")
        results.append(("연동 시스템", False))

    # 최종 결과
    print("\n\n" + "="*80)
    print("[전체 테스트 결과]")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[OK] 통과" if result else "[X] 실패"
        print(f"{status}: {test_name}")

    print(f"\n총 {total}개 시스템 중 {passed}개 통과")

    if passed == total:
        print("\n[SUCCESS] 모든 시스템이 정상 작동 중입니다!")
        print("\n시스템 상태:")
        print("   [OK] 전략 진화: 정상")
        print("   [OK] 가상매매: 정상")
        print("   [OK] 연동: 정상")
        return 0
    else:
        print(f"\n[!] {total - passed}개 시스템에 문제가 있습니다.")
        print("\n해결 방법:")
        print("   1. python init_virtual_trading.py")
        print("   2. python init_evolution_db.py")
        print("   3. python run_strategy_optimizer.py --auto-deploy")
        print("   4. 대시보드에서 상태 확인")
        return 1


if __name__ == "__main__":
    exit_code = main()

    print("\n" + "="*80)
    input("Press Enter to exit...")

    sys.exit(exit_code)
