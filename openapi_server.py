"""
OpenAPI Server (32-bit only)
=============================
This server runs in 32-bit Python environment and provides OpenAPI functionality via HTTP.

Main application (64-bit) communicates with this server via HTTP requests.

Architecture:
- 32-bit Python 3.9/3.10 (Anaconda kiwoom32)
- breadum/kiwoom for OpenAPI connection
- Flask for HTTP API
- Port: 5001

Usage:
    conda activate kiwoom32
    python openapi_server.py
"""

import os
import sys
import logging
import threading
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Set Qt environment before importing koapy
os.environ['QT_API'] = 'pyqt5'

# Import config constants
sys.path.insert(0, os.path.dirname(__file__))
try:
    from config.constants import OPENAPI_HOST, PORTS
except ImportError:
    # Fallback to hardcoded values if config not available
    OPENAPI_HOST = '127.0.0.1'
    PORTS = {'openapi': 5001}

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
connection_status = "not_started"  # not_started, connecting, connected, failed
qt_app = None  # Qt Application must persist

# TR 요청을 메인 스레드에서 실행하기 위한 헬퍼
import threading
tr_request_lock = threading.Lock()
tr_request_result = {}  # request_id -> {'completed': bool, 'result': any}


def initialize_openapi_in_main_thread():
    """Initialize OpenAPI in MAIN thread (Qt requirement)"""
    global openapi_context, account_list, connection_status, qt_app

    try:
        # Qt 애플리케이션을 먼저 생성
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer

        logger.info("🔧 Initializing Qt Application...")

        # QApplication이 이미 있는지 확인
        qt_app = QApplication.instance()
        if qt_app is None:
            qt_app = QApplication(sys.argv)
            logger.info("✅ Qt Application created")
        else:
            logger.info("✅ Qt Application already exists")

        # breadum/kiwoom 라이브러리 사용
        from kiwoom import Kiwoom
        import kiwoom

        # 경고 메시지 숨기기
        kiwoom.config.MUTE = True

        logger.info("🔧 Initializing Kiwoom OpenAPI connection...")
        logger.info("")
        logger.info("=" * 60)
        logger.info("⚠️  로그인 창 안내")
        logger.info("=" * 60)
        logger.info("1. 키움증권 로그인 창이 나타납니다")
        logger.info("2. 창이 안 보이면 '작업 표시줄'을 확인하세요")
        logger.info("3. 로그인 정보를 입력하고 '로그인' 버튼을 클릭하세요")
        logger.info("4. 인증서 비밀번호를 입력하세요")
        logger.info("=" * 60)
        logger.info("")

        connection_status = "connecting"

        # Kiwoom API 생성
        logger.info("🔧 Creating Kiwoom API instance...")
        openapi_context = Kiwoom()
        logger.info("✅ Kiwoom API instance created")

        # Qt 이벤트 처리하여 객체가 제대로 초기화되도록 함
        logger.info("🔧 Processing Qt events...")
        qt_app.processEvents()

        return True

    except Exception as e:
        connection_status = "failed"
        logger.error("")
        logger.error("=" * 60)
        logger.error(f"❌ OpenAPI initialization error: {e}")
        logger.error("=" * 60)
        import traceback
        traceback.print_exc()
        return False


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


@app.route('/connect', methods=['POST'])
def connect():
    """Connect to OpenAPI"""
    global connection_status

    # If already connecting or connected, return status
    if connection_status in ['connecting', 'connected']:
        return jsonify({
            'status': connection_status,
            'success': connection_status == 'connected',
            'accounts': account_list
        })

    # OpenAPI must be initialized from main thread (Qt requirement)
    # So we just return a message telling the client to wait
    return jsonify({
        'status': 'not_started',
        'success': False,
        'message': 'OpenAPI will be initialized automatically on server startup. Please wait and poll /health.',
        'accounts': []
    })


@app.route('/accounts', methods=['GET'])
def get_accounts():
    """Get account list"""
    if not openapi_context:
        return jsonify({'error': 'Not connected'}), 400

    return jsonify({
        'accounts': account_list
    })


@app.route('/balance/<account_no>', methods=['GET'])
def get_balance(account_no):
    """Get account balance"""
    if not openapi_context:
        return jsonify({'error': 'Not connected'}), 400

    try:
        # Call OpenAPI method for balance
        # This is a placeholder - implement actual koapy calls
        balance_data = {
            'account_no': account_no,
            'total_balance': 0,
            'available_balance': 0,
            'positions': []
        }
        return jsonify(balance_data)
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/order', methods=['POST'])
def place_order():
    """Place order via OpenAPI"""
    if not openapi_context:
        return jsonify({'error': 'Not connected'}), 400

    data = request.json
    account_no = data.get('account_no')
    code = data.get('code')
    qty = data.get('qty')
    price = data.get('price', 0)
    order_type = data.get('order_type', 'market')  # market or limit
    side = data.get('side')  # buy or sell

    try:
        # Implement actual OpenAPI order placement
        # This is a placeholder
        result = {
            'success': True,
            'order_id': 'ORDER_123',
            'message': 'Order placed successfully'
        }
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/realtime/price/<code>', methods=['GET'])
def get_realtime_price(code):
    """Get real-time price via OpenAPI"""
    if not openapi_context:
        return jsonify({'error': 'Not connected'}), 400

    try:
        # Implement real-time price query
        # This is a placeholder
        price_data = {
            'code': code,
            'current_price': 0,
            'volume': 0,
            'timestamp': None
        }
        return jsonify(price_data)
    except Exception as e:
        logger.error(f"Error getting price: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/stock/<code>/minute/<int:interval>', methods=['GET'])
def get_minute_data(code, interval):
    """Get minute chart data (past data available)

    Supported intervals: 1, 3, 5, 10, 15, 30, 60 minutes
    """
    if not openapi_context:
        return jsonify({'error': 'Not connected'}), 400

    # 유효한 interval 체크
    valid_intervals = [1, 3, 5, 10, 15, 30, 60]
    if interval not in valid_intervals:
        return jsonify({'error': f'Invalid interval: {interval}. Valid: {valid_intervals}'}), 400

    try:
        from PyQt5.QtCore import QEventLoop, QTimer
        from datetime import datetime

        logger.info(f"📊 {code} {interval}분봉 조회 요청")

        # TR 요청 함수 (연속 조회 지원)
        def request_tr_sync(rqname, trcode, inputs, timeout=10000, prev_next=0, unique_id=None):
            """TR 동기 요청 (prev_next: 0=조회, 2=연속조회)"""
            received_data = {'result': None, 'completed': False}

            def on_receive(scr_no, rq_name, tr_code, record_name, prev_next_received):
                # unique_id를 사용하여 정확히 일치하는지 확인
                if unique_id and not rq_name.startswith(rqname):
                    return
                elif not unique_id and rq_name != rqname:
                    return

                logger.info(f"  📥 OnReceiveTrData - rqname: '{rq_name}', prev_next: {prev_next_received}")

                try:
                    # ✅ breadum/kiwoom은 rqname 사용 (test_stock_comprehensive_20.py 참고)
                    cnt = openapi_context.GetRepeatCnt(tr_code, rq_name)
                    items = []

                    logger.info(f"  📊 GetRepeatCnt: {cnt}개")

                    # 복수 데이터 추출 (제한: 100개 - GetCommData 버퍼 이슈 방지)
                    max_extract = min(cnt, 100)
                    logger.info(f"  📦 추출 제한: {max_extract}개 (전체 {cnt}개 중)")

                    for i in range(max_extract):
                        # opt10080 분봉차트 기본 출력 필드만 사용
                        try:
                            # ✅ breadum/kiwoom: GetCommData(trcode, rqname, index, field) - 4개 파라미터
                            item = {
                                '체결시간': openapi_context.GetCommData(tr_code, rq_name, i, "체결시간").strip(),
                                '현재가': openapi_context.GetCommData(tr_code, rq_name, i, "현재가").strip(),
                                '시가': openapi_context.GetCommData(tr_code, rq_name, i, "시가").strip(),
                                '고가': openapi_context.GetCommData(tr_code, rq_name, i, "고가").strip(),
                                '저가': openapi_context.GetCommData(tr_code, rq_name, i, "저가").strip(),
                                '거래량': openapi_context.GetCommData(tr_code, rq_name, i, "거래량").strip(),
                            }

                            items.append(item)

                            # 첫 5개와 마지막 2개만 샘플 로그 출력 (추가 후)
                            if i < 5 or i >= cnt - 2:
                                time_val = item.get('체결시간', '')
                                price_val = item.get('현재가', '')
                                vol_val = item.get('거래량', '')
                                logger.info(f"    [{i}] 시간:{time_val} 가격:{price_val} 량:{vol_val}")
                        except Exception as e:
                            logger.error(f"    [{i}] 데이터 추출 실패: {e}")
                            if i < 3:  # 처음 3개만 에러 상세 로그
                                import traceback
                                logger.error(traceback.format_exc())
                            continue

                    # prev_next 값도 함께 반환
                    received_data['result'] = {
                        'items': items,
                        'count': cnt,
                        'total_received': len(items),
                        'prev_next': int(prev_next_received) if prev_next_received else 0
                    }
                    logger.info(f"  ✅ 최종: {len(items)}개 캔들 추출 완료 (prev_next={prev_next_received})")
                except Exception as e:
                    logger.error(f"  ❌ 데이터 추출 오류: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    received_data['result'] = {'error': str(e)}

                received_data['completed'] = True
                if event_loop.isRunning():
                    event_loop.quit()

            # 이벤트 핸들러 연결
            openapi_context.OnReceiveTrData.connect(on_receive)

            # 입력값 설정 (⚠️ 연속 조회 시에는 설정하면 안 됨!)
            if prev_next == 0:
                # 최초 조회만 입력값 설정
                for key, value in inputs.items():
                    openapi_context.SetInputValue(key, value)
                logger.info(f"  ✅ SetInputValue 설정 완료")
            else:
                # prev_next=2일 때는 SetInputValue 호출 안 함 (내부 상태 유지)
                logger.info(f"  ⏭️  SetInputValue 생략 (연속 조회)")

            # TR 요청 (prev_next: 0=조회, 2=연속)
            event_loop = QEventLoop()
            ret = openapi_context.CommRqData(rqname, trcode, prev_next, "0101")

            if ret != 0:
                return {'error': f'Request failed: {ret}'}

            # 타임아웃 설정
            QTimer.singleShot(timeout, event_loop.quit)
            event_loop.exec_()

            # 이벤트 핸들러 연결 해제
            try:
                openapi_context.OnReceiveTrData.disconnect(on_receive)
            except:
                pass

            return received_data['result'] if received_data['completed'] else {'error': 'Timeout'}

        # opt10080: 분봉 조회 (연속 조회 지원)
        all_items = []
        prev_next = 0
        request_count = 0
        max_requests = 5  # 최대 5회 연속 조회 (한 번에 100개씩 = 최대 500개)

        # ✅ 동시 요청 구분을 위한 unique ID 생성
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        rqname_unique = f'minute_{unique_id}'

        logger.info(f"  🔑 Unique request name: {rqname_unique}")

        while request_count < max_requests:
            request_count += 1
            logger.info(f"  🔄 분봉 조회 {request_count}회차 (prev_next={prev_next})")

            minute_data = request_tr_sync(
                rqname_unique,
                'opt10080',
                {
                    '종목코드': code,
                    '틱범위': str(interval),
                    '수정주가구분': '1'
                },
                prev_next=prev_next,
                unique_id=unique_id
            )

            if minute_data and 'items' in minute_data:
                items = minute_data['items']
                all_items.extend(items)
                logger.info(f"  ✅ {request_count}회차: {len(items)}개 추가 (누적: {len(all_items)}개)")

                # prev_next 확인
                next_flag = minute_data.get('prev_next', 0)
                if next_flag == 0:
                    logger.info(f"  🏁 연속 조회 완료 (prev_next=0)")
                    break
                else:
                    prev_next = 2  # 다음 조회는 연속조회 플래그
                    time.sleep(0.25)  # API 호출 제한 (초당 5회)
            else:
                logger.warning(f"  ⚠️ {request_count}회차 조회 실패")
                break

        result = {
            'stock_code': code,
            'interval': interval,
            'timestamp': datetime.now().isoformat(),
            'data': {'items': all_items, 'count': len(all_items), 'total_received': len(all_items)}
        }

        logger.info(f"✅ {code} {interval}분봉 최종 {len(all_items)}개 조회 완료")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Minute data error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/stock/<code>/comprehensive', methods=['GET'])
def get_comprehensive_data(code):
    """Get comprehensive stock data (20 types)"""
    if not openapi_context:
        return jsonify({'error': 'Not connected'}), 400

    try:
        from PyQt5.QtCore import QEventLoop, QTimer
        from datetime import datetime, timedelta

        # 데이터 수집 결과
        result_data = {
            'stock_code': code,
            'timestamp': datetime.now().isoformat(),
            'data': {}
        }

        # 1. 마스터 정보
        try:
            result_data['data']['01_master'] = {
                'stock_name': openapi_context.GetMasterCodeName(code),
                'current_price': openapi_context.GetMasterLastPrice(code),
                'listed_stock_cnt': openapi_context.GetMasterListedStockCnt(code),
            }
        except Exception as e:
            logger.error(f"Master info error: {e}")
            result_data['data']['01_master'] = {'error': str(e)}

        # TR 요청 함수
        def request_tr_sync(rqname, trcode, inputs, timeout=5000):
            """TR 동기 요청"""
            received_data = {'result': None, 'completed': False}

            def on_receive(scr_no, rq_name, tr_code, record_name, prev_next):
                if rq_name != rqname:
                    return

                try:
                    cnt = openapi_context.GetRepeatCnt(tr_code, rq_name)
                    data = {}

                    if cnt == 0:
                        # 단일 데이터
                        data = extract_single_data(tr_code, rq_name)
                    else:
                        # 복수 데이터
                        data = extract_multi_data(tr_code, rq_name, cnt)

                    received_data['result'] = data
                except Exception as e:
                    received_data['result'] = {'error': str(e)}

                received_data['completed'] = True
                if event_loop.isRunning():
                    event_loop.quit()

            # 이벤트 핸들러 연결
            openapi_context.OnReceiveTrData.connect(on_receive)

            # 입력값 설정
            for key, value in inputs.items():
                openapi_context.SetInputValue(key, value)

            # TR 요청
            event_loop = QEventLoop()
            ret = openapi_context.CommRqData(rqname, trcode, 0, "0101")

            if ret != 0:
                return {'error': f'Request failed: {ret}'}

            # 타임아웃 설정
            QTimer.singleShot(timeout, event_loop.quit)
            event_loop.exec_()

            # 이벤트 핸들러 연결 해제
            try:
                openapi_context.OnReceiveTrData.disconnect(on_receive)
            except:
                pass

            return received_data['result'] if received_data['completed'] else {'error': 'Timeout'}

        def extract_single_data(trcode, rqname):
            """단일 데이터 추출"""
            data = {}
            fields = ['종목명', '현재가', '등락률', '거래량', '시가', '고가', '저가', '전일대비', '시가총액']

            for field in fields:
                try:
                    # ✅ breadum/kiwoom: GetCommData(trcode, rqname, index, field) - 4개 파라미터
                    value = openapi_context.GetCommData(trcode, rqname, 0, field).strip()
                    if value:
                        data[field] = value
                except:
                    pass

            return data

        def extract_multi_data(trcode, rqname, cnt):
            """복수 데이터 추출"""
            items = []
            for i in range(min(cnt, 20)):
                item = {}
                fields = ['일자', '체결시간', '현재가', '거래량', '시가', '고가', '저가', '등락률']

                for field in fields:
                    try:
                        # ✅ breadum/kiwoom: GetCommData(trcode, rqname, index, field) - 4개 파라미터
                        value = openapi_context.GetCommData(trcode, rqname, i, field).strip()
                        if value:
                            item[field] = value
                    except:
                        pass

                if item:
                    items.append(item)

            return {'items': items, 'count': cnt}

        # 날짜 계산
        today = datetime.now()
        days_since_friday = (today.weekday() - 4) % 7
        if days_since_friday == 0 and today.hour < 16:
            days_since_friday = 7
        last_friday = today - timedelta(days=days_since_friday)
        target_date = last_friday.strftime('%Y%m%d')

        # TR 목록
        tr_list = [
            {'name': '02_basic', 'trcode': 'opt10001', 'inputs': {'종목코드': code}},
            {'name': '03_quote', 'trcode': 'opt10004', 'inputs': {'종목코드': code}},
            {'name': '04_daily_chart', 'trcode': 'opt10081', 'inputs': {'종목코드': code, '기준일자': target_date, '수정주가구분': '1'}},
            {'name': '05_minute_chart', 'trcode': 'opt10080', 'inputs': {'종목코드': code, '틱범위': '1', '수정주가구분': '1'}},
            {'name': '06_volume', 'trcode': 'opt10002', 'inputs': {'종목코드': code}},
            {'name': '07_conclusion', 'trcode': 'opt10003', 'inputs': {'종목코드': code}},
            {'name': '08_market_info', 'trcode': 'opt10007', 'inputs': {'종목코드': code}},
            {'name': '09_change_rate', 'trcode': 'opt10005', 'inputs': {'종목코드': code, '기준일자': target_date}},
            {'name': '10_investor_trend', 'trcode': 'opt10059', 'inputs': {'일자': target_date, '종목코드': code, '금액수량구분': '1', '매매구분': '0', '단위구분': '1'}},
            {'name': '11_investor_institution', 'trcode': 'opt10060', 'inputs': {'종목코드': code, '일자': target_date}},
            {'name': '12_foreign_institution', 'trcode': 'opt10061', 'inputs': {'종목코드': code, '기준일자': target_date}},
            {'name': '13_program_trading', 'trcode': 'opt10062', 'inputs': {'종목코드': code, '시간구분': '0'}},
            {'name': '14_time_conclusion', 'trcode': 'opt10016', 'inputs': {'종목코드': code, '시간구분': '1'}},
            {'name': '15_daily_trading_top', 'trcode': 'opt10063', 'inputs': {'종목코드': code, '조회구분': '1'}},
            {'name': '16_monthly_investor', 'trcode': 'opt10064', 'inputs': {'종목코드': code, '시작일자': target_date, '끝일자': datetime.now().strftime('%Y%m%d')}},
            {'name': '17_credit_balance', 'trcode': 'opt10013', 'inputs': {'종목코드': code, '기준일자': target_date}},
        ]

        # TR 요청 실행 (API 제한 준수)
        for i, tr in enumerate(tr_list):
            logger.info(f"Requesting {tr['name']}...")
            data = request_tr_sync(tr['name'], tr['trcode'], tr['inputs'])
            result_data['data'][tr['name']] = data

            # API 제한 준수 (0.3초 대기, 마지막 요청 제외)
            if i < len(tr_list) - 1:
                time.sleep(0.3)

        # 수집된 데이터 개수
        success_count = len([k for k, v in result_data['data'].items() if v and 'error' not in v])
        result_data['success_count'] = success_count
        result_data['total_count'] = len(result_data['data'])

        logger.info(f"Comprehensive data collected: {success_count}/{result_data['total_count']}")

        return jsonify(result_data)

    except Exception as e:
        logger.error(f"Comprehensive data error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Shutdown server"""
    logger.info("🛑 Shutting down OpenAPI server...")

    # Cleanup OpenAPI context
    global openapi_context
    if openapi_context:
        try:
            openapi_context.__exit__(None, None, None)
        except:
            pass
        openapi_context = None

    # Shutdown Flask
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()

    return jsonify({'message': 'Server shutting down'})


def run_flask_in_thread():
    """Run Flask server in background thread"""
    logger.info(f"🚀 Starting Flask HTTP server on http://{OPENAPI_HOST}:{PORTS['openapi']}")
    app.run(
        host=OPENAPI_HOST,
        port=PORTS['openapi'],
        debug=False,
        use_reloader=False,
        threaded=False,  # ❗ Qt 메인 스레드 문제 방지
        processes=1
    )


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("OpenAPI Server (32-bit)")
    logger.info("=" * 60)

    # Check Python architecture
    import struct
    bits = struct.calcsize('P') * 8
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Architecture: {bits}-bit")

    if bits != 32:
        logger.error("❌ ERROR: This server must run in 32-bit Python!")
        logger.error("   Please use: conda activate autotrade_32")
        sys.exit(1)

    logger.info("   Available endpoints:")
    logger.info("   - GET  /health")
    logger.info("   - POST /connect")
    logger.info("   - GET  /accounts")
    logger.info("   - GET  /balance/<account_no>")
    logger.info("   - POST /order")
    logger.info("   - GET  /realtime/price/<code>")
    logger.info("   - POST /shutdown")
    logger.info("-" * 60)

    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask_in_thread, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask server started in background thread")

    # Wait for Flask to initialize
    import time
    time.sleep(2)

    # Initialize OpenAPI in MAIN thread (Qt requirement)
    logger.info("")
    logger.info("🔧 Initializing OpenAPI in main thread...")
    logger.info("   (Qt GUI must run in main thread)")
    logger.info("")

    success = initialize_openapi_in_main_thread()

    if not success:
        logger.error("")
        logger.error("❌ OpenAPI initialization failed")
        logger.error("   Server will continue running, but OpenAPI is not available")
        logger.error("")
        return

    # 로그인 이벤트 핸들러 정의
    def on_login(err_code):
        global connection_status, account_list

        if err_code == 0:
            connection_status = "connected"
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ 로그인 성공!")
            logger.info("=" * 60)

            # Get account list (로그인 성공 후에도 계좌 목록이 없을 수 있음)
            logger.info("🔍 Getting account list...")
            try:
                # breadum/kiwoom uses GetLoginInfo("ACCNO") or GetLoginInfo("ACCOUNT_CNT")
                account_str = openapi_context.GetLoginInfo("ACCNO")
                if account_str:
                    # ACCNO returns semicolon-separated account numbers
                    account_list = [acc.strip() for acc in account_str.split(';') if acc.strip()]
                    logger.info(f"   계좌 목록: {account_list}")
                else:
                    logger.warning("   계좌 목록이 비어있습니다 (모의투자 또는 계좌 없음)")
                    account_list = []
            except Exception as e:
                logger.warning(f"   계좌 목록 조회 실패: {e}")
                account_list = []

            logger.info("=" * 60)
            logger.info("")
            logger.info("✅ Server is ready!")
            logger.info("   Press Ctrl+C to stop")
            logger.info("")
        else:
            connection_status = "failed"
            logger.error("")
            logger.error("=" * 60)
            logger.error(f"❌ 로그인 실패: err_code={err_code}")
            logger.error("=" * 60)

    # 이벤트 핸들러 연결
    logger.info("")
    logger.info("🔐 Connecting event handler and starting login...")
    logger.info("   👀 로그인 창을 찾아보세요!")
    logger.info("   - 화면에 보이지 않으면 작업 표시줄의 깜빡이는 아이콘 클릭")
    logger.info("   - Alt+Tab으로 창 전환해보세요")
    logger.info("")

    openapi_context.OnEventConnect.connect(on_login)

    # CommConnect() 먼저 호출 (비동기로 로그인 창 띄움)
    openapi_context.CommConnect()

    # Keep main thread alive with Qt event loop
    try:
        if qt_app is not None:
            logger.info("🔄 Starting Qt event loop in main thread...")
            # Qt 이벤트 루프 실행 (GUI 표시에 필요)
            sys.exit(qt_app.exec_())
        else:
            # Qt 앱이 없으면 단순 대기
            logger.info("⚠️  Qt application not available, using simple loop")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down...")
        if openapi_context:
            try:
                openapi_context.__exit__(None, None, None)
            except:
                pass
        sys.exit(0)


if __name__ == '__main__':
    main()
