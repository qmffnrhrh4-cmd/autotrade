"""
Market Routes Module
Handles all market data API endpoints including orderbook, news, chart data, and rankings
"""
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys
import pandas as pd
from flask import Blueprint, jsonify, request
from utils.response_helper import error_response

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Create Blueprint
market_bp = Blueprint('market', __name__)

# Module-level variables
_bot_instance = None
_realtime_chart_manager = None


def set_bot_instance(bot):
    """Set the bot instance for market routes"""
    global _bot_instance
    _bot_instance = bot


def set_realtime_chart_manager(manager):
    """Set the realtime chart manager for market routes"""
    global _realtime_chart_manager
    _realtime_chart_manager = manager


@market_bp.route('/api/orderbook/<stock_code>')
def get_orderbook_api(stock_code: str):
    """Get real-time order book for stock"""
    try:
        from features.order_book import OrderBookService

        if _bot_instance and hasattr(_bot_instance, 'market_api'):
            service = OrderBookService(_bot_instance.market_api)
            data = service.get_order_book_for_dashboard(stock_code)
            return jsonify(data)
        else:
            return error_response('Bot not initialized')
    except Exception as e:
        return error_response(str(e))


@market_bp.route('/api/news/<stock_code>')
def get_news_api(stock_code: str):
    """Get news feed for stock with sentiment analysis"""
    try:
        from features.news_feed import NewsFeedService

        # Get stock name from bot if available
        stock_name = stock_code
        if _bot_instance and hasattr(_bot_instance, 'market_api'):
            # Try to get stock name from market API
            # For now, use code as fallback
            pass

        service = NewsFeedService()
        result = service.get_news_for_dashboard(stock_code, stock_name, limit=10)
        return jsonify(result)
    except Exception as e:
        print(f"News API error: {e}")
        return error_response(str(e))


@market_bp.route('/api/search/stocks')
def search_stocks():
    """Search stocks by code or name"""
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 20))

        if not query:
            return jsonify({'success': False, 'message': 'Query required', 'results': []})

        # 종목 검색 (종목코드 또는 종목명)
        results = []

        if _bot_instance and hasattr(_bot_instance, 'market_api'):
            try:
                # 간단한 종목 검색 - 실제로는 종목 마스터 DB를 검색해야 함
                # 여기서는 상위 거래량 종목에서 검색
                from research import DataFetcher
                data_fetcher = DataFetcher(_bot_instance.client)

                # 거래량 상위 종목 가져오기
                volume_rank = data_fetcher.get_volume_rank('ALL', 100)

                # 검색어로 필터링
                query_lower = query.lower()
                for stock in volume_rank:
                    code = stock.get('code', '')
                    name = stock.get('name', '')

                    # 종목코드 또는 종목명에 검색어 포함 여부 확인
                    if (query_lower in code.lower() or
                        query_lower in name.lower() or
                        query in code or
                        query in name):
                        results.append({
                            'code': code,
                            'name': name,
                            'price': stock.get('price', 0),
                            'change_rate': stock.get('change_rate', 0)
                        })

                    if len(results) >= limit:
                        break

                return jsonify({
                    'success': True,
                    'query': query,
                    'count': len(results),
                    'results': results
                })

            except Exception as e:
                print(f"Stock search error: {e}")
                # Note: error_response doesn't support 'results' key, so keep jsonify for special format
                return jsonify({
                    'success': False,
                    'message': str(e),
                    'results': []
                })
        else:
            return jsonify({
                'success': False,
                'message': 'Bot not initialized',
                'results': []
            })

    except Exception as e:
        print(f"Search API error: {e}")
        # Note: error_response doesn't support 'results' key, so keep jsonify for special format
        return jsonify({'success': False, 'message': str(e), 'results': []})


@market_bp.route('/api/chart/<stock_code>')
def get_chart_data(stock_code: str):
    """Get real chart data from Kiwoom API with timeframe support"""
    try:
        timeframe = request.args.get('timeframe', 'D')  # D=일봉, W=주봉, M=월봉, 숫자=분봉
        print(f"\n📊 Chart request for {stock_code} (timeframe: {timeframe})")

        if not _bot_instance:
            print(f"❌ bot_instance is None")
            return jsonify({
                'success': False,
                'error': '트레이딩 봇이 초기화되지 않았습니다',
                'data': [],
                'signals': [],
                'name': stock_code,
                'current_price': 0
            })

        if not hasattr(_bot_instance, 'data_fetcher'):
            print(f"❌ bot_instance has no data_fetcher")
            return jsonify({
                'success': False,
                'error': '데이터 수집기를 사용할 수 없습니다',
                'data': [],
                'signals': [],
                'name': stock_code,
                'current_price': 0
            })

        print(f"✓ bot_instance and data_fetcher available")

        # Get real OHLCV data from Kiwoom
        chart_data = []
        indicators = {}

        try:
            from utils.trading_date import get_last_trading_date

            # Get proper trading date (handles weekends and test mode)
            # If bot is in test mode, use test_date; otherwise use last trading date
            if _bot_instance and hasattr(_bot_instance, 'test_mode_active') and _bot_instance.test_mode_active:
                end_date_str = getattr(_bot_instance, 'test_date', get_last_trading_date())
                print(f"🧪 Test mode active, using test_date: {end_date_str}")
            else:
                end_date_str = get_last_trading_date()
                print(f"📆 Using last trading date: {end_date_str}")

            # Calculate start date (150 days back for ~100 trading days)
            end_date = datetime.strptime(end_date_str, '%Y%m%d')
            start_date = end_date - timedelta(days=150)
            start_date_str = start_date.strftime('%Y%m%d')

            print(f"📅 Fetching data from {start_date_str} to {end_date_str}")

            # Fetch data based on timeframe
            daily_data = []
            actual_timeframe = timeframe  # Track what we actually got

            if timeframe.isdigit():
                # Minute data (1, 5, 15, 30, 60)
                print(f"📊 Attempting to fetch {timeframe}-minute data")

                minute_data_available = False
                interval = int(timeframe)

                # 1. Try OpenAPI first (과거 데이터 포함, 가장 안정적)
                if _bot_instance and hasattr(_bot_instance, 'openapi_client') and _bot_instance.openapi_client:
                    if _bot_instance.openapi_client.is_connected:
                        try:
                            print(f"📊 Trying OpenAPI minute data (past data available)...")
                            openapi_minute_data = _bot_instance.openapi_client.get_minute_data(
                                stock_code=stock_code,
                                interval=interval
                            )

                            if openapi_minute_data and len(openapi_minute_data) > 0:
                                print(f"✅ OpenAPI minute data: {len(openapi_minute_data)} candles")
                                # Convert OpenAPI format to internal format
                                daily_data = []
                                for item in openapi_minute_data:
                                    # OpenAPI 형식: {'체결시간': 'YYYYMMDDHHMMSS', '현재가': '70000', ...}
                                    time_str = item.get('체결시간', '').strip()

                                    # 체결시간에서 일자/시간 분리
                                    if len(time_str) >= 14:
                                        # YYYYMMDDHHMMSS 형식
                                        date = time_str[:8]
                                        time = time_str[8:14]
                                    elif len(time_str) >= 8:
                                        # YYYYMMDD 형식 (시간 없음)
                                        date = time_str[:8]
                                        time = ''
                                    else:
                                        # 날짜 정보 없음
                                        date = ''
                                        time = time_str

                                    # 가격 데이터는 부호 제거 ('+', '-' 제거)
                                    current_price = item.get('현재가', '0').replace('+', '').replace('-', '').strip()
                                    open_price = item.get('시가', '0').replace('+', '').replace('-', '').strip()
                                    high_price = item.get('고가', '0').replace('+', '').replace('-', '').strip()
                                    low_price = item.get('저가', '0').replace('+', '').replace('-', '').strip()
                                    volume = item.get('거래량', '0').strip()

                                    daily_data.append({
                                        'date': date,
                                        'time': time,
                                        'open': int(open_price) if open_price else 0,
                                        'high': int(high_price) if high_price else 0,
                                        'low': int(low_price) if low_price else 0,
                                        'close': int(current_price) if current_price else 0,
                                        'volume': int(volume) if volume else 0
                                    })
                                minute_data_available = True
                                actual_timeframe = timeframe
                            else:
                                print(f"⚠️ OpenAPI minute data: no data (weekend/holiday)")
                        except Exception as e:
                            print(f"⚠️ OpenAPI minute data failed: {e}")
                    else:
                        print(f"⚠️ OpenAPI not connected")

                # 2. Try real-time minute data if OpenAPI failed (장중 실시간)
                if not minute_data_available and _realtime_chart_manager:
                    try:
                        # Check if we have real-time data for this stock
                        if stock_code in _realtime_chart_manager.charts:
                            candle_count = _realtime_chart_manager.charts[stock_code].get_candle_count()
                            if candle_count > 0:
                                print(f"✅ Using real-time minute data ({candle_count} candles)")
                                # Get requested number of minutes (default 60)
                                minutes = int(timeframe) if timeframe == '1' else 60
                                daily_data = _realtime_chart_manager.get_minute_data(stock_code, minutes=minutes)
                                minute_data_available = True
                                actual_timeframe = timeframe
                        else:
                            # Stock not subscribed yet, try to add it
                            print(f"📡 Adding {stock_code} to real-time tracking...")
                            try:
                                # Create NEW event loop to avoid conflicts
                                import threading

                                def add_stock_sync(stock_code):
                                    """Add stock in separate thread with new event loop"""
                                    new_loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(new_loop)
                                    try:
                                        result = new_loop.run_until_complete(
                                            _realtime_chart_manager.add_stock(stock_code)
                                        )
                                        return result
                                    finally:
                                        new_loop.close()

                                # Run in thread to avoid event loop conflicts
                                from concurrent.futures import ThreadPoolExecutor, TimeoutError
                                with ThreadPoolExecutor(max_workers=1) as executor:
                                    future = executor.submit(add_stock_sync, stock_code)
                                    try:
                                        success = future.result(timeout=5)
                                        if success:
                                            print(f"✅ {stock_code} added to real-time tracking")
                                            # Try to get data after subscription (might be empty initially)
                                            minutes = int(timeframe) if timeframe == '1' else 60
                                            daily_data = _realtime_chart_manager.get_minute_data(stock_code, minutes=minutes)
                                            if daily_data and len(daily_data) > 0:
                                                minute_data_available = True
                                                actual_timeframe = timeframe
                                    except TimeoutError:
                                        print(f"⚠️ Timeout adding {stock_code} to real-time tracking")
                            except Exception as e:
                                print(f"⚠️ Failed to add stock to real-time tracking: {e}")
                    except Exception as e:
                        print(f"⚠️ Real-time data fetch failed: {e}")

                # 3. Fallback to daily data if all minute data sources failed
                if not minute_data_available:
                    print(f"⚠️ All minute data sources failed, falling back to daily data")
                    actual_timeframe = 'D'
                    daily_data = _bot_instance.data_fetcher.get_daily_price(
                        stock_code=stock_code,
                        start_date=start_date_str,
                        end_date=end_date_str
                    )
            else:
                # Daily, Weekly, Monthly data
                daily_data = _bot_instance.data_fetcher.get_daily_price(
                    stock_code=stock_code,
                    start_date=start_date_str,
                    end_date=end_date_str
                )

            print(f"📦 Received {len(daily_data) if daily_data else 0} data points (timeframe: {actual_timeframe})")

            # Get current price and stock name
            current_price = 0
            stock_name = stock_code
            try:
                price_info = _bot_instance.market_api.get_current_price(stock_code)
                if price_info:
                    current_price = int(price_info.get('prpr', 0))
                    stock_name = price_info.get('prdt_name', stock_code)
            except:
                pass

            # Convert daily data to chart format and calculate indicators
            if daily_data:
                # 분봉은 1000개, 일봉은 200개로 제한 (분봉 1000개 ≈ 16시간, 일봉 200개 ≈ 7개월)
                limit = 1000 if actual_timeframe in ['1', '3', '5', '10', '15', '30', '60'] else 200
                print(f"🔄 Converting {len(daily_data[:limit])} data points to chart format (timeframe: {actual_timeframe})")

                # Take data and reverse to get chronological order (oldest to newest)
                recent_data = daily_data[:limit]
                recent_data.reverse()  # Reverse to get oldest first

                # Prepare data for indicators
                df = pd.DataFrame(recent_data)
                df['close'] = df['close'].astype(float)
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['volume'] = df['volume'].astype(float)

                # Calculate indicators with safety checks
                from indicators.momentum import rsi, macd
                from indicators.trend import sma, ema
                from indicators.volatility import bollinger_bands

                # Initialize indicators as None
                rsi_values = None
                macd_line = signal_line = histogram = None
                sma_5 = sma_20 = sma_60 = None
                ema_12 = ema_26 = None
                bb_upper = bb_middle = bb_lower = None

                try:
                    # RSI (requires at least 15 data points)
                    if len(df) >= 15:
                        rsi_values = rsi(df['close'], period=14)
                except Exception as e:
                    print(f"⚠️ RSI calculation error: {e}")

                try:
                    # MACD (requires at least 34 data points: 26 + 9 - 1)
                    if len(df) >= 34:
                        macd_line, signal_line, histogram = macd(df['close'])
                except Exception as e:
                    print(f"⚠️ MACD calculation error: {e}")

                try:
                    # Moving Averages
                    if len(df) >= 5:
                        sma_5 = sma(df['close'], 5)
                    if len(df) >= 20:
                        sma_20 = sma(df['close'], 20)
                    if len(df) >= 60:
                        sma_60 = sma(df['close'], 60)
                    if len(df) >= 12:
                        ema_12 = ema(df['close'], 12)
                    if len(df) >= 26:
                        ema_26 = ema(df['close'], 26)
                except Exception as e:
                    print(f"⚠️ Moving averages calculation error: {e}")

                try:
                    # Bollinger Bands (requires at least 20 data points)
                    if len(df) >= 20:
                        bb_upper, bb_middle, bb_lower = bollinger_bands(df['close'], period=20, std_dev=2.0)
                except Exception as e:
                    print(f"⚠️ Bollinger Bands calculation error: {e}")

                # Prepare indicator data
                indicators = {
                    'rsi': [],
                    'macd': [],
                    'volume': [],
                    'ma5': [],
                    'ma20': [],
                    'ma60': [],
                    'ema12': [],
                    'ema26': [],
                    'bb_upper': [],
                    'bb_middle': [],
                    'bb_lower': []
                }

                for idx, item in enumerate(recent_data):
                    try:
                        # Parse date and time
                        date_str = item.get('date', item.get('stck_bsop_date', ''))
                        time_str = item.get('time', item.get('stck_cntg_hour', ''))

                        if date_str:
                            # For minute data, combine date and time
                            if timeframe.isdigit() and time_str:
                                # Minute data: YYYYMMDD + HHMMSS -> UNIX timestamp
                                datetime_str = f"{date_str}{time_str}"
                                try:
                                    dt_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                                    timestamp = int(dt_obj.timestamp())
                                    time_value = timestamp
                                except:
                                    # Fallback to date only
                                    date_obj = datetime.strptime(date_str, '%Y%m%d')
                                    formatted_date = date_obj.strftime('%Y-%m-%d')
                                    time_value = formatted_date
                            else:
                                # Daily data: YYYYMMDD -> YYYY-MM-DD
                                date_obj = datetime.strptime(date_str, '%Y%m%d')
                                formatted_date = date_obj.strftime('%Y-%m-%d')
                                time_value = formatted_date

                            chart_data.append({
                                'time': time_value,
                                'open': float(item.get('open', item.get('stck_oprc', 0))),
                                'high': float(item.get('high', item.get('stck_hgpr', 0))),
                                'low': float(item.get('low', item.get('stck_lwpr', 0))),
                                'close': float(item.get('close', item.get('stck_clpr', 0)))
                            })

                            # Add indicator data (use time_value for both daily and minute data)
                            # Use try-except for each indicator to avoid slice errors
                            try:
                                if rsi_values is not None and idx < len(rsi_values) and not pd.isna(rsi_values.iloc[idx]):
                                    indicators['rsi'].append({'time': time_value, 'value': float(rsi_values.iloc[idx])})
                            except Exception as e:
                                pass

                            try:
                                if macd_line is not None and idx < len(macd_line) and not pd.isna(macd_line.iloc[idx]):
                                    indicators['macd'].append({
                                        'time': time_value,
                                        'macd': float(macd_line.iloc[idx]),
                                        'signal': float(signal_line.iloc[idx]),
                                        'histogram': float(histogram.iloc[idx])
                                    })
                            except Exception as e:
                                pass

                            # Volume - Korean stock market convention: 상승(빨강), 하락(파랑)
                            close_price = float(item.get('close', 0))
                            open_price = float(item.get('open', 0))
                            indicators['volume'].append({
                                'time': time_value,
                                'value': float(item.get('volume', 0)),
                                'color': '#ef4444' if close_price >= open_price else '#3b82f6'  # Red for up, Blue for down
                            })

                            # Moving Averages (only add if not NaN)
                            try:
                                if sma_5 is not None and idx < len(sma_5) and not pd.isna(sma_5.iloc[idx]):
                                    indicators['ma5'].append({'time': time_value, 'value': float(sma_5.iloc[idx])})
                            except Exception as e:
                                pass

                            try:
                                if sma_20 is not None and idx < len(sma_20) and not pd.isna(sma_20.iloc[idx]):
                                    indicators['ma20'].append({'time': time_value, 'value': float(sma_20.iloc[idx])})
                            except Exception as e:
                                pass

                            try:
                                if sma_60 is not None and idx < len(sma_60) and not pd.isna(sma_60.iloc[idx]):
                                    indicators['ma60'].append({'time': time_value, 'value': float(sma_60.iloc[idx])})
                            except Exception as e:
                                pass

                            try:
                                if ema_12 is not None and idx < len(ema_12) and not pd.isna(ema_12.iloc[idx]):
                                    indicators['ema12'].append({'time': time_value, 'value': float(ema_12.iloc[idx])})
                            except Exception as e:
                                pass

                            try:
                                if ema_26 is not None and idx < len(ema_26) and not pd.isna(ema_26.iloc[idx]):
                                    indicators['ema26'].append({'time': time_value, 'value': float(ema_26.iloc[idx])})
                            except Exception as e:
                                pass

                            # Bollinger Bands
                            try:
                                if bb_upper is not None and idx < len(bb_upper) and not pd.isna(bb_upper.iloc[idx]):
                                    indicators['bb_upper'].append({'time': time_value, 'value': float(bb_upper.iloc[idx])})
                                    indicators['bb_middle'].append({'time': time_value, 'value': float(bb_middle.iloc[idx])})
                                    indicators['bb_lower'].append({'time': time_value, 'value': float(bb_lower.iloc[idx])})
                            except Exception as e:
                                pass

                    except Exception as e:
                        print(f"⚠️ Error parsing chart data item: {e}, item={item}")
                        continue

                print(f"✅ Chart data ready: {len(chart_data)} points")
                if len(chart_data) > 0:
                    print(f"📊 Date range: {chart_data[0]['time']} to {chart_data[-1]['time']}")
            else:
                print(f"⚠️ No daily data received from API")

            # Generate AI trading signals (placeholder - would come from real AI analysis)
            signals = []

            return jsonify({
                'success': True,
                'data': chart_data,
                'indicators': indicators,
                'signals': signals,
                'name': stock_name,
                'current_price': current_price,
                'timeframe': actual_timeframe,  # Actual timeframe used (may differ from requested)
                'requested_timeframe': timeframe  # What user requested
            })

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Chart data fetch error for {stock_code}: {error_msg}")
            import traceback
            traceback.print_exc()

            # Log to activity monitor
            if _bot_instance and hasattr(_bot_instance, 'monitor'):
                _bot_instance.monitor.log_activity(
                    'error',
                    f'차트 로드 실패 ({stock_code}): {error_msg}',
                    level='error'
                )

            # Return error response with message
            return jsonify({
                'success': False,
                'error': f'차트 데이터를 가져올 수 없습니다: {error_msg}',
                'data': [],
                'signals': [],
                'name': stock_code,
                'current_price': 0
            })

    except Exception as e:
        print(f"📊 Chart API outer error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e))


@market_bp.route('/api/realtime_chart/add/<stock_code>', methods=['POST'])
def add_realtime_chart(stock_code):
    """Add stock to real-time minute chart tracking"""
    try:
        if not _realtime_chart_manager:
            return jsonify({
                'success': False,
                'error': '실시간 차트 관리자가 초기화되지 않았습니다'
            })

        # Use thread-safe event loop approach
        from concurrent.futures import ThreadPoolExecutor, TimeoutError

        def add_stock_sync(stock_code):
            """Add stock in separate thread with new event loop"""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                result = new_loop.run_until_complete(
                    _realtime_chart_manager.add_stock(stock_code)
                )
                return result
            finally:
                new_loop.close()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(add_stock_sync, stock_code)
            try:
                success = future.result(timeout=10)
                return jsonify({
                    'success': success,
                    'message': f'{"성공적으로 추가됨" if success else "추가 실패"}: {stock_code}'
                })
            except TimeoutError:
                return jsonify({
                    'success': False,
                    'error': '종목 추가 시간 초과'
                })
    except Exception as e:
        return error_response(str(e))


@market_bp.route('/api/realtime_chart/remove/<stock_code>', methods=['POST'])
def remove_realtime_chart(stock_code):
    """Remove stock from real-time minute chart tracking"""
    try:
        if not _realtime_chart_manager:
            return jsonify({
                'success': False,
                'error': '실시간 차트 관리자가 초기화되지 않았습니다'
            })

        # Use thread-safe event loop approach
        from concurrent.futures import ThreadPoolExecutor, TimeoutError

        def remove_stock_sync(stock_code):
            """Remove stock in separate thread with new event loop"""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(
                    _realtime_chart_manager.remove_stock(stock_code)
                )
                return True
            finally:
                new_loop.close()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(remove_stock_sync, stock_code)
            try:
                future.result(timeout=10)
                return jsonify({
                    'success': True,
                    'message': f'제거됨: {stock_code}'
                })
            except TimeoutError:
                return jsonify({
                    'success': False,
                    'error': '종목 제거 시간 초과'
                })
    except Exception as e:
        return error_response(str(e))


@market_bp.route('/api/realtime_chart/status')
def get_realtime_chart_status():
    """Get status of all real-time tracked stocks"""
    try:
        if not _realtime_chart_manager:
            return jsonify({
                'success': False,
                'error': '실시간 차트 관리자가 초기화되지 않았습니다'
            })

        status = _realtime_chart_manager.get_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return error_response(str(e))


@market_bp.route('/api/chart/<stock_code>/daily')
def get_daily_chart_data(stock_code: str):
    """Get daily chart data"""
    try:
        if not _bot_instance or not hasattr(_bot_instance, 'openapi_client'):
            return jsonify({
                'success': False,
                'error': 'OpenAPI 클라이언트를 사용할 수 없습니다',
                'data': []
            })

        openapi_client = _bot_instance.openapi_client
        if not openapi_client or not openapi_client.is_connected:
            return jsonify({
                'success': False,
                'error': 'OpenAPI가 연결되지 않았습니다',
                'data': []
            })

        # Get comprehensive data which includes daily chart
        comprehensive_data = openapi_client.get_comprehensive_data(stock_code)

        if not comprehensive_data or 'data' not in comprehensive_data:
            return jsonify({
                'success': False,
                'error': '종합 데이터 가져오기 실패',
                'data': []
            })

        # Extract daily chart data
        daily_chart = comprehensive_data['data'].get('04_daily_chart', {})

        if 'items' not in daily_chart or not daily_chart['items']:
            return jsonify({
                'success': False,
                'error': '일봉 차트 데이터가 없습니다',
                'data': []
            })

        return jsonify({
            'success': True,
            'data': daily_chart['items']
        })

    except Exception as e:
        logger.error(f"Daily chart data error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        })


@market_bp.route('/api/chart/<stock_code>/minute/<int:interval>')
def get_minute_chart_data(stock_code: str, interval: int):
    """Get minute chart data"""
    try:
        if not _bot_instance or not hasattr(_bot_instance, 'openapi_client'):
            return jsonify({
                'success': False,
                'error': 'OpenAPI 클라이언트를 사용할 수 없습니다',
                'data': []
            })

        openapi_client = _bot_instance.openapi_client
        if not openapi_client or not openapi_client.is_connected:
            return jsonify({
                'success': False,
                'error': 'OpenAPI가 연결되지 않았습니다',
                'data': []
            })

        # Validate interval
        valid_intervals = [1, 3, 5, 10, 15, 30, 60]
        if interval not in valid_intervals:
            return jsonify({
                'success': False,
                'error': f'잘못된 분봉 간격입니다. 유효한 값: {valid_intervals}',
                'data': []
            })

        # Get minute data
        minute_data = openapi_client.get_minute_data(stock_code, interval)

        if not minute_data or len(minute_data) == 0:
            return jsonify({
                'success': False,
                'error': '분봉 데이터가 없습니다',
                'data': []
            })

        return jsonify({
            'success': True,
            'data': minute_data
        })

    except Exception as e:
        logger.error(f"Minute chart data error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        })


@market_bp.route('/api/chart/ai_analysis/<stock_code>')
def get_ai_chart_analysis(stock_code: str):
    """Get AI-powered chart analysis with key points"""
    try:
        if not _bot_instance:
            return jsonify({
                'success': False,
                'error': '트레이딩 봇이 초기화되지 않았습니다'
            })

        timeframe = request.args.get('timeframe', 'D')

        # Get chart data first - Use correct method signature
        from research import DataFetcher
        from utils.trading_date import get_last_trading_date

        # Create DataFetcher (same as virtual trading fix)
        if hasattr(_bot_instance, 'data_fetcher') and _bot_instance.data_fetcher:
            data_fetcher = _bot_instance.data_fetcher
        else:
            data_fetcher = DataFetcher(_bot_instance.client)

        # Calculate date range (60 trading days ≈ 90 calendar days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')

        # Fetch recent data with correct parameters
        daily_data = data_fetcher.get_daily_price(
            stock_code=stock_code,
            start_date=start_date_str,
            end_date=end_date_str
        )

        # Safety check: ensure daily_data is a list
        if not daily_data or not isinstance(daily_data, list) or len(daily_data) == 0:
            return jsonify({
                'success': False,
                'error': '차트 데이터가 없습니다'
            })

        # Analyze chart patterns and signals
        analysis_points = []

        # Initialize variables
        trend_change = 0
        support = 0
        resistance = 0
        current_price = 0

        # Simple trend analysis - with safety check
        recent_prices = [item.get('close', 0) for item in daily_data[-20:]] if len(daily_data) >= 20 else [item.get('close', 0) for item in daily_data]
        if len(recent_prices) >= 20:
            trend_start = recent_prices[0]
            trend_end = recent_prices[-1]
            trend_change = ((trend_end - trend_start) / trend_start) * 100

            if trend_change > 10:
                analysis_points.append({
                    'type': 'trend',
                    'signal': 'bullish',
                    'description': f'강한 상승 추세 ({trend_change:.1f}% 상승)',
                    'date': daily_data[-1].get('date'),
                    'price': recent_prices[-1],
                    'confidence': 'high'
                })
            elif trend_change < -10:
                analysis_points.append({
                    'type': 'trend',
                    'signal': 'bearish',
                    'description': f'강한 하락 추세 ({abs(trend_change):.1f}% 하락)',
                    'date': daily_data[-1].get('date'),
                    'price': recent_prices[-1],
                    'confidence': 'high'
                })

        # Volume analysis - with safety checks
        recent_volumes = [item.get('volume', 0) for item in daily_data[-20:]] if len(daily_data) >= 20 else [item.get('volume', 0) for item in daily_data]
        if len(recent_volumes) >= 20:
            avg_volume = sum(recent_volumes[:-1]) / len(recent_volumes[:-1]) if len(recent_volumes) > 1 else recent_volumes[0]
            current_volume = recent_volumes[-1]

            if avg_volume > 0 and current_volume > avg_volume * 2:
                analysis_points.append({
                    'type': 'volume',
                    'signal': 'breakout',
                    'description': f'거래량 급증 (평균 대비 {(current_volume/avg_volume):.1f}배)',
                    'date': daily_data[-1].get('date'),
                    'price': recent_prices[-1] if recent_prices else 0,
                    'confidence': 'high'
                })

        # Support/Resistance levels - with safety checks
        all_prices = [item.get('close', 0) for item in daily_data] if daily_data else []
        if len(recent_prices) >= 20:
            support = min(recent_prices[-20:])
            resistance = max(recent_prices[-20:])
            current_price = recent_prices[-1]
        elif len(recent_prices) > 0:
            support = min(recent_prices)
            resistance = max(recent_prices)
            current_price = recent_prices[-1]
        else:
            support = 0
            resistance = 0
            current_price = 0

        # Test support/resistance only if we have valid values
        if support > 0 and abs(current_price - support) / support < 0.02:
            analysis_points.append({
                'type': 'support',
                'signal': 'support_test',
                'description': f'지지선 테스트 ({support:,.0f}원)',
                'date': daily_data[-1].get('date') if daily_data else '',
                'price': support,
                'confidence': 'medium'
            })

        if resistance > 0 and abs(current_price - resistance) / resistance < 0.02:
            analysis_points.append({
                'type': 'resistance',
                'signal': 'resistance_test',
                'description': f'저항선 테스트 ({resistance:,.0f}원)',
                'date': daily_data[-1].get('date') if daily_data else '',
                'price': resistance,
                'confidence': 'medium'
            })

        # Summary
        summary = {
            'trend': 'neutral',
            'strength': 'medium',
            'recommendation': 'hold',
            'key_levels': {
                'support': support,
                'resistance': resistance,
                'current': current_price
            }
        }

        if trend_change > 5:
            summary['trend'] = 'bullish'
            summary['recommendation'] = 'buy'
        elif trend_change < -5:
            summary['trend'] = 'bearish'
            summary['recommendation'] = 'sell'

        # JavaScript가 기대하는 형식으로 변환
        # analysis_points를 annotations 형식으로 변환
        annotations = []
        for idx, point in enumerate(analysis_points):
            anno = {
                'type': 'point' if point['type'] in ['trend', 'volume'] else 'line',
                'price': point.get('price', 0),
                'label': point.get('description', ''),
                'signal': point.get('signal', ''),
                'color': 'rgba(255, 99, 132, 0.8)' if 'bullish' in point.get('signal', '') or 'buy' in point.get('signal', '') else 'rgba(54, 162, 235, 0.8)'
            }
            # 인덱스 추정 (최근 포인트들이므로 차트 끝부분)
            if idx < len(daily_data):
                anno['position'] = len(daily_data) - len(analysis_points) + idx
            else:
                anno['position'] = len(daily_data) - 1

            annotations.append(anno)

        # 지지/저항선 추가
        if support > 0:
            annotations.append({
                'type': 'line',
                'price': support,
                'label': f'지지선: {support:,.0f}원',
                'color': 'rgb(75, 192, 192)'
            })

        if resistance > 0:
            annotations.append({
                'type': 'line',
                'price': resistance,
                'label': f'저항선: {resistance:,.0f}원',
                'color': 'rgb(255, 205, 86)'
            })

        # summary를 문자열로 변환
        summary_text = f"{summary['recommendation'].upper()} | 추세: {summary['trend']} | 현재가: {summary['key_levels']['current']:,.0f}원"

        # key_points 생성
        key_points = [point.get('description', '') for point in analysis_points]

        analysis_result = {
            'signal': summary['recommendation'],
            'summary': summary_text,
            'key_points': key_points,
            'annotations': annotations
        }

        return jsonify({
            'success': True,
            'stock_code': stock_code,
            'timeframe': timeframe,
            'analysis': analysis_result,  # JavaScript가 기대하는 키
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        print(f"AI Chart Analysis error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e))


@market_bp.route('/api/market/detect/<stock_code>')
def detect_market_condition(stock_code: str):
    """Detect market condition and alerts"""
    try:
        if not _bot_instance:
            return jsonify({
                'success': False,
                'error': '트레이딩 봇이 초기화되지 않았습니다'
            })

        from market_detector import integrate_with_bot

        # Initialize detector
        detector = integrate_with_bot(_bot_instance)

        # Detect market condition
        result = detector.detect_market_condition(stock_code)

        return jsonify({
            'success': True,
            'detection': result
        })

    except Exception as e:
        logger.error(f"Market detection error: {e}")
        return error_response(str(e))


@market_bp.route('/api/market/auto-response/<stock_code>', methods=['POST'])
def auto_response_to_market(stock_code: str):
    """Auto response to market condition"""
    try:
        if not _bot_instance:
            return jsonify({
                'success': False,
                'error': '트레이딩 봇이 초기화되지 않았습니다'
            })

        from market_detector import integrate_with_bot

        # Get current positions
        positions = request.json.get('positions', [])

        # Initialize detector
        detector = integrate_with_bot(_bot_instance)

        # Get auto response
        response = detector.auto_response(stock_code, positions)

        return jsonify({
            'success': True,
            'response': response
        })

    except Exception as e:
        logger.error(f"Auto response error: {e}")
        return error_response(str(e))
