# 🚀 AutoTrade - 시작 가이드

축하합니다! 설치가 완료되었습니다! 🎉

---

## ✅ 설치 확인

로그인 테스트가 성공했다면 모든 준비가 끝났습니다!

```
✅✅✅ 로그인 성공!
계좌 목록: ['6452323210']
✅ 계좌 조회 성공: 1개 계좌
```

---

## 🎯 메인 프로그램 실행

### Anaconda Prompt에서:

```cmd
conda activate autotrade_32
cd C:\Users\USER\Desktop\autotrade
python main.py
```

### 또는 RUN_MAIN.bat 사용:

**Anaconda Prompt에서 실행:**
```cmd
cd C:\Users\USER\Desktop\autotrade
RUN_MAIN.bat
```

---

## 📊 대시보드 접속

프로그램이 시작되면:

```
✓ 웹 대시보드 시작 완료
  → http://localhost:5000
```

**브라우저에서 접속:**
```
http://localhost:5000
```

---

## 🔧 main.py가 자동으로 하는 일

프로그램이 시작되면 자동으로:

1. **REST API 연결** (시세 조회용 - 64비트) ✅
2. **OpenAPI 연결** (자동매매용 - 32비트) ✅
3. **WebSocket 연결** (실시간 데이터 수신) ✅
4. **대시보드 시작** (http://localhost:5000) ✅
5. **자동매매 봇 시작** ✅

모든 것이 자동으로 연결됩니다!

---

## 📋 실행 로그 예시

```
================================================================
AutoTrade Pro v2.0
================================================================

1. 트레이딩 봇 초기화 중...
🌐 REST API 클라이언트 초기화 중...
✓ REST API 클라이언트 초기화 완료

🔧 OpenAPI 클라이언트 초기화 중...
📡 OpenAPI 서버 연결 중...
   (32비트 서버가 자동으로 시작됩니다)
🔐 자동 로그인 시도 중...
✅ OpenAPI 로그인 성공!
✅ OpenAPI 클라이언트 초기화 완료
   계좌 목록: ['6452323210']

✓ 트레이딩 봇 초기화 완료

2. 웹 대시보드 시작 중...
✓ 웹 대시보드 시작 완료
  → http://localhost:5000

3. 자동매매 봇 시작...
```

---

## 🔍 주요 기능

### 1. REST API (시세 조회)
- 실시간 시세 조회
- 차트 데이터 조회
- 시장 정보 조회
- **64비트 환경에서 작동**

### 2. OpenAPI (자동매매)
- 자동 로그인
- 주문 실행 (매수/매도)
- 계좌 조회
- 체결 내역 조회
- **32비트 환경에서 작동**

### 3. 웹 대시보드
- 실시간 모니터링
- 포트폴리오 현황
- 매매 내역 확인
- AI 분석 결과
- **브라우저에서 접속**

---

## 💡 사용 팁

### 매번 실행할 때

**Anaconda Prompt 열고:**
```cmd
conda activate autotrade_32
cd C:\Users\USER\Desktop\autotrade
python main.py
```

### 바탕화면 바로가기 만들기

1. 바탕화면에 텍스트 파일 생성: `AutoTrade.bat`
2. 다음 내용 입력:
```batch
@echo off
call C:\Users\USER\anaconda3\Scripts\activate.bat autotrade_32
cd C:\Users\USER\Desktop\autotrade
python main.py
pause
```
3. 저장 후 더블클릭으로 실행!

---

## ❓ 문제 해결

### "OpenAPI 초기화 실패"

**원인:** 32비트 환경이 아니거나 koapy 미설치

**해결:**
```cmd
conda activate autotrade_32
pip install koapy PyQt5 protobuf==3.20.3
```

### "Environment not found"

**해결:**
```cmd
# Anaconda Prompt에서
INSTALL_ANACONDA_PROMPT.bat
```

### 대시보드가 안 열림

**해결:**
- 브라우저에서 `http://localhost:5000` 직접 입력
- 포트 5000이 이미 사용 중인지 확인
- 프로그램 재시작

---

## 📚 다음 단계

1. ✅ **설정 확인**: `config/` 폴더에서 설정 파일 확인
2. ✅ **전략 설정**: 원하는 매매 전략 선택
3. ✅ **모니터링**: 대시보드에서 실시간 확인
4. ✅ **자동매매 시작**: 봇이 자동으로 매매 실행

---

## 🎉 완료!

이제 AutoTrade가 다음을 자동으로 수행합니다:

- ✅ REST API로 시세 조회
- ✅ OpenAPI로 자동 주문 실행
- ✅ 대시보드에서 모니터링
- ✅ AI 분석으로 종목 선정

**Happy Trading! 🚀📈**

---

## 📞 도움

문제가 생기면:
1. 로그 확인: 터미널 출력 메시지
2. 설정 확인: `config/` 폴더
3. 테스트: `python test_login.py`

**성공적인 자동매매 되세요!** 💪
