# 분봉 차트 조회 실패 분석 보고서

## 테스트 일시
2025-11-07 18:09 (NXT 애프터마켓 시간)

## 문제 상황
모든 분봉 조회 메서드가 **"정상적으로 처리되었습니다"** 응답하지만 **데이터 0개** 반환

### 실패한 메서드들
1. Method 1: ka10080 직접 호출 (수정주가 반영)
2. Method 2: ka10080 대체 파라미터 (수정주가 미반영)
3. Method 3: ChartDataAPI 래퍼
4. Method 4: 다중 시간프레임 일괄 조회
5. Method 5: 비표준 간격 (3/10/20분)

## 원인 분석

### 1. 시간대 문제 (가장 가능성 높음)
**현재 시간**: 18:09 (애프터마켓)
**정규 장 시간**: 09:00 - 15:30

키움증권 ka10080 API는 **장 시간에만 분봉 데이터 제공**일 가능성:
- 장외 시간에는 분봉 생성 안됨
- 당일 분봉은 장 종료 후 조회 가능하나, API가 막혀있을 수 있음

### 2. API return_code는 0인데 데이터가 없는 이유
```
return_code: 0 (성공)
return_msg: "정상적으로 처리되었습니다"
stk_tic_pole_chart_qry: [] (빈 배열)
```

→ API 호출 자체는 성공했지만, **해당 시간/조건에 데이터가 없음**

### 3. 가능한 원인들

#### A. 장외 시간 제약
- 분봉은 실시간 데이터이므로 장 시간에만 제공
- 과거 분봉은 일봉 API를 사용해야 할 수 있음

#### B. NXT 시간대 특수성
- NXT 거래는 호가/체결만 제공하고 분봉은 미제공일 수 있음
- NXT 분봉은 별도 API가 필요할 수 있음

#### C. API 파라미터 문제
현재 사용 중인 파라미터:
```python
{
    "stk_cd": stock_code,
    "tic_scope": "1",  # 1/5/15/30/60
    "upd_stkpc_tp": "1"  # 수정주가 반영
}
```

누락 가능한 파라미터:
- `base_dt`: 기준일 (YYYYMMDD)
- `base_tm`: 기준시각 (HHMMSS)
- `data_cnt`: 조회 개수

#### D. 코스피/코스닥 구분 필요
- 일부 API는 시장 구분 필요 (`mrkt_tp`)
- 종목에 따라 파라미터 변경 필요

## 해결 방안

### 단기 해결책 (즉시 적용 가능)

#### 1. 정규 장 시간에 재테스트
**추천 테스트 시간**:
- 오전: 09:30 - 11:30
- 오후: 13:00 - 15:00

#### 2. 기준일 파라미터 추가
```python
from utils.trading_date import get_last_trading_date

body = {
    "stk_cd": stock_code,
    "tic_scope": str(interval),
    "upd_stkpc_tp": "1",
    "base_dt": get_last_trading_date()  # 추가
}
```

#### 3. 과거 날짜 분봉 조회 시도
```python
body = {
    "stk_cd": stock_code,
    "tic_scope": str(interval),
    "upd_stkpc_tp": "1",
    "base_dt": "20251106"  # 어제
}
```

### 중기 해결책

#### 1. 키움증권 API 문서 재확인
ka10080 API 스펙 정확히 확인:
- 필수 파라미터
- 시간 제약
- 반환 데이터 형식

#### 2. 대체 API 탐색
- WebSocket 실시간 분봉 구독
- `core.realtime_minute_chart.py`의 `RealtimeMinuteChart` 사용

#### 3. Fallback 로직 구현
```python
# 1순위: ka10080 API
# 2순위: WebSocket 실시간 분봉
# 3순위: 체결 데이터로 분봉 직접 생성
```

### 장기 해결책

#### 1. 분봉 캐싱 시스템 구축
- 장 시간에 분봉 수집 후 DB 저장
- 장외 시간에는 캐시 데이터 사용

#### 2. WebSocket 기반 실시간 분봉 생성
```python
from core.realtime_minute_chart import RealtimeMinuteChart

chart = RealtimeMinuteChart(stock_code)
candles = chart.get_candles(minutes=60)  # 최근 60분 캔들
```

## 추천 테스트 시나리오

### 시나리오 1: 정규 장 시간 재테스트
**시간**: 내일 09:30 ~ 15:00
**목적**: 장 시간에는 분봉 데이터가 정상 조회되는지 확인

### 시나리오 2: 기준일 파라미터 추가 테스트
**수정 파일**: `tests/manual/test_minute_chart_multi_method.py`
**변경 내용**:
```python
body = {
    "stk_cd": stock_code,
    "tic_scope": str(interval),
    "upd_stkpc_tp": "1",
    "base_dt": get_last_trading_date()  # 추가
}
```

### 시나리오 3: WebSocket 실시간 분봉 테스트
**새 파일**: `tests/manual/test_realtime_minute_chart.py`
**내용**: WebSocket으로 실시간 체결 → 분봉 생성

## 결론

**주요 원인**: 장외 시간(18:09)에 분봉 API가 데이터를 제공하지 않음

**권장 조치**:
1. ✅ **즉시**: 내일 정규 장 시간에 동일 테스트 재실행
2. ✅ **단기**: 기준일 파라미터 추가 후 재테스트
3. ✅ **중기**: WebSocket 기반 실시간 분봉 구현
4. ✅ **장기**: 분봉 캐싱 시스템 구축

## 참고 파일

- `/home/user/autotrade/api/market/chart_data.py` - 차트 API 구현
- `/home/user/autotrade/core/realtime_minute_chart.py` - 실시간 분봉 생성기
- `/home/user/autotrade/api/kiwoom_api_specs.py` - API 스펙 문서
