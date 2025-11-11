"""
WebSocket 실시간 데이터 수신 디버깅 테스트

NXT 시간대에 체결 데이터가 실제로 수신되는지 확인합니다.

테스트 순서:
1. WebSocket 연결
2. 체결 데이터 구독
3. 원시 메시지 수신 확인
4. 체결 데이터 파싱 확인
5. 분봉 생성 확인
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def print_separator(char="=", length=80):
    """구분선 출력"""
    print(char * length)


def print_section(title: str):
    """섹션 제목 출력"""
    print()
    print_separator()
    print(title)
    print_separator()
    print()


async def test_websocket_raw_data():
    """WebSocket 원시 데이터 수신 테스트"""

    print_section("🔍 WebSocket 원시 데이터 수신 디버깅")

    # 현재 시간
    now = datetime.now()
    print(f"📅 테스트 시작 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # API 토큰
    print("🔧 API 토큰 가져오는 중...")
    from core.rest_client import KiwoomRESTClient

    client = KiwoomRESTClient()

    if not client or not hasattr(client, 'token') or not client.token:
        print("❌ API 토큰 없음")
        return

    print("✅ API 토큰 확보")
    print()

    # WebSocket Manager
    print("🔧 WebSocket Manager 생성 중...")
    from core.websocket_manager import WebSocketManager

    ws_manager = WebSocketManager(
        access_token=client.token,
        base_url=client.base_url
    )

    # 연결
    print("🔌 WebSocket 연결 중...")
    connect_success = await ws_manager.connect()

    if not connect_success:
        print("❌ WebSocket 연결 실패")
        return

    print("✅ WebSocket 연결 성공")
    print()

    # 테스트 종목
    test_stock = "005930"  # 삼성전자

    print(f"📋 테스트 종목: {test_stock}")
    print()

    # 수신 데이터 카운터
    received_messages = []
    tick_count = 0
    real_messages = []

    # 원시 데이터 콜백
    def on_raw_message(data: Dict[str, Any]):
        """모든 WebSocket 메시지 수신"""
        nonlocal tick_count
        received_messages.append(data)

        msg_type = data.get('trnm', 'UNKNOWN')

        if msg_type == 'REAL':
            # 실시간 데이터
            real_messages.append(data)

            # 체결 데이터인지 확인
            data_list = data.get('data', [])
            for item in data_list:
                item_type = item.get('type', '')
                item_code = item.get('item', '')

                if item_type == '0B':  # 체결 데이터
                    tick_count += 1
                    values = item.get('values', {})

                    print(f"📊 체결 데이터 #{tick_count}:")
                    print(f"   종목: {item_code}")
                    print(f"   타입: {item_type}")
                    print(f"   현재가: {values.get('10', 'N/A')}")
                    print(f"   체결량: {values.get('15', 'N/A')}")
                    print(f"   시각: {values.get('16', 'N/A')}")
                    print(f"   전체 데이터: {values}")
                    print()

        # 주기적으로 상태 출력
        if len(received_messages) % 10 == 0:
            print(f"📈 수신 메시지: {len(received_messages)}개 (체결: {tick_count}개)")

    # 콜백 등록 (모든 메시지 수신)
    print("🎯 원시 데이터 콜백 등록 중...")

    # WebSocketManager에 직접 콜백 추가
    original_handle = ws_manager._handle_message if hasattr(ws_manager, '_handle_message') else None

    async def custom_handle_message(message):
        """커스텀 메시지 핸들러"""
        # 원본 처리
        if original_handle:
            await original_handle(message)

        # 우리 콜백 호출
        on_raw_message(message)

    # 메시지 핸들러 교체
    if hasattr(ws_manager, '_handle_message'):
        ws_manager._handle_message = custom_handle_message

    print("✅ 콜백 등록 완료")
    print()

    # 구독
    print(f"🔔 {test_stock} 체결 데이터 구독 중...")
    success = await ws_manager.subscribe(
        stock_codes=[test_stock],
        types=["0B"],
        grp_no=f"debug_{test_stock}"
    )

    if not success:
        print(f"❌ 구독 실패")
        await ws_manager.disconnect()
        return

    print(f"✅ 구독 성공")
    print()

    # 데이터 수집
    wait_seconds = 30

    print(f"⏰ {wait_seconds}초 동안 데이터 수신 대기 중...")
    print("   (체결 데이터가 수신되면 실시간으로 출력됩니다)")
    print()

    for i in range(wait_seconds):
        remaining = wait_seconds - i
        print(f"\r⏰ 대기 중... {remaining}초 남음 | 수신: {len(received_messages)}개 | 체결: {tick_count}개", end="", flush=True)
        await asyncio.sleep(1)

    print("\n")
    print("✅ 데이터 수집 완료!")
    print()

    # 결과 분석
    print_section("📊 수신 데이터 분석")

    print(f"총 수신 메시지: {len(received_messages)}개")
    print(f"실시간 메시지 (REAL): {len(real_messages)}개")
    print(f"체결 데이터 (0B): {tick_count}개")
    print()

    if len(received_messages) == 0:
        print("❌ WebSocket 메시지가 전혀 수신되지 않았습니다!")
        print()
        print("가능한 원인:")
        print("  1. WebSocket 연결이 끊어짐")
        print("  2. 메시지 핸들러가 호출되지 않음")
        print("  3. WebSocket 서버 문제")

    elif len(real_messages) == 0:
        print("⚠️ REAL 메시지가 수신되지 않았습니다")
        print()
        print("수신된 메시지 타입:")
        msg_types = {}
        for msg in received_messages:
            msg_type = msg.get('trnm', 'UNKNOWN')
            msg_types[msg_type] = msg_types.get(msg_type, 0) + 1

        for msg_type, count in msg_types.items():
            print(f"  • {msg_type}: {count}개")

        print()
        print("가능한 원인:")
        print("  1. 구독이 실패했거나 활성화되지 않음")
        print("  2. 해당 시간대에 거래가 없음")
        print("  3. 종목이 거래 정지 상태")

    elif tick_count == 0:
        print("⚠️ REAL 메시지는 수신되었지만 체결 데이터(0B)가 없습니다")
        print()
        print("수신된 REAL 메시지 샘플:")
        for i, msg in enumerate(real_messages[:3], 1):
            print(f"\n메시지 #{i}:")
            print(f"  타입: {msg.get('trnm')}")
            print(f"  데이터: {msg.get('data', [])[:2]}")  # 처음 2개만

        print()
        print("가능한 원인:")
        print("  1. 현재 시간대(19:02)에 실제 체결이 발생하지 않음")
        print("  2. NXT 애프터마켓 거래가 종료됨 (보통 18:00까지)")
        print("  3. 다른 타입의 실시간 데이터만 수신됨")

    else:
        print("✅ 체결 데이터 정상 수신!")
        print()
        print(f"📈 초당 평균 체결: {tick_count / wait_seconds:.2f}개")

        if tick_count > 0:
            print()
            print("🎉 분봉 생성이 가능합니다!")
            print("   → RealtimeMinuteChart를 사용하여 분봉을 생성할 수 있습니다")

    print()

    # 구독 해제
    print("🛑 구독 해제 중...")
    await ws_manager.unsubscribe(f"debug_{test_stock}")

    # 연결 종료
    print("🔌 WebSocket 연결 종료 중...")
    await ws_manager.disconnect()
    print("✅ 테스트 완료")
    print()


async def test_message_handler():
    """WebSocket 메시지 핸들러 테스트"""

    print_section("🔍 WebSocket 메시지 핸들러 동작 확인")

    # API 토큰
    from core.rest_client import KiwoomRESTClient
    client = KiwoomRESTClient()

    if not client or not hasattr(client, 'token') or not client.token:
        print("❌ API 토큰 없음")
        return

    # WebSocket Manager
    from core.websocket_manager import WebSocketManager

    ws_manager = WebSocketManager(
        access_token=client.token,
        base_url=client.base_url
    )

    # 연결
    print("🔌 WebSocket 연결 중...")
    connect_success = await ws_manager.connect()

    if not connect_success:
        print("❌ WebSocket 연결 실패")
        return

    print("✅ WebSocket 연결 성공")
    print()

    # WebSocketManager 내부 확인
    print("🔍 WebSocketManager 상태:")
    print(f"  • is_connected: {ws_manager.is_connected}")
    print(f"  • is_logged_in: {ws_manager.is_logged_in}")
    print(f"  • websocket: {ws_manager.websocket}")
    print(f"  • subscriptions: {ws_manager.subscriptions}")
    print(f"  • callbacks: {ws_manager.callbacks}")
    print()

    # 구독
    test_stock = "005930"

    print(f"🔔 {test_stock} 구독 중...")
    success = await ws_manager.subscribe(
        stock_codes=[test_stock],
        types=["0B"],
        grp_no=f"handler_test_{test_stock}"
    )

    print(f"  구독 결과: {'✅ 성공' if success else '❌ 실패'}")
    print(f"  등록된 구독: {ws_manager.subscriptions}")
    print()

    # 콜백 등록 테스트
    callback_called = []

    def test_callback(data):
        callback_called.append(data)
        print(f"✅ 콜백 호출됨! 데이터: {data}")

    ws_manager.register_callback('0B', test_callback)
    print(f"✅ 콜백 등록 완료")
    print(f"  등록된 콜백: {ws_manager.callbacks}")
    print()

    # 대기
    print("⏰ 10초 동안 대기 중...")
    await asyncio.sleep(10)
    print()

    print(f"📊 콜백 호출 횟수: {len(callback_called)}개")

    if len(callback_called) > 0:
        print("✅ 콜백이 정상 동작합니다!")
    else:
        print("❌ 콜백이 호출되지 않았습니다")
        print()
        print("가능한 원인:")
        print("  1. 체결 데이터가 수신되지 않음 (거래 없음)")
        print("  2. 메시지 핸들러가 콜백을 호출하지 않음")
        print("  3. WebSocket 데이터 수신 문제")

    print()

    # 정리
    await ws_manager.unsubscribe(f"handler_test_{test_stock}")
    await ws_manager.disconnect()
    print("✅ 테스트 완료")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="WebSocket 데이터 수신 디버깅")
    parser.add_argument(
        "--handler",
        action="store_true",
        help="메시지 핸들러 테스트"
    )

    args = parser.parse_args()

    if args.handler:
        asyncio.run(test_message_handler())
    else:
        asyncio.run(test_websocket_raw_data())


if __name__ == "__main__":
    main()
