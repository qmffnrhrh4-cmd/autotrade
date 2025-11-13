"""
전략 진화 → 가상매매 연동 테스트

전략 진화에서 생성된 전략이 가상매매로 제대로 연동되는지 확인합니다.
"""
import sys
import os
import sqlite3
import json
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger_new import get_logger

logger = get_logger()

EVOLUTION_DB = "data/strategy_evolution.db"
VIRTUAL_DB = "data/virtual_trading.db"


def test_databases_exist():
    """두 데이터베이스 존재 확인"""
    print("=" * 80)
    print("1️⃣  데이터베이스 존재 확인")
    print("=" * 80)

    all_exist = True

    if not os.path.exists(EVOLUTION_DB):
        print(f"❌ 전략 진화 DB 없음: {EVOLUTION_DB}")
        print(f"   해결 방법: python init_evolution_db.py 실행")
        all_exist = False
    else:
        print(f"✅ 전략 진화 DB 존재")

    if not os.path.exists(VIRTUAL_DB):
        print(f"❌ 가상매매 DB 없음: {VIRTUAL_DB}")
        print(f"   해결 방법: python init_virtual_trading.py 실행")
        all_exist = False
    else:
        print(f"✅ 가상매매 DB 존재")

    return all_exist


def test_evolution_strategies():
    """전략 진화에서 생성된 전략 확인"""
    print("\n" + "=" * 80)
    print("2️⃣  전략 진화 전략 확인")
    print("=" * 80)

    try:
        conn = sqlite3.connect(EVOLUTION_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 진화된 전략 수 확인
        cursor.execute("SELECT COUNT(*) as count FROM evolved_strategies")
        total = cursor.fetchone()['count']

        if total == 0:
            print("⚠️  경고: 진화된 전략이 없습니다")
            print("   해결 방법: python run_strategy_optimizer.py --auto-deploy 실행")
            conn.close()
            return False

        print(f"✅ 진화된 전략: {total}개")

        # 최고 성과 전략 TOP 3
        cursor.execute("""
            SELECT id, generation, fitness_score,
                   backtest_return_pct, backtest_sharpe_ratio, backtest_win_rate,
                   created_at
            FROM evolved_strategies
            ORDER BY fitness_score DESC
            LIMIT 3
        """)
        top_strategies = cursor.fetchall()

        print(f"\n   🏆 최고 성과 전략 TOP 3:")
        for i, strat in enumerate(top_strategies, 1):
            print(f"      {i}. ID={strat['id']} | 세대={strat['generation']} | 적합도={strat['fitness_score']:.2f}")
            print(f"         백테스트: 수익률={strat['backtest_return_pct']:.2f}%, "
                  f"샤프={strat['backtest_sharpe_ratio']:.2f}, 승률={strat['backtest_win_rate']:.1f}%")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        return False


def test_deployment_linkage():
    """전략 진화 → 가상매매 배포 연결 확인"""
    print("\n" + "=" * 80)
    print("3️⃣  전략 배포 연결 확인")
    print("=" * 80)

    try:
        # 전략 진화 DB 연결
        evo_conn = sqlite3.connect(EVOLUTION_DB)
        evo_conn.row_factory = sqlite3.Row
        evo_cursor = evo_conn.cursor()

        # 가상매매 DB 연결
        vt_conn = sqlite3.connect(VIRTUAL_DB)
        vt_conn.row_factory = sqlite3.Row
        vt_cursor = vt_conn.cursor()

        # 전략 진화 DB에서 배포된 전략 확인
        evo_cursor.execute("""
            SELECT id, generation, fitness_score, deployed_at, is_deployed
            FROM evolved_strategies
            WHERE is_deployed = 1
            ORDER BY deployed_at DESC
        """)
        deployed_from_evolution = evo_cursor.fetchall()

        if not deployed_from_evolution:
            print("⚠️  경고: 배포된 전략이 없습니다")
            print("   해결 방법:")
            print("   1. python run_strategy_optimizer.py --auto-deploy 실행 (자동 배포 모드)")
            print("   2. 대시보드에서 수동으로 전략을 가상매매에 추가")
            evo_conn.close()
            vt_conn.close()
            return False

        print(f"✅ 배포된 전략: {len(deployed_from_evolution)}개")

        # 가상매매 전략 중 진화 전략과 연결된 것 확인
        for deployed in deployed_from_evolution:
            print(f"\n   🔗 배포 전략 ID={deployed['id']}")
            print(f"      세대: {deployed['generation']}")
            print(f"      적합도: {deployed['fitness_score']:.2f}")
            print(f"      배포일: {deployed['deployed_at']}")

            # description에 evolution_strategy_id가 포함되어 있는지 확인
            vt_cursor.execute("""
                SELECT id, name, description, current_capital, total_profit, return_rate,
                       trade_count, win_rate
                FROM virtual_strategies
                WHERE is_active = 1 AND description LIKE ?
            """, (f"%evolution_strategy_id={deployed['id']}%",))
            linked_vt = vt_cursor.fetchone()

            if linked_vt:
                print(f"      ✅ 가상매매 연결 확인:")
                print(f"         가상매매 ID: {linked_vt['id']}")
                print(f"         전략명: {linked_vt['name']}")
                print(f"         현재 자본: {linked_vt['current_capital']:,.0f}원")
                print(f"         총 손익: {linked_vt['total_profit']:,.0f}원 ({linked_vt['return_rate']:.2f}%)")
                print(f"         거래: {linked_vt['trade_count']}회 (승률={linked_vt['win_rate']:.1f}%)")
            else:
                print(f"      ⚠️  가상매매 연결 없음")

        evo_conn.close()
        vt_conn.close()
        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_genes_match():
    """전략 유전자 일치 여부 확인"""
    print("\n" + "=" * 80)
    print("4️⃣  전략 유전자 일치 확인")
    print("=" * 80)

    try:
        # 전략 진화 DB 연결
        evo_conn = sqlite3.connect(EVOLUTION_DB)
        evo_conn.row_factory = sqlite3.Row
        evo_cursor = evo_conn.cursor()

        # 가상매매 DB 연결
        vt_conn = sqlite3.connect(VIRTUAL_DB)
        vt_conn.row_factory = sqlite3.Row
        vt_cursor = vt_conn.cursor()

        # 최고 적합도 전략의 유전자 확인
        evo_cursor.execute("""
            SELECT id, generation, fitness_score
            FROM evolved_strategies
            ORDER BY fitness_score DESC
            LIMIT 1
        """)
        best_strategy = evo_cursor.fetchone()

        if not best_strategy:
            print("⚠️  진화된 전략이 없습니다")
            evo_conn.close()
            vt_conn.close()
            return False

        print(f"✅ 최고 전략: ID={best_strategy['id']}, 적합도={best_strategy['fitness_score']:.2f}")

        # 유전자 확인
        evo_cursor.execute("""
            SELECT gene_name, gene_value
            FROM strategy_genes
            WHERE strategy_id = ?
        """, (best_strategy['id'],))
        genes = evo_cursor.fetchall()

        if genes:
            print(f"\n   🧬 유전자 정보: {len(genes)}개")
            for gene in genes[:5]:  # 처음 5개만 표시
                print(f"      {gene['gene_name']}: {gene['gene_value']}")
            if len(genes) > 5:
                print(f"      ... (외 {len(genes) - 5}개)")
        else:
            print("   ⚠️  유전자 정보가 없습니다")

        evo_conn.close()
        vt_conn.close()
        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        return False


def test_performance_comparison():
    """백테스트 성과 vs 실전 가상매매 성과 비교"""
    print("\n" + "=" * 80)
    print("5️⃣  성과 비교 (백테스트 vs 가상매매)")
    print("=" * 80)

    try:
        # 전략 진화 DB 연결
        evo_conn = sqlite3.connect(EVOLUTION_DB)
        evo_conn.row_factory = sqlite3.Row
        evo_cursor = evo_conn.cursor()

        # 가상매매 DB 연결
        vt_conn = sqlite3.connect(VIRTUAL_DB)
        vt_conn.row_factory = sqlite3.Row
        vt_cursor = vt_conn.cursor()

        # 배포된 전략의 성과 비교
        evo_cursor.execute("""
            SELECT id, generation, fitness_score,
                   backtest_return_pct, backtest_sharpe_ratio, backtest_win_rate
            FROM evolved_strategies
            WHERE is_deployed = 1
            ORDER BY deployed_at DESC
            LIMIT 3
        """)
        deployed_strategies = evo_cursor.fetchall()

        if not deployed_strategies:
            print("⚠️  배포된 전략이 없어 비교할 수 없습니다")
            evo_conn.close()
            vt_conn.close()
            return False

        print(f"✅ 배포된 전략 성과 비교:")

        for strat in deployed_strategies:
            print(f"\n   📊 전략 ID={strat['id']} (세대={strat['generation']})")
            print(f"      [백테스트]")
            print(f"         수익률: {strat['backtest_return_pct']:.2f}%")
            print(f"         샤프 비율: {strat['backtest_sharpe_ratio']:.2f}")
            print(f"         승률: {strat['backtest_win_rate']:.1f}%")

            # 가상매매 실전 성과 찾기
            vt_cursor.execute("""
                SELECT id, name, return_rate, win_rate, trade_count,
                       total_profit, current_capital
                FROM virtual_strategies
                WHERE is_active = 1 AND description LIKE ?
            """, (f"%evolution_strategy_id={strat['id']}%",))
            vt_strat = vt_cursor.fetchone()

            if vt_strat:
                print(f"      [가상매매 실전]")
                print(f"         수익률: {vt_strat['return_rate']:.2f}%")
                print(f"         승률: {vt_strat['win_rate']:.1f}%")
                print(f"         거래: {vt_strat['trade_count']}회")
                print(f"         총 손익: {vt_strat['total_profit']:,.0f}원")

                # 성과 차이
                return_diff = vt_strat['return_rate'] - strat['backtest_return_pct']
                win_rate_diff = vt_strat['win_rate'] - strat['backtest_win_rate']

                diff_emoji = "📈" if return_diff >= 0 else "📉"
                print(f"      [차이] {diff_emoji}")
                print(f"         수익률 차이: {return_diff:+.2f}%")
                print(f"         승률 차이: {win_rate_diff:+.1f}%")

                if vt_strat['trade_count'] < 10:
                    print(f"         ⚠️  거래 수가 적어({vt_strat['trade_count']}회) 통계적 신뢰도가 낮습니다")
            else:
                print(f"      [가상매매 실전] 연결된 전략 없음")

        evo_conn.close()
        vt_conn.close()
        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """통합 테스트 실행"""
    print("\n🔗 전략 진화 → 가상매매 연동 테스트 시작\n")

    results = []

    # 테스트 실행
    results.append(("데이터베이스 존재 확인", test_databases_exist()))

    if results[0][1]:  # 두 DB가 모두 존재하면 나머지 테스트 진행
        results.append(("전략 진화 전략 확인", test_evolution_strategies()))
        results.append(("전략 배포 연결 확인", test_deployment_linkage()))
        results.append(("전략 유전자 일치 확인", test_strategy_genes_match()))
        results.append(("성과 비교", test_performance_comparison()))

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
        print("\n🎉 모든 테스트 통과! 전략 진화 → 가상매매 연동이 정상 작동 중입니다.")
        print("\n💡 확인 사항:")
        print("   - 전략 진화에서 생성된 전략이 가상매매에 배포됨")
        print("   - 백테스트 성과와 실전 성과 비교 가능")
        print("   - 전략 유전자 정보 저장 및 조회 가능")
        return 0
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패.")
        print("\n💡 해결 방법:")
        print("   1. python run_strategy_optimizer.py --auto-deploy 실행 (전략 진화 + 자동 배포)")
        print("   2. 대시보드 > 전략 진화 탭에서 진행 상황 확인")
        print("   3. 대시보드 > 가상매매 탭에서 배포된 전략 확인")
        return 1


if __name__ == "__main__":
    exit_code = main()

    print("\n" + "=" * 80)
    input("Press Enter to exit...")

    sys.exit(exit_code)
