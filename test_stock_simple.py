#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
간단한 종목 데이터 수집 테스트
TR 데이터를 제대로 받아오는 최소한의 예제
"""

import sys
import json
import time
from datetime import datetime, timedelta
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
    print(f"   💾 저장: {filepath.name}")
    return filepath


class SimpleStockCollector:
    """간단한 종목 데이터 수집"""

    def __init__(self, api):
        self.api = api
        self.received_data = None
        self.event_loop = None

    def on_receive_tr_data(self, scr_no, rqname, trcode, record_name, prev_next):
        """TR 데이터 수신"""
        print(f"      ✅ 데이터 수신: {rqname}")

        # GetCommData를 사용하여 데이터 추출
        data = {}

        try:
            # 종목코드별로 다른 필드 추출
            if trcode == 'opt10001':  # 주식기본정보
                data = {
                    '종목명': self.api.GetCommData(trcode, rqname, 0, "종목명").strip(),
                    '현재가': self.api.GetCommData(trcode, rqname, 0, "현재가").strip(),
                    '등락률': self.api.GetCommData(trcode, rqname, 0, "등락률").strip(),
                    '거래량': self.api.GetCommData(trcode, rqname, 0, "거래량").strip(),
                    '거래대금': self.api.GetCommData(trcode, rqname, 0, "거래대금").strip(),
                    '시가': self.api.GetCommData(trcode, rqname, 0, "시가").strip(),
                    '고가': self.api.GetCommData(trcode, rqname, 0, "고가").strip(),
                    '저가': self.api.GetCommData(trcode, rqname, 0, "저가").strip(),
                    '전일대비': self.api.GetCommData(trcode, rqname, 0, "전일대비").strip(),
                }
            elif trcode == 'opt10081':  # 일봉차트
                # 여러 행 데이터
                cnt = self.api.GetRepeatCnt(trcode, rqname)
                print(f"         일봉 데이터 {cnt}개")

                items = []
                for i in range(min(cnt, 10)):  # 최근 10일
                    item = {
                        '일자': self.api.GetCommData(trcode, rqname, i, "일자").strip(),
                        '현재가': self.api.GetCommData(trcode, rqname, i, "현재가").strip(),
                        '시가': self.api.GetCommData(trcode, rqname, i, "시가").strip(),
                        '고가': self.api.GetCommData(trcode, rqname, i, "고가").strip(),
                        '저가': self.api.GetCommData(trcode, rqname, i, "저가").strip(),
                        '거래량': self.api.GetCommData(trcode, rqname, i, "거래량").strip(),
                    }
                    items.append(item)

                data = {'items': items, 'count': cnt}

            elif trcode == 'opt10004':  # 호가
                data = {
                    '매도호가1': self.api.GetCommData(trcode, rqname, 0, "(최우선)매도호가").strip(),
                    '매수호가1': self.api.GetCommData(trcode, rqname, 0, "(최우선)매수호가").strip(),
                    '매도호가잔량1': self.api.GetCommData(trcode, rqname, 0, "(최우선)매도호가잔량").strip(),
                    '매수호가잔량1': self.api.GetCommData(trcode, rqname, 0, "(최우선)매수호가잔량").strip(),
                }

        except Exception as e:
            print(f"         ⚠️ 데이터 추출 오류: {e}")
            # 원시 데이터라도 저장
            data = {'raw': '데이터 추출 실패'}

        self.received_data = {
            'trcode': trcode,
            'rqname': rqname,
            'data': data,
            'prev_next': prev_next
        }

        # 이벤트 루프 종료
        if self.event_loop and self.event_loop.isRunning():
            self.event_loop.quit()

    def request_tr(self, rqname, trcode, inputs):
        """TR 요청 및 대기"""
        self.received_data = None
        self.event_loop = QEventLoop()

        # 입력값 설정
        for key, value in inputs.items():
            self.api.SetInputValue(key, value)

        # 요청
        ret = self.api.CommRqData(rqname, trcode, 0, "0101")

        if ret != 0:
            print(f"         ❌ 요청 실패: {ret}")
            return None

        # 최대 5초 대기
        QTimer.singleShot(5000, self.event_loop.quit)
        self.event_loop.exec_()

        return self.received_data

    def collect(self, stock_code):
        """데이터 수집"""
        print(f"\n{'='*80}")
        stock_name = self.api.GetMasterCodeName(stock_code)
        print(f"  종목: {stock_code} ({stock_name})")
        print(f"{'='*80}")

        all_data = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'timestamp': datetime.now().isoformat(),
            'data': {}
        }

        # 1. 마스터 정보
        print("\n📊 1. 마스터 정보")
        master = {
            '종목명': self.api.GetMasterCodeName(stock_code),
            '현재가': self.api.GetMasterLastPrice(stock_code),
            '상장주식수': self.api.GetMasterListedStockCnt(stock_code),
        }
        for k, v in master.items():
            print(f"   {k}: {v}")
        all_data['data']['마스터'] = master

        # 2. 주식기본정보 (opt10001)
        print("\n📊 2. 주식기본정보 (opt10001)")
        result = self.request_tr(
            rqname='주식기본정보요청',
            trcode='opt10001',
            inputs={'종목코드': stock_code}
        )
        if result:
            all_data['data']['기본정보'] = result
        time.sleep(0.3)

        # 3. 일봉차트 (opt10081) - 최근 10일
        print("\n📊 3. 일봉차트 (opt10081)")

        # 가까운 금요일 계산
        today = datetime.now()
        days_since_friday = (today.weekday() - 4) % 7
        if days_since_friday == 0 and today.hour < 16:  # 금요일이지만 장 마감 전
            days_since_friday = 7
        last_friday = today - timedelta(days=days_since_friday)
        target_date = last_friday.strftime('%Y%m%d')

        print(f"      기준일: {target_date} (가까운 금요일)")

        result = self.request_tr(
            rqname='일봉차트조회',
            trcode='opt10081',
            inputs={
                '종목코드': stock_code,
                '기준일자': target_date,
                '수정주가구분': '1'
            }
        )
        if result:
            all_data['data']['일봉차트'] = result
        time.sleep(0.3)

        # 4. 호가 (opt10004)
        print("\n📊 4. 호가잔량 (opt10004)")
        result = self.request_tr(
            rqname='호가조회',
            trcode='opt10004',
            inputs={'종목코드': stock_code}
        )
        if result:
            all_data['data']['호가'] = result
        time.sleep(0.3)

        # 결과 저장
        count = len([k for k in all_data['data'].keys() if all_data['data'][k]])
        print(f"\n✅ 수집 완료: {count}가지")

        save_json(all_data, f'stock_{stock_code}')
        return all_data


def main():
    """메인 함수"""
    print("=" * 80)
    print("  간단한 종목 데이터 수집 테스트")
    print("=" * 80)

    app = QApplication(sys.argv)

    from kiwoom import Kiwoom
    import kiwoom as kw
    kw.config.MUTE = True

    print("\n🔧 API 초기화...")
    api = Kiwoom()

    def on_login(err_code):
        if err_code == 0:
            print("\n✅ 로그인 성공!")

            def start():
                try:
                    collector = SimpleStockCollector(api)

                    # 이벤트 연결
                    api.OnReceiveTrData.connect(collector.on_receive_tr_data)

                    # 3개 종목 수집
                    stocks = ['005930', '000660', '035420']
                    results = []

                    for code in stocks:
                        result = collector.collect(code)
                        results.append(result)
                        time.sleep(1)

                    # 요약
                    print(f"\n{'='*80}")
                    print("  전체 결과")
                    print(f"{'='*80}")
                    for r in results:
                        count = len([k for k in r['data'].keys() if r['data'][k]])
                        print(f"   {r['stock_code']} ({r['stock_name']}): {count}가지")

                    save_json({'stocks': results}, 'summary')

                    print("\n✅ 완료!\n")

                except Exception as e:
                    print(f"\n❌ 오류: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    print("5초 후 종료...")
                    QTimer.singleShot(5000, app.quit)

            QTimer.singleShot(1000, start)
        else:
            print(f"\n❌ 로그인 실패")
            app.quit()

    api.OnEventConnect.connect(on_login)

    print("🔐 로그인 중...\n")
    api.CommConnect()

    sys.exit(app.exec_())


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n중단")
        sys.exit(0)
    except Exception as e:
        print(f"\n오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
