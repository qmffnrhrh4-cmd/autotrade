# koapy Windows 설치 및 실행 가이드

## ⚠️ 중요사항

**키움 Open API는 Windows 전용입니다!**
- Linux/Mac에서는 실행 불가
- 반드시 Windows 환경에서 테스트해야 합니다

---

## 🔧 설치 단계 (Windows에서 실행)

### 1단계: Python 환경 확인

```cmd
# Python 버전 확인 (64비트 권장)
python --version
python -c "import struct; print(f'{struct.calcsize(\"P\") * 8}-bit')"
```

### 2단계: 올바른 버전의 패키지 설치

**중요**: 반드시 이 순서대로 설치해야 합니다!

```cmd
# 1. protobuf와 grpcio 먼저 설치
pip install protobuf==3.20.3 grpcio==1.50.0

# 2. koapy를 --no-deps로 설치 (버전 업그레이드 방지)
pip install --no-deps koapy

# 3. 필요한 의존성 수동 설치
pip install PyQt5 pandas numpy requests beautifulsoup4 lxml
pip install python-dateutil pytz tzlocal wrapt rx
pip install Click jsonlines korean-lunar-calendar openpyxl pendulum
pip install pyhocon PySide2 qtpy schedule Send2Trash SQLAlchemy tabulate tqdm

# 4. protobuf와 grpcio가 업그레이드되었는지 확인 후 다시 설치
pip install --force-reinstall protobuf==3.20.3 grpcio==1.50.0
```

### 3단계: PyQt5 패치 적용

```cmd
# 패치 스크립트 실행
python patch_koapy.py
```

### 4단계: 설치 확인

```cmd
# koapy 진단 도구 실행
python check_koapy_installation.py
```

---

## 🚀 실행 방법

### 방법 1: 간단한 테스트 (권장)

```cmd
python tests\manual\test_koapy_simple.py
```

**기능:**
- koapy 기본 연결 테스트
- 수동 로그인 (로그인창 표시)
- 계좌 정보 조회

### 방법 2: 고급 기능 테스트

```cmd
python tests\manual\test_koapy_advanced.py
```

**기능:**
- 주식 기본 정보 조회 (삼성전자 예제)
- 일별 주가 데이터 조회
- 계좌 정보 및 잔고 조회
- 조건 검색식 사용
- Low-level TR 호출

### 방법 3: CLI 사용

```cmd
# 터미널 1: 서버 시작
python -m koapy.cli serve

# 터미널 2: 클라이언트 명령
python -m koapy.cli login
python -m koapy.cli get balance
python -m koapy.cli get orders
```

---

## 📝 올바른 API 사용법

### ✅ 정확한 방법 (test_koapy_advanced.py 참고)

```python
from koapy import KiwoomOpenApiPlusEntrypoint

with KiwoomOpenApiPlusEntrypoint() as context:
    # 로그인
    context.EnsureConnected()

    # 주식 기본 정보 조회
    info = context.GetStockBasicInfoAsDict('005930')  # 삼성전자

    # 종목명 조회
    name = context.GetMasterCodeName('005930')

    # 현재가 조회
    price = context.GetMasterLastPrice('005930')

    # 일별 주가 데이터
    df = context.GetDailyStockDataAsDataFrame(
        '005930',
        adjusted_price=True  # 수정주가
    )

    # 계좌 목록
    accounts = context.GetAccountList()

    print(f"종목명: {name}")
    print(f"현재가: {price:,}원")
    print(f"계좌: {accounts}")
```

### ❌ 잘못된 방법 (사용하지 마세요)

```python
# 이런 방식은 작동하지 않습니다!
event = context.api.OnReceiveTrData.wait()  # ❌ AttributeError
```

---

## 🔍 문제 해결

### 문제 1: "koapy가 설치되지 않았습니다"

```cmd
pip show koapy
# 버전: 0.3.5 이상이어야 함
```

### 문제 2: protobuf 버전 오류

```cmd
pip show protobuf | findstr Version
# 반드시 3.20.3이어야 함

# 다시 설치
pip install --force-reinstall protobuf==3.20.3 grpcio==1.50.0
```

### 문제 3: QTimer.singleShot 타입 오류

```cmd
# 패치 재실행
python patch_koapy.py
```

### 문제 4: ImportError: cannot import name 'SIGNAL'

이 오류는 Python 3.11과 koapy 0.3.5의 호환성 문제입니다.
- 패치를 적용하고 의존성을 수동으로 설치하면 해결됩니다

---

## 📦 최종 버전 확인

올바르게 설치되었다면:

```cmd
pip show protobuf grpcio koapy
```

**출력 예시:**
```
Name: protobuf
Version: 3.20.3

Name: grpcio
Version: 1.50.0

Name: koapy
Version: 0.3.5
```

---

## 💡 추가 참고사항

### 자동 로그인 설정 (선택사항)

`test_koapy_simple.py` 파일을 열어서 credential 설정:

```python
credential = {
    'user_id': 'your_id',
    'user_password': 'your_password',
    'cert_password': 'cert_password',
    'is_simulation': True,  # 모의투자
}
```

### 모의투자 vs 실전투자

```python
# 모의투자 (기본값, 안전)
context.EnsureConnected({'is_simulation': True})

# 실전투자 (주의!)
context.EnsureConnected({'is_simulation': False})
```

---

## 🎯 요약

1. **Windows에서만 실행 가능**
2. protobuf==3.20.3, grpcio==1.50.0 필수
3. koapy는 --no-deps로 설치
4. 패치 스크립트 실행 (patch_koapy.py)
5. 기존 테스트 파일 사용 (test_koapy_advanced.py)

---

## 📚 참고 문서

- koapy 공식: https://github.com/elbakramer/koapy
- AutomaticPosting-koapy: https://github.com/meteormin/AutomaticPosting-koapy
- 키움증권 Open API+: https://www3.kiwoom.com/nkw.templateFrameSet.do?m=m1408000000

---

**작성일**: 2025-11-07
**버전**: koapy 0.3.5, protobuf 3.20.3, grpcio 1.50.0
