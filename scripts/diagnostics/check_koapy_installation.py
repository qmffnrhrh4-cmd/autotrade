"""
koapy 설치 및 import 경로 확인 도구
"""
import sys
import subprocess

print("="*80)
print("koapy 설치 상태 확인")
print("="*80)
print()

# 1. pip list로 설치 확인
print("1️⃣ pip list 확인...")
result = subprocess.run(
    ['pip', 'list'],
    capture_output=True,
    text=True
)

koapy_found = False
for line in result.stdout.split('\n'):
    if 'koapy' in line.lower():
        print(f"   ✅ {line}")
        koapy_found = True

if not koapy_found:
    print("   ❌ koapy가 설치되지 않음")
    print()
    print("설치 명령:")
    print("   pip install koapy")
    sys.exit(1)

print()

# 2. import 시도
print("2️⃣ import 테스트...")

try:
    import koapy
    print(f"   ✅ koapy 모듈 import 성공")
    print(f"   경로: {koapy.__file__}")
    print(f"   버전: {koapy.__version__ if hasattr(koapy, '__version__') else '알 수 없음'}")
except ImportError as e:
    print(f"   ❌ import 실패: {e}")

print()

# 3. 세부 모듈 확인
print("3️⃣ 세부 모듈 import 테스트...")

modules_to_test = [
    'koapy.KiwoomOpenApiPlusEntrypoint',
    'koapy.context.KiwoomOpenApiContext',
    'koapy.grpc.KiwoomOpenApiServiceClient',
]

for module_path in modules_to_test:
    try:
        parts = module_path.split('.')
        if len(parts) == 2:
            module = __import__(parts[0], fromlist=[parts[1]])
            getattr(module, parts[1])
        elif len(parts) == 3:
            module = __import__('.'.join(parts[:2]), fromlist=[parts[2]])
            getattr(module, parts[2])

        print(f"   ✅ {module_path}")
    except Exception as e:
        print(f"   ❌ {module_path}: {e}")

print()

# 4. 사용 가능한 클래스 확인
print("4️⃣ 사용 가능한 koapy 클래스...")
try:
    import koapy
    import inspect

    classes = []
    for name, obj in inspect.getmembers(koapy):
        if inspect.isclass(obj) and not name.startswith('_'):
            classes.append(name)

    if classes:
        print(f"   찾은 클래스: {len(classes)}개")
        for cls in classes[:10]:  # 처음 10개만
            print(f"   - {cls}")
        if len(classes) > 10:
            print(f"   ... 외 {len(classes) - 10}개")
    else:
        print("   ⚠️ 클래스를 찾을 수 없음")
        print()
        print("   koapy 모듈 내용:")
        print(f"   {dir(koapy)}")

except Exception as e:
    print(f"   ❌ 오류: {e}")

print()

# 5. 올바른 import 방법 제시
print("="*80)
print("💡 koapy 사용 방법")
print("="*80)
print()

try:
    # 방법 1: KiwoomOpenApiPlusEntrypoint
    try:
        from koapy import KiwoomOpenApiPlusEntrypoint
        print("✅ 방법 1 가능:")
        print("   from koapy import KiwoomOpenApiPlusEntrypoint")
        print()
    except:
        print("❌ 방법 1 불가능")
        print()

    # 방법 2: KiwoomOpenApiContext
    try:
        from koapy import KiwoomOpenApiContext
        print("✅ 방법 2 가능:")
        print("   from koapy import KiwoomOpenApiContext")
        print()
    except:
        print("❌ 방법 2 불가능")
        print()

    # 방법 3: 전체 import
    try:
        import koapy
        print("✅ 방법 3 가능:")
        print("   import koapy")
        print(f"   사용 가능한 항목: {[x for x in dir(koapy) if not x.startswith('_')]}")
        print()
    except:
        print("❌ 방법 3 불가능")
        print()

except Exception as e:
    print(f"❌ 오류: {e}")

print("="*80)
