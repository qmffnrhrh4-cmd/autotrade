"""
가상매매 시스템 테스트

가상매매가 제대로 작동하는지 확인합니다.
"""
import sys
import os
import sqlite3
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger_new import get_logger

logger = get_logger()

DB_PATH = "data/virtual_trading.db"


def test_virtual_db_exists():
    """가상매매 데이터베이스 존재 확인"""
    print("=" * 80)
    print("1️⃣  가상매매 데이터베이스 확인")
    print("=" * 80)

    if not os.path.exists(DB_PATH):
        print(f"❌ 실패: 데이터베이스 파일이 없습니다: {DB_PATH}")
        print(f"   해결 방법: python init_virtual_trading.py 실행")
        return False

    print(f"✅ 성공: 데이터베이스 존재 - {DB_PATH}")

    # 파일 크기 확인
    file_size = os.path.getsize(DB_PATH)
    print(f"   파일 크기: {file_size:,} bytes")

    return True


def test_virtual_tables():
    """가상매매 테이블 구조 확인"""
    print("\n" + "=" * 80)
    print("2️⃣  가상매매 테이블 구조 확인")
    print("=" * 80)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print(f"✅ 테이블 수: {len(tables)}개")

        expected_tables = ['virtual_strategies', 'virtual_positions', 'virtual_trades']
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


def test_virtual_strategies():
    """가상매매 전략 확인"""
    print("\n" + "=" * 80)
    print("3️⃣  가상매매 전략 확인")
    print("=" * 80)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 활성 전략 확인
        cursor.execute("""
            SELECT id, name, initial_capital, current_capital, total_profit, return_rate,
                   trade_count, win_count, loss_count, win_rate, created_at
            FROM virtual_strategies
            WHERE is_active = 1
            ORDER BY created_at DESC
        """)
        strategies = cursor.fetchall()

        if not strategies:
            print("⚠️  경고: 활성 가상매매 전략이 없습니다")
            print("   해결 방법: 대시보드에서 전략을 생성하거나, 전략 진화를 통해 자동 배포")
            conn.close()
            return True

        print(f"✅ 활성 전략: {len(strategies)}개")

        for strat in strategies:
            print(f"\n   📊 전략: {strat['name']} (ID={strat['id']})")
            print(f"      초기 자본: {strat['initial_capital']:,.0f}원")
            print(f"      현재 자본: {strat['current_capital']:,.0f}원")
            print(f"      총 손익: {strat['total_profit']:,.0f}원 ({strat['return_rate']:.2f}%)")
            print(f"      거래: {strat['trade_count']}회 (승={strat['win_count']}, 패={strat['loss_count']}, 승률={strat['win_rate']:.1f}%)")
            print(f"      생성일: {strat['created_at']}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        return False


def test_virtual_positions():
    """가상매매 포지션 확인"""
    print("\n" + "=" * 80)
    print("4️⃣  가상매매 포지션 확인")
    print("=" * 80)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 활성 포지션 확인
        cursor.execute("""
            SELECT p.id, p.strategy_id, s.name as strategy_name,
                   p.stock_code, p.stock_name, p.quantity, p.avg_price,
                   p.current_price,
                   (p.current_price - p.avg_price) * p.quantity as unrealized_profit,
                   ((p.current_price - p.avg_price) / p.avg_price * 100) as unrealized_profit_pct,
                   p.buy_date
            FROM virtual_positions p
            JOIN virtual_strategies s ON p.strategy_id = s.id
            WHERE p.is_closed = 0
            ORDER BY p.buy_date DESC
        """)
        positions = cursor.fetchall()

        if not positions:
            print("ℹ️  현재 열린 포지션이 없습니다 (정상)")
            conn.close()
            return True

        print(f"✅ 열린 포지션: {len(positions)}개")

        for pos in positions:
            profit_emoji = "📈" if pos['unrealized_profit'] > 0 else "📉"
            print(f"\n   {profit_emoji} 포지션 ID={pos['id']}")
            print(f"      전략: {pos['strategy_name']}")
            print(f"      종목: {pos['stock_name']} ({pos['stock_code']})")
            print(f"      수량: {pos['quantity']}주")
            print(f"      평균가: {pos['avg_price']:,.0f}원")
            print(f"      현재가: {pos['current_price']:,.0f}원")
            print(f"      평가손익: {pos['unrealized_profit']:,.0f}원 ({pos['unrealized_profit_pct']:.2f}%)")
            print(f"      매수일: {pos['buy_date']}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        return False


def test_virtual_trades():
    """가상매매 거래 내역 확인"""
    print("\n" + "=" * 80)
    print("5️⃣  가상매매 거래 내역 확인")
    print("=" * 80)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 최근 거래 확인
        cursor.execute("""
            SELECT t.id, t.strategy_id, s.name as strategy_name,
                   t.stock_code, t.stock_name, t.side,
                   t.quantity, t.price, t.profit, t.profit_percent,
                   t.timestamp
            FROM virtual_trades t
            JOIN virtual_strategies s ON t.strategy_id = s.id
            ORDER BY t.timestamp DESC
            LIMIT 10
        """)
        trades = cursor.fetchall()

        if not trades:
            print("ℹ️  아직 거래 내역이 없습니다")
            conn.close()
            return True

        print(f"✅ 최근 거래: {min(len(trades), 10)}건 표시")

        for trade in trades:
            action_emoji = "💰" if trade['side'] == 'BUY' else "💸"
            profit_text = ""
            if trade['side'] == 'SELL' and trade['profit'] is not None:
                profit_emoji = "📈" if trade['profit'] > 0 else "📉"
                profit_text = f" | {profit_emoji} 손익: {trade['profit']:,.0f}원 ({trade['profit_percent']:.2f}%)"

            print(f"\n   {action_emoji} 거래 ID={trade['id']}")
            print(f"      전략: {trade['strategy_name']}")
            print(f"      종목: {trade['stock_name']} ({trade['stock_code']})")
            print(f"      수량: {trade['quantity']}주 × {trade['price']:,.0f}원{profit_text}")
            print(f"      시간: {trade['timestamp']}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        return False


def main():
    """가상매매 테스트 실행"""
    print("\n💰 가상매매 시스템 테스트 시작\n")

    results = []

    # 테스트 실행
    results.append(("데이터베이스 존재 확인", test_virtual_db_exists()))

    if results[0][1]:  # DB가 존재하면 나머지 테스트 진행
        results.append(("테이블 구조 확인", test_virtual_tables()))
        results.append(("전략 확인", test_virtual_strategies()))
        results.append(("포지션 확인", test_virtual_positions()))
        results.append(("거래 내역 확인", test_virtual_trades()))

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
        print("\n🎉 모든 테스트 통과! 가상매매 시스템이 정상 작동 중입니다.")
        return 0
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패. 위의 오류를 확인하세요.")
        return 1


if __name__ == "__main__":
    exit_code = main()

    print("\n" + "=" * 80)
    input("Press Enter to exit...")

    sys.exit(exit_code)
