#!/usr/bin/env python
"""
koapy 구조 진단 및 올바른 import 방법 찾기
"""

import sys
import os

print("="*80)
print("🔍 koapy 패키지 구조 진단")
print("="*80)

print(f"\n🐍 Python: {sys.version}")
print(f"📍 경로: {sys.executable}")

# 1. koapy 설치 확인
print("\n" + "="*80)
print("STEP 1: koapy 설치 확인")
print("="*80)

try:
    import koapy
    print(f"✅ koapy 설치됨")
    print(f"   버전: {koapy.__version__}")
    print(f"   경로: {koapy.__file__}")
except ImportError as e:
    print(f"❌ koapy import 실패: {e}")
    sys.exit(1)

# 2. koapy 내부 구조 확인
print("\n" + "="*80)
print("STEP 2: koapy 패키지 구조")
print("="*80)

koapy_dir = os.path.dirname(koapy.__file__)
print(f"\nkoapy 디렉토리: {koapy_dir}\n")

# koapy 내부 모듈 리스트
print("📦 koapy 내부 모듈:")
for item in dir(koapy):
    if not item.startswith('_'):
        print(f"   - {item}")

# 3. KiwoomOpenApiContext 찾기
print("\n" + "="*80)
print("STEP 3: KiwoomOpenApiContext 찾기")
print("="*80)

import_methods = [
    # 방법 1: 직접 import (0.8.x 방식)
    ("from koapy import KiwoomOpenApiContext",
     lambda: __import__('koapy', fromlist=['KiwoomOpenApiContext']).KiwoomOpenApiContext),

    # 방법 2: context 서브모듈
    ("from koapy.context import KiwoomOpenApiContext",
     lambda: __import__('koapy.context', fromlist=['KiwoomOpenApiContext']).KiwoomOpenApiContext),

    # 방법 3: openapi 서브모듈
    ("from koapy.openapi import KiwoomOpenApiContext",
     lambda: __import__('koapy.openapi', fromlist=['KiwoomOpenApiContext']).KiwoomOpenApiContext),

    # 방법 4: backend
    ("from koapy.backend import KiwoomOpenApiContext",
     lambda: __import__('koapy.backend', fromlist=['KiwoomOpenApiContext']).KiwoomOpenApiContext),

    # 방법 5: backend.kiwoom_open_api_plus
    ("from koapy.backend.kiwoom_open_api_plus import KiwoomOpenApiContext",
     lambda: __import__('koapy.backend.kiwoom_open_api_plus', fromlist=['KiwoomOpenApiContext']).KiwoomOpenApiContext),

    # 방법 6: utils
    ("from koapy.utils.KiwoomOpenApiContext import KiwoomOpenApiContext",
     lambda: __import__('koapy.utils.KiwoomOpenApiContext', fromlist=['KiwoomOpenApiContext']).KiwoomOpenApiContext),
]

successful_methods = []

for import_str, import_func in import_methods:
    try:
        cls = import_func()
        print(f"✅ 성공: {import_str}")
        print(f"   클래스: {cls}")
        print(f"   모듈: {cls.__module__}")
        successful_methods.append((import_str, cls))
    except (ImportError, AttributeError) as e:
        print(f"❌ 실패: {import_str}")
        print(f"   에러: {e}")

# 4. 패키지 파일 탐색
print("\n" + "="*80)
print("STEP 4: koapy 디렉토리 구조 탐색")
print("="*80)

import os
from pathlib import Path

koapy_path = Path(koapy_dir)
print(f"\n📁 {koapy_path}:")

# 상위 3개 레벨만 탐색
for root, dirs, files in os.walk(koapy_path):
    level = root.replace(str(koapy_path), '').count(os.sep)
    if level > 2:  # 3레벨까지만
        continue

    indent = ' ' * 2 * level
    print(f'{indent}📂 {os.path.basename(root)}/')

    subindent = ' ' * 2 * (level + 1)
    for file in files:
        if file.endswith('.py'):
            print(f'{subindent}📄 {file}')

            # KiwoomOpenApiContext가 있는지 확인
            file_path = Path(root) / file
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if 'class KiwoomOpenApiContext' in content:
                        print(f'{subindent}   ⭐ KiwoomOpenApiContext 발견!')
                        print(f'{subindent}   경로: {file_path}')
            except:
                pass

# 5. 성공한 import 방법 요약
print("\n" + "="*80)
print("STEP 5: 결과 요약")
print("="*80)

if successful_methods:
    print(f"\n✅ {len(successful_methods)}개의 성공한 import 방법 발견:")
    for idx, (import_str, cls) in enumerate(successful_methods, 1):
        print(f"\n{idx}. {import_str}")
        print(f"   클래스 위치: {cls.__module__}")

    print("\n" + "="*80)
    print("💡 권장 사용법")
    print("="*80)

    best_method, best_cls = successful_methods[0]
    print(f"\n다음과 같이 사용하세요:")
    print(f"\n```python")
    print(f"{best_method}")
    print(f"")
    print(f"# 로그인 창 실행")
    print(f"with KiwoomOpenApiContext() as context:")
    print(f"    accounts = context.GetAccountList()")
    print(f"    print(f'계좌: {{accounts}}')")
    print(f"```")

else:
    print("\n❌ KiwoomOpenApiContext를 찾을 수 없습니다.")
    print("\n해결 방법:")
    print("1. koapy 재설치:")
    print("   pip uninstall koapy -y")
    print("   pip install koapy==0.8.3")
    print("")
    print("2. 또는 최신 버전 설치:")
    print("   pip install koapy --upgrade")

# 6. 간단한 로그인 테스트 (성공한 경우)
if successful_methods:
    print("\n" + "="*80)
    print("STEP 6: 로그인 창 테스트")
    print("="*80)

    try:
        from PyQt5.QtWidgets import QApplication

        best_import, best_cls = successful_methods[0]

        print(f"\n{best_import} 사용")
        print(f"\n🔑 로그인 창을 실행하시겠습니까? (y/n): ", end='')

        user_input = input().strip().lower()

        if user_input == 'y':
            print("\n로그인 창 실행 중...")
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)

            with best_cls() as context:
                print("✅ 로그인 성공!")
                accounts = context.GetAccountList()
                print(f"📊 계좌 수: {len(accounts)}")
                for idx, acc in enumerate(accounts, 1):
                    print(f"   {idx}. {acc}")
        else:
            print("\n로그인 테스트를 건너뜁니다.")

    except Exception as e:
        print(f"\n⚠️  로그인 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*80)
print("✅ 진단 완료")
print("="*80)
