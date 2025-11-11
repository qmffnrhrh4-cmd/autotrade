#!/bin/bash
# AutoTrade 시작 스크립트 (Linux/Mac)
# 전략 최적화 엔진 + 메인 애플리케이션 동시 실행

echo "================================================================================"
echo "🚀 AutoTrade Pro - Starting"
echo "================================================================================"
echo ""

# 1. 진화 데이터베이스 초기화 (없는 경우)
if [ ! -f "data/strategy_evolution.db" ]; then
    echo "📊 진화 데이터베이스 초기화 중..."
    python3 init_evolution_db.py
    echo ""
fi

# 2. 전략 최적화 엔진 시작 (백그라운드)
echo "================================================================================"
echo "Step 1: Starting Strategy Optimizer (Background)"
echo "================================================================================"
echo ""

# 기존 optimizer 프로세스 종료
pkill -f "run_strategy_optimizer.py" 2>/dev/null

# 백그라운드로 실행
nohup python3 run_strategy_optimizer.py --auto-deploy > logs/strategy_optimizer.log 2>&1 &
OPTIMIZER_PID=$!

echo "✅ Strategy optimizer started (PID: $OPTIMIZER_PID)"
echo "   Log file: logs/strategy_optimizer.log"
echo ""
sleep 2

# 3. 메인 애플리케이션 시작
echo "================================================================================"
echo "Step 2: Starting Main Application"
echo "================================================================================"
echo ""

python3 main.py

# 4. 종료 시 백그라운드 프로세스도 종료
echo ""
echo "================================================================================"
echo "Shutting down..."
echo "================================================================================"

# Optimizer 프로세스 종료
if ps -p $OPTIMIZER_PID > /dev/null 2>&1; then
    echo "Stopping strategy optimizer (PID: $OPTIMIZER_PID)..."
    kill $OPTIMIZER_PID 2>/dev/null
fi

echo "✅ AutoTrade stopped"
echo ""
