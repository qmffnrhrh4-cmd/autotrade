# 지속적 전략 최적화 시스템 (Continuous Strategy Optimization System)

## 개요

1분도 쉬지 않고 계속 백테스팅과 가상매매를 돌려서 가장 좋은 전략과 조건을 탐색하고 자기진화하는 자동화 시스템입니다.

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                   전략 최적화 엔진                           │
│  (Strategy Optimization Engine)                             │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼────────┐
│  백테스팅      │   │  가상매매       │
│  루프          │   │  실시간 평가    │
│  (Backtest)    │   │  (Paper Trade)  │
└───────┬────────┘   └────────┬────────┘
        │                     │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │   전략 평가 &       │
        │   순위 시스템       │
        │   (Evaluation)      │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │   유전 알고리즘     │
        │   (GA Evolution)    │
        │   - 변이            │
        │   - 교차            │
        │   - 선택            │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │   최우수 전략       │
        │   자동 적용         │
        │   (Auto Deploy)     │
        └─────────────────────┘
```

## 핵심 컴포넌트

### 1. 데이터 수집 엔진 (Data Collection Engine)
```python
# 지속적으로 다양한 데이터 수집
- 1분봉, 5분봉, 15분봉, 30분봉, 60분봉, 일봉
- RSI, MACD, Bollinger Bands, Stochastic
- 체결강도, 호가창 (매수/매도 호가 비율)
- 외국인/기관 순매수
- 섹터 모멘텀
- 시장 지수 (KOSPI, KOSDAQ)
```

### 2. 백테스팅 루프 (24/7 Backtesting Loop)
```python
while True:
    # 1. 새로운 전략 생성 (변이/교차)
    new_strategies = generate_strategy_variants()

    # 2. 병렬 백테스팅 (12개 전략 동시)
    results = parallel_backtest(
        strategies=new_strategies,
        stock_universe=['005930', '000660', ...],  # 코스피 200
        period='3M',  # 최근 3개월
        intervals=[1, 5, 15, 30, 60]  # 다양한 시간프레임
    )

    # 3. 성과 평가 및 순위
    ranked_strategies = rank_strategies(results)

    # 4. 상위 20% 전략만 살아남음 (자연선택)
    survivors = select_top_strategies(ranked_strategies, top_percent=0.2)

    # 5. 생존 전략으로 새로운 세대 생성
    next_generation = evolve_strategies(survivors)

    # 6. 최우수 전략을 실시간 매매에 적용
    deploy_best_strategy(ranked_strategies[0])

    # 7. 10분 대기 후 다시 시작
    time.sleep(600)
```

### 3. 가상매매 실시간 평가 (Live Paper Trading Evaluation)
```python
while True:
    # 1. 상위 5개 전략을 가상매매로 실행
    for strategy in top_5_strategies:
        execute_paper_trade(strategy)

    # 2. 실시간 성과 모니터링
    performance = monitor_live_performance()

    # 3. 10분마다 성과 업데이트
    update_strategy_scores(performance)

    # 4. 가상매매 성과가 백테스팅보다 30% 이상 낮으면 전략 제거
    remove_underperforming_strategies(threshold=-0.3)

    time.sleep(600)
```

### 4. 유전 알고리즘 진화 (Genetic Algorithm Evolution)

#### 전략 유전자 (Strategy Genome)
```python
strategy_genome = {
    # 매수 조건
    'buy_rsi_threshold': [20, 40],          # 변이 범위
    'buy_macd_signal': ['crossover', 'above'],
    'buy_volume_ratio': [1.2, 3.0],
    'buy_bid_ask_ratio': [1.1, 2.0],

    # 매도 조건
    'sell_rsi_threshold': [60, 80],
    'sell_take_profit': [0.05, 0.20],       # 5% ~ 20%
    'sell_stop_loss': [-0.10, -0.03],       # -10% ~ -3%
    'sell_trailing_stop': [0.02, 0.10],

    # 포지션 크기
    'position_size_pct': [0.05, 0.20],      # 계좌의 5% ~ 20%

    # 시간 필터
    'trade_time_start': ['09:00', '10:00'],
    'trade_time_end': ['14:00', '15:20'],

    # 종목 필터
    'min_price': [5000, 50000],
    'max_price': [100000, 500000],
    'min_volume': [100000, 1000000],
}
```

#### 진화 연산자
```python
def mutate(strategy, mutation_rate=0.1):
    """변이: 유전자를 무작위로 변경"""
    for gene, range_values in strategy.items():
        if random.random() < mutation_rate:
            if isinstance(range_values, list) and len(range_values) == 2:
                # 범위 내에서 무작위 값 선택
                strategy[gene] = random.uniform(range_values[0], range_values[1])
    return strategy

def crossover(strategy1, strategy2):
    """교차: 두 전략의 유전자를 섞음"""
    child = {}
    for gene in strategy1.keys():
        # 50% 확률로 부모1 또는 부모2의 유전자 선택
        child[gene] = strategy1[gene] if random.random() < 0.5 else strategy2[gene]
    return child

def select_parents(population, fitness_scores):
    """선택: 성과가 좋은 전략을 부모로 선택 (토너먼트 선택)"""
    tournament_size = 3
    tournament = random.sample(list(zip(population, fitness_scores)), tournament_size)
    tournament.sort(key=lambda x: x[1], reverse=True)
    return tournament[0][0], tournament[1][0]
```

### 5. 평가 지표 (Fitness Function)
```python
def calculate_fitness(backtest_result):
    """
    다중 목표 최적화 (Multi-Objective Optimization)
    """
    # 가중치
    weights = {
        'total_return': 0.30,      # 총 수익률 (30%)
        'sharpe_ratio': 0.25,      # 샤프 비율 (25%)
        'win_rate': 0.15,          # 승률 (15%)
        'max_drawdown': 0.15,      # 최대 낙폭 (15%) - 역수
        'profit_factor': 0.10,     # 손익비 (10%)
        'avg_holding_days': 0.05,  # 평균 보유일 (5%) - 짧을수록 좋음
    }

    fitness = (
        weights['total_return'] * normalize(backtest_result.total_return_pct, 0, 100) +
        weights['sharpe_ratio'] * normalize(backtest_result.sharpe_ratio, 0, 3) +
        weights['win_rate'] * normalize(backtest_result.win_rate, 0, 100) +
        weights['max_drawdown'] * (1 - normalize(abs(backtest_result.max_drawdown_pct), 0, 30)) +
        weights['profit_factor'] * normalize(backtest_result.profit_factor, 0, 3) +
        weights['avg_holding_days'] * (1 - normalize(backtest_result.avg_holding_days, 0, 30))
    )

    return fitness * 100  # 0-100 점수

def normalize(value, min_val, max_val):
    """값을 0-1 범위로 정규화"""
    return max(0, min(1, (value - min_val) / (max_val - min_val)))
```

### 6. 대시보드 실시간 업데이트
```python
# 대시보드에 다음 정보를 실시간 표시:

1. 현재 실행 중인 전략 세대 (Generation #)
2. 각 세대의 최고 Fitness Score
3. 현재 최우수 전략의 상세 조건
4. 진화 그래프 (세대별 성과 향상 추이)
5. 실시간 가상매매 성과
6. 백테스팅 진행 상황 (진행률, 예상 완료 시간)
```

## 구현 계획

### Phase 1: 백테스팅 자동화 (1주)
- [ ] 병렬 백테스팅 엔진 구축
- [ ] 12개 전략을 동시에 테스트
- [ ] 결과 DB에 저장 및 순위화

### Phase 2: 전략 진화 시스템 (1주)
- [ ] 전략 유전자 정의
- [ ] 변이/교차/선택 연산자 구현
- [ ] 세대별 진화 로직

### Phase 3: 가상매매 연동 (1주)
- [ ] 상위 전략을 가상매매로 자동 실행
- [ ] 실시간 성과 모니터링
- [ ] 성과 저하 시 자동 전략 교체

### Phase 4: 대시보드 실시간 모니터링 (1주)
- [ ] 진화 현황 실시간 표시
- [ ] 세대별 성과 그래프
- [ ] 전략 상세 조건 표시

### Phase 5: 자동 배포 시스템 (1주)
- [ ] 최우수 전략 자동 실매매 적용
- [ ] 안전 장치 (최소 백테스팅 기간, 최소 승률 등)
- [ ] 롤백 기능

## 예상 효과

1. **24/7 자동 최적화**: 시장이 변해도 자동으로 적응
2. **과최적화 방지**: 가상매매로 실전 검증
3. **리스크 관리**: 성과 저하 시 자동 전략 교체
4. **데이터 기반**: 감정 없는 객관적 전략 선택
5. **지속적 개선**: 매 세대마다 성과 향상

## 필요한 리소스

- **컴퓨팅**: 백테스팅을 위한 멀티코어 CPU (최소 8코어)
- **메모리**: 16GB 이상 (대량의 차트 데이터 처리)
- **스토리지**: SSD 100GB 이상 (과거 데이터 저장)
- **API**: 한국투자증권 API (분당 요청 제한 고려)

## 시작 방법

```bash
# 1. 전략 최적화 엔진 시작
python -m ai.strategy_optimizer --mode continuous

# 2. 대시보드에서 모니터링
# http://localhost:5000/dashboard

# 3. 실시간 로그 확인
tail -f logs/strategy_evolution.log
```

## 주의사항

⚠️ **과최적화 위험**: 백테스팅 성과가 좋아도 실전에서는 다를 수 있음
⚠️ **API 제한**: 한투 API는 분당 요청 제한이 있으므로 주의
⚠️ **시장 변화**: 시장 레짐이 급변하면 기존 전략이 무용지물이 될 수 있음
⚠️ **자동 매매**: 실매매 적용 전 충분한 가상매매 검증 필수
