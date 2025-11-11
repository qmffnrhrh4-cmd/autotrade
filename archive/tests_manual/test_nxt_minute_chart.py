"""
NXT 시간대 분봉 차트 조회 테스트

이 테스트는 NXT 시간대(08:00-09:00, 15:30-20:00)에
_NX 접미사를 사용해서 분봉 차트를 조회하는 기능을 테스트합니다.

테스트 시나리오:
1. NXT 시간대 실시간 분봉 조회 (_NX 접미사)
2. NXT 실패 시 기본 코드 fallback
3. 과거 데이터 조회 (base_date 파라미터)
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import TradingBotV2
from utils.trading_date import is_nxt_hours, get_last_trading_date


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


def test_nxt_minute_chart():
    """NXT 분봉 차트 조회 테스트"""

    print_section("NXT 분봉 차트 조회 테스트")

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
    print()

    # 봇 초기화
    bot = TradingBotV2()

    if not bot.client:
        print("❌ API 연결 실패")
        return

    if not hasattr(bot.client, 'token') or not bot.client.token:
        print("❌ API 토큰 없음 - 로그인 필요")
        return

    print("✅ API 연결 성공")
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

    # 테스트할 분봉 간격
    intervals = [1, 5, 15]

    # 각 종목별 테스트
    for name, stock_code in test_stocks:
        print_separator("━", 80)
        print(f"[{name}] {stock_code} - {format_time()}")
        print_separator("━", 80)
        print()

        for interval in intervals:
            print(f"━━━ {interval}분봉 테스트 ━━━")
            print()

            # 테스트 1: NXT 시간대 실시간 조회 (자동 _NX 처리)
            print(f"📊 Test 1: NXT 자동 전환 모드 (use_nxt_fallback=True)")
            try:
                chart_data = bot.market_api.get_minute_chart(
                    stock_code=stock_code,
                    interval=interval,
                    count=10,
                    adjusted=True,
                    use_nxt_fallback=True
                )

                if chart_data and len(chart_data) > 0:
                    print(f"  ✅ 성공: {len(chart_data)}개 조회")

                    # 첫 번째와 마지막 데이터 출력
                    first = chart_data[0]
                    last = chart_data[-1]

                    print(f"  📈 최신 데이터:")
                    print(f"     - 시간: {first.get('date')} {first.get('time')}")
                    print(f"     - OHLC: {first.get('open'):,} / {first.get('high'):,} / {first.get('low'):,} / {first.get('close'):,}")
                    print(f"     - 거래량: {first.get('volume'):,}")
                    print(f"     - 출처: {first.get('source')}")

                    if len(chart_data) > 1:
                        print(f"  📉 가장 오래된 데이터:")
                        print(f"     - 시간: {last.get('date')} {last.get('time')}")
                        print(f"     - 종가: {last.get('close'):,}")
                else:
                    print(f"  ❌ 실패: 데이터 없음")

            except Exception as e:
                print(f"  ❌ 예외 발생: {e}")

            print()

            # 테스트 2: NXT 전용 모드 (fallback 비활성화)
            if is_nxt:
                print(f"📊 Test 2: NXT 전용 모드 (use_nxt_fallback=False)")
                try:
                    chart_data_nxt_only = bot.market_api.get_minute_chart(
                        stock_code=stock_code,
                        interval=interval,
                        count=10,
                        adjusted=True,
                        use_nxt_fallback=False
                    )

                    if chart_data_nxt_only and len(chart_data_nxt_only) > 0:
                        print(f"  ✅ NXT 전용 성공: {len(chart_data_nxt_only)}개 조회")
                        print(f"  📍 출처: {chart_data_nxt_only[0].get('source')}")
                    else:
                        print(f"  ⚠️ NXT 전용 실패 - _NX 접미사로만 조회 시도했으나 데이터 없음")

                except Exception as e:
                    print(f"  ❌ 예외 발생: {e}")

                print()

        print()

    # 테스트 3: 과거 데이터 조회 (base_date 사용)
    print_section("📅 과거 데이터 조회 테스트 (base_date)")

    # 지난 거래일 가져오기
    last_trading_date = get_last_trading_date()

    # 5일 전 데이터 (YYYYMMDD 형식)
    five_days_ago = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")

    print(f"기준일 설정:")
    print(f"  • 최근 거래일: {last_trading_date}")
    print(f"  • 5일 전: {five_days_ago}")
    print()

    test_stock_name, test_stock_code = test_stocks[0]

    for base_dt in [last_trading_date, five_days_ago]:
        print(f"━━━ {test_stock_name} ({test_stock_code}) - 기준일: {base_dt} ━━━")

        try:
            chart_data_historical = bot.market_api.get_minute_chart(
                stock_code=test_stock_code,
                interval=5,
                count=20,
                adjusted=True,
                base_date=base_dt,
                use_nxt_fallback=True
            )

            if chart_data_historical and len(chart_data_historical) > 0:
                print(f"✅ 성공: {len(chart_data_historical)}개 조회")

                # 시간 범위 출력
                first = chart_data_historical[0]
                last = chart_data_historical[-1]
                print(f"📊 데이터 범위:")
                print(f"   최신: {first.get('date')} {first.get('time')} - 종가 {first.get('close'):,}원")
                print(f"   과거: {last.get('date')} {last.get('time')} - 종가 {last.get('close'):,}원")
            else:
                print(f"❌ 실패: 데이터 없음 (기준일: {base_dt})")

        except Exception as e:
            print(f"❌ 예외 발생: {e}")

        print()

    # 요약
    print_section("📊 테스트 요약")

    print("✅ 완료된 테스트:")
    print(f"  1. NXT 자동 전환 모드 테스트 ({len(test_stocks)}개 종목 × {len(intervals)}개 간격)")
    if is_nxt:
        print(f"  2. NXT 전용 모드 테스트 ({len(test_stocks)}개 종목 × {len(intervals)}개 간격)")
    print(f"  3. 과거 데이터 조회 테스트 (2개 기준일)")
    print()

    print("🎯 권장 테스트 시간:")
    print("  • NXT 프리마켓: 내일 오전 08:00 - 09:00")
    print("  • NXT 애프터마켓: 오늘/내일 오후 15:30 - 20:00")
    print("  • 정규장 비교: 내일 오전 09:30 - 15:00")
    print()

    print("📝 예상 결과:")
    print("  • NXT 시간대:")
    print("    - _NX 접미사 성공 시: source='nxt_chart'")
    print("    - _NX 접미사 실패 시: source='nxt_chart_fallback' (기본 코드)")
    print("  • 정규장 시간대:")
    print("    - source='regular_chart'")
    print("  • 장외 시간 (현재):")
    print("    - 실시간 데이터 없음")
    print("    - base_date 사용 시 과거 데이터 조회 가능")
    print()


if __name__ == "__main__":
    test_nxt_minute_chart()
