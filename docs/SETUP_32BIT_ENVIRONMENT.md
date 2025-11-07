# 🔧 32비트 Python 환경 설정 가이드

## 왜 32비트 환경이 필요한가?

키움증권 OpenAPI는 **32비트 ActiveX 컴포넌트**로만 제공됩니다:
- ✅ **OpenAPI (자동매매)**: 32비트 필수
- ✅ **REST API (시세조회)**: 64비트 가능

따라서 **32비트 Python 환경**을 만들어야 합니다!

---

## 📋 방법 1: Anaconda로 32비트 환경 생성 (권장)

### 1.1 Anaconda 32비트 버전 설치 여부 확인

```cmd
# 현재 Anaconda 비트 확인
python -c "import struct; print(f'{struct.calcsize(\"P\")*8}-bit')"
```

- **32-bit** 출력: 이미 32비트 환경 ✅
- **64-bit** 출력: 32비트 환경 생성 필요

### 1.2 32비트 Conda 환경 생성

```cmd
# 32비트 Python 3.11 환경 생성
set CONDA_FORCE_32BIT=1
conda create -n autotrade_32 python=3.11 --no-default-packages
conda activate autotrade_32

# 비트 확인
python -c "import struct; print(f'{struct.calcsize(\"P\")*8}-bit')"
```

**예상 출력:**
```
32-bit
```

### 1.3 의존성 설치

```cmd
cd C:\Users\USER\Desktop\autotrade

# 모든 패키지 설치
pip install -r requirements.txt

# 또는 핵심 패키지만 먼저 설치
pip install PyQt5 koapy protobuf==3.20.3 grpcio==1.50.0 pywin32
```

### 1.4 설치 확인

```cmd
python -c "from PyQt5.QtWidgets import QApplication; print('PyQt5 OK')"
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('koapy OK')"
```

---

## 📋 방법 2: 32비트 Python 직접 설치

### 2.1 Python 32비트 다운로드

1. https://www.python.org/downloads/ 접속
2. **Windows installer (32-bit)** 다운로드
3. 설치 시 **"Add Python to PATH"** 체크

### 2.2 가상환경 생성

```cmd
# C:\Python311-32 경로에 설치되었다고 가정
cd C:\Users\USER\Desktop\autotrade

# 32비트 Python으로 가상환경 생성
C:\Python311-32\python.exe -m venv venv_32bit

# 가상환경 활성화
venv_32bit\Scripts\activate

# 비트 확인
python -c "import struct; print(f'{struct.calcsize(\"P\")*8}-bit')"
```

### 2.3 의존성 설치

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 📋 방법 3: koapy 서버 모드 (권장 대안)

**64비트 Python을 계속 사용**하면서, koapy가 자동으로 **32비트 서버**를 시작하게 할 수 있습니다.

### 3.1 64비트 Python에서 koapy 설치

```cmd
pip install koapy protobuf==3.20.3 grpcio==1.50.0
```

### 3.2 32비트 서버 자동 시작 설정

koapy는 다음 방식으로 작동합니다:
1. **64비트 Python 클라이언트** (메인 프로그램)
2. **32비트 Python 서버** (OpenAPI 통신) - 자동 시작
3. **gRPC 통신** (클라이언트 ↔ 서버)

```python
from koapy import KiwoomOpenApiPlusEntrypoint

# 자동으로 32비트 서버를 시작합니다
with KiwoomOpenApiPlusEntrypoint() as context:
    context.EnsureConnected()
    accounts = context.GetAccountList()
    print(accounts)
```

**장점:**
- ✅ 64비트 Python 계속 사용 가능
- ✅ 32비트 서버는 koapy가 자동 관리
- ✅ gRPC로 프로세스 격리

**단점:**
- ⚠️ 32비트 Python이 시스템에 설치되어 있어야 함
- ⚠️ koapy 서버 설정 필요

---

## ✅ 설치 확인

### 테스트 1: Python 비트 확인

```cmd
python -c "import struct; print(f'Python: {struct.calcsize(\"P\")*8}-bit')"
```

### 테스트 2: PyQt5 확인

```cmd
python -c "from PyQt5.QtWidgets import QApplication; print('✅ PyQt5 OK')"
```

### 테스트 3: koapy 확인

```cmd
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('✅ koapy OK')"
```

### 테스트 4: 로그인 테스트

```cmd
python test_login.py
```

---

## 🔍 문제 해결

### 문제 1: "No Qt bindings could be found"

**원인:** PyQt5 미설치

**해결:**
```cmd
pip install PyQt5 PyQt5-Qt5 PyQt5-sip
```

### 문제 2: "No module named 'pydantic'"

**원인:** 의존성 미설치

**해결:**
```cmd
pip install -r requirements.txt
```

### 문제 3: koapy 서버 시작 실패

**원인:** 32비트 Python 미설치 또는 경로 문제

**해결:**
1. 32비트 Python을 시스템에 설치
2. `PATH`에 32비트 Python 경로 추가
3. koapy 설정 파일 확인:
   ```cmd
   # koapy 설정 확인
   python -m koapy config show
   ```

### 문제 4: protobuf 버전 충돌

**원인:** protobuf 4.x와 koapy 호환 안 됨

**해결:**
```cmd
pip uninstall protobuf
pip install protobuf==3.20.3
```

---

## 📌 권장 워크플로우

### 시나리오 A: 자동매매만 사용 (OpenAPI)
→ **32비트 Anaconda 환경** 사용 (방법 1)

### 시나리오 B: REST API + OpenAPI 모두 사용
→ **방법 3 (koapy 서버 모드)** 사용:
- 64비트 Python: REST API + 메인 로직
- 32비트 서버: OpenAPI 통신 (koapy 자동 관리)

### 시나리오 C: 개발 + 테스트
→ **방법 1 + 방법 2** 병행:
- 개발: 64비트 Python (Visual Studio Code, Jupyter 등)
- 실행: 32비트 환경으로 전환

---

## 🚀 빠른 시작 스크립트

### Windows Batch 스크립트 (setup_32bit.bat)

```batch
@echo off
echo ====================================
echo  32비트 Python 환경 설정
echo ====================================
echo.

REM Anaconda 환경 생성
set CONDA_FORCE_32BIT=1
conda create -n autotrade_32 python=3.11 -y
call conda activate autotrade_32

REM 비트 확인
python -c "import struct; print(f'✅ Python: {struct.calcsize(\"P\")*8}-bit')"

REM 의존성 설치
echo.
echo 의존성 설치 중...
pip install --upgrade pip
pip install -r requirements.txt

REM 설치 확인
echo.
echo ====================================
echo  설치 확인
echo ====================================
python -c "from PyQt5.QtWidgets import QApplication; print('✅ PyQt5')"
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('✅ koapy')"
python -c "from pydantic import BaseModel; print('✅ pydantic')"

echo.
echo ====================================
echo  설치 완료!
echo ====================================
echo.
echo 다음 단계:
echo   1. conda activate autotrade_32
echo   2. python test_login.py
echo.
pause
```

---

## 📚 참고 자료

- [koapy GitHub](https://github.com/elbakramer/koapy)
- [키움증권 OpenAPI 가이드](https://www.kiwoom.com/h/customer/download/VOpenApiInfoView)
- [PyQt5 문서](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [Anaconda 32비트 환경](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)

---

## 💡 추가 팁

### VSCode에서 32비트 환경 사용

1. **Ctrl+Shift+P** → "Python: Select Interpreter"
2. `autotrade_32` 환경 선택
3. 터미널 재시작

### 환경 전환 스크립트

**activate_32.bat:**
```batch
@echo off
conda activate autotrade_32
echo ✅ 32비트 환경 활성화됨
python -c "import struct; print(f'Python: {struct.calcsize(\"P\")*8}-bit')"
```

**activate_64.bat:**
```batch
@echo off
conda activate base
echo ✅ 64비트 환경 활성화됨
python -c "import struct; print(f'Python: {struct.calcsize(\"P\")*8}-bit')"
```

---

**작성일:** 2025-11-07
**버전:** v1.0
