"""
Quick koapy import test with QT_API fix
"""
import os
import sys

# CRITICAL: Set QT_API BEFORE importing anything else
os.environ['QT_API'] = 'pyqt5'

print("=" * 80)
print("Quick koapy Import Test")
print("=" * 80)
print()

print(f"QT_API environment variable: {os.environ.get('QT_API')}")
print()

try:
    print("[1/3] Testing PyQt5...")
    from PyQt5 import QtCore
    print(f"    ✅ PyQt5 version: {QtCore.PYQT_VERSION_STR}")
    print()
except Exception as e:
    print(f"    ❌ PyQt5 failed: {e}")
    sys.exit(1)

try:
    print("[2/3] Testing qtpy...")
    import qtpy
    print(f"    ✅ qtpy API: {qtpy.API_NAME}")
    print()
except Exception as e:
    print(f"    ❌ qtpy failed: {e}")
    sys.exit(1)

try:
    print("[3/3] Testing koapy import...")
    from koapy import KiwoomOpenApiPlusEntrypoint
    print("    ✅ koapy import successful!")
    print()
except Exception as e:
    print(f"    ❌ koapy import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("🎉 SUCCESS! All imports working!")
print("=" * 80)
print()
print("Next step:")
print("  python tests\\manual\\test_koapy_simple.py")
print()
