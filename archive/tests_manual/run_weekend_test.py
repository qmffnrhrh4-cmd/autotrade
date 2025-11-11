#!/usr/bin/env python3
"""
주말/장마감 후 통합 테스트 실행 스크립트

이 스크립트는 다음을 테스트합니다:
1. REST API 호출 (가장 최근 영업일 데이터)
2. WebSocket 연결 및 구독 테스트
3. 전체 기능 통합 테스트 (시장탐색, 매수, AI분석, 매도, 차트)

키움증권 확인 사항:
- REST API로 장이 안 열렸을 때도 가장 최근일 데이터로 테스트 가능
- 웹소켓은 장 운영 시간에만 실시간 데이터 수신 (장 외 시간은 연결만 테스트)
"""
import sys
import asyncio
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def print_banner():
    """배너 출력"""
    print("\n" + "=" * 80)
    print("🧪 주말/장마감 후 통합 테스트")
    print("=" * 80)
    print(f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S (%A)')}")
    print("=" * 80)
    print()


async def test_rest_api():
    """REST API 테스트"""
    print("\n" + "┌" + "─" * 78 + "┐")
    print("│" + " " * 28 + "REST API 테스트" + " " * 35 + "│")
    print("└" + "─" * 78 + "┘")

    try:
        from features.test_mode_manager import TestModeManager

        manager = TestModeManager()

        # 테스트 모드 활성화 확인
        if manager.check_and_activate_test_mode():
            print(f"✅ 테스트 모드 활성화됨")
            print(f"   사용할 데이터 날짜: {manager.test_date}")
            print()

            # 전체 기능 테스트 실행
            results = await manager.run_comprehensive_test()

            # 요약 출력
            print("\n📊 REST API 테스트 요약")
            print("─" * 80)

            if results and "tests" in results:
                for test_name, test_result in results["tests"].items():
                    status = "✅" if test_result.get("success") else "❌"
                    print(f"  {status} {test_name.replace('_', ' ').title()}")

            return True
        else:
            print("⚠️  정규 장 시간입니다. 실시간 모드로 실행됩니다.")
            print("   (테스트 모드는 주말 또는 장 마감 시간에만 활성화됩니다)")
            return False

    except Exception as e:
        print(f"❌ REST API 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_websocket():
    """WebSocket 테스트"""
    print("\n" + "┌" + "─" * 78 + "┐")
    print("│" + " " * 26 + "WebSocket 연결 테스트" + " " * 31 + "│")
    print("└" + "─" * 78 + "┘")

    try:
        from config import get_credentials
        import websockets

        credentials = get_credentials()
        ws_url = credentials.KIWOOM_WEBSOCKET_URL
        appkey = credentials.KIWOOM_REST_APPKEY

        print(f"WebSocket URL: {ws_url}")
        print("연결 시도 중...")

        # WebSocket 연결 테스트 (5초 타임아웃)
        async with asyncio.timeout(5):
            ws = await websockets.connect(ws_url)
            print("✅ WebSocket 연결 성공")

            # Ping 테스트
            await ws.ping()
            print("✅ Ping 응답 성공")

            await ws.close()
            print("✅ WebSocket 연결 정상 종료")

        print("\n⚠️  참고: 장 운영 시간이 아니므로 실시간 데이터는 수신되지 않을 수 있습니다.")
        print("   실시간 데이터 테스트는 장 운영 시간(09:00-15:30)에 실행하세요.")

        return True

    except asyncio.TimeoutError:
        print("❌ WebSocket 연결 타임아웃 (5초 초과)")
        return False
    except Exception as e:
        print(f"❌ WebSocket 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_trading_date_utils():
    """거래일 유틸리티 테스트"""
    print("\n" + "┌" + "─" * 78 + "┐")
    print("│" + " " * 26 + "거래일 유틸리티 테스트" + " " * 30 + "│")
    print("└" + "─" * 78 + "┘")

    try:
        from utils.trading_date import (
            get_last_trading_date,
            get_trading_date_with_fallback,
            is_market_hours,
            is_after_market_hours
        )

        print(f"가장 최근 거래일: {get_last_trading_date()}")
        print(f"장 운영 시간 여부: {is_market_hours()}")
        print(f"장 마감 후 여부: {is_after_market_hours()}")

        print(f"\n최근 5일 거래일:")
        recent_dates = get_trading_date_with_fallback(5)
        for i, date in enumerate(recent_dates, 1):
            print(f"  {i}. {date}")

        print("✅ 거래일 유틸리티 테스트 성공")
        return True

    except Exception as e:
        print(f"❌ 거래일 유틸리티 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_full_websocket_test():
    """전체 WebSocket 기능 테스트 (장 운영 시간에만 실행)"""
    print("\n" + "┌" + "─" * 78 + "┐")
    print("│" + " " * 23 + "전체 WebSocket 기능 테스트" + " " * 28 + "│")
    print("└" + "─" * 78 + "┘")

    try:
        from utils.trading_date import is_market_hours

        if not is_market_hours():
            print("⚠️  현재 장 운영 시간이 아닙니다.")
            print("   전체 WebSocket 기능 테스트는 장 운영 시간(09:00-15:30)에 실행하세요.")
            print("   현재는 연결 테스트만 수행했습니다.")
            return True

        print("장 운영 시간입니다. 전체 WebSocket 테스트를 실행합니다...")
        print()

        # test_websocket_v2.py 실행
        from test_websocket_v2 import WebSocketTesterV2

        tester = WebSocketTesterV2()
        await tester.run_comprehensive_test()

        return True

    except Exception as e:
        print(f"❌ 전체 WebSocket 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 함수"""
    print_banner()

    results = {
        "trading_date_utils": False,
        "rest_api": False,
        "websocket_connection": False,
        "websocket_full": False
    }

    # 1. 거래일 유틸리티 테스트
    results["trading_date_utils"] = await test_trading_date_utils()

    # 2. REST API 테스트
    results["rest_api"] = await test_rest_api()

    # 3. WebSocket 연결 테스트
    results["websocket_connection"] = await test_websocket()

    # 4. 전체 WebSocket 기능 테스트 (장 운영 시간에만)
    results["websocket_full"] = await run_full_websocket_test()

    # 최종 결과 요약
    print("\n" + "=" * 80)
    print("📊 최종 테스트 결과 요약")
    print("=" * 80)

    for test_name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {test_name.replace('_', ' ').title()}")

    success_count = sum(results.values())
    total_count = len(results)

    print("─" * 80)
    print(f"총 {success_count}/{total_count} 테스트 성공")
    print("=" * 80)

    if success_count == total_count:
        print("✅ 모든 테스트가 성공했습니다!")
    elif success_count > 0:
        print("⚠️  일부 테스트가 실패했습니다. 로그를 확인하세요.")
    else:
        print("❌ 모든 테스트가 실패했습니다. 설정을 확인하세요.")

    print()


if __name__ == "__main__":
    try:
        print("\n⚠️  중요: 이 테스트는 주말/장마감 후에도 실행 가능합니다.")
        print("   - REST API: 가장 최근 영업일 데이터로 테스트")
        print("   - WebSocket: 연결 테스트만 수행 (장 운영 시간에는 실시간 데이터 수신)")
        print()

        response = input("테스트를 시작하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            asyncio.run(main())
        else:
            print("테스트 취소")

    except KeyboardInterrupt:
        print("\n\n테스트 중단됨")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
