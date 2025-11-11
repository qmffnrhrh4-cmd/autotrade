#!/usr/bin/env python3
"""
전략 진화 데이터베이스 초기화 스크립트

용도: data/strategy_evolution.db가 없을 때 자동으로 생성
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = "data/strategy_evolution.db"


def init_evolution_database():
    """진화 데이터베이스 초기화"""
    # data 디렉토리 생성
    data_dir = Path(DB_PATH).parent
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"📊 진화 데이터베이스 초기화 중: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 진화된 전략 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evolved_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generation INTEGER NOT NULL,
            genes TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. 적합도 결과 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fitness_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER NOT NULL,
            generation INTEGER NOT NULL,
            total_return_pct REAL,
            sharpe_ratio REAL,
            win_rate REAL,
            max_drawdown_pct REAL,
            profit_factor REAL,
            total_trades INTEGER,
            fitness_score REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (strategy_id) REFERENCES evolved_strategies(id)
        )
    """)

    # 3. 세대 통계 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generation_stats (
            generation INTEGER PRIMARY KEY,
            best_fitness REAL NOT NULL,
            avg_fitness REAL NOT NULL,
            worst_fitness REAL NOT NULL,
            best_strategy_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    print(f"✅ 진화 데이터베이스 초기화 완료!")
    print(f"   - evolved_strategies 테이블 생성")
    print(f"   - fitness_results 테이블 생성")
    print(f"   - generation_stats 테이블 생성")
    print()
    print("💡 다음 단계:")
    print("   전략 최적화 엔진 실행:")
    print("   python run_strategy_optimizer.py --auto-deploy")


if __name__ == "__main__":
    init_evolution_database()
