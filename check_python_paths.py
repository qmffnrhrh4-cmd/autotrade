"""
Python import 경로 확인
"""
import sys

print("=" * 80)
print("Python 경로 확인")
print("=" * 80)
print()

print(f"Python 실행 파일: {sys.executable}")
print(f"Python 버전: {sys.version}")
print()

print("sys.path:")
for i, path in enumerate(sys.path, 1):
    print(f"  {i}. {path}")
print()

print("=" * 80)
print("PyQt5 import 테스트")
print("=" * 80)
print()

try:
    import PyQt5
    print(f"✅ PyQt5 import 성공!")
    print(f"   경로: {PyQt5.__file__}")
    print(f"   버전: {PyQt5.Qt.PYQT_VERSION_STR}")
except Exception as e:
    print(f"❌ PyQt5 import 실패: {e}")
    import traceback
    traceback.print_exc()

print()

try:
    from PyQt5.QtWidgets import QApplication
    print(f"✅ PyQt5.QtWidgets.QApplication import 성공!")
except Exception as e:
    print(f"❌ PyQt5.QtWidgets.QApplication import 실패: {e}")
    import traceback
    traceback.print_exc()

print()

print("=" * 80)
print("site-packages 확인")
print("=" * 80)
print()

import site
print("site.getsitepackages():")
for pkg_path in site.getsitepackages():
    print(f"  - {pkg_path}")

print()
print(f"site.getusersitepackages(): {site.getusersitepackages()}")

print()
input("종료하려면 Enter를 누르세요...")
