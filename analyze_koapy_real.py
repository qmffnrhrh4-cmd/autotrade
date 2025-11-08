#!/usr/bin/env python
"""
koapy 실제 구조 완전 분석
- 모든 파일 탐색
- 모든 클래스 나열
- 실제 사용 가능한 API 찾기
"""

import sys
import os
import inspect
from pathlib import Path

print("="*80)
print("🔍 koapy 실제 구조 완전 분석")
print("="*80)

# 1. koapy import 확인
try:
    import koapy
    print(f"\n✅ koapy v{koapy.__version__}")
    print(f"📁 위치: {koapy.__file__}")
    koapy_dir = Path(koapy.__file__).parent
except ImportError as e:
    print(f"❌ koapy를 찾을 수 없습니다: {e}")
    sys.exit(1)

print("\n" + "="*80)
print("📦 koapy 패키지의 모든 모듈")
print("="*80)

# koapy의 모든 속성 나열
print("\nkoapy 패키지에서 직접 접근 가능한 항목:")
for name in dir(koapy):
    if not name.startswith('_'):
        obj = getattr(koapy, name)
        obj_type = type(obj).__name__
        print(f"  - {name} ({obj_type})")

print("\n" + "="*80)
print("📂 koapy 디렉토리의 모든 Python 파일")
print("="*80)

all_py_files = []
for root, dirs, files in os.walk(koapy_dir):
    # __pycache__ 제외
    dirs[:] = [d for d in dirs if d != '__pycache__']

    for file in files:
        if file.endswith('.py'):
            file_path = Path(root) / file
            rel_path = file_path.relative_to(koapy_dir)
            all_py_files.append((file_path, rel_path))
            print(f"  {rel_path}")

print(f"\n총 {len(all_py_files)}개 파일")

print("\n" + "="*80)
print("🔍 'Context', 'Login', 'Api', 'Kiwoom' 키워드 검색")
print("="*80)

important_findings = []

for file_path, rel_path in all_py_files:
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

            # class 정의 찾기
            for keyword in ['Context', 'Login', 'Api', 'Kiwoom', 'QAxWidget', 'Control']:
                if f'class {keyword}' in content or f'class Kiwoom{keyword}' in content:
                    # 실제 클래스 이름 추출
                    import re
                    classes = re.findall(r'class\s+(\w*' + keyword + r'\w*)\s*[:\(]', content)
                    if classes:
                        for cls_name in classes:
                            important_findings.append({
                                'file': rel_path,
                                'class': cls_name,
                                'keyword': keyword
                            })
                            print(f"  ⭐ {cls_name} → {rel_path}")
    except:
        pass

print("\n" + "="*80)
print("🎯 import 가능한 모듈 탐색")
print("="*80)

# koapy의 하위 모듈들을 동적으로 import 시도
possible_modules = [
    'koapy.backend',
    'koapy.backend.kiwoom_open_api_plus',
    'koapy.backend.kiwoom_open_api_plus.core',
    'koapy.backend.cybos_plus',
    'koapy.context',
    'koapy.grpc',
    'koapy.cli',
    'koapy.utils',
]

successfully_imported = []

for module_name in possible_modules:
    try:
        module = __import__(module_name, fromlist=[''])
        print(f"\n✅ {module_name}")

        # 모듈의 모든 멤버 출력
        members = [name for name in dir(module) if not name.startswith('_')]
        if members:
            print(f"   멤버: {', '.join(members[:10])}")  # 처음 10개만
            if len(members) > 10:
                print(f"   ... 외 {len(members)-10}개")

        successfully_imported.append(module_name)

        # Context나 Kiwoom이 들어간 클래스 찾기
        for name in members:
            if 'Context' in name or 'Kiwoom' in name or 'Control' in name:
                obj = getattr(module, name)
                if inspect.isclass(obj):
                    print(f"   ⭐⭐⭐ 클래스 발견: {name}")
                    print(f"       Import: from {module_name} import {name}")

    except ImportError as e:
        print(f"❌ {module_name}: {str(e)[:50]}")

print("\n" + "="*80)
print("📋 발견된 중요 클래스 목록")
print("="*80)

if important_findings:
    for finding in important_findings:
        print(f"\n클래스: {finding['class']}")
        print(f"파일: {finding['file']}")

        # import 경로 추측
        module_path = str(finding['file']).replace('/', '.').replace('\\', '.').replace('.py', '')
        module_path = f"koapy.{module_path}" if not module_path.startswith('koapy') else module_path
        print(f"추측 Import: from {module_path} import {finding['class']}")
else:
    print("⚠️  관련 클래스를 찾지 못했습니다.")

print("\n" + "="*80)
print("🧪 실제 로그인 시도")
print("="*80)

print("\nkoapy 0.8.x에서 로그인하는 방법을 찾습니다...")

# 방법 1: KiwoomOpenApiPlusEntrypoint
try:
    from koapy.backend.kiwoom_open_api_plus.core.KiwoomOpenApiPlusEntrypoint import KiwoomOpenApiPlusEntrypoint
    print("✅ 방법 1: KiwoomOpenApiPlusEntrypoint 발견!")
    print("   from koapy.backend.kiwoom_open_api_plus.core.KiwoomOpenApiPlusEntrypoint import KiwoomOpenApiPlusEntrypoint")

    print("\n로그인을 시도하시겠습니까? (y/n): ", end='')
    if input().strip().lower() == 'y':
        print("\n로그인 창 실행 중...")

        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)

        api = KiwoomOpenApiPlusEntrypoint()
        api.login()

        accounts = api.GetAccountList()
        print(f"✅ 계좌: {accounts}")

except ImportError as e:
    print(f"❌ 방법 1 실패: {e}")

# 방법 2: with 컨텍스트 매니저 찾기
print("\n\nwith 문으로 사용 가능한 클래스 찾기...")
for module_name in successfully_imported:
    try:
        module = __import__(module_name, fromlist=[''])
        for name in dir(module):
            if not name.startswith('_'):
                obj = getattr(module, name)
                if inspect.isclass(obj):
                    # __enter__, __exit__ 메서드가 있는지 확인 (컨텍스트 매니저)
                    if hasattr(obj, '__enter__') and hasattr(obj, '__exit__'):
                        print(f"✅ 컨텍스트 매니저 발견: {module_name}.{name}")
    except:
        pass

print("\n" + "="*80)
print("💡 권장 사항")
print("="*80)

print("\n1. koapy 공식 문서 확인:")
print("   GitHub: https://github.com/elbakramer/koapy")
print("   pip show koapy")

print("\n2. koapy 예제 파일 확인:")
examples_dir = koapy_dir / 'examples'
if examples_dir.exists():
    print(f"   {examples_dir}")
    for ex_file in examples_dir.glob('*.py'):
        print(f"   - {ex_file.name}")
else:
    print("   examples 디렉토리를 찾을 수 없습니다")

print("\n3. 또는 환경을 Python 3.9로 재생성:")
print("   conda remove -n autotrade_32 --all -y")
print("   conda create -n autotrade_32 python=3.9 -y")
print("   conda activate autotrade_32")
print("   pip install koapy==0.8.3 PyQt5==5.15.9")

print("\n" + "="*80)
