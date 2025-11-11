# 대시보드 이슈 수정 가이드

3가지 대시보드 문제를 다양한 접근법으로 해결하는 테스트 및 패치 파일 모음

## 📋 문제 요약

### 1. 계좌 잔고 계산 오류
- **현재 상태**: 인출가능액(`ord_alow_amt`)을 현금으로 표시
- **원하는 상태**: 예수금 - (보유주식 구매가 × 수량) = 실제 사용가능액
- **파일**: `patches/fix_account_balance.py`

### 2. NXT 시장가격 조회 불가
- **현재 상태**: NXT 시간(16:00-18:00)에 현재가 조회 안됨
- **원하는 상태**: NXT 시간에도 시장가격 조회 가능
- **파일**: `patches/fix_nxt_price.py`

### 3. AI 스캐닝 종목 연동 안됨
- **현재 상태**: 대시보드에 "스캐닝 종목 0, AI 분석 완료 0" 표시
- **원하는 상태**: Fast Scan → Deep Scan → AI Scan 결과 실시간 표시
- **파일**: `patches/fix_ai_scanning.py`

---

## 🧪 테스트 실행 방법

### 통합 테스트 (모든 문제 진단)

```python
# main.py에 추가하거나 Python 콘솔에서 실행

from tests.manual_tests.test_dashboard_issues import run_all_tests

# 봇 실행 후
results = run_all_tests(
    bot_instance=bot,
    market_api=bot.market_api,
    account_api=bot.account_api
)

# 결과 확인
print("\n=== 테스트 결과 요약 ===")
for category, tests in results.items():
    print(f"\n{category}:")
    for test in tests:
        status = "✅" if test.get('success') else "❌"
        print(f"  {status} {test.get('method')}")
```

### 개별 테스트

#### 1. 계좌 잔고 테스트

```python
from tests.manual_tests.test_dashboard_issues import AccountBalanceCalculator

deposit = bot.account_api.get_deposit()
holdings = bot.account_api.get_holdings()

# 접근법 1: 예수금 - 구매원가
result1 = AccountBalanceCalculator.approach_1_deposit_minus_holdings(deposit, holdings)
print(f"실제 사용가능액: {result1['available_cash']:,}원")
print(f"계산식: {result1['_debug']['calculation']}")

# 접근법 2: 수동 계산
result2 = AccountBalanceCalculator.approach_2_orderable_amount_direct(deposit, holdings)

# 접근법 3: 계좌평가현황 API
result3 = AccountBalanceCalculator.approach_3_evaluation_based(
    bot.account_api.get_account_evaluation(), holdings
)

# 접근법 4: 모든 필드 확인
result4 = AccountBalanceCalculator.approach_4_manual_calculation(deposit, holdings)
print("\n=== 예수금 필드 비교 ===")
for key, value in result4['deposit_fields'].items():
    print(f"{key}: {value:,}원")
```

#### 2. NXT 가격 조회 테스트

```python
from tests.manual_tests.test_dashboard_issues import NXTPriceChecker

checker = NXTPriceChecker(bot.market_api)
stock_code = '005930'  # 삼성전자

# 접근법 1: 시간대별 API
result1 = checker.approach_1_direct_stock_price(stock_code)
print(f"현재가: {result1['current_price']:,}원")

# 접근법 3: 보유종목 현재가
result3 = checker.approach_3_holdings_current_price(stock_code, bot.account_api)

# 접근법 4: 여러 소스 시도 (가장 견고)
result4 = checker.approach_4_time_aware_price(stock_code)
print(f"가격 소스: {result4['price_source']}")
print(f"NXT 시간: {result4['is_nxt_market']}")
```

#### 3. AI 스캐닝 연동 테스트

```python
from tests.manual_tests.test_dashboard_issues import AIScanningIntegrator

integrator = AIScanningIntegrator(bot)

# 접근법 1: scanner_pipeline 직접 접근
result1 = integrator.approach_1_scanner_pipeline_direct()
print(f"Fast Scan: {result1['fast_scan_count']}개")
print(f"Deep Scan: {result1['deep_scan_count']}개")
print(f"AI Scan: {result1['ai_scan_count']}개")

# 접근법 2: scan_progress 사용
result2 = integrator.approach_2_scan_progress_attribute()

# 접근법 3: 결합 (추천)
result3 = integrator.approach_3_combined_sources()
print("\n=== 최종 카운트 ===")
print(f"스캐닝 종목: {result3['final_counts']['scanning_stocks']}")
print(f"AI 분석 완료: {result3['final_counts']['ai_analyzed']}")
print(f"매수 대기: {result3['final_counts']['buy_pending']}")
```

---

## 🔧 수정 적용 방법

### 방법 1: 패치 직접 사용 (빠른 테스트)

각 패치 파일의 함수를 직접 호출하여 테스트:

```python
# 1. 계좌 잔고 수정
from tests.manual_tests.patches.fix_account_balance import AccountBalanceFix

deposit = bot.account_api.get_deposit()
holdings = bot.account_api.get_holdings()
fixed_account = AccountBalanceFix.approach_1_deposit_minus_purchase(deposit, holdings)
print(f"수정된 현금: {fixed_account['cash']:,}원")

# 2. NXT 가격 조회 수정
from tests.manual_tests.patches.fix_nxt_price import MarketAPIExtended

market_api_ext = MarketAPIExtended(bot.market_api, bot.account_api)
price_info = market_api_ext.get_current_price_with_source('005930')
print(f"현재가: {price_info['price']:,}원 (출처: {price_info['source']})")

# 3. AI 스캐닝 연동 수정
from tests.manual_tests.patches.fix_ai_scanning import get_scanning_info

scanning_info = get_scanning_info(bot, method='combined')
print(f"Fast Scan: {scanning_info['fast_scan']['count']}개")
print(f"Deep Scan: {scanning_info['deep_scan']['count']}개")
print(f"AI Scan: {scanning_info['ai_scan']['count']}개")
```

### 방법 2: 대시보드 코드 수정 (영구 적용)

#### 1. 계좌 잔고 수정

`dashboard/app_apple.py` 파일의 `get_account()` 함수 수정:

```python
# 기존 코드 (233번 라인)
cash = int(deposit.get('ord_alow_amt', 0)) if deposit else 0

# 수정된 코드
# 예수금
deposit_amount = int(deposit.get('dps_amt', 0)) if deposit else 0
# 보유주식 총 구매원가
total_purchase_cost = sum(int(h.get('pchs_amt', 0)) for h in holdings) if holdings else 0
# 실제 사용가능액
cash = deposit_amount - total_purchase_cost
```

**또는** 패치 함수로 교체:

```python
from tests.manual_tests.patches.fix_account_balance import get_account_fixed_approach_1

@app.route('/api/account')
def get_account():
    test_mode_active = getattr(bot_instance, 'test_mode_active', False)
    test_date = getattr(bot_instance, 'test_date', None)

    result = get_account_fixed_approach_1(bot_instance, test_mode_active, test_date)
    return jsonify(result)
```

#### 2. NXT 가격 조회 수정

`dashboard/app_apple.py`의 가격 조회 부분:

```python
from tests.manual_tests.patches.fix_nxt_price import MarketAPIExtended

# bot_instance 초기화 후
market_api_extended = MarketAPIExtended(
    bot_instance.market_api,
    bot_instance.account_api
)

# 가격 조회가 필요한 곳에서
price_info = market_api_extended.get_current_price_with_source(stock_code)
current_price = price_info['price']
```

**또는** `api/market.py`에 메서드 추가:

```python
# api/market.py의 MarketAPI 클래스에 추가

def get_current_price_nxt_aware(self, stock_code: str, account_api=None) -> Optional[int]:
    """NXT 시간 지원 현재가 조회"""
    from tests.manual_tests.patches.fix_nxt_price import NXTPriceFix

    result = NXTPriceFix.approach_4_multiple_sources(self, account_api, stock_code)
    if result and result.get('success'):
        return result.get('current_price', 0)
    return None
```

#### 3. AI 스캐닝 연동 수정

`dashboard/app_apple.py`의 `/api/system` 엔드포인트 수정:

```python
from tests.manual_tests.patches.fix_ai_scanning import AIScanningFix

@app.route('/api/system')
def get_system_status():
    # ... (기존 system_status, test_mode_info, risk_info 코드)

    # 실제 scanning 정보 가져오기 - 수정된 로직
    scanning_info = AIScanningFix.approach_3_combined_sources(bot_instance)

    return jsonify({
        'system': system_status,
        'test_mode': test_mode_info,
        'risk': risk_info,
        'scanning': scanning_info
    })
```

---

## 📊 접근법 비교

### 1. 계좌 잔고 계산

| 접근법 | 장점 | 단점 | 추천도 |
|--------|------|------|--------|
| **접근법 1**: `dps_amt - pchs_amt` | 가장 정확, API 필드 직접 사용 | - | ⭐⭐⭐⭐⭐ |
| **접근법 2**: 수동 계산 | 상세한 계산 과정 | 복잡함 | ⭐⭐⭐ |
| **접근법 3**: 계좌평가현황 API | API가 계산해줌 | API 호출 추가 | ⭐⭐⭐⭐ |
| **접근법 4**: 모든 필드 확인 | 디버깅에 유용 | 실전 사용 부적합 | ⭐⭐ |

**추천**: 접근법 1 (`approach_1_deposit_minus_purchase`)

### 2. NXT 가격 조회

| 접근법 | 장점 | 단점 | 추천도 |
|--------|------|------|--------|
| **접근법 1**: 시간대별 API | 간단, 명확 | 시간 체크 필요 | ⭐⭐⭐⭐ |
| **접근법 2**: NXT 전용 API | 정확 | API 지원 여부 불확실 | ⭐⭐ |
| **접근법 3**: 보유종목 현재가 | 빠름 | 보유종목만 가능 | ⭐⭐⭐ |
| **접근법 4**: 여러 소스 시도 | 가장 견고함 | 약간 복잡 | ⭐⭐⭐⭐⭐ |

**추천**: 접근법 4 (`approach_4_multiple_sources`) - Fallback 지원

### 3. AI 스캐닝 연동

| 접근법 | 장점 | 단점 | 추천도 |
|--------|------|------|--------|
| **접근법 1**: `scanner_pipeline` 직접 | 실시간, 정확 | pipeline 필수 | ⭐⭐⭐⭐ |
| **접근법 2**: `scan_progress` 동기화 | 기존 코드 호환 | 동기화 오버헤드 | ⭐⭐⭐ |
| **접근법 3**: 결합 | 가장 견고함 | - | ⭐⭐⭐⭐⭐ |
| **접근법 4**: 실시간 트리거 | 항상 최신 데이터 | 스캔 비용 | ⭐⭐ |

**추천**: 접근법 3 (`approach_3_combined_sources`) - 여러 소스 결합

---

## 🚀 빠른 시작

### 1단계: 테스트 실행

```bash
cd /home/user/autotrade
python main.py  # 봇 실행
```

Python 콘솔에서:

```python
from tests.manual_tests.test_dashboard_issues import run_all_tests
results = run_all_tests(bot, bot.market_api, bot.account_api)
```

### 2단계: 결과 확인

각 접근법의 성공/실패 여부를 확인하고, 가장 적합한 방법 선택

### 3단계: 패치 적용

선택한 접근법을 대시보드 코드에 적용:

```python
# 예시: 계좌 잔고 수정 (접근법 1)
from tests.manual_tests.patches.fix_account_balance import AccountBalanceFix

deposit = bot.account_api.get_deposit()
holdings = bot.account_api.get_holdings()
fixed_account = AccountBalanceFix.approach_1_deposit_minus_purchase(deposit, holdings)

# dashboard/app_apple.py의 get_account() 함수에 위 로직 적용
```

### 4단계: 대시보드 확인

브라우저에서 대시보드 접속하여 수정 사항 확인

---

## 📁 파일 구조

```
tests/manual_tests/
├── test_dashboard_issues.py          # 통합 테스트 파일
├── patches/
│   ├── fix_account_balance.py        # 계좌 잔고 수정
│   ├── fix_nxt_price.py              # NXT 가격 조회 수정
│   └── fix_ai_scanning.py            # AI 스캐닝 연동 수정
└── README_DASHBOARD_FIXES.md         # 이 문서
```

---

## ❓ FAQ

### Q1: 어떤 접근법을 사용해야 하나요?

**A**: 각 문제별 추천 접근법:
- **계좌 잔고**: 접근법 1 (`approach_1_deposit_minus_purchase`)
- **NXT 가격**: 접근법 4 (`approach_4_multiple_sources`)
- **AI 스캐닝**: 접근법 3 (`approach_3_combined_sources`)

### Q2: 테스트가 실패하면?

**A**:
1. 에러 메시지 확인
2. `result['traceback']` 출력하여 상세 원인 파악
3. API 응답 필드 확인 (`result['_debug']`)
4. 다른 접근법 시도

### Q3: 대시보드에 바로 적용해도 되나요?

**A**:
1. 먼저 테스트 파일로 검증
2. 성공한 접근법만 대시보드에 적용
3. 백업 후 적용 권장

### Q4: NXT 시간이 아닌데 NXT 가격을 조회하려면?

**A**: `approach_3_holdings_current_price`를 사용하거나, `approach_4_multiple_sources`는 자동으로 적절한 소스 선택

### Q5: scanner_pipeline이 없으면?

**A**: `approach_3_combined_sources`를 사용하면 `scan_progress`로 자동 Fallback

---

## 🐛 디버깅 팁

### 계좌 잔고가 이상한 값이 나올 때

```python
# 모든 필드 확인
result = AccountBalanceCalculator.approach_4_manual_calculation(deposit, holdings)
print("=== 예수금 필드 ===")
for key, value in result['deposit_fields'].items():
    print(f"{key}: {value:,}원")

print("\n=== 보유종목 ===")
for h in result['holdings_summary']:
    print(f"{h['name']}: {h['quantity']}주 × {h['avg_price']:,}원 = {h['pchs_amt']:,}원")
```

### NXT 가격이 0으로 나올 때

```python
# 여러 소스 시도 상태 확인
result = NXTPriceChecker.approach_4_time_aware_price(stock_code)
print(f"시도한 소스: {result.get('sources_tried')}")
print(f"현재 시간: {result.get('current_time')}")
print(f"정규시장: {result.get('is_regular_market')}")
print(f"NXT시장: {result.get('is_nxt_market')}")
```

### AI 스캐닝이 0으로 나올 때

```python
# 데이터 소스 확인
result = AIScanningIntegrator.approach_3_combined_sources()
print(f"Fast Scan 소스: {result['fast_scan'].get('source')}")
print(f"Deep Scan 소스: {result['deep_scan'].get('source')}")
print(f"AI Scan 소스: {result['ai_scan'].get('source')}")

# scanner_pipeline 직접 확인
if hasattr(bot, 'scanner_pipeline'):
    pipeline = bot.scanner_pipeline
    print(f"Fast results: {len(pipeline.fast_scan_results)}")
    print(f"Deep results: {len(pipeline.deep_scan_results)}")
    print(f"AI results: {len(pipeline.ai_scan_results)}")
```

---

## 📝 수정 이력

- 2025-01-XX: 초기 작성
  - 3가지 문제에 대한 테스트 및 패치 파일 생성
  - 각 문제별 4가지 접근법 제공
  - 통합 테스트 프레임워크 구축

---

## 💡 추가 개선 사항

향후 개선 가능한 사항:

1. **자동 선택**: 환경에 따라 최적의 접근법 자동 선택
2. **캐싱**: 가격 조회 결과 캐싱으로 API 호출 최소화
3. **알림**: 스캐닝 결과 변경 시 대시보드 자동 업데이트
4. **성능 모니터링**: 각 접근법의 응답 시간 측정

---

**문의**: 문제가 지속되면 이슈 등록 또는 로그 확인
