# NXT 현재가 조회 문제 분석

## 📊 문제 요약

NXT(Next Generation Trading) 종목의 현재가 조회가 실패하는 문제.

## 🔍 발견 사항

### 1. 키움증권 공식 문서 분석

**ka10001 (주식기본정보요청)** 와 **ka10003 (체결정보요청)** 모두 동일한 종목코드 형식 지원:

```
| stk_cd  | 종목코드 | String | Y | 20 | 거래소별 종목코드
                                       (KRX:039490,NXT:039490_NX,SOR:039490_AL) |
```

**문서에 따르면**:
- KRX 종목: 기본 코드 (예: 249420)
- NXT 종목: **_NX 접미사** (예: 249420_NX)  ← 핵심!
- SOR 종목: _AL 접미사 (예: 249420_AL)

### 2. 현재 구현 상태

**파일**: `api/market/market_data.py:31-140`

**현재 동작**:
```python
def get_stock_price(self, stock_code: str, use_fallback: bool = True):
    # _NX 접미사 제거 (테스트 결과: 기본 코드만 작동)
    base_code = stock_code[:-3] if stock_code.endswith("_NX") else stock_code

    body = {"stk_cd": base_code}

    response = self.client.request(
        api_id="ka10003",  ← 체결정보요청 사용
        body=body,
        path="stkinfo"
    )
```

**문제점**:
- ka10003 API 사용 중
- _NX 접미사를 **강제로 제거**
- 이유: 이전 테스트에서 _NX 사용 시 0% 성공률

### 3. 키움 API 어시스턴트 추천

사용자가 공유한 키움 API 어시스턴트 응답:

> **NXT 거래소 종목코드는 종목코드 뒤에 "_NX"를 붙여 사용합니다.**
> **fn_ka10001 함수를 호출하여 해당 종목의 현재가를 포함한 기본 정보를 조회합니다.**

**핵심 차이점**:
- 어시스턴트는 **ka10001**을 추천 (주식기본정보요청)
- 현재 구현은 **ka10003** 사용 (체결정보요청)
- 두 API는 동일한 문서를 가지지만, **실제 동작이 다를 수 있음**

### 4. 테스트 결과 (debug_nxt_all_methods.py)

**실행 시간**: NXT 시간 외 (장 마감 후)

| API/방법 | 코드 | 결과 | 현재가 |
|---------|------|------|--------|
| ka10003 | 249420 (기본) | ✅ 성공 | 30,600원 |
| ka10003 | 249420_NX | ❌ 실패 | - |
| ka10004 | 249420 (기본) | ✅ 성공 | 30,575원 |
| ka10004 | 249420_NX | ❌ 실패 | - |
| ka30002 | 249420 (기본) | ✅ 성공 | - |
| ka30002 | 249420_NX | ❌ 실패 | - |
| WebSocket (모든 타입) | 모두 | ❌ 타임아웃 | - |

**성공률**: 11.1% (2/18 방법)

**중요**: 이 테스트는 **ka10001을 테스트하지 않았음**

### 5. 계좌 API의 종목코드 형식

**파일**: `api/account.py:462-485`

계좌 잔고 조회(ka10071) API는 NXT 종목을 다음과 같이 반환:

```json
{
  "stk_cd": "249420_NX",  ← _NX 접미사 포함
  "stk_nm": "일동제약",
  ...
}
```

**현재 해결책**:
```python
# api/account.py:462
if holdings:
    for holding in holdings:
        if 'stk_cd' in holding and holding['stk_cd'].endswith('_NX'):
            original_code = holding['stk_cd']
            holding['stk_cd'] = holding['stk_cd'][:-3]  # _NX 제거
```

## 💡 가설

### 가설 1: ka10001 vs ka10003 차이
**가능성**: ka10001은 _NX 접미사를 올바르게 처리하지만, ka10003은 처리하지 못할 수 있음.

**근거**:
- 키움 API 어시스턴트가 **명시적으로 ka10001 추천**
- 두 API의 문서는 동일하지만 내부 구현이 다를 수 있음
- ka10001 = "주식기본정보요청" (더 포괄적)
- ka10003 = "체결정보요청" (실시간 체결에 특화)

### 가설 2: NXT 거래 시간 의존성
**가능성**: _NX 접미사는 NXT 거래 시간(08:00-09:00, 15:30-20:00)에만 작동.

**근거**:
- 기존 테스트는 장 마감 후 실행됨
- NXT 시간 외에는 _NX 코드가 유효하지 않을 수 있음

## 🎯 제안 해결책

### 방안 1: ka10001로 API 변경 (추천)

**장점**:
- 키움 공식 어시스턴트 추천 방법
- _NX 접미사를 제거할 필요 없음
- 더 깔끔한 코드

**단점**:
- NXT 거래 시간에 실제 테스트 필요
- ka10001이 실시간 현재가를 제공하는지 확인 필요

**구현 예시**:
```python
def get_stock_price(self, stock_code: str, use_fallback: bool = True):
    """
    종목 현재가 조회 (ka10001 - 주식기본정보요청)
    NXT 종목은 _NX 접미사 유지
    """
    body = {"stk_cd": stock_code}  # _NX 접미사 그대로 사용

    response = self.client.request(
        api_id="ka10001",  # ka10003 → ka10001로 변경
        body=body,
        path="stkinfo"
    )

    if response and response.get('return_code') == 0:
        # ka10001 응답 파싱
        cur_prc = response.get('cur_prc', '0')  # 필드명 확인 필요
        current_price = abs(int(cur_prc.replace('+', '').replace('-', '')))

        return {
            'current_price': current_price,
            'source': 'ka10001',
            ...
        }

    return None
```

### 방안 2: 조건부 API 사용

NXT 종목 여부에 따라 다른 API 사용:

```python
def get_stock_price(self, stock_code: str):
    is_nxt_stock = stock_code.endswith('_NX')

    if is_nxt_stock:
        # NXT 종목: ka10001 + _NX 접미사
        api_id = "ka10001"
        body = {"stk_cd": stock_code}  # _NX 유지
    else:
        # 일반 종목: ka10003 + 기본 코드
        api_id = "ka10003"
        body = {"stk_cd": stock_code}

    response = self.client.request(api_id=api_id, body=body, path="stkinfo")
    ...
```

### 방안 3: 현재 방식 유지 (임시 해결)

_NX 접미사 제거 + ka10003 사용 (현재 구현)

**장점**:
- 이미 작동 중 (기본 코드로 조회하면 성공)
- 추가 테스트 불필요

**단점**:
- NXT 시간대에 실시간 가격이 정확한지 불확실
- 공식 문서와 다른 방식
- 계좌 API에서 _NX 접미사를 제거하는 패치 필요

## 📋 필요 작업

### 1단계: ka10001 테스트 실행 (필수)

**파일**: `tests/debug/test_ka10001_nx.py` (이미 생성됨)

**실행 조건**: NXT 거래 시간 (오전 08:00-09:00 또는 오후 15:30-20:00)

**테스트 항목**:
1. ka10001 + 기본 코드 (249420)
2. ka10001 + _NX 코드 (249420_NX)
3. 응답 구조 확인
4. 현재가 필드명 확인

### 2단계: 테스트 결과에 따른 구현 선택

**시나리오 A**: ka10001 + _NX 성공
→ 방안 1 적용 (ka10003 → ka10001 전환)

**시나리오 B**: ka10001 + 기본 코드 성공
→ 방안 3 유지 (현재 방식)

**시나리오 C**: 모두 실패
→ 추가 조사 필요, 키움 고객센터 문의

### 3단계: 전체 수정 파일

성공 시나리오에 따라 다음 파일 수정:

1. **api/market/market_data.py** - 현재가 조회 API 변경
2. **api/account.py** - _NX 제거 로직 수정/제거
3. **research/data_fetcher.py** - 동일 수정
4. **api_server/main.py** - 동일 수정
5. **utils/nxt_realtime_price.py** - NXT 실시간 가격 관리

## 🚨 주의사항

1. **테스트는 반드시 NXT 거래 시간에 실행**
   - 오전 08:00-09:00
   - 오후 15:30-20:00

2. **테스트 종목**:
   - 249420 (일동제약) - 거래량 많음
   - 052020 (에프엔에스테크)

3. **성공 기준**:
   - API 응답 return_code = 0
   - 현재가 필드 존재 및 0보다 큼
   - 가격이 합리적인 범위

## 📚 참고 문서

- `/home/user/autotrade/kiwoom_docs/종목정보.md` - ka10001, ka10003 상세 스펙
- `/home/user/autotrade/tests/debug/debug_nxt_all_methods.py` - 종합 테스트 결과
- `/home/user/autotrade/tests/debug/test_ka10001_nx.py` - ka10001 테스트 (실행 대기)

## 🎓 배운 교훈

1. **문서와 실제 동작이 다를 수 있음** - ka10003은 문서상 _NX 지원이지만 실패
2. **API 어시스턴트 추천을 따르는 게 안전** - ka10001 추천에는 이유가 있을 것
3. **NXT 시간대 의존성 고려** - 거래 시간 외 테스트는 의미 없을 수 있음
4. **종합 테스트의 중요성** - 18가지 조합 테스트로 문제 명확히 파악

---
작성일: 2025-11-06
작성자: Claude (Sonnet 4.5)
버전: v5.15
