# AI 크로스 체크 기능 (선택사항)

## ⚠️ 중요: 기본 설정
- **기본 모델**: `gemini-2.5-flash` (Thinking 엔진 탑재, 최신 정식 모델)
- **크로스 체크**: 기본적으로 **비활성화** (enable_cross_check: false)
- 대부분의 경우 **2.5 Flash 단독 사용 권장**

## 개요
Gemini 2.0-flash-exp와 2.5-flash 두 모델을 동시에 실행하여 AI 신호의 신뢰도를 높이는 **선택적** 기능입니다.

> **참고**: Gemini 2.5 Flash는 2.0 Flash Exp보다 우수한 성능을 가진 정식 모델입니다.
> Thinking 엔진을 탑재하고 멀티모달 기능이 대폭 강화되어 추론 능력과 성능이 크게 향상되었습니다.

## 작동 원리

### 1. 두 모델 동시 실행
- `gemini-2.0-flash-exp`: 빠르고 최신 모델 (실험적)
- `gemini-2.5-flash`: 안정적인 상용 모델

### 2. 결과 비교 로직

#### ✅ 신호 일치 (buy + buy)
- 두 모델의 신호가 같으면 신뢰도 상향
- Medium → High, High → Very High

#### ⚠️ 신호 불일치 (buy + hold)
- 더 보수적인 신호 선택
- 예: buy vs hold → hold 선택
- 신뢰도: Medium

#### ❌ 한 모델 실패
- 성공한 모델의 결과 사용
- 실패 정보 기록

## 설정 방법

### 1. secrets.json에 설정 추가
```json
{
  "gemini": {
    "api_key": "YOUR_API_KEY",
    "model_name": "gemini-2.5-flash",
    "enable_cross_check": true
  }
}
```

### 2. 코드에서 직접 활성화
```python
from ai.gemini_analyzer import GeminiAnalyzer

# 크로스 체크 활성화
analyzer = GeminiAnalyzer(enable_cross_check=True)
analyzer.initialize()

# 분석 실행
result = analyzer.analyze_stock(stock_data, score_info, portfolio_info)

# 크로스 체크 정보 확인
if 'cross_check' in result:
    cc = result['cross_check']
    print(f"2.0 신호: {cc['model_2_0_signal']}")
    print(f"2.5 신호: {cc['model_2_5_signal']}")
    print(f"일치 여부: {cc['agreement']}")
```

## 테스트

### 테스트 실행
```bash
python test_cross_check.py
```

### 테스트 결과
- 일반 모드 vs 크로스 체크 모드 비교
- 각 모델의 신호 확인
- 신뢰도 변화 확인
- 결과를 `cross_check_test_results.json`에 저장

## 장점

### ✅ 신뢰도 향상
두 모델이 일치하면 신호의 신뢰도가 높아집니다.

### ✅ 리스크 감소
의견이 다르면 보수적으로 판단하여 손실 리스크 감소

### ✅ 장애 대응
한 모델이 실패해도 다른 모델로 백업

### ✅ 투명성
각 모델의 판단을 모두 볼 수 있어 의사결정 투명

## 단점

### ⚠️ 비용 증가
두 모델을 동시에 실행하므로 API 비용 2배

### ⚠️ 속도 저하
두 모델을 순차적으로 실행하므로 분석 시간 증가

### ⚠️ 기회 손실
보수적 선택으로 인한 수익 기회 감소 가능

## 권장 사용 시나리오

### 실거래
- ✅ 추천: 안정성이 최우선

### 백테스팅
- ❌ 비추천: 비용과 시간 낭비

### 고액 거래
- ✅ 추천: 신중한 판단 필요

### 변동성 큰 시장
- ✅ 추천: 리스크 관리 중요

## 버전 정보
- 추가 버전: v6.2.0
- 작성일: 2025-11-06
