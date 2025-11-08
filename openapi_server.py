"""
OpenAPI Server (32-bit only)
=============================
This server runs in 32-bit Python environment and provides OpenAPI functionality via HTTP.

Main application (64-bit) communicates with this server via HTTP requests.

Architecture:
- 32-bit Python 3.10 (Anaconda autotrade_32)
- koapy for OpenAPI connection
- Flask for HTTP API
- Port: 5001

Usage:
    conda activate autotrade_32
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
# Ensure Qt GUI runs properly
os.environ['QT_QPA_PLATFORM'] = 'windows'

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
        from koapy import KiwoomOpenApiPlusEntrypoint

        logger.info("🔧 Initializing OpenAPI connection...")
        connection_status = "connecting"

        # IMPORTANT: Qt GUI must run in main thread
        openapi_context = KiwoomOpenApiPlusEntrypoint().__enter__()

        # Auto-login (will show login window)
        logger.info("🔐 Attempting login...")
        logger.info("   ⚠️  로그인 창이 나타납니다. 로그인을 완료해주세요.")
        openapi_context.EnsureConnected()

        # Check connection
        state = openapi_context.GetConnectState()
        if state == 1:
            account_list = openapi_context.GetAccountList()
            connection_status = "connected"
            logger.info(f"✅ OpenAPI connected! Accounts: {account_list}")
            return True
        else:
            connection_status = "failed"
            logger.error("❌ OpenAPI connection failed")
            return False

    except Exception as e:
        connection_status = "failed"
        logger.error(f"❌ OpenAPI initialization error: {e}")
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

    # Keep main thread alive (Qt event loop)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down...")
        sys.exit(0)


if __name__ == '__main__':
    main()
