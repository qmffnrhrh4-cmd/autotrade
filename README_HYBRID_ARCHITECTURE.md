# 🔀 Hybrid Architecture Guide

## 📐 아키텍처 개요

AutoTrade는 **하이브리드 아키텍처**를 사용합니다:

```
start.bat 실행 (명령어 1개)
    ↓
    ├─ [숨김] 32-bit Anaconda: openapi_server.py (포트 5001)
    │   └─ koapy → 키움 OpenAPI 연결
    │   └─ Flask HTTP API 제공
    │
    └─ [보임] 64-bit Python 3.13: main.py (포트 5000)
        ├─ REST API (주문, 시세, 계좌)
        ├─ OpenAPI HTTP Client (포트 5001로 요청)
        ├─ 전략 엔진
        └─ 웹 대시보드
```

## 🎯 왜 하이브리드?

### 문제:
- **REST API**: 64비트/32비트 둘 다 작동 ✅
- **OpenAPI**: 32비트만 작동 (ActiveX) ❌
- **최신 라이브러리들**: 64비트가 더 좋음 ✅

### 해결:
1. **64비트 환경**: main.py + 모든 최신 라이브러리 사용
2. **32비트 환경**: OpenAPI 서버만 실행 (백그라운드)
3. **HTTP 통신**: 두 환경 간 통신

## 🚀 사용법

### 명령어 1개로 시작:

```cmd
start.bat
```

이 명령어가 자동으로:
1. ✅ 32비트 환경에서 OpenAPI 서버 시작 (숨김)
2. ✅ 64비트 환경에서 main.py 시작 (보임)
3. ✅ main.py 종료 시 OpenAPI 서버도 함께 종료

### 실행 화면:

```
================================================================
 AutoTrade Hybrid Launcher
================================================================

Starting AutoTrade with hybrid architecture:
  [Hidden]  32-bit: OpenAPI server (port 5001)
  [Visible] 64-bit: Main application (port 5000)

[OK] Anaconda found: C:\Users\USER\anaconda3
[OK] autotrade_32 environment found

[1/2] Starting OpenAPI server (32-bit, hidden)...
[OK] OpenAPI server starting in background (32-bit)...
    - Server URL: http://localhost:5001
    - Running in autotrade_32 environment

Waiting for OpenAPI server to initialize...

[2/2] Starting main application (64-bit)...

Python 3.13.x

================================================================
 Running main.py
================================================================

AutoTrade Pro v2.0
...
```

## 📁 파일 구조

### 새로 추가된 파일:

```
autotrade/
├── start.bat                    # ⭐ 메인 런처 (명령어 1개)
├── openapi_server.py            # 32비트 OpenAPI 서버
│
├── core/
│   └── openapi_client.py        # HTTP 클라이언트 (수정됨)
│
└── main.py                      # 64비트 메인 앱 (cleanup 추가)
```

## 🔧 각 컴포넌트 설명

### 1. start.bat (런처)

**역할**: 두 프로세스를 시작하는 마스터 스크립트

**동작**:
1. Anaconda 경로 자동 탐지
2. autotrade_32 환경 확인
3. VBS 스크립트로 OpenAPI 서버를 숨김 실행
4. 64비트 Python으로 main.py 실행
5. main.py 종료 시 OpenAPI 서버에 shutdown 요청

### 2. openapi_server.py (32비트)

**역할**: OpenAPI 전용 HTTP 서버

**포트**: 5001

**API 엔드포인트**:
- `GET  /health` - 상태 확인
- `POST /connect` - OpenAPI 연결
- `GET  /accounts` - 계좌 목록
- `GET  /balance/<account_no>` - 잔고 조회
- `POST /order` - 주문 실행
- `GET  /realtime/price/<code>` - 실시간 시세
- `POST /shutdown` - 서버 종료

**실행 환경**:
- Python 3.10 (32-bit)
- Anaconda autotrade_32 환경
- koapy, PyQt5, protobuf 3.20.3

### 3. core/openapi_client.py (HTTP 클라이언트)

**역할**: main.py에서 OpenAPI 서버와 통신

**변경 사항**:
- ❌ 기존: koapy 직접 사용 (32비트 필수)
- ✅ 신규: HTTP 요청으로 OpenAPI 서버와 통신 (64비트 OK)

**사용법**:
```python
from core import get_openapi_client

# 자동으로 localhost:5001에 연결
client = get_openapi_client(auto_connect=True)

# 계좌 조회
accounts = client.get_account_list()

# 주문
client.buy_market_order("005930", 10)
```

### 4. main.py (64비트)

**역할**: 메인 애플리케이션

**변경 사항**:
- `finally` 블록 추가
- 종료 시 `bot.openapi_client.shutdown_server()` 호출
- OpenAPI 서버 자동 종료

## 🔄 통신 흐름

### 예시: 주문 실행

```
사용자 → 웹 대시보드 (port 5000)
    ↓
main.py (64-bit)
    ↓
bot.openapi_client.buy_market_order()
    ↓ HTTP POST
openapi_server.py (32-bit, port 5001)
    ↓
koapy.BuyStockAtMarketPrice()
    ↓
키움 OpenAPI (32-bit ActiveX)
    ↓
키움증권 서버
```

## ⚙️ 설정

### OpenAPI 서버 URL 변경

`core/openapi_client.py`:
```python
client = KiwoomOpenAPIClient(
    server_url="http://127.0.0.1:5001",  # 기본값
    auto_connect=True
)
```

### OpenAPI 서버 포트 변경

`openapi_server.py`:
```python
app.run(
    host='127.0.0.1',
    port=5001,  # 여기 변경
    debug=False
)
```

## 🐛 문제 해결

### "OpenAPI 서버 연결 실패"

**증상**:
```
❌ OpenAPI 서버 연결 실패: http://127.0.0.1:5001/health
   서버가 실행 중인지 확인하세요 (openapi_server.py)
```

**원인**: OpenAPI 서버가 시작 안 됨

**해결**:
1. start.bat 사용 (자동 시작)
2. 또는 수동으로:
   ```cmd
   # Anaconda Prompt
   conda activate autotrade_32
   python openapi_server.py
   ```

### "autotrade_32 environment not found"

**원인**: 32비트 환경 미생성

**해결**:
```cmd
INSTALL_ANACONDA_PROMPT.bat
```

### OpenAPI 서버가 안 보임

**정상입니다!** OpenAPI 서버는 백그라운드로 숨김 실행됩니다.

확인 방법:
```cmd
# 작업 관리자 → 프로세스 → python.exe (autotrade_32)
# 또는
curl http://localhost:5001/health
```

### main.py 종료 시 OpenAPI 서버가 안 꺼짐

**원인**: cleanup 코드 실패

**해결**:
수동으로 종료:
```cmd
curl -X POST http://localhost:5001/shutdown
```

또는 작업 관리자에서 python.exe 프로세스 종료

## 📊 장점

✅ **64비트 환경 활용**
- 최신 라이브러리 사용 가능
- 더 많은 메모리
- 더 빠른 성능

✅ **32비트 최소화**
- OpenAPI만 32비트에서 실행
- 나머지는 모두 64비트

✅ **깔끔한 분리**
- 마이크로서비스 구조
- OpenAPI 문제가 main.py에 영향 안 줌

✅ **사용 편의성**
- 명령어 1개로 모든 것 시작
- 자동 cleanup

## 🔐 보안

- OpenAPI 서버는 **localhost만** 접속 가능 (`127.0.0.1`)
- 외부 네트워크에서 접근 불가
- main.py와 같은 머신에서만 통신

## 📝 요약

| 항목 | 기존 | 하이브리드 |
|------|------|------------|
| 실행 환경 | 32비트 전체 | 64비트 + 32비트 서버 |
| 라이브러리 제약 | 32비트만 | 64비트 최신 버전 |
| 실행 방법 | run.bat | **start.bat** |
| OpenAPI | koapy 직접 | HTTP 통신 |
| 복잡도 | 낮음 | 중간 |
| 성능 | 보통 | **향상** |
| 확장성 | 제한적 | **높음** |

---

**Happy Trading with Hybrid Power! 🚀📈**
