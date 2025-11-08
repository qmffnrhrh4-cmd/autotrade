#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAPI 종합 데이터 수집 테스트

breadum/kiwoom 라이브러리를 사용하여 제공하는 모든 데이터를 수집합니다.

실행 방법:
    conda activate kiwoom32
    python test_openapi_comprehensive.py

종료 방법:
    Ctrl+C (아나콘다 프롬프트)
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
    output_dir = Path("tests")
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

        # 계좌 확인
        try:
            acc_info = self.api.get_login_info("ACCLIST")
            if acc_info:
                print(f"   get_login_info 결과: {acc_info}")
                if ';' in acc_info:
                    accounts = [acc.strip() for acc in acc_info.split(';') if acc.strip()]
                else:
                    accounts = [acc_info]
        except Exception as e:
            print(f"   계좌 조회 실패: {e}")
            accounts = ['6452323210']

        if not accounts:
            accounts = ['6452323210']

        print(f"📋 계좌 목록: {accounts}")

        # 시작 시간
        self.start_time = time.time()

        # 테스트할 종목 코드
        test_stocks = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER

        try:
            # 1. 로그인 정보
            self.test_login_info()
            time.sleep(1)

            # 2. 각 종목별 기본 정보
            for stock_code in test_stocks:
                print(f"\n🔍 종목 테스트: {stock_code}")
                self.test_stock_master_info(stock_code)
                time.sleep(1)

            # 3. 사용 가능한 모든 메서드 탐색
            self.explore_api_methods()

            # 종료
            elapsed = time.time() - self.start_time

            print_section("완료")
            print(f"✅ 전체 테스트 완료")
            print(f"   소요 시간: {elapsed:.1f}초")
            print(f"   결과 저장: tests/ 폴더")

            print("\n💡 테스트 결과:")
            print("   1. tests/ 폴더에서 JSON 파일 확인")
            print("   2. breadum/kiwoom에서 실제 사용 가능한 메서드 확인")
            print("   3. 추가 데이터가 필요하면 explore_api_methods 결과 확인")

            print("\n⌨️  프롬프트 종료 방법:")
            print("   Ctrl+C (아나콘다 프롬프트)")

        except Exception as e:
            print(f"\n❌ 테스트 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Qt 앱 종료
            print("\n👋 프로그램 종료 중...")
            QTimer.singleShot(2000, self.app.quit)

    def test_login_info(self):
        """로그인 정보 조회"""
        print_section("1. 로그인 정보")

        results = {}

        try:
            # 계좌 목록
            acclist = self.api.get_login_info("ACCLIST")
            print(f"✅ 계좌 목록: {acclist}")
            results['acclist'] = acclist

            # 사용자 ID
            user_id = self.api.get_login_info("USER_ID")
            print(f"✅ 사용자 ID: {user_id}")
            results['user_id'] = user_id

            # 사용자 이름
            user_name = self.api.get_login_info("USER_NAME")
            print(f"✅ 사용자 이름: {user_name}")
            results['user_name'] = user_name

            # 접속 서버
            get_server = self.api.get_login_info("GetServerGubun")
            print(f"✅ 서버 구분: {get_server}")
            results['server'] = get_server

            save_json(results, 'login_info')

        except Exception as e:
            print(f"❌ 로그인 정보 조회 실패: {e}")
            import traceback
            traceback.print_exc()

    def test_stock_master_info(self, stock_code='005930'):
        """종목 마스터 정보 조회 (get_master_* 메서드들)"""
        print_section(f"2. 종목 마스터 정보 ({stock_code})")

        results = {}

        try:
            # 종목명
            name = self.api.get_master_code_name(stock_code)
            print(f"✅ 종목명: {name}")
            results['code_name'] = name

            # 현재가 (최종가)
            last_price = self.api.get_master_last_price(stock_code)
            print(f"✅ 현재가: {last_price}")
            results['last_price'] = last_price

            # 상장주식수
            stock_cnt = self.api.get_master_listed_stock_cnt(stock_code)
            print(f"✅ 상장주식수: {stock_cnt:,}주")
            results['listed_stock_cnt'] = stock_cnt

            # 시가총액
            stock_num = self.api.get_master_listed_stock_num(stock_code)
            print(f"✅ 상장주식수(num): {stock_num}")
            results['listed_stock_num'] = stock_num

            # 구분 정보
            construction_gb = self.api.get_master_construction_gb(stock_code)
            print(f"✅ 구분: {construction_gb}")
            results['construction_gb'] = construction_gb

            # 감리구분
            supervision_gb = self.api.get_master_supervision_gb(stock_code)
            print(f"✅ 감리구분: {supervision_gb}")
            results['supervision_gb'] = supervision_gb

            # 상장일
            listed_date = self.api.get_master_listed_date(stock_code)
            print(f"✅ 상장일: {listed_date}")
            results['listed_date'] = listed_date

            # 전일가
            try:
                prev_price = self.api.get_prev_price(stock_code)
                print(f"✅ 전일가: {prev_price}")
                results['prev_price'] = prev_price
            except:
                print(f"   전일가 조회 불가")

            save_json(results, f'stock_master_{stock_code}')

        except Exception as e:
            print(f"❌ 종목 마스터 정보 조회 실패: {e}")
            import traceback
            traceback.print_exc()

    def explore_api_methods(self):
        """API 객체의 모든 메서드 탐색"""
        print_section("3. API 메서드 탐색")

        results = {
            'get_methods': [],
            'set_methods': [],
            'send_methods': [],
            'request_methods': [],
            'other_methods': []
        }

        print("🔍 사용 가능한 메서드 분석 중...")

        for attr in dir(self.api):
            if attr.startswith('_'):
                continue

            if callable(getattr(self.api, attr, None)):
                if 'get' in attr.lower():
                    results['get_methods'].append(attr)
                elif 'set' in attr.lower():
                    results['set_methods'].append(attr)
                elif 'send' in attr.lower():
                    results['send_methods'].append(attr)
                elif 'request' in attr.lower() or 'req' in attr.lower():
                    results['request_methods'].append(attr)
                else:
                    results['other_methods'].append(attr)

        print(f"\n✅ GET 메서드 ({len(results['get_methods'])}개):")
        for method in results['get_methods'][:10]:
            print(f"   - {method}")
        if len(results['get_methods']) > 10:
            print(f"   ... 외 {len(results['get_methods']) - 10}개")

        print(f"\n✅ REQUEST 메서드 ({len(results['request_methods'])}개):")
        for method in results['request_methods'][:10]:
            print(f"   - {method}")
        if len(results['request_methods']) > 10:
            print(f"   ... 외 {len(results['request_methods']) - 10}개")

        print(f"\n✅ SEND 메서드 ({len(results['send_methods'])}개):")
        for method in results['send_methods'][:10]:
            print(f"   - {method}")

        print(f"\n✅ SET 메서드 ({len(results['set_methods'])}개):")
        for method in results['set_methods'][:10]:
            print(f"   - {method}")

        print(f"\n✅ 기타 메서드 ({len(results['other_methods'])}개):")
        for method in results['other_methods'][:10]:
            print(f"   - {method}")
        if len(results['other_methods']) > 10:
            print(f"   ... 외 {len(results['other_methods']) - 10}개")

        save_json(results, 'api_methods')


def main():
    """메인 함수"""
    print("=" * 80)
    print("  OpenAPI 종합 데이터 수집 테스트")
    print("  breadum/kiwoom 라이브러리 사용")
    print("=" * 80)
    print("\n💡 종료 방법: Ctrl+C")

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

    # 로그인 완료 이벤트 연결
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
        print("\n\n👋 Ctrl+C: 사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
