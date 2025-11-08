"""
koapy 로그인 간단 테스트 스크립트

사용법:
  1. autotrade_32 환경 활성화
  2. python test_koapy_login.py 실행
  3. 로그인 창에서 로그인
"""
import sys
import os

# Qt 환경 설정
os.environ['QT_API'] = 'pyqt5'

from PyQt5.QtWidgets import QApplication

print("="*60)
print("koapy 로그인 테스트")
print("="*60)

# 1. Qt Application 생성
print("\n1. Qt Application 생성...")
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)
    print("✅ Qt Application 생성 완료")
else:
    print("✅ Qt Application 이미 존재")

# 2. koapy 초기화
print("\n2. koapy 초기화...")
try:
    from koapy import KiwoomOpenApiPlusEntrypoint

    print("✅ koapy 임포트 성공")
    print("\n3. OpenAPI Entrypoint 생성...")

    # Context manager 사용
    with KiwoomOpenApiPlusEntrypoint() as context:
        print("✅ Entrypoint 생성 완료")

        print("\n" + "="*60)
        print("⚠️  로그인 창 안내")
        print("="*60)
        print("1. 키움증권 로그인 창이 나타납니다")
        print("2. 창이 안 보이면 '작업 표시줄'을 확인하세요")
        print("3. 로그인 정보를 입력하고 '로그인' 버튼 클릭")
        print("4. 인증서 비밀번호 입력")
        print("="*60)
        print()

        print("4. Qt 이벤트 처리...")
        for _ in range(5):
            app.processEvents()
            import time
            time.sleep(0.1)

        print("\n5. EnsureConnected() 호출...")
        print("👀 로그인 창을 찾아보세요!")
        print("   - Alt+Tab으로 창 전환")
        print("   - 작업 표시줄의 깜빡이는 아이콘 클릭")
        print()

        # EnsureConnected 호출 (로그인 창 표시)
        context.EnsureConnected()

        # 연결 상태 확인
        print("\n6. 연결 상태 확인...")
        state = context.GetConnectState()
        print(f"   연결 상태 코드: {state}")

        if state == 1:
            print("\n" + "="*60)
            print("✅ 로그인 성공!")
            accounts = context.GetAccountList()
            print(f"   계좌 목록: {accounts}")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("❌ 로그인 실패")
            print(f"   상태 코드: {state} (1이어야 정상)")
            print("\n예상 원인:")
            print("1. 로그인 정보 오류")
            print("2. 인증서 비밀번호 오류")
            print("3. 키움 OpenAPI+ 미설치")
            print("4. 32비트 환경 아님")
            print("="*60)

except ImportError as e:
    print(f"\n❌ koapy 임포트 실패: {e}")
    print("\n해결 방법:")
    print("  conda activate autotrade_32")
    print("  pip install koapy")
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("테스트 완료")
print("프로그램을 종료하려면 Enter 키를 누르세요...")
print("="*60)
input()
