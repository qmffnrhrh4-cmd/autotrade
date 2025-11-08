# 🔧 OpenAPI 32비트 환경 설정 가이드

## 📋 개요

키움 OpenAPI는 32비트에서만 작동하므로, 별도의 32비트 Python 환경이 필요합니다.
이 가이드는 **자동 설정 스크립트**를 사용하여 모든 설정을 한 번에 처리합니다.

---

## 🚀 빠른 시작 (권장)

### 방법 1: 배치 파일 실행 (가장 쉬움)

```bash
# 더블클릭 또는 명령 프롬프트에서 실행
setup_openapi_32bit.bat
```

**자동으로 처리되는 작업:**
- ✅ Python 3.9로 다운그레이드
- ✅ koapy 0.8.3 설치
- ✅ PyQt5 5.15.9 설치
- ✅ 필수 라이브러리 설치
- ✅ 버전 검증
- ✅ Import 테스트
- ✅ 로그인 창 테스트

---

### 방법 2: Python 스크립트 직접 실행

```bash
# 1. 가상환경 활성화
conda activate autotrade_32

# 2. 설정 스크립트 실행
python setup_openapi_32bit.py
```

---

## 📖 단계별 실행 과정

### STEP 1: Conda 환경 확인
- Anaconda/Miniconda 설치 여부 확인
- conda 명령어 사용 가능 여부 체크

### STEP 2: 현재 환경 확인
- Python 버전 확인 (3.9 목표)
- 아키텍처 확인 (32비트 권장)
- 가상환경 이름 확인 (autotrade_32)

### STEP 3: Python 3.9 다운그레이드 (필요시)
```bash
conda install python=3.9 -y
```
- 약 3-5분 소요
- 기존 패키지 일부 제거될 수 있음

### STEP 4: 필수 패키지 설치
```bash
pip install koapy==0.8.3 PyQt5==5.15.9 --no-cache-dir
pip install requests pandas numpy
```
- 약 2-3분 소요
- pip 실패 시 conda로 자동 재시도

### STEP 5: 패키지 검증
```python
import koapy          # v0.8.3
import PyQt5          # v5.15.9
import requests
import pandas
import numpy
```

### STEP 6: PyQt5 테스트
```python
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QCoreApplication
```

### STEP 7: koapy 테스트
```python
from koapy import KiwoomOpenApiContext
from koapy.backend.kiwoom_open_api_plus.core.KiwoomOpenApiPlusQAxWidget import KiwoomOpenApiPlusQAxWidget
```

### STEP 8: 키움 OCX 파일 확인
다음 경로에서 OCX 파일 탐색:
- `C:\OpenAPI\KHOpenAPI.ocx`
- `C:\OpenAPI\KHOpenAPICtrl.ocx`
- `C:\Program Files (x86)\Kiwoom\OpenAPI\KHOpenAPI.ocx`
- `C:\KiwoomFlash3\OpenAPI\KHOpenAPI.ocx`

### STEP 9: 로그인 창 테스트
```python
with KiwoomOpenApiContext() as context:
    accounts = context.GetAccountList()
    user_id = context.GetLoginInfo("USER_ID")
```
- 로그인 창 자동 표시
- ID/PW/인증서 비밀번호 입력
- 계좌 정보 자동 확인

### STEP 10: 빠른 테스트 스크립트 생성
`quick_login_test.bat` 파일 자동 생성

---

## ✅ 성공 시 출력

```
================================================================================
✨ 모든 설정 및 테스트 완료!
================================================================================

다음 단계:
  1. OpenAPI 로그인 성공 ✅
  2. openapi_server.py 실행 가능
  3. main.py에서 REST API 사용 가능

📝 설정 완료 요약
================================================================================
✅ Python 3.9 환경 구성
✅ koapy, PyQt5 설치
✅ Import 테스트 완료
✅ OCX 파일 확인됨

빠른 테스트: quick_login_test.bat 실행
```

---

## ❌ 문제 해결

### 문제 1: "conda를 찾을 수 없습니다"
**원인:** Anaconda/Miniconda 미설치

**해결:**
1. Anaconda 다운로드: https://www.anaconda.com/download
2. 설치 시 "Add to PATH" 체크
3. 재부팅 후 재시도

---

### 문제 2: "autotrade_32 환경을 찾을 수 없습니다"
**원인:** 가상환경 미생성

**해결:**
```bash
# 32비트 Python 3.9 환경 생성
conda create -n autotrade_32 python=3.9 -y

# 환경 활성화
conda activate autotrade_32

# 스크립트 재실행
python setup_openapi_32bit.py
```

---

### 문제 3: "Python 다운그레이드 실패"
**원인:** 환경이 손상되었거나 권한 부족

**해결:**
```bash
# 환경 재생성
conda deactivate
conda remove -n autotrade_32 --all -y
conda create -n autotrade_32 python=3.9 -y
conda activate autotrade_32
python setup_openapi_32bit.py
```

---

### 문제 4: "koapy 설치 실패"
**원인:** Python 버전 호환성 문제

**해결:**
```bash
# Python 버전 확인
python --version  # 3.9.x 이어야 함

# 수동 설치
pip uninstall koapy -y
pip install koapy==0.8.3 --no-cache-dir

# conda로 시도
conda install koapy -c conda-forge -y
```

---

### 문제 5: "PyQt5 Import 실패"
**원인:** PyQt5 또는 의존성 설치 문제

**해결:**
```bash
# PyQt5 재설치
pip uninstall PyQt5 PyQt5-Qt5 PyQt5-sip -y
pip install PyQt5==5.15.9 --no-cache-dir

# Visual C++ 재배포 패키지 설치
# https://aka.ms/vs/17/release/vc_redist.x86.exe
```

---

### 문제 6: "OCX 파일을 찾을 수 없습니다"
**원인:** 키움 OpenAPI+ 미설치

**해결:**
1. 키움증권 홈페이지 접속
2. OpenAPI+ 다운로드: https://www.kiwoom.com/nkw.templateFrameSet.do?m=m1408000000
3. 설치 후 재부팅
4. 스크립트 재실행

---

### 문제 7: "로그인 창이 표시되지 않음"
**원인:** 백그라운드 실행, COM 객체 초기화 실패

**해결:**
```bash
# 관리자 권한으로 실행
# 명령 프롬프트 우클릭 > 관리자 권한으로 실행

conda activate autotrade_32
python setup_openapi_32bit.py
```

---

### 문제 8: "로그인 타임아웃"
**원인:** 로그인 미완료, 인터넷 연결 문제

**해결:**
- 로그인 창에서 ID/PW/인증서 비밀번호 정확히 입력
- 키움 서버 점검 시간 확인 (평일 05:00-08:00)
- 인터넷 연결 상태 확인

---

## 🔄 환경 재생성 (최후 수단)

모든 해결 방법이 실패한 경우:

```bash
# 1. 기존 환경 완전 삭제
conda deactivate
conda remove -n autotrade_32 --all -y

# 2. 새 32비트 환경 생성
set CONDA_FORCE_32BIT=1
conda create -n autotrade_32 python=3.9 -y

# 3. 환경 활성화
conda activate autotrade_32

# 4. 수동 설치
pip install koapy==0.8.3 PyQt5==5.15.9 requests pandas numpy --no-cache-dir

# 5. 검증
python -c "from koapy import KiwoomOpenApiContext; print('성공!')"
```

---

## 📁 생성되는 파일

| 파일명 | 용도 |
|--------|------|
| `setup_openapi_32bit.py` | 메인 설정 스크립트 |
| `setup_openapi_32bit.bat` | 배치 실행 파일 |
| `quick_login_test.bat` | 빠른 로그인 테스트 |
| `_temp_login_test.py` | 임시 테스트 파일 (자동 삭제) |

---

## 🎯 다음 단계

설정 완료 후:

1. **openapi_server.py 실행** (32비트 환경)
   ```bash
   conda activate autotrade_32
   python openapi_server.py
   ```

2. **main.py 실행** (64비트 메인 환경)
   ```bash
   conda activate autotrade  # 또는 메인 환경
   python main.py
   ```

3. **하이브리드 구조 확인**
   - main.py → REST API → openapi_server.py
   - 64비트 ↔ HTTP ↔ 32비트

---

## 📞 지원

문제가 지속되면:
1. 전체 로그 저장
2. Python 버전 확인 (`python --version`)
3. 패키지 버전 확인 (`pip list`)
4. 에러 메시지 전문 저장

---

## 📝 참고

- Python 3.9: koapy 0.8.3 호환
- Python 3.10+: koapy 0.9.0 호환
- 32비트 권장 (OpenAPI는 32비트 전용)
- Windows 전용 (Linux/Mac 미지원)
