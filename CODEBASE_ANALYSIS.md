# AutoTrade 코드베이스 분석 보고서
## 하드코딩 및 주석 분석

---

## 1. TODO/FIXME 주석 분석

### 긴급 처리 필요
| 파일 | 라인 | 내용 | 우선순위 |
|------|------|------|---------|
| `virtual_trading/models.py` | 326 | `current_capital` + 주식 평가금액 계산 필요 | 높음 |
| `virtual_trading/scheduler.py` | 461-462 | 코스피/코스닥 등락률 실시간 계산 필요 | 높음 |
| `research/scan_strategies.py` | 526, 551 | AI 시장 분석 및 스캔 전략 질의 구현 필요 | 높음 |

### 미완성 API 엔드포인트
| 파일 | 라인 | 내용 |
|------|------|------|
| `api_server/main.py` | 497 | AI 분석 결과 조회 미구현 |
| `api_server/main.py` | 514 | 분석 결과 조회 미구현 |
| `api_server/main.py` | 537 | 백테스트 실행 미구현 |
| `api_server/main.py` | 552 | 백테스트 결과 조회 미구현 |
| `api_server/main.py` | 572 | 리포트 생성 미구현 |
| `api_server/main.py` | 592 | 최적화 실행 미구현 |
| `api_server/main.py` | 607 | 최적화 결과 조회 미구현 |

### 업타임 계산
| 파일 | 라인 | 내용 |
|------|------|------|
| `api_server/main.py` | 186 | 실제 시작 시간 추적 필요 |

---

## 2. 하드코딩된 매직 넘버 분석

### 2.1 지표 계산 임계값 (indicators/)

#### Volume Indicators
```
파일: indicators/volume.py
라인 112-129: 거래량 비율 점수
  - 2.0 이상: 90점 (very_high)
  - 1.5 이상: 70점 (high)
  - 1.2 이상: 60점 (above_average)
  - 0.5 이하: 20점 (very_low)
  - 0.7 이하: 35점 (low)
  - 기타: 50점 (normal)

라인 150-163: OBV 점수
  - Bullish confirmation: 70점
  - Bearish: 25점
  - 기본: 50점

라인 170: 복합 신호 조건 (score >= 65 && vol_ratio >= 1.5)
라인 253: 볼륨 구간 분석 (num_bins=10)
```

#### Volatility Indicators
```
파일: indicators/volatility.py
라인 14, 68-69: Bollinger Bands 기본값
  - period: 20
  - std_dev: 2.0
  - atr_period: 14

라인 128-139: %B 기반 조건
  - percent_b > 0.8: 65점 (near_upper)
  - percent_b < 0.2: 65점 (near_lower)
  - 기타: 40점 (neutral)

라인 145, 148: Bollinger Band Squeeze 임계값
  - 0.7: tight squeeze
  - 0.85: moderate squeeze
```

#### Trend Indicators
```
파일: indicators/trend.py
라인 40: 이동평균선 기본값
  - short_period: 20
  - long_period: 60

라인 82, 122, 131, 134: 추세 점수
  - 상승 강세: 100점
  - 상승: 50점
```

### 2.2 AI 학습 시스템 상수 (features/ai_learning.py)

```python
라인 14-30: 거래 분석 기본값
  MIN_TRADES_FOR_ANALYSIS = 10
  MIN_DATA_FOR_PATTERN = 20
  MIN_PATTERN_SAMPLES = 3
  RSI_OVERSOLD = 30
  RSI_OVERBOUGHT = 70
  VOLUME_SURGE_MULTIPLIER = 1.8
  MOMENTUM_PERIOD = 5
  MOMENTUM_THRESHOLD = 0.05
  MIN_SUCCESS_RATE_RSI = 0.55
  MIN_SUCCESS_RATE_VOLUME = 0.60
  MIN_SUCCESS_RATE_MOMENTUM = 0.58
  BULL_TREND_THRESHOLD = 0.02
  BEAR_TREND_THRESHOLD = -0.02
  HIGH_VOLATILITY_THRESHOLD = 0.30
  NORMAL_VOLATILITY_THRESHOLD = 0.20
  MIN_OPTIMIZATION_DATA = 5
```

### 2.3 실전 투자 설정 (virtual_trading/live_trading_bridge.py)

```python
라인 22-33: LiveTradingConfig
  min_win_rate: float = 60.0%
  min_trades: int = 50
  min_return_rate: float = 10.0%
  max_drawdown: float = 15.0%
  max_daily_loss_pct: float = 5.0%
  max_position_size_pct: float = 20.0%
  max_total_investment_pct: float = 80.0%
  initial_live_capital: float = 10,000,000원 (1천만원)
```

### 2.4 위험 관리 점수 (virtual_trading/evolution_engine.py)

```python
라인 588-607: 수익률 점수
  >= 30%: +40점
  >= 20%: +35점
  >= 10%: +25점
  < 10%: +15점

라인 600-607: Sharpe Ratio 점수
  >= 2.0: +30점
  >= 1.5: +25점
  >= 1.0: +20점
  >= 0.5: +10점

라인 610-621: 승률 점수
  >= 70%: +20점
  >= 60%: +15점
  >= 50%: +10점
  >= 40%: +5점
  >= 20: 거래 수 +10점
  >= 10: 거래 수 +5점

라인 640-657: Drawdown 점수
  <= 5%: +30점
  <= 10%: +25점
  <= 15%: +20점
  <= 20%: +10점
```

### 2.5 리스크 분석 기본값 (strategy/advanced_risk_analytics.py)

```python
라인 38: confidence_level: float = 0.95 (95%)
라인 126: num_simulations: int = 10000
라인 218, 258: periods_per_year: int = 252 (거래일)
라인 461-462: 시뮬레이션 파라미터
  time_horizon: int = 252
  num_simulations: int = 1000
```

### 2.6 기술 분석 계산값 (research/analyzer.py)

```python
라인 166: commission_rate = 0.00015 (0.015%)
라인 248: commission_rate = 0.00015 (0.015%)
라인 260: min 데이터 크기 = 20
라인 292: RSI period = 14
라인 269-271: price_position = 0.5 (기본값)
```

### 2.7 시장 스캔 조건 (research/scan_strategies.py)

```python
라인 108-112: VolumeBasedStrategy 필터
  min_price: 1,000원
  max_price: 1,000,000원
  min_volume: 100,000주
  min_rate: 1.0%
  max_rate: 15.0%

라인 162-183: 거래대금 점수
  > 1억: 40점
  > 5천만: 30점
  else: 0점

라인 172: 상승률 조건: 2.0% <= rate <= 10.0%
라인 179, 190: 거래량/후보 수 조건: 1,000,000주, 20개
라인 254: rate 계산: (close - open) / open
라인 465-469: 상승률 점수
  >= 10%: 높음
  >= 5%: 중간
  >= 3%: 낮음

라인 536: 기본 점수 = 50점
```

### 2.8 자동 리밸런싱 (features/auto_rebalancer.py)

```python
라인 65: rebalance_threshold: float = 5.0% (5% 이탈시)
라인 331, 348, 390, 411: weight = 100.0 / len(holdings) (균등 배분)
```

### 2.9 API 호출 설정 (api/batch_client.py)

```python
라인 36: batch_size: int = 20 (배치 크기)
라인 37: max_retries: int = 3 (재시도 횟수)
라인 38: rate_limit_per_second: int = 100
라인 58: request_interval = 1.0 / rate_limit_per_second
```

---

## 3. 하드코딩된 경로 및 문자열

### 3.1 API 엔드포인트 (config/constants.py)

```python
라인 82-90: 호스트 및 포트 설정
  HOST = '0.0.0.0'
  OPENAPI_HOST = '127.0.0.1'
  REDIS_HOST = 'localhost'
  
  PORTS = {
    'openapi': 5001,
    'dashboard': 5000,
    'redis': 6379
  }

라인 92-97: URL 구성
  'openapi_server': f'http://127.0.0.1:5001'
  'kiwoom_api_base': 'https://api.kiwoom.com'
  'openapi_health': f'http://127.0.0.1:5001/health'
  'dashboard': f'http://localhost:5000'
```

### 3.2 시간 설정 (config/constants.py)

```python
라인 61-65: MARKET_HOURS
  regular: {'start': '09:00', 'end': '15:30'}
  nxt_premarket: {'start': '08:00', 'end': '09:00'}
  nxt_aftermarket: {'start': '15:40', 'end': '20:00'}
```

### 3.3 AI 모델 설정 (config/constants.py)

```python
라인 10-14: AI_MODELS
  primary: 'gemini-2.5-flash'
  secondary: 'gemini-2.0-flash-exp'
  fallback: 'gemini-pro'
```

### 3.4 시간 필터 (core/realtime_minute_chart.py)

```python
라인 68: max_candles = 390 (09:00 ~ 15:30)
라인 179: 시장 운영 시간 체크 (hour < 8 or hour >= 20)
라인 201, 296: 기본 조회 기간 = 60분
```

### 3.5 주문 유형 (api/order.py)

```python
라인 50, 192: order_type: str = '02' (지정가)
라인 84-92: 거래 유형 상수
  '62': 시간외단일가
  '81': 장마감후시간외
  '61': 장시작전시간외
  '0': 보통(지정가)
  '3': 시장가
```

### 3.6 초기 자본금 (config/constants.py, fix_virtual_trading.py)

```python
라인 67-68: config/constants.py
  DEFAULT_INITIAL_CAPITAL = 10,000,000원
  DEFAULT_VIRTUAL_CAPITAL = 10,000,000원

라인 51: fix_virtual_trading.py
  initial_capital = 10,000,000원
```

### 3.7 API 타임아웃 (config/constants.py)

```python
라인 55-59: API_TIMEOUTS
  'default': 10초
  'long': 30초
  'short': 5초
```

### 3.8 지연 시간 설정 (config/constants.py)

```python
라인 70-80: DELAYS
  'api_retry': 1.0초
  'api_retry_error': 2.0초
  'paper_trading_check': 30.0초
  'paper_trading_error': 60.0초
  'order_check': 30.0초
  'websocket_reconnect': 5.0초
  'rate_limit': 0.2초
  'server_init': 1.0초
  'batch_delay': 0.1초
```

---

## 4. 설정으로 이동해야 할 값들

### 우선순위 높음 (즉시 이동 권장)

| 값 | 현재위치 | 설정파일 | 변수명 | 타입 |
|-----|--------|---------|-------|------|
| 60.0 (최소승률%) | live_trading_bridge.py:22 | trading_params.py | MIN_WIN_RATE | float |
| 50 (최소거래횟수) | live_trading_bridge.py:23 | trading_params.py | MIN_TRADES_COUNT | int |
| 10.0 (최소수익률%) | live_trading_bridge.py:24 | trading_params.py | MIN_RETURN_RATE | float |
| 15.0 (최대낙폭%) | live_trading_bridge.py:25 | trading_params.py | MAX_DRAWDOWN_PCT | float |
| 5.0 (일일손실제한%) | live_trading_bridge.py:28 | trading_params.py | MAX_DAILY_LOSS_PCT | float |
| 20.0 (포지션크기%) | live_trading_bridge.py:29 | trading_params.py | MAX_POSITION_SIZE_PCT | float |
| 20 (볼린저밴드기간) | volatility.py:13, 67 | indicator_params.py | BB_PERIOD | int |
| 2.0 (볼린저밴드표준편차) | volatility.py:14, 68 | indicator_params.py | BB_STD_DEV | float |
| 14 (ATR기간) | volatility.py:38, 69 | indicator_params.py | ATR_PERIOD | int |
| 30 (RSI오버솔드) | features/ai_learning.py:17 | indicator_params.py | RSI_OVERSOLD | int |
| 70 (RSI오버바우트) | features/ai_learning.py:18 | indicator_params.py | RSI_OVERBOUGHT | int |
| 1.8 (거래량급증배수) | features/ai_learning.py:19 | ai_params.py | VOLUME_SURGE_MULTIPLIER | float |
| 20 (분석최소데이터) | features/ai_learning.py:15 | ai_params.py | MIN_DATA_FOR_PATTERN | int |
| 0.95 (신뢰도%) | advanced_risk_analytics.py:38 | risk_params.py | VAR_CONFIDENCE_LEVEL | float |
| 10000 (몬테카를로시뮬레이션) | advanced_risk_analytics.py:126 | risk_params.py | MONTE_CARLO_SIMULATIONS | int |

### 우선순위 중간 (정규화 권장)

| 값 | 현재위치 | 설정파일 | 변수명 |
|-----|--------|---------|-------|
| 100 (API rate limit/sec) | batch_client.py:38 | api_params.py | API_RATE_LIMIT_PER_SEC |
| 20 (batch size) | batch_client.py:36 | api_params.py | BATCH_SIZE |
| 1000, 500_000_000 (거래대금조건) | scan_strategies.py:162-165 | screening_params.py | TRADING_VALUE_THRESHOLDS |
| 2.0 - 10.0 (상승률범위) | scan_strategies.py:172 | screening_params.py | PRICE_CHANGE_RANGE |
| 390 (최대분봉수) | realtime_minute_chart.py:68 | chart_params.py | MAX_MINUTE_CANDLES |
| 0.00015 (수수료율) | analyzer.py:166, 248 | trading_params.py | COMMISSION_RATE |
| 5.0 (리밸런싱임계값%) | auto_rebalancer.py:65 | rebalance_params.py | REBALANCE_THRESHOLD_PCT |
| 30, 60 (이동평균기간) | trend.py:40 | indicator_params.py | MA_SHORT_PERIOD, MA_LONG_PERIOD |

---

## 5. 불필요한 주석 분석

### 5.1 자명한 코드를 설명하는 주석

```python
// analyzer.py:63-65
# 현재가 정보
price_info = self.fetcher.get_current_price(stock_code)  # ← 변수명이 충분히 명확함

// core/realtime_minute_chart.py:28-36
# 체결 데이터로 캔들 업데이트
if self.open == 0:
    self.open = price  # ← 메서드명이 이미 업데이트를 명시함

// evolution_engine.py:81-83
# 딕셔너리로 변환
return {  # ← 메서드명이 이미 변환을 명시함
```

### 5.2 버전 관리 주석 (정리 필요)

```python
// core/__init__.py:30
# v4.2 Standard Types (CRITICAL #2)

// strategy/__init__.py:15, 30, 31, 42
# v4.0 Advanced Strategies
# v4.2: Position from core (standardized), PositionManager from local
# v4.2: Use standard Position

// main.py 전반적으로 많은 버전/Fix 주석들
// Fix v6.1.3, Fix v6.1.5, Fix v6.1.4 등
```

### 5.3 중복 설명 주석

```python
// features/ai_learning.py:22-29
MIN_SUCCESS_RATE_RSI = 0.55  # RSI 기반 신호 최소 성공률
MIN_SUCCESS_RATE_VOLUME = 0.60  # 거래량 기반 신호 최소 성공률
# ← 변수명이 이미 충분히 설명함
```

---

## 6. 코드 개선 제안

### 6.1 매직 넘버 상수화 우선순위

**Phase 1 (긴급):**
1. Trading threshold (승률, 수익률, 낙폭) → trading_params.py
2. Technical indicator parameters (기간, 표준편차) → indicator_params.py
3. Risk management values (손실 제한, 포지션크기) → risk_params.py

**Phase 2 (중요):**
1. Scoring thresholds → scoring_params.py
2. API configuration → api_params.py
3. Market hours → market_params.py

**Phase 3 (개선):**
1. Algorithm parameters → algo_params.py
2. AI model settings → ai_params.py
3. Screening filters → screening_params.py

### 6.2 설정 파일 구조 (제안)

```python
config/
├── constants.py (기존 - 공통상수)
├── trading_params.py (신규 - 거래 파라미터)
├── indicator_params.py (신규 - 지표 파라미터)
├── risk_params.py (신규 - 위험 파라미터)
├── api_params.py (신규 - API 파라미터)
├── screening_params.py (신규 - 스크리닝 조건)
├── market_params.py (신규 - 시장 시간/조건)
└── algo_params.py (신규 - 알고리즘 파라미터)
```

### 6.3 주석 정리 가이드라인

**삭제할 주석:**
- 버전/Fix 관리 주석 → git history 활용
- 변수명으로 충분한 설명 주석
- 메서드명으로 충분한 기능 주석

**유지할 주석:**
- 왜(Why) 설명하는 주석 (비즈니스 로직)
- 복잡한 알고리즘 설명
- 특정 값 선택 이유
- TODO/FIXME (우선순위 정보와 함께)

---

## 7. 정리 우선순위

### 높음 (1주일 내)
- [ ] TODO/FIXME 우선순위 정리 및 일정 수립
- [ ] 거래 파라미터 설정 파일 생성 (trading_params.py)
- [ ] 지표 파라미터 설정 파일 생성 (indicator_params.py)

### 중간 (2-3주)
- [ ] 나머지 설정 파일 생성
- [ ] 코드에서 하드코딩 제거 및 설정 사용으로 변경
- [ ] 버전/Fix 주석 정리

### 낮음 (1개월)
- [ ] 불필요한 주석 정리
- [ ] 코드 문서화 개선
- [ ] 설정 파일 통합 (필요시)

