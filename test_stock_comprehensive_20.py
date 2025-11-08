#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
종목별 20가지 데이터 종합 수집
올바른 breadum/kiwoom API 패턴 사용

수집 데이터:
1. 마스터 정보 (종목명, 현재가, 상장주식수)
2. 주식기본정보 (opt10001)
3. 호가잔량 (opt10004)
4. 일봉차트 (opt10081)
5. 분봉차트 (opt10080)
6. 주식거래량 (opt10002)
7. 체결정보 (opt10003)
8. 시세표성정보 (opt10007)
9. 전일대비 등락률 (opt10005)
10. 투자자별 매매동향 (opt10059)
11. 종목별 투자자 기관 (opt10060)
12. 외인기관 종목별 매매 (opt10061)
13. 프로그램매매 종목별 (opt10062)
14. 시간대별 체결가 (opt10016)
15. 일자별 매매상위 (opt10063)
16. 월별 투자자 매매 (opt10064)
17. 주문체결내역 조회 (opt10075)
18. 당일매매일지 (opt10076)
19. 신용잔고 (opt10013)
20. 주식선물현재가(시세) (opt50001)
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


class ComprehensiveStockCollector:
    """종합 종목 데이터 수집 (20가지)"""

    def __init__(self, api):
        self.api = api
        self.received_data = None
        self.event_loop = None

    def on_receive_tr_data(self, scr_no, rqname, trcode, record_name, prev_next):
        """TR 데이터 수신"""
        print(f"      ✅ 데이터 수신: {rqname}")

        data = {}

        try:
            # 반복 횟수 확인
            cnt = self.api.GetRepeatCnt(trcode, rqname)

            if cnt == 0:
                # 단일 데이터
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
                        '시가총액': self.api.GetCommData(trcode, rqname, 0, "시가총액").strip(),
                    }
                elif trcode == 'opt10004':  # 호가
                    data = {
                        '매도호가1': self.api.GetCommData(trcode, rqname, 0, "(최우선)매도호가").strip(),
                        '매수호가1': self.api.GetCommData(trcode, rqname, 0, "(최우선)매수호가").strip(),
                        '매도호가잔량1': self.api.GetCommData(trcode, rqname, 0, "(최우선)매도호가잔량").strip(),
                        '매수호가잔량1': self.api.GetCommData(trcode, rqname, 0, "(최우선)매수호가잔량").strip(),
                    }
                elif trcode == 'opt10007':  # 시세표성정보
                    data = {
                        '종목명': self.api.GetCommData(trcode, rqname, 0, "종목명").strip(),
                        '현재가': self.api.GetCommData(trcode, rqname, 0, "현재가").strip(),
                        '거래량': self.api.GetCommData(trcode, rqname, 0, "거래량").strip(),
                        '시가총액': self.api.GetCommData(trcode, rqname, 0, "시가총액").strip(),
                    }
                elif trcode == 'opt10013':  # 신용잔고
                    data = {
                        '신용잔고율': self.api.GetCommData(trcode, rqname, 0, "신용잔고율").strip(),
                        '신용잔고증감': self.api.GetCommData(trcode, rqname, 0, "신용잔고증감").strip(),
                    }
                elif trcode == 'opt50001':  # 주식선물현재가
                    data = {
                        '현재가': self.api.GetCommData(trcode, rqname, 0, "현재가").strip(),
                        '전일대비': self.api.GetCommData(trcode, rqname, 0, "전일대비").strip(),
                    }
                else:
                    # 기타 단일 데이터 - 가능한 필드 추출
                    for field_name in ['종목명', '현재가', '거래량', '등락률', '시가', '고가', '저가']:
                        try:
                            value = self.api.GetCommData(trcode, rqname, 0, field_name).strip()
                            if value:
                                data[field_name] = value
                        except:
                            pass
            else:
                # 복수 데이터
                items = []
                for i in range(min(cnt, 20)):  # 최대 20개
                    item = {}

                    if trcode == 'opt10081':  # 일봉차트
                        item = {
                            '일자': self.api.GetCommData(trcode, rqname, i, "일자").strip(),
                            '현재가': self.api.GetCommData(trcode, rqname, i, "현재가").strip(),
                            '시가': self.api.GetCommData(trcode, rqname, i, "시가").strip(),
                            '고가': self.api.GetCommData(trcode, rqname, i, "고가").strip(),
                            '저가': self.api.GetCommData(trcode, rqname, i, "저가").strip(),
                            '거래량': self.api.GetCommData(trcode, rqname, i, "거래량").strip(),
                        }
                    elif trcode == 'opt10080':  # 분봉차트
                        item = {
                            '체결시간': self.api.GetCommData(trcode, rqname, i, "체결시간").strip(),
                            '현재가': self.api.GetCommData(trcode, rqname, i, "현재가").strip(),
                            '시가': self.api.GetCommData(trcode, rqname, i, "시가").strip(),
                            '고가': self.api.GetCommData(trcode, rqname, i, "고가").strip(),
                            '저가': self.api.GetCommData(trcode, rqname, i, "저가").strip(),
                            '거래량': self.api.GetCommData(trcode, rqname, i, "거래량").strip(),
                        }
                    elif trcode == 'opt10002':  # 주식거래량
                        item = {
                            '일자': self.api.GetCommData(trcode, rqname, i, "일자").strip(),
                            '거래량': self.api.GetCommData(trcode, rqname, i, "거래량").strip(),
                            '거래대금': self.api.GetCommData(trcode, rqname, i, "거래대금").strip(),
                        }
                    elif trcode == 'opt10003':  # 체결정보
                        item = {
                            '체결시간': self.api.GetCommData(trcode, rqname, i, "체결시간").strip(),
                            '현재가': self.api.GetCommData(trcode, rqname, i, "현재가").strip(),
                            '대비': self.api.GetCommData(trcode, rqname, i, "대비").strip(),
                            '거래량': self.api.GetCommData(trcode, rqname, i, "거래량").strip(),
                        }
                    elif trcode == 'opt10005':  # 전일대비 등락률
                        item = {
                            '일자': self.api.GetCommData(trcode, rqname, i, "일자").strip(),
                            '등락률': self.api.GetCommData(trcode, rqname, i, "등락률").strip(),
                            '현재가': self.api.GetCommData(trcode, rqname, i, "현재가").strip(),
                        }
                    elif trcode == 'opt10059':  # 투자자별 매매동향
                        item = {
                            '일자': self.api.GetCommData(trcode, rqname, i, "일자").strip(),
                            '기관순매수': self.api.GetCommData(trcode, rqname, i, "기관순매수").strip(),
                            '외인순매수': self.api.GetCommData(trcode, rqname, i, "외인순매수").strip(),
                        }
                    elif trcode == 'opt10060':  # 종목별 투자자 기관
                        item = {
                            '투자자': self.api.GetCommData(trcode, rqname, i, "투자자").strip(),
                            '매수거래량': self.api.GetCommData(trcode, rqname, i, "매수거래량").strip(),
                            '매도거래량': self.api.GetCommData(trcode, rqname, i, "매도거래량").strip(),
                        }
                    elif trcode == 'opt10061':  # 외인기관 종목별 매매
                        item = {
                            '일자': self.api.GetCommData(trcode, rqname, i, "일자").strip(),
                            '외인순매수': self.api.GetCommData(trcode, rqname, i, "외인순매수").strip(),
                            '기관순매수': self.api.GetCommData(trcode, rqname, i, "기관순매수").strip(),
                        }
                    elif trcode == 'opt10062':  # 프로그램매매 종목별
                        item = {
                            '시간': self.api.GetCommData(trcode, rqname, i, "시간").strip(),
                            '매수량': self.api.GetCommData(trcode, rqname, i, "매수량").strip(),
                            '매도량': self.api.GetCommData(trcode, rqname, i, "매도량").strip(),
                        }
                    elif trcode == 'opt10016':  # 시간대별 체결가
                        item = {
                            '체결시간': self.api.GetCommData(trcode, rqname, i, "체결시간").strip(),
                            '현재가': self.api.GetCommData(trcode, rqname, i, "현재가").strip(),
                            '거래량': self.api.GetCommData(trcode, rqname, i, "거래량").strip(),
                        }
                    elif trcode == 'opt10063':  # 일자별 매매상위
                        item = {
                            '일자': self.api.GetCommData(trcode, rqname, i, "일자").strip(),
                            '현재가': self.api.GetCommData(trcode, rqname, i, "현재가").strip(),
                            '거래량': self.api.GetCommData(trcode, rqname, i, "거래량").strip(),
                        }
                    elif trcode == 'opt10064':  # 월별 투자자 매매
                        item = {
                            '일자': self.api.GetCommData(trcode, rqname, i, "일자").strip(),
                            '기관': self.api.GetCommData(trcode, rqname, i, "기관").strip(),
                            '외인': self.api.GetCommData(trcode, rqname, i, "외인").strip(),
                        }
                    else:
                        # 기타 복수 데이터 - 일반적 필드 추출
                        for field_name in ['일자', '체결시간', '현재가', '거래량', '시가', '고가', '저가']:
                            try:
                                value = self.api.GetCommData(trcode, rqname, i, field_name).strip()
                                if value:
                                    item[field_name] = value
                            except:
                                pass

                    if item:
                        items.append(item)

                data = {'items': items, 'count': cnt}

        except Exception as e:
            print(f"         ⚠️ 데이터 추출 오류: {e}")
            data = {'error': str(e)}

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
        """데이터 수집 (20가지)"""
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

        # 가까운 금요일 계산
        today = datetime.now()
        days_since_friday = (today.weekday() - 4) % 7
        if days_since_friday == 0 and today.hour < 16:
            days_since_friday = 7
        last_friday = today - timedelta(days=days_since_friday)
        target_date = last_friday.strftime('%Y%m%d')

        # 1. 마스터 정보
        print("\n📊 1. 마스터 정보")
        master = {
            '종목명': self.api.GetMasterCodeName(stock_code),
            '현재가': self.api.GetMasterLastPrice(stock_code),
            '상장주식수': self.api.GetMasterListedStockCnt(stock_code),
        }
        for k, v in master.items():
            print(f"   {k}: {v}")
        all_data['data']['01_마스터'] = master

        # TR 요청 목록 (19가지 추가)
        tr_list = [
            # 2. 주식기본정보
            {
                'num': 2,
                'name': '주식기본정보',
                'trcode': 'opt10001',
                'inputs': {'종목코드': stock_code}
            },
            # 3. 호가잔량
            {
                'num': 3,
                'name': '호가잔량',
                'trcode': 'opt10004',
                'inputs': {'종목코드': stock_code}
            },
            # 4. 일봉차트
            {
                'num': 4,
                'name': '일봉차트',
                'trcode': 'opt10081',
                'inputs': {
                    '종목코드': stock_code,
                    '기준일자': target_date,
                    '수정주가구분': '1'
                }
            },
            # 5. 분봉차트
            {
                'num': 5,
                'name': '분봉차트',
                'trcode': 'opt10080',
                'inputs': {
                    '종목코드': stock_code,
                    '틱범위': '1',
                    '수정주가구분': '1'
                }
            },
            # 6. 주식거래량
            {
                'num': 6,
                'name': '주식거래량',
                'trcode': 'opt10002',
                'inputs': {'종목코드': stock_code}
            },
            # 7. 체결정보
            {
                'num': 7,
                'name': '체결정보',
                'trcode': 'opt10003',
                'inputs': {'종목코드': stock_code}
            },
            # 8. 시세표성정보
            {
                'num': 8,
                'name': '시세표성정보',
                'trcode': 'opt10007',
                'inputs': {'종목코드': stock_code}
            },
            # 9. 전일대비등락률
            {
                'num': 9,
                'name': '전일대비등락률',
                'trcode': 'opt10005',
                'inputs': {
                    '종목코드': stock_code,
                    '기준일자': target_date
                }
            },
            # 10. 투자자별매매동향
            {
                'num': 10,
                'name': '투자자별매매동향',
                'trcode': 'opt10059',
                'inputs': {
                    '일자': target_date,
                    '종목코드': stock_code,
                    '금액수량구분': '1',
                    '매매구분': '0',
                    '단위구분': '1'
                }
            },
            # 11. 종목별투자자기관
            {
                'num': 11,
                'name': '종목별투자자기관',
                'trcode': 'opt10060',
                'inputs': {
                    '종목코드': stock_code,
                    '일자': target_date
                }
            },
            # 12. 외인기관종목별매매
            {
                'num': 12,
                'name': '외인기관종목별매매',
                'trcode': 'opt10061',
                'inputs': {
                    '종목코드': stock_code,
                    '기준일자': target_date
                }
            },
            # 13. 프로그램매매종목별
            {
                'num': 13,
                'name': '프로그램매매종목별',
                'trcode': 'opt10062',
                'inputs': {
                    '종목코드': stock_code,
                    '시간구분': '0'
                }
            },
            # 14. 시간대별체결가
            {
                'num': 14,
                'name': '시간대별체결가',
                'trcode': 'opt10016',
                'inputs': {
                    '종목코드': stock_code,
                    '시간구분': '1'
                }
            },
            # 15. 일자별매매상위
            {
                'num': 15,
                'name': '일자별매매상위',
                'trcode': 'opt10063',
                'inputs': {
                    '종목코드': stock_code,
                    '조회구분': '1'
                }
            },
            # 16. 월별투자자매매
            {
                'num': 16,
                'name': '월별투자자매매',
                'trcode': 'opt10064',
                'inputs': {
                    '종목코드': stock_code,
                    '시작일자': target_date,
                    '끝일자': datetime.now().strftime('%Y%m%d')
                }
            },
            # 17. 신용잔고
            {
                'num': 17,
                'name': '신용잔고',
                'trcode': 'opt10013',
                'inputs': {
                    '종목코드': stock_code,
                    '기준일자': target_date
                }
            },
            # 18. 시간대별체결조회
            {
                'num': 18,
                'name': '시간대별체결조회',
                'trcode': 'opt10016',
                'inputs': {
                    '종목코드': stock_code,
                    '시간구분': '0'
                }
            },
            # 19. 주식선물현재가
            {
                'num': 19,
                'name': '주식선물현재가',
                'trcode': 'opt50001',
                'inputs': {'종목코드': stock_code}
            },
            # 20. 일별체결정보
            {
                'num': 20,
                'name': '일별체결정보',
                'trcode': 'opt10003',
                'inputs': {
                    '종목코드': stock_code,
                    '틱범위': '1'
                }
            },
        ]

        # TR 요청 실행
        for tr in tr_list:
            print(f"\n📊 {tr['num']}. {tr['name']} ({tr['trcode']})")

            result = self.request_tr(
                rqname=tr['name'],
                trcode=tr['trcode'],
                inputs=tr['inputs']
            )

            if result and result.get('data'):
                all_data['data'][f"{tr['num']:02d}_{tr['name']}"] = result

            time.sleep(0.3)  # API 제한 준수

        # 결과 저장
        count = len([k for k in all_data['data'].keys() if all_data['data'][k]])
        print(f"\n✅ 수집 완료: {count}가지")

        save_json(all_data, f'stock_20types_{stock_code}')
        return all_data


def main():
    """메인 함수"""
    print("=" * 80)
    print("  종목별 20가지 데이터 종합 수집")
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
                    collector = ComprehensiveStockCollector(api)

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

                    save_json({'stocks': results}, 'summary_20types')

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
