#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAPI 종합 데이터 수집 테스트

breadum/kiwoom 라이브러리를 사용하여 제공하는 모든 데이터를 수집합니다.

실행 방법:
    conda activate kiwoom32
    python test_openapi_comprehensive.py
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import QApplication


def print_section(title):
    """섹션 헤더 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def save_json(data, filename):
    """JSON 파일로 저장"""
    output_dir = Path("test_outputs")
    output_dir.mkdir(exist_ok=True)

    filepath = output_dir / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"   💾 저장: {filepath}")
    return filepath


def test_account_info(api):
    """계좌 정보 조회"""
    print_section("1. 계좌 정보")

    results = {}

    try:
        # 계좌 목록
        accounts = api.get_account_list()
        print(f"✅ 계좌 목록: {accounts}")
        results['accounts'] = accounts

        if accounts:
            account = accounts[0]

            # 예수금 조회
            deposit = api.get_deposit()
            print(f"✅ 예수금: {deposit:,}원")
            results['deposit'] = deposit

            # 출금 가능 금액
            withdrawal = api.get_withdrawable_cash()
            print(f"✅ 출금가능: {withdrawal:,}원")
            results['withdrawable_cash'] = withdrawal

            # 보유 종목 정보
            stocks = api.get_stocks()
            print(f"✅ 보유 종목 수: {len(stocks)}")
            results['stocks'] = stocks

            # 각 보유 종목 상세 정보
            for stock in stocks[:3]:  # 최대 3개만
                code = stock.get('종목코드', '')
                name = stock.get('종목명', '')
                print(f"   - {name}({code}): {stock.get('보유수량', 0)}주, "
                      f"수익률: {stock.get('수익률', 0)}%")

        save_json(results, 'account_info')

    except Exception as e:
        print(f"❌ 계좌 정보 조회 실패: {e}")
        import traceback
        traceback.print_exc()


def test_stock_basic_info(api, stock_code='005930'):
    """종목 기본 정보 조회"""
    print_section(f"2. 종목 기본 정보 ({stock_code})")

    results = {}

    try:
        # 종목 이름
        name = api.get_master_stock_name(stock_code)
        print(f"✅ 종목명: {name}")
        results['stock_name'] = name

        # 현재가
        price = api.get_current_price(stock_code)
        print(f"✅ 현재가: {price:,}원")
        results['current_price'] = price

        # 시장 구분
        market_type = api.get_master_market_type(stock_code)
        print(f"✅ 시장구분: {market_type}")
        results['market_type'] = market_type

        # 상장주식수
        listed_stock_count = api.get_master_listed_stock_count(stock_code)
        print(f"✅ 상장주식수: {listed_stock_count:,}주")
        results['listed_stock_count'] = listed_stock_count

        # 감리구분
        supervision = api.get_master_supervision_type(stock_code)
        print(f"✅ 감리구분: {supervision}")
        results['supervision'] = supervision

        # 액면가
        construction_price = api.get_master_construction_price(stock_code)
        print(f"✅ 액면가: {construction_price}원")
        results['construction_price'] = construction_price

        # 자본금
        capital = api.get_master_capital(stock_code)
        print(f"✅ 자본금: {capital:,}원")
        results['capital'] = capital

        # 신용구분
        credit_type = api.get_master_credit_type(stock_code)
        print(f"✅ 신용구분: {credit_type}")
        results['credit_type'] = credit_type

        # 거래정지 여부
        suspension = api.get_master_suspension_type(stock_code)
        print(f"✅ 거래정지: {suspension}")
        results['suspension'] = suspension

        save_json(results, f'stock_basic_{stock_code}')

    except Exception as e:
        print(f"❌ 종목 기본 정보 조회 실패: {e}")
        import traceback
        traceback.print_exc()


def test_stock_quote(api, stock_code='005930'):
    """종목 시세 정보 조회"""
    print_section(f"3. 종목 시세 정보 ({stock_code})")

    results = {}

    try:
        # opt10001: 주식기본정보요청
        stock_info = api.block_request(
            "opt10001",
            종목코드=stock_code,
            output="주식기본정보",
            next=0
        )

        if stock_info:
            print(f"✅ 종목기본정보:")
            for key, value in list(stock_info.items())[:10]:  # 처음 10개만 출력
                print(f"   - {key}: {value}")

            results['basic_info'] = stock_info

        # opt10002: 주식거래량요청
        volume_info = api.block_request(
            "opt10002",
            종목코드=stock_code,
            output="주식거래량",
            next=0
        )

        if volume_info:
            print(f"✅ 거래량정보: {len(volume_info)}개 항목")
            results['volume_info'] = volume_info[:5]  # 최근 5개만 저장

        # opt10003: 체결정보요청
        transaction_info = api.block_request(
            "opt10003",
            종목코드=stock_code,
            output="체결정보",
            next=0
        )

        if transaction_info:
            print(f"✅ 체결정보: {len(transaction_info)}개 항목")
            results['transaction_info'] = transaction_info[:5]

        save_json(results, f'stock_quote_{stock_code}')

    except Exception as e:
        print(f"❌ 종목 시세 정보 조회 실패: {e}")
        import traceback
        traceback.print_exc()


def test_order_book(api, stock_code='005930'):
    """호가 정보 조회"""
    print_section(f"4. 호가 정보 ({stock_code})")

    results = {}

    try:
        # opt10004: 호가요청
        order_book = api.block_request(
            "opt10004",
            종목코드=stock_code,
            output="호가",
            next=0
        )

        if order_book:
            print(f"✅ 호가정보:")
            # 매도 호가
            print("   [매도]")
            for i in range(1, 6):
                sell_price = order_book.get(f'매도호가{i}', 0)
                sell_qty = order_book.get(f'매도호가수량{i}', 0)
                print(f"   {i}: {sell_price:>8}원 x {sell_qty:>10}주")

            # 매수 호가
            print("   [매수]")
            for i in range(1, 6):
                buy_price = order_book.get(f'매수호가{i}', 0)
                buy_qty = order_book.get(f'매수호가수량{i}', 0)
                print(f"   {i}: {buy_price:>8}원 x {buy_qty:>10}주")

            results['order_book'] = order_book

        save_json(results, f'order_book_{stock_code}')

    except Exception as e:
        print(f"❌ 호가 정보 조회 실패: {e}")
        import traceback
        traceback.print_exc()


def test_chart_data(api, stock_code='005930'):
    """차트 데이터 조회"""
    print_section(f"5. 차트 데이터 ({stock_code})")

    results = {}

    try:
        # opt10081: 일봉 데이터
        daily_chart = api.block_request(
            "opt10081",
            종목코드=stock_code,
            기준일자=datetime.now().strftime('%Y%m%d'),
            수정주가구분="1",
            output="일봉차트",
            next=0
        )

        if daily_chart:
            print(f"✅ 일봉 데이터: {len(daily_chart)}개")
            results['daily_chart'] = daily_chart[:10]  # 최근 10일만

            # 최근 데이터 출력
            if daily_chart:
                recent = daily_chart[0]
                print(f"   최근: {recent.get('일자', '')} - "
                      f"시가: {recent.get('시가', 0):,}, "
                      f"고가: {recent.get('고가', 0):,}, "
                      f"저가: {recent.get('저가', 0):,}, "
                      f"종가: {recent.get('현재가', 0):,}")

        # opt10080: 분봉 데이터
        minute_chart = api.block_request(
            "opt10080",
            종목코드=stock_code,
            틱범위="1",
            수정주가구분="1",
            output="분봉차트",
            next=0
        )

        if minute_chart:
            print(f"✅ 분봉 데이터: {len(minute_chart)}개")
            results['minute_chart'] = minute_chart[:10]

        save_json(results, f'chart_data_{stock_code}')

    except Exception as e:
        print(f"❌ 차트 데이터 조회 실패: {e}")
        import traceback
        traceback.print_exc()


def test_investor_data(api, stock_code='005930'):
    """투자자 매매 동향"""
    print_section(f"6. 투자자 매매 동향 ({stock_code})")

    results = {}

    try:
        # opt10059: 투자자별 매매동향
        investor = api.block_request(
            "opt10059",
            일자=datetime.now().strftime('%Y%m%d'),
            종목코드=stock_code,
            금액수량구분="1",
            매매구분="0",
            단위구분="1",
            output="투자자별매매동향",
            next=0
        )

        if investor:
            print(f"✅ 투자자별 매매동향: {len(investor)}개 항목")

            for item in investor[:5]:
                date = item.get('일자', '')
                foreign = item.get('외국인순매수', 0)
                institution = item.get('기관계순매수', 0)
                print(f"   {date}: 외국인 {foreign:>12,}, 기관 {institution:>12,}")

            results['investor'] = investor[:10]

        save_json(results, f'investor_data_{stock_code}')

    except Exception as e:
        print(f"❌ 투자자 매매 동향 조회 실패: {e}")
        import traceback
        traceback.print_exc()


def test_market_index(api):
    """시장 지수 조회"""
    print_section("7. 시장 지수")

    results = {}

    try:
        # KOSPI
        kospi = api.block_request(
            "opt10001",
            종목코드="001",
            output="주식기본정보",
            next=0
        )

        if kospi:
            print(f"✅ KOSPI: {kospi.get('현재가', 0)}")
            results['kospi'] = kospi

        # KOSDAQ
        kosdaq = api.block_request(
            "opt10001",
            종목코드="101",
            output="주식기본정보",
            next=0
        )

        if kosdaq:
            print(f"✅ KOSDAQ: {kosdaq.get('현재가', 0)}")
            results['kosdaq'] = kosdaq

        save_json(results, 'market_index')

    except Exception as e:
        print(f"❌ 시장 지수 조회 실패: {e}")
        import traceback
        traceback.print_exc()


def test_condition_search(api):
    """조건 검색"""
    print_section("8. 조건 검색")

    results = {}

    try:
        # 조건 목록 조회
        conditions = api.get_condition_list()

        if conditions:
            print(f"✅ 조건 목록: {len(conditions)}개")

            for idx, name in conditions.items():
                print(f"   {idx}: {name}")

            results['conditions'] = conditions

            # 첫 번째 조건으로 검색 (있으면)
            if conditions:
                first_idx = list(conditions.keys())[0]
                first_name = conditions[first_idx]

                print(f"\n   조건검색 실행: {first_name}")
                stocks = api.get_condition_stock_list(first_idx, first_name)

                if stocks:
                    print(f"   ✅ 검색 결과: {len(stocks)}개 종목")
                    results['search_results'] = stocks[:10]

        save_json(results, 'condition_search')

    except Exception as e:
        print(f"❌ 조건 검색 실패: {e}")
        import traceback
        traceback.print_exc()


def test_realtime_data(api, stock_code='005930'):
    """실시간 데이터 수신 테스트"""
    print_section(f"9. 실시간 데이터 ({stock_code})")

    print("실시간 데이터는 이벤트 기반이므로 별도 구현 필요")
    print("TR 코드: 주식체결(실시간), 주식호가(실시간) 등")


def main():
    """메인 함수"""
    print("=" * 80)
    print("  OpenAPI 종합 데이터 수집 테스트")
    print("  breadum/kiwoom 라이브러리 사용")
    print("=" * 80)

    # Qt Application
    app = QApplication(sys.argv)

    # Kiwoom API
    from kiwoom import Kiwoom
    api = Kiwoom()

    # 로그인
    print("\n🔐 로그인 중...")
    api.login()

    accounts = api.get_account_list()
    if not accounts:
        print("❌ 로그인 실패 또는 계좌 없음")
        return

    print(f"✅ 로그인 성공: {accounts}")

    # 테스트할 종목 코드
    test_stocks = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER

    # 시작 시간
    start_time = time.time()

    # 1. 계좌 정보
    test_account_info(api)

    # 2-9. 각 종목별 데이터
    for stock_code in test_stocks:
        test_stock_basic_info(api, stock_code)
        time.sleep(0.5)  # API 호출 제한 고려

        test_stock_quote(api, stock_code)
        time.sleep(0.5)

        test_order_book(api, stock_code)
        time.sleep(0.5)

        test_chart_data(api, stock_code)
        time.sleep(0.5)

        test_investor_data(api, stock_code)
        time.sleep(0.5)

    # 시장 지수
    test_market_index(api)
    time.sleep(0.5)

    # 조건 검색
    test_condition_search(api)

    # 실시간 데이터 안내
    test_realtime_data(api, test_stocks[0])

    # 종료
    elapsed = time.time() - start_time

    print_section("완료")
    print(f"✅ 전체 테스트 완료")
    print(f"   소요 시간: {elapsed:.1f}초")
    print(f"   결과 저장: test_outputs/ 폴더")

    print("\n💡 다음 단계:")
    print("   1. test_outputs/ 폴더에서 JSON 파일 확인")
    print("   2. 필요한 데이터를 main.py에 통합")
    print("   3. 실시간 데이터 수신 기능 구현")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
