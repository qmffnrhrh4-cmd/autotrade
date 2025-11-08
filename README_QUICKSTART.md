# 🚀 AutoTrade Quick Start Guide

## 한 줄 요약
**일반 CMD에서 `run.bat` 실행하면 끝!**

---

## 📋 설치 (처음 한 번만)

### 방법 1: 자동 설치 (추천)

```cmd
# 일반 CMD에서:
SETUP_QUICK.bat
```

이 스크립트가 자동으로:
- ✅ autotrade_32 환경 확인
- ✅ 32비트 호환 패키지 설치 (pandas, numpy, koapy 등)
- ✅ 설치 검증

---

### 방법 2: 수동 설치

**1단계: 환경 생성 (Anaconda Prompt에서)**
```cmd
INSTALL_ANACONDA_PROMPT.bat
```

**2단계: 패키지 설치 (Anaconda Prompt에서)**
```cmd
install_core.bat
```

---

## ▶️ 실행 (매번)

### 방법 1: 일반 CMD에서 (추천)

```cmd
run.bat
```

### 방법 2: 직접 실행

```cmd
python main.py
```

### 방법 3: Anaconda Prompt에서

```cmd
conda activate autotrade_32
python main.py
```

---

## ✅ 설치 확인

```cmd
CHECK_SETUP.bat
```

이 스크립트가 다음을 검증:
- [OK] Anaconda 설치
- [OK] autotrade_32 환경
- [OK] Python 3.10 (32-bit)
- [OK] 필수 패키지 (pydantic, pandas, numpy, PyQt5, koapy 등)

---

## 🔧 문제 해결

### "ModuleNotFoundError: No module named 'pydantic'"

**해결:**
```cmd
SETUP_QUICK.bat
```

### "pandas build error" 또는 설치 실패

**원인:** requirements.txt의 pandas/numpy 버전이 32비트와 호환 안 됨

**해결:**
```cmd
install_core.bat
```
이 스크립트는 32비트 호환 버전 사용:
- pandas==2.0.3 (2.2.0 대신)
- numpy==1.24.3 (1.26.0 대신)

### "autotrade_32 environment not found"

**해결:**
```cmd
# Anaconda Prompt에서:
INSTALL_ANACONDA_PROMPT.bat
```

### "Anaconda not found" (run.bat 실행 시)

**해결:**
1. Anaconda가 설치되어 있는지 확인
2. 설치 경로가 다음 중 하나인지 확인:
   - `%USERPROFILE%\anaconda3`
   - `%USERPROFILE%\Anaconda3`
   - `C:\ProgramData\Anaconda3`
   - `C:\ProgramData\anaconda3`

---

## 📦 설치되는 패키지

### 핵심 패키지
- **pydantic**: 타입 안전 설정 관리
- **pandas**: 데이터 처리
- **numpy**: 수치 계산
- **requests**: HTTP 통신
- **Flask**: 웹 대시보드

### OpenAPI 관련
- **PyQt5**: Qt 바인딩 (koapy 의존성)
- **protobuf==3.20.3**: Protocol Buffers (koapy 필수)
- **grpcio==1.50.0**: gRPC (koapy 통신)
- **koapy**: 키움 OpenAPI+ wrapper
- **pywin32**: Windows COM/ActiveX

---

## 💡 작동 원리

### run.bat가 하는 일:
1. Anaconda 찾기 (여러 경로 시도)
2. autotrade_32 환경 활성화
3. python main.py 실행

### main.py가 하는 일:
1. REST API 클라이언트 초기화
2. OpenAPI 클라이언트 초기화 및 자동 로그인 ✨
3. 웹 대시보드 시작 (http://localhost:5000)

**OpenAPI 자동 로그인 코드는 이미 main.py에 구현되어 있음!** (lines 204-222)

---

## 🎯 실행 예시

```cmd
C:\Users\USER\Desktop\autotrade> run.bat

Found Anaconda at: C:\Users\USER\anaconda3
Activating autotrade_32 environment...

🚀 AutoTrade 시작!
🔧 REST API 클라이언트 초기화 중...
✅ REST API 클라이언트 초기화 완료

🔧 OpenAPI 클라이언트 초기화 중...
키움 OpenAPI 서버 연결 중...
✅✅✅ 로그인 성공!
   계좌 목록: ['6452323210']
✅ OpenAPI 클라이언트 초기화 완료

📊 웹 대시보드 시작...
✅ 대시보드: http://localhost:5000
```

---

## 📊 두 가지 API 역할

### REST API (주요)
- ✅ 시세 조회
- ✅ 주문 실행
- ✅ 계좌 정보
- ✅ 체결 내역

### OpenAPI (보조)
- ✅ 자동 로그인
- ✅ 실시간 시세 (TR)
- ✅ 추가 데이터 조회

**하이브리드 구조:** REST API 기반 + OpenAPI 보조

---

## 📁 파일 구조

```
autotrade/
├── run.bat                      # ⭐ 여기서 시작!
├── SETUP_QUICK.bat              # 전체 설치
├── CHECK_SETUP.bat              # 설치 확인
│
├── INSTALL_ANACONDA_PROMPT.bat  # 환경 생성
├── install_core.bat             # 패키지 설치
│
├── main.py                      # 메인 프로그램
├── requirements.txt             # 전체 패키지 목록
│
└── core/
    ├── rest_client.py           # REST API
    ├── openapi_client.py        # OpenAPI wrapper
    └── ...
```

---

## ✅ 체크리스트

- [ ] Anaconda 설치됨
- [ ] SETUP_QUICK.bat 실행 완료
- [ ] CHECK_SETUP.bat 통과
- [ ] run.bat으로 실행 성공
- [ ] REST API 연결 확인
- [ ] OpenAPI 로그인 확인
- [ ] 대시보드 접속 (http://localhost:5000)

---

## 🆘 추가 도움말

### 전체 패키지 재설치
```cmd
REINSTALL_PACKAGES.bat
```

### 개발 환경 (64-bit, Jupyter)
```cmd
CREATE_DEV_ENV.bat
```

### 환경 정보
README_ENVIRONMENTS.md 참고

---

**Happy Trading! 📈🚀**
