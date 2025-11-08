#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
종목별 20가지 데이터 종합 수집 테스트
kiwoom32 환경에서 실행

확실히 작동하는 메서드만 사용합니다.
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QEventLoop


def save_json(data, filename):
    """JSON 파일로 저장"""
    output_dir = Path("tests")
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"      💾 저장: {filepath.name}")
    return filepath


class StockDataCollector:
    """종목 데이터 종합 수집 클래스"""

    def __init__(self, api):
        self.api = api
        self.tr_responses = {}

    def on_receive_tr_data(self, scr_no, rqname, trcode, recordname, prev_next):
        """TR 데이터 수신 이벤트"""
        print(f"         [수신] {rqname} / {trcode}")

        data = {}

        # 반복 횟수 확인
        cnt = self.api.get_repeat_cnt(trcode, rqname)

        if cnt == 0:
            # 단일 데이터 - comm_get_data 사용
            try:
                # 단일 데이터 추출 (인덱스 0)
                for i in range(100):  # 최대 100개 필드 시도
                    try:
                        value = self.api.comm_get_data(trcode, "", rqname, i, "")
                        if value:
                            data[f'field_{i}'] = value.strip()
                    except:
                        break
            except:
                pass
        else:
            # 복수 데이터
            items = []
            for idx in range(min(cnt, 20)):  # 최대 20개
                item = {}
                try:
                    for i in range(50):  # 최대 50개 필드
                        try:
                            value = self.api.comm_get_data(trcode, "", rqname, idx, f"field_{i}")
                            if value:
                                item[f'field_{i}'] = value.strip()
                        except:
                            break
                except:
                    pass
                if item:
                    items.append(item)
            data['items'] = items
            data['total_count'] = cnt

        self.tr_responses[rqname] = {
            'trcode': trcode,
            'data': data,
            'prev_next': prev_next
        }

    def request_tr(self, rqname, trcode, screen_no, inputs):
        """TR 요청"""
        # 입력값 설정
        for key, value in inputs.items():
            self.api.set_input_value(key, value)

        # 요청
        ret = self.api.comm_rq_data(rqname, trcode, 0, screen_no)

        if ret == 0:
            # 응답 대기 (최대 3초)
            for _ in range(30):
                QApplication.processEvents()
                if rqname in self.tr_responses:
                    return self.tr_responses[rqname]
                time.sleep(0.1)

        return None

    def collect_stock_data(self, stock_code):
        """종목별 데이터 수집"""
        print(f"\n{'='*80}")

        # 종목명 조회 (확실히 작동)
        stock_name = self.api.get_master_code_name(stock_code)
        print(f"  종목: {stock_code} ({stock_name})")
        print(f"{'='*80}")

        all_data = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'timestamp': datetime.now().isoformat(),
            'data': {}
        }

        # === 1. 마스터 정보 (확실히 작동하는 것만) ===
        print("\n📊 1. 마스터 정보")
        master_info = {}

        try:
            master_info['종목명'] = self.api.get_master_code_name(stock_code)
            print(f"   ✅ 종목명: {master_info['종목명']}")
        except Exception as e:
            print(f"   ⚠️  종목명 실패: {e}")

        try:
            master_info['현재가'] = self.api.get_master_last_price(stock_code)
            print(f"   ✅ 현재가: {master_info['현재가']}")
        except Exception as e:
            print(f"   ⚠️  현재가 실패: {e}")

        try:
            master_info['상장주식수'] = self.api.get_master_listed_stock_cnt(stock_code)
            print(f"   ✅ 상장주식수: {master_info['상장주식수']:,}")
        except Exception as e:
            print(f"   ⚠️  상장주식수 실패: {e}")

        all_data['data']['마스터정보'] = master_info

        # TR 요청 목록 (20가지)
        tr_requests = [
            # 2. 주식기본정보
            {
                'name': '주식기본정보',
                'rqname': 'stock_basic',
                'trcode': 'opt10001',
                'screen': '0101',
                'inputs': {'종목코드': stock_code}
            },
            # 3. 호가잔량
            {
                'name': '호가잔량',
                'rqname': 'orderbook',
                'trcode': 'opt10004',
                'screen': '0102',
                'inputs': {'종목코드': stock_code}
            },
            # 4. 체결정보
            {
                'name': '체결정보',
                'rqname': 'execution',
                'trcode': 'opt10003',
                'screen': '0103',
                'inputs': {'종목코드': stock_code}
            },
            # 5. 주식거래량
            {
                'name': '주식거래량',
                'rqname': 'volume',
                'trcode': 'opt10002',
                'screen': '0104',
                'inputs': {'종목코드': stock_code}
            },
            # 6. 일봉차트
            {
                'name': '일봉차트',
                'rqname': 'daily_chart',
                'trcode': 'opt10081',
                'screen': '0105',
                'inputs': {
                    '종목코드': stock_code,
                    '기준일자': datetime.now().strftime('%Y%m%d'),
                    '수정주가구분': '1'
                }
            },
            # 7. 분봉차트
            {
                'name': '분봉차트',
                'rqname': 'minute_chart',
                'trcode': 'opt10080',
                'screen': '0106',
                'inputs': {
                    '종목코드': stock_code,
                    '틱범위': '1',
                    '수정주가구분': '1'
                }
            },
            # 8. 투자자별매매동향
            {
                'name': '투자자매매',
                'rqname': 'investor',
                'trcode': 'opt10059',
                'screen': '0107',
                'inputs': {
                    '일자': datetime.now().strftime('%Y%m%d'),
                    '종목코드': stock_code,
                    '금액수량구분': '1',
                    '매매구분': '0',
                    '단위구분': '1'
                }
            },
            # 9. 주식시세
            {
                'name': '주식시세',
                'rqname': 'stock_price',
                'trcode': 'opt10007',
                'screen': '0108',
                'inputs': {'종목코드': stock_code}
            },
            # 10. 시세표성정보
            {
                'name': '시세표성',
                'rqname': 'market_cap',
                'trcode': 'OPT10008',
                'screen': '0109',
                'inputs': {'종목코드': stock_code}
            },
            # 11. 종목정보
            {
                'name': '종목정보',
                'rqname': 'stock_info',
                'trcode': 'opt10086',
                'screen': '0110',
                'inputs': {'종목코드': stock_code}
            },
        ]

        # TR 요청 실행
        for idx, req in enumerate(tr_requests, start=2):
            print(f"\n📊 {idx}. {req['name']} ({req['trcode']})")

            try:
                result = self.request_tr(
                    rqname=req['rqname'],
                    trcode=req['trcode'],
                    screen_no=req['screen'],
                    inputs=req['inputs']
                )

                if result:
                    print(f"   ✅ 조회 성공")
                    all_data['data'][req['name']] = result
                else:
                    print(f"   ⚠️  응답 없음")

                # API 호출 제한 준수 (0.2초 대기)
                time.sleep(0.2)

            except Exception as e:
                print(f"   ❌ 실패: {e}")

        # 결과 저장
        data_count = len([k for k in all_data['data'].keys() if all_data['data'][k]])

        print(f"\n{'='*80}")
        print(f"  ✅ 수집 완료: {data_count}가지 데이터")
        print(f"{'='*80}")

        save_json(all_data, f'stock_comprehensive_{stock_code}')

        return all_data


def main():
    """메인 함수"""
    print("=" * 80)
    print("  종목별 종합 데이터 수집 (20가지 목표)")
    print("=" * 80)

    app = QApplication(sys.argv)

    from kiwoom import Kiwoom
    import kiwoom
    kiwoom.config.MUTE = True

    print("\n🔧 API 초기화...")
    api = Kiwoom()

    def on_login_complete(err_code):
        if err_code == 0:
            print("\n✅ 로그인 성공!")

            def start_collection():
                try:
                    collector = StockDataCollector(api)

                    # TR 이벤트 연결
                    api.connect('on_receive_tr_data', slot=collector.on_receive_tr_data)

                    # 3개 종목
                    test_stocks = ['005930', '000660', '035420']
                    results = []

                    for stock_code in test_stocks:
                        result = collector.collect_stock_data(stock_code)
                        results.append(result)
                        time.sleep(1)  # 종목 간 1초 대기

                    # 요약
                    print("\n" + "=" * 80)
                    print("  📊 전체 결과")
                    print("=" * 80)
                    for r in results:
                        data_count = len([k for k in r['data'].keys() if r['data'][k]])
                        print(f"   {r['stock_code']} ({r['stock_name']}): {data_count}가지")

                    summary = {
                        'timestamp': datetime.now().isoformat(),
                        'stocks': [{
                            'code': r['stock_code'],
                            'name': r['stock_name'],
                            'data_count': len([k for k in r['data'].keys() if r['data'][k]])
                        } for r in results]
                    }
                    save_json(summary, 'summary')

                    print(f"\n✅ 완료!")
                    print(f"📁 결과: tests/ 폴더\n")

                except Exception as e:
                    print(f"\n❌ 오류: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    print("👋 5초 후 종료...")
                    QTimer.singleShot(5000, app.quit)

            QTimer.singleShot(1000, start_collection)
        else:
            print(f"\n❌ 로그인 실패: {err_code}")
            app.quit()

    api.connect('on_event_connect', slot=on_login_complete)

    print("🔐 로그인 중...\n")
    api.login()

    sys.exit(app.exec_())


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 중단")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
