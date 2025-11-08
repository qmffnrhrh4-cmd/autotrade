# 🚀 Single Command Execution

## ⚡ 단일 명령어로 모든 것 실행

```cmd
python main.py
```

**끝!** 이게 전부입니다. 🎉

---

## 🎯 작동 원리

### `python main.py` 실행 시:

```
python main.py
    ↓
    ├─ 1. OpenAPI 서버 자동 시작 (32-bit, 백그라운드)
    │   └─ Anaconda autotrade_32 환경 자동 탐지
    │   └─ openapi_server.py 실행 (포트 5001)
    │   └─ 창 안 보임 (백그라운드)
    │
    ├─ 2. main.py 실행 (64-bit)
    │   └─ REST API 초기화
    │   └─ OpenAPI HTTP 클라이언트 초기화
    │   └─ 전략 엔진 시작
    │   └─ 웹 대시보드 시작 (포트 5000)
    │
    └─ 3. main.py 종료 시 OpenAPI 서버도 자동 종료
        └─ 깔끔한 cleanup
```

---

## 📋 사전 요구사항

### 1회만 설치:

```cmd
# 1. Anaconda 환경 생성
INSTALL_ANACONDA_PROMPT.bat

# 2. 패키지 설치 (선택 사항)
SETUP_QUICK.bat
```

그 다음부터는 **`python main.py`** 하나로 끝!

---

## 💡 실행 예시

### Windows CMD (64-bit Python 3.13):

```cmd
C:\Users\USER\Desktop\autotrade> python main.py

============================================================
                  AutoTrade Pro v2.0
============================================================

🔧 OpenAPI 서버 시작 중 (32-bit, 백그라운드)...
✅ OpenAPI 서버 시작됨 (백그라운드)
   - 서버 URL: http://localhost:5001
   - 환경: autotrade_32 (32-bit Python 3.10)
   - 서버 초기화 중... 완료

1. 트레이딩 봇 초기화 중...
🌐 REST API 클라이언트 초기화 중...
✓ REST API 클라이언트 초기화 완료

🔧 OpenAPI HTTP 클라이언트 초기화...
   서버 URL: http://127.0.0.1:5001
📡 OpenAPI 서버 연결 확인 중...
✅ OpenAPI 서버 연결됨!
📋 계좌 목록: ['6452323210']
✅ OpenAPI 클라이언트 초기화 완료
   계좌 목록: ['6452323210']

✓ 트레이딩 봇 초기화 완료

2. 웹 대시보드 시작 중...
✓ 웹 대시보드 시작 완료
  → http://localhost:5000

3. 자동매매 봇 시작...
============================================================
```

---

## 🛑 종료 시

### Ctrl+C 또는 창 닫기:

```
============================================================
Shutting down...
============================================================
🛑 OpenAPI 서버에 종료 신호 전송 중...
🛑 OpenAPI 서버 프로세스 종료 중...
✅ OpenAPI 서버 종료됨
============================================================
```

**자동으로 모든 것이 깔끔하게 종료됩니다!**

---

## 🔧 주요 기능

### ✅ 자동 탐지

- **Anaconda 경로**: 여러 표준 경로 자동 탐지
- **autotrade_32 환경**: 존재 여부 자동 확인
- **openapi_server.py**: 프로젝트 디렉토리에서 자동 탐지

### ✅ 백그라운드 실행

- **OpenAPI 서버**: 창이 보이지 않음
- **CREATE_NO_WINDOW 플래그**: Windows에서 완전 숨김
- **자동 초기화**: 3초 대기 후 준비 완료

### ✅ 자동 Cleanup

- **Graceful Shutdown**: HTTP API로 종료 신호 전송
- **강제 종료**: 응답 없으면 프로세스 종료
- **타임아웃**: 5초 대기 후 강제 kill

### ✅ 오류 처리

Anaconda 없으면:
```
⚠️  Anaconda를 찾을 수 없습니다 - OpenAPI 기능 비활성화
   REST API 기능은 정상 작동합니다
```

autotrade_32 환경 없으면:
```
⚠️  autotrade_32 환경을 찾을 수 없습니다 - OpenAPI 기능 비활성화
   환경 생성: INSTALL_ANACONDA_PROMPT.bat 실행
   REST API 기능은 정상 작동합니다
```

**→ REST API는 계속 작동! 일부 기능만 비활성화**

---

## 🎨 장점

| 항목 | 기존 (start.bat) | 신규 (python main.py) |
|------|------------------|----------------------|
| **명령어** | start.bat | **python main.py** |
| **환경** | 배치 파일 필요 | Python만 있으면 OK |
| **IDE 지원** | ❌ | **✅ VS Code, PyCharm** |
| **디버깅** | 어려움 | **✅ 쉬움** |
| **크로스 플랫폼** | Windows 전용 | **✅ Win/Linux/Mac** |
| **자동화** | 수동 | **✅ 자동 탐지** |

---

## 🔍 문제 해결

### "Anaconda를 찾을 수 없습니다"

**원인**: Anaconda가 표준 경로에 없음

**해결**:
1. Anaconda가 설치되어 있는지 확인
2. 또는 `main.py`의 `find_anaconda_path()` 함수에 경로 추가:

```python
possible_paths = [
    Path.home() / "anaconda3",
    Path.home() / "Anaconda3",
    Path("C:/ProgramData/Anaconda3"),
    Path("C:/ProgramData/anaconda3"),
    Path("D:/your/custom/path/Anaconda3"),  # 여기 추가
]
```

### "autotrade_32 environment not found"

**해결**:
```cmd
INSTALL_ANACONDA_PROMPT.bat
```

### OpenAPI 서버가 시작 안 됨

**확인 방법**:
```cmd
curl http://localhost:5001/health
```

**수동 시작**:
```cmd
# Anaconda Prompt
conda activate autotrade_32
python openapi_server.py
```

그 다음 별도 터미널에서:
```cmd
python main.py
```

---

## 🧪 테스트

### 최소 테스트:

```cmd
# 1. git pull
git pull origin claude/fix-qt-bindings-issue-011CUuArZTwm6np9XhDC3tCG

# 2. 실행
python main.py
```

### 예상 출력:

```
✅ OpenAPI 서버 시작됨 (백그라운드)
✅ OpenAPI 서버 연결됨!
📋 계좌 목록: ['YOUR_ACCOUNT']
```

---

## 📊 비교

### 이전 방식 (복잡):

```cmd
# 1. Anaconda Prompt 열기
# 2. 환경 활성화
conda activate autotrade_32
# 3. 서버 시작
python openapi_server.py
# 4. 새 터미널 열기
# 5. main.py 실행
python main.py
# 6. 종료 시 두 터미널 모두 닫기
```

### 신규 방식 (간단):

```cmd
python main.py
# Ctrl+C로 종료
```

**7단계 → 1단계!** 🚀

---

## 🎓 고급 사용법

### VS Code 디버깅:

`launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Main",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "console": "integratedTerminal"
        }
    ]
}
```

**F5 키로 디버깅 시작!** OpenAPI 서버도 자동 시작됩니다.

### PyCharm 실행:

Run Configuration:
- Script path: `/path/to/autotrade/main.py`
- Python interpreter: Python 3.13 (64-bit)

**▶️ 버튼 클릭!** 모든 것이 자동으로 시작됩니다.

---

## 📝 요약

### Before:
```
start.bat 실행 → 복잡한 배치 스크립트 → 수동 환경 관리
```

### After:
```
python main.py → 자동으로 모든 것 처리 → 단일 명령어
```

---

**One Command to Rule Them All! 🚀📈**

```cmd
python main.py
```
