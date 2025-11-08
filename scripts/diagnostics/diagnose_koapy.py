"""
koapy 상세 진단 도구 - 정확한 에러 메시지 확인
"""
import sys

print("=" * 80)
print("koapy 상세 진단 도구")
print("=" * 80)
print()

# 1. Python 환경 확인
print("[1] Python 환경")
print(f"   Python 버전: {sys.version}")
print(f"   Python 경로: {sys.executable}")
import struct
print(f"   비트: {struct.calcsize('P') * 8}-bit")
print()

# 2. 핵심 패키지 버전 확인
print("[2] 핵심 패키지 버전")
packages_to_check = [
    'protobuf', 'grpcio', 'koapy', 'PyQt5', 'pandas', 'numpy',
    'qtpy', 'wrapt', 'rx', 'Click', 'attrs'
]

for pkg in packages_to_check:
    try:
        import importlib.metadata as md
        version = md.version(pkg)
        print(f"   ✅ {pkg}: {version}")
    except Exception as e:
        print(f"   ❌ {pkg}: 설치되지 않음 ({e})")
print()

# 3. koapy 모듈 import 시도 (단계별)
print("[3] koapy import 단계별 테스트")
print()

# 3-1. 기본 import
print("   [3-1] import koapy")
try:
    import koapy
    print(f"   ✅ 성공: {koapy.__file__}")
except Exception as e:
    print(f"   ❌ 실패: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    print()
    print("koapy 기본 import에 실패했습니다.")
    print("더 이상 진행할 수 없습니다.")
    sys.exit(1)
print()

# 3-2. KiwoomOpenApiPlusEntrypoint import
print("   [3-2] from koapy import KiwoomOpenApiPlusEntrypoint")
try:
    from koapy import KiwoomOpenApiPlusEntrypoint
    print(f"   ✅ 성공")
except Exception as e:
    print(f"   ❌ 실패: {type(e).__name__}: {e}")
    print()
    print("   상세 에러:")
    import traceback
    traceback.print_exc()
    print()
    print("=" * 80)
    print("진단 결과: KiwoomOpenApiPlusEntrypoint import 실패")
    print("=" * 80)
    print()

    # 에러 유형별 해결책
    if "ModuleNotFoundError" in str(type(e).__name__):
        print("원인: 필요한 모듈이 설치되지 않았습니다.")
        print()
        print("해결책:")
        print("  pip install qtpy PyQt5 wrapt rx attrs")
    elif "AttributeError" in str(type(e).__name__):
        print("원인: 모듈 속성 오류")
    elif "ImportError" in str(type(e).__name__):
        print("원인: Import 오류")
        print()
        print("해결책:")
        print("  1. pip uninstall -y koapy")
        print("  2. pip install --no-deps koapy")
        print("  3. 필요한 의존성 수동 설치")

    sys.exit(1)
print()

# 4. koapy 사용 가능 클래스 확인
print("[4] koapy 사용 가능 클래스")
try:
    import inspect
    classes = []
    for name, obj in inspect.getmembers(koapy):
        if inspect.isclass(obj) and not name.startswith('_'):
            classes.append(name)

    print(f"   찾은 클래스: {len(classes)}개")
    for cls in classes[:15]:
        print(f"   - {cls}")
    if len(classes) > 15:
        print(f"   ... 외 {len(classes) - 15}개")
except Exception as e:
    print(f"   ❌ 오류: {e}")
print()

# 5. PyQt5 확인
print("[5] PyQt5 상태")
try:
    from PyQt5 import QtCore
    print(f"   ✅ PyQt5 버전: {QtCore.PYQT_VERSION_STR}")
    print(f"   ✅ Qt 버전: {QtCore.QT_VERSION_STR}")
except Exception as e:
    print(f"   ❌ PyQt5 로드 실패: {e}")
print()

# 6. qtpy 상태
print("[6] qtpy 상태")
try:
    import qtpy
    print(f"   ✅ qtpy 버전: {qtpy.__version__ if hasattr(qtpy, '__version__') else '알 수 없음'}")
    print(f"   ✅ API: {qtpy.API}")
    print(f"   ✅ API_NAME: {qtpy.API_NAME}")
except Exception as e:
    print(f"   ❌ qtpy 로드 실패: {e}")
print()

print("=" * 80)
print("✅ 모든 진단 완료!")
print("=" * 80)
print()
print("koapy가 정상적으로 import 되었습니다.")
print()
print("다음 단계:")
print("  python tests\\manual\\test_koapy_simple.py")
print("  python tests\\manual\\test_koapy_advanced.py")
print()
