#!/usr/bin/env python3
"""
ka90009와 ka10065 응답 구조 상세 디버깅
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

# 로깅 레벨을 DEBUG로 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

from core.rest_client import KiwoomRESTClient


def get_last_trading_date():
    """간단한 거래일 계산"""
    today = datetime.now()
    if today.weekday() == 5:  # 토요일
        today = today - timedelta(days=1)
    elif today.weekday() == 6:  # 일요일
        today = today - timedelta(days=2)
    return today.strftime("%Y%m%d")


def debug_ka90009():
    """ka90009 응답 구조 확인"""
    print("\n" + "="*80)
    print("ka90009 (외국인기관매매) 응답 구조 디버깅")
    print("="*80)

    client = KiwoomRESTClient()
    last_trading_date = get_last_trading_date()

    body = {
        "mrkt_tp": "001",
        "amt_qty_tp": "1",
        "qry_dt_tp": "1",
        "date": last_trading_date,
        "stex_tp": "1"
    }

    print(f"\n요청 파라미터:")
    print(json.dumps(body, indent=2, ensure_ascii=False))

    response = client.request(api_id="ka90009", body=body, path="rkinfo")

    if response:
        print(f"\nreturn_code: {response.get('return_code')}")
        print(f"return_msg: {response.get('return_msg')}")

        # 모든 키 출력
        print(f"\n응답의 모든 키: {list(response.keys())}")

        # 데이터 키 찾기
        metadata_keys = {'return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key'}
        data_keys = [k for k in response.keys() if k not in metadata_keys]

        print(f"\n데이터 키들: {data_keys}")

        # 각 키의 내용 확인
        for key in data_keys:
            val = response.get(key)
            print(f"\n키: '{key}'")
            print(f"  타입: {type(val)}")

            if isinstance(val, list):
                print(f"  길이: {len(val)}")
                if len(val) > 0:
                    print(f"  첫 번째 항목 타입: {type(val[0])}")
                    if isinstance(val[0], dict):
                        print(f"  첫 번째 항목 키들: {list(val[0].keys())}")
                        print(f"\n  첫 번째 항목 전체 데이터:")
                        print(json.dumps(val[0], indent=4, ensure_ascii=False))
                        print(f"\n  두 번째 항목 전체 데이터:")
                        if len(val) > 1:
                            print(json.dumps(val[1], indent=4, ensure_ascii=False))
                        print(f"\n  세 번째 항목 전체 데이터:")
                        if len(val) > 2:
                            print(json.dumps(val[2], indent=4, ensure_ascii=False))
    else:
        print("❌ 응답 없음")


def debug_ka10065():
    """ka10065 응답 구조 확인"""
    print("\n" + "="*80)
    print("ka10065 (장중투자자별매매) 응답 구조 디버깅")
    print("="*80)

    client = KiwoomRESTClient()

    body = {
        "trde_tp": "1",
        "mrkt_tp": "001",
        "orgn_tp": "9000"
    }

    print(f"\n요청 파라미터:")
    print(json.dumps(body, indent=2, ensure_ascii=False))

    response = client.request(api_id="ka10065", body=body, path="rkinfo")

    if response:
        print(f"\nreturn_code: {response.get('return_code')}")
        print(f"return_msg: {response.get('return_msg')}")

        # 모든 키 출력
        print(f"\n응답의 모든 키: {list(response.keys())}")

        # 데이터 키 찾기
        metadata_keys = {'return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key'}
        data_keys = [k for k in response.keys() if k not in metadata_keys]

        print(f"\n데이터 키들: {data_keys}")

        # 각 키의 내용 확인
        for key in data_keys:
            val = response.get(key)
            print(f"\n키: '{key}'")
            print(f"  타입: {type(val)}")

            if isinstance(val, list):
                print(f"  길이: {len(val)}")
                if len(val) > 0:
                    print(f"  첫 번째 항목 타입: {type(val[0])}")
                    if isinstance(val[0], dict):
                        print(f"  첫 번째 항목 키들: {list(val[0].keys())}")
                        print(f"\n  첫 번째 항목 전체 데이터:")
                        print(json.dumps(val[0], indent=4, ensure_ascii=False))
                        print(f"\n  두 번째 항목 전체 데이터:")
                        if len(val) > 1:
                            print(json.dumps(val[1], indent=4, ensure_ascii=False))
                        print(f"\n  세 번째 항목 전체 데이터:")
                        if len(val) > 2:
                            print(json.dumps(val[2], indent=4, ensure_ascii=False))
    else:
        print("❌ 응답 없음")


def main():
    print("\n" + "="*80)
    print("API 응답 구조 상세 디버깅")
    print("="*80)

    try:
        # 1. ka90009 디버깅
        debug_ka90009()

        # 2. ka10065 디버깅
        debug_ka10065()

        print("\n" + "="*80)
        print("디버깅 완료!")
        print("="*80)
        print("\n위 출력에서:")
        print("1. '첫 번째 항목 키들'을 확인하세요")
        print("2. 실제 데이터에서 종목명과 현재가 필드명을 찾으세요")
        print("3. 예상 필드명: stk_nm (종목명), cur_prc (현재가)")
        print("="*80)

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == '__main__':
    main()
