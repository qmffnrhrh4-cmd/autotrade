# AutoTrade Pro v2.0 🚀

**Kiwoom API + Gemini AI 기반 자동매매 봇**

[![Version](https://img.shields.io/badge/version-2.0-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

---

## 🎯 빠른 시작

### ⚡ 원클릭 설치 (권장)

```bash
python setup_kiwoom32.py
```

이 스크립트가 자동으로:
- ✅ **32비트 Python 환경 생성** (kiwoom32)
- ✅ **필수 패키지 설치** (breadum/kiwoom, PyQt5, pandas<2.0, flask 등)
- ✅ **OpenAPI+ 설치 확인**
- ✅ **환경 검증**

### 📦 OpenAPI+ 설치 (최초 1회)

OpenAPI+ 모듈을 설치하지 않았다면:

```bash
python install_kiwoom_openapi.py
```

이 스크립트가:
- OpenAPI+ 모듈 다운로드 및 설치
- KOA Studio 설치
- COM 등록 자동 처리

---

## 🚀 실행 방법

### 1. 메인 봇 실행 (64비트 Python)

```bash
python main.py
```

**자동으로 수행되는 작업:**
- kiwoom32 환경 자동 탐지
- OpenAPI 서버 자동 시작 (32비트)
- 로그인 창 표시
- 로그인 완료 후 자동매매 시작

### 2. OpenAPI 서버만 실행 (32비트 Python)

```bash
conda activate kiwoom32
python openapi_server.py
```

---

## 📋 수동 설치 (고급 사용자)

### 1. 32비트 Python 환경 생성

**⚠️ 중요: 키움 OpenAPI는 32비트 전용입니다!**

```bash
conda create -n kiwoom32 -y
conda activate kiwoom32
conda config --env --set subdir win-32
conda install python=3.9 -y
```

### 2. Python 패키지 설치

```bash
pip install "PyQt5==5.15.10" "pandas<2.0" numpy requests flask flask-cors kiwoom
```

### 2. API 키 설정

`config/credentials.py` 파일 편집:

```python
# Kiwoom API (필수)
KIWOOM_API_KEY = "your-kiwoom-api-key"
KIWOOM_API_SECRET = "your-kiwoom-api-secret"
KIWOOM_ACCOUNT_NO = "your-account-number"

# Gemini API (AI 분석용)
GEMINI_API_KEY = "your-gemini-api-key"
```

---

## 🎯 주요 기능

### 1. 자동 매매 🤖
- Gemini AI 기반 종목 분석
- 모멘텀 전략 자동 실행
- 자동 매수/매도 신호

### 2. 대시보드 📊
- **계좌 정보**: 총 자산, 현금, 평가금액, 손익
- **보유 종목**: 실시간 현황 및 수익률
- **매매 통계**: 총 거래, 승률, AI 분석 수
- **제어 패널**: 시작/정지/매수중지/매수재개

### 3. 리스크 관리 🛡️
- 손절/익절 자동 실행
- 포지션 크기 관리
- 일일 손실 제한
- 연속 손실 모니터링

---

## 🖥️ 대시보드 화면

### 표시 정보:
- 💰 총 자산
- 💵 보유 현금 (예수금)
- 📊 평가 금액
- 📈 총 손익 (금액 & %)
- 🎯 보유 종목 수 / 최대 포지션
- 📋 보유 종목 상세 (종목명, 수량, 매수가, 현재가, 손익)

### 제어 버튼:
- ▶️ **시작**: 봇 시작
- ⏹️ **정지**: 봇 정지
- ⏸️ **매수 중지**: 매수만 중지 (매도는 유지)
- ▶️ **매수 재개**: 매수 재개
- 🔄 **새로고침**: 수동 새로고침

**자동 새로고침**: 10초마다 자동 업데이트

---

## ⚙️ 설정

### control.json (실시간 설정)

봇 실행 중에도 `control.json` 파일을 수정하면 즉시 반영:

```json
{
  "run": true,
  "pause_buy": false,
  "pause_sell": false,
  "max_positions": 5,
  "risk_per_trade": 0.20,
  "take_profit": 0.10,
  "stop_loss": -0.05
}
```

### config/trading_params.py

전략 파라미터 설정:

```python
MAX_OPEN_POSITIONS = 5
RISK_PER_TRADE_RATIO = 0.20
TAKE_PROFIT_RATIO = 0.10
STOP_LOSS_RATIO = -0.05

FILTER_MIN_PRICE = 1000
FILTER_MAX_PRICE = 100000
FILTER_MIN_VOLUME = 100000
```

---

## 📂 프로젝트 구조

```
autotrade/
├── main.py                  ← 메인 실행 파일
├── control.json             ← 실시간 제어 설정
│
├── api/                     ← Kiwoom API
│   ├── account.py           # 계좌 조회
│   ├── market.py            # 시장 데이터
│   └── order.py             # 주문 실행
│
├── strategy/                ← 매매 전략
│   ├── momentum_strategy.py # 모멘텀 전략
│   ├── risk_manager.py      # 리스크 관리
│   └── portfolio_manager.py # 포트폴리오 관리
│
├── ai/                      ← AI 분석
│   └── gemini_analyzer.py   # Gemini AI
│
├── dashboard/               ← 웹 대시보드
│   └── dashboard.py         # Flask 대시보드
│
├── config/                  ← 설정
│   ├── credentials.py       # API 키
│   └── trading_params.py    # 매매 파라미터
│
└── logs/                    ← 로그
    └── trading_bot.log
```

---

## ❓ 문제 해결

### Q: 계좌 정보가 0원으로 표시됨
```
✓ config/credentials.py에 API 키 확인
✓ Kiwoom API 키 유효성 확인
✓ 계좌번호 정확한지 확인
```

### Q: AI 분석이 안 됨
```
✓ GEMINI_API_KEY 설정 확인
✓ Gemini API 크레딧 확인
```

### Q: 대시보드가 안 열림
```
✓ 포트 5000 사용 중인지 확인
✓ main.py 실행 확인
```

### Q: 주문이 안 나감
```
✓ api/order.py가 DRY RUN 모드인지 확인
✓ 실제 거래를 원하면 order.py 수정 필요
```

---

## ⚠️ 안전 수칙

1. **소액 테스트**: 처음엔 소액으로 시작
2. **DRY RUN**: 실제 거래 전에 시뮬레이션
3. **손절 설정**: 반드시 손절매 설정
4. **모니터링**: 대시보드로 실시간 확인
5. **로그 확인**: 이상 징후 체크

---

## 🚀 시작하기

```bash
# 1. API 키 설정
# config/credentials.py 편집

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 실행!
python main.py

# 4. 브라우저에서 접속
# http://localhost:5000
```

**Happy Trading! 💰📈**

---

## 📚 Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[OPTIMIZATION_NOTES_v5.5.md](OPTIMIZATION_NOTES_v5.5.md)** - Future optimization opportunities
- **[docs/](docs/)** - Additional documentation
  - [Quick Start Guide](docs/QUICK_START.md)
  - [Windows Installation](docs/INSTALL_WINDOWS.md)
  - [Project Structure](docs/PROJECT_STRUCTURE.md)
  - [Guides](docs/guides/) - Feature-specific guides
  - [Archive](docs/archive/) - Historical documentation

---

## 🔄 Recent Updates

### v5.6.0 (2025-11-05)
- ✅ Fixed virtual trading history auto-refresh issue (now manually controlled)
- ✅ Added JSON download for virtual trades
- ✅ Improved dashboard UX and version display
- ✅ Cleaned up verbose DEBUG logs
- ✅ Consolidated documentation

### v5.5.1 (2025-11-05)
- ✅ Removed obsolete app_apple.py (3,249 lines cleanup)
- ✅ Updated deployment scripts
- ✅ Documented future optimization opportunities

### v5.5.0 (2025-11-05)
- ✅ Fixed critical account balance 2x duplication bug
- ✅ Improved balance accuracy (99.98% match with mobile)

See [CHANGELOG.md](CHANGELOG.md) for complete version history.

---

## 🤝 Support

For issues, questions, or contributions, please contact the development team.

---

**AutoTrade Pro** - Powered by AI, Built for Performance 🚀
