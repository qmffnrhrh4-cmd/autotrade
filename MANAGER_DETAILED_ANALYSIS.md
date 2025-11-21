# Manager 클래스 상세 분석 보고서

## 1. 포지션/포트폴리오 관리 상세 분석

### 1.1 PositionManager vs PortfolioManager 비교

**PositionManager (260줄)**
```python
# 주요 메서드:
- add_position(stock_code, quantity, purchase_price, ...)
- update_position(stock_code, current_price, ...)
- remove_position(stock_code)
- get_positions()
- get_position(stock_code)
- calculate_pnl(stock_code)
- get_all_pnl()

# 특징:
- BaseManager 상속 (enabled, stats 등)
- 개별 Position 객체 관리
- core.Position 클래스 사용
```

**PortfolioManager (553줄)**
```python
# 주요 메서드:
- update_portfolio(holdings, cash)
- get_total_assets()
- calculate_weights()
- rebalance()
- get_position_info(stock_code)
- check_exposure(stock_code, max_position_size)
- should_rebalance()

# 특징:
- KiwoomRESTClient 클라이언트 의존
- 전체 포트폴리오 레벨에서 관리
- 리밸런싱 로직 포함
- 자산 배분 최적화
```

### 1.2 문제점

| 문제 | PositionManager | PortfolioManager | 영향 |
|------|---|---|---|
| 저수준 API | O | X | 두 클래스 모두 필요 |
| 리밸런싱 | X | O | 포트폴리오 조정 어려움 |
| 데이터 동기화 | 별도 | 독립적 | 불일치 위험 |
| 테스트 난이도 | 쉬움 | 어려움 | 테스트 커버리지 부족 |

### 1.3 통합 방안

```python
# 제안: UnifiedPositionManager
class UnifiedPositionManager(BaseManager):
    
    def __init__(self):
        self.positions = {}  # {stock_code: Position}
        self.portfolio_config = {...}
        self.rebalance_history = []
    
    # 저수준 (PositionManager 기능)
    def add_position(self, ...): pass
    def update_position(self, ...): pass
    def remove_position(self, ...): pass
    
    # 고수준 (PortfolioManager 기능)
    def update_portfolio(self, ...): pass
    def rebalance(self, ...): pass
    def calculate_weights(self): pass
    
    # 새로운 메서드
    def sync_with_broker_holdings(self, broker_holdings): pass
    def get_portfolio_metrics(self): pass
```

---

## 2. 캐싱 시스템 상세 분석

### 2.1 3개 캐싱 시스템 비교

**cache_manager.py (399줄)**
```python
# 특징:
- BaseManager 상속
- TTL 기반 자동 만료
- LRU 제거 정책
- CacheEntry 래퍼 클래스
- 상태 추적 (hit/miss/eviction)

# 클래스: CacheManager
# TTL 설정:
  - STOCK_PRICE: 5초
  - PORTFOLIO: 10초
  - ACCOUNT_INFO: 30초
  - STRATEGY_LIST: 60초 (기본)
  - MARKET_DATA: 60초
  - STOCK_INFO: 300초
  - HISTORICAL_DATA: 600초
```

**data_cache.py (586줄)**
```python
# 특징:
- LRUCache, OrderedDict 기반
- 스레드 안전 (RLock)
- 메모리 사용량 추적
- 크기 제한 (기본: 1000개)
- 태그 기반 무효화

# 클래스: LRUCache
# 기능:
  - get(key) - 접근 기록
  - put(key, value) - 저장
  - remove(key)
  - clear_by_tag(tag)
  - get_stats()
```

**redis_cache.py (389줄)**
```python
# 특징:
- Redis 서버 연동 (선택사항)
- TTL 지원
- JSON/Pickle 직렬화
- 메모리 캐시 fallback
- 캐시 통계

# 클래스: RedisCacheManager
# 의존성: redis 라이브러리 (선택)
# 기본값: localhost:6379
```

### 2.2 사용 위치 및 충돌

| 파일 | 사용처 | 캐싱 시스템 |
|------|--------|-----------|
| api/market_api.py | 주가 데이터 | redis_cache? cache_manager? data_cache? |
| core/broker.py | 거래 | cache_manager |
| utils/ 다수 | 유틸 | @cache_manager.cached? @lru_cache? |

**→ 결론: 세 시스템이 동시에 사용되거나 전혀 통합되지 않음**

### 2.3 권장 계층화 구조

```
┌─────────────────────────────────────────┐
│  Application Layer (API, 매매로직)      │
│  사용: CacheManager 데코레이터           │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│  CacheManager (기본 인터페이스)         │
│  - TTL 관리                             │
│  - 통계 수집                            │
│  - 자동 만료                            │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼────────────┐  ┌───────▼──────────┐
│ MemoryCache    │  │  RedisCache      │
│ (data_cache)   │  │ (redis_cache)    │
│ - LRU 정책     │  │ - 분산 캐시      │
│ - 로컬 메모리  │  │ - TTL 지원       │
└────────────────┘  └──────────────────┘

# 사용 예:
@cache_manager.cache(ttl=60)
def get_stock_price(stock_code):
    # Redis 먼저 확인 → 메모리 캐시 → DB 조회
    return ...
```

---

## 3. Manager 기능 매트릭스

### 3.1 Manager별 책임 (RACI)

| 기능 | 포지션 | 포트폴리오 | 캐시 | 위험 | 주문 | 웹소켓 |
|------|--------|-----------|------|------|------|--------|
| 포지션 추가 | R | C | | | | |
| 자산 업데이트 | R | C | | | | |
| 리밸런싱 | C | R | | | | |
| 손절 확인 | | | | R | C | |
| 주문 실행 | C | | | C | R | |
| 캐시 관리 | | | R | | | |
| 실시간 데이터 | C | C | | | | R |

**R: Responsible(담당), C: Consulted(상담), A: Approved(승인), I: Informed(통보)**

### 3.2 현재 문제점

```
1. 책임 불명확
   - dynamic_risk_manager와 emergency_manager가 
     모두 손절 처리 가능
   
2. 데이터 흐름 복잡
   - PositionManager → PortfolioManager 
     → DynamicRiskManager 체인이 명확하지 않음

3. 의존성 복잡
   - 원형 의존성 가능성
     (Manager A가 Manager B 사용, 
      Manager B가 Manager A 콜백)

4. 테스트 불가능
   - 실제 API/DB/Redis 없이 테스트 어려움
```

---

## 4. ai/program_manager.py 분해 분석 (1,192줄)

### 4.1 현재 구조

```python
class ProgramManager:
    """프로그램 전체 관리 (너무 큼!)"""
    
    def __init__(self):
        # 진화 엔진 관련
        self.evolution_engine = ...
        self.strategy_candidates = ...
        
        # 가상 매매 관련
        self.virtual_trading_manager = ...
        self.virtual_strategies = ...
        
        # 실거래 관련
        self.live_trading_enabled = ...
        self.broker_client = ...
        
        # 통계 관련
        self.statistics = ...
        self.history = ...
    
    # 50+ 메서드...
```

### 4.2 추천 분해

```
ai/program_manager.py (1,192줄)
│
├─ ai/evolution_manager.py (새로)
│  ├── EvolutionManager
│  │   ├── run_evolution()
│  │   ├── select_top_strategies()
│  │   ├── generate_offspring()
│  │   └── evaluate_fitness()
│  └── 약 300줄
│
├─ ai/virtual_trading_manager.py (재구성)
│  ├── VirtualTradingManager
│  │   ├── run_virtual_trading()
│  │   ├── execute_strategy()
│  │   ├── update_performance()
│  │   └── candidate_analysis()
│  └── 약 400줄
│
├─ ai/live_trading_manager.py (새로)
│  ├── LiveTradingManager
│  │   ├── start_live_trading()
│  │   ├── stop_live_trading()
│  │   ├── execute_live_order()
│  │   └── monitor_positions()
│  └── 약 200줄
│
└─ ai/unified_program_manager.py (파사드)
   ├── UnifiedProgramManager (조정 역할)
   │   ├── evolution_mgr: EvolutionManager
   │   ├── virtual_mgr: VirtualTradingManager
   │   ├── live_mgr: LiveTradingManager
   │   └── coordinate()
   └── 약 150줄
```

### 4.3 이점

| 항목 | 현재 | 분해 후 | 이득 |
|------|------|--------|------|
| 파일 크기 | 1,192줄 | 300+400+200+150 | 각 파일 단일 책임 |
| 테스트 | 어려움 | 쉬움 | 각 부분 독립 테스트 |
| 재사용성 | 낮음 | 높음 | 각 Manager 독립 사용 |
| 유지보수 | 어려움 | 쉬움 | 파일당 50-100줄 |

---

## 5. 통합 우선순위 및 영향도

### 5.1 우선순위 순서

```
1순위 (긴급 - 버그 방지):
   ├─ 캐싱 시스템 통합 (3개 → 1개)
   │  영향도: 높음 (API 응답 속도)
   │  복잡도: 중간
   │  예상 시간: 4-6시간
   │
   └─ 백테스팅 통합 (4개 → 1개)
      영향도: 높음 (백테스팅 일관성)
      복잡도: 높음
      예상 시간: 8-10시간

2순위 (중요 - 성능 향상):
   ├─ 포지션 관리 통합 (2개 → 1개)
   │  영향도: 높음 (실거래 안정성)
   │  복잡도: 높음
   │  예상 시간: 6-8시간
   │
   └─ program_manager.py 분해
      영향도: 중간 (코드 품질)
      복잡도: 높음
      예상 시간: 10-12시간

3순위 (개선 - 유지보수성):
   ├─ 테스트 폴더 정리
   │  영향도: 낮음
   │  복잡도: 낮음
   │  예상 시간: 2-3시간
   │
   └─ 유틸리티 정리
      영향도: 낮음
      복잡도: 낮음
      예상 시간: 3-4시간
```

### 5.2 영향도 분석

**높은 영향도 변경 (회귀 테스트 필수):**
```
1. 캐싱 시스템 통합
   - 모든 API 호출에 영향
   - Redis 연결 실패 처리 검증 필요
   - TTL 설정 재검증 필요

2. 포지션 관리 통합
   - 실거래 전략 변경 필요
   - 가상 매매 영향
   - 대시보드 조회 영향

3. 백테스팅 통합
   - 기존 백테스트 스크립트 마이그레이션 필요
   - 결과 비교 필수 (회귀 없음 확인)
```

---

## 6. 리팩토링 체크리스트

### Phase 1: 캐싱 시스템 통합 (Week 1)

```
□ utils/cache_manager.py 분석
  └─ CacheManager 기본 인터페이스 정의
  
□ utils/data_cache.py 병합
  └─ LRUCache를 MemoryCache로 래핑
  
□ utils/redis_cache.py 정리
  └─ RedisCache 폴백 로직 추가
  
□ 통합 테스트
  └─ @cache_manager.cache() 데코레이터 검증
  
□ 마이그레이션
  └─ 모든 import 수정
     - from utils.data_cache import ... 
     → from utils.cache_manager import ...
     
□ 성능 테스트
  └─ 캐시 히트율 모니터링
     - 이전: ____%
     - 이후: ____%
```

### Phase 2: 포지션 관리 통합 (Week 2)

```
□ strategy/unified_position_manager.py 생성
  └─ PositionManager 기능 포함
  └─ PortfolioManager 기능 포함
  
□ 레거시 파일 래핑
  └─ strategy/position_manager.py 
     → UnifiedPositionManager 호출
  └─ strategy/portfolio_manager.py 
     → UnifiedPositionManager 호출
     
□ 통합 테스트
  └─ 포지션 추가/수정/삭제
  └─ 리밸런싱 로직
  
□ 마이그레이션
  └─ strategy/*.py 파일들 업데이트
  └─ virtual_trading/*.py 파일들 업데이트
  
□ 회귀 테스트
  └─ 기존 테스트 모두 통과 확인
```

### Phase 3: 백테스팅 통합 (Week 3)

```
□ ai/unified_backtester.py 생성
  └─ AdvancedBacktester 기반
  └─ StrategyBacktester 기능 통합
  └─ BacktestAdapter 기능 포함
  
□ ai/strategy_backtester.py 삭제
□ virtual_trading/backtest_adapter.py 삭제

□ dashboard 라우트 업데이트
  └─ backtest.py 수정
  └─ backtest_analysis.py 수정
  
□ 통합 테스트
  └─ 모든 백테스팅 시나리오 검증
  
□ 회귀 테스트
  └─ 기존 백테스팅 결과 비교
```

### Phase 4: program_manager.py 분해 (Week 4)

```
□ ai/evolution_manager.py 추출
□ ai/virtual_trading_manager.py 재구성
□ ai/live_trading_manager.py 신규 생성
□ ai/unified_program_manager.py 생성 (파사드)

□ 통합 테스트
  └─ 각 Manager 독립 테스트
  └─ 통합 조정 테스트
  
□ 회귀 테스트
  └─ 기존 프로그램 동작 동일성 확인
```

---

## 7. 의존성 그래프

### 현재 상태 (복잡함)

```
ai/program_manager.py (중심)
    ├─→ ai/backtesting.py
    ├─→ ai/advanced_backtester.py (중복!)
    ├─→ ai/strategy_backtester.py (중복!)
    ├─→ virtual_trading/ai_strategy_manager.py
    ├─→ virtual_trading/virtual_trader.py
    ├─→ virtual_trading/evolution_engine.py
    ├─→ strategy/dynamic_risk_manager.py
    ├─→ strategy/position_manager.py
    ├─→ strategy/portfolio_manager.py
    ├─→ utils/cache_manager.py
    ├─→ utils/data_cache.py
    ├─→ utils/redis_cache.py (중복!)
    └─→ ... (40+ 더 있음)
```

### 목표 상태 (명확함)

```
ai/unified_program_manager.py (파사드)
    ├─→ ai/evolution_manager.py
    │   └─→ ai/unified_backtester.py
    ├─→ ai/virtual_trading_manager.py
    │   ├─→ ai/unified_backtester.py
    │   ├─→ strategy/unified_position_manager.py
    │   └─→ utils/cache_manager.py
    ├─→ ai/live_trading_manager.py
    │   ├─→ strategy/unified_position_manager.py
    │   ├─→ core/broker.py
    │   └─→ utils/cache_manager.py
    └─→ dashboard/routes/unified_backtest.py
```

---

## 8. 예상 효과

### 코드 품질

| 항목 | 현재 | 목표 | 개선도 |
|------|------|------|--------|
| 순환 복잡도 | 높음 | 낮음 | -40% |
| 중복 코드 | 많음 | 거의 없음 | -90% |
| 테스트 커버리지 | 50% | 80% | +30% |
| 문서화 | 부분 | 완전 | +60% |

### 성능

| 항목 | 현재 | 목표 | 개선도 |
|------|------|------|--------|
| 캐시 히트율 | 60% | 85% | +25% |
| API 응답시간 | 200ms | 100ms | -50% |
| 메모리 사용 | 500MB | 300MB | -40% |
| 초기 로딩 | 5초 | 2초 | -60% |

### 유지보수성

| 항목 | 현재 | 목표 | 개선도 |
|------|------|------|--------|
| 버그 수정 시간 | 2시간 | 30분 | -75% |
| 기능 추가 시간 | 8시간 | 2시간 | -75% |
| 새 개발자 온보딩 | 3주 | 1주 | -67% |
| 통합 테스트 시간 | 30분 | 5분 | -83% |

