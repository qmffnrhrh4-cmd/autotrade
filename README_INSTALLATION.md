# 🛠️ AutoTrade Installation Guide

## 🎯 목표
**일반 CMD에서 `run.bat` 실행 → REST API + OpenAPI 동시 연결**

---

## 📋 요구사항

1. **Anaconda 3** (Python 3.10, 32-bit 환경)
2. **Windows OS** (키움 OpenAPI는 Windows 전용)
3. **키움증권 계좌** (실제 거래용)

---

## 🚀 설치 방법

### Option A: 원클릭 설치 (추천)

```cmd
# 1. Anaconda Prompt 열기
INSTALL_ANACONDA_PROMPT.bat

# 2. 일반 CMD 열기
SETUP_QUICK.bat

# 3. 검증
CHECK_SETUP.bat

# 4. 실행
run.bat
```

### Option B: 단계별 설치

**Step 1: Anaconda 환경 생성**
```cmd
# Anaconda Prompt에서
cd C:\Users\USER\Desktop\autotrade
INSTALL_ANACONDA_PROMPT.bat
```

이 스크립트가 생성하는 것:
- 환경 이름: `autotrade_32`
- Python: 3.10 (32-bit)
- 이유: 키움 OpenAPI는 32비트 ActiveX 전용

**Step 2: 패키지 설치**
```cmd
# Anaconda Prompt에서 (autotrade_32 환경에서)
install_core.bat
```

또는 수동:
```cmd
conda activate autotrade_32

# 32비트 호환 버전 사용!
pip install pydantic==2.5.3
pip install pandas==2.0.3
pip install numpy==1.24.3
pip install PyQt5 PyQt5-Qt5 PyQt5-sip
pip install protobuf==3.20.3 grpcio==1.50.0
pip install koapy pywin32
pip install Flask flask-socketio flask-cors
pip install requests urllib3
```

**Step 3: 검증**
```cmd
# 일반 CMD에서도 가능
CHECK_SETUP.bat
```

예상 출력:
```
[OK] Anaconda found
[OK] autotrade_32 environment activated
Python 3.10.x
Architecture: 32 bit

[OK] pydantic
[OK] pandas 2.0.3
[OK] numpy 1.24.3
[OK] PyQt5
[OK] koapy

All packages verified! Ready to run!
```

**Step 4: 실행**
```cmd
# 일반 CMD에서
run.bat
```

---

## 🔍 중요한 버전 제약

### 32비트 호환성

| 패키지 | 일반 버전 | 32비트 호환 버전 | 이유 |
|--------|----------|------------------|------|
| pandas | >=2.2.0 | ==2.0.3 | 2.2.0+ no 32-bit wheels |
| numpy | >=1.26.0 | ==1.24.3 | 1.26.0+ no 32-bit wheels |
| protobuf | latest | ==3.20.3 | koapy requires 3.20.x |
| grpcio | latest | ==1.50.0 | Compatible with protobuf 3.20 |

### 왜 requirements.txt로 설치 안 되나요?

`requirements.txt`는 64비트 환경을 위한 최신 버전 사용:
```
pandas>=2.2.0
numpy>=1.26.0
```

이 버전들은 **pre-built wheels이 32비트에 없어서** 소스 빌드 시도 → 실패

**해결:** `install_core.bat` 사용 (32비트 호환 버전)

---

## 🛠️ 설치 스크립트 설명

### INSTALL_ANACONDA_PROMPT.bat
- **언제**: 최초 1회 (환경 생성)
- **어디서**: Anaconda Prompt
- **무엇을**: autotrade_32 환경 생성 (Python 3.10 32-bit)

### SETUP_QUICK.bat
- **언제**: 최초 1회 또는 패키지 문제 발생 시
- **어디서**: 일반 CMD 또는 Anaconda Prompt
- **무엇을**: 전체 패키지 설치 (32비트 호환 버전)

### install_core.bat
- **언제**: 핵심 패키지만 재설치할 때
- **어디서**: Anaconda Prompt (autotrade_32 활성화 후)
- **무엇을**: pydantic, pandas, numpy, koapy 등 핵심 패키지

### REINSTALL_PACKAGES.bat
- **언제**: requirements.txt 기반 전체 재설치 (64비트 버전)
- **어디서**: Anaconda Prompt
- **무엇을**: 모든 패키지 (주의: pandas/numpy 빌드 실패 가능)

### CHECK_SETUP.bat
- **언제**: 설치 후 검증
- **어디서**: 일반 CMD 또는 Anaconda Prompt
- **무엇을**: 환경 및 패키지 확인

### run.bat
- **언제**: 매번 실행
- **어디서**: 일반 CMD (어디서든)
- **무엇을**: autotrade_32 활성화 + main.py 실행

---

## 🔧 문제 해결

### 1. "No module named 'pydantic'"

**원인:** 패키지 설치 실패 (pandas 빌드 에러로 인해 중단)

**해결:**
```cmd
SETUP_QUICK.bat
```

또는
```cmd
conda activate autotrade_32
install_core.bat
```

### 2. "metadata-generation-failed" (pandas)

**원인:** pandas>=2.2.0은 32비트 pre-built wheels 없음

**해결:** 32비트 호환 버전 사용
```cmd
pip install pandas==2.0.3 numpy==1.24.3
```

### 3. "No Qt bindings could be found"

**원인:** PyQt5 설치 안 됨

**해결:**
```cmd
pip install PyQt5 PyQt5-Qt5 PyQt5-sip
```

### 4. "Descriptors cannot be created directly"

**원인:** protobuf 4.x 설치됨 (koapy는 3.20.x 필요)

**해결:**
```cmd
pip install protobuf==3.20.3
```

### 5. "autotrade_32 environment not found"

**원인:** Anaconda 환경 미생성

**해결:**
```cmd
# Anaconda Prompt에서
INSTALL_ANACONDA_PROMPT.bat
```

### 6. "Anaconda not found" (run.bat)

**원인:** Anaconda 설치 경로가 표준 경로가 아님

**해결:**
1. Anaconda 설치 확인
2. run.bat 수정 - CONDA_PATH 경로 추가

### 7. OpenAPI 연결 실패

**증상:**
```
⚠️  OpenAPI 연결 실패 - 자동매매 기능 비활성화
   REST API로 시세 조회는 계속 가능합니다
```

**원인:**
- 32비트 환경이 아님
- koapy 설치 안 됨
- 키움증권 프로그램 미설치

**확인:**
```cmd
python -c "import struct; print('Architecture:', struct.calcsize('P')*8, 'bit')"
```

출력이 `Architecture: 32 bit`이어야 함

**해결:**
```cmd
conda activate autotrade_32  # 32비트 환경 사용
pip install koapy pywin32 PyQt5
```

---

## 📊 설치 확인 체크리스트

- [ ] Anaconda 설치됨
- [ ] autotrade_32 환경 생성됨
- [ ] Python 3.10 (32-bit) 확인
- [ ] 핵심 패키지 설치됨:
  - [ ] pydantic
  - [ ] pandas==2.0.3
  - [ ] numpy==1.24.3
  - [ ] PyQt5
  - [ ] protobuf==3.20.3
  - [ ] koapy
  - [ ] Flask
- [ ] CHECK_SETUP.bat 통과
- [ ] run.bat으로 실행 성공

---

## 🎓 추가 정보

### 환경 구조
- **autotrade_32** (32비트 Python 3.10): OpenAPI + REST API 실행 환경
- **autotrade_dev** (64비트 Python 3.13): 개발 환경 (선택 사항)

상세 정보: `README_ENVIRONMENTS.md`

### 빠른 시작
전체 워크플로우: `README_QUICKSTART.md`

---

## 🆘 여전히 안 되나요?

1. **전체 재설치:**
```cmd
# Anaconda Prompt
conda env remove -n autotrade_32
INSTALL_ANACONDA_PROMPT.bat
SETUP_QUICK.bat
```

2. **수동 확인:**
```cmd
conda activate autotrade_32
python --version  # Python 3.10.x
python -c "import struct; print(struct.calcsize('P')*8)"  # 32
pip list | findstr "pandas numpy koapy PyQt5"
```

3. **로그 확인:**
```cmd
python main.py
# 에러 메시지 전체 확인
```

---

**설치 완료 후 → `run.bat` 실행 → REST API + OpenAPI 동시 연결! 🚀**
