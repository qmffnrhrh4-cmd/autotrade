"""
NXT 시간대 실시간 분봉 차트 테스트

WebSocket 체결 데이터로 실시간 분봉을 생성하여 NXT 시간대에도 분봉 데이터를 확보합니다.

✅ 작동 방식:
1. WebSocket으로 실시간 체결 데이터 구독 (ka10045 / 0B 타입)
2. 체결 데이터를 1분 단위로 집계하여 OHLCV 생성
3. NXT 시간대(08:00-09:00, 15:30-20:00) 포함

✅ 지원 시간대:
- 프리마켓: 08:00-09:00
- 정규장: 09:00-15:30
- 애프터마켓: 15:30-20:00
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import TradingBotV2
from core.realtime_minute_chart import RealtimeMinuteChart, RealtimeMinuteChartManager
from utils.trading_date import is_nxt_hours


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


def format_time():
    """현재 시간 포맷"""
    return datetime.now().strftime("%H:%M:%S")


def print_candle(candle: Dict[str, Any]):
    """분봉 데이터 출력"""
    print(f"  📊 {candle['date']} {candle['time']}")
    print(f"     시가: {candle['open']:,}원")
    print(f"     고가: {candle['high']:,}원")
    print(f"     저가: {candle['low']:,}원")
    print(f"     종가: {candle['close']:,}원")
    print(f"     거래량: {candle['volume']:,}주")


async def test_realtime_minute_chart():
    """NXT 실시간 분봉 차트 테스트"""

    print_section("NXT 실시간 분봉 차트 테스트 (WebSocket)")

    # 현재 시간 확인
    now = datetime.now()
    is_nxt = is_nxt_hours()

    print(f"📅 테스트 시작 시간")
    print(f"  시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  NXT 시간대: {'✅ YES' if is_nxt else '❌ NO'}")
    if is_nxt:
        if 8 <= now.hour < 9:
            print(f"  시간대: 🌅 프리마켓 (08:00-09:00)")
        else:
            print(f"  시간대: 🌆 애프터마켓 (15:30-20:00)")
    else:
        if 9 <= now.hour < 15 or (now.hour == 15 and now.minute < 30):
            print(f"  시간대: 📈 정규장 (09:00-15:30)")
        else:
            print(f"  시간대: ⏰ 장외 시간 (20:00-08:00)")
    print()

    # API 토큰 가져오기
    print("🔧 API 토큰 가져오는 중...")
    from core.rest_client import KiwoomRESTClient

    client = KiwoomRESTClient()  # 싱글톤 패턴

    if not client or not hasattr(client, 'token') or not client.token:
        print("❌ API 토큰 없음 - 로그인 필요")
        return

    print("✅ API 토큰 확보")
    print()

    # WebSocket Manager 직접 생성
    print("🔧 WebSocket Manager 생성 중...")
    from core.websocket_manager import WebSocketManager

    ws_manager = WebSocketManager(
        access_token=client.token,
        base_url=client.base_url
    )

    # WebSocket 연결
    print("🔌 WebSocket 연결 중...")
    connect_success = await ws_manager.connect()

    if not connect_success:
        print("❌ WebSocket 연결 실패")
        return

    print("✅ WebSocket 연결 성공")
    print()

    # 테스트 종목
    test_stocks = [
        ("삼성전자", "005930"),
        ("SK하이닉스", "000660"),
        ("NAVER", "035420"),
    ]

    print(f"📋 테스트 종목: {len(test_stocks)}개")
    for name, code in test_stocks:
        print(f"  • {name} ({code})")
    print()

    # 실시간 분봉 매니저 생성
    print("🎯 실시간 분봉 매니저 생성 중...")
    chart_manager = RealtimeMinuteChartManager(ws_manager)
    print("✅ 매니저 생성 완료")
    print()

    # 종목별 구독
    print_section("📡 실시간 분봉 구독 시작")

    subscribed_stocks = []

    for name, stock_code in test_stocks:
        print(f"━━━ {name} ({stock_code}) 구독 시도 ━━━")

        try:
            success = await chart_manager.add_stock(stock_code)

            if success:
                print(f"✅ 구독 성공: {stock_code}")
                subscribed_stocks.append((name, stock_code))
            else:
                print(f"❌ 구독 실패: {stock_code}")

        except Exception as e:
            print(f"❌ 예외 발생: {e}")

        print()

    if not subscribed_stocks:
        print("❌ 구독된 종목이 없습니다.")
        return

    print(f"✅ 총 {len(subscribed_stocks)}개 종목 구독 완료")
    print()

    # 실시간 데이터 수집 (30초 대기)
    print_section("⏱️  실시간 데이터 수집 중...")

    print("📊 30초 동안 체결 데이터를 수집합니다...")
    print("   (거래가 활발한 시간대에는 더 많은 데이터가 수집됩니다)")
    print()

    wait_seconds = 30

    for i in range(wait_seconds):
        remaining = wait_seconds - i
        print(f"\r⏰ 대기 중... {remaining}초 남음", end="", flush=True)
        await asyncio.sleep(1)

    print("\n")
    print("✅ 데이터 수집 완료!")
    print()

    # 수집된 데이터 확인
    print_section("📊 수집된 분봉 데이터 확인")

    status = chart_manager.get_status()

    print(f"WebSocket 연결: {'✅ 연결됨' if status['connected'] else '❌ 미연결'}")
    print()

    for name, stock_code in subscribed_stocks:
        print_separator("━", 80)
        print(f"[{name}] {stock_code}")
        print_separator("━", 80)
        print()

        stock_status = status['stocks'].get(stock_code, {})

        print(f"📍 구독 상태: {'✅ 활성' if stock_status.get('subscribed') else '❌ 비활성'}")
        print(f"📊 수집된 분봉 개수: {stock_status.get('candle_count', 0)}개")
        print(f"⏰ 현재 분봉 시간: {stock_status.get('current_minute', 'N/A')}")
        print()

        # 최근 5개 분봉 조회
        minute_data = chart_manager.get_minute_data(stock_code, minutes=5)

        if minute_data and len(minute_data) > 0:
            print(f"✅ 최근 {len(minute_data)}개 분봉:")
            print()

            for idx, candle in enumerate(minute_data, 1):
                print(f"[{idx}] {candle['date']} {candle['time']}")
                print(f"    OHLC: {candle['open']:,} / {candle['high']:,} / {candle['low']:,} / {candle['close']:,}")
                print(f"    거래량: {candle['volume']:,}주")
                print()

            # 현재 진행 중인 분봉
            current = chart_manager.get_current_candle(stock_code)
            if current:
                print("🔴 현재 진행 중인 분봉:")
                print_candle(current)
                print()

        else:
            print("⚠️ 수집된 분봉 데이터가 없습니다.")
            print()
            print("가능한 원인:")
            print("  • 실제 체결이 발생하지 않음 (거래 부진)")
            print("  • 장외 시간 (20:00-08:00)")
            print("  • WebSocket 데이터 수신 문제")
            print()

    # 구독 해제
    print_section("🛑 구독 해제")

    for name, stock_code in subscribed_stocks:
        print(f"🛑 {name} ({stock_code}) 구독 해제 중...")
        try:
            await chart_manager.remove_stock(stock_code)
            print(f"✅ 구독 해제 완료: {stock_code}")
        except Exception as e:
            print(f"❌ 구독 해제 실패: {e}")

    print()

    # WebSocket 연결 종료
    print("🔌 WebSocket 연결 종료 중...")
    try:
        await ws_manager.disconnect()
        print("✅ WebSocket 연결 종료 완료")
    except Exception as e:
        print(f"⚠️ WebSocket 종료 중 오류: {e}")

    print()

    # 요약
    print_section("📊 테스트 요약")

    print("✅ 완료된 작업:")
    print(f"  1. {len(subscribed_stocks)}개 종목 실시간 구독")
    print(f"  2. 30초 동안 체결 데이터 수집")
    print(f"  3. 분봉 데이터 생성 및 확인")
    print(f"  4. 구독 해제")
    print()

    total_candles = sum(
        status['stocks'].get(code, {}).get('candle_count', 0)
        for _, code in subscribed_stocks
    )

    print(f"📈 총 수집된 분봉: {total_candles}개")
    print()

    if total_candles > 0:
        print("✅ 성공!")
        print()
        print("💡 NXT 시간대 분봉 조회 방법:")
        print()
        print("```python")
        print("from core.realtime_minute_chart import RealtimeMinuteChartManager")
        print()
        print("# 매니저 생성")
        print("chart_manager = RealtimeMinuteChartManager(bot.websocket_manager)")
        print()
        print("# 종목 구독")
        print("await chart_manager.add_stock('005930')")
        print()
        print("# 실시간 데이터 수집 (백그라운드)")
        print("await asyncio.sleep(60)  # 60초 대기")
        print()
        print("# 분봉 데이터 조회")
        print("minute_data = chart_manager.get_minute_data('005930', minutes=30)")
        print("for candle in minute_data:")
        print("    print(f\"{candle['time']}: {candle['close']:,}원\")")
        print("```")
    else:
        print("⚠️ 데이터 수집 실패")
        print()
        print("해결 방법:")
        print("  1. 거래 시간대에 재시도 (08:00-20:00)")
        print("  2. 대기 시간 늘리기 (30초 → 60초)")
        print("  3. 거래량이 많은 종목 선택")
        print("  4. WebSocket 연결 상태 확인")

    print()


async def test_comparison():
    """REST API vs WebSocket 분봉 비교 테스트"""

    print_section("📊 REST API vs WebSocket 분봉 비교")

    # API 토큰 가져오기
    from core.rest_client import KiwoomRESTClient

    client = KiwoomRESTClient()  # 싱글톤 패턴

    if not client or not hasattr(client, 'token') or not client.token:
        print("❌ API 토큰 없음")
        return

    test_stock = "005930"  # 삼성전자

    print(f"📋 테스트 종목: {test_stock}")
    print()

    # 1. REST API로 분봉 조회 (과거 데이터)
    print("━━━ REST API 분봉 조회 ━━━")
    print()

    from utils.trading_date import get_last_trading_date
    from api.market.chart_data import get_minute_chart

    last_date = get_last_trading_date()

    rest_data = get_minute_chart(
        stock_code=test_stock,
        interval=1,
        count=10,
        base_date=last_date
    )

    if rest_data and len(rest_data) > 0:
        print(f"✅ REST API 성공: {len(rest_data)}개 조회")
        print(f"  기준일: {last_date}")
        print(f"  최근 데이터: {rest_data[0]['date']} {rest_data[0]['time']} - {rest_data[0]['close']:,}원")
    else:
        print(f"❌ REST API 실패: 데이터 없음")

    print()

    # 2. WebSocket으로 실시간 분봉 생성
    print("━━━ WebSocket 실시간 분봉 생성 ━━━")
    print()

    # WebSocket Manager 생성
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

    chart_manager = RealtimeMinuteChartManager(ws_manager)

    print(f"🔔 {test_stock} 구독 중...")
    success = await chart_manager.add_stock(test_stock)

    if not success:
        print(f"❌ 구독 실패")
        await ws_manager.disconnect()
        return

    print(f"✅ 구독 성공")
    print()

    print("⏰ 30초 동안 데이터 수집 중...")
    await asyncio.sleep(30)
    print("✅ 수집 완료")
    print()

    ws_data = chart_manager.get_minute_data(test_stock, minutes=10)

    if ws_data and len(ws_data) > 0:
        print(f"✅ WebSocket 성공: {len(ws_data)}개 생성")
        print(f"  최근 데이터: {ws_data[-1]['date']} {ws_data[-1]['time']} - {ws_data[-1]['close']:,}원")
    else:
        print(f"⚠️ WebSocket: 데이터 없음 (거래 없음 또는 장외 시간)")

    print()

    # 구독 해제 및 연결 종료
    await chart_manager.remove_stock(test_stock)
    await ws_manager.disconnect()

    # 비교 요약
    print_separator("━", 80)
    print("📊 비교 요약")
    print_separator("━", 80)
    print()

    print("REST API (ka10080):")
    print(f"  ✅ 과거 데이터 조회 가능")
    print(f"  ❌ NXT 시간대 _NX 미지원")
    print(f"  ❌ 장외 시간 실시간 데이터 없음")
    print(f"  데이터 개수: {len(rest_data) if rest_data else 0}개")
    print()

    print("WebSocket (ka10045 / 0B 타입):")
    print(f"  ✅ 실시간 체결 데이터로 분봉 생성")
    print(f"  ✅ NXT 시간대 지원 (08:00-20:00)")
    print(f"  ✅ 정규장 + 프리마켓 + 애프터마켓 모두 지원")
    print(f"  데이터 개수: {len(ws_data) if ws_data else 0}개")
    print()

    print("💡 권장:")
    print("  • 과거 데이터: REST API (base_date 사용)")
    print("  • NXT 실시간 데이터: WebSocket 분봉 생성")
    print("  • 정규장 실시간: 둘 다 가능 (WebSocket 권장)")
    print()


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="NXT 실시간 분봉 테스트")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="REST API vs WebSocket 비교 테스트"
    )

    args = parser.parse_args()

    if args.compare:
        asyncio.run(test_comparison())
    else:
        asyncio.run(test_realtime_minute_chart())


if __name__ == "__main__":
    main()
