#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAPI 서버 데이터 수신 테스트
32비트 OpenAPI 서버에서 20가지 종목 데이터를 받아오는지 확인
"""

import requests
import json
from datetime import datetime
from pathlib import Path


def save_json(data, filename):
    """JSON 파일로 저장"""
    output_dir = Path("debug_output")
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"   💾 저장: {filepath}")
    return filepath


def test_openapi_server():
    """OpenAPI 서버 테스트"""
    print("=" * 80)
    print("OpenAPI Server Data Test")
    print("=" * 80)

    base_url = "http://127.0.0.1:5001"

    # 1. Health check
    print("\n1️⃣ Health Check")
    print("-" * 80)
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        health = response.json()
        print(f"   Status: {health.get('status')}")
        print(f"   Server Ready: {health.get('server_ready')}")
        print(f"   OpenAPI Connected: {health.get('openapi_connected')}")
        print(f"   Connection Status: {health.get('connection_status')}")
        print(f"   Accounts: {health.get('accounts')}")

        if health.get('connection_status') != 'connected':
            print("\n❌ OpenAPI가 연결되지 않았습니다!")
            print("   start_with_openapi.bat 를 실행하고 로그인하세요.")
            return

    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        print("   OpenAPI 서버가 실행 중인지 확인하세요.")
        return

    # 2. 종합 데이터 조회
    print("\n2️⃣ Comprehensive Data Test")
    print("-" * 80)

    test_stocks = [
        ('005930', '삼성전자'),
        ('000660', 'SK하이닉스'),
        ('035420', 'NAVER'),
    ]

    all_results = []

    for stock_code, stock_name in test_stocks:
        print(f"\n📊 {stock_code} ({stock_name})")
        print("-" * 60)

        try:
            print("   요청 중...")
            response = requests.get(
                f"{base_url}/stock/{stock_code}/comprehensive",
                timeout=120  # 2분 타임아웃 (17개 TR * 0.3초 대기)
            )

            if response.status_code == 200:
                data = response.json()

                # 결과 요약
                success_count = data.get('success_count', 0)
                total_count = data.get('total_count', 0)

                print(f"\n   ✅ 수신 성공: {success_count}/{total_count}")

                # 데이터 상세 출력
                print(f"\n   📋 수신 데이터:")
                for key, value in data.get('data', {}).items():
                    if value and 'error' not in value:
                        # 데이터 크기 확인
                        if isinstance(value, dict):
                            if 'items' in value:
                                item_count = len(value['items'])
                                print(f"      ✅ {key}: {item_count} items")
                            else:
                                field_count = len(value)
                                print(f"      ✅ {key}: {field_count} fields")
                        else:
                            print(f"      ✅ {key}")
                    else:
                        error_msg = value.get('error', 'unknown') if isinstance(value, dict) else str(value)
                        print(f"      ❌ {key}: {error_msg}")

                # JSON 저장
                save_json(data, f"openapi_comprehensive_{stock_code}")
                all_results.append(data)

            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text}")

        except requests.Timeout:
            print(f"   ❌ 타임아웃 (120초 초과)")
        except Exception as e:
            print(f"   ❌ 오류: {e}")
            import traceback
            traceback.print_exc()

        print()

    # 3. 전체 요약
    if all_results:
        print("\n3️⃣ Summary")
        print("=" * 80)

        total_success = 0
        total_requests = 0

        for result in all_results:
            code = result.get('stock_code')
            success = result.get('success_count', 0)
            total = result.get('total_count', 0)
            print(f"   {code}: {success}/{total}")
            total_success += success
            total_requests += total

        print(f"\n   Overall: {total_success}/{total_requests}")

        # 전체 결과 저장
        save_json({'results': all_results}, 'openapi_summary')

    print("\n✅ 테스트 완료!\n")


if __name__ == '__main__':
    try:
        test_openapi_server()
    except KeyboardInterrupt:
        print("\n\n중단됨")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
