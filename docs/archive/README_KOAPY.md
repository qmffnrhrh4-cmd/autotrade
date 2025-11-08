# 🚀 koapy 자동 설치 및 테스트

키움 Open API를 64비트 Python에서 사용하기 위한 완전 자동화 솔루션

---

## ⚡ 빠른 시작 (5분)

```cmd
koapy_auto_setup_and_test.bat
```

**이 명령 하나로 끝!** 🎉

---

## 📦 포함된 파일

### 자동 설치 스크립트

| 파일 | 설명 | 추천 |
|------|------|------|
| **koapy_auto_setup_and_test.bat** | 🌟 만능 자동 설치+테스트 (에러 자동 해결) | ⭐⭐⭐ |
| setup_koapy_windows.bat | 기본 자동 설치 | ⭐⭐ |

### 진단 도구

| 파일 | 설명 |
|------|------|
| **diagnose_koapy.py** | 상세 진단 및 에러 분석 |
| check_koapy_installation.py | 간단한 설치 확인 |

### 테스트 파일

| 파일 | 설명 |
|------|------|
| tests/manual/test_koapy_simple.py | 기본 로그인 테스트 |
| tests/manual/test_koapy_advanced.py | 고급 기능 테스트 (주식 조회, 계좌) |

### 문서

| 파일 | 설명 |
|------|------|
| **KOAPY_QUICKSTART.md** | 5분 빠른 시작 가이드 |
| KOAPY_WINDOWS_SETUP.md | 상세 설치 및 문제 해결 가이드 |

---

## 🎯 사용법

### 1. 자동 설치 및 테스트 (권장)

```cmd
# Windows에서 실행
koapy_auto_setup_and_test.bat
```

**자동으로 처리되는 것:**
- ✅ 충돌 패키지 제거
- ✅ 올바른 버전 설치 (protobuf 3.20.3, grpcio 1.50.0)
- ✅ 모든 의존성 자동 설치
- ✅ import 테스트 (실패 시 최대 3번 재시도)
- ✅ 자동 진단 및 수정
- ✅ 최종 테스트 자동 실행

### 2. 문제 진단

```cmd
python diagnose_koapy.py
```

### 3. 테스트 실행

```cmd
# 기본 테스트
python tests\manual\test_koapy_simple.py

# 고급 테스트
python tests\manual\test_koapy_advanced.py
```

---

## ✅ 성공 확인

설치가 성공하면:

```
================================================================
[SUCCESS] koapy import is working!
================================================================

Final package versions:
  protobuf: 3.20.3
  grpcio: 1.50.0
  koapy: 0.3.5
```

---

## ⚠️ 필수 사항

1. **Windows 전용** - Linux/Mac 불가
2. **키움 OpenAPI+ 설치** 필요
   - 다운로드: https://www3.kiwoom.com/
3. **64비트 Python 3.11** 권장

---

## 🐛 문제 해결

| 증상 | 해결책 |
|------|--------|
| "koapy를 찾을 수 없습니다" | `koapy_auto_setup_and_test.bat` 실행 |
| import 실패 | `python diagnose_koapy.py` → 지시사항 따르기 |
| 버전 충돌 | 자동 스크립트가 해결 (수동: `pip install --force-reinstall protobuf==3.20.3`) |
| 테스트 실패 | 키움 OpenAPI+ 설치 확인, 로그인 정보 확인 |

---

## 📖 상세 문서

- 📘 **KOAPY_QUICKSTART.md** - 빠른 시작 (5분)
- 📗 **KOAPY_WINDOWS_SETUP.md** - 상세 설치 가이드
- 📙 **requirements.txt** - 패키지 버전 정보

---

## 🎓 예제 코드

### 기본 사용법

```python
from koapy import KiwoomOpenApiPlusEntrypoint

with KiwoomOpenApiPlusEntrypoint() as context:
    # 로그인
    context.EnsureConnected()

    # 삼성전자 정보 조회
    info = context.GetStockBasicInfoAsDict('005930')
    name = context.GetMasterCodeName('005930')
    price = context.GetMasterLastPrice('005930')

    print(f"종목명: {name}")
    print(f"현재가: {price:,}원")
```

### 일별 시세 조회

```python
# DataFrame으로 조회
df = context.GetDailyStockDataAsDataFrame(
    '005930',
    adjusted_price=True
)
print(df.head(10))
```

### 계좌 정보

```python
# 계좌 목록
accounts = context.GetAccountList()
print(f"계좌: {accounts}")

# 잔고 조회
balance = context.GetDepositInfo(accounts[0])
```

---

## 💡 팁

### 자동 로그인 설정

`tests/manual/test_koapy_simple.py` 수정:

```python
credential = {
    'user_id': 'your_id',
    'user_password': 'your_pw',
    'cert_password': 'cert_pw',
    'is_simulation': True,  # 모의투자
}
```

### 모의투자 전환

```python
# 모의투자
context.EnsureConnected({'is_simulation': True})

# 실전투자
context.EnsureConnected({'is_simulation': False})
```

---

## 🔧 기술 스택

- **koapy** 0.3.5+ - 키움 Open API wrapper
- **protobuf** 3.20.3 - gRPC 통신
- **grpcio** 1.50.0 - RPC 프레임워크
- **PyQt5** 5.15+ - GUI 프레임워크
- **pandas** 2.2+ - 데이터 분석

---

## 📞 지원

문제가 있으면:

1. `python diagnose_koapy.py` 실행
2. 에러 메시지 확인
3. `KOAPY_WINDOWS_SETUP.md` 문제 해결 섹션 참고

---

## 🎉 완성!

**`koapy_auto_setup_and_test.bat` 하나로 모든 것이 해결됩니다!**

Happy Trading! 📈💰

---

*마지막 업데이트: 2025-11-07*
