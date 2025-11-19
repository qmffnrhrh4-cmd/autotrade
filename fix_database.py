#!/usr/bin/env python3
"""
데이터베이스 긴급 수정 스크립트
is_virtual 컬럼 추가
"""
import sqlite3
from pathlib import Path

def fix_database():
    """데이터베이스에 is_virtual 컬럼 추가"""
    db_path = Path("data/autotrade.db")

    if not db_path.exists():
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return False

    print(f"📂 데이터베이스: {db_path}")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 현재 테이블 구조 확인
        cursor.execute("PRAGMA table_info(trades)")
        columns = [row[1] for row in cursor.fetchall()]

        print(f"📋 현재 컬럼: {', '.join(columns)}")

        if 'is_virtual' in columns:
            print("✅ is_virtual 컬럼이 이미 존재합니다")
            return True

        print("🔧 is_virtual 컬럼 추가 중...")

        # 컬럼 추가
        cursor.execute("ALTER TABLE trades ADD COLUMN is_virtual INTEGER DEFAULT 0 NOT NULL")

        # 인덱스 추가
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_is_virtual ON trades(is_virtual)")

        conn.commit()

        # 확인
        cursor.execute("PRAGMA table_info(trades)")
        columns_after = [row[1] for row in cursor.fetchall()]

        if 'is_virtual' in columns_after:
            print("✅ is_virtual 컬럼 추가 완료")
            print(f"📋 업데이트된 컬럼: {', '.join(columns_after)}")

            # 인덱스 확인
            cursor.execute("PRAGMA index_list(trades)")
            indexes = cursor.fetchall()
            print(f"📑 인덱스: {len(indexes)}개")
            for idx in indexes:
                print(f"   - {idx[1]}")

            return True
        else:
            print("❌ 컬럼 추가 실패")
            return False

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("="*80)
    print("데이터베이스 긴급 수정")
    print("="*80)
    print()

    success = fix_database()

    print()
    print("="*80)
    if success:
        print("✅ 수정 완료!")
    else:
        print("❌ 수정 실패")
    print("="*80)

    input("\nPress Enter to exit...")
