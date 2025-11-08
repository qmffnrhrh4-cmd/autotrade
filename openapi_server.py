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
from flask import Flask, jsonify, request
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Set Qt environment before importing koapy
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
connection_status = "not_started"  # not_started, connecting, connected, failed


def initialize_openapi_in_main_thread():
    """Initialize OpenAPI in MAIN thread (Qt requirement)"""
    global openapi_context, account_list, connection_status

    try:
        # Qt 애플리케이션을 먼저 생성
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer

        logger.info("🔧 Initializing Qt Application...")

        # QApplication이 이미 있는지 확인
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
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

        # 로그인 이벤트 핸들러 등록
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
                    account_list = openapi_context.get_account_list()
                    if account_list and len(account_list) > 0:
                        logger.info(f"   계좌 목록: {account_list}")
                    else:
                        logger.warning("   계좌 목록이 비어있습니다 (모의투자 또는 계좌 없음)")
                        account_list = []
                except Exception as e:
                    logger.warning(f"   계좌 목록 조회 실패: {e}")
                    account_list = []

                logger.info("=" * 60)
            else:
                connection_status = "failed"
                logger.error("")
                logger.error("=" * 60)
                logger.error(f"❌ 로그인 실패: err_code={err_code}")
                logger.error("=" * 60)

        # 이벤트 핸들러 연결
        openapi_context.OnEventConnect.connect(on_login)

        # 비동기 로그인 시작
        logger.info("🔐 Starting async login...")
        logger.info("   👀 로그인 창을 찾아보세요!")
        logger.info("   - 화면에 보이지 않으면 작업 표시줄의 깜빡이는 아이콘 클릭")
        logger.info("   - Alt+Tab으로 창 전환해보세요")
        logger.info("")

        # CommConnect()는 비동기로 실행됨 (Qt 이벤트 루프에서 처리)
        openapi_context.CommConnect()

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

    if success:
        logger.info("")
        logger.info("✅ Server is ready!")
        logger.info("   Press Ctrl+C to stop")
        logger.info("")
    else:
        logger.error("")
        logger.error("❌ OpenAPI initialization failed")
        logger.error("   Server will continue running, but OpenAPI is not available")
        logger.error("")

    # Keep main thread alive with Qt event loop
    try:
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            logger.info("🔄 Starting Qt event loop in main thread...")
            # Qt 이벤트 루프 실행 (GUI 표시에 필요)
            sys.exit(app.exec_())
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
