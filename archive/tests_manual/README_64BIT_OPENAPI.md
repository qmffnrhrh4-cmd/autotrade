# 64비트 Kiwoom Open API 테스트 가이드

## 📋 목차
- [개요](#개요)
- [사전 준비](#사전-준비)
- [테스트 파일 설명](#테스트-파일-설명)
- [사용 방법](#사용-방법)
- [문제 해결](#문제-해결)

## 개요

이 디렉토리에는 64비트 Python 환경에서 Kiwoom Open API를 테스트하는 스크립트가 포함되어 있습니다.

**주요 기능:**
- 64비트 환경에서 Open API 로그인 테스트
- 과거 분봉 데이터 조회
- 단계별 디버깅

## 사전 준비

### 1. 64비트 Kiwoom Open API 설치

```bash
# 64비트 OCX 다운로드 및 설치
# https://github.com/teranum/64bit-kiwoom-openapi 참조
```

### 2. OCX 등록 (관리자 권한 필요)

```cmd
# C:\OpenAPI\register.bat 실행 (관리자 권한으로)
regsvr32 /u C:\OpenAPI\KHOpenAPI64.ocx
regsvr32 C:\OpenAPI\KHOpenAPI64.ocx
```

### 3. Python 환경 확인

```bash
# 64비트 Python인지 확인
python -c "import struct; print(struct.calcsize('P') * 8)"
# 출력: 64 (64비트 Python)

# pywin32 설치
pip install pywin32
```

### 4. 다른 Kiwoom 프로그램 종료

**중요:** Open API 테스트 전에 반드시 다음을 종료해야 합니다:
- 키움증권 HTS (영웅문)
- 다른 Open API 기반 프로그램
- 작업 관리자에서 `KH`로 시작하는 모든 프로세스

## 테스트 파일 설명

### 1. `test_64bit_openapi_debug.py` - 디버깅용 스크립트

**목적:** 로그인 실패 원인을 단계별로 진단

**확인 항목:**
1. Kiwoom 프로세스 실행 여부
2. OCX 등록 상태
3. COM 초기화
4. ActiveX 컨트롤 생성
5. 이벤트 핸들러 연결
6. CommConnect 호출

**사용법:**
```bash
python tests/manual/test_64bit_openapi_debug.py
```

### 2. `test_64bit_openapi_with_data.py` - 분봉 데이터 조회 테스트

**목적:** 로그인 성공 후 실제 과거 분봉 데이터 조회

**기능:**
- 자동 로그인 (이벤트 기반)
- 분봉 데이터 요청 (opt10080 TR)
- 데이터 파싱 및 출력
- 다양한 분봉 단위 지원 (1분, 3분, 5분, 10분 등)

**사용법:**
```bash
python tests/manual/test_64bit_openapi_with_data.py
```

## 사용 방법

### Step 1: 환경 확인

```bash
# 1. 64비트 Python 확인
python -c "import struct; print(struct.calcsize('P') * 8)"

# 2. pywin32 설치 확인
python -c "import win32com.client; print('OK')"
```

### Step 2: 디버깅 스크립트 실행

```bash
python tests/manual/test_64bit_openapi_debug.py
```

**예상 출력:**
```
✅ Kiwoom 관련 프로세스 없음
✅ ProgID 등록 확인
✅ COM 초기화 성공
✅ ActiveX 컨트롤 생성 성공
✅ 이벤트 핸들러 연결 성공
✅ CommConnect 호출 성공
```

로그인 창이 나타나면 ID/PW를 입력하세요.

### Step 3: 분봉 데이터 조회 테스트

```bash
python tests/manual/test_64bit_openapi_with_data.py
```

**기능:**
1. 자동으로 로그인 창 대기
2. 로그인 성공 후 삼성전자(005930) 1분봉 조회
3. 최근 20개 분봉 데이터 출력

**예상 출력:**
```
📈 분봉 데이터 (100개)
날짜         시각         현재가      시가        고가        저가        거래량
--------------------------------------------------------------------------------
20250107    153000      71500      71600      71700      71500        12345
20250107    152900      71600      71500      71650      71500        23456
...
```

## 문제 해결

### ❌ 오류 코드: 0x8000FFFF (E_UNEXPECTED)

**원인:**
1. 다른 Kiwoom 프로세스와 충돌 ⭐ (가장 흔함)
2. 32비트 프로세스가 64비트 OCX 호출
3. 로그인 서버 연결 실패
4. 방화벽/백신 프로그램 차단

**해결 방법:**

#### 1단계: 모든 Kiwoom 프로세스 종료
```cmd
# 작업 관리자에서 확인할 프로세스:
- KHOpenAPI.exe
- OpSysMsg.exe
- 영웅문 관련 프로세스
```

#### 2단계: Python 64비트 확인
```bash
python -c "import struct; print(struct.calcsize('P') * 8)"
# 반드시 "64" 출력되어야 함
```

#### 3단계: 관리자 권한으로 실행
```cmd
# 명령 프롬프트를 관리자 권한으로 실행 후
python tests/manual/test_64bit_openapi_debug.py
```

#### 4단계: 재부팅
위 방법들이 실패하면 PC를 재부팅하고 재시도

### ❌ OCX가 등록되지 않았습니다

**해결 방법:**
```cmd
# 관리자 권한으로 명령 프롬프트 실행
regsvr32 C:\OpenAPI\KHOpenAPI64.ocx
```

### ❌ 로그인 창이 나타나지 않습니다

**원인:**
- 메시지 루프가 제대로 실행되지 않음
- UI 스레드 블로킹

**해결 방법:**
`test_64bit_openapi_with_data.py` 사용 (별도 메시지 루프 스레드 포함)

### ❌ 분봉 데이터가 비어있습니다

**원인:**
1. 장 시간 외 조회 (데이터 없을 수 있음)
2. 종목코드 오류
3. TR 요청 간격 미준수 (최소 0.5초)

**해결 방법:**
```python
# 장 시간 확인
# 평일 09:00 ~ 15:30 (한국시간)

# 다른 종목 시도
stock_code = "005930"  # 삼성전자
# stock_code = "035720"  # 카카오
```

### ❌ TR 요청 실패 (ret != 0)

**오류 코드:**
- `-200`: 시세 과부하
- `-201`: 조회 제한 초과
- 기타: API 문서 참조

**해결 방법:**
- TR 요청 간격을 0.5초 이상으로 설정
- 조회 횟수 제한 확인

## 코드 예제

### 기본 로그인 및 분봉 조회

```python
from tests.manual.test_64bit_openapi_with_data import KiwoomAPI64

# API 초기화
api = KiwoomAPI64()
api.initialize()

# 로그인
if api.connect(timeout=60):
    # 삼성전자 1분봉 조회
    data = api.request_minute_candle("005930", "1")

    if data:
        api.print_candle_data(data, max_rows=20)

    api.disconnect()
```

### 여러 종목 조회

```python
import time

stocks = [
    ("005930", "삼성전자"),
    ("035720", "카카오"),
    ("000660", "SK하이닉스"),
]

for code, name in stocks:
    print(f"\n{name} ({code}) 조회 중...")
    data = api.request_minute_candle(code, "1")

    if data:
        api.print_candle_data(data, max_rows=10)

    # TR 요청 간격 (최소 0.5초)
    time.sleep(0.5)
```

## 참고 자료

- [64비트 Kiwoom Open API GitHub](https://github.com/teranum/64bit-kiwoom-openapi)
- [키움증권 Open API 가이드](https://www.kiwoom.com/h/customer/download/VOpenApiInfoView)
- TR 코드 목록:
  - `opt10080`: 주식 분봉 조회
  - `opt10081`: 주식 일봉 조회
  - `opt10001`: 주식 기본 정보 조회

## 라이센스

이 테스트 스크립트는 교육 및 개발 목적으로 제공됩니다.
키움증권 Open API 사용 시 키움증권의 이용약관을 준수해야 합니다.
