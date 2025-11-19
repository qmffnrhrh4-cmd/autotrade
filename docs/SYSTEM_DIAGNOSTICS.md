# 🔍 시스템 자가 진단 시스템

AutoTrade Pro는 시작할 때 자동으로 모든 기능과 연계를 체크하고 리포트를 생성합니다.

---

## ✨ 주요 기능

### 1️⃣ **자동 진단 (시작 시)**
프로그램을 시작하면 자동으로 다음을 체크합니다:
- ✅ 데이터베이스 연결 및 스키마
- ✅ 가상매매 시스템
- ✅ 모듈 Import 상태
- ✅ 설정 파일 유효성
- ✅ 파일 시스템 권한
- ✅ 모듈 간 통합 연동

### 2️⃣ **수동 진단 (언제든지)**
```bash
# Python으로 실행
python run_diagnostics.py

# 또는 Windows에서 더블클릭
run_diagnostics.bat
```

### 3️⃣ **상세 리포트 생성**
진단 결과는 자동으로 저장됩니다:
- `logs/diagnostics_report.json` - JSON 형식 (프로그램용)
- `logs/diagnostics_report.txt` - 텍스트 형식 (사람이 읽기 쉬움)

---

## 📊 체크 항목

### **Database (데이터베이스)**
- [x] 메인 DB 연결 테스트
- [x] is_virtual 컬럼 존재 확인
- [x] 인덱스 확인
- [x] 거래 기록 조회

### **Virtual Trading (가상매매)**
- [x] 가상매매 DB 연결
- [x] 전략 목록 조회

### **Module Import (모듈)**
- [x] 핵심 모듈 import 가능 여부
  - database
  - api.openapi
  - api.account, order, data_fetcher
  - virtual_trading
  - ai.strategy_loader, program_manager
  - strategy.emergency_manager, scoring_system

### **Configuration (설정)**
- [x] 설정 파일 로드
- [x] 필수 설정 존재 확인

### **Filesystem (파일 시스템)**
- [x] 필수 디렉토리 존재
- [x] 쓰기 권한 확인

### **Integration (통합 테스트)**
- [x] 가상매매 → 메인 DB 연동
- [x] 전략진화 → 실제 매매 연동

---

## 📋 결과 예시

### **성공 케이스**
```
✅ [Database] Main DB Connection: 메인 데이터베이스 연결 성공
✅ [Database] Schema Check (is_virtual): is_virtual 컬럼이 존재합니다
✅ [Database] Index Check: 모든 인덱스가 존재합니다 (5개)
✅ [Database] Trade Records: 거래 기록 142개 확인
✅ [Virtual Trading] Virtual Trading DB: 가상매매 DB 정상 (3개 전략)
✅ [Module Import] database: 데이터베이스 모델 import 성공
...

📊 진단 결과 요약
================================================================================
✅ 성공: 24/24 (100.0%)
⚠️  경고: 0/24
❌ 실패: 0/24
⏱️  소요시간: 0.52초
🎯 전체 상태: HEALTHY
```

### **경고/오류 케이스**
```
❌ [Database] Schema Check (is_virtual): is_virtual 컬럼이 없습니다
   💡 해결방법: 시스템이 자동으로 컬럼을 추가합니다

⚠️  [Integration] Strategy Evolution → Trading: 전략 로더 초기화 실패 (선택적 기능)
   상세: 전략 파일이 없습니다
   💡 해결방법: python run_strategy_optimizer.py 실행하여 전략 생성

📊 진단 결과 요약
================================================================================
✅ 성공: 20/24 (83.3%)
⚠️  경고: 3/24
❌ 실패: 1/24
⏱️  소요시간: 0.68초
🎯 전체 상태: DEGRADED
```

---

## 🛠️ 문제 해결 가이드

### **데이터베이스 관련**

**문제:** `is_virtual 컬럼이 없습니다`
```bash
# 해결: 시스템이 자동으로 추가하지만, 수동으로도 가능
python scripts/migrate_add_is_virtual.py
```

**문제:** `데이터베이스 연결 실패`
```bash
# 해결: data/ 디렉토리 권한 확인
chmod 755 data/
```

### **모듈 Import 관련**

**문제:** `모듈 import 실패`
```bash
# 해결: 필수 패키지 설치
pip install -r requirements.txt
```

### **파일 시스템 관련**

**문제:** `디렉토리가 없습니다`
```bash
# 해결: 필수 디렉토리 생성
mkdir -p data logs config
```

**문제:** `쓰기 권한 없음`
```bash
# 해결: 권한 부여
chmod 755 data/ logs/
```

---

## 🔧 개발자용

### **새로운 체크 항목 추가**

`utils/system_diagnostics.py`에 메서드 추가:

```python
def check_my_feature(self) -> bool:
    """내 기능 체크"""
    logger.info("🎯 내 기능 진단 중...")

    try:
        # 체크 로직
        result = check_something()

        if result:
            self.add_result(DiagnosticResult(
                category="My Feature",
                check_name="Feature Test",
                status="pass",
                message="기능이 정상입니다"
            ))
            return True
        else:
            self.add_result(DiagnosticResult(
                category="My Feature",
                check_name="Feature Test",
                status="fail",
                message="기능이 작동하지 않습니다",
                solution="수정 방법..."
            ))
            return False

    except Exception as e:
        self.add_result(DiagnosticResult(
            category="My Feature",
            check_name="Feature Test",
            status="fail",
            message="체크 실패",
            details=str(e)
        ))
        return False
```

그리고 `run_full_diagnostics()`에 추가:
```python
def run_full_diagnostics(self):
    ...
    self.check_my_feature()  # 추가
    ...
```

---

## 📈 통계 및 모니터링

### **진단 히스토리**
모든 진단 결과는 타임스탬프와 함께 저장되므로:
- 시간에 따른 시스템 상태 추적 가능
- 문제 발생 시점 파악
- 성능 저하 감지

### **CI/CD 통합**
```bash
# 테스트 파이프라인에 추가
python run_diagnostics.py
if [ $? -ne 0 ]; then
    echo "System diagnostics failed!"
    exit 1
fi
```

---

## 💡 팁

1. **정기 진단**
   - 매일 아침 시스템 시작 전에 자동 진단
   - 문제를 미리 발견하고 해결

2. **배포 전 체크**
   - 코드 변경 후 항상 진단 실행
   - 새로운 기능이 기존 시스템을 망가뜨리지 않았는지 확인

3. **리포트 공유**
   - `logs/diagnostics_report.txt`를 이슈 리포트에 첨부
   - 문제 재현에 도움

---

## 🎯 기대 효과

✅ **사전 예방**
- 사용자가 발견하기 전에 문제를 자동으로 감지
- 시스템 다운타임 최소화

✅ **빠른 디버깅**
- 상세한 진단 리포트로 문제 원인 즉시 파악
- 해결 방법 자동 제시

✅ **안정성 향상**
- 모든 모듈 간 연계가 올바르게 작동하는지 확인
- 숨겨진 버그 조기 발견

✅ **개발 효율성**
- 매번 수동으로 체크할 필요 없음
- 자동화된 통합 테스트

---

## 📞 문의

문제가 발생하면:
1. `logs/diagnostics_report.txt` 확인
2. 제시된 해결 방법 시도
3. 그래도 안 되면 이슈 생성 (리포트 첨부)
