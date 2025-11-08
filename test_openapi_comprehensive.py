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
from PyQt5.QtCore import QTimer


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


class OpenAPITester:
    """OpenAPI 테스트 클래스"""

    def __init__(self, api, app):
        self.api = api
        self.app = app
        self.start_time = None
        self.is_connected = False

    def on_connect(self, err_code):
        """로그인 완료 콜백"""
        if err_code == 0:
            print("\n✅ 로그인 성공!")
            self.is_connected = True
            # 로그인 성공 후 잠시 대기 후 테스트 시작
            QTimer.singleShot(1000, self.run_tests)
        else:
            print(f"\n❌ 로그인 실패: {err_code}")
            self.app.quit()

    def run_tests(self):
        """모든 테스트 실행"""
        print("\n🚀 테스트 시작...")

        # 계좌 확인 - 여러 방법 시도
        accounts = []

        # 방법 1: get_login_info 사용
        try:
            acc_info = self.api.get_login_info("ACCLIST")
            if acc_info:
                print(f"   get_login_info 결과: {acc_info}")
                if ';' in acc_info:
                    accounts = [acc.strip() for acc in acc_info.split(';') if acc.strip()]
                else:
                    accounts = [acc_info]
        except Exception as e:
            print(f"   get_login_info 실패: {e}")

        # 방법 2: account 속성 확인
        if not accounts:
            try:
                if hasattr(self.api, 'account'):
                    acc = self.api.account
                    print(f"   account 속성: {acc}")
                    accounts = [acc] if acc else []
            except Exception as e:
                print(f"   account 속성 실패: {e}")

        # 방법 3: accounts 속성 확인
        if not accounts:
            try:
                if hasattr(self.api, 'accounts'):
                    accs = self.api.accounts
                    print(f"   accounts 속성: {accs}")
                    accounts = accs if isinstance(accs, list) else [accs]
            except Exception as e:
                print(f"   accounts 속성 실패: {e}")

        # 디버깅: API 객체의 모든 속성/메서드 출력
        if not accounts:
            print("\n   🔍 API 객체 분석:")
            for attr in dir(self.api):
                if 'account' in attr.lower() or 'login' in attr.lower():
                    print(f"      - {attr}")

        # 계좌 조회 실패 시 직접 지정
        if not accounts:
            print("⚠️  계좌 자동 조회 실패 - 직접 지정된 계좌 사용")
            accounts = ['64523232-10']

        print(f"📋 계좌 목록: {accounts}")

        # 시작 시간
        self.start_time = time.time()

        # 테스트할 종목 코드
        test_stocks = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER

        try:
            # 1. 계좌 정보
            self.test_account_info(accounts[0])
            time.sleep(1)

            # 2-6. 각 종목별 데이터
            for stock_code in test_stocks:
                print(f"\n🔍 종목 테스트: {stock_code}")

                self.test_stock_basic_info(stock_code)
                time.sleep(1)

                self.test_stock_quote(stock_code)
                time.sleep(1)

                self.test_order_book(stock_code)
                time.sleep(1)

                self.test_chart_data(stock_code)
                time.sleep(1)

            # 7. 시장 지수
            self.test_market_index()
            time.sleep(1)

            # 종료
            elapsed = time.time() - self.start_time

            print_section("완료")
            print(f"✅ 전체 테스트 완료")
            print(f"   소요 시간: {elapsed:.1f}초")
            print(f"   결과 저장: test_outputs/ 폴더")

            print("\n💡 다음 단계:")
            print("   1. test_outputs/ 폴더에서 JSON 파일 확인")
            print("   2. 필요한 데이터를 main.py에 통합")
            print("   3. 실시간 데이터 수신 기능 구현")

        except Exception as e:
            print(f"\n❌ 테스트 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Qt 앱 종료
            print("\n👋 프로그램 종료")
            QTimer.singleShot(1000, self.app.quit)

    def test_account_info(self, account_no):
        """계좌 정보 조회"""
        print_section("1. 계좌 정보")

        results = {}

        try:
            # 계좌 목록
            accounts = self.api.get_login_info("ACCLIST")
            print(f"✅ 계좌 목록: {accounts}")
            results['accounts'] = accounts if isinstance(accounts, list) else [accounts]

            # opw00001: 예수금상세현황요청
            print("   예수금 조회 중...")
            deposit_data = self.api.block_request(
                "opw00001",
                계좌번호=account_no,
                비밀번호="",
                비밀번호입력매체구분="00",
                조회구분="2",
                output="예수금상세현황요청",
                next=0
            )

            if deposit_data:
                print(f"✅ 예수금 정보:")
                for key, value in list(deposit_data.items())[:10]:
                    print(f"   - {key}: {value}")
                results['deposit_data'] = deposit_data

            # opw00018: 계좌평가잔고내역요청
            print("   보유 종목 조회 중...")
            stocks_data = self.api.block_request(
                "opw00018",
                계좌번호=account_no,
                비밀번호="",
                비밀번호입력매체구분="00",
                조회구분="2",
                output="계좌평가결과",
                next=0
            )

            if stocks_data:
                print(f"✅ 계좌 평가:")
                for key, value in list(stocks_data.items())[:10]:
                    print(f"   - {key}: {value}")
                results['account_eval'] = stocks_data

            save_json(results, 'account_info')

        except Exception as e:
            print(f"❌ 계좌 정보 조회 실패: {e}")
            import traceback
            traceback.print_exc()

    def test_stock_basic_info(self, stock_code='005930'):
        """종목 기본 정보 조회"""
        print_section(f"2. 종목 기본 정보 ({stock_code})")

        results = {}

        try:
            # 종목 이름
            name = self.api.get_master_code_name(stock_code)
            print(f"✅ 종목명: {name}")
            results['stock_name'] = name

            # 현재가
            price = self.api.get_master_last_price(stock_code)
            print(f"✅ 현재가: {price}원")
            results['current_price'] = price

            # 상장주식수
            listed_count = self.api.get_master_listed_stock_cnt(stock_code)
            print(f"✅ 상장주식수: {listed_count:,}주")
            results['listed_stock_count'] = listed_count

            # 전일가
            prev_price = self.api.get_master_prev_price(stock_code)
            print(f"✅ 전일가: {prev_price}원")
            results['prev_price'] = prev_price

            # 시가
            open_price = self.api.get_master_open_price(stock_code)
            print(f"✅ 시가: {open_price}원")
            results['open_price'] = open_price

            # 고가
            high_price = self.api.get_master_high_price(stock_code)
            print(f"✅ 고가: {high_price}원")
            results['high_price'] = high_price

            # 저가
            low_price = self.api.get_master_low_price(stock_code)
            print(f"✅ 저가: {low_price}원")
            results['low_price'] = low_price

            # 거래량
            volume = self.api.get_master_volume(stock_code)
            print(f"✅ 거래량: {volume:,}주")
            results['volume'] = volume

            save_json(results, f'stock_basic_{stock_code}')

        except Exception as e:
            print(f"❌ 종목 기본 정보 조회 실패: {e}")
            import traceback
            traceback.print_exc()

    def test_stock_quote(self, stock_code='005930'):
        """종목 시세 정보 조회"""
        print_section(f"3. 종목 시세 정보 ({stock_code})")

        results = {}

        try:
            # opt10001: 주식기본정보요청
            stock_info = self.api.block_request(
                "opt10001",
                종목코드=stock_code,
                output="주식기본정보",
                next=0
            )

            if stock_info:
                print(f"✅ 종목기본정보:")
                for key, value in list(stock_info.items())[:10]:
                    print(f"   - {key}: {value}")

                results['basic_info'] = stock_info

            save_json(results, f'stock_quote_{stock_code}')

        except Exception as e:
            print(f"❌ 종목 시세 정보 조회 실패: {e}")
            import traceback
            traceback.print_exc()

    def test_order_book(self, stock_code='005930'):
        """호가 정보 조회"""
        print_section(f"4. 호가 정보 ({stock_code})")

        results = {}

        try:
            # opt10004: 호가요청
            order_book = self.api.block_request(
                "opt10004",
                종목코드=stock_code,
                output="호가잔량",
                next=0
            )

            if order_book:
                print(f"✅ 호가정보:")
                # 매도 호가
                print("   [매도]")
                for i in range(1, 6):
                    sell_price_key = f'매도호가{i}' if f'매도호가{i}' in order_book else f'(최우선)매도호가'
                    sell_qty_key = f'매도호가수량{i}' if f'매도호가수량{i}' in order_book else f'(최우선)매도호가잔량'

                    sell_price = order_book.get(sell_price_key, 0)
                    sell_qty = order_book.get(sell_qty_key, 0)

                    if sell_price:
                        print(f"   {i}: {sell_price:>8}원 x {sell_qty:>10}주")
                        break

                # 매수 호가
                print("   [매수]")
                for i in range(1, 6):
                    buy_price_key = f'매수호가{i}' if f'매수호가{i}' in order_book else f'(최우선)매수호가'
                    buy_qty_key = f'매수호가수량{i}' if f'매수호가수량{i}' in order_book else f'(최우선)매수호가잔량'

                    buy_price = order_book.get(buy_price_key, 0)
                    buy_qty = order_book.get(buy_qty_key, 0)

                    if buy_price:
                        print(f"   {i}: {buy_price:>8}원 x {buy_qty:>10}주")
                        break

                # 전체 데이터 저장
                results['order_book'] = order_book

                # 키 목록 출력
                print(f"\n   사용 가능한 키: {list(order_book.keys())[:10]}")

            save_json(results, f'order_book_{stock_code}')

        except Exception as e:
            print(f"❌ 호가 정보 조회 실패: {e}")
            import traceback
            traceback.print_exc()

    def test_chart_data(self, stock_code='005930'):
        """차트 데이터 조회"""
        print_section(f"5. 차트 데이터 ({stock_code})")

        results = {}

        try:
            # opt10081: 일봉 데이터
            daily_chart = self.api.block_request(
                "opt10081",
                종목코드=stock_code,
                기준일자=datetime.now().strftime('%Y%m%d'),
                수정주가구분="1",
                output="주식일봉차트조회",
                next=0
            )

            if daily_chart:
                if isinstance(daily_chart, list):
                    print(f"✅ 일봉 데이터: {len(daily_chart)}개")
                    results['daily_chart'] = daily_chart[:10]

                    if daily_chart:
                        recent = daily_chart[0]
                        print(f"   최근 데이터 키: {list(recent.keys())[:10]}")
                else:
                    print(f"✅ 일봉 데이터: dict 형태")
                    results['daily_chart'] = daily_chart
                    print(f"   데이터 키: {list(daily_chart.keys())[:10]}")

            save_json(results, f'chart_data_{stock_code}')

        except Exception as e:
            print(f"❌ 차트 데이터 조회 실패: {e}")
            import traceback
            traceback.print_exc()

    def test_market_index(self):
        """시장 지수 조회"""
        print_section("7. 시장 지수")

        results = {}

        try:
            # opt10001: KOSPI 조회
            kospi = self.api.block_request(
                "opt10001",
                종목코드="001",
                output="주식기본정보",
                next=0
            )

            if kospi:
                print(f"✅ KOSPI 정보:")
                for key, value in list(kospi.items())[:5]:
                    print(f"   - {key}: {value}")
                results['kospi'] = kospi

            # opt10001: KOSDAQ 조회
            kosdaq = self.api.block_request(
                "opt10001",
                종목코드="101",
                output="주식기본정보",
                next=0
            )

            if kosdaq:
                print(f"✅ KOSDAQ 정보:")
                for key, value in list(kosdaq.items())[:5]:
                    print(f"   - {key}: {value}")
                results['kosdaq'] = kosdaq

            save_json(results, 'market_index')

        except Exception as e:
            print(f"❌ 시장 지수 조회 실패: {e}")
            import traceback
            traceback.print_exc()


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
    import kiwoom

    # 경고 메시지 숨기기
    kiwoom.config.MUTE = True

    print("\n🔧 API 초기화 중...")
    api = Kiwoom()

    # 테스터 생성
    tester = OpenAPITester(api, app)

    # 로그인 완료 이벤트 연결 (핵심!)
    api.connect('on_event_connect', slot=tester.on_connect)

    print("🔐 로그인 중...")
    print("   (로그인 창이 나타나면 로그인하세요)")

    # 로그인
    api.login()

    # Qt 이벤트 루프 실행
    sys.exit(app.exec_())


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
