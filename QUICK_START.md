# 🚀 AutoTrade Pro - Quick Start Guide

## ⚠️ 시작하기 전에

현재 다음과 같은 오류가 발생하고 있습니다:

```
❌ 로그인 실패 (코드 805004): 토큰 인증에 실패했습니다
```

**원인**: API 자격증명이 설정되지 않았습니다.

---

## 📋 1단계: API 자격증명 설정 (필수!)

### 방법 1: 자동 설정 스크립트 (권장)

Windows 명령 프롬프트에서:

```batch
setup_secrets.bat
```

또는 Python으로 직접:

```batch
python scripts\setup_secrets.py
```

### 방법 2: 수동 설정

1. **템플릿 파일 복사**
   ```batch
   copy _immutable\credentials\secrets.example.json _immutable\credentials\secrets.json
   ```

2. **텍스트 편집기로 `secrets.json` 열기**
   ```batch
   notepad _immutable\credentials\secrets.json
   ```

3. **다음 정보를 입력하세요**:

   ```json
   {
     "kiwoom_rest": {
       "base_url": "https://api.kiwoom.com",
       "appkey": "YOUR_KIWOOM_APPKEY_HERE",
       "secretkey": "YOUR_KIWOOM_SECRETKEY_HERE",
       "account_number": "12345678-01"
     },
     "kiwoom_websocket": {
       "url": "wss://api.kiwoom.com:10000/api/dostk/websocket"
     },
     "gemini": {
       "api_key": "YOUR_GEMINI_API_KEY_HERE",
       "model_name": "gemini-2.5-flash"
     },
     "telegram": {
       "bot_token": "",
       "chat_id": ""
     }
   }
   ```

### 필수 정보:

#### 1. **키움증권 API 키** (필수)
- 키움증권 Open API 사이트에서 발급받으세요
- `appkey`: 앱키
- `secretkey`: 시크릿키
- `account_number`: 계좌번호 (형식: `12345678-01`)
- `base_url`:
  - 실거래: `https://api.kiwoom.com`
  - 모의투자: `https://mockapi.kiwoom.com`

#### 2. **Google Gemini API 키** (AI 분석용, 권장)
- https://makersuite.google.com/app/apikey 에서 무료로 발급
- AI 기반 종목 분석 및 시장 예측에 사용됩니다

#### 3. **Telegram Bot** (선택사항)
- 실시간 거래 알림을 받으려면 설정하세요
- 설정하지 않아도 시스템은 정상 작동합니다

---

## 🎯 2단계: 시스템 시작

자격증명 설정 완료 후:

```batch
start_with_openapi.bat
```

이 스크립트는 다음을 자동으로 수행합니다:

1. ✅ **OpenAPI 서버 시작** (32비트, Kiwoom 연결)
2. ✅ **전략 최적화 엔진 시작** (백그라운드)
3. ✅ **메인 애플리케이션 시작** (실시간 매매)
4. ✅ **웹 대시보드 시작** (http://localhost:5000)

### ⚠️ 주의사항

- **Kiwoom 로그인 창**이 나타나면 반드시 로그인하세요
  - 작업 표시줄에 숨어있을 수 있습니다
  - Alt+Tab으로 찾을 수 있습니다
- 로그인하지 않으면 API가 작동하지 않습니다

---

## 🌐 3단계: 웹 대시보드 접속

브라우저에서:

```
http://localhost:5000
```

### 대시보드 기능:

- 📊 **실시간 계좌 현황** - 자산, 수익률, 보유 종목
- 🤖 **AI 분석** - Gemini 기반 종목 분석 및 매매 신호
- 📈 **백테스팅** - 12가지 전략 성과 비교
- 💼 **가상매매** - 전략별 독립 시뮬레이션
- ⚙️ **설정 관리** - 리스크 관리, 전략 파라미터

---

## 🔧 문제 해결

### 1. 한글이 깨져서 보입니다

✅ **이미 수정됨** - `start_with_openapi.bat`에 UTF-8 인코딩이 추가되었습니다.

### 2. "secrets.json 파일이 없습니다" 오류

```batch
setup_secrets.bat
```

위 스크립트를 실행하여 API 키를 설정하세요.

### 3. 백테스팅 결과가 비어있습니다 (0개 전략, 0회 거래)

**원인**: API 연결 실패 → 데이터를 가져올 수 없음

**해결방법**:
1. `secrets.json` 파일이 올바르게 설정되었는지 확인
2. 시스템을 재시작: `start_with_openapi.bat`
3. Kiwoom 로그인 창에서 로그인 완료

### 4. 가상매매 전략이 모두 0원, 0% 수익률

**원인**: 백테스팅과 동일 (API 연결 필요)

**해결방법**: 위 3번 참조

### 5. JavaScript 에러: "Cannot read properties of null"

✅ **이미 수정됨** - 대시보드가 이제 빈 데이터를 gracefully 처리합니다.

---

## 📚 추가 문서

- 📖 **전체 설정 가이드**: `README.md`
- 🔐 **API 키 관리**: `_immutable/credentials/README.md`
- 🏗️ **프로젝트 구조**: `docs/PROJECT_STRUCTURE.md`
- 🧪 **테스트 가이드**: `tests/README.md`

---

## 🆘 도움이 필요하신가요?

1. **로그 확인**:
   - 메인 로그: `logs/autotrade.log`
   - 전략 최적화: `logs/strategy_optimizer.log`

2. **시스템 진단**:
   ```batch
   python run_diagnostics.py
   ```

3. **API 키 재설정**:
   ```batch
   setup_secrets.bat
   ```

---

## 🎉 시작하기

1. ✅ `setup_secrets.bat` 실행
2. ✅ API 키 입력
3. ✅ `start_with_openapi.bat` 실행
4. ✅ Kiwoom 로그인
5. 🚀 http://localhost:5000 접속

**Happy Trading! 📈**
