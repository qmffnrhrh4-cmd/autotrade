"""
간단한 koapy 로그인 테스트
"""
import os
import sys

# CRITICAL: Set QT_API before any imports
os.environ['QT_API'] = 'pyqt5'

print("=" * 80)
print("  koapy 로그인 테스트")
print("=" * 80)
print()

try:
    from koapy import KiwoomOpenApiPlusEntrypoint
    print("✅ koapy import 성공")
    print()
except Exception as e:
    print(f"❌ koapy import 실패: {e}")
    sys.exit(1)

print("키움 OpenAPI 서버 연결 중...")
print("(32비트 서버가 자동으로 시작됩니다)")
print()

try:
    with KiwoomOpenApiPlusEntrypoint() as context:
        print("✅ KiwoomOpenApiPlusEntrypoint 생성 성공")
        print()

        print("로그인 시도 중...")
        print("(로그인 창이 나타나면 수동으로 로그인하세요)")
        print()

        # 연결 시도
        context.EnsureConnected()

        # 연결 상태 확인
        state = context.GetConnectState()

        if state == 1:
            print("=" * 80)
            print("✅✅✅ 로그인 성공!")
            print("=" * 80)
            print()

            # 계좌 정보 조회
            try:
                accounts = context.GetAccountList()
                print(f"계좌 목록: {accounts}")
                print()

                if accounts:
                    print(f"✅ 계좌 조회 성공: {len(accounts)}개 계좌")
                else:
                    print("⚠️  계좌가 없습니다")

            except Exception as e:
                print(f"⚠️  계좌 조회 실패: {e}")

            print()
            print("=" * 80)
            print("  테스트 완료!")
            print("=" * 80)
            print()
            print("다음 테스트:")
            print("  python tests\\manual\\test_koapy_advanced.py")
            print()

        else:
            print("❌ 로그인 실패")
            print(f"   연결 상태: {state} (1=연결됨, 0=연결안됨)")

except KeyboardInterrupt:
    print()
    print("⚠️  사용자가 중단했습니다")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    print()
    import traceback
    traceback.print_exc()

print()
print("Enter를 눌러 종료...")
input()
