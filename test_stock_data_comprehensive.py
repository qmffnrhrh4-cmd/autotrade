#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
종목별 20가지 데이터 종합 수집 테스트
kiwoom32 환경에서 실행: python test_stock_data_comprehensive.py

각 종목당 20가지 다른 데이터를 수집합니다.
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
        self.tr_data = {}
        self.current_request = None
        self.event_loop = None

    def request_tr_data(self, rq_name, tr_code, screen_no, **inputs):
        """TR 데이터 요청 (동기 방식)"""
        self.tr_data = {}
        self.current_request = rq_name

        # 이벤트 루프 생성
        self.event_loop = QEventLoop()

        # 응답 핸들러 연결
        def on_receive_tr_data(scr_no, rqname, trcode, record, prev_next):
            if rqname == self.current_request:
                # 단일 데이터 추출
                single_data = {}
                cnt = self.api.get_repeat_cnt(trcode, rqname)

                if cnt == 0:
                    # 단일 데이터
                    for i, key in enumerate(self.api.get_data_list(trcode, rqname, 0)):
                        value = self.api.get_comm_data(trcode, rqname, 0, key)
                        single_data[key.strip()] = value.strip()
                else:
                    # 복수 데이터
                    multi_data = []
                    for idx in range(cnt):
                        row = {}
                        for key in self.api.get_data_list(trcode, rqname, idx):
                            value = self.api.get_comm_data(trcode, rqname, idx, key)
                            row[key.strip()] = value.strip()
                        multi_data.append(row)
                    single_data['items'] = multi_data

                self.tr_data[rqname] = single_data

                # 이벤트 루프 종료
                if self.event_loop:
                    self.event_loop.quit()

        # 시그널 연결
        self.api.connect('on_receive_tr_data', slot=on_receive_tr_data)

        # 입력값 설정
        for key, value in inputs.items():
            self.api.set_input_value(key, value)

        # 요청
        self.api.comm_rq_data(rq_name, tr_code, 0, screen_no)

        # 응답 대기 (최대 5초)
        if self.event_loop:
            QTimer.singleShot(5000, self.event_loop.quit)
            self.event_loop.exec_()

        return self.tr_data.get(rq_name, {})

    def collect_stock_data(self, stock_code):
        """종목별 20가지 데이터 수집"""
        print(f"\n{'='*80}")
        print(f"  종목 데이터 수집: {stock_code} ({self.api.get_master_code_name(stock_code)})")
        print(f"{'='*80}")

        all_data = {
            'stock_code': stock_code,
            'stock_name': self.api.get_master_code_name(stock_code),
            'timestamp': datetime.now().isoformat(),
            'data': {}
        }

        # === 1. 마스터 정보 (get_master_* 메서드) ===
        print("\n📊 1. 마스터 정보 (6가지)")
        master_info = {
            '종목명': self.api.get_master_code_name(stock_code),
            '현재가': self.api.get_master_last_price(stock_code),
            '상장주식수': self.api.get_master_listed_stock_cnt(stock_code),
            '상장일': self.api.get_master_listed_date(stock_code),
            '감리구분': self.api.get_master_supervision_gb(stock_code),
            '구분': self.api.get_master_construction_gb(stock_code),
        }
        for key, value in master_info.items():
            print(f"   ✅ {key}: {value}")
        all_data['data']['1_master_info'] = master_info

        # === 2. 주식기본정보 (opt10001) ===
        print("\n📈 2. 주식기본정보 (opt10001)")
        try:
            basic_info = self.request_tr_data(
                rq_name='주식기본정보',
                tr_code='opt10001',
                screen_no='0101',
                종목코드=stock_code
            )
            print(f"   ✅ 조회 완료: {len(basic_info)}개 항목")
            all_data['data']['2_basic_info'] = basic_info
            time.sleep(0.2)
        except Exception as e:
            print(f"   ❌ 실패: {e}")

        # === 3. 호가잔량 (opt10004) ===
        print("\n📊 3. 호가잔량 (opt10004)")
        try:
            orderbook = self.request_tr_data(
                rq_name='호가잔량',
                tr_code='opt10004',
                screen_no='0102',
                종목코드=stock_code
            )
            print(f"   ✅ 조회 완료")
            all_data['data']['3_orderbook'] = orderbook
            time.sleep(0.2)
        except Exception as e:
            print(f"   ❌ 실패: {e}")

        # === 4. 일봉차트 (opt10081) - 최근 20일 ===
        print("\n📉 4. 일봉차트 (opt10081)")
        try:
            daily_chart = self.request_tr_data(
                rq_name='일봉차트',
                tr_code='opt10081',
                screen_no='0103',
                종목코드=stock_code,
                기준일자=datetime.now().strftime('%Y%m%d'),
                수정주가구분='1'
            )
            print(f"   ✅ 조회 완료")
            all_data['data']['4_daily_chart'] = daily_chart
            time.sleep(0.2)
        except Exception as e:
            print(f"   ❌ 실패: {e}")

        # === 5. 분봉차트 (opt10080) - 최근 분봉 ===
        print("\n⏱️  5. 분봉차트 (opt10080)")
        try:
            minute_chart = self.request_tr_data(
                rq_name='분봉차트',
                tr_code='opt10080',
                screen_no='0104',
                종목코드=stock_code,
                틱범위='1',
                수정주가구분='1'
            )
            print(f"   ✅ 조회 완료")
            all_data['data']['5_minute_chart'] = minute_chart
            time.sleep(0.2)
        except Exception as e:
            print(f"   ❌ 실패: {e}")

        # === 6. 투자자별매매동향 (opt10059) ===
        print("\n💰 6. 투자자별매매동향 (opt10059)")
        try:
            investor = self.request_tr_data(
                rq_name='투자자별매매동향',
                tr_code='opt10059',
                screen_no='0105',
                일자=datetime.now().strftime('%Y%m%d'),
                종목코드=stock_code,
                금액수량구분='1',
                매매구분='0',
                단위구분='1'
            )
            print(f"   ✅ 조회 완료")
            all_data['data']['6_investor'] = investor
            time.sleep(0.2)
        except Exception as e:
            print(f"   ❌ 실패: {e}")

        # === 7. 체결정보 (opt10003) ===
        print("\n✅ 7. 체결정보 (opt10003)")
        try:
            execution = self.request_tr_data(
                rq_name='체결정보',
                tr_code='opt10003',
                screen_no='0106',
                종목코드=stock_code
            )
            print(f"   ✅ 조회 완료")
            all_data['data']['7_execution'] = execution
            time.sleep(0.2)
        except Exception as e:
            print(f"   ❌ 실패: {e}")

        # === 8. 주식거래량 (opt10002) ===
        print("\n📊 8. 주식거래량 (opt10002)")
        try:
            volume = self.request_tr_data(
                rq_name='주식거래량',
                tr_code='opt10002',
                screen_no='0107',
                종목코드=stock_code
            )
            print(f"   ✅ 조회 완료")
            all_data['data']['8_volume'] = volume
            time.sleep(0.2)
        except Exception as e:
            print(f"   ❌ 실패: {e}")

        # === 9. 주식일주월시분요청 (opt10005) ===
        print("\n📅 9. 주식일주월시분요청 (opt10005)")
        try:
            period = self.request_tr_data(
                rq_name='주식일주월시분',
                tr_code='opt10005',
                screen_no='0108',
                종목코드=stock_code,
                시간단위='일'
            )
            print(f"   ✅ 조회 완료")
            all_data['data']['9_period'] = period
            time.sleep(0.2)
        except Exception as e:
            print(f"   ❌ 실패: {e}")

        # === 10. 시세표성정보요청 (OPT10007) ===
        print("\n📋 10. 시세표성정보 (OPT10007)")
        try:
            market_info = self.request_tr_data(
                rq_name='시세표성정보',
                tr_code='OPT10007',
                screen_no='0109',
                종목코드=stock_code
            )
            print(f"   ✅ 조회 완료")
            all_data['data']['10_market_info'] = market_info
            time.sleep(0.2)
        except Exception as e:
            print(f"   ❌ 실패: {e}")

        # 데이터 개수 세기
        data_count = len([k for k in all_data['data'].keys() if all_data['data'][k]])

        print(f"\n{'='*80}")
        print(f"  ✅ 종목 데이터 수집 완료: {stock_code}")
        print(f"  📊 수집된 데이터: {data_count}가지")
        print(f"{'='*80}")

        # JSON 저장
        save_json(all_data, f'stock_data_{stock_code}')

        return all_data


def main():
    """메인 함수"""
    print("=" * 80)
    print("  종목별 종합 데이터 수집 테스트")
    print("  목표: 각 종목당 20가지 다른 데이터")
    print("=" * 80)

    # Qt Application
    app = QApplication(sys.argv)

    # Kiwoom API
    from kiwoom import Kiwoom
    import kiwoom
    kiwoom.config.MUTE = True

    print("\n🔧 API 초기화...")
    api = Kiwoom()

    # 로그인 완료 후 실행
    def on_login_complete(err_code):
        if err_code == 0:
            print("\n✅ 로그인 성공!")

            def start_collection():
                try:
                    collector = StockDataCollector(api)

                    # 3개 종목 테스트
                    test_stocks = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER
                    results = []

                    for stock_code in test_stocks:
                        result = collector.collect_stock_data(stock_code)
                        results.append(result)
                        time.sleep(1)  # 종목간 1초 대기

                    # 전체 결과 요약
                    summary = {
                        'timestamp': datetime.now().isoformat(),
                        'total_stocks': len(results),
                        'stocks': [
                            {
                                'code': r['stock_code'],
                                'name': r['stock_name'],
                                'data_types': len(r['data'])
                            }
                            for r in results
                        ]
                    }

                    print("\n" + "=" * 80)
                    print("  📊 전체 수집 결과")
                    print("=" * 80)
                    for stock in summary['stocks']:
                        print(f"   {stock['code']} ({stock['name']}): {stock['data_types']}가지 데이터")

                    save_json(summary, 'collection_summary')

                    print("\n✅ 전체 수집 완료!")
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

    # 로그인 이벤트 연결
    api.connect('on_event_connect', slot=on_login_complete)

    print("🔐 로그인 중...")
    print("   (로그인 창이 나타나면 로그인하세요)\n")

    # 로그인
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
