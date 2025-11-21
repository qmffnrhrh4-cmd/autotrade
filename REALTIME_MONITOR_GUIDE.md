# 실시간 활동 모니터 사용 가이드

## 🎯 개요

실시간 활동 모니터는 AutoTrade Pro의 **모든 거래 활동을 실시간으로 확인**할 수 있는 대시보드입니다.

## 🚀 빠른 시작

### 1. 가상매매 전략 초기화

```bash
# Windows
init_virtual_trading.bat

# Linux/Mac
python scripts/init_virtual_trading_strategies.py
```

이 명령어는 **12개의 다양한 거래 전략**을 자동으로 생성합니다:
- 모멘텀 추세 전략
- 평균 회귀 전략
- 돌파 매매 전략
- 가치 투자 전략
- 스윙 트레이딩 전략
- MACD 크로스오버 전략
- 역발상 전략
- 섹터 로테이션 전략
- 급등주 추격 전략
- 배당 성장주 전략
- 기관 추종 전략
- 거래량 + RSI 복합 전략

### 2. 시스템 시작

```bash
start_with_openapi.bat
```

또는 개별 실행:

```bash
# 1. 대시보드만 시작
python dashboard/app.py

# 2. 가상매매 포함 전체 시스템
python main.py --virtual-trading
```

### 3. 대시보드 접속

브라우저에서 다음 URL을 엽니다:

| 대시보드 | URL | 설명 |
|---------|-----|------|
| 메인 대시보드 | http://localhost:5000 | 전체 시스템 현황 |
| **실시간 모니터** | http://localhost:5000/live-monitor | 실시간 거래 활동 |
| 진화 대시보드 | http://localhost:5000/evolution | 전략 진화 현황 |

---

## 📊 실시간 모니터 화면 구성

### 상단 통계

| 지표 | 설명 |
|-----|------|
| 활성 전략 | 현재 작동 중인 전략 개수 |
| 오늘 거래 | 오늘 실행된 총 거래 횟수 |
| 보유 포지션 | 현재 보유 중인 종목 개수 |
| 오늘 수익 | 오늘 발생한 총 손익 |

### 제어판

| 버튼 | 기능 |
|-----|------|
| 모든 전략 시작 | 모든 가상매매 전략 활성화 |
| 일시 정지 | 모든 전략 일시 정지 |
| 모두 중지 | 모든 전략 중지 |
| 로그 지우기 | 화면의 로그 초기화 |
| 새로고침 | 통계 수동 갱신 |

### 3개 패널

#### 1. 활성 전략 현황 (왼쪽)
- 현재 작동 중인 전략 목록
- 각 전략의 상태 (분석 중, 보유 중 등)
- 실시간 수익률

#### 2. 실시간 로그 (중앙)
- 시스템의 모든 활동을 실시간으로 표시
- 로그 종류:
  - 🔵 **INFO** (파란색): 일반 정보
  - 🟢 **SUCCESS** (초록색): 성공 메시지
  - 🟡 **WARNING** (노란색): 경고
  - 🔴 **ERROR** (빨간색): 오류
  - 🟣 **TRADE** (보라색): 거래 체결

#### 3. 최근 거래 (오른쪽)
- 최근 20개 거래 내역
- 매수/매도 구분
- 종목명, 수량, 가격, 손익

---

## 🔄 실시간 업데이트

### WebSocket 실시간 연결

모니터는 **WebSocket**을 통해 실시간으로 업데이트됩니다:

- ✅ 거래 체결 즉시 알림
- ✅ 전략 상태 변경 즉시 반영
- ✅ 시스템 로그 실시간 표시
- ✅ 통계 5초마다 자동 갱신

---

## 📝 로그 메시지 예시

```
[14:23:15] [시스템] 실시간 모니터링이 시작되었습니다.
[14:23:18] [전략] 모멘텀추세: 삼성전자 분석 중...
[14:23:20] [거래] 매수 삼성전자 10주 @ 70,000원
[14:25:30] [전략] 모멘텀추세: 익절 조건 충족 (수익률 +5.2%)
[14:25:32] [거래] 매도 삼성전자 10주 @ 73,600원
[14:25:32] [시스템] 수익 +36,000원 실현
```

---

## 🎮 주요 기능

### 1. 전략 제어

```javascript
// 모든 전략 시작
POST /api/virtual-trading/start-all

// 응답:
{
  "success": true,
  "activated_count": 12,
  "total_strategies": 12,
  "message": "12개 전략이 활성화되었습니다"
}
```

### 2. 실시간 통계

자동으로 5초마다 갱신:
- 활성 전략 수
- 총 거래 횟수
- 보유 포지션 수
- 총 손익

### 3. 거래 내역

최근 20개 거래를 실시간으로 표시:
- 매수/매도 구분 (빨간색/파란색 배지)
- 종목명
- 체결 가격 및 수량
- 손익 (매도 시)

---

## 🔧 문제 해결

### 전략이 보이지 않는 경우

```bash
# 1. 데이터베이스 초기화
python scripts/init_databases.py

# 2. 전략 초기화
python scripts/init_virtual_trading_strategies.py

# 3. 대시보드 재시작
# Ctrl+C로 종료 후
python dashboard/app.py
```

### 로그가 표시되지 않는 경우

1. 브라우저 F12 (개발자 도구) 열기
2. Console 탭에서 WebSocket 연결 확인
3. 오류 메시지 확인

```javascript
// Console에 표시되어야 하는 메시지:
Connected to AutoTrade Pro
```

### 거래가 실행되지 않는 경우

1. **시장 시간 확인**: 가상매매도 시장 시간에만 작동
2. **전략 조건 확인**: 각 전략의 매수 조건이 매우 엄격함
3. **API 연결 확인**: Kiwoom OpenAPI 연결 상태 확인

```bash
# API 연결 확인
python run_diagnostics.py
```

---

## 📈 성능 지표

### 자동 갱신 주기

| 항목 | 갱신 주기 |
|-----|----------|
| 실시간 로그 | 즉시 (WebSocket) |
| 거래 알림 | 즉시 (WebSocket) |
| 통계 | 5초 |
| 전략 상태 | 5초 |
| 거래 내역 | 5초 |

---

## 🎯 사용 시나리오

### 시나리오 1: 하루 동안 모니터링

```bash
# 1. 아침에 시스템 시작
start_with_openapi.bat

# 2. 브라우저에서 실시간 모니터 열기
http://localhost:5000/live-monitor

# 3. "모든 전략 시작" 클릭

# 4. 하루 종일 실시간으로 거래 내역 확인

# 5. 장 마감 후 통계 확인
```

### 시나리오 2: 특정 전략만 테스트

```python
# Python으로 직접 제어
from virtual_trading import VirtualTradingManager

manager = VirtualTradingManager()

# 전략 ID 1번만 활성화
manager.activate_strategy(1)

# 대시보드에서 확인
# http://localhost:5000/live-monitor
```

---

## 🚀 다음 단계

1. ✅ 가상매매 전략 초기화
2. ✅ 실시간 모니터 확인
3. ⏩ 진화 알고리즘 시작
4. ⏩ 전략 성과 분석
5. ⏩ 최적 전략 실전 투자 전환

---

## 📞 지원

문제가 발생하면:
1. `logs/` 디렉토리의 로그 파일 확인
2. GitHub Issues: https://github.com/qmffnrhrh4-cmd/autotrade/issues
3. 시스템 진단: `python run_diagnostics.py`

---

**Happy Trading! 📈💰**
