#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
개선된 종목 데이터 수집
- API 제한 준수 (초당 5회)
- 더 긴 대기 시간
- 상세한 에러 로깅
- 권한 필요한 TR 제외
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


class ImprovedStockCollector:
    """개선된 종목 데이터 수집"""

    def __init__(self, api):
        self.api = api
        self.received_data = None
        self.event_loop = None
        self.request_count = 0
        self.last_request_time = time.time()

    def on_receive_tr_data(self, scr_no, rqname, trcode, record_name, prev_next):
        """TR 데이터 수신"""
        print(f"      ✅ 데이터 수신: {rqname} ({trcode})")

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
                    elif trcode == 'opt10059':  # 투자자별 매매동향
                        item = {
                            '일자': self.api.GetCommData(trcode, rqname, i, "일자").strip(),
                            '기관순매수': self.api.GetCommData(trcode, rqname, i, "기관순매수").strip(),
                            '외인순매수': self.api.GetCommData(trcode, rqname, i, "외인순매수").strip(),
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

    def wait_for_api_limit(self):
        """API 호출 제한 준수 (초당 5회)"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        # 1초 이내에 5회 이상 요청 시 대기
        if elapsed < 1.0:
            self.request_count += 1
            if self.request_count >= 5:
                wait_time = 1.0 - elapsed + 0.1  # 여유 0.1초
                print(f"         ⏳ API 제한 대기: {wait_time:.1f}초")
                time.sleep(wait_time)
                self.request_count = 0
                self.last_request_time = time.time()
        else:
            # 1초 경과 시 카운트 초기화
            self.request_count = 0
            self.last_request_time = current_time

    def request_tr(self, rqname, trcode, inputs, timeout=10):
        """TR 요청 및 대기"""
        self.received_data = None
        self.event_loop = QEventLoop()

        # API 제한 준수
        self.wait_for_api_limit()

        # 입력값 설정
        for key, value in inputs.items():
            self.api.SetInputValue(key, value)

        # 요청
        ret = self.api.CommRqData(rqname, trcode, 0, "0101")

        if ret != 0:
            error_msg = f"요청 실패 코드: {ret}"
            print(f"         ❌ {error_msg}")
            return {'error': error_msg, 'error_code': ret}

        # 타임아웃 대기
        QTimer.singleShot(timeout * 1000, self.event_loop.quit)
        self.event_loop.exec_()

        if self.received_data is None:
            error_msg = f"타임아웃 ({timeout}초)"
            print(f"         ⚠️ {error_msg}")
            return {'error': error_msg}

        return self.received_data

    def collect(self, stock_code):
        """데이터 수집 (권한 필요한 TR 제외)"""
        print(f"\n{'='*80}")
        stock_name = self.api.GetMasterCodeName(stock_code)
        print(f"  종목: {stock_code} ({stock_name})")
        print(f"{'='*80}")

        all_data = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'timestamp': datetime.now().isoformat(),
            'data': {},
            'errors': []
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
        try:
            master = {
                '종목명': self.api.GetMasterCodeName(stock_code),
                '현재가': self.api.GetMasterLastPrice(stock_code),
                '상장주식수': self.api.GetMasterListedStockCnt(stock_code),
            }
            for k, v in master.items():
                print(f"   {k}: {v}")
            all_data['data']['01_마스터'] = master
        except Exception as e:
            error = f"마스터 정보 오류: {e}"
            print(f"   ❌ {error}")
            all_data['errors'].append(error)

        # TR 요청 목록 (권한 필요한 것 제외)
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
            # 6. 투자자별매매동향
            {
                'num': 6,
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
        ]

        # TR 요청 실행
        success_count = 0
        error_count = 0

        for tr in tr_list:
            print(f"\n📊 {tr['num']}. {tr['name']} ({tr['trcode']})")

            try:
                result = self.request_tr(
                    rqname=tr['name'],
                    trcode=tr['trcode'],
                    inputs=tr['inputs'],
                    timeout=10
                )

                if result:
                    if 'error' in result:
                        error_count += 1
                        all_data['errors'].append(f"{tr['name']}: {result.get('error')}")
                    elif result.get('data'):
                        all_data['data'][f"{tr['num']:02d}_{tr['name']}"] = result
                        success_count += 1
                    else:
                        error_count += 1
                        all_data['errors'].append(f"{tr['name']}: 데이터 없음")
                else:
                    error_count += 1
                    all_data['errors'].append(f"{tr['name']}: 응답 없음")

                # TR 간 추가 대기
                time.sleep(0.5)

            except Exception as e:
                error = f"{tr['name']} 예외: {e}"
                print(f"         ❌ {error}")
                all_data['errors'].append(error)
                error_count += 1

        # 결과 저장
        total_count = len(all_data['data'])
        print(f"\n{'='*40}")
        print(f"  수집 완료: {total_count}가지")
        print(f"  성공: {success_count}개 ✅")
        print(f"  실패: {error_count}개 ❌")
        print(f"{'='*40}")

        if all_data['errors']:
            print(f"\n⚠️  오류 목록:")
            for error in all_data['errors']:
                print(f"   - {error}")

        save_json(all_data, f'stock_improved_{stock_code}')
        return all_data


def main():
    """메인 함수"""
    print("=" * 80)
    print("  개선된 종목 데이터 수집")
    print("  - API 제한 준수 (초당 5회)")
    print("  - 더 긴 타임아웃 (10초)")
    print("  - 상세한 에러 로깅")
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
                    collector = ImprovedStockCollector(api)

                    # 이벤트 연결
                    api.OnReceiveTrData.connect(collector.on_receive_tr_data)

                    # 3개 종목 수집
                    stocks = ['005930', '000660', '035420']
                    results = []

                    for code in stocks:
                        result = collector.collect(code)
                        results.append(result)

                        # 종목 간 충분한 대기 (API 제한 대응)
                        print(f"\n⏳ 다음 종목 전 대기 (2초)...")
                        time.sleep(2)

                    # 요약
                    print(f"\n{'='*80}")
                    print("  전체 결과")
                    print(f"{'='*80}")
                    for r in results:
                        count = len(r['data'])
                        errors = len(r.get('errors', []))
                        print(f"   {r['stock_code']} ({r['stock_name']}): {count}가지 수집, {errors}개 오류")

                    save_json({'stocks': results}, 'summary_improved')

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
            print(f"\n❌ 로그인 실패: {err_code}")
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
