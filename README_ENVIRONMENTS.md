# 🔧 AutoTrade 환경 가이드

## 📋 두 가지 환경 구조

AutoTrade는 두 가지 환경을 사용할 수 있습니다:

### 1. autotrade_32 (필수) - 실행 환경
```
환경 이름: autotrade_32
Python: 3.10 (32비트)
용도: AutoTrade 실행
필수 이유: OpenAPI (koapy)는 32비트 필수
```

**이 환경에서 실행:**
- ✅ `python main.py` (메인 프로그램)
- ✅ `python test_login.py` (로그인 테스트)
- ✅ OpenAPI 기반 자동매매
- ✅ REST API 시세 조회

### 2. autotrade_dev (선택) - 개발 환경
```
환경 이름: autotrade_dev
Python: 3.13 (64비트)
용도: 개발, 분석, 테스트
선택 사항: 필요시에만 생성
```

**이 환경에서 사용:**
- ✅ Jupyter Notebook/Lab
- ✅ 데이터 분석 (pandas, numpy)
- ✅ 코드 개발 및 테스트
- ✅ REST API 테스트 (OpenAPI 제외)

---

## 🚀 빠른 사용법

### AutoTrade 실행 (항상 32비트)

```cmd
# Anaconda Prompt에서
conda activate autotrade_32
python main.py
```

### 개발 작업 (선택적 64비트)

```cmd
# Anaconda Prompt에서
conda activate autotrade_dev
jupyter lab
```

---

## 📦 패키지 관리

### autotrade_32 패키지 재설치

```cmd
# Anaconda Prompt에서
cd C:\Users\USER\Desktop\autotrade
REINSTALL_PACKAGES.bat
```

또는 수동:
```cmd
conda activate autotrade_32
pip install -r requirements.txt
```

### autotrade_dev 환경 생성 (선택)

```cmd
# Anaconda Prompt에서
cd C:\Users\USER\Desktop\autotrade
CREATE_DEV_ENV.bat
```

---

## ⚠️ 중요한 규칙

### ❌ 절대 안 됨

```cmd
# autotrade_dev에서 main.py 실행 - 안 됨!
conda activate autotrade_dev
python main.py  # ❌ OpenAPI 작동 안 함!
```

### ✅ 올바른 방법

```cmd
# autotrade_32에서 main.py 실행 - 정상!
conda activate autotrade_32
python main.py  # ✅ 모든 기능 작동!
```

---

## 🔄 환경 전환

### 현재 환경 확인

```cmd
conda env list
```

출력 예시:
```
# conda environments:
#
base                     C:\Users\USER\anaconda3
autotrade_32          *  C:\Users\USER\anaconda3\envs\autotrade_32
autotrade_dev            C:\Users\USER\anaconda3\envs\autotrade_dev
```

`*` 표시가 현재 활성화된 환경입니다.

### 환경 전환 방법

```cmd
# 32비트 환경으로 전환 (실행용)
conda activate autotrade_32

# 64비트 환경으로 전환 (개발용)
conda activate autotrade_dev

# base 환경으로 복귀
conda activate base
```

---

## 💡 왜 두 환경이 필요한가?

### 문제: Python 비트 충돌

- **OpenAPI (키움증권)**: 32비트 ActiveX 전용
- **일반 개발 도구**: 64비트가 더 좋음

### 해결: 환경 분리

```
┌──────────────────────────────────────┐
│  autotrade_32 (32비트 Python 3.10)  │
│  ├─ OpenAPI (koapy) ✅              │
│  ├─ REST API ✅                     │
│  └─ main.py 실행 ✅                 │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  autotrade_dev (64비트 Python 3.13) │
│  ├─ Jupyter Notebook ✅             │
│  ├─ 데이터 분석 ✅                  │
│  └─ 코드 개발 ✅                    │
└──────────────────────────────────────┘
```

---

## 📊 환경별 패키지

### autotrade_32 (실행 환경)

**필수 패키지:**
- PyQt5 (koapy 의존성)
- koapy (OpenAPI)
- protobuf==3.20.3
- grpcio==1.50.0
- pydantic
- pandas, numpy
- 기타 requirements.txt 모든 패키지

**Python 버전:**
- 3.10 (32비트)

### autotrade_dev (개발 환경)

**개발 도구:**
- jupyter, jupyterlab
- ipython
- black, flake8, mypy
- pytest

**데이터 분석:**
- pandas, numpy
- matplotlib, seaborn, plotly
- scikit-learn

**Python 버전:**
- 3.13 (64비트)

---

## 🔧 문제 해결

### "ImportError: No module named 'XXX'"

**원인:** 잘못된 환경에서 실행

**해결:**
```cmd
# 현재 환경 확인
conda env list

# 올바른 환경으로 전환
conda activate autotrade_32

# 패키지 재설치
pip install -r requirements.txt
```

### "OpenAPI 연결 실패"

**원인:** 64비트 환경에서 실행

**해결:**
```cmd
# 반드시 32비트 환경 사용
conda activate autotrade_32
python main.py
```

### 패키지가 모두 사라짐

**해결:**
```cmd
conda activate autotrade_32
REINSTALL_PACKAGES.bat
```

---

## 📝 요약

| 작업 | 환경 | 명령어 |
|------|------|--------|
| **AutoTrade 실행** | autotrade_32 | `python main.py` |
| **로그인 테스트** | autotrade_32 | `python test_login.py` |
| **Jupyter 사용** | autotrade_dev | `jupyter lab` |
| **데이터 분석** | autotrade_dev | `python analyze.py` |
| **패키지 설치** | 해당 환경 | `pip install XXX` |

---

## ✅ 베스트 프랙티스

1. **실행은 항상 autotrade_32에서**
   ```cmd
   conda activate autotrade_32
   python main.py
   ```

2. **개발은 autotrade_dev에서 (선택)**
   ```cmd
   conda activate autotrade_dev
   jupyter lab
   ```

3. **환경 혼동 방지**
   - 터미널 제목에 환경 이름 확인
   - 명령어 실행 전 `conda env list` 확인

4. **패키지 관리**
   - requirements.txt 수정 시 두 환경 모두 업데이트
   - 정기적으로 패키지 버전 확인

---

**Happy Coding & Trading! 🚀📈**
