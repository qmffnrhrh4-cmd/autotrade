"""
장외시간 분봉 데이터 자동 조회 테스트
아이디어 1: REST API base_date 활용

기능:
- 장외시간 (20:00-08:00) 감지 시 자동으로 마지막 영업일 분봉 조회
- 이미 구현된 get_last_trading_date() + base_date 파라미터 활용
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime


def print_section(title: str):
    """섹션 구분선 출력"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def test_off_market_minute_chart():
    """장외시간 분봉 조회 테스트"""

    # Import trading_date module directly (avoid utils/__init__.py)
    import importlib.util
    spec = importlib.util.spec_from_file_location("trading_date", str(project_root / "utils" / "trading_date.py"))
    trading_date_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trading_date_module)

    is_any_trading_hours = trading_date_module.is_any_trading_hours
    is_market_hours = trading_date_module.is_market_hours
    is_nxt_hours = trading_date_module.is_nxt_hours
    get_last_trading_date = trading_date_module.get_last_trading_date
    get_trading_date_with_fallback = trading_date_module.get_trading_date_with_fallback

    print_section("📅 현재 시간 및 장 상태 확인")

    now = datetime.now()
    print(f"현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"요일: {['월', '화', '수', '목', '금', '토', '일'][now.weekday()]}")
    print(f"\n장 운영 상태:")
    print(f"  - 정규장 (09:00-15:30): {is_market_hours()}")
    print(f"  - NXT 시간 (08:00-09:00, 15:30-20:00): {is_nxt_hours()}")
    print(f"  - 거래 시간 전체 (08:00-20:00): {is_any_trading_hours()}")
    print(f"  - 장외시간 (20:00-08:00): {not is_any_trading_hours()}")

    print_section("🗓️ 조회 대상 날짜 결정")

    is_off_market = not is_any_trading_hours()

    if is_off_market:
        target_date = get_last_trading_date()
        print(f"⚠️ 장외시간입니다!")
        print(f"✅ 마지막 영업일 자동 조회: {target_date}")
        print(f"   → {target_date[:4]}년 {target_date[4:6]}월 {target_date[6:8]}일")

        # 폴백 날짜도 표시
        fallback_dates = get_trading_date_with_fallback(5)
        print(f"\n📋 최근 5일 영업일 (폴백용):")
        for i, date in enumerate(fallback_dates, 1):
            print(f"   {i}. {date[:4]}-{date[4:6]}-{date[6:8]}")
    else:
        target_date = now.strftime('%Y%m%d')
        print(f"✅ 거래 시간입니다!")
        print(f"✅ 오늘 날짜 사용: {target_date}")
        print(f"   → {target_date[:4]}년 {target_date[4:6]}월 {target_date[6:8]}일")

    print_section("🔌 API 연결")

    try:
        # TradingBotV2 사용 (main.py에서 import)
        from main import TradingBotV2
        from api.market import MarketAPI

        bot = TradingBotV2()

        if not bot.client:
            print("❌ API 클라이언트 초기화 실패")
            return

        # Check if client has a valid token
        if not hasattr(bot.client, 'token') or not bot.client.token:
            print("❌ API 인증 실패")
            return

        print("✅ API 연결 성공")

        client = bot.client
        market_api = MarketAPI(client)

    except Exception as e:
        print(f"❌ API 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    print_section("📊 분봉 데이터 조회 테스트")

    test_stocks = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("035420", "NAVER")
    ]

    intervals = [1, 5, 15, 30, 60]

    for stock_code, stock_name in test_stocks:
        print(f"\n{'─'*80}")
        print(f"📈 {stock_name} ({stock_code})")
        print(f"{'─'*80}\n")

        for interval in intervals:
            try:
                # 직접 API 호출로 응답 확인
                body = {
                    "stk_cd": stock_code,
                    "tic_scope": str(interval),
                    "upd_stkpc_tp": "1",  # 수정주가
                    "base_dt": target_date  # 기준일
                }

                print(f"🔍 {interval}분봉 요청: {body}")

                response = client.request(
                    api_id="ka10080",
                    body=body,
                    path="chart"
                )

                print(f"📥 API 응답:")
                print(f"   - return_code: {response.get('return_code') if response else 'No response'}")
                print(f"   - return_msg: {response.get('return_msg') if response else 'N/A'}")

                if response and response.get('return_code') == 0:
                    minute_data = response.get('stk_tic_pole_chart_qry', [])
                    print(f"   - 데이터 배열 길이: {len(minute_data)}")

                    if minute_data and len(minute_data) > 0:
                        print(f"✅ {interval}분봉: {len(minute_data)}개 조회 성공")

                        # 첫 번째 데이터 출력
                        first = minute_data[0]
                        print(f"   최신 데이터:")
                        print(f"   - 날짜: {first.get('dt', 'N/A')}")
                        print(f"   - 시간: {first.get('tm', 'N/A')}")
                        print(f"   - 시가: {first.get('open_pric', 'N/A')}")
                        print(f"   - 고가: {first.get('high_pric', 'N/A')}")
                        print(f"   - 저가: {first.get('low_pric', 'N/A')}")
                        print(f"   - 종가: {first.get('cur_prc', 'N/A')}")
                        print(f"   - 거래량: {first.get('trde_qty', 'N/A')}")
                    else:
                        print(f"⚠️ {interval}분봉: API 응답 성공했지만 데이터 배열이 비어있음")
                        print(f"   💡 원인: base_dt 파라미터가 장외시간에는 작동하지 않을 수 있음")
                else:
                    print(f"❌ {interval}분봉: API 오류")

            except Exception as e:
                print(f"❌ {interval}분봉 조회 실패: {e}")
                import traceback
                traceback.print_exc()

        print()  # 종목 사이 공백

    print_section("📊 테스트 결과 분석")

    if is_off_market:
        print("⏰ 테스트 환경: 장외시간 (20:00-08:00)")
        print(f"📅 조회 시도 날짜: {target_date}")
        print()
        print("❓ 예상 결과:")
        print("   - base_dt 파라미터로 과거 영업일 분봉 조회")
        print("   - 오늘(또는 마지막 영업일) 장 종료 후 데이터 반환")
        print()
        print("🔍 실제 결과 분석:")
        print("   위의 API 응답을 확인하세요.")
        print()
        print("💡 만약 모든 데이터가 비어있다면:")
        print("   → base_dt 파라미터는 지원되지만, 장외시간에는 작동하지 않을 수 있음")
        print("   → REST API의 한계: 장중에만 분봉 데이터 제공")
        print("   → 대안: 아이디어 2 (캐싱) 또는 아이디어 3 (Open API) 필요")
    else:
        print("⏰ 테스트 환경: 거래 시간 중")
        print(f"📅 조회 날짜: {target_date}")
        print()
        print("✅ 거래 시간에는 base_dt 없이도 당일 데이터 조회 가능")

    print()
    print("━" * 80)
    print()
    print("📌 결론:")
    print()
    print("아이디어 1 (REST API base_dt 파라미터) 검증 결과:")
    print("   ❓ 파라미터는 지원되나, 장외시간 작동 여부는 API 응답에 따라 달라짐")
    print("   ❓ 위의 실제 API 응답을 확인하여 판단 필요")
    print()
    print("대안:")
    print("   💡 아이디어 2: 거래 시간 중 분봉 캐싱 → 장외시간에 캐시 조회")
    print("   💡 아이디어 3: Kiwoom Open API 활용 (과거 데이터에 강력)")
    print()


if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║            🌙 장외시간 분봉 데이터 자동 조회 테스트 (아이디어 1)            ║
║                                                                          ║
║  기능: REST API base_date 파라미터를 활용한 과거 분봉 조회                ║
║  장점: 추가 개발 없음, 안정적, REST API만으로 해결                         ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
""")

    try:
        test_off_market_minute_chart()
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자가 테스트를 중단했습니다.")
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류 발생:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
