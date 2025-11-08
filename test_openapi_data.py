#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAPI 서버를 통한 데이터 수집 테스트

먼저 openapi_server.py를 kiwoom32 환경에서 실행한 후
이 스크립트를 64비트 환경에서 실행하세요.
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime


def save_json(data, filename):
    """JSON 파일로 저장 - tests/ 폴더"""
    output_dir = Path("tests")
    output_dir.mkdir(exist_ok=True)

    filepath = output_dir / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"   💾 저장: {filepath}")
    return filepath


def test_openapi_server():
    """OpenAPI 서버 테스트"""
    base_url = "http://localhost:5001"

    print("=" * 80)
    print("  OpenAPI 서버 데이터 수집 테스트")
    print("=" * 80)

    # 1. 서버 상태 확인
    print("\n1️⃣  서버 상태 확인")
    try:
        response = requests.get(f"{base_url}/status", timeout=5)
        status = response.json()
        print(f"   ✅ 서버 상태: {status}")
        save_json(status, 'server_status')
    except Exception as e:
        print(f"   ❌ 서버 연결 실패: {e}")
        print("\n💡 먼저 다른 터미널에서 openapi_server.py를 실행하세요:")
        print("   conda activate kiwoom32")
        print("   python openapi_server.py")
        return

    # 2. 계좌 정보
    print("\n2️⃣  계좌 정보")
    try:
        response = requests.get(f"{base_url}/accounts", timeout=5)
        accounts = response.json()
        print(f"   ✅ 계좌: {accounts}")
        save_json(accounts, 'accounts')
    except Exception as e:
        print(f"   ❌ 실패: {e}")

    # 3. 종목 정보 (마스터 API 사용)
    print("\n3️⃣  종목 정보")
    test_stocks = ['005930', '000660', '035420']

    for stock_code in test_stocks:
        print(f"\n   📊 {stock_code}")
        try:
            # 종목명 조회
            response = requests.post(
                f"{base_url}/api/get_master_code_name",
                json={'code': stock_code},
                timeout=5
            )
            if response.status_code == 200:
                stock_name = response.json().get('result', '')
                print(f"      종목명: {stock_name}")

            # 현재가 조회
            response = requests.post(
                f"{base_url}/api/get_master_last_price",
                json={'code': stock_code},
                timeout=5
            )
            if response.status_code == 200:
                price = response.json().get('result', '')
                print(f"      현재가: {price}")

        except Exception as e:
            print(f"      ❌ 실패: {e}")

    # 4. 사용 가능한 엔드포인트 확인
    print("\n4️⃣  서버 엔드포인트 확인")
    endpoints = [
        '/status',
        '/accounts',
        '/api/get_master_code_name',
        '/api/get_master_last_price',
        '/api/get_login_info',
    ]

    available_endpoints = []
    for endpoint in endpoints:
        try:
            if endpoint.startswith('/api/'):
                response = requests.post(f"{base_url}{endpoint}", json={}, timeout=2)
            else:
                response = requests.get(f"{base_url}{endpoint}", timeout=2)

            if response.status_code in [200, 400]:  # 400도 엔드포인트는 존재
                available_endpoints.append(endpoint)
                print(f"   ✅ {endpoint}")
        except:
            print(f"   ❌ {endpoint}")

    save_json({'endpoints': available_endpoints}, 'available_endpoints')

    # 완료
    print("\n" + "=" * 80)
    print("  ✅ 테스트 완료")
    print("=" * 80)
    print(f"\n📁 결과: tests/ 폴더")


if __name__ == '__main__':
    test_openapi_server()
