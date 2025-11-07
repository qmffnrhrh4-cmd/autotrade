"""
koapy SIGNAL 호환성 패치

Python 3.11과 최신 PyQt5에서 제거된 SIGNAL을 추가
"""
import os
import sys
from pathlib import Path

print("="*80)
print("koapy SIGNAL 호환성 패치")
print("="*80)
print()

# koapy 설치 경로 찾기
try:
    import koapy
    koapy_path = Path(koapy.__file__).parent
    print(f"koapy 설치 경로: {koapy_path}")
except ImportError:
    print("❌ koapy가 설치되지 않았습니다!")
    sys.exit(1)

# 패치할 파일 경로
patch_file = koapy_path / "compat" / "pyside2" / "QtCore.py"

if not patch_file.exists():
    print(f"❌ 패치 파일을 찾을 수 없습니다: {patch_file}")
    print()
    print("대체 경로 확인 중...")

    # 다른 가능한 경로들
    alternative_paths = [
        koapy_path / "compat" / "QtCore.py",
        koapy_path / "utils" / "QtCore.py",
    ]

    for alt_path in alternative_paths:
        if alt_path.exists():
            patch_file = alt_path
            print(f"✅ 대체 경로 발견: {patch_file}")
            break
    else:
        print("❌ 어떤 경로에서도 QtCore.py를 찾을 수 없습니다.")
        print()
        print("수동 패치 방법:")
        print("1. 다음 파일을 찾으세요:")
        print(f"   {koapy_path}\\compat\\pyside2\\QtCore.py")
        print()
        print("2. 파일의 마지막에 다음 코드를 추가하세요:")
        print()
        print("# Compatibility for Python 3.11 / PyQt5")
        print("# SIGNAL was removed from PyQt5, so we define it here")
        print("def SIGNAL(signal_name):")
        print('    """Dummy SIGNAL function for compatibility"""')
        print("    return signal_name")
        print()
        sys.exit(1)

print(f"패치 파일: {patch_file}")
print()

# 파일 읽기
try:
    with open(patch_file, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"❌ 파일 읽기 실패: {e}")
    sys.exit(1)

# SIGNAL이 이미 정의되어 있는지 확인
if 'def SIGNAL' in content or 'SIGNAL =' in content:
    print("⚠️  SIGNAL이 이미 정의되어 있습니다.")
    print("   패치가 이미 적용되었거나 필요하지 않습니다.")
    print()
else:
    # 백업
    backup_file = patch_file.with_suffix('.py.bak')
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 백업 파일: {backup_file}")
    except Exception as e:
        print(f"⚠️  백업 실패 (계속 진행): {e}")

    # 패치 코드 추가
    patch_code = '''

# ============================================
# Compatibility patch for Python 3.11 / PyQt5
# ============================================
# SIGNAL was removed from modern PyQt5/PySide2
# Define it here for backward compatibility

def SIGNAL(signal_name):
    """
    Dummy SIGNAL function for compatibility with old Qt code.

    In old-style Qt signal/slot syntax, SIGNAL() was used like:
        SIGNAL("clicked()")

    Modern Qt uses new-style connections without SIGNAL().
    This is a compatibility shim for legacy code.
    """
    return signal_name

# Also export SIGNAL
__all__ = list(globals().keys())
if 'SIGNAL' not in __all__:
    __all__.append('SIGNAL')
'''

    # 파일 끝에 패치 추가
    new_content = content + patch_code

    # 파일 저장
    try:
        with open(patch_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ 패치 적용 완료!")
    except Exception as e:
        print(f"❌ 패치 적용 실패: {e}")
        sys.exit(1)

print()
print("="*80)
print("패치 완료!")
print("="*80)
print()
print("다음 명령으로 테스트하세요:")
print("   python quick_test.py")
print()
