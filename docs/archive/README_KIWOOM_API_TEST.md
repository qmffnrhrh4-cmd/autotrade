# 키움증권 Open API 64비트 통합 테스트 가이드

## 📌 개요

`test_kiwoom_openapi_comprehensive.py`는 64비트 Python 환경에서 키움증권 Open API를 완전히 활용할 수 있는 통합 테스트 파일입니다.

### 주요 특징

- ✅ **64비트 Python 완전 지원** - Python 3.11.9 (64비트)에서 테스트됨
- ✅ **최신 COM Threading Model** - RPC_E_CALL_REJECTED 오류 해결
- ✅ **자동 진단 기능** - 충돌 프로세스 자동 감지 및 제거
- ✅ **다양한 기능 통합** - 로그인, 시세조회, 과거데이터, 잔고, 실시간
- ✅ **재사용 가능한 클래스** - 다른 프로젝트에서 import하여 사용 가능
- ✅ **상세한 오류 처리** - 각 단계별 오류 원인 및 해결책 제시

## 🚀 빠른 시작

### 1. 사전 준비

#### (1) 64비트 Python 설치

```bash
# Python 버전 확인
python -c "import struct; print(struct.calcsize('P') * 8)"
# 출력: 64 (64비트 Python)
```

64비트가 아니면 [Python 공식 사이트](https://www.python.org/downloads/)에서 64비트 버전을 다운로드하세요.

#### (2) pywin32 설치

```bash
pip install pywin32
```

#### (3) 64비트 Kiwoom Open API 설치

- GitHub: [64bit-kiwoom-openapi](https://github.com/teranum/64bit-kiwoom-openapi)
- 다운로드 후 설치 파일 실행
- 관리자 권한으로 OCX 등록:

```cmd
# 명령 프롬프트를 관리자 권한으로 실행
regsvr32 C:\OpenApi\KHOpenAPI64.ocx
```

#### (4) 충돌 프로세스 종료

**중요**: 테스트 전에 반드시 모든 키움 프로그램을 종료하세요:

- 영웅문 (HTS)
- 다른 Open API 기반 프로그램
- 작업 관리자에서 `KH`로 시작하는 모든 프로세스

또는 자동으로 종료:

```bash
# 진단 도구 실행
python diagnose_kiwoom_64bit.py
```

### 2. 테스트 실행

```bash
python test_kiwoom_openapi_comprehensive.py
```

### 3. 로그인

- 테스트 실행 후 키움 로그인 창이 나타나면 ID/PW를 입력하세요
- 인증서 비밀번호도 입력하세요

## 📖 기능 설명

### KiwoomOpenAPI 클래스

#### 초기화

```python
from test_kiwoom_openapi_comprehensive import KiwoomOpenAPI

# 자동 진단 포함 (권장)
api = KiwoomOpenAPI(auto_diagnose=True)

# 자동 진단 비활성화
api = KiwoomOpenAPI(auto_diagnose=False)
```

#### 연결 및 로그인

```python
# ActiveX 연결
if api.connect():
    # 로그인 (60초 타임아웃)
    if api.login(timeout=60):
        print("로그인 성공!")

        # 계좌 리스트 확인
        accounts = api.get_account_list()
        print(f"보유 계좌: {accounts}")
```

#### 과거 데이터 조회

##### 1. 분봉 데이터

```python
# 삼성전자 1분봉 100개 조회
data = api.get_minute_candle(
    stock_code="005930",  # 삼성전자
    interval=1,           # 1분봉 (1, 3, 5, 10, 15, 30, 45, 60)
    count=100             # 100개
)

# 데이터 구조:
# [
#     {
#         'date': '2025010715300',  # YYYYMMDDHHmmss
#         'open': 71500,
#         'high': 71700,
#         'low': 71500,
#         'close': 71600,
#         'volume': 12345
#     },
#     ...
# ]

# CSV 저장
from test_kiwoom_openapi_comprehensive import save_to_csv
save_to_csv(data, "samsung_1min.csv")
```

##### 2. 일봉 데이터

```python
# 삼성전자 일봉 100개 조회
data = api.get_daily_candle(
    stock_code="005930",
    count=100,
    adjusted=True  # 수정주가 (True) 또는 원주가 (False)
)

# 데이터 구조: 분봉과 동일 (date는 'YYYYMMDD' 형식)
```

#### 종목 정보 조회

```python
# 삼성전자 기본 정보
info = api.get_stock_info("005930")

# 반환 데이터:
# {
#     '종목명': '삼성전자',
#     '현재가': 71600,
#     '전일대비': 500,
#     '등락률': 0.70,
#     '거래량': 12345678,
#     '시가': 71500,
#     '고가': 71900,
#     '저가': 71400
# }
```

#### 계좌 잔고 조회

```python
# 첫 번째 계좌의 잔고 조회
balance = api.get_balance()

# 또는 특정 계좌
balance = api.get_balance(account_no="8012345678")

# 반환 데이터:
# {
#     'data': [
#         {
#             '종목명': '삼성전자',
#             '보유수량': 10,
#             '매입가': 70000,
#             '현재가': 71600,
#             '평가손익': 16000,
#             '수익률': 2.29
#         },
#         ...
#     ],
#     'deposit': 1000000  # 예수금
# }

# 출력
print(f"예수금: {balance['deposit']:,}원")
for stock in balance['data']:
    print(f"{stock['종목명']}: {stock['보유수량']}주 "
          f"(수익률: {stock['수익률']:.2f}%)")
```

#### 실시간 시세 구독

```python
# 실시간 데이터 콜백 함수 정의
def my_realtime_callback(stock_code, realtype, realdata):
    """실시간 데이터 수신 시 호출됨"""
    print(f"[실시간] {stock_code} - {realtype}")
    # realdata에서 필요한 정보 추출

# 콜백 등록
api.add_realtime_callback(my_realtime_callback)

# 실시간 시세 구독
api.subscribe_realtime(
    screen_no="1000",
    stock_codes=["005930", "035720"],  # 삼성전자, 카카오
    fids=["10", "11", "12"],  # 10=현재가, 11=전일대비, 12=등락률
    realtype=0  # 0=추가, 1=신규
)

# 메시지 루프 (실시간 데이터 수신 위해 필요)
import pythoncom
while True:
    pythoncom.PumpWaitingMessages()
    time.sleep(0.01)

# 구독 해지
api.unsubscribe_realtime("1000")
```

#### 연결 종료

```python
api.disconnect()
```

## 🔧 고급 사용법

### 다른 프로젝트에서 import

```python
# my_trading_bot.py
from test_kiwoom_openapi_comprehensive import KiwoomOpenAPI
import time

# API 초기화
api = KiwoomOpenAPI(auto_diagnose=True)

# 연결 및 로그인
if api.connect() and api.login():
    # 매매 로직 구현
    while True:
        # 1. 삼성전자 현재 정보 조회
        info = api.get_stock_info("005930")
        current_price = info['현재가']

        # 2. 매매 전략 실행
        if current_price < 70000:
            print("매수 신호!")
            # TODO: 주문 API 구현

        # 3. 대기
        time.sleep(1)

        # 메시지 루프 처리 (중요!)
        import pythoncom
        pythoncom.PumpWaitingMessages()

    # 종료
    api.disconnect()
```

### 대량 데이터 수집

```python
# 여러 종목의 1년치 일봉 데이터 수집
stocks = {
    "005930": "삼성전자",
    "035720": "카카오",
    "000660": "SK하이닉스",
    "005380": "현대차",
    "051910": "LG화학"
}

all_data = {}

for code, name in stocks.items():
    print(f"\n{name} ({code}) 데이터 수집 중...")

    # 1년치 일봉 (약 250개)
    data = api.get_daily_candle(code, count=250)

    if data:
        all_data[code] = data
        save_to_csv(data, f"{name}_daily.csv")

    # API 제한 준수 (0.2초 대기)
    time.sleep(0.2)

print(f"\n✅ 총 {len(all_data)}개 종목 데이터 수집 완료!")
```

### 연속 조회 (1000개 이상)

```python
# 삼성전자 분봉 2000개 조회 (자동으로 연속 조회 처리)
data = api.get_minute_candle(
    stock_code="005930",
    interval=1,
    count=2000  # 자동으로 여러 번 요청하여 2000개 수집
)

print(f"총 {len(data)}개 데이터 수집 완료!")
```

## ⚠️ 문제 해결

### 1. 오류: 0x8000FFFF (E_UNEXPECTED)

**원인**: 다른 키움 프로세스와 충돌

**해결**:
```bash
# 방법 1: 진단 도구 사용
python diagnose_kiwoom_64bit.py

# 방법 2: 수동으로 프로세스 종료
taskkill /F /IM KHOpenAPI.exe
taskkill /F /IM KHOpenAPICtrl.exe
taskkill /F /IM OpSysMsg.exe

# 방법 3: PC 재부팅 (권장)
```

### 2. 오류: RPC_E_CALL_REJECTED (0x8001011F)

**원인**: COM threading model 문제

**해결**: 이미 이 스크립트에 적용됨 (`CoInitializeEx(COINIT_APARTMENTTHREADED)`)

### 3. OCX가 등록되지 않았습니다

**해결**:
```cmd
# 관리자 권한으로 명령 프롬프트 실행
regsvr32 C:\OpenApi\KHOpenAPI64.ocx
```

### 4. 로그인 창이 나타나지 않습니다

**원인**: 메시지 루프 문제

**해결**:
1. 모든 키움 프로세스 종료
2. Python 스크립트 재실행
3. PC 재부팅

### 5. 32비트 Python 오류

**해결**: 64비트 Python 설치
```bash
python -c "import struct; print(struct.calcsize('P') * 8)"
# 반드시 "64" 출력되어야 함
```

## 📊 API 제한 사항

### TR 요청 제한

- **초당 5건** 제한
- 이 스크립트는 자동으로 0.2초 대기 (초당 5건 준수)

### 연속 조회 제한

- 한 번에 최대 약 900개 데이터 수신
- 더 많은 데이터가 필요하면 연속 조회 사용 (자동 처리됨)

### 실시간 시세 제한

- 한 화면당 최대 100종목
- 총 200종목까지 등록 가능

## 🎯 TR 코드 참고

### 시세 조회

- `opt10001`: 주식 기본 정보
- `opt10080`: 주식 분봉 조회
- `opt10081`: 주식 일봉 조회
- `opt10082`: 주식 주봉 조회
- `opt10083`: 주식 월봉 조회

### 계좌 조회

- `opw00001`: 예수금상세현황요청
- `opw00018`: 계좌평가잔고내역요청
- `opt10075`: 미체결요청
- `opt10076`: 체결내역조회

### 주문

- 주문 관련 API는 신중하게 사용해야 하므로 별도 구현 필요

## 💡 다음 단계

### 1. 자동매매 봇 개발

```python
# trading_bot.py
from test_kiwoom_openapi_comprehensive import KiwoomOpenAPI

class TradingBot:
    def __init__(self):
        self.api = KiwoomOpenAPI(auto_diagnose=True)

    def run(self):
        if self.api.connect() and self.api.login():
            # 매매 전략 구현
            pass
```

### 2. 데이터베이스 연동

```python
import sqlite3

# 분봉 데이터를 SQLite에 저장
conn = sqlite3.connect('stock_data.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS minute_candle (
    stock_code TEXT,
    date TEXT,
    open INTEGER,
    high INTEGER,
    low INTEGER,
    close INTEGER,
    volume INTEGER,
    PRIMARY KEY (stock_code, date)
)
''')

for item in data:
    cursor.execute('''
    INSERT OR REPLACE INTO minute_candle VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ("005930", item['date'], item['open'], item['high'],
          item['low'], item['close'], item['volume']))

conn.commit()
```

### 3. 백테스팅 시스템

과거 데이터를 활용하여 매매 전략을 백테스팅하세요.

### 4. 실시간 알림

특정 조건 충족 시 Slack, Discord, Email 등으로 알림 발송

## 📚 참고 자료

- [키움증권 Open API 가이드](https://www.kiwoom.com/h/customer/download/VOpenApiInfoView)
- [64bit-kiwoom-openapi GitHub](https://github.com/teranum/64bit-kiwoom-openapi)
- [pywin32 문서](https://github.com/mhammond/pywin32)

## ⚖️ 라이센스 및 주의사항

- 이 코드는 교육 및 개발 목적으로 제공됩니다
- 키움증권 Open API 이용약관을 준수하세요
- 실전 투자 시 충분한 테스트 후 사용하세요
- 투자 손실에 대한 책임은 사용자에게 있습니다

## 📞 지원

문제가 발생하면:

1. `diagnose_kiwoom_64bit.py` 실행
2. 이 문서의 "문제 해결" 섹션 참고
3. GitHub Issues 등록

---

**Happy Trading! 📈**
