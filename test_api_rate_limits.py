"""
키움 OpenAPI 연속 조회 제한 테스트
다양한 조건으로 테스트하여 정확한 API 제한 사항을 파악
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

def test_continuous_inquiry(api, stock_code, interval, delay_seconds, max_attempts, test_name):
    """
    연속 조회 테스트

    Args:
        api: Kiwoom API 인스턴스
        stock_code: 종목코드
        interval: 분봉 간격
        delay_seconds: 요청 간 대기 시간 (초)
        max_attempts: 최대 시도 횟수
        test_name: 테스트 이름

    Returns:
        dict: 테스트 결과
    """
    log(f"\n{'='*80}")
    log(f"테스트: {test_name}")
    log(f"조건: 대기시간={delay_seconds}초, 최대시도={max_attempts}회")
    log(f"{'='*80}")

    result = {
        'test_name': test_name,
        'delay_seconds': delay_seconds,
        'max_attempts': max_attempts,
        'start_time': datetime.now().isoformat(),
        'attempts': [],
        'success_count': 0,
        'total_items': 0,
        'errors': [],
        'conclusion': ''
    }

    all_items = []
    prev_next_value = 0
    attempt_count = 0

    # 이벤트 핸들러는 루프 밖에서 한 번만 정의하고 연결
    received_data = {'result': None, 'completed': False, 'return_code': None, 'event_loop': None}

    def on_receive(scr_no, rq_name, tr_code, record_name, prev_next):
        if rq_name != 'test_minute':
            return

        try:
            cnt = api.GetRepeatCnt(tr_code, rq_name)
            items = []

            for i in range(min(cnt, 100)):
                item = {
                    '체결시간': api.GetCommData(tr_code, rq_name, i, "체결시간").strip(),
                    '현재가': api.GetCommData(tr_code, rq_name, i, "현재가").strip(),
                }
                items.append(item)

            received_data['result'] = {
                'items': items,
                'count': cnt,
                'prev_next': int(prev_next) if prev_next else 0
            }
        except Exception as e:
            received_data['result'] = {'error': str(e)}

        received_data['completed'] = True
        if received_data['event_loop'] and received_data['event_loop'].isRunning():
            received_data['event_loop'].quit()

    # 이벤트 핸들러를 한 번만 연결 (연속 조회의 핵심!)
    api.OnReceiveTrData.connect(on_receive)

    while attempt_count < max_attempts:
        attempt_count += 1
        attempt_start = time.time()
        log(f"\n--- {attempt_count}회차 시도 (prev_next={prev_next_value}) ---")

        # 매 시도마다 결과 초기화
        received_data['result'] = None
        received_data['completed'] = False

        # 입력값 설정 (매 요청마다 설정 필요!)
        api.SetInputValue('종목코드', stock_code)
        api.SetInputValue('틱범위', str(interval))
        api.SetInputValue('수정주가구분', '1')

        # TR 요청
        event_loop = QEventLoop()
        received_data['event_loop'] = event_loop
        ret = api.CommRqData('test_minute', 'opt10080', prev_next_value, '0101')

        attempt_result = {
            'attempt': attempt_count,
            'return_code': ret,
            'prev_next': prev_next_value,
            'elapsed_time': 0,
            'items_received': 0,
            'success': False,
            'error_message': None
        }

        if ret != 0:
            error_messages = {
                -100: "사용자정보교환 실패",
                -101: "서버접속 실패",
                -102: "버전처리 실패",
                -200: "시세과부하",
                -201: "조회전문작성 실패",
                -300: "조회제한 초과 (TR 요청 제한)",
            }
            error_msg = error_messages.get(ret, f"알 수 없는 오류 ({ret})")
            log(f"❌ 요청 실패: {error_msg}")

            attempt_result['error_message'] = error_msg
            result['errors'].append(f"Attempt {attempt_count}: {error_msg}")

            result['attempts'].append(attempt_result)
            break
        else:
            # 타임아웃 설정
            QTimer.singleShot(10000, event_loop.quit)
            event_loop.exec_()

            if received_data['completed'] and received_data['result']:
                res = received_data['result']

                if 'error' in res:
                    log(f"❌ 데이터 추출 오류: {res['error']}")
                    attempt_result['error_message'] = res['error']
                    result['errors'].append(f"Attempt {attempt_count}: {res['error']}")
                else:
                    items = res.get('items', [])
                    all_items.extend(items)
                    prev_next_value = res.get('prev_next', 0)

                    attempt_result['items_received'] = len(items)
                    attempt_result['success'] = True
                    result['success_count'] += 1

                    log(f"✅ 성공: {len(items)}개 수신 (누적: {len(all_items)}개)")
                    log(f"   Next prev_next: {prev_next_value}")

                    if prev_next_value != 2:
                        log(f"ℹ️  연속 조회 종료 (prev_next={prev_next_value})")
                        attempt_result['elapsed_time'] = time.time() - attempt_start
                        result['attempts'].append(attempt_result)
                        break
            else:
                log(f"❌ 타임아웃")
                attempt_result['error_message'] = 'Timeout'
                result['errors'].append(f"Attempt {attempt_count}: Timeout")

        attempt_result['elapsed_time'] = time.time() - attempt_start
        result['attempts'].append(attempt_result)

        # 다음 요청 전 대기
        if prev_next_value == 2 and attempt_count < max_attempts:
            log(f"⏳ {delay_seconds}초 대기 중...")
            time.sleep(delay_seconds)

    # 모든 시도가 끝난 후 이벤트 핸들러 해제
    try:
        api.OnReceiveTrData.disconnect(on_receive)
    except:
        pass

    result['total_items'] = len(all_items)
    result['end_time'] = datetime.now().isoformat()

    # 결론 도출
    if result['success_count'] == 0:
        result['conclusion'] = "❌ 첫 요청도 실패"
    elif result['success_count'] == 1:
        result['conclusion'] = f"⚠️  1회만 성공 ({result['total_items']}개) - 연속 조회 불가"
    elif result['success_count'] == max_attempts:
        result['conclusion'] = f"✅ 모든 시도 성공 ({result['total_items']}개) - 최적 조건!"
    else:
        result['conclusion'] = f"△ {result['success_count']}/{max_attempts} 성공 ({result['total_items']}개)"

    log(f"\n{'='*80}")
    log(f"결과: {result['conclusion']}")
    log(f"{'='*80}\n")

    return result


def run_all_tests():
    """모든 테스트 실행"""
    log("키움 OpenAPI 연속 조회 제한 테스트 시작")
    log(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # QApplication 초기화
    app = QApplication(sys.argv)

    # Kiwoom API 초기화
    api = Kiwoom()
    api.CommConnect()

    # 로그인 대기
    log("로그인 대기 중...")
    loop = QEventLoop()
    api.OnEventConnect.connect(lambda err_code: loop.quit())
    loop.exec_()

    log("✅ 로그인 완료!\n")

    # 테스트할 종목
    stock_code = '005930'  # 삼성전자
    interval = 1  # 1분봉

    # ==========================================
    # 테스트 1: 다양한 대기 시간 테스트 (2회 시도)
    # ==========================================
    for delay in [1, 3, 5, 10, 15, 20, 30]:
        result = test_continuous_inquiry(
            api, stock_code, interval,
            delay_seconds=delay,
            max_attempts=2,
            test_name=f"대기시간 테스트 ({delay}초)"
        )
        test_results.append(result)

        # 테스트 간 충분한 간격 (30초)
        if delay < 30:
            log(f"다음 테스트 전 30초 대기...")
            time.sleep(30)

    # ==========================================
    # 테스트 2: 성공한 대기 시간으로 더 많은 시도
    # ==========================================
    successful_delays = [r['delay_seconds'] for r in test_results if r['success_count'] >= 2]

    if successful_delays:
        best_delay = min(successful_delays)  # 가장 짧은 성공 대기시간
        log(f"\n✅ {best_delay}초가 2회 연속 성공! 더 많은 시도 테스트...")
        time.sleep(30)

        for attempts in [3, 5, 7, 10]:
            result = test_continuous_inquiry(
                api, stock_code, interval,
                delay_seconds=best_delay,
                max_attempts=attempts,
                test_name=f"연속 {attempts}회 시도 ({best_delay}초 대기)"
            )
            test_results.append(result)

            if result['success_count'] < attempts:
                log(f"⚠️  {attempts}회 시도에서 실패 - 이전 횟수가 최대값")
                break

            time.sleep(30)

    # ==========================================
    # 테스트 3: 점진적 대기 시간 증가 테스트
    # ==========================================
    log("\n점진적 대기 시간 증가 테스트...")
    time.sleep(30)

    result = test_progressive_delay(api, stock_code, interval)
    test_results.append(result)

    # 결과 저장
    save_results()

    log("\n\n" + "="*80)
    log("모든 테스트 완료!")
    log("="*80)
    print_summary()


def test_progressive_delay(api, stock_code, interval):
    """점진적으로 대기 시간을 늘려가며 테스트"""
    log(f"\n{'='*80}")
    log(f"테스트: 점진적 대기 시간 증가")
    log(f"조건: 1회차 후 5초 → 2회차 후 10초 → 3회차 후 15초 ...")
    log(f"{'='*80}")

    result = {
        'test_name': '점진적 대기 시간 증가',
        'delay_seconds': 'progressive',
        'max_attempts': 5,
        'start_time': datetime.now().isoformat(),
        'attempts': [],
        'success_count': 0,
        'total_items': 0,
        'errors': [],
        'conclusion': ''
    }

    delays = [5, 10, 15, 20, 30]
    all_items = []
    prev_next_value = 0

    # 이벤트 핸들러는 루프 밖에서 한 번만 정의하고 연결
    received_data = {'result': None, 'completed': False, 'event_loop': None}

    def on_receive(scr_no, rq_name, tr_code, record_name, prev_next):
        if rq_name != 'test_prog':
            return

        try:
            cnt = api.GetRepeatCnt(tr_code, rq_name)
            items = []

            for i in range(min(cnt, 100)):
                item = {
                    '체결시간': api.GetCommData(tr_code, rq_name, i, "체결시간").strip(),
                    '현재가': api.GetCommData(tr_code, rq_name, i, "현재가").strip(),
                }
                items.append(item)

            received_data['result'] = {
                'items': items,
                'count': cnt,
                'prev_next': int(prev_next) if prev_next else 0
            }
        except Exception as e:
            received_data['result'] = {'error': str(e)}

        received_data['completed'] = True
        if received_data['event_loop'] and received_data['event_loop'].isRunning():
            received_data['event_loop'].quit()

    # 이벤트 핸들러를 한 번만 연결
    api.OnReceiveTrData.connect(on_receive)

    for attempt_count in range(1, 6):
        log(f"\n--- {attempt_count}회차 시도 (prev_next={prev_next_value}) ---")

        # 매 시도마다 결과 초기화
        received_data['result'] = None
        received_data['completed'] = False

        # 입력값 설정 (매 요청마다 설정 필요!)
        api.SetInputValue('종목코드', stock_code)
        api.SetInputValue('틱범위', str(interval))
        api.SetInputValue('수정주가구분', '1')

        event_loop = QEventLoop()
        received_data['event_loop'] = event_loop
        ret = api.CommRqData('test_prog', 'opt10080', prev_next_value, '0101')

        attempt_result = {
            'attempt': attempt_count,
            'return_code': ret,
            'items_received': 0,
            'success': False,
            'delay_after': delays[attempt_count - 1] if attempt_count < len(delays) else 30
        }

        if ret != 0:
            log(f"❌ 요청 실패: {ret}")
            result['errors'].append(f"Attempt {attempt_count}: Error {ret}")
            result['attempts'].append(attempt_result)
            break
        else:
            QTimer.singleShot(10000, event_loop.quit)
            event_loop.exec_()

            if received_data['completed'] and received_data['result']:
                res = received_data['result']

                if 'error' not in res:
                    items = res.get('items', [])
                    all_items.extend(items)
                    prev_next_value = res.get('prev_next', 0)

                    attempt_result['items_received'] = len(items)
                    attempt_result['success'] = True
                    result['success_count'] += 1

                    log(f"✅ 성공: {len(items)}개 수신 (누적: {len(all_items)}개)")

                    if prev_next_value != 2:
                        result['attempts'].append(attempt_result)
                        break

        result['attempts'].append(attempt_result)

        if prev_next_value == 2 and attempt_count < 5:
            delay = delays[attempt_count - 1]
            log(f"⏳ {delay}초 대기 중...")
            time.sleep(delay)

    # 모든 시도가 끝난 후 이벤트 핸들러 해제
    try:
        api.OnReceiveTrData.disconnect(on_receive)
    except:
        pass

    result['total_items'] = len(all_items)
    result['end_time'] = datetime.now().isoformat()
    result['conclusion'] = f"{result['success_count']}/5 성공 ({result['total_items']}개)"

    log(f"\n결과: {result['conclusion']}\n")

    return result


def save_results():
    """테스트 결과 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON 저장
    json_filename = f"api_rate_limit_test_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    log(f"\n✅ 결과 저장: {json_filename}")

    # 요약 리포트 저장
    report_filename = f"api_rate_limit_report_{timestamp}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("키움 OpenAPI 연속 조회 제한 테스트 결과 요약\n")
        f.write(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")

        for i, result in enumerate(test_results, 1):
            f.write(f"\n테스트 {i}: {result['test_name']}\n")
            f.write(f"-" * 80 + "\n")
            f.write(f"대기 시간: {result['delay_seconds']}초\n")
            f.write(f"최대 시도: {result['max_attempts']}회\n")
            f.write(f"성공 횟수: {result['success_count']}/{result['max_attempts']}\n")
            f.write(f"총 데이터: {result['total_items']}개\n")
            f.write(f"결론: {result['conclusion']}\n")

            if result['errors']:
                f.write(f"\n오류:\n")
                for error in result['errors']:
                    f.write(f"  - {error}\n")

            f.write(f"\n시도별 상세:\n")
            for attempt in result['attempts']:
                status = "✅" if attempt['success'] else "❌"
                f.write(f"  {status} {attempt['attempt']}회차: ")
                f.write(f"코드={attempt['return_code']}, ")
                f.write(f"수신={attempt['items_received']}개, ")
                f.write(f"소요={attempt.get('elapsed_time', 0):.2f}초\n")
                if attempt.get('error_message'):
                    f.write(f"     오류: {attempt['error_message']}\n")

            f.write("\n")

    log(f"✅ 리포트 저장: {report_filename}")


def print_summary():
    """테스트 결과 요약 출력"""
    print("\n" + "="*80)
    print("테스트 결과 요약")
    print("="*80)

    # 2회 연속 성공한 최소 대기 시간
    successful_2x = [r for r in test_results if r['success_count'] >= 2 and isinstance(r['delay_seconds'], (int, float))]
    if successful_2x:
        min_delay_2x = min(r['delay_seconds'] for r in successful_2x)
        print(f"\n✅ 2회 연속 성공 최소 대기 시간: {min_delay_2x}초")
    else:
        print(f"\n❌ 2회 연속 성공한 조건 없음")

    # 최대 성공 횟수
    max_success = max((r['success_count'] for r in test_results), default=0)
    max_items = max((r['total_items'] for r in test_results), default=0)

    print(f"\n📊 통계:")
    print(f"  - 최대 연속 성공: {max_success}회")
    print(f"  - 최대 수집 데이터: {max_items}개")

    # 권장사항
    print(f"\n💡 권장사항:")
    if successful_2x:
        best = min(successful_2x, key=lambda r: r['delay_seconds'])
        print(f"  - 대기 시간: {best['delay_seconds']}초 이상")
        print(f"  - 최대 시도: {best['success_count']}회 이하")
        print(f"  - 예상 수집량: {best['total_items']}개")
    else:
        print(f"  - 연속 조회가 현재 시점에서 불가능할 수 있습니다")
        print(f"  - 장 마감 후 시간대에 다시 테스트 권장")
        print(f"  - 또는 단일 조회(100개)만 사용 권장")

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
