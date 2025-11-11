# 전략 최적화 엔진 빠른 시작 가이드

## 🚀 지금 바로 시작하기

### 1. 테스트 실행 (3세대, 5초 간격)
```bash
cd /home/user/autotrade
python run_strategy_optimizer.py \
    --population-size 10 \
    --max-generations 3 \
    --interval 5 \
    --stocks 005930,000660
```

### 2. 프로덕션 실행 (24/7 무한 실행)
```bash
# 백그라운드에서 실행
nohup python run_strategy_optimizer.py \
    --population-size 20 \
    --mutation-rate 0.15 \
    --crossover-rate 0.7 \
    --interval 600 \
    --stocks 005930,000660,035720,005380,051910 \
    > logs/optimizer.log 2>&1 &

# 프로세스 ID 저장
echo $! > data/optimizer.pid
```

### 3. 실행 중인 엔진 확인
```bash
# 로그 확인
tail -f logs/optimizer.log

# 프로세스 확인
ps aux | grep strategy_optimizer

# DB 확인
sqlite3 data/strategy_evolution.db "SELECT * FROM generation_stats ORDER BY generation DESC LIMIT 5;"
```

### 4. 엔진 중지
```bash
# PID 파일이 있으면
kill $(cat data/optimizer.pid)

# 또는 직접
pkill -f run_strategy_optimizer.py
```

## 📊 대시보드에서 모니터링

대시보드에 접속하여 진화 현황을 실시간으로 확인할 수 있습니다 (구현 예정).

### API 엔드포인트

1. **진화 상태**: `GET /api/evolution/status`
2. **진화 히스토리**: `GET /api/evolution/history`
3. **최우수 전략**: `GET /api/evolution/best-strategy`
4. **세대 상세**: `GET /api/evolution/generation/<generation>`

## 💡 사용 팁

### 파라미터 튜닝

```bash
# 빠른 탐색 (높은 변이율)
python run_strategy_optimizer.py --mutation-rate 0.3 --population-size 30

# 안정적 진화 (낮은 변이율)
python run_strategy_optimizer.py --mutation-rate 0.1 --population-size 50

# 공격적 교차 (다양성 증가)
python run_strategy_optimizer.py --crossover-rate 0.9
```

### 성능 최적화

1. **병렬 처리**: 최대 4개 전략을 동시에 평가 (ThreadPoolExecutor)
2. **데이터 캐싱**: 차트 데이터를 캐싱하여 API 호출 최소화
3. **DB 인덱스**: generation, fitness_score에 인덱스 추가

### 주의사항

⚠️ **메모리 사용량**: 세대당 20개 전략 × 100세대 = 2000개 전략 데이터
⚠️ **API 제한**: 한투 API는 분당 요청 제한이 있으므로 interval을 10분(600초) 이상 권장
⚠️ **디스크 공간**: DB 크기는 1000세대 기준 약 100MB

## 🔧 트러블슈팅

### 문제: DB 파일을 찾을 수 없음
```bash
mkdir -p data
python run_strategy_optimizer.py
```

### 문제: 백테스터 연결 안됨
현재는 시뮬레이션 모드로 동작합니다. 실제 백테스터 연결은 Phase 2에서 구현됩니다.

### 문제: 프로세스가 종료되지 않음
```bash
kill -9 $(ps aux | grep run_strategy_optimizer | grep -v grep | awk '{print $2}')
```

## 📈 다음 단계

- [ ] Phase 2: 실제 백테스터 연동
- [ ] Phase 3: 가상매매 자동 실행
- [ ] Phase 4: 대시보드 UI 추가
- [ ] Phase 5: 자동 배포 시스템

## 로그 예시

```
🚀 지속적 전략 최적화 시작
초기 세대 생성 중... (크기: 20)
✅ 초기 세대 20개 생성 완료

================================================================================
📊 세대 0 평가 중...
================================================================================
✅ 세대 0 평가 완료 (2.3초)
  🏆 최고 점수: 68.54
  📊 평균 점수: 52.31
  📉 최저 점수: 38.92
세대 0 DB 저장 완료
세대 진화 중... (현재 세대: 0)
  엘리트 보존: 4개 (최고 점수: 68.54)
✅ 다음 세대 생성 완료: 20개
⏰ 600초 후 다음 세대 시작...
```
