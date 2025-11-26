"""
미체결내역 및 최근거래내역 API 테스트
"""
import sys
import os
import json

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.rest_client import KiwoomRESTClient
from api.account import AccountAPI


def test_orders_api():
    print("=" * 60)
    print("미체결내역 / 최근거래내역 API 테스트")
    print("=" * 60)

    # 클라이언트 초기화 (싱글톤)
    print("\n[1] REST 클라이언트 초기화...")
    try:
        client = KiwoomRESTClient()
        print("   OK - 클라이언트 초기화 성공")
    except Exception as e:
        print(f"   FAIL - 클라이언트 초기화 실패: {e}")
        return

    # AccountAPI 초기화
    print("\n[2] AccountAPI 초기화...")
    try:
        account_api = AccountAPI(client)
        print("   OK - AccountAPI 초기화 성공")
    except Exception as e:
        print(f"   FAIL - AccountAPI 초기화 실패: {e}")
        return

    # 미체결 주문 조회
    print("\n" + "=" * 60)
    print("[3] 미체결 주문 조회 (ka10075)")
    print("=" * 60)
    try:
        result = account_api.get_outstanding_orders()
        if result:
            print(f"   return_code: {result.get('return_code')}")
            print(f"   return_msg: {result.get('return_msg')}")

            # 미체결 리스트 출력
            orders = result.get('nccs_list', []) or result.get('nccs_ord_list', []) or []
            if not orders:
                # 다른 키로 시도
                for key in result.keys():
                    if isinstance(result[key], list) and len(result[key]) > 0:
                        orders = result[key]
                        print(f"   (주문 리스트 키: {key})")
                        break

            print(f"\n   미체결 건수: {len(orders)}건")

            if orders:
                print("\n   [미체결 주문 목록]")
                for i, order in enumerate(orders[:5], 1):  # 최대 5건만 출력
                    print(f"   {i}. {order}")
            else:
                print("   미체결 주문 없음")

            # 전체 응답 키 출력
            print(f"\n   응답 키: {list(result.keys())}")
        else:
            print("   FAIL - 조회 결과 없음")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

    # 체결 주문 조회 (최근 거래내역)
    print("\n" + "=" * 60)
    print("[4] 체결 주문 조회 - 최근 거래내역 (ka10076)")
    print("=" * 60)
    try:
        result = account_api.get_executed_orders()
        if result:
            print(f"   return_code: {result.get('return_code')}")
            print(f"   return_msg: {result.get('return_msg')}")

            # 체결 리스트 출력
            orders = result.get('ccs_list', []) or result.get('ccs_ord_list', []) or []
            if not orders:
                # 다른 키로 시도
                for key in result.keys():
                    if isinstance(result[key], list) and len(result[key]) > 0:
                        orders = result[key]
                        print(f"   (주문 리스트 키: {key})")
                        break

            print(f"\n   체결 건수: {len(orders)}건")

            if orders:
                print("\n   [최근 체결 목록]")
                for i, order in enumerate(orders[:5], 1):  # 최대 5건만 출력
                    print(f"   {i}. {order}")
            else:
                print("   체결 주문 없음")

            # 전체 응답 키 출력
            print(f"\n   응답 키: {list(result.keys())}")
        else:
            print("   FAIL - 조회 결과 없음")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

    # 직접 API 호출 테스트
    print("\n" + "=" * 60)
    print("[5] 직접 API 호출 테스트")
    print("=" * 60)

    # ka10075 직접 호출
    print("\n   [5-1] ka10075 직접 호출...")
    try:
        result = client.call_verified_api(
            api_id='ka10075',
            variant_idx=1,
            body_override={'trde_tp': '0', 'all_stk_tp': '0'}
        )
        print(f"   return_code: {result.get('return_code')}")
        print(f"   return_msg: {result.get('return_msg')}")
        print(f"   응답 키: {list(result.keys())}")

        # JSON 출력 (일부)
        result_str = json.dumps(result, indent=2, ensure_ascii=False, default=str)
        if len(result_str) > 1000:
            print(f"\n   응답 (일부):\n{result_str[:1000]}...")
        else:
            print(f"\n   응답:\n{result_str}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

    # ka10076 직접 호출
    print("\n   [5-2] ka10076 직접 호출...")
    try:
        result = client.call_verified_api(
            api_id='ka10076',
            variant_idx=1,
            body_override={'qry_tp': '0'}
        )
        print(f"   return_code: {result.get('return_code')}")
        print(f"   return_msg: {result.get('return_msg')}")
        print(f"   응답 키: {list(result.keys())}")

        # JSON 출력 (일부)
        result_str = json.dumps(result, indent=2, ensure_ascii=False, default=str)
        if len(result_str) > 1000:
            print(f"\n   응답 (일부):\n{result_str[:1000]}...")
        else:
            print(f"\n   응답:\n{result_str}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    test_orders_api()
