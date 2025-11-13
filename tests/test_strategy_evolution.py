"""
전략 진화 시스템 테스트

전략 진화가 제대로 작동하는지 확인합니다.
"""
import sys
import os
import sqlite3
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger_new import get_logger

logger = get_logger()

DB_PATH = "data/strategy_evolution.db"


def test_evolution_db_exists():
    """전략 진화 데이터베이스 존재 확인"""
    print("=" * 80)
    print("1️⃣  전략 진화 데이터베이스 확인")
    print("=" * 80)

    if not os.path.exists(DB_PATH):
        print(f"❌ 실패: 데이터베이스 파일이 없습니다: {DB_PATH}")
        print(f"   해결 방법: python init_evolution_db.py 실행")
        return False

    print(f"✅ 성공: 데이터베이스 존재 - {DB_PATH}")

    # 파일 크기 확인
    file_size = os.path.getsize(DB_PATH)
    print(f"   파일 크기: {file_size:,} bytes")

    return True


def test_evolution_tables():
    """전략 진화 테이블 구조 확인"""
    print("\n" + "=" * 80)
    print("2️⃣  전략 진화 테이블 구조 확인")
    print("=" * 80)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print(f"✅ 테이블 수: {len(tables)}개")

        expected_tables = ['evolved_strategies', 'generation_stats', 'strategy_genes']
        for table_name in expected_tables:
            if any(table_name in t[0] for t in tables):
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"   ✓ {table_name}: {count}개 레코드")
            else:
                print(f"   ⚠️  {table_name}: 테이블 없음")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        return False


def test_evolution_data():
    """전략 진화 데이터 확인"""
    print("\n" + "=" * 80)
    print("3️⃣  전략 진화 데이터 확인")
    print("=" * 80)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 최신 세대 확인
        cursor.execute("""
            SELECT generation, best_fitness, avg_fitness, worst_fitness, created_at
            FROM generation_stats
            ORDER BY generation DESC
            LIMIT 1
        """)
        latest = cursor.fetchone()

        if not latest:
            print("⚠️  경고: 아직 진화가 시작되지 않았습니다")
            print("   해결 방법: python run_strategy_optimizer.py --auto-deploy 실행")
            conn.close()
            return True

        print(f"✅ 최신 세대: {latest['generation']}세대")
        print(f"   최고 적합도: {latest['best_fitness']:.2f}")
        print(f"   평균 적합도: {latest['avg_fitness']:.2f}")
        print(f"   최악 적합도: {latest['worst_fitness']:.2f}")
        print(f"   업데이트: {latest['created_at']}")

        # 전체 진화된 전략 수
        cursor.execute("SELECT COUNT(*) as count FROM evolved_strategies")
        total_strategies = cursor.fetchone()['count']
        print(f"\n   총 진화된 전략: {total_strategies}개")

        # 최고 성과 전략
        cursor.execute("""
            SELECT id, generation, fitness_score, created_at
            FROM evolved_strategies
            ORDER BY fitness_score DESC
            LIMIT 3
        """)
        top_strategies = cursor.fetchall()

        print(f"\n   🏆 최고 성과 전략 TOP 3:")
        for i, strat in enumerate(top_strategies, 1):
            print(f"      {i}. ID={strat['id']} | 세대={strat['generation']} | 적합도={strat['fitness_score']:.2f}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        return False


def test_evolution_progress():
    """전략 진화 진행 상황 확인"""
    print("\n" + "=" * 80)
    print("4️⃣  전략 진화 진행 상황")
    print("=" * 80)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 세대별 통계
        cursor.execute("""
            SELECT
                COUNT(*) as total_generations,
                MIN(generation) as first_gen,
                MAX(generation) as latest_gen,
                AVG(best_fitness) as avg_best_fitness
            FROM generation_stats
        """)
        stats = cursor.fetchone()

        if stats['total_generations'] == 0:
            print("⚠️  진화가 아직 시작되지 않았습니다")
            conn.close()
            return True

        print(f"✅ 총 세대 수: {stats['total_generations']}세대")
        print(f"   첫 세대: {stats['first_gen']}세대")
        print(f"   최신 세대: {stats['latest_gen']}세대")
        print(f"   평균 최고 적합도: {stats['avg_best_fitness']:.2f}")

        # 최근 5세대 추이
        cursor.execute("""
            SELECT generation, best_fitness, avg_fitness, created_at
            FROM generation_stats
            ORDER BY generation DESC
            LIMIT 5
        """)
        recent = cursor.fetchall()

        print(f"\n   📈 최근 5세대 추이:")
        for gen in recent:
            print(f"      {gen['generation']}세대: 최고={gen['best_fitness']:.2f}, 평균={gen['avg_fitness']:.2f} ({gen['created_at']})")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        return False


def main():
    """전략 진화 테스트 실행"""
    print("\n🧬 전략 진화 시스템 테스트 시작\n")

    results = []

    # 테스트 실행
    results.append(("데이터베이스 존재 확인", test_evolution_db_exists()))

    if results[0][1]:  # DB가 존재하면 나머지 테스트 진행
        results.append(("테이블 구조 확인", test_evolution_tables()))
        results.append(("진화 데이터 확인", test_evolution_data()))
        results.append(("진행 상황 확인", test_evolution_progress()))

    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{status}: {test_name}")

    print(f"\n총 {total}개 테스트 중 {passed}개 통과")

    if passed == total:
        print("\n🎉 모든 테스트 통과! 전략 진화 시스템이 정상 작동 중입니다.")
        return 0
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패. 위의 오류를 확인하세요.")
        return 1


if __name__ == "__main__":
    exit_code = main()

    print("\n" + "=" * 80)
    input("Press Enter to exit...")

    sys.exit(exit_code)
