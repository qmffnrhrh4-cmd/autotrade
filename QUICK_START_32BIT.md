# 🚀 빠른 시작 가이드 - 32비트 환경 설정

## ⚠️ 중요: 왜 32비트가 필요한가?

**키움증권 OpenAPI는 32비트 전용입니다!**

- ✅ **자동매매 (OpenAPI)**: 32비트 Python 필수
- ✅ **시세조회 (REST API)**: 64비트 가능

---

## 🎯 원클릭 설정 (권장)

### 방법 1: 자동 설치 스크립트 (가장 쉬움)

1. **관리자 권한**으로 명령 프롬프트 열기
2. 프로젝트 폴더로 이동:
   ```cmd
   cd C:\Users\USER\Desktop\autotrade
   ```

3. **설치 스크립트 실행**:
   ```cmd
   setup_32bit.bat
   ```

4. 설치가 완료되면 **새 터미널 열기** 후:
   ```cmd
   activate_32.bat
   python test_login.py
   ```

**끝!** 🎉

---

## 📋 수동 설정 (고급 사용자)

### 1단계: 32비트 환경 생성

```cmd
set CONDA_FORCE_32BIT=1
conda create -n autotrade_32 python=3.11 -y
conda activate autotrade_32
```

### 2단계: 비트 확인

```cmd
python -c "import struct; print(f'{struct.calcsize(\"P\")*8}-bit')"
```

**출력:** `32-bit` ✅

### 3단계: 의존성 설치

```cmd
pip install --upgrade pip
pip install PyQt5 PyQt5-Qt5 PyQt5-sip
pip install protobuf==3.20.3 grpcio==1.50.0 koapy
pip install pywin32
pip install -r requirements.txt
```

### 4단계: 설치 확인

```cmd
python -c "from PyQt5.QtWidgets import QApplication; print('✅ PyQt5')"
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('✅ koapy')"
python -c "from pydantic import BaseModel; print('✅ pydantic')"
```

### 5단계: 로그인 테스트

```cmd
python test_login.py
```

---

## 🔧 현재 발생한 문제 해결

### 문제 1: "No Qt bindings could be found"

**원인:** PyQt5가 설치되지 않음

**해결:**
```cmd
conda activate autotrade_32
pip install PyQt5 PyQt5-Qt5 PyQt5-sip
```

### 문제 2: "No module named 'pydantic'"

**원인:** requirements.txt 패키지 미설치

**해결:**
```cmd
conda activate autotrade_32
pip install -r requirements.txt
```

### 문제 3: 64비트 환경에서 실행 중

**확인:**
```cmd
python -c "import struct; print(f'{struct.calcsize(\"P\")*8}-bit')"
```

**64-bit 출력 시:**
```cmd
# 32비트 환경으로 전환
conda activate autotrade_32
```

---

## 📌 환경 전환 치트시트

### 32비트 환경 활성화
```cmd
conda activate autotrade_32
# 또는
activate_32.bat
```

### 64비트 환경으로 복귀
```cmd
conda activate base
```

### 현재 환경 확인
```cmd
python -c "import struct; print(f'{struct.calcsize(\"P\")*8}-bit')"
conda env list
```

---

## 🎯 VSCode 설정

### Python 인터프리터 변경

1. **Ctrl+Shift+P** → "Python: Select Interpreter"
2. `Python 3.11.x ('autotrade_32')` 선택
3. 터미널 재시작

### settings.json 설정 (선택사항)

```json
{
    "python.defaultInterpreterPath": "C:/Users/USER/anaconda3/envs/autotrade_32/python.exe",
    "python.terminal.activateEnvironment": true
}
```

---

## 🧪 테스트

### 1. 비트 확인
```cmd
python -c "import struct; print(struct.calcsize('P') * 8, 'bit')"
```

### 2. Qt 바인딩 확인
```cmd
python -c "import os; os.environ['QT_API']='pyqt5'; from PyQt5.QtWidgets import QApplication; print('OK')"
```

### 3. koapy 확인
```cmd
python -c "from koapy import KiwoomOpenApiPlusEntrypoint; print('OK')"
```

### 4. 전체 테스트
```cmd
python test_login.py
```

---

## 🚨 자주 묻는 질문 (FAQ)

### Q1: 32비트 환경 생성이 안 되고 계속 64비트가 생성됩니다

**A:** Anaconda가 64비트로 설치되어 있으면 `CONDA_FORCE_32BIT` 옵션이 작동하지 않을 수 있습니다.

**해결책:**
1. **Python 32비트 직접 설치**: https://www.python.org/downloads/
2. 32비트 Python으로 가상환경 생성:
   ```cmd
   C:\Python311-32\python.exe -m venv venv_32bit
   venv_32bit\Scripts\activate
   ```

### Q2: koapy를 64비트 환경에서 쓸 수 없나요?

**A:** 가능합니다! koapy는 **서버 모드**를 지원합니다.

- **64비트 클라이언트** (메인 프로그램)
- **32비트 서버** (OpenAPI 통신) - koapy가 자동 실행
- **gRPC 통신**

하지만 시스템에 32비트 Python이 설치되어 있어야 합니다.

### Q3: 기존 64비트 환경은 어떻게 하나요?

**A:** 그대로 두세요! 두 환경을 병행 사용 가능합니다.

```cmd
# REST API 사용 시
conda activate base  # 64비트

# OpenAPI 사용 시
conda activate autotrade_32  # 32비트
```

### Q4: PyQt5 설치 시 에러가 발생합니다

**A:** 다음을 시도해보세요:

```cmd
# 방법 1: pip 업그레이드
python -m pip install --upgrade pip
pip install PyQt5

# 방법 2: conda로 설치
conda install pyqt -c conda-forge

# 방법 3: wheel 파일 직접 설치
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyqt5 에서 다운로드
pip install PyQt5‑5.15.10‑cp311‑cp311‑win32.whl
```

---

## 📚 더 자세한 정보

- **상세 가이드**: `docs/SETUP_32BIT_ENVIRONMENT.md`
- **koapy 문서**: https://github.com/elbakramer/koapy
- **키움 OpenAPI**: https://www.kiwoom.com/

---

## 💡 추천 워크플로우

### 개발 단계
```cmd
# 64비트 환경에서 개발 (IDE, Jupyter 사용)
conda activate base
code .  # VSCode 실행
```

### 실행 단계
```cmd
# 32비트 환경으로 전환 후 실행
conda activate autotrade_32
python main.py
```

### 테스트 단계
```cmd
# 32비트 환경에서 테스트
conda activate autotrade_32
python test_login.py
pytest tests/
```

---

**✅ 이제 시작할 준비가 되었습니다!**

다음 명령어로 로그인 테스트를 진행하세요:

```cmd
conda activate autotrade_32
python test_login.py
```

성공하면 이렇게 표시됩니다:
```
✅✅✅ 로그인 성공!
계좌 목록: ['1234567890', ...]
```

**Happy Trading! 🚀📈**
