# koapy 빠른 시작 가이드 (5분 완성)

## 🚀 한 번에 끝내기 (권장)

```cmd
# 이 명령 하나로 모든 것이 자동으로 해결됩니다!
koapy_auto_setup_and_test.bat
```

**이 스크립트가 자동으로 하는 일:**
1. ✅ 기존 패키지 완전 정리
2. ✅ 올바른 버전 자동 설치
3. ✅ 모든 의존성 자동 설치
4. ✅ 버전 충돌 자동 해결
5. ✅ import 테스트 (3번까지 재시도)
6. ✅ 실패 시 자동 진단 및 수정
7. ✅ 최종 테스트 자동 실행
8. ✅ 성공할 때까지 반복

**예상 소요 시간:** 5-10분 (인터넷 속도에 따라)

---

## 📋 사용법

### Windows에서 실행

```cmd
# 1. 저장소 최신 버전 받기
git pull origin claude/kiwoum-openapi-test-file-011CUtytrEXFEdtf3tvF4Vjd

# 2. 자동 설치 및 테스트 실행
koapy_auto_setup_and_test.bat

# 그게 끝입니다! 🎉
```

---

## 🔍 문제가 있을 때

### 진단 도구 사용

```cmd
python diagnose_koapy.py
```

**진단 도구가 보여주는 것:**
- Python 환경 정보
- 설치된 패키지 버전
- import 성공/실패 여부
- 정확한 에러 메시지
- 해결 방법 제안

### 수동 재설치

```cmd
# 1. 완전 정리
pip uninstall -y protobuf grpcio koapy PyQt5 qtpy

# 2. 자동 설치 다시 실행
koapy_auto_setup_and_test.bat
```

---

## ✅ 설치 성공 확인

설치가 성공하면 다음과 같은 메시지가 표시됩니다:

```
================================================================
[SUCCESS] koapy import is working!
================================================================

Final package versions:
  protobuf: 3.20.3
  grpcio: 1.50.0
  koapy: 0.3.5
  PyQt5: 5.15.11
  pandas: 2.3.3

================================================================
                 Installation Complete!
================================================================
```

---

## 🧪 테스트 실행

### 자동 테스트 (스크립트가 자동 실행)

`koapy_auto_setup_and_test.bat`가 자동으로 테스트를 실행합니다.

### 수동 테스트

```cmd
# 간단한 테스트
python tests\manual\test_koapy_simple.py

# 고급 기능 테스트
python tests\manual\test_koapy_advanced.py
```

---

## 📝 테스트 종류

### test_koapy_simple.py
- 기본 로그인 테스트
- 계좌 정보 조회
- 수동 로그인 (로그인 창 표시)

### test_koapy_advanced.py
- 주식 기본 정보 조회 (삼성전자)
- 일별 주가 데이터 조회
- 계좌 잔고 조회
- 조건 검색식 사용
- Low-level TR 호출

---

## ⚠️ 중요 사항

### 1. Windows 전용
- koapy와 키움 Open API는 **Windows에서만** 작동합니다
- Linux/Mac에서는 실행 불가

### 2. 키움 OpenAPI+ 필요
- 키움증권 OpenAPI+ 프로그램이 설치되어 있어야 합니다
- 다운로드: https://www3.kiwoom.com/

### 3. 64비트 Python 권장
- 64비트 Python 사용 권장
- koapy가 자동으로 32비트 서버를 실행합니다

### 4. 로그인 필요
- 테스트 실행 시 키움 계정으로 로그인해야 합니다
- 모의투자 계정으로도 테스트 가능

---

## 🎯 빠른 문제 해결

| 문제 | 해결책 |
|------|--------|
| "koapy를 찾을 수 없습니다" | `koapy_auto_setup_and_test.bat` 실행 |
| import 실패 | `python diagnose_koapy.py` 실행 후 지시사항 따르기 |
| 버전 충돌 | `pip install --force-reinstall protobuf==3.20.3 grpcio==1.50.0` |
| 로그인 실패 | 키움 OpenAPI+ 설치 확인 |
| 테스트 실패 | 인터넷 연결 및 키움 서버 상태 확인 |

---

## 📚 추가 문서

- **KOAPY_WINDOWS_SETUP.md** - 상세 설치 가이드
- **setup_koapy_windows.bat** - 기본 설치 스크립트
- **diagnose_koapy.py** - 진단 도구

---

## 💡 팁

### 자동 로그인 설정

`tests/manual/test_koapy_simple.py` 파일을 열어서:

```python
credential = {
    'user_id': 'your_id',          # 키움 아이디
    'user_password': 'your_pw',    # 비밀번호
    'cert_password': 'cert_pw',    # 공인인증서 비밀번호
    'is_simulation': True,         # 모의투자
}
```

### 모의투자 vs 실전

```python
# 모의투자 (안전)
context.EnsureConnected({'is_simulation': True})

# 실전투자 (주의!)
context.EnsureConnected({'is_simulation': False})
```

---

## 🎉 완료!

`koapy_auto_setup_and_test.bat` 하나로 모든 설치와 테스트가 완료됩니다!

문제가 있으면 `diagnose_koapy.py`를 실행하세요.

**Happy Trading! 📈**
