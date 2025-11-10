"""
키움 OpenAPI 종합 테스트
주요 TR들이 제대로 작동하는지 확인
"""

import sys
import time
import json
from datetime import datetime
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QEventLoop, QTimer
from kiwoom import Kiwoom

# 테스트 결과 저장
test_results = []

def log(msg):
    """로그 출력 및 기록"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

class OpenAPITester:
    def __init__(self, api):
        self.api = api
        self.received_data = {'result': None, 'completed': False, 'event_loop': None}

    def reset(self):
        """데이터 초기화"""
        self.received_data = {'result': None, 'completed': False, 'event_loop': None}

    def test_opt10001_stock_info(self, stock_code):
        """
        opt10001 - 주식기본정보조회
        단일 데이터 TR (연속조회 없음)
        """
        log(f"\n{'='*80}")
        log(f"테스트: opt10001 - 주식기본정보조회")
        log(f"종목: {stock_code}")
        log(f"{'='*80}")

        result = {
            'tr_code': 'opt10001',
            'tr_name': '주식기본정보조회',
            'stock_code': stock_code,
            'start_time': datetime.now().isoformat(),
            'success': False,
            'data': None,
            'error': None
        }

        self.reset()

        def on_receive(scr_no, rq_name, tr_code, record_name, prev_next):
            if rq_name != 'test_opt10001':
                return

            try:
                data = {
                    '종목명': self.api.GetCommData(tr_code, rq_name, 0, "종목명").strip(),
                    '현재가': self.api.GetCommData(tr_code, rq_name, 0, "현재가").strip(),
                    '등락율': self.api.GetCommData(tr_code, rq_name, 0, "등락율").strip(),
                    '거래량': self.api.GetCommData(tr_code, rq_name, 0, "거래량").strip(),
                    '시가': self.api.GetCommData(tr_code, rq_name, 0, "시가").strip(),
                    '고가': self.api.GetCommData(tr_code, rq_name, 0, "고가").strip(),
                    '저가': self.api.GetCommData(tr_code, rq_name, 0, "저가").strip(),
                    '거래대금': self.api.GetCommData(tr_code, rq_name, 0, "거래대금").strip(),
                }

                self.received_data['result'] = data
            except Exception as e:
                self.received_data['result'] = {'error': str(e)}

            self.received_data['completed'] = True
            if self.received_data['event_loop'] and self.received_data['event_loop'].isRunning():
                self.received_data['event_loop'].quit()

        self.api.OnReceiveTrData.connect(on_receive)

        try:
            self.api.SetInputValue('종목코드', stock_code)

            event_loop = QEventLoop()
            self.received_data['event_loop'] = event_loop

            ret = self.api.CommRqData('test_opt10001', 'opt10001', 0, '0101')

            if ret != 0:
                result['error'] = f"CommRqData failed: {ret}"
                log(f"❌ 요청 실패: {ret}")
            else:
                QTimer.singleShot(10000, event_loop.quit)
                event_loop.exec_()

                if self.received_data['completed'] and self.received_data['result']:
                    if 'error' not in self.received_data['result']:
                        result['success'] = True
                        result['data'] = self.received_data['result']
                        log(f"✅ 성공: {self.received_data['result']}")
                    else:
                        result['error'] = self.received_data['result']['error']
                        log(f"❌ 데이터 추출 오류: {result['error']}")
                else:
                    result['error'] = 'Timeout'
                    log(f"❌ 타임아웃")
        finally:
            try:
                self.api.OnReceiveTrData.disconnect(on_receive)
            except:
                pass

        result['end_time'] = datetime.now().isoformat()
        return result

    def test_opt10081_daily_chart(self, stock_code, max_requests=3):
        """
        opt10081 - 주식일봉차트조회
        연속조회 가능
        """
        log(f"\n{'='*80}")
        log(f"테스트: opt10081 - 주식일봉차트조회 (연속조회)")
        log(f"종목: {stock_code}, 최대 {max_requests}회")
        log(f"{'='*80}")

        result = {
            'tr_code': 'opt10081',
            'tr_name': '주식일봉차트조회',
            'stock_code': stock_code,
            'start_time': datetime.now().isoformat(),
            'success': False,
            'total_items': 0,
            'requests': [],
            'error': None
        }

        all_items = []
        prev_next_value = 0
        request_count = 0

        def on_receive(scr_no, rq_name, tr_code, record_name, prev_next):
            if rq_name != 'test_opt10081':
                return

            try:
                cnt = self.api.GetRepeatCnt(tr_code, rq_name)
                items = []

                for i in range(cnt):
                    item = {
                        '일자': self.api.GetCommData(tr_code, rq_name, i, "일자").strip(),
                        '현재가': self.api.GetCommData(tr_code, rq_name, i, "현재가").strip(),
                        '시가': self.api.GetCommData(tr_code, rq_name, i, "시가").strip(),
                        '고가': self.api.GetCommData(tr_code, rq_name, i, "고가").strip(),
                        '저가': self.api.GetCommData(tr_code, rq_name, i, "저가").strip(),
                        '거래량': self.api.GetCommData(tr_code, rq_name, i, "거래량").strip(),
                    }
                    items.append(item)

                self.received_data['result'] = {
                    'items': items,
                    'count': cnt,
                    'prev_next': int(prev_next) if prev_next else 0
                }
            except Exception as e:
                self.received_data['result'] = {'error': str(e)}

            self.received_data['completed'] = True
            if self.received_data['event_loop'] and self.received_data['event_loop'].isRunning():
                self.received_data['event_loop'].quit()

        self.api.OnReceiveTrData.connect(on_receive)

        try:
            while request_count < max_requests:
                request_count += 1
                self.received_data['result'] = None
                self.received_data['completed'] = False

                log(f"  {request_count}회차 조회 (prev_next={prev_next_value})")

                # 매 요청마다 SetInputValue 호출
                self.api.SetInputValue('종목코드', stock_code)
                self.api.SetInputValue('기준일자', datetime.now().strftime('%Y%m%d'))
                self.api.SetInputValue('수정주가구분', '1')

                event_loop = QEventLoop()
                self.received_data['event_loop'] = event_loop

                ret = self.api.CommRqData('test_opt10081', 'opt10081', prev_next_value, '0101')

                request_result = {
                    'attempt': request_count,
                    'return_code': ret,
                    'items_received': 0,
                    'success': False
                }

                if ret != 0:
                    request_result['error'] = f"Request failed: {ret}"
                    result['requests'].append(request_result)
                    log(f"  ❌ 요청 실패: {ret}")
                    break
                else:
                    QTimer.singleShot(10000, event_loop.quit)
                    event_loop.exec_()

                    if self.received_data['completed'] and self.received_data['result']:
                        res = self.received_data['result']

                        if 'error' not in res:
                            items = res.get('items', [])
                            all_items.extend(items)
                            prev_next_value = res.get('prev_next', 0)

                            request_result['items_received'] = len(items)
                            request_result['success'] = True

                            log(f"  ✅ {len(items)}개 수신 (누적: {len(all_items)}개)")

                            if prev_next_value != 2:
                                log(f"  ℹ️  연속 조회 종료 (prev_next={prev_next_value})")
                                result['requests'].append(request_result)
                                break
                        else:
                            request_result['error'] = res['error']
                            log(f"  ❌ 데이터 추출 오류: {res['error']}")
                    else:
                        request_result['error'] = 'Timeout'
                        log(f"  ❌ 타임아웃")

                result['requests'].append(request_result)

                if prev_next_value == 2 and request_count < max_requests:
                    time.sleep(1.0)

            if len(all_items) > 0:
                result['success'] = True
                result['total_items'] = len(all_items)
                result['sample_data'] = all_items[:3]  # 첫 3개만 저장
                log(f"\n✅ 최종 결과: 총 {len(all_items)}개 일봉 데이터 수집")
            else:
                result['error'] = 'No data received'
                log(f"\n❌ 데이터 없음")

        finally:
            try:
                self.api.OnReceiveTrData.disconnect(on_receive)
            except:
                pass

        result['end_time'] = datetime.now().isoformat()
        return result

    def test_opt10080_minute_chart(self, stock_code, interval, max_requests=5):
        """
        opt10080 - 주식분봉차트조회
        연속조회 가능 (이미 성공 확인됨)
        """
        log(f"\n{'='*80}")
        log(f"테스트: opt10080 - 주식분봉차트조회 ({interval}분봉)")
        log(f"종목: {stock_code}, 최대 {max_requests}회")
        log(f"{'='*80}")

        result = {
            'tr_code': 'opt10080',
            'tr_name': f'주식분봉차트조회_{interval}분',
            'stock_code': stock_code,
            'interval': interval,
            'start_time': datetime.now().isoformat(),
            'success': False,
            'total_items': 0,
            'requests': [],
            'error': None
        }

        all_items = []
        prev_next_value = 0
        request_count = 0

        def on_receive(scr_no, rq_name, tr_code, record_name, prev_next):
            if rq_name != 'test_opt10080':
                return

            try:
                cnt = self.api.GetRepeatCnt(tr_code, rq_name)
                items = []

                for i in range(min(cnt, 100)):
                    item = {
                        '체결시간': self.api.GetCommData(tr_code, rq_name, i, "체결시간").strip(),
                        '현재가': self.api.GetCommData(tr_code, rq_name, i, "현재가").strip(),
                        '시가': self.api.GetCommData(tr_code, rq_name, i, "시가").strip(),
                        '고가': self.api.GetCommData(tr_code, rq_name, i, "고가").strip(),
                        '저가': self.api.GetCommData(tr_code, rq_name, i, "저가").strip(),
                        '거래량': self.api.GetCommData(tr_code, rq_name, i, "거래량").strip(),
                    }
                    items.append(item)

                self.received_data['result'] = {
                    'items': items,
                    'count': cnt,
                    'prev_next': int(prev_next) if prev_next else 0
                }
            except Exception as e:
                self.received_data['result'] = {'error': str(e)}

            self.received_data['completed'] = True
            if self.received_data['event_loop'] and self.received_data['event_loop'].isRunning():
                self.received_data['event_loop'].quit()

        self.api.OnReceiveTrData.connect(on_receive)

        try:
            while request_count < max_requests:
                request_count += 1
                self.received_data['result'] = None
                self.received_data['completed'] = False

                log(f"  {request_count}회차 조회 (prev_next={prev_next_value})")

                # 매 요청마다 SetInputValue 호출
                self.api.SetInputValue('종목코드', stock_code)
                self.api.SetInputValue('틱범위', str(interval))
                self.api.SetInputValue('수정주가구분', '1')

                event_loop = QEventLoop()
                self.received_data['event_loop'] = event_loop

                ret = self.api.CommRqData('test_opt10080', 'opt10080', prev_next_value, '0101')

                request_result = {
                    'attempt': request_count,
                    'return_code': ret,
                    'items_received': 0,
                    'success': False
                }

                if ret != 0:
                    request_result['error'] = f"Request failed: {ret}"
                    result['requests'].append(request_result)
                    log(f"  ❌ 요청 실패: {ret}")
                    break
                else:
                    QTimer.singleShot(10000, event_loop.quit)
                    event_loop.exec_()

                    if self.received_data['completed'] and self.received_data['result']:
                        res = self.received_data['result']

                        if 'error' not in res:
                            items = res.get('items', [])
                            all_items.extend(items)
                            prev_next_value = res.get('prev_next', 0)

                            request_result['items_received'] = len(items)
                            request_result['success'] = True

                            log(f"  ✅ {len(items)}개 수신 (누적: {len(all_items)}개)")

                            if prev_next_value != 2:
                                log(f"  ℹ️  연속 조회 종료 (prev_next={prev_next_value})")
                                result['requests'].append(request_result)
                                break
                        else:
                            request_result['error'] = res['error']
                            log(f"  ❌ 데이터 추출 오류: {res['error']}")
                    else:
                        request_result['error'] = 'Timeout'
                        log(f"  ❌ 타임아웃")

                result['requests'].append(request_result)

                if prev_next_value == 2 and request_count < max_requests:
                    time.sleep(1.0)

            if len(all_items) > 0:
                result['success'] = True
                result['total_items'] = len(all_items)
                result['sample_data'] = all_items[:3]
                log(f"\n✅ 최종 결과: 총 {len(all_items)}개 분봉 데이터 수집")
            else:
                result['error'] = 'No data received'
                log(f"\n❌ 데이터 없음")

        finally:
            try:
                self.api.OnReceiveTrData.disconnect(on_receive)
            except:
                pass

        result['end_time'] = datetime.now().isoformat()
        return result

    def test_opw00001_deposit(self):
        """
        opw00001 - 예수금상세현황요청
        계좌 정보 필요
        """
        log(f"\n{'='*80}")
        log(f"테스트: opw00001 - 예수금상세현황요청")
        log(f"{'='*80}")

        result = {
            'tr_code': 'opw00001',
            'tr_name': '예수금상세현황요청',
            'start_time': datetime.now().isoformat(),
            'success': False,
            'data': None,
            'error': None
        }

        # 계좌번호 가져오기
        account_cnt = self.api.GetLoginInfo("ACCOUNT_CNT")
        if account_cnt == '0':
            result['error'] = 'No account found'
            log(f"❌ 계좌 없음")
            return result

        accounts = self.api.GetLoginInfo("ACCNO").rstrip(';').split(';')
        account = accounts[0]
        log(f"계좌: {account}")

        self.reset()

        def on_receive(scr_no, rq_name, tr_code, record_name, prev_next):
            if rq_name != 'test_opw00001':
                return

            try:
                data = {
                    '예수금': self.api.GetCommData(tr_code, rq_name, 0, "예수금").strip(),
                    'd+2추정예수금': self.api.GetCommData(tr_code, rq_name, 0, "d+2추정예수금").strip(),
                    '유가잔고평가액': self.api.GetCommData(tr_code, rq_name, 0, "유가잔고평가액").strip(),
                    '예탁자산평가액': self.api.GetCommData(tr_code, rq_name, 0, "예탁자산평가액").strip(),
                    '주문가능금액': self.api.GetCommData(tr_code, rq_name, 0, "주문가능금액").strip(),
                }

                self.received_data['result'] = data
            except Exception as e:
                self.received_data['result'] = {'error': str(e)}

            self.received_data['completed'] = True
            if self.received_data['event_loop'] and self.received_data['event_loop'].isRunning():
                self.received_data['event_loop'].quit()

        self.api.OnReceiveTrData.connect(on_receive)

        try:
            self.api.SetInputValue('계좌번호', account)
            self.api.SetInputValue('비밀번호', '')
            self.api.SetInputValue('비밀번호입력매체구분', '00')
            self.api.SetInputValue('조회구분', '2')

            event_loop = QEventLoop()
            self.received_data['event_loop'] = event_loop

            ret = self.api.CommRqData('test_opw00001', 'opw00001', 0, '0101')

            if ret != 0:
                result['error'] = f"CommRqData failed: {ret}"
                log(f"❌ 요청 실패: {ret}")
            else:
                QTimer.singleShot(10000, event_loop.quit)
                event_loop.exec_()

                if self.received_data['completed'] and self.received_data['result']:
                    if 'error' not in self.received_data['result']:
                        result['success'] = True
                        result['data'] = self.received_data['result']
                        log(f"✅ 성공: {self.received_data['result']}")
                    else:
                        result['error'] = self.received_data['result']['error']
                        log(f"❌ 데이터 추출 오류: {result['error']}")
                else:
                    result['error'] = 'Timeout'
                    log(f"❌ 타임아웃")
        finally:
            try:
                self.api.OnReceiveTrData.disconnect(on_receive)
            except:
                pass

        result['end_time'] = datetime.now().isoformat()
        return result


def run_all_tests():
    """모든 테스트 실행"""
    log("="*80)
    log("키움 OpenAPI 종합 테스트 시작")
    log(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("="*80)

    # QApplication 초기화
    app = QApplication(sys.argv)

    # Kiwoom API 초기화
    api = Kiwoom()
    api.CommConnect()

    # 로그인 대기
    log("\n로그인 대기 중...")
    loop = QEventLoop()
    api.OnEventConnect.connect(lambda err_code: loop.quit())
    loop.exec_()

    log("✅ 로그인 완료!\n")

    # 테스터 초기화
    tester = OpenAPITester(api)

    # 테스트할 종목
    stock_code = '005930'  # 삼성전자

    # ===========================================
    # 테스트 1: opt10001 - 주식기본정보조회
    # ===========================================
    result = tester.test_opt10001_stock_info(stock_code)
    test_results.append(result)
    time.sleep(1)

    # ===========================================
    # 테스트 2: opt10080 - 주식분봉차트조회 (1분)
    # ===========================================
    result = tester.test_opt10080_minute_chart(stock_code, 1, max_requests=5)
    test_results.append(result)
    time.sleep(1)

    # ===========================================
    # 테스트 3: opt10080 - 주식분봉차트조회 (5분)
    # ===========================================
    result = tester.test_opt10080_minute_chart(stock_code, 5, max_requests=3)
    test_results.append(result)
    time.sleep(1)

    # ===========================================
    # 테스트 4: opt10081 - 주식일봉차트조회
    # ===========================================
    result = tester.test_opt10081_daily_chart(stock_code, max_requests=3)
    test_results.append(result)
    time.sleep(1)

    # ===========================================
    # 테스트 5: opw00001 - 예수금상세현황요청
    # ===========================================
    result = tester.test_opw00001_deposit()
    test_results.append(result)

    # 결과 저장 및 출력
    save_results()
    print_summary()


def save_results():
    """테스트 결과 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON 저장
    json_filename = f"openapi_comprehensive_test_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    log(f"\n✅ 결과 저장: {json_filename}")

    # 리포트 저장
    report_filename = f"openapi_comprehensive_report_{timestamp}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("키움 OpenAPI 종합 테스트 결과\n")
        f.write(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")

        for i, result in enumerate(test_results, 1):
            f.write(f"\n테스트 {i}: {result['tr_name']}\n")
            f.write(f"-" * 80 + "\n")
            f.write(f"TR코드: {result['tr_code']}\n")

            if 'stock_code' in result:
                f.write(f"종목코드: {result['stock_code']}\n")

            if 'interval' in result:
                f.write(f"분봉간격: {result['interval']}분\n")

            status = "✅ 성공" if result['success'] else "❌ 실패"
            f.write(f"결과: {status}\n")

            if 'total_items' in result:
                f.write(f"수집 데이터: {result['total_items']}개\n")

            if result.get('error'):
                f.write(f"오류: {result['error']}\n")

            if 'requests' in result:
                f.write(f"\n연속 조회 상세:\n")
                for req in result['requests']:
                    status = "✅" if req['success'] else "❌"
                    f.write(f"  {status} {req['attempt']}회차: {req['items_received']}개")
                    if req.get('error'):
                        f.write(f" (오류: {req['error']})")
                    f.write("\n")

            if 'sample_data' in result and result['sample_data']:
                f.write(f"\n샘플 데이터 (첫 3개):\n")
                for j, item in enumerate(result['sample_data'][:3], 1):
                    f.write(f"  [{j}] {item}\n")

            if 'data' in result and result['data']:
                f.write(f"\n데이터:\n")
                for key, value in result['data'].items():
                    f.write(f"  {key}: {value}\n")

            f.write("\n")

    log(f"✅ 리포트 저장: {report_filename}")


def print_summary():
    """테스트 결과 요약 출력"""
    print("\n" + "="*80)
    print("테스트 결과 요약")
    print("="*80)

    total_tests = len(test_results)
    success_tests = sum(1 for r in test_results if r['success'])

    print(f"\n총 테스트: {total_tests}개")
    print(f"성공: {success_tests}개")
    print(f"실패: {total_tests - success_tests}개")

    print(f"\n상세 결과:")
    for i, result in enumerate(test_results, 1):
        status = "✅" if result['success'] else "❌"
        name = result['tr_name']

        details = ""
        if 'total_items' in result and result['total_items'] > 0:
            details = f" ({result['total_items']}개)"
        elif result.get('error'):
            details = f" (오류: {result['error']})"

        print(f"  {i}. {status} {name}{details}")

    print("\n" + "="*80)


if __name__ == '__main__':
    try:
        run_all_tests()
    except KeyboardInterrupt:
        log("\n사용자에 의해 중단됨")
        if test_results:
            save_results()
            print_summary()
    except Exception as e:
        log(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if test_results:
            save_results()
            print_summary()
