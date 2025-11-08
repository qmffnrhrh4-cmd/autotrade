#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAPI 종합 데이터 수집 테스트

종료: 창을 그냥 닫으면 됩니다 (Qt 창 닫기)
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import QApplication


def save_json(data, filename):
    """JSON 파일로 저장 - tests/ 폴더"""
    output_dir = Path("tests")
    output_dir.mkdir(exist_ok=True)

    filepath = output_dir / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"💾 저장: {filepath}")
    return filepath


def main():
    """메인 함수"""
    print("=" * 80)
    print("  OpenAPI 데이터 수집 테스트")
    print("=" * 80)
    print("\n💡 종료: Qt 창을 닫으면 됩니다")

    # Qt Application
    app = QApplication(sys.argv)

    # Kiwoom API
    from kiwoom import Kiwoom
    import kiwoom
    kiwoom.config.MUTE = True

    print("\n🔧 API 초기화 중...")
    api = Kiwoom()

    print("🔐 로그인 중...")
    api.login()

    print("\n✅ 로그인 완료!")
    print("\n" + "=" * 80)
    print("  테스트 시작")
    print("=" * 80)

    # 1. 로그인 정보
    print("\n1️⃣  로그인 정보")
    login_info = {}
    try:
        login_info['계좌목록'] = api.get_login_info("ACCLIST")
        login_info['사용자ID'] = api.get_login_info("USER_ID")
        login_info['사용자명'] = api.get_login_info("USER_NAME")
        login_info['서버구분'] = api.get_login_info("GetServerGubun")

        for key, value in login_info.items():
            print(f"   ✅ {key}: {value}")

        save_json(login_info, 'login_info')
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 2. 종목 마스터 정보
    test_stocks = ['005930', '000660', '035420']

    for stock_code in test_stocks:
        print(f"\n2️⃣  종목 정보: {stock_code}")
        stock_info = {}

        try:
            stock_info['종목명'] = api.get_master_code_name(stock_code)
            stock_info['현재가'] = api.get_master_last_price(stock_code)
            stock_info['상장주식수'] = api.get_master_listed_stock_cnt(stock_code)
            stock_info['상장일'] = api.get_master_listed_date(stock_code)
            stock_info['감리구분'] = api.get_master_supervision_gb(stock_code)

            print(f"   ✅ 종목명: {stock_info['종목명']}")
            print(f"   ✅ 현재가: {stock_info['현재가']}")
            print(f"   ✅ 상장주식수: {stock_info['상장주식수']:,}주")

            save_json(stock_info, f'stock_{stock_code}')
        except Exception as e:
            print(f"   ❌ 오류: {e}")

    # 3. API 메서드 탐색
    print(f"\n3️⃣  API 메서드 탐색")

    methods = {
        'GET': [],
        'SET': [],
        'SEND': [],
        'REQUEST': [],
        'OTHER': []
    }

    for attr in dir(api):
        if attr.startswith('_'):
            continue
        if callable(getattr(api, attr, None)):
            if 'get' in attr.lower():
                methods['GET'].append(attr)
            elif 'set' in attr.lower():
                methods['SET'].append(attr)
            elif 'send' in attr.lower():
                methods['SEND'].append(attr)
            elif 'request' in attr.lower() or 'req' in attr.lower():
                methods['REQUEST'].append(attr)
            else:
                methods['OTHER'].append(attr)

    print(f"   ✅ GET 메서드: {len(methods['GET'])}개")
    print(f"   ✅ REQUEST 메서드: {len(methods['REQUEST'])}개")
    print(f"   ✅ SEND 메서드: {len(methods['SEND'])}개")
    print(f"   ✅ SET 메서드: {len(methods['SET'])}개")
    print(f"   ✅ 기타 메서드: {len(methods['OTHER'])}개")

    # REQUEST 메서드 상위 10개 출력
    print(f"\n   📋 REQUEST 메서드 (상위 10개):")
    for method in methods['REQUEST'][:10]:
        print(f"      - {method}")

    save_json(methods, 'api_methods')

    # 완료
    print("\n" + "=" * 80)
    print("  ✅ 테스트 완료!")
    print("=" * 80)
    print(f"\n📁 결과: tests/ 폴더에 JSON 파일 저장됨")
    print(f"💡 종료: 이 창을 닫으면 됩니다")
    print("\n프로그램이 자동으로 종료됩니다 (5초 후)...")

    # 5초 후 자동 종료
    import time
    time.sleep(5)

    print("👋 종료합니다")
    app.quit()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Ctrl+C로 종료")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌오류: {e}")
        import traceback
        traceback.print_exc()
