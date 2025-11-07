"""
koapy PyQt5 버전 호환성 패치

QTimer.singleShot이 int를 요구하는데 float를 전달하는 버그 수정
"""
import os
import sys
from pathlib import Path

print("="*80)
print("koapy PyQt5 호환성 패치")
print("="*80)

# koapy 설치 경로 찾기
try:
    import koapy
    koapy_path = Path(koapy.__file__).parent
    print(f"\nkoapy 설치 경로: {koapy_path}")
except ImportError:
    print("\n❌ koapy가 설치되지 않았습니다!")
    sys.exit(1)

# 패치할 파일 경로
patch_file = koapy_path / "pyqt5" / "KiwoomOpenApiTrayApplication.py"

if not patch_file.exists():
    print(f"❌ 패치 파일을 찾을 수 없습니다: {patch_file}")
    sys.exit(1)

print(f"패치 파일: {patch_file}")

# 파일 읽기
with open(patch_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 백업
backup_file = patch_file.with_suffix('.py.bak')
with open(backup_file, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"백업 파일: {backup_file}")

# 패치 적용
# 문제 라인: QTimer.singleShot((timediff.total_seconds() + 1) * 1000, notify_and_wait_for_next)
# 수정: QTimer.singleShot(int((timediff.total_seconds() + 1) * 1000), notify_and_wait_for_next)

original = "QTimer.singleShot((timediff.total_seconds() + 1) * 1000, notify_and_wait_for_next)"
patched = "QTimer.singleShot(int((timediff.total_seconds() + 1) * 1000), notify_and_wait_for_next)"

if original in content:
    content = content.replace(original, patched)

    # 파일 저장
    with open(patch_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("\n✅ 패치 적용 완료!")
    print("\n다음 명령으로 테스트하세요:")
    print("   python test_koapy_quick.py")
else:
    print("\n⚠️  패치할 코드를 찾을 수 없습니다.")
    print("   koapy 버전이 다를 수 있습니다.")
    print("\n수동으로 다음 파일을 수정하세요:")
    print(f"   {patch_file}")
    print(f"\n   라인 251 근처:")
    print(f"   변경 전: {original}")
    print(f"   변경 후: {patched}")

print("\n" + "="*80)
