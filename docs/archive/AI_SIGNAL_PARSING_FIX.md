# AI 신호 파싱 문제 해결 보고서

## 문제 상황

```
AI 분석 최종 실패 (3회 시도): '\n "signal"'
❌ AI 분석 최종 실패: '\n "signal"'
```

모든 종목 분석에서 AI가 계속 동작하지 않는 문제 발생.

## 원인 분석

### 1. JSON 파싱 자체는 정상 작동
- `test_json_parsing_simple.py` 테스트 결과: 모든 파싱 전략 100% 성공
- 문제는 파싱 로직이 아님

### 2. 실제 원인: Gemini API 응답 문제
1. **프롬프트가 너무 복잡함**
   - 기존: 276줄의 매우 복잡한 프롬프트 (STOCK_ANALYSIS_PROMPT_TEMPLATE)
   - 복잡한 중첩 JSON 스키마 요구
   - Gemini가 올바른 JSON 생성에 실패

2. **응답 검증 부족**
   - 빈 응답이나 null 체크 없음
   - 에러 메시지가 불명확함

3. **디버깅 정보 부족**
   - 실제 API 응답 내용을 로깅하지 않음
   - 에러 발생 시 원인 파악 어려움

## 해결 방안

### 1. 간소화된 프롬프트 도입 (v6.1.1)

**기존**: 복잡한 프롬프트 (276줄, 중첩된 JSON 스키마)
```python
STOCK_ANALYSIS_PROMPT_TEMPLATE  # 실패율 높음
```

**개선**: 간단하고 명확한 프롬프트 (58줄)
```python
STOCK_ANALYSIS_PROMPT_TEMPLATE_SIMPLE  # 신뢰성 높음
```

#### 개선된 프롬프트의 특징
- ✅ 간단한 JSON 구조 (6개 필드만 요구)
- ✅ 명확한 형식 지시
- ✅ "반드시 JSON으로만 응답하세요" 명시
- ✅ 예제 포함

### 2. 강화된 응답 검증

```python
# 응답 텍스트 검증 추가
if not hasattr(response, 'text'):
    raise ValueError("Gemini API response has no 'text' attribute")

response_text = response.text
if not response_text or len(response_text.strip()) == 0:
    raise ValueError("Gemini API returned empty response")

# 응답 길이 로깅
logger.debug(f"Gemini 응답 길이: {len(response_text)} chars")
```

### 3. 상세한 에러 로깅

```python
# JSON 파싱 에러 시 상세 정보 제공
except json.JSONDecodeError as e:
    logger.warning(f"JSON 파싱 실패 (위치: {e.pos}, 메시지: {e.msg})")
    if json_str:
        error_context = json_str[max(0, e.pos-50):min(len(json_str), e.pos+50)]
        logger.warning(f"에러 컨텍스트: ...{error_context}...")
        logger.warning(f"JSON 문자열 샘플 (처음 200자): {json_str[:200]}")
```

### 4. 응답 미리보기 로깅

```python
# 파싱 전에 응답 내용 확인 가능
preview_len = min(300, len(response_text))
logger.debug(f"응답 미리보기 ({preview_len}/{len(response_text)} chars): {response_text[:preview_len]}")
```

## 변경 파일

### 1. `ai/gemini_analyzer.py` (주요 변경)
- ✅ `STOCK_ANALYSIS_PROMPT_TEMPLATE_SIMPLE` 추가
- ✅ 응답 검증 로직 강화
- ✅ 에러 로깅 상세화
- ✅ 디버깅 정보 추가

### 2. `test_ai_signal_parsing.py` (신규 생성)
- 다양한 프롬프트 전략 테스트
- 다양한 파싱 전략 테스트
- 여러 Gemini 모델 테스트
- 성공 조건 자동 탐색

### 3. `test_json_parsing_simple.py` (신규 생성)
- API 키 없이 파싱 로직 테스트
- 10가지 테스트 케이스
- 3가지 파싱 전략 비교

## 테스트 방법

### 방법 1: JSON 파싱 테스트 (API 키 불필요)
```bash
python test_json_parsing_simple.py
```

결과: 모든 전략 10/10 성공

### 방법 2: 실제 AI 분석 테스트 (API 키 필요)
```bash
# API 키 설정
export GEMINI_API_KEY='your-key'

# 빠른 테스트 (4개 조합)
python test_ai_signal_parsing.py
# 선택: 1

# 종합 테스트 (모든 조합)
python test_ai_signal_parsing.py
# 선택: 2
```

### 방법 3: 메인 프로그램 실행
```bash
python main.py
```

이제 AI 분석이 성공적으로 작동해야 합니다.

## 예상 결과

### 성공 시 로그
```
✅ AI 결정: BUY
💡 사유: [분석 이유들]
신뢰도: High
```

### 실패 시 로그 (개선됨)
```
⚠️ AI 응답 지연 또는 에러 (시도 1/3), 2초 후 재시도...
디버깅 정보:
  - Gemini 응답 길이: 150 chars
  - 응답 미리보기: {...}
  - JSON 파싱 실패 (위치: 45, 메시지: Expecting ',' delimiter)
  - 에러 컨텍스트: ..."signal": "buy",  "co...
```

## 추가 개선 사항

### 만약 여전히 실패한다면

1. **로그 확인**
   ```bash
   tail -f logs/ai_analyzer.log  # 로그 파일 위치 확인
   ```

2. **다른 Gemini 모델 시도**
   ```python
   # config.py 또는 초기화 시
   model_name = 'gemini-1.5-flash'  # 또는 'gemini-1.5-pro'
   ```

3. **더 간단한 프롬프트 사용**
   - 필요시 STOCK_ANALYSIS_PROMPT_TEMPLATE_SIMPLE을 더 간소화

4. **Fallback to Mock Analyzer**
   - AI 실패 시 점수 기반 판단으로 대체
   - 이미 코드에 구현되어 있음

## 핵심 교훈

1. **간단함이 최고**: 복잡한 프롬프트 < 간단하고 명확한 프롬프트
2. **검증이 중요**: API 응답 검증 필수
3. **로깅이 생명**: 디버깅을 위한 상세한 로깅
4. **테스트 주도**: API 키 없이도 로직 테스트 가능하게

## 버전 정보

- **v6.1.0**: 복잡한 프롬프트 (실패율 높음)
- **v6.1.1**: 간소화된 프롬프트 + 강화된 검증 (현재 버전)

## 문의사항

문제가 지속되면 다음 정보를 포함하여 보고:
1. 로그 파일 내용 (특히 "응답 미리보기" 부분)
2. Gemini 모델 버전
3. 실패한 종목 정보
