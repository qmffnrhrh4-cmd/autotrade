"""
OpenAPI Server v2 (32-bit only) - Qt Main Thread TR Processing
===============================================================
Qt 메인 스레드에서 TR 요청을 처리하는 큐 기반 시스템

Architecture:
- Flask: HTTP API (background thread)
- Qt Main Thread: TR 요청 처리 (QTimer로 큐 체크)
- Request Queue: Flask → Qt
- Result Dict: Qt → Flask
"""

import os
import sys
import logging
import threading
import time
import uuid
import queue
from flask import Flask, jsonify, request
from flask_cors import CORS

# Set Qt environment
os.environ['QT_API'] = 'pyqt5'

app = Flask(__name__)
CORS(app)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global OpenAPI context
openapi_context = None
account_list = []
connection_status = "not_started"
qt_app = None

# TR Request Queue System
tr_request_queue = queue.Queue()
tr_result_dict = {}  # request_id -> {'completed': bool, 'result': any, 'error': str}
tr_result_lock = threading.Lock()


def process_tr_in_main_thread(request_id, tr_type, params):
    """메인 스레드에서 TR 요청 처리 (Qt에서 호출)"""
    from PyQt5.QtCore import QEventLoop, QTimer
    from datetime import datetime
    import time

    logger.info(f"[{request_id}] 메인 스레드에서 TR 처리 시작: {tr_type}")

    try:
        if tr_type == 'minute_chart':
            # 분봉 조회 (연속 조회 지원)
            stock_code = params['stock_code']
            interval = params['interval']

            all_items = []
            prev_next_value = 0
            request_count = 0
            max_requests = 10  # 최대 10회 연속 조회 (100개 × 10 = 1000개)
                               # SetInputValue를 매번 호출하면 연속 조회 가능

            logger.info(f"[{request_id}] {stock_code} {interval}분봉 연속 조회 시작 (최대 {max_requests}회)")

            # 이벤트 핸들러는 루프 밖에서 한 번만 정의하고 연결
            received_data = {'result': None, 'completed': False, 'event_loop': None}

            def on_receive(scr_no, rq_name, tr_code, record_name, prev_next):
                if rq_name != 'minute_qt':
                    return

                try:
                    cnt = openapi_context.GetRepeatCnt(tr_code, rq_name)
                    items = []

                    max_extract = min(cnt, 100)

                    for i in range(max_extract):
                        try:
                            item = {
                                '체결시간': openapi_context.GetCommData(tr_code, rq_name, i, "체결시간").strip(),
                                '현재가': openapi_context.GetCommData(tr_code, rq_name, i, "현재가").strip(),
                                '시가': openapi_context.GetCommData(tr_code, rq_name, i, "시가").strip(),
                                '고가': openapi_context.GetCommData(tr_code, rq_name, i, "고가").strip(),
                                '저가': openapi_context.GetCommData(tr_code, rq_name, i, "저가").strip(),
                                '거래량': openapi_context.GetCommData(tr_code, rq_name, i, "거래량").strip(),
                            }
                            items.append(item)
                        except:
                            continue

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
            openapi_context.OnReceiveTrData.connect(on_receive)

            while request_count < max_requests:
                request_count += 1
                logger.info(f"[{request_id}] {request_count}회차 조회 (prev_next={prev_next_value})")

                # 매 시도마다 결과 초기화
                received_data['result'] = None
                received_data['completed'] = False

                # 입력값 설정 (매 요청마다 설정 필요!)
                openapi_context.SetInputValue('종목코드', stock_code)
                openapi_context.SetInputValue('틱범위', str(interval))
                openapi_context.SetInputValue('수정주가구분', '1')

                # TR 요청
                event_loop = QEventLoop()
                received_data['event_loop'] = event_loop
                ret = openapi_context.CommRqData('minute_qt', 'opt10080', prev_next_value, '0101')

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
                    logger.error(f"[{request_id}] {request_count}회차 요청 실패: {error_msg}")

                    # -300 에러는 조회 제한이므로 이미 받은 데이터라도 반환
                    if ret == -300 and len(all_items) > 0:
                        logger.warning(f"[{request_id}] 조회 제한으로 중단, 이미 받은 {len(all_items)}개 데이터는 반환")
                    break
                else:
                    # 타임아웃 설정
                    QTimer.singleShot(10000, event_loop.quit)
                    event_loop.exec_()

                    if received_data['completed'] and received_data['result']:
                        result = received_data['result']

                        if 'error' in result:
                            logger.error(f"[{request_id}] {request_count}회차 오류: {result['error']}")
                            break

                        items = result.get('items', [])
                        all_items.extend(items)
                        logger.info(f"[{request_id}] {request_count}회차: {len(items)}개 수신 (누적: {len(all_items)}개)")

                        # 연속 조회 가능 여부 확인
                        prev_next_value = result.get('prev_next', 0)
                        if prev_next_value != 2:
                            logger.info(f"[{request_id}] 연속 조회 종료 (prev_next={prev_next_value})")
                            break
                    else:
                        logger.error(f"[{request_id}] {request_count}회차 타임아웃")
                        break

                # API 요청 제한 준수 (연속 조회 시 1초 대기)
                # 키움 API는 초당 5회 제한 (0.2초 권장이지만 안전하게 1초)
                if prev_next_value == 2 and request_count < max_requests:
                    logger.info(f"[{request_id}] API 제한 준수를 위해 1초 대기...")
                    time.sleep(1.0)

            # 모든 시도가 끝난 후 이벤트 핸들러 해제
            try:
                openapi_context.OnReceiveTrData.disconnect(on_receive)
            except:
                pass

            # 최종 결과 저장
            result_data = {
                'items': all_items,
                'count': len(all_items)
            }

            with tr_result_lock:
                tr_result_dict[request_id] = {
                    'completed': True,
                    'result': result_data,
                    'error': None
                }

            logger.info(f"[{request_id}] TR 처리 완료: 총 {len(all_items)}개 캔들 수집")

        elif tr_type == 'comprehensive':
            # 종합 데이터 조회 (간소화 버전 - 마스터 정보 + 일봉 차트)
            stock_code = params['stock_code']

            logger.info(f"[{request_id}] {stock_code} 종합 데이터 조회 시작")

            result_data = {
                'stock_code': stock_code,
                'timestamp': datetime.now().isoformat(),
                'data': {}
            }

            # 1. 마스터 정보 (API 호출 없음 - 즉시 가능)
            try:
                result_data['data']['01_master'] = {
                    'stock_name': openapi_context.GetMasterCodeName(stock_code),
                    'current_price': openapi_context.GetMasterLastPrice(stock_code),
                    'listed_stock_cnt': openapi_context.GetMasterListedStockCnt(stock_code),
                }
                logger.info(f"[{request_id}] 마스터 정보 수집 완료")
            except Exception as e:
                logger.error(f"[{request_id}] 마스터 정보 오류: {e}")
                result_data['data']['01_master'] = {'error': str(e)}

            # 2. 일봉 차트 (opt10081)
            try:
                logger.info(f"[{request_id}] 일봉 차트 조회 중...")

                received_data = {'result': None, 'completed': False, 'event_loop': None}

                def on_receive_daily(scr_no, rq_name, tr_code, record_name, prev_next):
                    if rq_name != 'daily_qt':
                        return

                    try:
                        cnt = openapi_context.GetRepeatCnt(tr_code, rq_name)
                        items = []

                        for i in range(min(cnt, 100)):
                            try:
                                item = {
                                    '일자': openapi_context.GetCommData(tr_code, rq_name, i, "일자").strip(),
                                    '현재가': openapi_context.GetCommData(tr_code, rq_name, i, "현재가").strip(),
                                    '시가': openapi_context.GetCommData(tr_code, rq_name, i, "시가").strip(),
                                    '고가': openapi_context.GetCommData(tr_code, rq_name, i, "고가").strip(),
                                    '저가': openapi_context.GetCommData(tr_code, rq_name, i, "저가").strip(),
                                    '거래량': openapi_context.GetCommData(tr_code, rq_name, i, "거래량").strip(),
                                }
                                items.append(item)
                            except:
                                continue

                        received_data['result'] = {'items': items, 'count': cnt}
                    except Exception as e:
                        received_data['result'] = {'error': str(e)}

                    received_data['completed'] = True
                    if received_data['event_loop'] and received_data['event_loop'].isRunning():
                        received_data['event_loop'].quit()

                openapi_context.OnReceiveTrData.connect(on_receive_daily)

                # 입력값 설정
                today = datetime.now().strftime('%Y%m%d')
                openapi_context.SetInputValue('종목코드', stock_code)
                openapi_context.SetInputValue('기준일자', today)
                openapi_context.SetInputValue('수정주가구분', '1')

                # TR 요청
                event_loop = QEventLoop()
                received_data['event_loop'] = event_loop
                ret = openapi_context.CommRqData('daily_qt', 'opt10081', 0, '0101')

                if ret == 0:
                    QTimer.singleShot(10000, event_loop.quit)
                    event_loop.exec_()

                    if received_data['completed'] and received_data['result']:
                        result_data['data']['04_daily_chart'] = received_data['result']
                        logger.info(f"[{request_id}] 일봉 차트 수집 완료: {received_data['result'].get('count', 0)}개")
                    else:
                        result_data['data']['04_daily_chart'] = {'error': 'Timeout'}
                else:
                    result_data['data']['04_daily_chart'] = {'error': f'Request failed: {ret}'}

                try:
                    openapi_context.OnReceiveTrData.disconnect(on_receive_daily)
                except:
                    pass

            except Exception as e:
                logger.error(f"[{request_id}] 일봉 차트 오류: {e}")
                result_data['data']['04_daily_chart'] = {'error': str(e)}

            # 결과 저장
            result_data['success_count'] = sum(1 for v in result_data['data'].values() if 'error' not in v)
            result_data['total_count'] = len(result_data['data'])

            with tr_result_lock:
                tr_result_dict[request_id] = {
                    'completed': True,
                    'result': result_data,
                    'error': None
                }

            logger.info(f"[{request_id}] 종합 데이터 처리 완료: {result_data['success_count']}/{result_data['total_count']}")

        else:
            # Unknown TR type
            with tr_result_lock:
                tr_result_dict[request_id] = {
                    'completed': True,
                    'result': None,
                    'error': f'Unknown TR type: {tr_type}'
                }

    except Exception as e:
        logger.error(f"[{request_id}] TR 처리 오류: {e}")
        import traceback
        traceback.print_exc()

        with tr_result_lock:
            tr_result_dict[request_id] = {
                'completed': True,
                'result': None,
                'error': str(e)
            }


def check_tr_queue():
    """QTimer에서 호출되어 TR 큐를 체크"""
    try:
        while not tr_request_queue.empty():
            try:
                request_id, tr_type, params = tr_request_queue.get_nowait()
                logger.info(f"[{request_id}] 큐에서 TR 요청 가져옴: {tr_type}")

                # 메인 스레드에서 직접 처리
                process_tr_in_main_thread(request_id, tr_type, params)

            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"TR 큐 처리 오류: {e}")
    except Exception as e:
        logger.error(f"check_tr_queue 오류: {e}")


# Flask Routes

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'server_ready': True,
        'openapi_connected': openapi_context is not None,
        'connection_status': connection_status,
        'accounts': account_list
    })


@app.route('/stock/<code>/minute/<int:interval>', methods=['GET'])
def get_minute_data(code, interval):
    """Get minute chart data (메인 스레드 큐 방식)"""
    if not openapi_context:
        return jsonify({'error': 'Not connected'}), 400

    valid_intervals = [1, 3, 5, 10, 15, 30, 60]
    if interval not in valid_intervals:
        return jsonify({'error': f'Invalid interval: {interval}'}), 400

    try:
        # Generate request ID
        request_id = str(uuid.uuid4())

        # 결과 딕셔너리 초기화
        with tr_result_lock:
            tr_result_dict[request_id] = {
                'completed': False,
                'result': None,
                'error': None
            }

        # TR 요청을 큐에 추가
        tr_request_queue.put((request_id, 'minute_chart', {
            'stock_code': code,
            'interval': interval
        }))

        logger.info(f"[{request_id}] {code} {interval}분봉 요청을 큐에 추가")

        # 결과 대기 (polling) - 10회 연속 조회 + 각 1초 대기 고려
        # 최대 10회 × (10초 응답 + 1초 대기) = 110초, 안전하게 120초로 설정
        timeout = 120
        start_time = time.time()

        while time.time() - start_time < timeout:
            with tr_result_lock:
                result_entry = tr_result_dict.get(request_id)

                if result_entry and result_entry['completed']:
                    # 완료됨
                    if result_entry['error']:
                        return jsonify({'error': result_entry['error']}), 500

                    result_data = result_entry['result']

                    # 결과 정리
                    del tr_result_dict[request_id]

                    # 응답 반환
                    from datetime import datetime
                    return jsonify({
                        'stock_code': code,
                        'interval': interval,
                        'timestamp': datetime.now().isoformat(),
                        'data': result_data
                    })

            # 잠시 대기
            time.sleep(0.1)

        # 타임아웃
        with tr_result_lock:
            if request_id in tr_result_dict:
                del tr_result_dict[request_id]

        return jsonify({'error': 'Request timeout'}), 504

    except Exception as e:
        logger.error(f"Minute data error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/accounts', methods=['GET'])
def get_accounts():
    """Get account list"""
    if not openapi_context:
        return jsonify({'error': 'Not connected'}), 400

    return jsonify({
        'accounts': account_list
    })


@app.route('/stock/<code>/comprehensive', methods=['GET'])
def get_comprehensive_data(code):
    """Get comprehensive stock data (20 types) - 메인 스레드 큐 방식"""
    if not openapi_context:
        return jsonify({'error': 'Not connected'}), 400

    try:
        from datetime import datetime

        # Generate request ID
        request_id = str(uuid.uuid4())

        # 결과 딕셔너리 초기화
        with tr_result_lock:
            tr_result_dict[request_id] = {
                'completed': False,
                'result': None,
                'error': None
            }

        # TR 요청을 큐에 추가
        tr_request_queue.put((request_id, 'comprehensive', {
            'stock_code': code
        }))

        logger.info(f"[{request_id}] {code} 종합 데이터 요청을 큐에 추가")

        # 결과 대기 (polling) - 종합 데이터는 여러 TR을 조회하므로 120초로 설정
        timeout = 120
        start_time = time.time()

        while time.time() - start_time < timeout:
            with tr_result_lock:
                result_entry = tr_result_dict.get(request_id)

                if result_entry and result_entry['completed']:
                    # 완료됨
                    if result_entry['error']:
                        return jsonify({'error': result_entry['error']}), 500

                    result_data = result_entry['result']

                    # 결과 정리
                    del tr_result_dict[request_id]

                    # 응답 반환
                    return jsonify(result_data)

            # 잠시 대기
            time.sleep(0.1)

        # 타임아웃
        with tr_result_lock:
            if request_id in tr_result_dict:
                del tr_result_dict[request_id]

        return jsonify({'error': 'Request timeout'}), 504

    except Exception as e:
        logger.error(f"Comprehensive data error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def run_flask():
    """Run Flask server"""
    logger.info("🚀 Starting Flask HTTP server on http://localhost:5001")
    app.run(
        host='127.0.0.1',
        port=5001,
        debug=False,
        use_reloader=False,
        threaded=True
    )


def main():
    """Main entry point"""
    global openapi_context, account_list, connection_status, qt_app

    logger.info("=" * 60)
    logger.info("OpenAPI Server v2 (Qt Main Thread Processing)")
    logger.info("=" * 60)

    # Check Python architecture
    import struct
    bits = struct.calcsize('P') * 8
    logger.info(f"Python: {sys.version}")
    logger.info(f"Architecture: {bits}-bit")

    if bits != 32:
        logger.error("❌ This server must run in 32-bit Python!")
        sys.exit(1)

    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask server started")

    time.sleep(2)

    # Initialize OpenAPI in main thread
    logger.info("\n🔧 Initializing OpenAPI...")

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QTimer
    from kiwoom import Kiwoom
    import kiwoom

    kiwoom.config.MUTE = True

    qt_app = QApplication.instance()
    if qt_app is None:
        qt_app = QApplication(sys.argv)

    logger.info("✅ Qt Application created")

    openapi_context = Kiwoom()
    qt_app.processEvents()

    logger.info("✅ Kiwoom API instance created")

    connection_status = "connecting"

    # Login event handler
    def on_login(err_code):
        global connection_status, account_list

        if err_code == 0:
            connection_status = "connected"
            logger.info("\n✅ 로그인 성공!")

            try:
                account_str = openapi_context.GetLoginInfo("ACCNO")
                if account_str:
                    account_list = [acc.strip() for acc in account_str.split(';') if acc.strip()]
                    logger.info(f"   계좌 목록: {account_list}")
            except Exception as e:
                logger.warning(f"   계좌 목록 조회 실패: {e}")

            logger.info("\n✅ Server is ready!\n")
        else:
            connection_status = "failed"
            logger.error(f"\n❌ 로그인 실패: {err_code}\n")

    openapi_context.OnEventConnect.connect(on_login)
    openapi_context.CommConnect()

    # QTimer for TR queue processing (메인 스레드에서 실행)
    queue_timer = QTimer()
    queue_timer.timeout.connect(check_tr_queue)
    queue_timer.start(100)  # 100ms마다 큐 체크

    logger.info("✅ TR 큐 처리 타이머 시작 (100ms)")

    # Run Qt event loop
    logger.info("🔄 Starting Qt event loop...\n")

    try:
        sys.exit(qt_app.exec_())
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down...")
        sys.exit(0)


if __name__ == '__main__':
    main()
