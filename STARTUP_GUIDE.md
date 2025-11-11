# AutoTrade 시작 가이드

## 🚀 빠른 시작

### Windows

```batch
start_with_openapi.bat
```

**실행 순서:**
1. OpenAPI 서버 시작 (32비트 Python)
2. Kiwoom 로그인 대기
3. **전략 최적화 엔진 시작 (백그라운드)** ⭐ 자동!
4. 메인 애플리케이션 시작 (64비트 Python)

### Linux/Mac

```bash
./start_autotrade.sh
```

**실행 순서:**
1. 진화 데이터베이스 초기화 (없는 경우)
2. **전략 최적화 엔진 시작 (백그라운드)** ⭐ 자동!
3. 메인 애플리케이션 시작

---

## 📋 포함된 기능

### ✅ 자동으로 시작되는 것들

1. **OpenAPI 서버** (Windows만)
   - Kiwoom API 연결
   - 포트: 5001

2. **전략 최적화 엔진** ⭐ **NEW!**
   - 유전 알고리즘 기반 전략 진화
   - 24/7 백테스팅
   - 자동 배포 (가상매매 연동)
   - 로그: `logs/strategy_optimizer.log`

3. **메인 애플리케이션**
   - 트레이딩 봇
   - 웹 대시보드 (포트: 5000)
   - AI 분석 엔진

---

## 🛠️ 수동 시작 (고급)

### 전략 최적화 엔진만 실행

```bash
# 자동 배포 활성화
python run_strategy_optimizer.py --auto-deploy

# 옵션 설정
python run_strategy_optimizer.py \
  --population-size 30 \
  --mutation-rate 0.2 \
  --interval 300 \
  --stocks "005930,000660,035720" \
  --auto-deploy
```

**주요 옵션:**
- `--population-size`: 세대당 전략 수 (기본: 20)
- `--mutation-rate`: 변이 확률 (기본: 0.15)
- `--crossover-rate`: 교차 확률 (기본: 0.7)
- `--interval`: 세대 간 대기 시간(초) (기본: 600)
- `--max-generations`: 최대 세대 수 (기본: 무한)
- `--stocks`: 테스트 종목 (기본: 005930,000660,035720)
- `--auto-deploy`: 최우수 전략 자동 배포
- `--simulation`: 시뮬레이션 모드 (API 없이 실행)

### 진화 데이터베이스 초기화

```bash
python init_evolution_db.py
```

---

## 📊 대시보드 접속

### 메인 대시보드
```
http://localhost:5000
```

### 전략 진화 현황 확인
```
http://localhost:5000/evolution
```

**확인 항목:**
- 현재 세대
- 최고 적합도
- 평균 적합도
- 세대별 진화 그래프
- 최우수 전략 상세정보
- 배포 가능한 전략 목록

---

## 🔍 로그 확인

### 전략 최적화 엔진 로그 (Linux/Mac)
```bash
tail -f logs/strategy_optimizer.log
```

### 메인 애플리케이션 로그
```bash
# 콘솔 출력 확인
```

---

## 🛑 종료

### Windows
- `Ctrl + C` 또는 창 닫기
- OpenAPI 서버는 자동으로 종료됨

### Linux/Mac
- `Ctrl + C`
- 백그라운드 프로세스 자동 종료

---

## ⚠️ 문제 해결

### 진화 데이터베이스 없음 오류
```bash
python init_evolution_db.py
```

### 전략 최적화 엔진이 실행되지 않음
```bash
# 수동 실행
python run_strategy_optimizer.py --auto-deploy

# 로그 확인 (Linux/Mac)
cat logs/strategy_optimizer.log
```

### 포트 충돌
- 5000번 포트 (대시보드): `dashboard/app.py` 설정 변경
- 5001번 포트 (OpenAPI): `openapi_server_v2.py` 설정 변경

---

## 📚 추가 정보

- **메인 README**: [README.md](README.md)
- **OpenAPI 설정**: [OPENAPI_SETUP_GUIDE.md](OPENAPI_SETUP_GUIDE.md)
- **전략 최적화 상세**: [docs/strategy_optimization.md](docs/strategy_optimization.md)

---

**마지막 업데이트**: 2025-11-12
