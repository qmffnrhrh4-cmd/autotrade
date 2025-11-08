#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAPI 종합 데이터 수집 테스트
breadum/kiwoom 공식 패턴 사용

참고: https://github.com/breadum/kiwoom/tree/main/tutorials
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from kiwoom import Kiwoom


def save_json(data, filename):
    """JSON 파일로 저장 - tests/ 폴더"""
    output_dir = Path("tests")
    output_dir.mkdir(exist_ok=True)

    filepath = output_dir / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"   💾 저장: {filepath}")
    return filepath


class DataCollector:
    """데이터 수집 클래스 (Bot 역할)"""

    def __init__(self, api):
        self.api = api
        self.results = {}

    def collect_login_info(self):
        """로그인 정보 수집"""
        print("\n" + "=" * 80)
        print("  1. 로그인 정보")
        print("=" * 80)

        login_info = {
            '계좌목록': self.api.get_login_info("ACCLIST"),
            '사용자ID': self.api.get_login_info("USER_ID"),
            '사용자명': self.api.get_login_info("USER_NAME"),
            '서버구분': self.api.get_login_info("GetServerGubun")
        }

        for key, value in login_info.items():
            print(f"   ✅ {key}: {value}")

        self.results['login_info'] = login_info
        save_json(login_info, 'login_info')

    def collect_stock_master_info(self, stock_codes):
        """종목 마스터 정보 수집"""
        print("\n" + "=" * 80)
        print("  2. 종목 마스터 정보")
        print("=" * 80)

        all_stocks = {}

        for stock_code in stock_codes:
            print(f"\n   📊 {stock_code}")

            stock_info = {
                '종목코드': stock_code,
                '종목명': self.api.get_master_code_name(stock_code),
                '현재가': self.api.get_master_last_price(stock_code),
                '상장주식수': self.api.get_master_listed_stock_cnt(stock_code),
                '상장일': self.api.get_master_listed_date(stock_code),
                '감리구분': self.api.get_master_supervision_gb(stock_code),
                '구분': self.api.get_master_construction_gb(stock_code),
            }

            print(f"      종목명: {stock_info['종목명']}")
            print(f"      현재가: {stock_info['현재가']}")
            print(f"      상장주식수: {stock_info['상장주식수']:,}주")

            all_stocks[stock_code] = stock_info

        self.results['stocks'] = all_stocks
        save_json(all_stocks, 'stock_master_info')

    def explore_api_methods(self):
        """사용 가능한 API 메서드 탐색"""
        print("\n" + "=" * 80)
        print("  3. API 메서드 탐색")
        print("=" * 80)

        methods = {
            'comm_': [],  # TR 요청 관련
            'send_': [],  # 주문 관련
            'get_master_': [],  # 종목 정보
            'get_chejan_': [],  # 체결 정보
            'get_login_': [],  # 로그인 정보
            'get_': [],  # 기타 get
            'set_': [],  # 설정
            'other': []
        }

        for attr in dir(self.api):
            if attr.startswith('_'):
                continue

            if not callable(getattr(self.api, attr, None)):
                continue

            categorized = False
            for prefix in methods.keys():
                if prefix != 'other' and attr.startswith(prefix):
                    methods[prefix].append(attr)
                    categorized = True
                    break

            if not categorized:
                methods['other'].append(attr)

        # comm_ 메서드 (TR 요청 관련)
        print(f"\n   📡 TR 요청 메서드 (comm_*): {len(methods['comm_'])}개")
        for method in methods['comm_'][:15]:
            print(f"      - {method}")
        if len(methods['comm_']) > 15:
            print(f"      ... 외 {len(methods['comm_']) - 15}개")

        # send_ 메서드 (주문 관련)
        print(f"\n   💰 주문 메서드 (send_*): {len(methods['send_'])}개")
        for method in methods['send_']:
            print(f"      - {method}")

        # get_master_ 메서드
        print(f"\n   📊 종목정보 메서드 (get_master_*): {len(methods['get_master_'])}개")
        for method in methods['get_master_'][:15]:
            print(f"      - {method}")
        if len(methods['get_master_']) > 15:
            print(f"      ... 외 {len(methods['get_master_']) - 15}개")

        # get_chejan_ 메서드
        print(f"\n   ✅ 체결정보 메서드 (get_chejan_*): {len(methods['get_chejan_'])}개")
        for method in methods['get_chejan_']:
            print(f"      - {method}")

        # get_login_ 메서드
        print(f"\n   🔐 로그인정보 메서드 (get_login_*): {len(methods['get_login_'])}개")
        for method in methods['get_login_']:
            print(f"      - {method}")

        # 기타 get 메서드
        print(f"\n   📋 기타 GET 메서드: {len(methods['get_'])}개")
        for method in methods['get_'][:10]:
            print(f"      - {method}")
        if len(methods['get_']) > 10:
            print(f"      ... 외 {len(methods['get_']) - 10}개")

        # set 메서드
        print(f"\n   ⚙️  SET 메서드: {len(methods['set_'])}개")
        for method in methods['set_'][:10]:
            print(f"      - {method}")
        if len(methods['set_']) > 10:
            print(f"      ... 외 {len(methods['set_']) - 10}개")

        self.results['methods'] = methods
        save_json(methods, 'api_methods')

    def run(self):
        """전체 수집 실행"""
        print("\n🚀 데이터 수집 시작...")

        # 1. 로그인 정보
        self.collect_login_info()
        time.sleep(0.5)

        # 2. 종목 마스터 정보
        test_stocks = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER
        self.collect_stock_master_info(test_stocks)
        time.sleep(0.5)

        # 3. API 메서드 탐색
        self.explore_api_methods()

        # 완료
        print("\n" + "=" * 80)
        print("  ✅ 데이터 수집 완료!")
        print("=" * 80)
        print(f"\n📁 결과: tests/ 폴더")
        print("\n💡 주요 발견:")
        print(f"   - comm_* 메서드: TR 데이터 요청용 (opt10001, opw00001 등)")
        print(f"   - send_* 메서드: 주문 전송용")
        print(f"   - get_master_* 메서드: 종목 정보 조회용 (이미 사용중)")

        # 결과 요약 저장
        summary = {
            'timestamp': datetime.now().isoformat(),
            'login_info': self.results.get('login_info', {}),
            'stock_count': len(self.results.get('stocks', {})),
            'method_counts': {
                'comm': len(self.results.get('methods', {}).get('comm_', [])),
                'send': len(self.results.get('methods', {}).get('send_', [])),
                'get_master': len(self.results.get('methods', {}).get('get_master_', [])),
            }
        }
        save_json(summary, 'collection_summary')

        return self.results


def main():
    """메인 함수"""
    print("=" * 80)
    print("  OpenAPI 데이터 수집 테스트")
    print("  breadum/kiwoom 공식 패턴 사용")
    print("=" * 80)

    # Qt Application
    app = QApplication(sys.argv)

    # Kiwoom API
    import kiwoom
    kiwoom.config.MUTE = True

    print("\n🔧 API 초기화 중...")
    api = Kiwoom()

    print("🔐 로그인 중...")
    print("   (로그인 창에서 로그인하세요)")

    # 로그인
    api.login()

    print("\n✅ 로그인 완료!")

    # 데이터 수집
    collector = DataCollector(api)
    results = collector.run()

    print("\n👋 5초 후 종료됩니다...")
    time.sleep(5)

    return results


if __name__ == '__main__':
    try:
        results = main()
        print("\n✅ 프로그램 정상 종료")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n👋 Ctrl+C로 중단됨")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
