#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kiwoom OpenAPI 직접 테스트
kiwoom32 환경에서 실행: conda activate kiwoom32 && python test_kiwoom_direct.py

로그인이 완료되면 자동으로 데이터를 수집하고 5초 후 종료됩니다.
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer


def save_json(data, filename):
    """JSON 파일로 저장"""
    output_dir = Path("tests")
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"   💾 저장: {filepath}")
    return filepath


def collect_data(api):
    """데이터 수집"""
    print("\n" + "=" * 80)
    print("  데이터 수집 시작")
    print("=" * 80)

    results = {}

    # 1. 로그인 정보
    print("\n1️⃣  로그인 정보")
    try:
        login_info = {
            '계좌목록': api.get_login_info("ACCLIST"),
            '사용자ID': api.get_login_info("USER_ID"),
            '사용자명': api.get_login_info("USER_NAME"),
            '서버구분': api.get_login_info("GetServerGubun")
        }
        for key, value in login_info.items():
            print(f"   ✅ {key}: {value}")
        results['login_info'] = login_info
        save_json(login_info, 'login_info')
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 2. 종목 정보
    print("\n2️⃣  종목 정보")
    test_stocks = ['005930', '000660', '035420']
    stocks = {}

    for stock_code in test_stocks:
        print(f"\n   📊 {stock_code}")
        try:
            stock_info = {
                '종목코드': stock_code,
                '종목명': api.get_master_code_name(stock_code),
                '현재가': api.get_master_last_price(stock_code),
                '상장주식수': api.get_master_listed_stock_cnt(stock_code),
            }
            print(f"      종목명: {stock_info['종목명']}")
            print(f"      현재가: {stock_info['현재가']}")
            stocks[stock_code] = stock_info
        except Exception as e:
            print(f"      ❌ 오류: {e}")

    results['stocks'] = stocks
    save_json(stocks, 'stocks')

    # 3. API 메서드 탐색
    print("\n3️⃣  API 메서드 탐색")
    methods = {'comm_': [], 'send_': [], 'get_master_': [], 'get_': []}

    for attr in dir(api):
        if attr.startswith('_'):
            continue
        if callable(getattr(api, attr, None)):
            for prefix in ['comm_', 'send_', 'get_master_', 'get_']:
                if attr.startswith(prefix):
                    methods[prefix].append(attr)
                    break

    print(f"   📡 comm_* 메서드: {len(methods['comm_'])}개")
    print(f"   💰 send_* 메서드: {len(methods['send_'])}개")
    print(f"   📊 get_master_* 메서드: {len(methods['get_master_'])}개")
    print(f"   📋 기타 get_* 메서드: {len(methods['get_'])}개")

    # comm_ 메서드 출력
    print(f"\n   📡 TR 요청 메서드 (comm_*):")
    for method in methods['comm_'][:10]:
        print(f"      - {method}")
    if len(methods['comm_']) > 10:
        print(f"      ... 외 {len(methods['comm_']) - 10}개")

    results['methods'] = methods
    save_json(methods, 'api_methods')

    # 요약
    print("\n" + "=" * 80)
    print("  ✅ 데이터 수집 완료!")
    print("=" * 80)
    print(f"\n📁 결과: tests/ 폴더")
    save_json(results, 'collection_summary')

    return results


def main():
    """메인 함수"""
    print("=" * 80)
    print("  Kiwoom OpenAPI 직접 테스트")
    print("=" * 80)

    # Qt Application
    app = QApplication(sys.argv)

    # Kiwoom API
    from kiwoom import Kiwoom
    import kiwoom
    kiwoom.config.MUTE = True

    print("\n🔧 API 초기화...")
    api = Kiwoom()

    # 로그인 완료 후 실행할 함수
    def on_login_complete(err_code):
        if err_code == 0:
            print("\n✅ 로그인 성공!")

            # 1초 후 데이터 수집 시작
            def start_collection():
                try:
                    collect_data(api)
                except Exception as e:
                    print(f"\n❌ 오류: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    # 5초 후 종료
                    print("\n👋 5초 후 자동 종료...")
                    QTimer.singleShot(5000, app.quit)

            QTimer.singleShot(1000, start_collection)

        else:
            print(f"\n❌ 로그인 실패: {err_code}")
            app.quit()

    # 로그인 이벤트 연결
    api.connect('on_event_connect', slot=on_login_complete)

    print("🔐 로그인 중...")
    print("   (로그인 창이 나타나면 로그인하세요)\n")

    # 로그인 시작
    api.login()

    # Qt 이벤트 루프 시작
    sys.exit(app.exec_())


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Ctrl+C로 중단")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
