#!/usr/bin/env python3
"""
API 응답 구조 디버깅 스크립트
ka90009와 ka10065의 실제 응답을 확인합니다.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from core.rest_client import KiwoomRESTClient


def get_last_trading_date():
    """간단한 거래일 계산 (주말 제외)"""
    today = datetime.now()
    # 토요일(5), 일요일(6)이면 금요일로
    if today.weekday() == 5:  # 토요일
        today = today - timedelta(days=1)
    elif today.weekday() == 6:  # 일요일
        today = today - timedelta(days=2)
    return today.strftime("%Y%m%d")


def debug_ka90009():
    """ka90009 (외국인기관매매) 디버깅"""
    print("=" * 80)
    print("ka90009 (외국인기관매매) 응답 구조 확인")
    print("=" * 80)

    client = KiwoomRESTClient()
    last_trading_date = get_last_trading_date()

    # 테스트할 variant들
    variants = [
        {
            "name": "현재 구현 (qry_dt_tp=1, date=last_trading_date)",
            "body": {
                "mrkt_tp": "001",
                "amt_qty_tp": "1",
                "qry_dt_tp": "1",
                "date": last_trading_date,
                "stex_tp": "1"
            }
        },
        {
            "name": "Variant 1 (successful_apis.json)",
            "body": {
                "mrkt_tp": "001",
                "amt_qty_tp": "1",
                "qry_dt_tp": "1",
                "date": last_trading_date,
                "stex_tp": "1"
            }
        },
        {
            "name": "Variant 3 (qry_dt_tp=0, date 없음)",
            "body": {
                "mrkt_tp": "000",
                "amt_qty_tp": "1",
                "qry_dt_tp": "0",
                "stex_tp": "1"
            }
        }
    ]

    for variant in variants:
        print(f"\n{variant['name']}")
        print("-" * 80)
        print(f"Body: {json.dumps(variant['body'], indent=2, ensure_ascii=False)}")

        response = client.request(api_id="ka90009", body=variant['body'], path="rkinfo")

        if response:
            print(f"return_code: {response.get('return_code')}")
            print(f"return_msg: {response.get('return_msg')}")

            # 데이터 키 찾기
            metadata_keys = {'return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key'}
            data_keys = [k for k in response.keys() if k not in metadata_keys]

            print(f"데이터 키: {data_keys}")

            for key in data_keys:
                val = response.get(key)
                if isinstance(val, list):
                    print(f"\n{key}: list[{len(val)}]")
                    if len(val) > 0:
                        print(f"첫 번째 항목 키: {list(val[0].keys()) if isinstance(val[0], dict) else 'N/A'}")
                        print(f"샘플 데이터 (상위 3개):")
                        for i, item in enumerate(val[:3], 1):
                            if isinstance(item, dict):
                                print(f"  {i}. {json.dumps(item, indent=4, ensure_ascii=False)}")
                elif isinstance(val, dict):
                    print(f"\n{key}: dict")
                    print(json.dumps(val, indent=2, ensure_ascii=False))
                else:
                    print(f"\n{key}: {type(val).__name__} = {val}")
        else:
            print("❌ 응답 없음")

        print()


def debug_ka10065():
    """ka10065 (장중투자자별매매) 디버깅"""
    print("=" * 80)
    print("ka10065 (장중투자자별매매) 응답 구조 확인")
    print("=" * 80)

    client = KiwoomRESTClient()

    # 테스트할 variant들
    variants = [
        {
            "name": "현재 구현 (KOSPI, 외국인)",
            "body": {
                "trde_tp": "1",
                "mrkt_tp": "001",
                "orgn_tp": "9000"
            }
        },
        {
            "name": "Variant 1 (successful_apis.json)",
            "body": {
                "trde_tp": "1",
                "mrkt_tp": "001",
                "orgn_tp": "9000"
            }
        },
        {
            "name": "Variant 2 (KOSDAQ, 전체)",
            "body": {
                "trde_tp": "2",
                "mrkt_tp": "101",
                "orgn_tp": "9999"
            }
        }
    ]

    for variant in variants:
        print(f"\n{variant['name']}")
        print("-" * 80)
        print(f"Body: {json.dumps(variant['body'], indent=2, ensure_ascii=False)}")

        response = client.request(api_id="ka10065", body=variant['body'], path="rkinfo")

        if response:
            print(f"return_code: {response.get('return_code')}")
            print(f"return_msg: {response.get('return_msg')}")

            # 데이터 키 찾기
            metadata_keys = {'return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key'}
            data_keys = [k for k in response.keys() if k not in metadata_keys]

            print(f"데이터 키: {data_keys}")

            for key in data_keys:
                val = response.get(key)
                if isinstance(val, list):
                    print(f"\n{key}: list[{len(val)}]")
                    if len(val) > 0:
                        print(f"첫 번째 항목 키: {list(val[0].keys()) if isinstance(val[0], dict) else 'N/A'}")
                        print(f"샘플 데이터 (상위 3개):")
                        for i, item in enumerate(val[:3], 1):
                            if isinstance(item, dict):
                                print(f"  {i}. {json.dumps(item, indent=4, ensure_ascii=False)}")
                elif isinstance(val, dict):
                    print(f"\n{key}: dict")
                    print(json.dumps(val, indent=2, ensure_ascii=False))
                else:
                    print(f"\n{key}: {type(val).__name__} = {val}")
        else:
            print("❌ 응답 없음")

        print()


def main():
    print("\nAPI 응답 구조 디버깅 시작\n")

    try:
        # 1. ka90009 디버깅
        debug_ka90009()

        # 2. ka10065 디버깅
        debug_ka10065()

        print("=" * 80)
        print("디버깅 완료")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == '__main__':
    main()
