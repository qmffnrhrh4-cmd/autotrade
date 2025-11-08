# 트레이딩 시스템 문제 분석 보고서

## 작성일: 2025-11-07
## 작성자: Claude AI Assistant

---

## ✅ 완료된 수정사항

### 1. NXT 거래가능 종목 테스트 파일 생성 ✅
**파일**: `/tests/manual/test_nxt_price_multi_method.py`

**목적**:
- 일반시장 종가와 NXT 현재가의 차이 확인
- 여러 API 메서드로 NXT 현재가 조회 시도
- 5초 간격 10번 반복 테스트로 실시간 가격 변동 감지

**구현된 테스트 방법**:
1. Method 1: ka10003 API (기본 코드)
2. Method 2: ka10003 API (_NX 접미사)
3. Method 3: ka10004 호가 API (기본 코드)
4. Method 4: ka10004 호가 API (_NX 접미사)
5. Method 5: ka10081 차트 종가
6. Method 6: NXTRealtimePriceManager

**사용법**:
```bash
python tests/manual/test_nxt_price_multi_method.py
```

---

### 2. 분봉 데이터 조회 테스트 파일 생성 ✅
**파일**: `/tests/manual/test_minute_chart_multi_method.py`

**목적**:
- 여러 API 메서드로 분봉 데이터 조회 시도
- 1분, 3분, 5분, 15분, 30분, 60분봉 조회 테스트
- 5초 간격 10번 반복 테스트로 데이터 변동 확인

**구현된 테스트 방법**:
1. Method 1: ka10080 API 직접 호출 (수정주가 반영)
2. Method 2: ka10080 API 대체 파라미터 (수정주가 미반영)
3. Method 3: ChartDataAPI 공식 래퍼
4. Method 4: 다중 시간프레임 일괄 조회
5. Method 5: 비표준 분봉 간격 시도 (3분, 10분, 20분)

**사용법**:
```bash
python tests/manual/test_minute_chart_multi_method.py
```

---

### 3. AI 실시간 시장 코멘터리 장외시간 분석 기능 추가 ✅
**파일**: `/dashboard/routes/ai/market_commentary.py`

**수정 내용**:
- 장외 시간 감지 강화 (프리마켓, 애프터마켓, 장 마감 후)
- 장외 시간 전용 분석 로직 추가:
  - 오늘 거래 복기 (최고 수익/최대 손실 종목)
  - 포트폴리오 균형 분석
  - 다음 거래일 전략 수립

**개선 효과**:
- 장외 시간에도 의미있는 코멘터리 제공
- 다음 거래일 준비 전략 제시
- 포트폴리오 복기 및 개선 방향 제안

---

### 4. AI 확신도 게이지 240% 문제 수정 ✅
**파일**: `/dashboard/routes/system.py`

**문제 원인**:
- `score` 필드가 0-440 범위의 점수인데, 이를 백분율로 변환하지 않고 그대로 사용
- 158점, 250점 같은 값을 그대로 확신도로 표시하여 240% 같은 비정상 값 발생

**수정 내용** (314-315번 라인):
```python
raw_score = cand.get('score', 0)
normalized_score = min(100, round((raw_score / 440) * 100))  # 최대 100%로 제한
```

**개선 효과**:
- 확신도가 0-100% 범위로 정규화됨
- 평균 계산 시 정상적인 백분율 표시

---

### 5. 리스크 히트맵 0% 문제 수정 ✅
**파일**: `/dashboard/templates/dashboard_main.html`

**문제 원인**:
- 실제 변동성 데이터를 사용하지 않고 수익률만 사용
- 모든 종목의 수익률이 0이거나 매우 작으면 리스크도 0% 근처로 표시됨

**수정 내용** (5164-5232번 라인):
- `/api/risk/analysis` API를 사용하여 실제 리스크 분석 데이터 활용
- Volatility와 VaR (Value at Risk)를 조합한 정확한 리스크 계산
- Fallback 로직 개선 (리스크 최소값 10% 보장)

**개선 효과**:
- 실제 변동성 기반 리스크 표시
- 더 정확한 포트폴리오 리스크 시각화

---

## 📋 분석된 문제들 (추가 작업 필요)

### 6. 실시간 포지션 모니터링 & AI 매매 신호 문제

**관련 파일**:
- `/dashboard/templates/dashboard_main.html` - 프론트엔드 표시
- `/dashboard/routes/portfolio.py` - 포트폴리오 API
- `/dashboard/routes/system.py` - AI 매매 신호 API
- `/features/realtime_alerts.py` - 실시간 알림

**분석 결과**:
대시보드에서 `/api/portfolio` 및 `/api/candidates` API를 호출하여 데이터를 가져오지만, 다음 중 하나의 이유로 정보가 표시되지 않을 수 있음:

1. **Bot Instance 미초기화**: `_bot_instance`가 None이거나 초기화되지 않음
2. **데이터 없음**: 실제 매매가 없어서 포지션이나 AI 신호가 없음
3. **API 응답 오류**: API가 에러를 반환하지만 프론트엔드에서 처리하지 않음
4. **WebSocket 연결 문제**: 실시간 업데이트를 위한 WebSocket이 연결되지 않음

**권장 해결책**:
1. Bot 초기화 상태 체크 강화
2. 데이터 없음 상태를 명확히 표시하는 UI 개선
3. 에러 로깅 및 사용자 피드백 개선
4. WebSocket 재연결 로직 추가

---

### 7. 12가지 가상매매 기법 중 9개 미작동 문제

**관련 파일**:
- `/virtual_trading/diverse_strategies.py` - 12가지 전략 구현
- `/virtual_trading/virtual_account.py` - 가상 계좌
- `/virtual_trading/data_enricher.py` - 데이터 보강

**12가지 전략 목록**:
1. ✅ MomentumStrategy (모멘텀 추세) - 작동
2. ✅ MeanReversionStrategy (평균회귀) - 작동
3. ✅ BreakoutStrategy (돌파 매매) - 작동
4. ❌ ValueInvestingStrategy (가치 투자) - 미작동
5. ❌ SwingTradingStrategy (스윙 매매) - 미작동
6. ❌ MACDStrategy - 미작동
7. ❌ ContrarianStrategy (역추세) - 미작동
8. ❌ SectorRotationStrategy (섹터 로테이션) - 미작동
9. ❌ HotStockStrategy (인기 종목) - 미작동
10. ❌ DividendGrowthStrategy (배당금 성장) - 미작동
11. ❌ InstitutionalFollowingStrategy (기관 추종) - 미작동
12. ❌ VolumeRSIStrategy (거래량-RSI 조합) - 미작동

**분석 결과**:
9개 전략이 작동하지 않는 주요 원인:

1. **데이터 부족**:
   - PER, PBR (가치 투자용)
   - MACD 지표
   - 섹터 정보
   - 배당 정보
   - 기관/외국인 매매 데이터

2. **조건 미충족**:
   - `should_buy()` 메서드의 조건이 너무 엄격
   - 실제 시장 데이터에서 조건을 만족하는 종목이 없음

3. **DataEnricher 미동작**:
   - 필수 데이터를 자동 생성해야 하는데 작동하지 않음

**권장 해결책**:
1. `data_enricher.py`의 데이터 보강 로직 강화
2. 각 전략의 `should_buy()` 조건 완화
3. 필수 데이터 수집 API 추가 (PER, PBR, 배당, 기관 매매 등)
4. 전략별 테스트 케이스 작성

**우선순위 전략 수정 순서**:
1. HotStockStrategy (거래량 데이터만 필요, 쉬움)
2. VolumeRSIStrategy (거래량 + RSI, 중간)
3. MACDStrategy (MACD 지표 추가 필요, 중간)
4. ValueInvestingStrategy (PER/PBR API 필요, 어려움)
5. InstitutionalFollowingStrategy (기관 매매 API 필요, 어려움)

---

### 8. 시장 트렌드 분석가 미동작 문제

**관련 파일**:
- `/ai/market_regime_classifier.py` - 시장 상태 분류기
- `/dashboard/routes/ai/market_commentary.py` - 시장 코멘터리 (이미 통합됨)

**분석 결과**:
시장 트렌드 분석가 기능은 실제로는 **이미 구현**되어 있습니다:
- `MarketRegimeClassifier` 클래스가 시장 상태를 BULL/BEAR/SIDEWAYS로 분류
- `market_commentary.py`에서 시장 트렌드를 분석하여 코멘터리 제공 (147-190번 라인)

**문제 원인**:
대시보드에서 별도의 "시장 트렌드 분석가" 섹션이 없거나, 데이터가 표시되지 않을 수 있음:

1. 시장 데이터가 장외 시간에는 수집되지 않음
2. Volume leaders나 gainers 데이터가 없으면 분석 불가
3. 프론트엔드에서 해당 데이터를 표시하는 UI가 누락됨

**권장 해결책**:
1. 대시보드에 "시장 트렌드 분석" 전용 섹션 추가
2. `/api/ai/market-commentary`의 `market_trend` 필드를 별도로 표시
3. 장외 시간에도 전일 데이터 기반 분석 제공
4. 시각화 차트 추가 (상승/하락 종목 비율 등)

---

### 9. AI 추천 종목 Top 5 기능 분석 및 개선

**현재 상태**:
사용자가 제공한 예시:
```
갱신
이노테크       F  ₩58,800  +300.00%  점수: 158/36%
싸이닉솔루션    F  ₩10,460  +29.94%   점수: 158/36%
잉글우드랩     F  ₩15,730  +19.89%   점수: 158/36%
모델솔루션     F  ₩19,520  +19.68%   점수: 146/33%
바이오솔루션    F  ₩9,490   +19.82%   점수: 122/28%
```

**문제점**:
1. **Grade "F"**: 모든 종목이 F 등급인데 Top 5로 추천되고 있음
2. **동일한 점수**: 상위 3개 종목이 모두 158점/36%로 동일 → 차별화 부족
3. **의미 불명확**: "AI 추천 종목"이 무엇을 기준으로 선정되는지 불분명
4. **실용성 의문**: F 등급 종목을 추천하는 것이 적절한가?

**분석 결과**:

**Grade 시스템**:
- 아마도 A ~ F 등급 (A가 최고, F가 최저)
- F 등급 종목만 표시되는 이유: 실제로 A~E 등급 종목이 없거나, 필터링 오류

**점수 시스템**:
- 총점: 158/440 (36%)
- 이는 매우 낮은 점수인데도 "추천"으로 표시됨
- 추천 기준이 너무 낮거나, 더 나은 종목이 없음

**권장 개선 방향**:

1. **추천 기준 재정의**:
   - F 등급 종목은 "주의 종목" 또는 "고위험 종목"으로 표시
   - 실제 추천은 B+ 이상 종목만 (60% 이상 점수)
   - 점수가 낮으면 "추천 종목 없음" 표시

2. **UI 개선**:
   ```
   ⚠️ 현재 추천 가능한 고품질 종목이 없습니다

   참고용 상위 종목 (주의 필요):
   - 이노테크 (F, 158점) - 고위험
   - 싸이닉솔루션 (F, 158점) - 고위험
   ```

3. **차별화 강화**:
   - 동일 점수 종목은 추가 지표로 순위 결정 (거래량, 변동성 등)
   - 각 종목별 특징 강조 ("거래량 급증", "돌파 시도" 등)

4. **기능 명칭 변경**:
   - "AI 추천 종목" → "AI 분석 상위 종목" 또는 "매매 검토 대상"
   - 추천이 아닌 "분석 결과"로 포지셔닝

**코드 수정 위치**:
- `/core/bot/scanner.py` - Top candidates 선별 로직 (158-183번 라인)
- `/dashboard/routes/system.py` - `/api/candidates` API
- `/dashboard/templates/dashboard_main.html` - UI 표시

---

### 10. AI 검토 프롬프트 개선

**현재 프롬프트** (사용자 제공):
```json
{
  "signal": "buy",
  "confidence_level": "High",
  "overall_score": 5.96,
  "reasons": [
    "대량 거래량과 함께 5.73% 상승하며 강력한 가격 모멘텀을 형성했습니다.",
    "매수 호가 강도(40/40)와 거래량 급증(60/60) 점수가 만점이며...",
    "단기적인 강한 매수세 유입과 시장의 관심 증가로 추가 상승 가능성..."
  ],
  "risks": [
    "기관 순매수가 0원이고 프로그램 매매 점수가 0점으로...",
    "단기 급등에 따른 차익 실현 매물이 출회될 경우...",
    "외국인 순매수 규모도 미미하여..."
  ]
}
```

**문제점**:
1. **너무 단순**: 3개 reasons + 3개 risks만으로는 심도있는 분석이 부족
2. **정량적 근거 부족**: "대량 거래량", "강한 매수세" 등 구체적 수치 없음
3. **리스크 평가 미흡**: 실제로 위험한 신호(기관/외국인 0원)인데 High confidence
4. **일관성 문제**: F 등급에 158점(36%)인데 "High confidence"는 모순

**개선 방향**:

#### 1. 프롬프트 구조 개선

**현재** (`STOCK_ANALYSIS_PROMPT_TEMPLATE_SIMPLE`):
- 단순한 JSON 출력
- 핵심 정보만 포함

**개선안**: 다층 분석 프롬프트
```
1. 정량적 분석 (Quantitative Analysis)
   - 기술적 지표: 점수별 해석 (거래량 60/60 → "극단적 거래량 급증")
   - 가격 행동: 구체적 수치 ("5.73% 상승, 일평균 대비 237%")
   - 스마트머니: 기관/외국인 매매 분석

2. 정성적 분석 (Qualitative Analysis)
   - 시장 맥락: 섹터 트렌드, 관련 뉴스
   - 심리 분석: 매수/매도 호가 불균형 해석

3. 리스크 평가 (Risk Assessment)
   - 단기 리스크 (1-3일): 차익 실현 압력
   - 중기 리스크 (1-2주): 기관 매수 부재
   - 장기 리스크 (1개월+): 펀더멘털 약세

4. 신뢰도 조정 (Confidence Calibration)
   - High: 80%+ 종합 점수, 기관+외국인 매수 증가
   - Medium: 60-80% 점수 또는 혼재된 신호
   - Low: 60% 미만 또는 강한 역풍 신호
```

#### 2. 프롬프트 예시

```python
ENHANCED_STOCK_ANALYSIS_PROMPT = """
당신은 20년 경력의 퀀트 헤지펀드 매니저입니다. 다음 종목을 분석해주세요.

## 종목 정보
- 종목명: {stock_name}
- 현재가: {current_price}원
- 종합 점수: {total_score}/440 ({percentage}%)

## 정량적 지표
{quantitative_scores}

## 요구사항
1. **정량적 분석** (30초):
   - 각 지표를 구체적 수치로 해석
   - 예: "거래량 60/60 = 일평균의 500% 급증"

2. **스마트머니 분석** (20초):
   - 기관/외국인/프로그램 매매 패턴
   - 매수 주체 분석 (개인 vs 기관 주도)

3. **리스크 계층화** (20초):
   - 단기 (1-3일): 기술적 조정 가능성
   - 중기 (1-2주): 추세 지속 여부
   - 장기 (1개월+): 펀더멘털 뒷받침

4. **신뢰도 재평가** (10초):
   - 종합 점수 60% 미만 → Low confidence
   - 기관/외국인 매수 부재 → confidence 하향
   - F 등급 종목 → "매우 높은 리스크" 명시

## 출력 형식
{{
  "signal": "buy/hold/sell",
  "confidence_level": "High/Medium/Low",
  "overall_score": float,
  "quantitative_analysis": {{
    "technical_score_interpretation": "...",
    "volume_analysis": "...",
    "price_momentum": "..."
  }},
  "smart_money_flow": {{
    "institutional_trend": "...",
    "foreign_trend": "...",
    "primary_buyer": "individual/institutional"
  }},
  "layered_risks": {{
    "short_term": ["..."],
    "medium_term": ["..."],
    "long_term": ["..."]
  }},
  "confidence_reasoning": "...",
  "final_recommendation": "..."
}}
"""
```

#### 3. 코드 수정 위치

**파일**: `/ai/gemini_analyzer.py`
- `STOCK_ANALYSIS_PROMPT_TEMPLATE_SIMPLE` (v6.1.1) 개선
- `STOCK_ANALYSIS_PROMPT_TEMPLATE_COMPLEX` (v6.1) 활용 확대

**추가 파일**: `/ai/unified_analyzer.py`
- `_build_advanced_prompt()` 메서드 강화

#### 4. 개선 효과 예측

**개선 전**:
```
✅ AI 결정: BUY
💡 사유: 대량 거래량과 함께 5.73% 상승...
(F 등급, 158점)
```

**개선 후**:
```
⚠️ AI 결정: HOLD (주의 필요)
📊 신뢰도: LOW (36% 종합 점수)
💡 정량 분석:
  - 거래량: 60/60 (일평균의 537% 급증) ✅
  - 가격 모멘텀: 5.73% 상승 (돌파 시도) ✅
  - 스마트머니: 기관 0원, 외국인 0원 ❌

⚠️ 주요 리스크:
  - 단기: 개인 주도 급등 → 차익 실현 압력 높음
  - 중기: 기관 매수 부재 → 상승 지속력 약함
  - 등급: F (하위 36%) → 고위험 종목

🎯 권장: 관망 또는 소량 분할 매수 (전체 자금의 1-2%)
```

---

## 🎯 우선순위 작업 제안

### 즉시 작업 (High Priority)
1. ✅ AI 확신도 게이지 수정 (완료)
2. ✅ 리스크 히트맵 개선 (완료)
3. 🔄 AI 추천 종목 기준 강화 (진행 필요)
4. 🔄 AI 검토 프롬프트 고도화 (진행 필요)

### 단기 작업 (Medium Priority)
5. 실시간 포지션 모니터링 디버깅
6. HotStockStrategy 활성화 (가장 쉬운 전략)
7. 시장 트렌드 분석가 UI 추가

### 중장기 작업 (Low Priority)
8. 나머지 8개 가상매매 전략 활성화
9. PER/PBR/배당 데이터 API 추가
10. 전략별 백테스팅 시스템 구축

---

## 📝 참고 사항

### 테스트 파일 실행 방법
```bash
# NXT 현재가 테스트
python tests/manual/test_nxt_price_multi_method.py

# 분봉 데이터 테스트
python tests/manual/test_minute_chart_multi_method.py
```

### 결과 파일 위치
- NXT 테스트: `/tests/manual/nxt_test_results_YYYYMMDD_HHMMSS.json`
- 분봉 테스트: `/tests/manual/minute_chart_test_results_YYYYMMDD_HHMMSS.json`

---

## 결론

총 10개의 문제 중:
- ✅ **5개 완료**: 테스트 파일 2개, 장외시간 분석, 확신도, 리스크 히트맵
- 📋 **5개 분석**: 포지션 모니터링, 가상매매, 트렌드 분석가, AI 추천, 프롬프트

나머지 문제들은 코드 수정이 필요하지만, 명확한 해결 방향이 제시되었습니다.
우선순위에 따라 순차적으로 진행하시기 바랍니다.
