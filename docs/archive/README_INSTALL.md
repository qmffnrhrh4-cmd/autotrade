# AutoTrade 설치 가이드

## 🎯 가장 쉬운 방법 (권장)

### Anaconda Prompt 사용

1. **Windows 키** 누르기
2. **"Anaconda Prompt"** 입력
3. 클릭해서 열기
4. 다음 명령어 실행:

```cmd
cd C:\Users\USER\Desktop\autotrade
INSTALL_ANACONDA_PROMPT.bat
```

**끝!**

---

## 🔄 대안 방법

### 방법 1: 일반 명령 프롬프트 (PATH 등록 필요)

```cmd
INSTALL.bat
```

만약 "Anaconda not found" 에러가 나면 → Anaconda Prompt 사용

---

### 방법 2: 수동 설치

**Anaconda Prompt에서:**

```cmd
cd C:\Users\USER\Desktop\autotrade

set CONDA_FORCE_32BIT=1
conda create -n autotrade_32 python=3.11 -y
conda activate autotrade_32

python -c "import struct; print(struct.calcsize('P')*8, 'bit')"

pip install PyQt5 PyQt5-Qt5 PyQt5-sip
pip install protobuf==3.20.3 grpcio==1.50.0 koapy
pip install pywin32
pip install -r requirements.txt

python test_login.py
```

---

## ❓ Anaconda가 정말 설치되어 있나요?

### 확인 방법

1. **Windows 키** 누르기
2. **"Anaconda"** 검색
3. 다음 중 하나가 보이나요?
   - Anaconda Prompt
   - Anaconda Navigator
   - Anaconda Powershell Prompt

보이면 → **설치됨** ✅
안 보이면 → **설치 필요** ❌

---

## 📥 Anaconda 설치

### 아직 설치 안 했다면:

1. https://www.anaconda.com/download 접속
2. **Windows 64-bit** 버전 다운로드
3. 설치 시:
   - ✅ "Add Anaconda to PATH" 체크 (권장)
   - ✅ "Register Anaconda as default Python" 체크
4. 설치 완료 후 **컴퓨터 재시작**
5. Anaconda Prompt 열어서 `conda --version` 확인

---

## 🚀 설치 후

### Anaconda Prompt에서:

```cmd
cd C:\Users\USER\Desktop\autotrade
conda activate autotrade_32
python test_login.py
```

---

## 💡 팁

### 매번 사용할 때

**Anaconda Prompt 열고:**

```cmd
conda activate autotrade_32
cd C:\Users\USER\Desktop\autotrade
python main.py
```

### 바로가기 만들기

`RUN_TEST.bat`와 `RUN_MAIN.bat`를 바탕화면에 복사해서 사용하세요.

---

## 🔧 문제 해결

### "Anaconda not found"

**해결:** Anaconda Prompt 사용
- Windows 키 → "Anaconda Prompt" 검색

### "conda is not recognized"

**해결:** PATH 등록 또는 Anaconda Prompt 사용

### "64-bit environment created"

**원인:** Anaconda가 64-bit 전용
**해결:** 괜찮습니다. koapy가 자동으로 32-bit 서버를 실행합니다.

---

## 📞 도움

문제가 계속되면 다음 정보를 알려주세요:

1. Anaconda가 설치되어 있나요? (예/아니오)
2. Anaconda Prompt가 보이나요? (예/아니오)
3. 에러 메시지 전체

---

**Happy Trading!** 🚀
