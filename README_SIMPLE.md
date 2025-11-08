# AutoTrade - 초간단 설치 가이드

## 3단계로 끝내기

### 1단계: 설치 (한 번만)

```cmd
INSTALL.bat
```

더블클릭하면 자동으로:
- 32비트 Python 환경 생성
- 모든 패키지 설치
- 설치 확인

**5-10분 소요**

---

### 2단계: 테스트

```cmd
RUN_TEST.bat
```

로그인 창이 뜨면 로그인하세요.

---

### 3단계: 실행

```cmd
RUN_MAIN.bat
```

---

## 문제 해결

### 문제: "Anaconda not found"

**해결:**
1. Anaconda 설치: https://www.anaconda.com/download
2. 설치 후 컴퓨터 재시작
3. 다시 `INSTALL.bat` 실행

---

### 문제: "Environment not found"

**해결:**
```cmd
INSTALL.bat
```
먼저 설치를 완료하세요.

---

### 문제: "PyQt5 FAIL" 또는 "koapy FAIL"

**해결:**
```cmd
conda activate autotrade_32
pip install PyQt5 koapy
```

---

## 수동 설치 (INSTALL.bat이 안 되면)

```cmd
# 1. 환경 생성
set CONDA_FORCE_32BIT=1
conda create -n autotrade_32 python=3.11 -y

# 2. 활성화
conda activate autotrade_32

# 3. 비트 확인 (32-bit 출력되어야 함)
python -c "import struct; print(struct.calcsize('P')*8, 'bit')"

# 4. 패키지 설치
pip install PyQt5 PyQt5-Qt5 PyQt5-sip
pip install protobuf==3.20.3 grpcio==1.50.0 koapy
pip install pywin32
pip install -r requirements.txt

# 5. 테스트
python test_login.py
```

---

## 파일 구조

```
INSTALL.bat      ← 설치 (한 번만 실행)
RUN_TEST.bat     ← 테스트 (로그인 확인)
RUN_MAIN.bat     ← 실행 (메인 프로그램)
```

---

## 자주 묻는 질문

**Q: 32비트가 왜 필요한가요?**
A: 키움 OpenAPI는 32비트 전용입니다.

**Q: 64비트 Python이 이미 있는데요?**
A: 괜찮습니다. 32비트 환경을 별도로 생성합니다.

**Q: 설치 시간이 얼마나 걸리나요?**
A: 5-10분 정도 소요됩니다.

**Q: 에러가 나요!**
A: 에러 메시지를 캡처해서 알려주세요.

---

## 완료!

설치 후:
1. `RUN_TEST.bat` 실행
2. 로그인 성공 확인
3. `RUN_MAIN.bat`로 메인 프로그램 실행

**Happy Trading!**
