"""
최소한의 koapy 로그인 테스트
로그인 창이 나타나는지만 확인합니다.
"""
import sys
import os
os.environ['QT_API'] = 'pyqt5'

print("\n로그인 테스트 시작...")
print("⚠️  주의: 로그인 창이 백그라운드에 나타날 수 있습니다!")
print("   → 지금 바로 Alt+Tab을 준비하세요!\n")

from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)

from koapy import KiwoomOpenApiPlusEntrypoint

print("Entrypoint 생성 중...")
context = KiwoomOpenApiPlusEntrypoint().__enter__()

print("\n" + "="*60)
print("🔐 로그인 창을 표시합니다!")
print("="*60)
print("👀 지금 바로:")
print("   1. Alt+Tab 누르기")
print("   2. 작업 표시줄 확인")
print("   3. 키움 로그인 창 찾기")
print("="*60)
print()

input("로그인 창을 찾았으면 Enter 누르세요...")

print("\nEnsureConnected 호출 중...")
context.EnsureConnected()

state = context.GetConnectState()
if state == 1:
    print(f"\n✅ 로그인 성공! 계좌: {context.GetAccountList()}")
else:
    print(f"\n❌ 로그인 실패 (상태: {state})")

context.__exit__(None, None, None)
