#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAPI 분봉 데이터 수신 테스트
32비트 OpenAPI 서버에서 분봉 데이터를 받아오는지 확인
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


def test_openapi_minute():
    """OpenAPI 분봉 데이터 테스트"""
    print("=" * 80)
    print("OpenAPI Minute Data Test")
    print("=" * 80)

    base_url = "http://127.0.0.1:5001"

    # 1. Health check
    print("\n1️⃣ Health Check")
    print("-" * 80)
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        health = response.json()
        print(f"   Status: {health.get('status')}")
        print(f"   OpenAPI Connected: {health.get('openapi_connected')}")
        print(f"   Connection Status: {health.get('connection_status')}")

        if health.get('connection_status') != 'connected':
            print("\n❌ OpenAPI가 연결되지 않았습니다!")
            print("   start_with_openapi.bat 를 실행하고 로그인하세요.")
            return

    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        print("   OpenAPI 서버가 실행 중인지 확인하세요.")
        return

    # 2. 분봉 데이터 조회
    print("\n2️⃣ Minute Data Test")
    print("-" * 80)

    test_stocks = [
        ('005930', '삼성전자'),
        ('000660', 'SK하이닉스'),
    ]

    intervals = [1, 3, 5, 10, 15, 30, 60]

    for stock_code, stock_name in test_stocks:
        print(f"\n📊 {stock_code} ({stock_name})")
        print("-" * 60)

        for interval in intervals:
            try:
                print(f"   {interval}분봉 요청 중...")
                response = requests.get(
                    f"{base_url}/stock/{stock_code}/minute/{interval}",
                    timeout=15
                )

                if response.status_code == 200:
                    data = response.json()

                    minute_data = data.get('data', {})
                    items = minute_data.get('items', [])

                    if items:
                        print(f"   ✅ {interval}분봉: {len(items)}개 캔들")

                        # 첫 번째 캔들 전체 출력 (디버깅용)
                        first = items[0]
                        print(f"      첫 번째 캔들 전체 데이터:")
                        for key, value in first.items():
                            print(f"        {key}: {value}")

                        # JSON 저장
                        save_json(data, f"minute_{stock_code}_{interval}min")
                    else:
                        print(f"   ⚠️  {interval}분봉: 데이터 없음 (주말/휴일)")

                else:
                    print(f"   ❌ HTTP {response.status_code}: {response.text}")

            except requests.Timeout:
                print(f"   ❌ {interval}분봉 타임아웃")
            except Exception as e:
                print(f"   ❌ {interval}분봉 오류: {e}")

        print()

    print("✅ 테스트 완료!\n")


if __name__ == '__main__':
    try:
        test_openapi_minute()
    except KeyboardInterrupt:
        print("\n\n중단됨")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
